#!/usr/bin/env python3
"""赛事情报层。

组合 API-Football 和联网搜索，补充中国竞彩盘口之外的赛前信息：
- 联赛排名、近期赛程、休息天数
- 伤停、停赛、预计/正式首发
- 基于近况和公开信息的战术/风格标签
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.supplemental_data import SupplementalDataCollector


ApiGetter = Callable[[str, Dict[str, Any]], Tuple[Optional[Dict[str, Any]], Optional[str]]]


TEAM_API_ALIASES = {
    "冈山绿雉": ["Fagiano Okayama", "Okayama"],
    "浦和红钻": ["Urawa Red Diamonds", "Urawa"],
    "清水鼓动": ["Shimizu S-Pulse", "Shimizu"],
    "清水心跳": ["Shimizu S-Pulse", "Shimizu"],
    "横滨水手": ["Yokohama F. Marinos", "Yokohama Marinos"],
    "韦斯特罗斯": ["Vasteras SK", "Vasteras"],
    "瓦斯特拉斯": ["Vasteras SK", "Vasteras"],
    "哥德堡": ["IFK Goteborg", "Goteborg"],
    "赫根": ["BK Hacken", "Hacken"],
    "哈马比": ["Hammarby"],
    "代格福什": ["Degerfors IF", "Degerfors"],
    "布鲁马波": ["IF Brommapojkarna", "Brommapojkarna"],
    "AC奥卢": ["AC Oulu", "Oulu"],
    "雅罗": ["FF Jaro", "Jaro"],
    "德国": ["Germany"],
    "芬兰": ["Finland"],
    "美国": ["United States", "USA"],
    "塞内加尔": ["Senegal"],
    "巴西": ["Brazil"],
    "巴拿马": ["Panama"],
    "瑞士": ["Switzerland"],
    "约旦": ["Jordan"],
    "捷克": ["Czechia", "Czech Republic"],
    "科索沃": ["Kosovo"],
    "哥伦比亚": ["Colombia"],
    "哥斯达黎加": ["Costa Rica"],
    "哥斯大黎加": ["Costa Rica"],
    "挪威": ["Norway"],
    "瑞典": ["Sweden"],
    "土耳其": ["Turkey"],
    "北马其顿": ["North Macedonia"],
    "奥地利": ["Austria"],
    "突尼斯": ["Tunisia"],
    "加拿大": ["Canada"],
    "乌兹别克斯坦": ["Uzbekistan"],
}


@dataclass
class TeamIntelligence:
    team_name: str
    api_team_id: Optional[int] = None
    api_team_name: Optional[str] = None
    league_rank: Optional[int] = None
    league_points: Optional[int] = None
    league_form: Optional[str] = None
    recent_fixtures: List[Dict[str, Any]] = field(default_factory=list)
    rest_days: Optional[int] = None
    rest_days_source: Optional[str] = None
    injuries: List[Dict[str, Any]] = field(default_factory=list)
    injury_status: str = "unknown"
    injury_sources: List[str] = field(default_factory=list)
    lineup: List[Dict[str, Any]] = field(default_factory=list)
    lineup_status: str = "unknown"
    lineup_sources: List[str] = field(default_factory=list)
    tactical_tags: List[str] = field(default_factory=list)
    clubelo_rating: Optional[float] = None
    clubelo_rank: Optional[int] = None
    fifa_rank: Optional[int] = None
    market_value_eur: Optional[float] = None
    supplemental_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MatchIntelligenceReport:
    home: TeamIntelligence
    away: TeamIntelligence
    api_fixture_id: Optional[int] = None
    api_fixture_date: Optional[str] = None
    api_league_id: Optional[int] = None
    api_season: Optional[int] = None
    fixture_status: Optional[str] = None
    schedule_density_note: Optional[str] = None
    tactical_notes: List[str] = field(default_factory=list)
    supplemental_data: Optional[Dict[str, Any]] = None
    web_evidence: List[Dict[str, str]] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    intelligence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MatchIntelligenceCollector:
    """补充赛事情报，不覆盖 500彩票网的竞彩赔率。"""

    def __init__(self, api_get: ApiGetter, supplemental_collector: Optional[SupplementalDataCollector] = None):
        self.api_get = api_get
        self.supplemental_collector = supplemental_collector or SupplementalDataCollector()

    def collect(
        self,
        home_name: str,
        away_name: str,
        match_date: Optional[str] = None,
        league_name: Optional[str] = None,
        home_stats: Optional[Any] = None,
        away_stats: Optional[Any] = None,
    ) -> MatchIntelligenceReport:
        report = MatchIntelligenceReport(
            home=TeamIntelligence(team_name=home_name),
            away=TeamIntelligence(team_name=away_name),
        )

        home_team = self._search_team(home_name, report)
        away_team = self._search_team(away_name, report)

        if home_team:
            self._apply_team_identity(report.home, home_team)
        else:
            report.home.warnings.append("API-Football 未匹配到主队")
        if away_team:
            self._apply_team_identity(report.away, away_team)
        else:
            report.away.warnings.append("API-Football 未匹配到客队")

        fixture = None
        if home_team and away_team:
            fixture = self._find_fixture(home_team["id"], away_team["id"], match_date, report)
            if fixture:
                fixture_info = fixture.get("fixture", {})
                league = fixture.get("league", {})
                report.api_fixture_id = fixture_info.get("id")
                report.api_fixture_date = fixture_info.get("date")
                report.fixture_status = (fixture_info.get("status") or {}).get("long")
                report.api_league_id = league.get("id")
                report.api_season = league.get("season")
                report.data_sources.append("API-Football fixtures")
            else:
                report.warnings.append("API-Football 未找到双方对应赛程")

        if report.api_league_id and report.api_season:
            self._collect_standings(report, [t for t in [home_team, away_team] if t])

        if home_team:
            report.home.recent_fixtures = self._recent_fixtures(home_team["id"], report.api_season, match_date, report)
            report.home.rest_days = self._rest_days(report.home.recent_fixtures, match_date)
            if report.home.rest_days is not None:
                report.home.rest_days_source = "API-Football recent fixtures"
        if away_team:
            report.away.recent_fixtures = self._recent_fixtures(away_team["id"], report.api_season, match_date, report)
            report.away.rest_days = self._rest_days(report.away.recent_fixtures, match_date)
            if report.away.rest_days is not None:
                report.away.rest_days_source = "API-Football recent fixtures"

        if report.api_fixture_id:
            self._collect_injuries(report)
            self._collect_lineups(report)

        report.home.tactical_tags = self._infer_tactical_tags(home_stats, report.home.recent_fixtures, is_home=True)
        report.away.tactical_tags = self._infer_tactical_tags(away_stats, report.away.recent_fixtures, is_home=False)
        self._collect_supplemental_sources(report, home_name, away_name, match_date, league_name)
        report.schedule_density_note = self._schedule_density_note(report.home.rest_days, report.away.rest_days)
        report.tactical_notes = self._build_tactical_notes(report)
        report.intelligence_score = self._score(report)
        report.warnings = list(dict.fromkeys(report.warnings + report.home.warnings + report.away.warnings))
        return report

    def _collect_supplemental_sources(
        self,
        report: MatchIntelligenceReport,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
        league_name: Optional[str],
    ):
        try:
            supplemental = self.supplemental_collector.collect(
                home_name=home_name,
                away_name=away_name,
                league=league_name,
                match_date=match_date,
            )
        except Exception as exc:
            report.warnings.append(f"补充数据源获取失败: {exc}")
            return

        report.supplemental_data = supplemental.to_dict()
        self._apply_supplemental_team(report.home, supplemental.home)
        self._apply_supplemental_team(report.away, supplemental.away)
        for source in supplemental.data_sources:
            if source not in report.data_sources:
                report.data_sources.append(source)
        for warning in supplemental.warnings:
            report.warnings.append(f"补充源: {warning}")

    @staticmethod
    def _apply_supplemental_team(target: TeamIntelligence, source: Any):
        target.clubelo_rating = getattr(source, "clubelo_rating", None)
        target.clubelo_rank = getattr(source, "clubelo_rank", None)
        target.fifa_rank = getattr(source, "fifa_rank", None)
        target.market_value_eur = getattr(source, "market_value_eur", None)
        target.supplemental_notes = list(getattr(source, "source_notes", []) or [])

    def merge_web_results(self, report: MatchIntelligenceReport, web_results: List[Any]) -> MatchIntelligenceReport:
        injury_pattern = re.compile(r"\b(injur|doubt|suspend|fitness|lineup|rotation|miss)\w*\b", re.I)
        tactic_pattern = re.compile(r"\b(press|counter|possession|set[- ]piece|preview|tactic|formation)\w*\b", re.I)
        for result in web_results[:12]:
            text = f"{getattr(result, 'title', '')} {getattr(result, 'snippet', '')}"
            if not injury_pattern.search(text) and not tactic_pattern.search(text):
                continue
            report.web_evidence.append({
                "title": getattr(result, "title", ""),
                "url": getattr(result, "url", ""),
                "snippet": getattr(result, "snippet", ""),
            })
        if report.web_evidence and "Web Search" not in report.data_sources:
            report.data_sources.append("Web Search")
        report.intelligence_score = self._score(report)
        return report

    def _search_team(self, team_name: str, report: MatchIntelligenceReport) -> Optional[Dict[str, Any]]:
        for term in self._search_terms(team_name):
            data, error = self.api_get("teams", {"search": term})
            if error:
                report.warnings.append(f"teams 搜索失败({term}): {error}")
                continue
            candidates = data.get("response") or []
            team = self._pick_team(candidates)
            if team:
                return team
        return None

    @staticmethod
    def _search_terms(team_name: str) -> List[str]:
        terms = []
        terms.extend(TEAM_API_ALIASES.get(team_name, []))
        normalized = re.sub(r"[\s·\-.]", "", team_name or "")
        terms.extend(TEAM_API_ALIASES.get(normalized, []))
        terms.append(team_name)
        return list(dict.fromkeys([
            cleaned for term in terms
            for cleaned in [MatchIntelligenceCollector._api_safe_term(term)]
            if cleaned
        ]))

    @staticmethod
    def _api_safe_term(term: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", term or "")
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _pick_team(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        exclude = ["women", " u19", " u20", " u21", " u23", "academy", " ii", " b"]
        filtered = []
        for candidate in candidates:
            team = candidate.get("team") or {}
            name = f" {team.get('name', '').lower()} "
            if not any(item in name for item in exclude):
                filtered.append(team)
        national = [team for team in filtered if team.get("national")]
        if national:
            return national[0]
        return (filtered or [c.get("team") for c in candidates if c.get("team")])[0] if candidates else None

    @staticmethod
    def _apply_team_identity(target: TeamIntelligence, team: Dict[str, Any]):
        target.api_team_id = team.get("id")
        target.api_team_name = team.get("name")

    def _find_fixture(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: Optional[str],
        report: MatchIntelligenceReport,
    ) -> Optional[Dict[str, Any]]:
        date_anchor = self._parse_date(match_date) or datetime.now()
        date_from = (date_anchor - timedelta(days=3)).strftime("%Y-%m-%d")
        date_to = (date_anchor + timedelta(days=3)).strftime("%Y-%m-%d")

        for season in self._candidate_seasons(date_anchor):
            data, error = self.api_get("fixtures", {
                "team": home_team_id,
                "season": season,
                "from": date_from,
                "to": date_to,
            })
            if error:
                report.warnings.append(f"fixtures 查询失败({season}): {error}")
                continue
            matches = []
            for item in data.get("response") or []:
                teams = item.get("teams") or {}
                ids = {teams.get("home", {}).get("id"), teams.get("away", {}).get("id")}
                if ids == {home_team_id, away_team_id}:
                    matches.append(item)
            if matches:
                matches.sort(key=lambda item: item.get("fixture", {}).get("date", ""))
                return matches[0]
        return None

    def _collect_standings(self, report: MatchIntelligenceReport, teams: List[Dict[str, Any]]):
        data, error = self.api_get("standings", {"league": report.api_league_id, "season": report.api_season})
        if error:
            report.warnings.append(f"standings 查询失败: {error}")
            return
        standings = []
        for league_item in data.get("response") or []:
            for table in (league_item.get("league") or {}).get("standings") or []:
                standings.extend(table)
        by_team = {(row.get("team") or {}).get("id"): row for row in standings}
        for team in teams:
            row = by_team.get(team.get("id"))
            target = report.home if team.get("id") == report.home.api_team_id else report.away
            if not row:
                continue
            target.league_rank = row.get("rank")
            target.league_points = row.get("points")
            target.league_form = row.get("form")
        if standings:
            report.data_sources.append("API-Football standings")

    def _recent_fixtures(
        self,
        team_id: int,
        season: Optional[int],
        match_date: Optional[str],
        report: MatchIntelligenceReport,
    ) -> List[Dict[str, Any]]:
        date_anchor = self._parse_date(match_date) or datetime.now()
        date_from = (date_anchor - timedelta(days=45)).strftime("%Y-%m-%d")
        date_to = (date_anchor - timedelta(days=1)).strftime("%Y-%m-%d")
        seasons = [season] if season else self._candidate_seasons(date_anchor)
        fixtures = []
        for candidate_season in seasons:
            data, error = self.api_get("fixtures", {
                "team": team_id,
                "season": candidate_season,
                "from": date_from,
                "to": date_to,
            })
            if error:
                report.warnings.append(f"recent fixtures 查询失败({team_id}/{candidate_season}): {error}")
                continue
            for item in data.get("response") or []:
                fixture = item.get("fixture") or {}
                goals = item.get("goals") or {}
                teams = item.get("teams") or {}
                fixtures.append({
                    "fixture_id": fixture.get("id"),
                    "date": fixture.get("date"),
                    "league": (item.get("league") or {}).get("name"),
                    "home": (teams.get("home") or {}).get("name"),
                    "away": (teams.get("away") or {}).get("name"),
                    "goals_home": goals.get("home"),
                    "goals_away": goals.get("away"),
                })
            if fixtures:
                break
        fixtures.sort(key=lambda item: item.get("date") or "", reverse=True)
        if fixtures and "API-Football recent fixtures" not in report.data_sources:
            report.data_sources.append("API-Football recent fixtures")
        return fixtures[:6]

    def _collect_injuries(self, report: MatchIntelligenceReport):
        for side in [report.home, report.away]:
            if not side.api_team_id:
                continue
            data, error = self.api_get("injuries", {
                "fixture": report.api_fixture_id,
                "team": side.api_team_id,
            })
            if error:
                side.warnings.append(f"injuries 查询失败: {error}")
                continue
            response = data.get("response") or []
            # 空响应只能说明 API 没有列出伤停，不能等同于官方确认无人缺阵。
            side.injury_status = "confirmed_injuries" if response else "reported_clear"
            side.injury_sources.append("API-Football injuries")
            for item in response:
                player = item.get("player") or {}
                side.injuries.append({
                    "player": player.get("name"),
                    "type": player.get("type"),
                    "reason": player.get("reason"),
                })
        if report.home.injury_status != "unknown" or report.away.injury_status != "unknown":
            report.data_sources.append("API-Football injuries")

    def _collect_lineups(self, report: MatchIntelligenceReport):
        data, error = self.api_get("fixtures/lineups", {"fixture": report.api_fixture_id})
        if error:
            report.warnings.append(f"lineups 查询失败: {error}")
            return
        for item in data.get("response") or []:
            team = item.get("team") or {}
            start_xi = item.get("startXI") or []
            target = None
            if team.get("id") == report.home.api_team_id:
                target = report.home
            elif team.get("id") == report.away.api_team_id:
                target = report.away
            if not target:
                continue
            target.lineup = [
                {
                    "player": (row.get("player") or {}).get("name"),
                    "number": (row.get("player") or {}).get("number"),
                    "pos": (row.get("player") or {}).get("pos"),
                }
                for row in start_xi
            ]
            if target.lineup:
                target.lineup_status = "official"
                target.lineup_sources.append("API-Football lineups")
        if report.home.lineup or report.away.lineup:
            report.data_sources.append("API-Football lineups")

    @staticmethod
    def _infer_tactical_tags(stats: Optional[Any], recent_fixtures: List[Dict[str, Any]], is_home: bool) -> List[str]:
        tags = []
        matches = getattr(stats, "matches_played", 0) or 0
        gf = getattr(stats, "goals_for", 0) or 0
        ga = getattr(stats, "goals_against", 0) or 0
        if matches:
            gf_avg = gf / matches
            ga_avg = ga / matches
            if gf_avg >= 1.7:
                tags.append("进攻效率高")
            elif gf_avg <= 1.0:
                tags.append("进攻偏弱")
            if ga_avg >= 1.6:
                tags.append("防线波动大")
            elif ga_avg <= 1.0:
                tags.append("防守稳定")
            if gf_avg + ga_avg >= 3.0:
                tags.append("开放型比赛倾向")
            elif gf_avg + ga_avg <= 2.1:
                tags.append("节奏偏保守")

        scored_first = 0
        conceded = 0
        for fixture in recent_fixtures:
            home_name = fixture.get("home")
            goals_home = fixture.get("goals_home")
            goals_away = fixture.get("goals_away")
            if goals_home is None or goals_away is None:
                continue
            team_is_home = is_home if home_name else False
            own = goals_home if team_is_home else goals_away
            opp = goals_away if team_is_home else goals_home
            if own and own >= 2:
                scored_first += 1
            if opp and opp >= 2:
                conceded += 1
        if scored_first >= 3:
            tags.append("近期多球能力较强")
        if conceded >= 3:
            tags.append("近期易被打穿")
        return list(dict.fromkeys(tags))

    @staticmethod
    def _schedule_density_note(home_rest: Optional[int], away_rest: Optional[int]) -> Optional[str]:
        if home_rest is None and away_rest is None:
            return None
        if home_rest is not None and away_rest is not None:
            if home_rest <= 3 and away_rest > home_rest + 2:
                return "主队休息时间明显少于客队，体能可能吃亏"
            if away_rest <= 3 and home_rest > away_rest + 2:
                return "客队休息时间明显少于主队，体能可能吃亏"
            return f"主队休息 {home_rest} 天，客队休息 {away_rest} 天"
        return f"主队休息 {home_rest} 天，客队休息 {away_rest} 天"

    @staticmethod
    def _build_tactical_notes(report: MatchIntelligenceReport) -> List[str]:
        notes = []
        if report.home.tactical_tags:
            notes.append(f"{report.home.team_name}: {'、'.join(report.home.tactical_tags)}")
        if report.away.tactical_tags:
            notes.append(f"{report.away.team_name}: {'、'.join(report.away.tactical_tags)}")
        if report.schedule_density_note:
            notes.append(report.schedule_density_note)
        if report.home.injuries:
            notes.append(f"{report.home.team_name} 伤停 {len(report.home.injuries)} 人")
        if report.away.injuries:
            notes.append(f"{report.away.team_name} 伤停 {len(report.away.injuries)} 人")
        return notes

    @staticmethod
    def _rest_days(fixtures: List[Dict[str, Any]], match_date: Optional[str]) -> Optional[int]:
        target = MatchIntelligenceCollector._parse_date(match_date)
        if not target or not fixtures:
            return None
        last_date = MatchIntelligenceCollector._parse_date(fixtures[0].get("date"))
        if not last_date:
            return None
        return max(0, (target.date() - last_date.date()).days)

    @staticmethod
    def _candidate_seasons(anchor: datetime) -> List[int]:
        return [anchor.year, anchor.year - 1, anchor.year - 2]

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value.replace("Z", "+0000"), fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _score(report: MatchIntelligenceReport) -> float:
        score = 0
        if report.api_fixture_id:
            score += 20
        if report.home.league_rank or report.away.league_rank:
            score += 15
        if report.home.recent_fixtures and report.away.recent_fixtures:
            score += 15
        if report.home.rest_days is not None or report.away.rest_days is not None:
            score += 10
        if report.home.injuries or report.away.injuries:
            score += 15
        if report.home.lineup or report.away.lineup:
            score += 15
        if report.tactical_notes:
            score += 10
        if report.web_evidence:
            score += 10
        return min(score, 100)


__all__ = [
    "MatchIntelligenceCollector",
    "MatchIntelligenceReport",
    "TeamIntelligence",
    "TEAM_API_ALIASES",
]
