#!/usr/bin/env python3
"""比赛天气上下文。

使用 Open-Meteo 免费接口，无需 API key。先用球场/城市静态坐标定位，
再抓比赛时间附近的温度、降雨、风速，并生成对进球/节奏的风险提示。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import requests


Coord = Tuple[float, float, str, str]


TEAM_COORDS: Dict[str, Coord] = {
    "冈山绿雉": (34.6618, 133.9350, "Okayama", "Asia/Tokyo"),
    "浦和红钻": (35.8617, 139.6455, "Saitama", "Asia/Tokyo"),
    "清水鼓动": (35.0159, 138.4896, "Shizuoka", "Asia/Tokyo"),
    "清水心跳": (35.0159, 138.4896, "Shizuoka", "Asia/Tokyo"),
    "横滨水手": (35.4437, 139.6380, "Yokohama", "Asia/Tokyo"),
    "韦斯特罗斯": (59.6099, 16.5448, "Vasteras", "Europe/Stockholm"),
    "瓦斯特拉斯": (59.6099, 16.5448, "Vasteras", "Europe/Stockholm"),
    "哥德堡": (57.7089, 11.9746, "Gothenburg", "Europe/Stockholm"),
    "赫根": (57.7089, 11.9746, "Gothenburg", "Europe/Stockholm"),
    "哈马比": (59.3293, 18.0686, "Stockholm", "Europe/Stockholm"),
    "代格福什": (59.2370, 14.4308, "Degerfors", "Europe/Stockholm"),
    "布鲁马波": (59.3293, 18.0686, "Stockholm", "Europe/Stockholm"),
    "AC奥卢": (65.0121, 25.4651, "Oulu", "Europe/Helsinki"),
    "雅罗": (63.6748, 22.7026, "Jakobstad", "Europe/Helsinki"),
    "德国": (52.5200, 13.4050, "Berlin", "Europe/Berlin"),
    "芬兰": (60.1699, 24.9384, "Helsinki", "Europe/Helsinki"),
    "美国": (38.9072, -77.0369, "Washington, DC", "America/New_York"),
    "塞内加尔": (14.7167, -17.4677, "Dakar", "Africa/Dakar"),
    "巴西": (-15.7939, -47.8828, "Brasilia", "America/Sao_Paulo"),
    "巴拿马": (8.9824, -79.5199, "Panama City", "America/Panama"),
    "瑞士": (46.9480, 7.4474, "Bern", "Europe/Zurich"),
    "约旦": (31.9539, 35.9106, "Amman", "Asia/Amman"),
    "捷克": (50.0755, 14.4378, "Prague", "Europe/Prague"),
    "科索沃": (42.6629, 21.1655, "Pristina", "Europe/Belgrade"),
    "哥伦比亚": (4.7110, -74.0721, "Bogota", "America/Bogota"),
    "哥斯达黎加": (9.9281, -84.0907, "San Jose", "America/Costa_Rica"),
    "哥斯大黎加": (9.9281, -84.0907, "San Jose", "America/Costa_Rica"),
    "挪威": (59.9139, 10.7522, "Oslo", "Europe/Oslo"),
    "瑞典": (59.3293, 18.0686, "Stockholm", "Europe/Stockholm"),
    "土耳其": (39.9334, 32.8597, "Ankara", "Europe/Istanbul"),
    "北马其顿": (41.9981, 21.4254, "Skopje", "Europe/Skopje"),
    "奥地利": (48.2082, 16.3738, "Vienna", "Europe/Vienna"),
    "突尼斯": (36.8065, 10.1815, "Tunis", "Africa/Tunis"),
    "加拿大": (45.4215, -75.6972, "Ottawa", "America/Toronto"),
    "乌兹别克斯坦": (41.2995, 69.2401, "Tashkent", "Asia/Tashkent"),
}


VENUE_COORDS: Dict[str, Coord] = {
    "Maracana": (-22.9122, -43.2302, "Maracana, Rio de Janeiro", "America/Sao_Paulo"),
    "Maracanã": (-22.9122, -43.2302, "Maracana, Rio de Janeiro", "America/Sao_Paulo"),
    "Estadio Jornalista Mario Filho": (-22.9122, -43.2302, "Maracana, Rio de Janeiro", "America/Sao_Paulo"),
    "MEWA Arena": (49.9842, 8.2242, "MEWA Arena, Mainz", "Europe/Berlin"),
    "Bank of America Stadium": (35.2258, -80.8528, "Bank of America Stadium, Charlotte", "America/New_York"),
}


MATCH_VENUE_OVERRIDES: Dict[Tuple[str, str], str] = {
    ("巴西", "巴拿马"): "Maracanã",
    ("Brazil", "Panama"): "Maracanã",
    ("德国", "芬兰"): "MEWA Arena",
    ("Germany", "Finland"): "MEWA Arena",
    ("美国", "塞内加尔"): "Bank of America Stadium",
    ("United States", "Senegal"): "Bank of America Stadium",
    ("USA", "Senegal"): "Bank of America Stadium",
}


@dataclass
class WeatherContext:
    location: str
    latitude: float
    longitude: float
    match_datetime: str
    local_match_datetime: Optional[str] = None
    timezone: Optional[str] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    weather_code: Optional[int] = None
    risk_note: Optional[str] = None
    source: str = "Open-Meteo"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WeatherContextCollector:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.session = requests.Session()

    def collect(
        self,
        home_team: str,
        match_dt: datetime,
        away_team: Optional[str] = None,
        venue: Optional[Dict[str, Any]] = None,
    ) -> Optional[WeatherContext]:
        coords = self._resolve_coords(home_team, away_team, venue)
        if not coords:
            return None
        lat, lon, location, timezone = coords
        local_dt = self._to_local_match_time(match_dt, timezone)
        context = WeatherContext(
            location=location,
            latitude=lat,
            longitude=lon,
            match_datetime=match_dt.isoformat(timespec="minutes"),
            local_match_datetime=local_dt.isoformat(timespec="minutes"),
            timezone=timezone,
        )
        try:
            response = self.session.get(
                self.BASE_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
                    "timezone": timezone,
                    "forecast_days": 3,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return context

        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        idx = self._nearest_hour_index(times, local_dt)
        if idx is None:
            return context

        context.temperature_c = self._value_at(hourly.get("temperature_2m"), idx)
        context.precipitation_mm = self._value_at(hourly.get("precipitation"), idx)
        context.wind_speed_kmh = self._value_at(hourly.get("wind_speed_10m"), idx)
        context.weather_code = self._value_at(hourly.get("weather_code"), idx)
        context.risk_note = self._risk_note(context)
        return context

    def _resolve_coords(
        self,
        home_team: str,
        away_team: Optional[str],
        venue: Optional[Dict[str, Any]],
    ) -> Optional[Coord]:
        venue_name = (venue or {}).get("name") or ""
        venue_city = (venue or {}).get("city") or ""
        for key in [venue_name, venue_city]:
            if key and key in VENUE_COORDS:
                return VENUE_COORDS[key]

        if venue_name or venue_city:
            geocoded = self._geocode(f"{venue_name} {venue_city}".strip())
            if geocoded:
                return geocoded

        override = MATCH_VENUE_OVERRIDES.get((home_team, away_team or ""))
        if override:
            return VENUE_COORDS.get(override)

        return TEAM_COORDS.get(home_team)

    def _geocode(self, query: str) -> Optional[Coord]:
        try:
            response = self.session.get(
                self.GEOCODING_URL,
                params={"name": query, "count": 1, "language": "en", "format": "json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return None

        results = data.get("results") or []
        if not results:
            return None
        item = results[0]
        lat = item.get("latitude")
        lon = item.get("longitude")
        timezone = item.get("timezone") or "UTC"
        if lat is None or lon is None:
            return None
        location = ", ".join(part for part in [item.get("name"), item.get("admin1"), item.get("country")] if part)
        return float(lat), float(lon), location or query, timezone

    @staticmethod
    def _to_local_match_time(match_dt: datetime, timezone: str) -> datetime:
        source_tz = ZoneInfo("Asia/Shanghai")
        if match_dt.tzinfo is None:
            aware = match_dt.replace(tzinfo=source_tz)
        else:
            aware = match_dt
        return aware.astimezone(ZoneInfo(timezone)).replace(tzinfo=None)

    @staticmethod
    def _nearest_hour_index(times, match_dt: datetime) -> Optional[int]:
        if not times:
            return None
        best_idx = None
        best_delta = None
        target = match_dt.replace(tzinfo=None)
        for idx, value in enumerate(times):
            try:
                current = datetime.fromisoformat(value)
            except ValueError:
                continue
            delta = abs((current - target).total_seconds())
            if best_delta is None or delta < best_delta:
                best_idx = idx
                best_delta = delta
        return best_idx

    @staticmethod
    def _value_at(values, idx):
        if not values or idx >= len(values):
            return None
        return values[idx]

    @staticmethod
    def _risk_note(context: WeatherContext) -> Optional[str]:
        notes = []
        if context.precipitation_mm is not None and context.precipitation_mm >= 2:
            notes.append("降雨可能降低传控质量并增加偶然性")
        if context.wind_speed_kmh is not None and context.wind_speed_kmh >= 25:
            notes.append("大风可能影响长传、传中和定位球落点")
        if context.temperature_c is not None and context.temperature_c >= 30:
            notes.append("高温可能降低比赛节奏和压迫强度")
        if context.temperature_c is not None and context.temperature_c <= 2:
            notes.append("低温可能增加身体对抗和失误")
        return "；".join(notes) if notes else "天气影响有限"


__all__ = ["WeatherContextCollector", "WeatherContext", "TEAM_COORDS", "VENUE_COORDS", "MATCH_VENUE_OVERRIDES"]
