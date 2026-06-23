#!/usr/bin/env python3
"""免费/可选数据源补充层。

该模块只补“可验证来源”的字段，不用本地旧 CSV 伪造完整数据。
当前优先接入：
- ClubElo: 俱乐部强弱基准
- football-data.co.uk: 欧洲主流联赛历史赛果/赔率 CSV
- 可选 API key 源只做可解释的缺口提示
"""

import csv
import io
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from core.source_registry import DataSourceRegistry


TEAM_SOURCE_ALIASES = {
    "清水鼓动": {"clubelo": "Shimizu S-Pulse"},
    "清水心跳": {"clubelo": "Shimizu S-Pulse"},
    "横滨水手": {"clubelo": "Yokohama F. Marinos"},
    "AC奥卢": {"clubelo": "AC Oulu"},
    "雅罗": {"clubelo": "FF Jaro"},
    "哥德堡": {"clubelo": "IFK Goteborg"},
    "赫根": {"clubelo": "Hacken"},
    "哈马比": {"clubelo": "Hammarby"},
    "代格福什": {"clubelo": "Degerfors"},
    "布鲁马波": {"clubelo": "Brommapojkarna"},
    "德国": {"national": "Germany"},
    "芬兰": {"national": "Finland"},
    "美国": {"national": "United States"},
    "塞内加尔": {"national": "Senegal"},
    "巴西": {"national": "Brazil"},
    "巴拿马": {"national": "Panama"},
    "瑞士": {"national": "Switzerland"},
    "约旦": {"national": "Jordan"},
    "捷克": {"national": "Czechia"},
    "科索沃": {"national": "Kosovo"},
    "哥伦比亚": {"national": "Colombia"},
    "哥斯达黎加": {"national": "Costa Rica"},
    "哥斯大黎加": {"national": "Costa Rica"},
    "挪威": {"national": "Norway"},
    "瑞典": {"national": "Sweden"},
    "土耳其": {"national": "Turkey"},
    "北马其顿": {"national": "North Macedonia"},
    "奥地利": {"national": "Austria"},
    "突尼斯": {"national": "Tunisia"},
    "加拿大": {"national": "Canada"},
    "乌兹别克斯坦": {"national": "Uzbekistan"},
}


FREE_EVENT_ALIASES = {
    "Czechia": "Czech Republic",
    "United States": "USA",
}


THE_ODDS_API_DEFAULT_SPORTS = [
    "soccer_intl_friendly",
    "soccer_fifa_world_cup",
    "soccer_japan_j_league",
    "soccer_sweden_allsvenskan",
    "soccer_finland_veikkausliiga",
    "soccer_brazil_campeonato",
]


FOOTBALL_DATA_LEAGUES = {
    "英超": "E0",
    "英冠": "E1",
    "西甲": "SP1",
    "德甲": "D1",
    "意甲": "I1",
    "法甲": "F1",
    "荷甲": "N1",
    "葡超": "P1",
    "土超": "T1",
    "比甲": "B1",
    "苏超": "SC0",
}


@dataclass
class TeamSupplementalData:
    team_name: str
    clubelo_name: Optional[str] = None
    clubelo_rating: Optional[float] = None
    clubelo_rank: Optional[int] = None
    clubelo_country: Optional[str] = None
    fifa_rank: Optional[int] = None
    fifa_points: Optional[float] = None
    market_value_eur: Optional[float] = None
    source_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalLeagueData:
    league: str
    season_code: str
    matches_loaded: int = 0
    home_matches: int = 0
    away_matches: int = 0
    avg_total_goals: Optional[float] = None
    avg_home_goals: Optional[float] = None
    avg_away_goals: Optional[float] = None
    bookmaker_columns: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchSupplementalData:
    home: TeamSupplementalData
    away: TeamSupplementalData
    historical_league: Optional[HistoricalLeagueData] = None
    external_sources: Dict[str, Any] = field(default_factory=dict)
    source_registry: List[Dict[str, Any]] = field(default_factory=list)
    missing_field_suggestions: Dict[str, List[str]] = field(default_factory=dict)
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "home": self.home.to_dict(),
            "away": self.away.to_dict(),
            "historical_league": self.historical_league.to_dict() if self.historical_league else None,
            "external_sources": self.external_sources,
            "source_registry": self.source_registry,
            "missing_field_suggestions": self.missing_field_suggestions,
            "data_sources": self.data_sources,
            "warnings": self.warnings,
        }


