from __future__ import annotations

import json
import math
import os
import random
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE = Path("data/worldcup_20260625")
API_DIR = BASE / "api"
OUT = BASE / "accessory_analysis.json"
API_BASE = "https://v3.football.api-sports.io"
FIXTURES = {
    "周三049": 1489408,
    "周三050": 1539009,
    "周三051": 1489406,
    "周三052": 1489405,
    "周三053": 1489407,
    "周三054": 1539010,
}
CONTEXT = {
    "周三049": {"ht_share": 0.42, "corner_home": 1.02, "corner_away": 0.95, "corner_total": 0.92, "card_total": 0.90},
    "周三050": {"ht_share": 0.47, "corner_home": 1.06, "corner_away": 1.06, "corner_total": 1.12, "card_total": 1.15},
    "周三051": {"ht_share": 0.44, "corner_home": 1.10, "corner_away": 0.95, "corner_total": 0.95, "card_total": 1.05},
    "周三052": {"ht_share": 0.46, "corner_home": 1.15, "corner_away": 0.90, "corner_total": 1.05, "card_total": 0.92},
    "周三053": {"ht_share": 0.44, "corner_home": 1.10, "corner_away": 1.05, "corner_total": 1.03, "card_total": 1.15},
    "周三054": {"ht_share": 0.43, "corner_home": 1.15, "corner_away": 0.90, "corner_total": 0.95, "card_total": 1.10},
}


