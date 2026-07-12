from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests


OUT_DIR = Path("data/worldcup_20260625/weather")
LOCATIONS = {
    "vancouver": {"code": "周三049", "latitude": 49.2768, "longitude": -123.1119, "timezone": "America/Vancouver", "kickoff": "2026-06-24T12:00"},
    "seattle": {"code": "周三050", "latitude": 47.5952, "longitude": -122.3316, "timezone": "America/Los_Angeles", "kickoff": "2026-06-24T12:00"},
    "miami": {"code": "周三051", "latitude": 25.9580, "longitude": -80.2389, "timezone": "America/New_York", "kickoff": "2026-06-24T18:00"},
    "atlanta": {"code": "周三052", "latitude": 33.7554, "longitude": -84.4008, "timezone": "America/New_York", "kickoff": "2026-06-24T18:00"},
    "monterrey": {"code": "周三053", "latitude": 25.6695, "longitude": -100.2446, "timezone": "America/Monterrey", "kickoff": "2026-06-24T19:00"},
    "mexico_city": {"code": "周三054", "latitude": 19.3029, "longitude": -99.1505, "timezone": "America/Mexico_City", "kickoff": "2026-06-24T19:00"},
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "locations": {}}
    for name, location in LOCATIONS.items():
        params = {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": location["timezone"], "start_date": "2026-06-24", "end_date": "2026-06-24",
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