class SupplementalDataCollector:
    """Collect extra data from free or optional external sources."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: int = 10):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.clubelo_base = "http://api.clubelo.com"

    def collect(
        self,
        home_name: str,
        away_name: str,
        league: Optional[str] = None,
        match_date: Optional[str] = None,
    ) -> MatchSupplementalData:
        report = MatchSupplementalData(
            home=TeamSupplementalData(team_name=home_name),
            away=TeamSupplementalData(team_name=away_name),
            source_registry=DataSourceRegistry.all(),
            missing_field_suggestions=self._missing_field_suggestions(),
        )

        for side in [report.home, report.away]:
            self._collect_clubelo(side, report)
            self._mark_optional_national_sources(side, report)

        if league:
            report.historical_league = self._collect_football_data_history(
                league=league,
                home_name=home_name,
                away_name=away_name,
                match_date=match_date,
            )
            if report.historical_league and report.historical_league.matches_loaded:
                report.data_sources.append("football-data.co.uk")
            elif report.historical_league and report.historical_league.warning:
                report.warnings.append(report.historical_league.warning)

        self._collect_free_event_data(report, home_name, away_name, match_date)
        self._collect_optional_odds_data(report, home_name, away_name, league, match_date)

        report.data_sources = list(dict.fromkeys(report.data_sources))
        report.warnings = list(dict.fromkeys(report.warnings + report.home.warnings + report.away.warnings))
        return report

    def _collect_clubelo(self, side: TeamSupplementalData, report: MatchSupplementalData):
        clubelo_name = self._alias(side.team_name, "clubelo")
        if not clubelo_name:
            side.source_notes.append("ClubElo 未配置该队别名或该队可能是国家队/低覆盖球队")
            return

        url = f"{self.clubelo_base}/{quote(clubelo_name)}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                side.warnings.append(f"ClubElo HTTP {response.status_code}")
                return
            rows = list(csv.DictReader(io.StringIO(response.text)))
        except requests.RequestException as exc:
            side.warnings.append(f"ClubElo 请求失败: {exc}")
            return
        except csv.Error as exc:
            side.warnings.append(f"ClubElo CSV 解析失败: {exc}")
            return

        latest = self._latest_clubelo_row(rows)
        if not latest:
            side.source_notes.append("ClubElo 未返回有效记录")
            return

        side.clubelo_name = latest.get("Club") or clubelo_name
        side.clubelo_country = latest.get("Country") or None
        side.clubelo_rating = self._safe_float(latest.get("Elo"))
        side.clubelo_rank = self._safe_int(latest.get("Rank"))
        side.source_notes.append("ClubElo 俱乐部强度基准")
        if "ClubElo" not in report.data_sources:
            report.data_sources.append("ClubElo")

    def _mark_optional_national_sources(self, side: TeamSupplementalData, report: MatchSupplementalData):
        national_name = self._alias(side.team_name, "national")
        if not national_name:
            return
        if os.getenv("FOOTBALLDATA_IO_KEY"):
            side.source_notes.append("已检测到 FOOTBALLDATA_IO_KEY，可扩展获取 FIFA 排名")
        else:
            side.source_notes.append("国家队 FIFA 排名建议接入 FootballData.io，需要 FOOTBALLDATA_IO_KEY")
            report.warnings.append(f"{side.team_name} FIFA排名缺失：需要 FOOTBALLDATA_IO_KEY 或联网搜索补齐")

    def _collect_football_data_history(
        self,
        league: str,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
    ) -> Optional[HistoricalLeagueData]:
        league_code = self._football_data_league_code(league)
        if not league_code:
            return HistoricalLeagueData(
                league=league,
                season_code="",
                warning=f"football-data.co.uk 暂无 {league} 对应联赛代码",
            )

        season_code = self._season_code(match_date)
        url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"
        history = HistoricalLeagueData(league=league, season_code=season_code, source_url=url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                history.warning = f"football-data.co.uk HTTP {response.status_code}: {league}/{season_code}"
                return history
            text = response.text.lstrip("\ufeff")
            rows = list(csv.DictReader(io.StringIO(text)))
        except requests.RequestException as exc:
            history.warning = f"football-data.co.uk 请求失败: {exc}"
            return history
        except csv.Error as exc:
            history.warning = f"football-data.co.uk CSV 解析失败: {exc}"
            return history

        played_rows = [
            row for row in rows
            if self._safe_int(row.get("FTHG")) is not None and self._safe_int(row.get("FTAG")) is not None
        ]
        history.matches_loaded = len(played_rows)
        if not played_rows:
            history.warning = "football-data.co.uk 尚未返回已完赛样本"
            return history

        home_terms = self._name_terms(home_name)
        away_terms = self._name_terms(away_name)
        history.home_matches = sum(1 for row in played_rows if self._row_matches_team(row, home_terms))
        history.away_matches = sum(1 for row in played_rows if self._row_matches_team(row, away_terms))
        total_home = sum(self._safe_int(row.get("FTHG")) or 0 for row in played_rows)
        total_away = sum(self._safe_int(row.get("FTAG")) or 0 for row in played_rows)
        history.avg_home_goals = round(total_home / len(played_rows), 3)
        history.avg_away_goals = round(total_away / len(played_rows), 3)
        history.avg_total_goals = round((total_home + total_away) / len(played_rows), 3)
        history.bookmaker_columns = [
            key for key in (rows[0].keys() if rows else [])
            if re.match(r"^(B365|BW|IW|PS|VC|WH|CL|BF)", key or "")
        ][:24]
        return history

    def _collect_free_event_data(
        self,
        report: MatchSupplementalData,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
    ):
        event = self._collect_thesportsdb_event(home_name, away_name, match_date)
        if event:
            report.external_sources["thesportsdb"] = event
            report.data_sources.append("TheSportsDB")

    def _collect_optional_odds_data(
        self,
        report: MatchSupplementalData,
        home_name: str,
        away_name: str,
        league: Optional[str],
        match_date: Optional[str],
    ):
        odds_api_io_key = self._env_value("ODDS_API_IO_KEY")
        if odds_api_io_key:
            payload = self._collect_odds_api_io(odds_api_io_key, home_name, away_name, league, match_date)
            if payload:
                report.external_sources["odds_api_io"] = payload
                if payload.get("available"):
                    report.data_sources.append("Odds-API.io")

        the_odds_api_key = self._env_value("THE_ODDS_API_KEY")
        if the_odds_api_key:
            payload = self._collect_the_odds_api(the_odds_api_key, home_name, away_name, match_date)
            if payload:
                report.external_sources["the_odds_api"] = payload
                if payload.get("available"):
                    report.data_sources.append("The Odds API")

    def _collect_thesportsdb_event(
        self,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        key = self._env_value("THESPORTSDB_KEY") or "123"
        home = self._event_alias(home_name)
        away = self._event_alias(away_name)
        queries = [f"{home}_vs_{away}", f"{away}_vs_{home}"]
        for query in queries:
            url = f"https://www.thesportsdb.com/api/v1/json/{quote(key)}/searchevents.php"
            try:
                response = self.session.get(url, params={"e": query}, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                events = (response.json() or {}).get("event") or []
            except (requests.RequestException, ValueError):
                continue
            event = self._pick_event(events, home, away, match_date)
            if event:
                return {
                    "event_id": event.get("idEvent"),
                    "event": event.get("strEvent"),
                    "league": event.get("strLeague"),
                    "season": event.get("strSeason"),
                    "date": event.get("dateEvent"),
                    "time": event.get("strTime"),
                    "venue": event.get("strVenue"),
                    "city": event.get("strCity"),
                    "country": event.get("strCountry"),
                    "home_score": self._safe_int(event.get("intHomeScore")),
                    "away_score": self._safe_int(event.get("intAwayScore")),
                    "status": event.get("strStatus"),
                    "source_url": "https://www.thesportsdb.com/api.php",
                }
        return None

    def _collect_odds_api_io(
        self,
        api_key: str,
        home_name: str,
        away_name: str,
        league: Optional[str],
        match_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        home = self._event_alias(home_name)
        away = self._event_alias(away_name)
        base = "https://api.odds-api.io/v3"
        params = {
            "apiKey": api_key,
            "sport": "football",
            "search": f"{home} {away}",
        }
        if match_date:
            params["date"] = match_date[:10]
        if league:
            params["league"] = league
        try:
            response = self.session.get(f"{base}/events", params=params, timeout=self.timeout)
            if response.status_code != 200:
                return {"available": False, "warning": f"events HTTP {response.status_code}"}
            data = response.json() or {}
        except (requests.RequestException, ValueError) as exc:
            return {"available": False, "warning": f"events 请求失败: {exc}"}

        events = self._payload_items(data, "events")
        event = self._pick_generic_event(events, home, away, match_date)
        if not event:
            return {"available": False, "events_checked": len(events), "warning": "未匹配到事件"}

        event_id = event.get("id") or event.get("eventId") or event.get("event_id")
        odds_summary = None
        if event_id:
            odds_summary = self._collect_odds_api_io_odds(base, api_key, str(event_id))

        return {
            "available": True,
            "event": self._compact_event(event),
            "odds": odds_summary,
            "source_url": "https://docs.odds-api.io/api-reference/odds/get-event-odds",
        }

    def _collect_odds_api_io_odds(self, base: str, api_key: str, event_id: str) -> Optional[Dict[str, Any]]:
        bookmakers = self._env_value("ODDS_API_IO_BOOKMAKERS") or "1xbet"
        params = {
            "apiKey": api_key,
            "eventId": event_id,
            "bookmakers": bookmakers,
        }
        try:
            response = self.session.get(f"{base}/odds", params=params, timeout=self.timeout)
            if response.status_code != 200:
                return {"warning": f"odds HTTP {response.status_code}"}
            data = response.json() or {}
        except (requests.RequestException, ValueError) as exc:
            return {"warning": f"odds 请求失败: {exc}"}

        items = self._payload_items(data, "odds")
        return {
            "bookmakers_requested": bookmakers,
            "markets": len(items),
            "sample": items[:3],
        }

    def _collect_the_odds_api(
        self,
        api_key: str,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        home = self._event_alias(home_name)
        away = self._event_alias(away_name)
        sport_keys = self._the_odds_api_sports()
        for sport_key in sport_keys:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                "apiKey": api_key,
                "regions": os.getenv("THE_ODDS_API_REGIONS", "eu,us"),
                "markets": os.getenv("THE_ODDS_API_MARKETS", "h2h,spreads,totals"),
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                events = response.json() or []
            except (requests.RequestException, ValueError):
                continue
            event = self._pick_generic_event(events, home, away, match_date)
            if event:
                return {
                    "available": True,
                    "sport_key": sport_key,
                    "event": self._compact_event(event),
                    "bookmakers": len(event.get("bookmakers") or []),
                    "markets": self._summarize_the_odds_api_markets(event),
                    "source_url": "https://the-odds-api.com/liveapi/guides/v4/",
                }
        return {"available": False, "sports_checked": sport_keys, "warning": "未匹配到事件或额度不足"}

    @staticmethod
    def _the_odds_api_sports() -> List[str]:
        raw = os.getenv("THE_ODDS_API_SPORTS", "")
        if raw.strip():
            return [item.strip() for item in raw.split(",") if item.strip()]
        return THE_ODDS_API_DEFAULT_SPORTS

    @staticmethod
    def _latest_clubelo_row(rows: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        valid = [row for row in rows if row.get("Elo")]
        if not valid:
            return None
        valid.sort(key=lambda row: row.get("To") or row.get("From") or "", reverse=True)
        return valid[0]

    @staticmethod
    def _alias(team_name: str, source: str) -> Optional[str]:
        return (TEAM_SOURCE_ALIASES.get(team_name) or {}).get(source)

    @staticmethod
    def _event_alias(team_name: str) -> str:
        alias = (TEAM_SOURCE_ALIASES.get(team_name) or {}).get("national")
        value = alias or team_name
        return FREE_EVENT_ALIASES.get(value, value)

    @staticmethod
    def _env_value(key: str) -> Optional[str]:
        value = os.getenv(key)
        if not value or value.startswith("optional_") or value.startswith("your_"):
            return None
        return value

    @staticmethod
    def _payload_items(data: Any, preferred_key: str) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []
        for key in [preferred_key, "data", "response", "results"]:
            items = data.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    @staticmethod
    def _pick_event(
        events: List[Dict[str, Any]],
        home: str,
        away: str,
        match_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        wanted_date = match_date[:10] if match_date else None
        candidates = []
        home_norm = SupplementalDataCollector._normalize_name(home)
        away_norm = SupplementalDataCollector._normalize_name(away)
        for event in events:
            text = SupplementalDataCollector._normalize_name(
                " ".join(str(event.get(key) or "") for key in ["strEvent", "strHomeTeam", "strAwayTeam"])
            )
            if home_norm in text and away_norm in text:
                if wanted_date and event.get("dateEvent") and event.get("dateEvent") != wanted_date:
                    continue
                candidates.append(event)
        return candidates[0] if candidates else (events[0] if events and not wanted_date else None)

    @staticmethod
    def _pick_generic_event(
        events: List[Dict[str, Any]],
        home: str,
        away: str,
        match_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        wanted_date = match_date[:10] if match_date else None
        home_norm = SupplementalDataCollector._normalize_name(home)
        away_norm = SupplementalDataCollector._normalize_name(away)
        for event in events:
            text = SupplementalDataCollector._normalize_name(
                " ".join(
                    str(event.get(key) or "")
                    for key in ["name", "event", "home_team", "away_team", "homeTeam", "awayTeam", "participants"]
                )
            )
            if home_norm not in text or away_norm not in text:
                continue
            commence = str(event.get("commence_time") or event.get("startTime") or event.get("date") or "")
            if wanted_date and commence[:10] and commence[:10] != wanted_date:
                continue
            return event
        return None

    @staticmethod
    def _compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "id", "eventId", "event_id", "name", "event", "home_team", "away_team",
            "homeTeam", "awayTeam", "commence_time", "startTime", "date", "league", "sport_key",
        ]
        return {key: event.get(key) for key in keys if event.get(key) is not None}

    @staticmethod
    def _summarize_the_odds_api_markets(event: Dict[str, Any]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for bookmaker in event.get("bookmakers") or []:
            for market in bookmaker.get("markets") or []:
                key = market.get("key")
                if key:
                    counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _football_data_league_code(league: str) -> Optional[str]:
        for name, code in FOOTBALL_DATA_LEAGUES.items():
            if name in league:
                return code
        return None

    @staticmethod
    def _season_code(match_date: Optional[str]) -> str:
        anchor = datetime.now()
        if match_date:
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M"):
                try:
                    anchor = datetime.strptime(match_date[:16], fmt)
                    break
                except ValueError:
                    continue
        start_year = anchor.year if anchor.month >= 7 else anchor.year - 1
        return f"{str(start_year)[-2:]}{str(start_year + 1)[-2:]}"

    @staticmethod
    def _name_terms(name: str) -> List[str]:
        raw = [name]
        alias = TEAM_SOURCE_ALIASES.get(name) or {}
        raw.extend(value for value in alias.values() if value)
        return [SupplementalDataCollector._normalize_name(item) for item in raw]

    @staticmethod
    def _row_matches_team(row: Dict[str, str], terms: List[str]) -> bool:
        home = SupplementalDataCollector._normalize_name(row.get("HomeTeam") or "")
        away = SupplementalDataCollector._normalize_name(row.get("AwayTeam") or "")
        return any(term and (term in home or term in away or home in term or away in term) for term in terms)

    @staticmethod
    def _normalize_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (value or "").lower())

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value in (None, ""):
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _missing_field_suggestions() -> Dict[str, List[str]]:
        return {
            "odds": ["500彩票网", "football-data.co.uk(历史)", "AnySport(可选API)"],
            "injuries": ["API-Football", "Sportmonks", "联网搜索"],
            "lineups": ["API-Football", "Sportmonks", "AnySport", "联网搜索"],
            "ranking": ["API-Football standings", "ClubElo", "FootballData.io FIFA Rankings"],
            "technical_stats": ["API-Football", "FBref", "Sportmonks"],
            "market_value": ["Transfermarkt页面/授权数据源"],
            "weather": ["Open-Meteo"],
        }


__all__ = [
    "SupplementalDataCollector",
    "TeamSupplementalData",
    "HistoricalLeagueData",
    "MatchSupplementalData",
    "TEAM_SOURCE_ALIASES",
    "FOOTBALL_DATA_LEAGUES",
]