def load_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def get_json(path: str, key: str) -> dict:
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.8)))
    response = session.get(
        API_BASE + path,
        headers={"x-apisports-key": key},
        timeout=30,
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def stat_map(team_block: dict) -> dict:
    return {item["type"]: item["value"] or 0 for item in team_block.get("statistics", [])}


def poisson(k: int, mean: float) -> float:
    return math.exp(-mean) * mean**k / math.factorial(k)


def score_matrix(home_mean: float, away_mean: float, maximum: int = 10) -> list[dict]:
    values = []
    for home in range(maximum + 1):
        for away in range(maximum + 1):
            values.append({"score": f"{home}-{away}", "probability": poisson(home, home_mean) * poisson(away, away_mean)})
    return sorted(values, key=lambda item: item["probability"], reverse=True)


def result_probabilities(matrix: list[dict]) -> dict:
    result = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for item in matrix:
        home, away = map(int, item["score"].split("-"))
        result["home" if home > away else "draw" if home == away else "away"] += item["probability"]
    return result


def mean_team_stats(samples: list[dict]) -> dict:
    keys = ["corners_for", "corners_against", "yellow_for", "yellow_against", "fouls_for", "shots_for", "shots_against"]
    if not samples:
        return {key: 0.0 for key in keys} | {"matches": 0}
    return {key: sum(float(item[key]) for item in samples) / len(samples) for key in keys} | {"matches": len(samples)}


def sample_poisson(mean: float, rng: random.Random) -> int:
    limit = math.exp(-mean)
    product = 1.0
    value = -1
    while product > limit:
        value += 1
        product *= rng.random()
    return value


def monte_carlo(home_mean: float, away_mean: float, seed: int, runs: int = 10000) -> dict:
    rng = random.Random(seed)
    result = {"home": 0, "draw": 0, "away": 0, "over_2_5": 0, "over_3_5": 0, "btts": 0}
    scores: dict[str, int] = {}
    for _ in range(runs):
        home = sample_poisson(home_mean, rng)
        away = sample_poisson(away_mean, rng)
        result["home" if home > away else "draw" if home == away else "away"] += 1
        result["over_2_5"] += home + away >= 3
        result["over_3_5"] += home + away >= 4
        result["btts"] += home > 0 and away > 0
        score = f"{home}-{away}"
        scores[score] = scores.get(score, 0) + 1
    return {
        "runs": runs,
        "probabilities": {key: value / runs for key, value in result.items()},
        "score_top10": [
            {"score": score, "probability": count / runs}
            for score, count in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
    }


def main() -> None:
    load_env(Path(".env"))
    key = os.environ["API_FOOTBALL_KEY"]
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    model_by_code = {item["identity"]["code"]: item for item in model["matches"]}
    team_samples: dict[int, list[dict]] = {}
    team_names: dict[int, str] = {}
    raw_audit: dict[str, dict] = {}

    for code, fixture_id in FIXTURES.items():
        fixture = json.loads((API_DIR / f"{fixture_id}_fixture.json").read_text(encoding="utf-8"))["response"][0]
        kickoff = fixture["fixture"]["timestamp"]
        raw_audit[code] = {"current_fixture": fixture_id, "teams": {}}
        for side in ("home", "away"):
            team = fixture["teams"][side]
            team_id = team["id"]
            team_names[team_id] = team["name"]
            if team_id in team_samples:
                continue
            fixtures = get_json(f"/fixtures?team={team_id}&league=1&season=2026&last=8", key).get("response", [])
            finished = [
                item for item in fixtures
                if item["fixture"]["timestamp"] < kickoff and item["fixture"]["status"]["short"] == "FT"
            ][-2:]
            samples = []
            for past in finished:
                past_id = past["fixture"]["id"]
                payload = get_json(f"/fixtures/statistics?fixture={past_id}", key)
                (API_DIR / f"history_{past_id}_statistics.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                blocks = payload.get("response", [])
                own = next((stat_map(item) for item in blocks if item["team"]["id"] == team_id), {})
                opponent = next((stat_map(item) for item in blocks if item["team"]["id"] != team_id), {})
                samples.append({
                    "fixture_id": past_id,
                    "opponent": next(
                        (item["team"]["name"] for item in blocks if item["team"]["id"] != team_id), "unknown"
                    ),
                    "corners_for": own.get("Corner Kicks", 0),
                    "corners_against": opponent.get("Corner Kicks", 0),
                    "yellow_for": own.get("Yellow Cards", 0),
                    "yellow_against": opponent.get("Yellow Cards", 0),
                    "fouls_for": own.get("Fouls", 0),
                    "shots_for": own.get("Total Shots", 0),
                    "shots_against": opponent.get("Total Shots", 0),
                })
            team_samples[team_id] = samples

    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "method": {
            "team_stats": "first two completed 2026 World Cup matches from API-Football; reliability n/(n+5), geometric for/against blend, remainder shrunk to tournament baseline",
            "half_time": "full-match decision mean split by LEG expected-goal share, then match-specific first-half share",
            "corners_cards": "for/against blend with group-final state, weather and tactical modifiers",
            "penalty_red": "tournament baseline adjusted by expected-goal and must-win intensity; lower-confidence auxiliary outputs",
            "simulation": "10,000 independent Poisson draws per match with deterministic seeds",
        },
        "matches": {},
        "team_samples": {},
    }
    for team_id, samples in team_samples.items():
        output["team_samples"][str(team_id)] = {"team": team_names[team_id], "matches": samples, "averages": mean_team_stats(samples)}

    for index, (code, fixture_id) in enumerate(FIXTURES.items(), start=1):
        fixture = json.loads((API_DIR / f"{fixture_id}_fixture.json").read_text(encoding="utf-8"))["response"][0]
        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]
        home_stats = mean_team_stats(team_samples[home_id])
        away_stats = mean_team_stats(team_samples[away_id])
        match = model_by_code[code]
        leg = match["leg"]
        total_mean = float(match["means"]["decision_final"])
        leg_total = max(0.01, leg["home_leg_expected_goals"] + leg["away_leg_expected_goals"])
        home_mean = total_mean * leg["home_leg_expected_goals"] / leg_total
        away_mean = total_mean - home_mean

        context = CONTEXT[code]
        ht_home = home_mean * context["ht_share"]
        ht_away = away_mean * context["ht_share"]
        ht_matrix = score_matrix(ht_home, ht_away, 7)
        ht_result = result_probabilities(ht_matrix)
        ht_total = ht_home + ht_away

        baseline_corners = 4.6
        corner_reliability = min(home_stats["matches"], away_stats["matches"]) / (
            min(home_stats["matches"], away_stats["matches"]) + 5
        )
        sample_home_corners = math.sqrt(max(0.1, home_stats["corners_for"]) * max(0.1, away_stats["corners_against"]))
        sample_away_corners = math.sqrt(max(0.1, away_stats["corners_for"]) * max(0.1, home_stats["corners_against"]))
        home_corners = (
            corner_reliability * sample_home_corners + (1 - corner_reliability) * baseline_corners
        ) * context["corner_home"]
        away_corners = (
            corner_reliability * sample_away_corners + (1 - corner_reliability) * baseline_corners
        ) * context["corner_away"]
        corner_total = (home_corners + away_corners) * context["corner_total"]
        scale = corner_total / max(0.01, home_corners + away_corners)
        home_corners *= scale
        away_corners *= scale

        baseline_cards = 1.6
        card_reliability = corner_reliability
        sample_home_cards = (home_stats["yellow_for"] + away_stats["yellow_against"]) / 2
        sample_away_cards = (away_stats["yellow_for"] + home_stats["yellow_against"]) / 2
        home_cards = (
            card_reliability * sample_home_cards + (1 - card_reliability) * baseline_cards
        ) * context["card_total"]
        away_cards = (
            card_reliability * sample_away_cards + (1 - card_reliability) * baseline_cards
        ) * context["card_total"]
        card_total = home_cards + away_cards

        penalty_probability = min(0.28, max(0.14, 0.18 + 0.035 * (total_mean - 2.4)))
        red_probability = min(0.13, max(0.06, 0.075 * context["card_total"]))
        full_matrix = score_matrix(home_mean, away_mean)
        simulation = monte_carlo(home_mean, away_mean, 20260625 + index)
        output["matches"][code] = {
            "fixture_id": fixture_id,
            "teams": {"home": fixture["teams"]["home"]["name"], "away": fixture["teams"]["away"]["name"]},
            "expected_goals": {"home": round(home_mean, 3), "away": round(away_mean, 3), "total": round(total_mean, 3)},
            "monte_carlo": simulation,
            "poisson_score_top10": full_matrix[:10],
            "half_time": {
                "expected_goals": {"home": round(ht_home, 3), "away": round(ht_away, 3)},
                "result": ht_result,
                "over_0_5": 1 - math.exp(-ht_total),
                "over_1_5": 1 - math.exp(-ht_total) * (1 + ht_total),
                "score_top5": ht_matrix[:5],
            },
            "corners": {
                "home": round(home_corners, 2), "away": round(away_corners, 2), "total": round(corner_total, 2),
                "over_8_5": 1 - sum(poisson(value, corner_total) for value in range(9)),
                "over_9_5": 1 - sum(poisson(value, corner_total) for value in range(10)),
            },
            "discipline": {
                "yellow_home": round(home_cards, 2), "yellow_away": round(away_cards, 2), "yellow_total": round(card_total, 2),
                "over_2_5": 1 - sum(poisson(value, card_total) for value in range(3)),
                "red_probability": red_probability,
                "penalty_probability": penalty_probability,
            },
        }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "summary": {
            code: {
                "xg": item["expected_goals"], "ht": item["half_time"]["result"],
                "corners": item["corners"], "discipline": item["discipline"],
                "mc": item["monte_carlo"]["probabilities"],
            }
            for code, item in output["matches"].items()
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
