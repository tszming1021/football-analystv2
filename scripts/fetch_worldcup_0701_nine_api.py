from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://v3.football.api-sports.io"
OUT_DIR = Path("data/worldcup_20260701_nine/api")
FIXTURES = {
    "周三080": 1567307,
    "周三081": 1567308,
    "周三082": 1562586,
    "周四083": 1567311,
    "周四084": 1567309,
    "周四085": 1567312,
    "周五086": 1565178,
    "周五087": 1565179,
}
ENDPOINTS = {
    "fixture": "/fixtures?id={fixture}",
    "predictions": "/predictions?fixture={fixture}",
    "injuries": "/injuries?fixture={fixture}",
    "lineups": "/fixtures/lineups?fixture={fixture}",
    "statistics": "/fixtures/statistics?fixture={fixture}",
    "odds": "/odds?fixture={fixture}",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_json(path: str, key: str) -> dict:
    response = requests.get(BASE_URL + path, headers={"x-apisports-key": key}, timeout=30)
    response.raise_for_status()
    return response.json()


def team_names(item: dict) -> tuple[str, str]:
    teams = item.get("teams", {})
    return teams.get("home", {}).get("name", ""), teams.get("away", {}).get("name", "")


def find_colombia_ghana_fixture(api_key: str) -> int:
    payload = get_json("/fixtures?league=1&season=2026&date=2026-07-04", api_key)
    discovery_path = OUT_DIR / "fixtures_2026-07-04_discovery.json"
    discovery_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in payload.get("response", []):
        home, away = team_names(item)
        joined = f"{home} {away}".lower()
        if "colombia" in joined and "ghana" in joined:
            return int(item["fixture"]["id"])
    raise RuntimeError("Colombia vs Ghana fixture not found in 2026-07-04 World Cup fixtures")


def main() -> None:
    load_env(Path(".env"))
    api_key = os.environ["API_FOOTBALL_KEY"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fixtures = dict(FIXTURES)
    audit = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fixtures": {},
        "standings": {},
        "discovery": {},
    }

    try:
        fixtures["周五088"] = find_colombia_ghana_fixture(api_key)
        audit["discovery"]["周五088"] = {
            "fixture_id": fixtures["周五088"],
            "source": "fixtures?league=1&season=2026&date=2026-07-04",
        }
    except Exception as exc:
        audit["discovery"]["周五088"] = {"exception": repr(exc)}

    for code, fixture_id in fixtures.items():
        audit["fixtures"][code] = {"fixture_id": fixture_id, "endpoints": {}}
        for name, template in ENDPOINTS.items():
            try:
                payload = get_json(template.format(fixture=fixture_id), api_key)
                output = OUT_DIR / f"{fixture_id}_{name}.json"
                output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                audit["fixtures"][code]["endpoints"][name] = {
                    "results": payload.get("results"),
                    "errors": payload.get("errors"),
                    "output": str(output),
                }
            except Exception as exc:
                audit["fixtures"][code]["endpoints"][name] = {"exception": repr(exc)}

    try:
        standings = get_json("/standings?league=1&season=2026", api_key)
        standings_path = OUT_DIR / "standings_worldcup_2026.json"
        standings_path.write_text(json.dumps(standings, ensure_ascii=False, indent=2), encoding="utf-8")
        audit["standings"] = {
            "results": standings.get("results"),
            "errors": standings.get("errors"),
            "output": str(standings_path),
        }
    except Exception as exc:
        audit["standings"] = {"exception": repr(exc)}

    audit_path = OUT_DIR / "api_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
