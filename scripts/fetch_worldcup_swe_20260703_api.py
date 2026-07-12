from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://v3.football.api-sports.io"
OUT_DIR = Path("data/worldcup_swe_20260703_four/api")
FIXTURES = {
    "周五086": 1565178,
    "周五087": 1565179,
    "周五088": 1567310,
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


def discover_sirius_mjallby(api_key: str) -> int:
    candidates = [
        "/fixtures?league=113&season=2026&date=2026-07-03",
        "/fixtures?league=113&season=2026&date=2026-07-04",
        "/fixtures?date=2026-07-03",
    ]
    for index, path in enumerate(candidates, 1):
        payload = get_json(path, api_key)
        discovery_path = OUT_DIR / f"discovery_sirius_mjallby_{index}.json"
        discovery_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        for item in payload.get("response", []):
            teams = item.get("teams", {})
            home = teams.get("home", {}).get("name", "").lower()
            away = teams.get("away", {}).get("name", "").lower()
            if "sirius" in home and ("mjallby" in away or "mjällby" in away):
                return int(item["fixture"]["id"])
    raise RuntimeError("Sirius vs Mjallby fixture not found")


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
        fixtures["周五201"] = discover_sirius_mjallby(api_key)
        audit["discovery"]["周五201"] = {"fixture_id": fixtures["周五201"], "source": "API-Football fixtures discovery"}
    except Exception as exc:
        audit["discovery"]["周五201"] = {"exception": repr(exc)}

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

    for label, path in {
        "worldcup": "/standings?league=1&season=2026",
        "allsvenskan": "/standings?league=113&season=2026",
    }.items():
        try:
            payload = get_json(path, api_key)
            output = OUT_DIR / f"standings_{label}_2026.json"
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            audit["standings"][label] = {"results": payload.get("results"), "errors": payload.get("errors"), "output": str(output)}
        except Exception as exc:
            audit["standings"][label] = {"exception": repr(exc)}

    audit_path = OUT_DIR / "api_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
