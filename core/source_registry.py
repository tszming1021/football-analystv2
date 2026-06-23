#!/usr/bin/env python3
"""数据源注册表。

集中记录每类缺失字段可以去哪里补，便于报告和调试时解释
“为什么这个字段有/没有数据”。
"""

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class DataSourceProfile:
    name: str
    url: str
    cost: str
    fields: List[str]
    notes: str
    env_key: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class DataSourceRegistry:
    """Describe recommended sources by data field."""

    SOURCES = [
        DataSourceProfile(
            name="500彩票网",
            url="https://trade.500.com/jczq/",
            cost="free",
            fields=["jingcai_odds", "handicap", "europe_odds", "asian_handicap", "recent_form", "h2h"],
            notes="中国竞彩比赛与盘口主源，适合作为赛前投注入口。",
        ),
        DataSourceProfile(
            name="API-Football",
            url="https://www.api-football.com/documentation-v3",
            cost="paid/free quota",
            fields=["fixtures", "standings", "injuries", "lineups", "team_statistics"],
            notes="结构化足球数据主补源；免费额度有限，伤停/首发覆盖受联赛和套餐影响。",
            env_key="API_FOOTBALL_KEY",
        ),
        DataSourceProfile(
            name="ClubElo",
            url="http://api.clubelo.com/",
            cost="free",
            fields=["club_elo", "club_rank", "club_form_strength"],
            notes="免费俱乐部 Elo 数据，适合补球队强弱基准；国家队和小联赛覆盖有限。",
        ),
        DataSourceProfile(
            name="football-data.co.uk",
            url="https://www.football-data.co.uk/data.php",
            cost="free",
            fields=["historical_results", "bookmaker_odds", "closing_odds", "shots", "cards", "corners"],
            notes="欧洲主流联赛历史赛果和博彩公司赔率 CSV，适合训练和回测，不适合作为中国竞彩即时盘口。",
        ),
        DataSourceProfile(
            name="FootballData.io FIFA Rankings",
            url="https://footballdata.io/documentation/fifa-rankings/",
            cost="free/paid quota",
            fields=["fifa_rank", "fifa_points", "national_team_strength"],
            notes="国家队排名补源；需要 API key。",
            env_key="FOOTBALLDATA_IO_KEY",
        ),
        DataSourceProfile(
            name="Sportmonks Football API",
            url="https://www.sportmonks.com/football-api/free-plan/",
            cost="free/paid quota",
            fields=["fixtures", "standings", "injuries", "lineups", "player_stats"],
            notes="可作为 API-Football 的备用结构化数据源；需要 API key。",
            env_key="SPORTMONKS_KEY",
        ),
        DataSourceProfile(
            name="TheStatsAPI",
            url="https://www.thestatsapi.com/football-api",
            cost="paid",
            fields=["fixtures", "venue", "referee", "xg", "xga", "shotmap", "lineups", "player_stats", "external_odds"],
            notes="优先用于真实xG/xGA和shotmap；赛前若xG未开放，则记录状态并回退到项目proxy xG。",
            env_key="THESTATSAPI_KEY",
        ),
        DataSourceProfile(
            name="AnySport",
            url="https://docs.anysport.io/",
            cost="free/paid quota",
            fields=["fixtures", "odds", "lineups", "standings"],
            notes="可选备用体育数据 API；具体免费额度以官网为准。",
            env_key="ANYSPORT_KEY",
        ),
        DataSourceProfile(
            name="Odds-API.io",
            url="https://docs.odds-api.io/api-reference/odds/get-event-odds",
            cost="free/paid quota",
            fields=["external_odds", "bookmaker_odds", "event_odds"],
            notes="有 API key 时自动尝试匹配足球事件并补充外部赔率，作为500深层盘口之外的交叉验证。",
            env_key="ODDS_API_IO_KEY",
        ),
        DataSourceProfile(
            name="The Odds API",
            url="https://the-odds-api.com/liveapi/guides/v4/",
            cost="free/paid quota",
            fields=["external_odds", "bookmaker_odds", "event_odds"],
            notes="有 API key 时按配置的 soccer sport keys 查询 h2h/spreads/totals。",
            env_key="THE_ODDS_API_KEY",
        ),
        DataSourceProfile(
            name="TheSportsDB",
            url="https://www.thesportsdb.com/api.php",
            cost="free",
            fields=["event_metadata", "venue", "kickoff_time", "final_score"],
            notes="免费事件查询源，用于补比赛时间、场地、赛果和天气定位线索。",
            env_key="THESPORTSDB_KEY",
        ),
        DataSourceProfile(
            name="FBref",
            url="https://fbref.com/en/",
            cost="free",
            fields=["xg", "shots", "possession", "passing", "pressing_proxy"],
            notes="技术统计质量高，但页面抓取需限速，适合赛后技术面补强。",
        ),
        DataSourceProfile(
            name="Open-Meteo",
            url="https://open-meteo.com/en/docs",
            cost="free",
            fields=["weather", "temperature", "precipitation", "wind"],
            notes="免费天气源，已用于天气和场地影响模块。",
        ),
    ]

    @classmethod
    def all(cls) -> List[Dict[str, object]]:
        return [source.to_dict() for source in cls.SOURCES]

    @classmethod
    def for_field(cls, field_name: str) -> List[Dict[str, object]]:
        return [
            source.to_dict()
            for source in cls.SOURCES
            if field_name in source.fields
        ]

    @classmethod
    def coverage_map(cls) -> Dict[str, List[str]]:
        coverage: Dict[str, List[str]] = {}
        for source in cls.SOURCES:
            for field in source.fields:
                coverage.setdefault(field, []).append(source.name)
        return coverage


__all__ = ["DataSourceProfile", "DataSourceRegistry"]
