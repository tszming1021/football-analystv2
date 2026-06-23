from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests
import scripts.fetch_worldcup_0622_weather as base


base.OUT_DIR = Path("data/worldcup_20260624/weather")
base.LOCATIONS = {
    "houston": {"code": "周二045", "latitude": 29.6847, "longitude": -95.4107, "timezone": "America/Chicago", "kickoff": "2026-06-23T12:00"},
    "foxborough": {"code": "周二046", "latitude": 42.0909, "longitude": -71.2643, "timezone": "America/New_York", "kickoff": "2026-06-23T16:00"},
    "toronto": {"code": "周二047", "latitude": 43.6332, "longitude": -79.4186, "timezone": "America/Toronto", "kickoff": "2026-06-23T19:00"},
    "guadalajara": {"code": "周二048", "latitude": 20.6818, "longitude": -103.4626, "timezone": "America/Mexico_City", "kickoff": "2026-06-23T20:00"},
}


def main() -> None:
    base.OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "locations": {}}
    for name, location in base.LOCATIONS.items():
        params = {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": location["timezone"], "start_date": "2026-06-23", "end_date": "2026-06-23",
        }
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        output = base.OUT_DIR / f"{name}.json"
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
    (base.OUT_DIR / "weather_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
