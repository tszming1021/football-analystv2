#!/usr/bin/env python3
"""Offline-trained national-team model for World Cup style matches.

Training reads historical CSV/JSON once and writes a compact JSON artifact.
Prediction only loads that artifact, so match analysis does not need to scan
historical datasets at runtime.
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DATA_DIR = Path(os.getenv("FOOTBALL_HISTORICAL_DATA_DIR", "data/historical"))
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "trained" / "worldcup_model.json"


@dataclass
class NationalTeamProfile:
    team: str
    matches: int
    elo: float
    attack_strength: float
    defense_weakness: float
    goals_for_avg: float
    goals_against_avg: float
    clean_sheet_rate: float
    failed_to_score_rate: float
    recent_form: List[str] = field(default_factory=list)
    tournament_mix: Dict[str, int] = field(default_factory=dict)
    top_scorer_share: float = 0.0
    shootout_win_rate: Optional[float] = None


@dataclass
class WorldCupModelArtifact:
    version: str
    trained_at: str
    source_dir: str
    global_goals_per_team: float
    neutral_goal_factor: float
    home_advantage_factor: float
    team_profiles: Dict[str, NationalTeamProfile]
    aliases: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["team_profiles"] = {
            team: asdict(profile) for team, profile in self.team_profiles.items()
        }
        return payload


class WorldCupOfflineTrainer:
    """Train compact national-team priors from downloaded public data."""

    IMPORTANT_TOURNAMENTS = {
        "FIFA World Cup": 1.45,
        "FIFA World Cup qualification": 1.25,
        "UEFA Euro": 1.25,
        "UEFA Euro qualification": 1.15,
        "Copa América": 1.22,
        "AFC Asian Cup": 1.16,
        "African Cup of Nations": 1.16,
        "CONCACAF Gold Cup": 1.12,
        "Oceania Nations Cup": 1.08,
        "UEFA Nations League": 1.08,
        "Friendly": 0.62,
    }

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR, cutoff_date: Optional[str] = None):
        self.data_dir = Path(data_dir)
        self.results_path = self.data_dir / "kaggle" / "results.csv"
        self.goalscorers_path = self.data_dir / "kaggle" / "goalscorers.csv"
        self.shootouts_path = self.data_dir / "kaggle" / "shootouts.csv"
        self.former_names_path = self.data_dir / "kaggle" / "former_names.csv"
        self.cutoff_date = datetime.strptime(cutoff_date, "%Y-%m-%d") if cutoff_date else None

    def train(self) -> WorldCupModelArtifact:
        if not self.results_path.exists():
            raise FileNotFoundError(f"Missing Kaggle results CSV: {self.results_path}")

        aliases = self._load_aliases()
        rows = self._load_results(aliases)
        if not rows:
            raise ValueError("No match rows loaded from historical data")

        ratings: Dict[str, float] = defaultdict(lambda: 1500.0)
        weighted_for: Dict[str, float] = defaultdict(float)
        weighted_against: Dict[str, float] = defaultdict(float)
        weights: Dict[str, float] = defaultdict(float)
        matches: Dict[str, int] = defaultdict(int)
        clean_sheets: Dict[str, int] = defaultdict(int)
        failed_to_score: Dict[str, int] = defaultdict(int)
        recent_form: Dict[str, deque] = defaultdict(lambda: deque(maxlen=8))
        tournament_mix: Dict[str, Counter] = defaultdict(Counter)
        total_goals = 0
        total_team_games = 0

        latest_date = max(row["date"] for row in rows)
        for row in rows:
            home = row["home_team"]
            away = row["away_team"]
            hs = row["home_score"]
            aw = row["away_score"]
            tournament = row["tournament"]
            neutral = row["neutral"]
            importance = self._importance(tournament)
            recency = self._recency_weight(row["date"], latest_date)
            weight = importance * recency

            self._update_elo(ratings, home, away, hs, aw, neutral, importance)

            for team, gf, ga, result in [
                (home, hs, aw, "W" if hs > aw else ("D" if hs == aw else "L")),
                (away, aw, hs, "W" if aw > hs else ("D" if hs == aw else "L")),
            ]:
                matches[team] += 1
                weighted_for[team] += gf * weight
                weighted_against[team] += ga * weight
                weights[team] += weight
                clean_sheets[team] += 1 if ga == 0 else 0
                failed_to_score[team] += 1 if gf == 0 else 0
                recent_form[team].append(result)
                tournament_mix[team][tournament] += 1
                total_goals += gf
                total_team_games += 1

        global_goals = total_goals / total_team_games if total_team_games else 1.25
        scorer_share = self._top_scorer_share(aliases)
        shootout_rates = self._shootout_rates(aliases)
        profiles: Dict[str, NationalTeamProfile] = {}
        for team in sorted(matches):
            avg_for = weighted_for[team] / weights[team] if weights[team] else global_goals
            avg_against = weighted_against[team] / weights[team] if weights[team] else global_goals
            profiles[team] = NationalTeamProfile(
                team=team,
                matches=matches[team],
                elo=round(ratings[team], 1),
                attack_strength=round(avg_for / global_goals, 4),
                defense_weakness=round(avg_against / global_goals, 4),
                goals_for_avg=round(avg_for, 4),
                goals_against_avg=round(avg_against, 4),
                clean_sheet_rate=round(clean_sheets[team] / matches[team], 4),
                failed_to_score_rate=round(failed_to_score[team] / matches[team], 4),
                recent_form=list(recent_form[team]),
                tournament_mix=dict(tournament_mix[team].most_common(8)),
                top_scorer_share=round(scorer_share.get(team, 0.0), 4),
                shootout_win_rate=shootout_rates.get(team),
            )

        return WorldCupModelArtifact(
            version="worldcup-offline-v1",
            trained_at=datetime.now().isoformat(timespec="seconds"),
            source_dir=str(self.data_dir),
            global_goals_per_team=round(global_goals, 4),
            neutral_goal_factor=0.94,
            home_advantage_factor=1.08,
            team_profiles=profiles,
            aliases=aliases,
            metadata={
                "matches_loaded": len(rows),
                "teams": len(profiles),
                "sources": [
                    str(self.results_path),
                    str(self.goalscorers_path),
                    str(self.shootouts_path),
                    str(self.former_names_path),
                ],
                "runtime_note": "Prediction loads this JSON artifact only; historical CSV files are not read at match time.",
            },
        )

    def save(self, output_path: Path = DEFAULT_MODEL_PATH) -> WorldCupModelArtifact:
        artifact = self.train()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact

    def _load_results(self, aliases: Dict[str, str]) -> List[Dict[str, Any]]:
        rows = []
        with self.results_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    date = datetime.strptime(row["date"], "%Y-%m-%d")
                    if self.cutoff_date and date >= self.cutoff_date:
                        continue
                    rows.append({
                        "date": date,
                        "home_team": self._canonical(row["home_team"], aliases),
                        "away_team": self._canonical(row["away_team"], aliases),
                        "home_score": int(row["home_score"]),
                        "away_score": int(row["away_score"]),
                        "tournament": row.get("tournament") or "Unknown",
                        "neutral": str(row.get("neutral", "")).upper() == "TRUE",
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        rows.sort(key=lambda item: item["date"])
        return rows

    def _load_aliases(self) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        if not self.former_names_path.exists():
            return aliases
        with self.former_names_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                current = row.get("current") or row.get("current_name") or row.get("new_name")
                former = row.get("former") or row.get("former_name") or row.get("old_name")
                if current and former:
                    aliases[self._norm(former)] = current.strip()
        return aliases

    def _top_scorer_share(self, aliases: Dict[str, str]) -> Dict[str, float]:
        if not self.goalscorers_path.exists():
            return {}
        scorers: Dict[str, Counter] = defaultdict(Counter)
        with self.goalscorers_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                team = self._canonical(row.get("team", ""), aliases)
                scorer = (row.get("scorer") or "").strip()
                if team and scorer:
                    scorers[team][scorer] += 1
        return {
            team: (counter.most_common(1)[0][1] / sum(counter.values()))
            for team, counter in scorers.items()
            if counter and sum(counter.values())
        }

    def _shootout_rates(self, aliases: Dict[str, str]) -> Dict[str, float]:
        if not self.shootouts_path.exists():
            return {}
        wins: Dict[str, int] = defaultdict(int)
        total: Dict[str, int] = defaultdict(int)
        with self.shootouts_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                home = self._canonical(row.get("home_team", ""), aliases)
                away = self._canonical(row.get("away_team", ""), aliases)
                winner = self._canonical(row.get("winner", ""), aliases)
                for team in [home, away]:
                    if team:
                        total[team] += 1
                if winner:
                    wins[winner] += 1
        return {team: round(wins[team] / count, 4) for team, count in total.items() if count}

    @classmethod
    def _update_elo(
        cls,
        ratings: Dict[str, float],
        home: str,
        away: str,
        hs: int,
        aw: int,
        neutral: bool,
        importance: float,
    ):
        home_advantage = 0 if neutral else 55
        diff = ratings[home] + home_advantage - ratings[away]
        expected_home = 1 / (1 + 10 ** (-diff / 400))
        actual_home = 1.0 if hs > aw else (0.5 if hs == aw else 0.0)
        margin = max(1, abs(hs - aw))
        margin_factor = math.log(margin + 1)
        k = 18 * importance * margin_factor
        change = k * (actual_home - expected_home)
        ratings[home] += change
        ratings[away] -= change

    @classmethod
    def _importance(cls, tournament: str) -> float:
        if tournament in cls.IMPORTANT_TOURNAMENTS:
            return cls.IMPORTANT_TOURNAMENTS[tournament]
        lowered = tournament.lower()
        if "qualification" in lowered:
            return 1.12
        if "cup" in lowered or "championship" in lowered:
            return 1.10
        return 0.85

    @staticmethod
    def _recency_weight(date: datetime, latest_date: datetime) -> float:
        years = max(0.0, (latest_date - date).days / 365.25)
        return 0.35 + 0.65 * math.exp(-years / 9.0)

    @classmethod
    def _canonical(cls, value: str, aliases: Dict[str, str]) -> str:
        cleaned = (value or "").strip()
        return aliases.get(cls._norm(cleaned), cleaned)

    @staticmethod
    def _norm(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())


class WorldCupTrainedModel:
    """Runtime model that only reads the compact training artifact."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)
        self.artifact: Optional[Dict[str, Any]] = None
        if self.model_path.exists():
            self.artifact = json.loads(self.model_path.read_text(encoding="utf-8"))

    @property
    def available(self) -> bool:
        return bool(self.artifact and self.artifact.get("team_profiles"))

    def profile(self, team: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        profiles = self.artifact.get("team_profiles") or {}
        aliases = self.artifact.get("aliases") or {}
        canonical = aliases.get(WorldCupOfflineTrainer._norm(team), team)
        if canonical in profiles:
            return profiles[canonical]
        normalized = WorldCupOfflineTrainer._norm(canonical)
        for name, profile in profiles.items():
            if WorldCupOfflineTrainer._norm(name) == normalized:
                return profile
        return None

    def lambdas(self, home_team: str, away_team: str, neutral: bool = True) -> Optional[Tuple[float, float]]:
        home = self.profile(home_team)
        away = self.profile(away_team)
        if not home or not away or not self.artifact:
            return None
        base = float(self.artifact.get("global_goals_per_team") or 1.25)
        home_adv = 1.0 if neutral else float(self.artifact.get("home_advantage_factor") or 1.08)
        neutral_factor = float(self.artifact.get("neutral_goal_factor") or 0.94) if neutral else 1.0
        elo_diff = float(home.get("elo", 1500)) - float(away.get("elo", 1500))
        strength_home = math.exp(elo_diff / 900)
        strength_away = math.exp(-elo_diff / 900)
        home_lambda = base * float(home["attack_strength"]) * float(away["defense_weakness"]) * strength_home * home_adv * neutral_factor
        away_lambda = base * float(away["attack_strength"]) * float(home["defense_weakness"]) * strength_away * neutral_factor
        return max(0.15, home_lambda), max(0.15, away_lambda)

    def summary(self, home_team: str, away_team: str) -> Dict[str, Any]:
        return {
            "model_path": str(self.model_path),
            "version": (self.artifact or {}).get("version"),
            "home_profile": self.profile(home_team),
            "away_profile": self.profile(away_team),
        }


__all__ = [
    "DEFAULT_DATA_DIR",
    "DEFAULT_MODEL_PATH",
    "NationalTeamProfile",
    "WorldCupModelArtifact",
    "WorldCupOfflineTrainer",
    "WorldCupTrainedModel",
]
