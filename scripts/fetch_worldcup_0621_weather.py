from __future__ import annotations

import json
from pathlib import Path

import requests


OUT_DIR = Path("data/worldcup_20260622/weather")
LOCATIONS = {
    "atlanta": {"latitude": 33.755, "longitude": -84.400, "timezone": "America/New_York", "kickoff": "2026-06-21T12:00"},
    "los_angeles": {"latitude": 33.953, "longitude": -118.339, "timezone": "America/Los_Angeles", "kickoff": "2026-06-21T12:00"},
    "miami": {"latitude": 25.958, "longitude": -80.239, "timezone": "America/New_York", "kickoff": "2026-06-21T18:00"},
    "vancouver": {"latitude": 49.277, "longitude": -123.112, "timezone": "America/Vancouver", "kickoff": "2026-06-21T18:00"},
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {}
    for name, location in LOCATIONS.items():
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": location["timezone"],
            "start_date": "2026-06-21",
            "end_date": "2026-06-21",
        }
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        output = OUT_DIR / f"{name}.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index = payload["hourly"]["time"].index(location["kickoff"])
        audit[name] = {
            "kickoff_local": location["kickoff"],
            "temperature_c": payload["hourly"]["temperature_2m"][index],
            "humidity_pct": payload["hourly"]["relative_humidity_2m"][index],
            "precipitation_probability_pct": payload["hourly"]["precipitation_probability"][index],
            "weather_code": payload["hourly"]["weather_code"][index],
            "wind_kmh": payload["hourly"]["wind_speed_10m"][index],
            "output": str(output),
        }
    audit_path = OUT_DIR / "weather_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
