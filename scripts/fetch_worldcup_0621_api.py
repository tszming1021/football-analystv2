from __future__ import annotations

import json
import os
from pathlib import Path

import requests


BASE_URL = "https://v3.football.api-sports.io"
OUT_DIR = Path("data/worldcup_20260622/api")
FIXTURE_IDS = [1489397, 1489395, 1489398, 1489396]
ENDPOINTS = {
    "predictions": "/predictions?fixture={fixture}",
    "injuries": "/injuries?fixture={fixture}",
    "lineups": "/fixtures/lineups?fixture={fixture}",
    "statistics": "/fixtures/statistics?fixture={fixture}",
    "odds": "/odds?fixture={fixture}",
}


def load_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_json(path: str, key: str) -> dict:
    response = requests.get(BASE_URL + path, headers={"x-apisports-key": key}, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    load_env(Path(".env"))
    api_key = os.environ["API_FOOTBALL_KEY"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fixtures": {}, "standings": {}}

    for fixture_id in FIXTURE_IDS:
        audit["fixtures"][str(fixture_id)] = {}
        for name, template in ENDPOINTS.items():
            payload = get_json(template.format(fixture=fixture_id), api_key)
            output = OUT_DIR / f"{fixture_id}_{name}.json"
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            audit["fixtures"][str(fixture_id)][name] = {
                "results": payload.get("results"),
                "errors": payload.get("errors"),
                "output": str(output),
            }

    standings = get_json("/standings?league=1&season=2026", api_key)
    standings_path = OUT_DIR / "standings_worldcup_2026.json"
    standings_path.write_text(json.dumps(standings, ensure_ascii=False, indent=2), encoding="utf-8")
    audit["standings"] = {
        "results": standings.get("results"),
        "errors": standings.get("errors"),
        "output": str(standings_path),
    }
    audit_path = OUT_DIR / "api_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
