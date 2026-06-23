#!/usr/bin/env python3
"""
World Cup focused data collection and prediction module.

Primary free/low-cost source strategy:
- football-data.org: World Cup fixtures/teams (requires FOOTBALL_DATA_ORG_KEY).
- API-Football: national-team stats, fixtures, h2h when plan allows (API_FOOTBALL_KEY).
- Odds-API.io / The Odds API: real bookmaker odds (ODDS_API_IO_KEY or THE_ODDS_API_KEY).
- TheSportsDB: free team/event metadata fallback (THESPORTSDB_KEY, defaults to public key 123).
"""

import os
import re
import requests
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.math_models import PoissonModel, KellyCriterion
from core.worldcup_trained_model import DEFAULT_MODEL_PATH, WorldCupTrainedModel


@dataclass
class WorldCupFixture:
    source: str
    home_team: str
    away_team: str
    match_date: Optional[str] = None
    status: Optional[str] = None
    competition: str = "FIFA World Cup"
    fixture_id: Optional[str] = None
    venue: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldCupTeamForm:
    team: str
    source: str
    matches_played: int = 0
    goals_for_avg: Optional[float] = None
    goals_against_avg: Optional[float] = None
    recent_form: List[str] = field(default_factory=list)
    rating_hint: float = 1.0


@dataclass
class WorldCupOdds:
    source: str
    bookmaker: str
    home_win: float
    draw: float
    away_win: float
    event_id: Optional[str] = None
    last_update: Optional[str] = None


