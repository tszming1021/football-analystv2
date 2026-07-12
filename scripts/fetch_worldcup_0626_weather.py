from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests


OUT_DIR = Path("data/worldcup_20260626/weather")
LOCATIONS = {
    "new_york_new_jersey": {"code": "周四055", "latitude": 40.8135, "longitude": -74.0745, "timezone": "America/New_York", "kickoff": "2026-06-25T16:00"},
    "philadelphia": {"code": "周四056", "latitude": 39.9008, "longitude": -75.1675, "timezone": "America/New_York", "kickoff": "2026-06-25T16:00"},
    "kansas_city": {"code": "周四057", "latitude": 39.0489, "longitude": -94.4839, "timezone": "America/Chicago", "kickoff": "2026-06-25T18:00"},
    "dallas": {"code": "周四058", "latitude": 32.7473, "longitude": -97.0945, "timezone": "America/Chicago", "kickoff": "2026-06-25T18:00"},
    "santa_clara": {"code": "周四059", "latitude": 37.4030, "longitude": -121.9700, "timezone": "America/Los_Angeles", "kickoff": "2026-06-25T19:00"},
    "inglewood": {"code": "周四060", "latitude": 33.9535, "longitude": -118.3392, "timezone": "America/Los_Angeles", "kickoff": "2026-06-25T19:00"},
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "locations": {}}
    for name, location in LOCATIONS.items():
        params = {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": location["timezone"], "start_date": "2026-06-25", "end_date": "2026-06-25",
        }
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        output = OUT_DIR / f"{name}.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index = payload["hourly"]["time"].index(location["kickoff"])
        audit["locations"][name] = {
            "code": location["code"], "kickoff_local": location["kickoff"],
            "temperature_c": payload["hourly"]["temperature_2m"][index],
            "humidity_pct": payload["hourly"]["relative_humidity_2m"][index],
            "precipitation_probability_pct": payload["hourly"]["precipitation_probability"][index],
            "weather_code": payload["hourly"]["weather_code"][index],
            "wind_kmh": payload["hourly"]["wind_speed_10m"][index], "output": str(output),
        }
    (OUT_DIR / "weather_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
