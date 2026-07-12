from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://v3.football.api-sports.io"
OUT_DIR = Path("data/nordic_20260704/api")
FIXTURES = {
    "周六204": 1495723,
    "周六205": 1494198,
    "周六206": 1494194,
    "周六207": 1495725,
    "周六208": 1495724,
    "周六209": 1495726,
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
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def get_json(path: str, key: str) -> dict:
    response = requests.get(BASE_URL + path, headers={"x-apisports-key": key}, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    load_env(Path(".env"))
    key = os.environ["API_FOOTBALL_KEY"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "fixtures": {}, "standings": {}}
    for code, fixture in FIXTURES.items():
        audit["fixtures"][code] = {"fixture_id": fixture, "endpoints": {}}
        for name, template in ENDPOINTS.items():
            try:
                payload = get_json(template.format(fixture=fixture), key)
                output = OUT_DIR / f"{fixture}_{name}.json"
                output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                audit["fixtures"][code]["endpoints"][name] = {
                    "results": payload.get("results"),
                    "errors": payload.get("errors"),
                    "output": str(output),
                }
            except Exception as exc:
                audit["fixtures"][code]["endpoints"][name] = {"exception": repr(exc)}
    for league_id, label in [(244, "veikkausliiga"), (113, "allsvenskan")]:
        try:
            payload = get_json(f"/standings?league={league_id}&season=2026", key)
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