@dataclass
class WorldCupPrediction:
    fixture: Optional[WorldCupFixture]
    home_form: WorldCupTeamForm
    away_form: WorldCupTeamForm
    expected_home_goals: float
    expected_away_goals: float
    probabilities: Dict[str, float]
    most_likely_score: Tuple[int, int]
    odds: List[WorldCupOdds]
    kelly: List[Dict[str, Any]]
    warnings: List[str]
    sources_used: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorldCupPredictor:
    """Collect World Cup data and produce a conservative Poisson/Kelly prediction."""

    FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
    API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
    SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
    ODDS_API_IO_BASE = "https://api.odds-api.io/v3"
    THE_ODDS_API_BASE = "https://api.the-odds-api.com/v4"

    FOOTBALL_DATA_WC_CODE = "WC"
    API_FOOTBALL_WORLD_CUP_LEAGUE_ID = 1
    THE_ODDS_WORLD_CUP_KEYS = [
        "soccer_fifa_world_cup",
        "soccer_fifa_world_cup_winner",
    ]

    def __init__(
        self,
        football_data_key: Optional[str] = None,
        api_football_key: Optional[str] = None,
        odds_api_io_key: Optional[str] = None,
        the_odds_api_key: Optional[str] = None,
        sportsdb_key: Optional[str] = None,
        season: int = 2026,
        trained_model_path: Optional[str] = None,
    ):
        self.football_data_key = football_data_key or os.getenv("FOOTBALL_DATA_ORG_KEY")
        self.api_football_key = api_football_key or os.getenv("API_FOOTBALL_KEY")
        self.odds_api_io_key = odds_api_io_key or os.getenv("ODDS_API_IO_KEY")
        self.the_odds_api_key = the_odds_api_key or os.getenv("THE_ODDS_API_KEY")
        self.sportsdb_key = sportsdb_key or os.getenv("THESPORTSDB_KEY", "123")
        self.odds_api_io_bookmakers = os.getenv("ODDS_API_IO_BOOKMAKERS", "1xbet")
        self.season = season
        self.session = requests.Session()
        self.trained_model = WorldCupTrainedModel(trained_model_path or os.getenv("WORLDCUP_TRAINED_MODEL_PATH") or DEFAULT_MODEL_PATH)

    def predict_match(self, home_team: str, away_team: str, bankroll: float = 10000) -> WorldCupPrediction:
        warnings: List[str] = []
        sources_used: List[str] = []

        fixture = self.find_fixture(home_team, away_team, warnings, sources_used)
        home_form = self.get_team_form(home_team, warnings, sources_used)
        away_form = self.get_team_form(away_team, warnings, sources_used)

        home_lambda, away_lambda = self._estimate_lambdas(home_form, away_form)
        poisson = PoissonModel.calculate_match_probabilities(home_lambda, away_lambda)

        odds = self.get_match_odds(home_team, away_team, warnings, sources_used)
        kelly = []
        if odds:
            selected = self._best_odds(odds)
            kelly_results = KellyCriterion.calculate_all(
                poisson_probs=poisson,
                odds={
                    "home": selected.home_win,
                    "draw": selected.draw,
                    "away": selected.away_win,
                },
                bankroll=bankroll,
                kelly_fraction=0.25,
            )
            kelly = [asdict(item) for item in kelly_results]
        else:
            warnings.append("未获取到真实世界杯赔率，跳过 EV/凯利计算")

        return WorldCupPrediction(
            fixture=fixture,
            home_form=home_form,
            away_form=away_form,
            expected_home_goals=poisson.expected_home_goals,
            expected_away_goals=poisson.expected_away_goals,
            probabilities={
                "home_win": poisson.home_win_prob,
                "draw": poisson.draw_prob,
                "away_win": poisson.away_win_prob,
                "over_2_5": poisson.over_25_prob,
                "under_2_5": poisson.under_25_prob,
                "btts_yes": poisson.btts_yes_prob,
            },
            most_likely_score=poisson.most_likely_score,
            odds=odds,
            kelly=kelly,
            warnings=list(dict.fromkeys(warnings)),
            sources_used=list(dict.fromkeys(sources_used)),
        )

    def find_fixture(
        self,
        home_team: str,
        away_team: str,
        warnings: List[str],
        sources_used: List[str],
    ) -> Optional[WorldCupFixture]:
        fixture = self._football_data_fixture(home_team, away_team, warnings)
        if fixture:
            sources_used.append("football-data.org")
            return fixture

        fixture = self._api_football_fixture(home_team, away_team, warnings)
        if fixture:
            sources_used.append("API-Football")
            return fixture

        fixture = self._sportsdb_event(home_team, away_team, warnings)
        if fixture:
            sources_used.append("TheSportsDB")
            return fixture

        warnings.append("未从免费数据源找到对应世界杯赛程")
        return None

    def get_team_form(
        self,
        team_name: str,
        warnings: List[str],
        sources_used: List[str],
    ) -> WorldCupTeamForm:
        trained = self._trained_team_form(team_name)
        if trained:
            sources_used.append("WorldCup offline trained model")
            return trained

        form = self._api_football_team_form(team_name, warnings)
        if form.matches_played:
            sources_used.append("API-Football")
            return form

        form = self._football_data_team_metadata(team_name, warnings)
        if form.source != "fallback":
            sources_used.append("football-data.org")
            return form

        sportsdb = self._sportsdb_team_metadata(team_name, warnings)
        if sportsdb.source != "fallback":
            sources_used.append("TheSportsDB")
            return sportsdb

        warnings.append(f"{team_name} 缺少可靠近期数据，使用中性球队强度")
        return form

    def get_match_odds(
        self,
        home_team: str,
        away_team: str,
        warnings: List[str],
        sources_used: List[str],
    ) -> List[WorldCupOdds]:
        odds = self._odds_api_io_odds(home_team, away_team, warnings)
        if odds:
            sources_used.append("Odds-API.io")
            return odds

        odds = self._the_odds_api_odds(home_team, away_team, warnings)
        if odds:
            sources_used.append("The Odds API")
            return odds

        return []

    def _football_data_fixture(self, home_team: str, away_team: str, warnings: List[str]) -> Optional[WorldCupFixture]:
        if not self.football_data_key:
            warnings.append("未设置 FOOTBALL_DATA_ORG_KEY，跳过 football-data.org 世界杯赛程")
            return None

        data = self._get_json(
            f"{self.FOOTBALL_DATA_BASE}/competitions/{self.FOOTBALL_DATA_WC_CODE}/matches",
            headers={"X-Auth-Token": self.football_data_key},
            params={"season": self.season},
            warnings=warnings,
            source="football-data.org matches",
        )
        for match in data.get("matches", []) if isinstance(data, dict) else []:
            home = match.get("homeTeam", {}).get("name", "")
            away = match.get("awayTeam", {}).get("name", "")
            if self._same_match(home, away, home_team, away_team):
                return WorldCupFixture(
                    source="football-data.org",
                    home_team=home,
                    away_team=away,
                    match_date=match.get("utcDate"),
                    status=match.get("status"),
                    fixture_id=str(match.get("id")),
                    raw=match,
                )
        return None

    def _api_football_fixture(self, home_team: str, away_team: str, warnings: List[str]) -> Optional[WorldCupFixture]:
        if not self.api_football_key:
            warnings.append("未设置 API_FOOTBALL_KEY，跳过 API-Football 世界杯赛程")
            return None

        data = self._api_football_get(
            "fixtures",
            {
                "league": self.API_FOOTBALL_WORLD_CUP_LEAGUE_ID,
                "season": self.season,
                "from": f"{self.season}-06-01",
                "to": f"{self.season}-07-31",
            },
            warnings,
        )
        for item in data.get("response", []) if isinstance(data, dict) else []:
            home = item.get("teams", {}).get("home", {}).get("name", "")
            away = item.get("teams", {}).get("away", {}).get("name", "")
            if self._same_match(home, away, home_team, away_team):
                fixture = item.get("fixture", {})
                return WorldCupFixture(
                    source="API-Football",
                    home_team=home,
                    away_team=away,
                    match_date=fixture.get("date"),
                    status=fixture.get("status", {}).get("long"),
                    fixture_id=str(fixture.get("id")),
                    venue=(fixture.get("venue") or {}).get("name"),
                    raw=item,
                )
        return None

    def _sportsdb_event(self, home_team: str, away_team: str, warnings: List[str]) -> Optional[WorldCupFixture]:
        query = f"fifa world cup {self.season} {home_team} vs {away_team}"
        data = self._get_json(
            f"{self.SPORTSDB_BASE}/{self.sportsdb_key}/searchevents.php",
            params={"e": query},
            warnings=warnings,
            source="TheSportsDB event search",
        )
        events = data.get("event") or [] if isinstance(data, dict) else []
        for event in events:
            home = event.get("strHomeTeam", "")
            away = event.get("strAwayTeam", "")
            if self._same_match(home, away, home_team, away_team):
                return WorldCupFixture(
                    source="TheSportsDB",
                    home_team=home,
                    away_team=away,
                    match_date=event.get("dateEvent"),
                    status=event.get("strStatus"),
                    fixture_id=event.get("idEvent"),
                    venue=event.get("strVenue"),
                    raw=event,
                )
        return None

    def _api_football_team_form(self, team_name: str, warnings: List[str]) -> WorldCupTeamForm:
        if not self.api_football_key:
            return WorldCupTeamForm(team=team_name, source="fallback")

        team_id = self._api_football_team_id(team_name, warnings)
        if not team_id:
            return WorldCupTeamForm(team=team_name, source="fallback")

        for season in [self.season, self.season - 1, self.season - 2, 2022]:
            data = self._api_football_get(
                "teams/statistics",
                {
                    "team": team_id,
                    "league": self.API_FOOTBALL_WORLD_CUP_LEAGUE_ID,
                    "season": season,
                },
                warnings,
            )
            stats = data.get("response") if isinstance(data, dict) else None
            if not isinstance(stats, dict) or not stats:
                continue

            played = stats.get("fixtures", {}).get("played", {}).get("total") or 0
            goals_for = stats.get("goals", {}).get("for", {}).get("total", {}).get("total") or 0
            goals_against = stats.get("goals", {}).get("against", {}).get("total", {}).get("total") or 0
            if played:
                return WorldCupTeamForm(
                    team=team_name,
                    source=f"API-Football World Cup {season}",
                    matches_played=played,
                    goals_for_avg=goals_for / played,
                    goals_against_avg=goals_against / played,
                    recent_form=list(stats.get("form") or "")[-5:],
                    rating_hint=1.0,
                )
        return WorldCupTeamForm(team=team_name, source="fallback")

    def _trained_team_form(self, team_name: str) -> Optional[WorldCupTeamForm]:
        profile = self.trained_model.profile(team_name)
        if not profile:
            return None
        return WorldCupTeamForm(
            team=profile.get("team", team_name),
            source=f"offline trained model {self.trained_model.model_path}",
            matches_played=int(profile.get("matches") or 0),
            goals_for_avg=float(profile.get("goals_for_avg") or 0.0),
            goals_against_avg=float(profile.get("goals_against_avg") or 0.0),
            recent_form=list(profile.get("recent_form") or []),
            rating_hint=float(profile.get("elo") or 1500.0),
        )

    def _football_data_team_metadata(self, team_name: str, warnings: List[str]) -> WorldCupTeamForm:
        if not self.football_data_key:
            return WorldCupTeamForm(team=team_name, source="fallback")

        data = self._get_json(
            f"{self.FOOTBALL_DATA_BASE}/competitions/{self.FOOTBALL_DATA_WC_CODE}/teams",
            headers={"X-Auth-Token": self.football_data_key},
            params={"season": self.season},
            warnings=warnings,
            source="football-data.org teams",
        )
        for team in data.get("teams", []) if isinstance(data, dict) else []:
            if self._norm(team.get("name")) == self._norm(team_name):
                return WorldCupTeamForm(team=team.get("name", team_name), source="football-data.org teams")
        return WorldCupTeamForm(team=team_name, source="fallback")

    def _sportsdb_team_metadata(self, team_name: str, warnings: List[str]) -> WorldCupTeamForm:
        data = self._get_json(
            f"{self.SPORTSDB_BASE}/{self.sportsdb_key}/searchteams.php",
            params={"t": team_name},
            warnings=warnings,
            source="TheSportsDB team search",
        )
        teams = data.get("teams") or [] if isinstance(data, dict) else []
        if teams:
            return WorldCupTeamForm(team=teams[0].get("strTeam", team_name), source="TheSportsDB teams")
        return WorldCupTeamForm(team=team_name, source="fallback")

    def _odds_api_io_odds(self, home_team: str, away_team: str, warnings: List[str]) -> List[WorldCupOdds]:
        if not self.odds_api_io_key:
            warnings.append("未设置 ODDS_API_IO_KEY，跳过 Odds-API.io 赔率")
            return []

        leagues = self._get_json(
            f"{self.ODDS_API_IO_BASE}/leagues",
            params={"apiKey": self.odds_api_io_key, "sport": "football"},
            warnings=warnings,
            source="Odds-API.io leagues",
        )
        league_slug = None
        for league in leagues if isinstance(leagues, list) else []:
            label = f"{league.get('name', '')} {league.get('slug', '')}".lower()
            if "world" in label and "cup" in label:
                league_slug = league.get("slug")
                break
        if not league_slug:
            warnings.append("Odds-API.io 未发现 World Cup league slug")
            return []

        events = self._get_json(
            f"{self.ODDS_API_IO_BASE}/events",
            params={
                "apiKey": self.odds_api_io_key,
                "sport": "football",
                "league": league_slug,
                "status": "pending",
                "limit": 100,
            },
            warnings=warnings,
            source="Odds-API.io events",
        )
        event_id = None
        for event in events if isinstance(events, list) else []:
            if self._same_match(event.get("home", ""), event.get("away", ""), home_team, away_team):
                event_id = event.get("id")
                break
        if not event_id:
            warnings.append("Odds-API.io 未找到该场世界杯比赛赔率事件")
            return []

        odds_data = self._get_json(
            f"{self.ODDS_API_IO_BASE}/odds",
            params={
                "apiKey": self.odds_api_io_key,
                "eventId": event_id,
                "bookmakers": self.odds_api_io_bookmakers,
            },
            warnings=warnings,
            source="Odds-API.io odds",
        )
        return self._parse_odds_api_io_payload(odds_data, str(event_id))

    def _the_odds_api_odds(self, home_team: str, away_team: str, warnings: List[str]) -> List[WorldCupOdds]:
        if not self.the_odds_api_key:
            warnings.append("未设置 THE_ODDS_API_KEY，跳过 The Odds API 赔率")
            return []

        sports = self._get_json(
            f"{self.THE_ODDS_API_BASE}/sports",
            params={"apiKey": self.the_odds_api_key, "all": "true"},
            warnings=warnings,
            source="The Odds API sports",
        )
        sport_keys = []
        for sport in sports if isinstance(sports, list) else []:
            key = sport.get("key", "")
            label = f"{key} {sport.get('title', '')} {sport.get('description', '')}".lower()
            if "soccer" in label and "world" in label and "cup" in label:
                sport_keys.append(key)
        sport_keys.extend([key for key in self.THE_ODDS_WORLD_CUP_KEYS if key not in sport_keys])

        for sport_key in sport_keys:
            data = self._get_json(
                f"{self.THE_ODDS_API_BASE}/sports/{sport_key}/odds",
                params={
                    "apiKey": self.the_odds_api_key,
                    "regions": "us,uk,eu",
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                },
                warnings=warnings,
                source=f"The Odds API {sport_key}",
            )
            parsed = self._parse_the_odds_api_payload(data, home_team, away_team)
            if parsed:
                return parsed
        return []

    def _api_football_team_id(self, team_name: str, warnings: List[str]) -> Optional[int]:
        data = self._api_football_get("teams", {"search": team_name}, warnings)
        for item in data.get("response", []) if isinstance(data, dict) else []:
            team = item.get("team", {})
            name = team.get("name", "")
            if self._norm(name) == self._norm(team_name) or self._norm(team_name) in self._norm(name):
                return team.get("id")
        return None

    def _api_football_get(self, endpoint: str, params: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
        if not self.api_football_key:
            return {}
        return self._get_json(
            f"{self.API_FOOTBALL_BASE}/{endpoint}",
            headers={"x-apisports-key": self.api_football_key},
            params=params,
            warnings=warnings,
            source=f"API-Football {endpoint}",
        )

    def _get_json(
        self,
        url: str,
        warnings: List[str],
        source: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            response = self.session.get(url, headers=headers or {}, params=params or {}, timeout=15)
            data = response.json()
        except Exception as e:
            warnings.append(f"{source} 请求失败: {e}")
            return {}

        if response.status_code >= 400:
            warnings.append(f"{source} HTTP {response.status_code}: {data}")
            return {}

        if isinstance(data, dict) and data.get("errors"):
            warnings.append(f"{source} API错误/限制: {data.get('errors')}")
        return data

    def _estimate_lambdas(self, home: WorldCupTeamForm, away: WorldCupTeamForm) -> Tuple[float, float]:
        trained = self.trained_model.lambdas(home.team, away.team, neutral=True)
        if trained:
            return trained

        home_attack = home.goals_for_avg if home.goals_for_avg is not None else 1.35
        home_defense = home.goals_against_avg if home.goals_against_avg is not None else 1.05
        away_attack = away.goals_for_avg if away.goals_for_avg is not None else 1.25
        away_defense = away.goals_against_avg if away.goals_against_avg is not None else 1.10

        home_lambda = max(0.2, ((home_attack + away_defense) / 2) * 1.03)
        away_lambda = max(0.2, ((away_attack + home_defense) / 2) * 0.97)
        return home_lambda, away_lambda

    def _best_odds(self, odds: List[WorldCupOdds]) -> WorldCupOdds:
        return WorldCupOdds(
            source="best_available",
            bookmaker="best_available",
            home_win=max(item.home_win for item in odds),
            draw=max(item.draw for item in odds),
            away_win=max(item.away_win for item in odds),
        )

    def _parse_odds_api_io_payload(self, payload: Any, event_id: str) -> List[WorldCupOdds]:
        if not isinstance(payload, dict):
            return []
        bookmakers = payload.get("bookmakers") or {}
        parsed = []
        for bookmaker_name, bookmaker_data in bookmakers.items():
            prices = None
            last_update = None

            if isinstance(bookmaker_data, dict):
                markets = bookmaker_data.get("markets", {})
                h2h = markets.get("h2h") or markets.get("moneyline") or markets.get("3way")
                prices = self._extract_three_way_prices(h2h)

            if isinstance(bookmaker_data, list):
                for market in bookmaker_data:
                    market_name = str(market.get("name", "")).lower()
                    if market_name not in {"ml", "moneyline", "match winner", "1x2", "3way"}:
                        continue
                    last_update = market.get("updatedAt")
                    odds_rows = market.get("odds") or []
                    prices = self._extract_three_way_prices(odds_rows[0] if odds_rows else None)
                    if prices:
                        break

            if prices:
                parsed.append(WorldCupOdds("Odds-API.io", bookmaker_name, *prices, event_id=event_id, last_update=last_update))
        return parsed

    def _parse_the_odds_api_payload(self, payload: Any, home_team: str, away_team: str) -> List[WorldCupOdds]:
        parsed = []
        for event in payload if isinstance(payload, list) else []:
            if not self._same_match(event.get("home_team", ""), event.get("away_team", ""), home_team, away_team):
                continue
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    outcomes = {item.get("name"): item.get("price") for item in market.get("outcomes", [])}
                    prices = (
                        self._float_or_zero(outcomes.get(event.get("home_team"))),
                        self._float_or_zero(outcomes.get("Draw")),
                        self._float_or_zero(outcomes.get(event.get("away_team"))),
                    )
                    if all(prices):
                        parsed.append(WorldCupOdds(
                            "The Odds API",
                            bookmaker.get("title", bookmaker.get("key", "unknown")),
                            *prices,
                            event_id=event.get("id"),
                            last_update=bookmaker.get("last_update"),
                        ))
        return parsed

    @staticmethod
    def _extract_three_way_prices(market: Any) -> Optional[Tuple[float, float, float]]:
        if isinstance(market, dict):
            keys = {str(key).lower(): value for key, value in market.items()}
            home = keys.get("home") or keys.get("1")
            draw = keys.get("draw") or keys.get("x")
            away = keys.get("away") or keys.get("2")
            prices = tuple(WorldCupPredictor._float_or_zero(value) for value in [home, draw, away])
            return prices if all(prices) else None
        if isinstance(market, list) and len(market) >= 3:
            prices = tuple(WorldCupPredictor._float_or_zero(value) for value in market[:3])
            return prices if all(prices) else None
        return None

    @staticmethod
    def _same_match(source_home: str, source_away: str, target_home: str, target_away: str) -> bool:
        return (
            WorldCupPredictor._team_match(source_home, target_home)
            and WorldCupPredictor._team_match(source_away, target_away)
        ) or (
            WorldCupPredictor._team_match(source_home, target_away)
            and WorldCupPredictor._team_match(source_away, target_home)
        )

    @staticmethod
    def _team_match(source: str, target: str) -> bool:
        a = WorldCupPredictor._norm(source)
        b = WorldCupPredictor._norm(target)
        return a == b or a in b or b in a

    @staticmethod
    def _norm(value: Optional[str]) -> str:
        value = (value or "").lower()
        value = re.sub(r"\b(fc|cf|national team|football team|men)\b", "", value)
        value = re.sub(r"[^a-z0-9]+", "", value)
        return value

    @staticmethod
    def _float_or_zero(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


__all__ = [
    "WorldCupFixture",
    "WorldCupTeamForm",
    "WorldCupOdds",
    "WorldCupPrediction",
    "WorldCupPredictor",
]
