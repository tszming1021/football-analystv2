from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests


OUT_DIR = Path("data/finland_20260623/weather")
LOCATIONS = {
    "lahti": ("周二201", 60.9837, 25.6507, "2026-06-23T18:00"),
    "kuopio": ("周二202", 62.8924, 27.6782, "2026-06-23T18:00"),
    "vaasa": ("周二203", 63.0951, 21.6165, "2026-06-23T18:00"),
    "pietarsaari": ("周二204", 63.6749, 22.7026, "2026-06-23T19:00"),
    "turku": ("周二205", 60.4422, 22.2917, "2026-06-23T19:00"),
    "mariehamn": ("周二206", 60.0973, 19.9348, "2026-06-23T20:00"),
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "locations": {}}
    for name, (code, lat, lon, kickoff) in LOCATIONS.items():
        params = {"latitude": lat, "longitude": lon,
                  "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
                  "timezone": "Europe/Helsinki", "start_date": "2026-06-23", "end_date": "2026-06-23"}
        payload = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30).json()
        output = OUT_DIR / f"{name}.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index = payload["hourly"]["time"].index(kickoff)
        audit["locations"][name] = {
            "code": code, "kickoff_local": kickoff,
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
