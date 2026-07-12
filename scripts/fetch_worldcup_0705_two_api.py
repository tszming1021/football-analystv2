from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://v3.football.api-sports.io"
OUT_DIR = Path("data/worldcup_20260705_two/api")
FIXTURES = {
    "周六089": 1567824,
    "周六090": 1569870,
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


def main() -> None:
    load_env(Path(".env"))
    key = os.environ["API_FOOTBALL_KEY"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fixtures": {},
        "standings": {},
    }
    for code, fixture_id in FIXTURES.items():
        audit["fixtures"][code] = {"fixture_id": fixture_id, "endpoints": {}}
        for name, template in ENDPOINTS.items():
            try:
                payload = get_json(template.format(fixture=fixture_id), key)
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
        payload = get_json("/standings?league=1&season=2026", key)
        output = OUT_DIR / "standings_worldcup_2026.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        audit["standings"]["worldcup"] = {"results": payload.get("results"), "errors": payload.get("errors"), "output": str(output)}
    except Exception as exc:
        audit["standings"]["worldcup"] = {"exception": repr(exc)}

    audit_path = OUT_DIR / "api_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
