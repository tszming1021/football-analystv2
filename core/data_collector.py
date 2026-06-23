#!/usr/bin/env python3
"""
数据收集层 - Data Collection Layer
负责从API和联网搜索获取数据
优先级：API > 联网搜索
禁止使用模拟数据
"""

import os
import sys
import json
import re
import time
import html as html_lib
import base64
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_new import ParsedMatch, TeamNameTranslator
from core.jingcai_500_collector import Jingcai500Collector, JingcaiMatch, JingcaiTeamStats
from core.match_intelligence import MatchIntelligenceCollector, MatchIntelligenceReport, TEAM_API_ALIASES
from core.odds_history import OddsHistoryStore
from core.supplemental_data import SupplementalDataCollector
from core.weather_context import WeatherContextCollector
from core.data_sources.thestatsapi import TheStatsAPIClient


@dataclass
class TeamData:
    """球队数据"""
    team_id: int
    name: str
    name_zh: str
    country: str
    founded: int
    logo: str
    league_info: Optional[Dict] = None


@dataclass
class MatchData:
    """比赛数据"""
    fixture_id: int
    match_date: datetime
    timezone: str
    venue: Dict
    home_team: TeamData
    away_team: TeamData
    league: Dict
    status: str
    referee: Optional[str] = None


@dataclass
class OddsData:
    """赔率数据"""
    bookmaker: str
    home_win: float
    draw: float
    away_win: float
    over_25: Optional[float] = None
    under_25: Optional[float] = None
    handicap: Optional[int] = None
    handicap_home_win: Optional[float] = None
    handicap_draw: Optional[float] = None
    handicap_away_win: Optional[float] = None
    timestamp: Optional[datetime] = None


@dataclass
class StatisticsData:
    """统计数据"""
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    xg: Optional[float] = None
    xga: Optional[float] = None
    clean_sheets: Optional[int] = None
    btts: Optional[int] = None
    form: Optional[List[str]] = None  # 近5场结果 ['W', 'W', 'D', 'L', 'W']
    source: str = ""
    season: Optional[int] = None


@dataclass
class WebSearchResult:
    """联网搜索结果"""
    source: str
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class CompleteDataReport:
    """完整数据报告"""
    # 输入信息
    parsed_match: ParsedMatch
    query_timestamp: datetime

    # API数据 (如果可用)
    api_available: bool = False
    api_error_message: Optional[str] = None

    home_team_data: Optional[TeamData] = None
    away_team_data: Optional[TeamData] = None
    match_data: Optional[MatchData] = None
    odds_data: List[OddsData] = field(default_factory=list)
    home_stats: Optional[StatisticsData] = None
    away_stats: Optional[StatisticsData] = None
    home_home_stats: Optional[StatisticsData] = None
    away_away_stats: Optional[StatisticsData] = None
    h2h_history: List[Dict] = field(default_factory=list)  # 历史交锋
    season_used: Optional[int] = None
    jingcai_match: Optional[Dict[str, Any]] = None
    match_intelligence: Optional[Dict[str, Any]] = None
    supplemental_data: Optional[Dict[str, Any]] = None
    weather_context: Optional[Dict[str, Any]] = None
    odds_history: Optional[Dict[str, Any]] = None
    qimen_analysis: Optional[Dict[str, Any]] = None

    # 联网搜索数据
    web_search_available: bool = False
    web_search_results: List[WebSearchResult] = field(default_factory=list)
    team_news: Dict[str, List[str]] = field(default_factory=dict)  # 球队新闻
    injury_updates: Dict[str, List[str]] = field(default_factory=dict)  # 伤病更新
    expert_predictions: List[str] = field(default_factory=list)  # 专家预测

    # 数据质量评估
    data_completeness_score: float = 0.0  # 0-100
    data_completeness_breakdown: Dict[str, Any] = field(default_factory=dict)
    data_sources_used: List[str] = field(default_factory=list)
    data_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典格式，便于序列化"""
        return {
            'parsed_match': {
                'home_team_raw': self.parsed_match.home_team_raw,
                'away_team_raw': self.parsed_match.away_team_raw,
                'home_team_en': self.parsed_match.home_team_en,
                'away_team_en': self.parsed_match.away_team_en,
                'input_str': self.parsed_match.input_str,
            },
            'query_timestamp': self.query_timestamp.isoformat(),
            'api_available': self.api_available,
            'api_error_message': self.api_error_message,
            'web_search_available': self.web_search_available,
            'data_completeness_score': self.data_completeness_score,
            'data_completeness_breakdown': self.data_completeness_breakdown,
            'data_sources_used': self.data_sources_used,
            'data_warnings': self.data_warnings,
            'season_used': self.season_used,
            'home_home_stats': self.home_home_stats.__dict__ if self.home_home_stats else None,
            'away_away_stats': self.away_away_stats.__dict__ if self.away_away_stats else None,
            'jingcai_match': self.jingcai_match,
            'match_intelligence': self.match_intelligence,
            'supplemental_data': self.supplemental_data,
            'weather_context': self.weather_context,
            'odds_history': self.odds_history,
            'qimen_analysis': self.qimen_analysis,
            'web_search_results': [item.__dict__ for item in self.web_search_results],
            'team_news': self.team_news,
            'injury_updates': self.injury_updates,
            'expert_predictions': self.expert_predictions,
        }


class DataCollector:
    """数据收集器 - 主类"""

    def __init__(self, api_football_key: Optional[str] = None):
        self.api_key = api_football_key or os.getenv('API_FOOTBALL_KEY')
        self.api_base = "https://v3.football.api-sports.io"
        self.session = requests.Session()
        self.jingcai_collector = Jingcai500Collector()
        self.supplemental_collector = SupplementalDataCollector(self.session, timeout=4)
        self.intelligence_collector = MatchIntelligenceCollector(self._api_get, self.supplemental_collector)
        self.odds_history_store = OddsHistoryStore()
        self.weather_collector = WeatherContextCollector()
        self.thestatsapi_client = TheStatsAPIClient(session=self.session, timeout=10)
        self.api_available = self._check_api_availability()

    def _headers(self) -> Dict[str, str]:
        return {'x-apisports-key': self.api_key} if self.api_key else {}

    def _api_get(self, endpoint: str, params: Dict[str, Any], timeout: int = 12) -> Tuple[Optional[Dict], Optional[str]]:
        """Call API-Football and return (payload, error_message)."""
        if not self.api_key:
            return None, "未提供 API-Football Key"

        try:
            response = self.session.get(
                f"{self.api_base}/{endpoint}",
                headers=self._headers(),
                params=params,
                timeout=timeout,
            )
            try:
                data = response.json()
            except ValueError:
                return None, f"{endpoint} 返回非 JSON 响应: HTTP {response.status_code}"

            if response.status_code != 200:
                return data, f"{endpoint} HTTP {response.status_code}: {data.get('message', '')}"

            errors = data.get('errors')
            if errors:
                return data, f"{endpoint} API限制/错误: {errors}"

            return data, None
        except requests.RequestException as e:
            return None, f"{endpoint} 请求失败: {e}"

    def _check_api_availability(self) -> bool:
        """检查API是否可用"""
        if not self.api_key:
            print("⚠️ 未提供 API-Football Key")
            return False

        try:
            # 测试API连接
            response = self.session.get(
                f"{self.api_base}/status",
                headers=self._headers(),
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                errors = data.get("errors") if isinstance(data, dict) else None
                if isinstance(data, dict) and not errors and "response" in data:
                    print(f"✅ API-Football 连接正常")
                    return True
            print(f"⚠️ API 连接失败: {response.status_code}")
            return False
        except Exception as e:
            print(f"⚠️ API 检查失败: {e}")
            return False

    def collect_data(self, parsed_match: ParsedMatch) -> CompleteDataReport:
        """
        收集完整数据 - 主入口

        流程:
        1. 优先尝试 500彩票网获取中国竞彩赔率和赛前数据
        2. API-Football 补充结构化足球数据
        3. 联网搜索只补新闻/伤停，不生成模拟数据
        """
        report = CompleteDataReport(
            parsed_match=parsed_match,
            query_timestamp=datetime.now(),
            api_available=self.api_available,
        )

        print("\n" + "="*60)
        print("📊 数据收集阶段")
        print("="*60)

        print("\n🎯 步骤 1/5: 500彩票网竞彩数据...")
        jingcai_ok = False
        try:
            jingcai_match = None
            for offset in (0, 1, 2):
                candidate_date = (report.query_timestamp + timedelta(days=offset)).strftime("%Y-%m-%d")
                jingcai_match = self.jingcai_collector.find_match(
                    parsed_match.home_team_raw,
                    parsed_match.away_team_raw,
                    match_date=candidate_date,
                )
                if jingcai_match:
                    break
            if jingcai_match:
                self._apply_jingcai_data(report, jingcai_match)
                report.data_sources_used.append("500彩票网")
                jingcai_ok = True
                print("✅ 500彩票网竞彩数据获取完成")
            else:
                print("⚠️ 500彩票网未找到该竞彩比赛")
        except Exception as e:
            print(f"⚠️ 500彩票网数据获取失败: {e}")
            report.data_warnings.append(f"500彩票网数据获取失败: {e}")

        has_core_jingcai_data = jingcai_ok and report.odds_data and report.home_stats and report.away_stats

        # 步骤2: API数据获取 (如果可用)。中国竞彩场景下仅补缺基础数据。
        if self.api_available and not has_core_jingcai_data:
            print("\n🔌 步骤 2/5: API-Football 基础数据补缺...")
            try:
                self._collect_api_data(report, parsed_match, preserve_existing=jingcai_ok)
                if "API-Football" not in report.data_sources_used:
                    report.data_sources_used.append("API-Football")
                print("✅ API 基础数据获取完成")
            except Exception as e:
                print(f"⚠️ API 基础数据获取失败: {e}")
                report.api_error_message = str(e)
        else:
            if has_core_jingcai_data:
                print("\n🔌 步骤 2/5: 500彩票网核心数据完整，API 只补赛事情报")
            else:
                print("\n🔌 步骤 2/5: 跳过 API 基础数据 (未提供 API Key 或 API 不可用)")

        print("\n🧩 步骤 3/5: 赛事情报数据...")
        try:
            self._collect_match_intelligence(report, parsed_match)
            if report.match_intelligence:
                sources = report.match_intelligence.get("data_sources") or []
                if any(source.startswith("API-Football") for source in sources):
                    if "API-Football Intelligence" not in report.data_sources_used:
                        report.data_sources_used.append("API-Football Intelligence")
                elif sources and "Match Intelligence" not in report.data_sources_used:
                    report.data_sources_used.append("Match Intelligence")
                supplemental_sources = (report.supplemental_data or {}).get("data_sources") or []
                if supplemental_sources and "Supplemental Sources" not in report.data_sources_used:
                    report.data_sources_used.append("Supplemental Sources")
                print(f"✅ 赛事情报获取完成 ({report.match_intelligence.get('intelligence_score', 0):.0f}%)")
            else:
                print("⚠️ 未获取到赛事情报")
        except Exception as e:
            print(f"⚠️ 赛事情报获取失败: {e}")
            report.data_warnings.append(f"赛事情报获取失败: {e}")

        try:
            self._collect_weather_context(report)
            if report.weather_context and "Weather" not in report.data_sources_used:
                report.data_sources_used.append("Weather")
        except Exception as e:
            report.data_warnings.append(f"天气数据获取失败: {e}")

        print("\n📈 步骤 3.5/5: xG/xGA数据源...")
        try:
            self._collect_xg_data(report, parsed_match)
            xg_data = ((report.supplemental_data or {}).get("xg_data") or {})
            if xg_data and "TheStatsAPI" not in report.data_sources_used:
                report.data_sources_used.append("TheStatsAPI")
            if xg_data.get("xg_available"):
                print("✅ TheStatsAPI真实xG获取完成")
            elif xg_data:
                print("⚠️ TheStatsAPI暂无真实xG，后续使用proxy xG")
            else:
                print("⚠️ 未配置TheStatsAPI，后续使用proxy xG")
        except Exception as e:
            report.data_warnings.append(f"xG数据源获取失败: {e}")

        # 步骤3: 联网搜索获取数据。只记录真实搜索结果，不生成模拟结论。
        print("\n🔍 步骤 4/5: 联网搜索数据...")
        try:
            self._collect_web_search_data(report, parsed_match)
            if report.web_search_available:
                report.data_sources_used.append("Web Search")
                self._merge_web_intelligence(report)
                print("✅ 联网搜索数据获取完成")
            else:
                print("⚠️ 联网搜索未获取到可用结果")
        except Exception as e:
            print(f"⚠️ 联网搜索失败: {e}")
            report.data_warnings.append(f"联网搜索失败: {e}")

        # 步骤4: 数据质量评估
        print("\n📊 步骤 5/5: 数据质量评估...")
        self._assess_data_quality(report)

        print("\n" + "="*60)
        print("✅ 数据收集完成")
        print(f"   数据来源: {', '.join(report.data_sources_used)}")
        print(f"   数据完整度: {report.data_completeness_score:.0f}%")
        print("="*60)

        return report

    def _apply_jingcai_data(self, report: CompleteDataReport, match: JingcaiMatch):
        """将 500彩票网数据映射到通用数据报告。"""
        try:
            match_dt = datetime.strptime(f"{match.match_date} {match.match_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            match_dt = report.query_timestamp
            report.data_warnings.append("500彩票网未解析到完整比赛时间，使用查询时间作为临时 match_date")
        self._filter_pre_match_jingcai_records(match, match_dt, report)
        if match.handicap is None:
            handicap_records = ((match.handicap_market or {}).get("records") or [])
            if handicap_records:
                match.handicap = self._safe_int_from_text(handicap_records[0].get("handicap"))
        home_team = TeamData(
            team_id=0,
            name=match.home_team,
            name_zh=match.home_team,
            country="China/Jingcai",
            founded=0,
            logo="",
        )
        away_team = TeamData(
            team_id=0,
            name=match.away_team,
            name_zh=match.away_team,
            country="China/Jingcai",
            founded=0,
            logo="",
        )

        report.home_team_data = home_team
        report.away_team_data = away_team
        report.match_data = MatchData(
            fixture_id=int(match.fixture_id) if str(match.fixture_id).isdigit() else 0,
            match_date=match_dt,
            timezone="Asia/Shanghai",
            venue={},
            home_team=home_team,
            away_team=away_team,
            league={"name": match.league, "source": "500彩票网"},
            status="Not Started",
        )

        if match.no_handicap_odds:
            odds = OddsData(
                bookmaker=match.no_handicap_odds.source,
                home_win=match.no_handicap_odds.home_win,
                draw=match.no_handicap_odds.draw,
                away_win=match.no_handicap_odds.away_win,
                handicap=match.handicap,
                timestamp=datetime.now(),
            )
            if match.handicap_odds:
                odds.handicap_home_win = match.handicap_odds.home_win
                odds.handicap_draw = match.handicap_odds.draw
                odds.handicap_away_win = match.handicap_odds.away_win
            report.odds_data = [odds]
        elif match.average_europe_odds:
            odds = OddsData(
                bookmaker=match.average_europe_odds.source,
                home_win=match.average_europe_odds.home_win,
                draw=match.average_europe_odds.draw,
                away_win=match.average_europe_odds.away_win,
                handicap=match.handicap,
                timestamp=datetime.now(),
            )
            handicap_records = ((match.handicap_market or {}).get("records") or [])
            if handicap_records and handicap_records[0].get("current_odds"):
                handicap_odds = handicap_records[0]["current_odds"]
                odds.handicap_home_win = handicap_odds.get("home")
                odds.handicap_draw = handicap_odds.get("draw")
                odds.handicap_away_win = handicap_odds.get("away")
            report.odds_data = [odds]
            report.data_warnings.append("500彩票网竞彩胜平负缺失，使用百家欧赔均值作为赔率模型 fallback")

        report.home_stats = self._jingcai_stats_to_statistics(match.home_stats)
        report.away_stats = self._jingcai_stats_to_statistics(match.away_stats)
        report.home_home_stats = self._jingcai_stats_to_statistics(match.home_home_stats)
        report.away_away_stats = self._jingcai_stats_to_statistics(match.away_away_stats)
        if match.h2h_summary:
            report.h2h_history = [{"source": "500彩票网", "summary": match.h2h_summary}]
        if match.h2h_records:
            report.h2h_history.extend([
                {"source": "500彩票网交锋历史", **record}
                for record in match.h2h_records[:10]
            ])
        if match.recommendation_text:
            report.expert_predictions.append(f"500彩票网: {match.recommendation_text}")
        if match.predicted_lineups or match.macau_recommendation:
            report.match_intelligence = report.match_intelligence or {}
            report.match_intelligence["jingcai_500"] = {
                "predicted_lineups": match.predicted_lineups,
                "macau_recommendation": match.macau_recommendation,
                "future_fixtures": match.future_fixtures,
            }

        snapshots = self.odds_history_store.record_jingcai_match(match)
        report.odds_history = self.odds_history_store.summary_for_fixture(match.fixture_id)

        report.jingcai_match = {
            "fixture_id": match.fixture_id,
            "match_num": match.match_num,
            "league": match.league,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "match_date": match.match_date,
            "match_time": match.match_time,
            "handicap": match.handicap,
            "no_handicap_odds": match.no_handicap_odds.__dict__ if match.no_handicap_odds else None,
            "handicap_odds": match.handicap_odds.__dict__ if match.handicap_odds else None,
            "average_europe_odds": match.average_europe_odds.__dict__ if match.average_europe_odds else None,
            "opening_average_europe_odds": match.opening_average_europe_odds.__dict__ if match.opening_average_europe_odds else None,
            "asian_average": match.asian_average,
            "europe_market": match.europe_market,
            "asian_market": match.asian_market,
            "handicap_market": match.handicap_market,
            "score_market": match.score_market,
            "mixed_market": match.mixed_market,
            "fifa_rankings": match.fifa_rankings,
            "league_standings": match.league_standings,
            "home_home_stats": match.home_home_stats.__dict__ if match.home_home_stats else None,
            "away_away_stats": match.away_away_stats.__dict__ if match.away_away_stats else None,
            "h2h_summary": match.h2h_summary,
            "h2h_records": match.h2h_records,
            "recent_records": match.recent_records,
            "future_fixtures": match.future_fixtures,
            "predicted_lineups": match.predicted_lineups,
            "macau_recommendation": match.macau_recommendation,
            "recommendation_text": match.recommendation_text,
            "docx_supplement": match.docx_supplement,
            "odds_snapshots_recorded": len(snapshots),
            "analysis_url": match.analysis_url,
            "europe_url": match.europe_url,
            "asian_url": match.asian_url,
            "handicap_url": Jingcai500Collector.HANDICAP_URL.format(fixture_id=match.fixture_id),
            "score_url": Jingcai500Collector.SCORE_URL.format(fixture_id=match.fixture_id),
        }

    @staticmethod
    def _jingcai_stats_to_statistics(stats: Optional[JingcaiTeamStats]) -> Optional[StatisticsData]:
        if not stats:
            return None
        return StatisticsData(
            matches_played=stats.matches_played,
            wins=stats.wins,
            draws=stats.draws,
            losses=stats.losses,
            goals_for=stats.goals_for,
            goals_against=stats.goals_against,
            xg=stats.goals_for / stats.matches_played if stats.matches_played else None,
            xga=stats.goals_against / stats.matches_played if stats.matches_played else None,
            form=stats.form,
            source=stats.source,
        )

    @staticmethod
    def _safe_int_from_text(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        match = re.search(r"[+-]?\d+", str(value))
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def _collect_api_data(self, report: CompleteDataReport, parsed_match: ParsedMatch, preserve_existing: bool = False):
        """通过API-Football收集数据"""
        # 1. 搜索球队
        home_team = self._search_team(parsed_match.home_team_raw, parsed_match.home_team_en)
        away_team = self._search_team(parsed_match.away_team_raw, parsed_match.away_team_en)

        if not home_team or not away_team:
            raise ValueError(f"无法找到球队: {home_team} vs {away_team}")

        if not preserve_existing:
            report.home_team_data = home_team
            report.away_team_data = away_team

        # 2. 在日期窗口中匹配双方赛程。Free 计划不能使用 next 参数。
        fixture = self._find_fixture_between_teams(home_team.team_id, away_team.team_id, report)
        if fixture and not preserve_existing:
            report.match_data = fixture
            report.season_used = fixture.league.get('season')

        # 3. 获取赔率
        if report.match_data and not report.odds_data:
            odds_list = self._get_odds(report.match_data.fixture_id)
            report.odds_data = odds_list
            if not odds_list:
                report.data_warnings.append("API-Football 未返回该比赛赔率，投注建议将被禁用")

        # 4. 获取历史交锋与赛季统计。若没有目标比赛，用最近可访问赛季兜底。
        if not report.h2h_history:
            report.h2h_history = self._get_h2h(home_team.team_id, away_team.team_id, report)
        league_id, season = self._infer_league_and_season(report, home_team.team_id)
        if league_id and season:
            report.season_used = report.season_used or season
            if not report.home_stats:
                report.home_stats = self._get_team_statistics(home_team.team_id, league_id, season)
            if not report.away_stats:
                report.away_stats = self._get_team_statistics(away_team.team_id, league_id, season)
        else:
            report.data_warnings.append("未能推断 league/season，无法获取球队统计")

    def _collect_match_intelligence(self, report: CompleteDataReport, parsed_match: ParsedMatch):
        """收集伤停、首发、赛程密度、排名和战术标签。"""
        match_date = None
        if report.match_data:
            match_date = report.match_data.match_date.strftime("%Y-%m-%d")
        elif report.jingcai_match:
            match_date = report.jingcai_match.get("match_date")

        if self.api_available:
            intelligence = self.intelligence_collector.collect(
                home_name=parsed_match.home_team_raw,
                away_name=parsed_match.away_team_raw,
                match_date=match_date,
                league_name=(report.jingcai_match or {}).get("league") or ((report.match_data.league or {}).get("name") if report.match_data else None),
                home_stats=report.home_stats,
                away_stats=report.away_stats,
            )
            report.match_intelligence = intelligence.to_dict()
            report.supplemental_data = report.match_intelligence.get("supplemental_data")
            for warning in intelligence.warnings[:8]:
                report.data_warnings.append(f"赛事情报: {warning}")
        else:
            report.match_intelligence = self._build_local_intelligence(report, parsed_match)
            report.supplemental_data = report.match_intelligence.get("supplemental_data")
        self._merge_jingcai_intelligence(report, parsed_match)

    def _collect_weather_context(self, report: CompleteDataReport):
        if not report.match_data:
            return
        context = self.weather_collector.collect(
            home_team=report.match_data.home_team.name_zh or report.match_data.home_team.name,
            away_team=report.match_data.away_team.name_zh or report.match_data.away_team.name,
            match_dt=report.match_data.match_date,
            venue=report.match_data.venue,
        )
        if context:
            report.weather_context = context.to_dict()

    def _collect_xg_data(self, report: CompleteDataReport, parsed_match: ParsedMatch):
        """Prefer actual xG providers. Proxy xG is calculated later in model layer."""
        if not self.thestatsapi_client.available:
            report.data_warnings.append("未提供 THESTATSAPI_KEY，真实xG源跳过")
            return

        match_date = None
        if report.match_data:
            match_date = report.match_data.match_date.strftime("%Y-%m-%d")
        elif report.jingcai_match:
            match_date = str(report.jingcai_match.get("match_date") or "")[:10] or None
        competition_hint = (report.jingcai_match or {}).get("league") or None
        if competition_hint and "世界杯" in str(competition_hint):
            competition_hint = "world cup"
        elif competition_hint and ("国际" in str(competition_hint) or "友谊" in str(competition_hint)):
            competition_hint = "friendly"

        probe = self.thestatsapi_client.probe_match(
            home_name=parsed_match.home_team_en or parsed_match.home_team_raw,
            away_name=parsed_match.away_team_en or parsed_match.away_team_raw,
            match_date=match_date,
            competition_hint=competition_hint,
        )
        supplemental = report.supplemental_data or {}
        supplemental["xg_data"] = probe.to_dict()
        report.supplemental_data = supplemental
        for warning in probe.warnings[:5]:
            report.data_warnings.append(f"TheStatsAPI: {warning}")

    def _merge_jingcai_intelligence(self, report: CompleteDataReport, parsed_match: ParsedMatch):
        """把500的近期赛程、未来赛程和预计阵容转成可评分的结构化情报。"""
        jingcai = report.jingcai_match or {}
        intelligence = report.match_intelligence or {}
        intelligence.setdefault("home", {"team_name": parsed_match.home_team_raw})
        intelligence.setdefault("away", {"team_name": parsed_match.away_team_raw})
        match_dt = report.match_data.match_date if report.match_data else report.query_timestamp
        recent = jingcai.get("recent_records") or {}
        future = jingcai.get("future_fixtures") or {}
        predicted = jingcai.get("predicted_lineups") or {}

        for side_name, team_name in (("home", parsed_match.home_team_raw), ("away", parsed_match.away_team_raw)):
            info = intelligence[side_name]
            records = self._team_mapping_value(recent, team_name) or []
            rest_days = self._rest_days_from_records(records, match_dt)
            if info.get("rest_days") is None and rest_days is not None:
                info["rest_days"] = rest_days
                info["rest_days_source"] = "500彩票网近期赛程"

            next_records = self._team_mapping_value(future, team_name) or []
            next_days = self._next_match_days(next_records, match_dt)
            if next_days is not None:
                info["next_match_days"] = next_days
                info["next_match_days_source"] = "500彩票网未来赛程"

            lineup = self._team_mapping_value(predicted, team_name)
            if isinstance(lineup, dict):
                starters = lineup.get("starting") or lineup.get("首发") or []
                if starters and not info.get("lineup"):
                    info["lineup"] = [{"player": player} for player in starters]
                    info["lineup_status"] = "predicted"
                    info["lineup_sources"] = ["500彩票网预计阵容"]
                absences = list(lineup.get("injuries") or []) + list(lineup.get("suspensions") or [])
                if absences and not info.get("injuries"):
                    info["injuries"] = [{"player": player, "reason": "500彩票网阵容页列为伤停/停赛"} for player in absences]
                    info["injury_status"] = "reported_injuries"
                    info["injury_sources"] = ["500彩票网预计阵容"]
                elif info.get("injury_status", "unknown") == "unknown":
                    info["injury_status"] = "reported_clear"
                    info["injury_sources"] = ["500彩票网预计阵容"]

        intelligence["schedule_density_note"] = self._schedule_density_note(
            intelligence["home"].get("rest_days"),
            intelligence["away"].get("rest_days"),
        )
        sources = intelligence.setdefault("data_sources", [])
        if any((intelligence[side].get("rest_days_source") or "").startswith("500") for side in ("home", "away")):
            sources.append("500彩票网赛程密度")
        if predicted:
            sources.append("500彩票网预计阵容")
        intelligence["data_sources"] = list(dict.fromkeys(sources))
        intelligence["intelligence_score"] = self._intelligence_coverage_score(intelligence)
        report.match_intelligence = intelligence

    def apply_llm_verified_intelligence(self, report: CompleteDataReport, llm_analysis: Dict[str, Any]):
        """只回写带来源的GPT结构化核验结果，并重新计算完整度。"""
        verified = (llm_analysis or {}).get("verified_intelligence") or {}
        sources = [str(url) for url in (verified.get("sources") or llm_analysis.get("web_sources") or []) if url]
        if not verified or not sources:
            return
        verified["sources"] = sources
        intelligence = report.match_intelligence or {}
        for side_name in ("home", "away"):
            update = verified.get(side_name) or {}
            target = intelligence.setdefault(side_name, {})
            injury_status = update.get("injury_status")
            if injury_status in {"confirmed_injuries", "confirmed_clear", "reported_injuries", "reported_clear"}:
                target["injury_status"] = injury_status
                target["injury_sources"] = sources
                absences = update.get("absences") or []
                if absences:
                    target["injuries"] = [
                        item if isinstance(item, dict) else {"player": str(item), "reason": "GPT联网核验"}
                        for item in absences
                    ]
            lineup_status = update.get("lineup_status")
            if lineup_status in {"official", "predicted"}:
                target["lineup_status"] = lineup_status
                target["lineup_sources"] = sources
            rest_days = update.get("rest_days")
            if isinstance(rest_days, int) and rest_days >= 0:
                target["rest_days"] = rest_days
                target["rest_days_source"] = "GPT联网核验"
        intelligence["gpt_verified"] = verified
        dynamics = verified.get("match_dynamics")
        if isinstance(dynamics, dict):
            intelligence["match_dynamics"] = dynamics
        intelligence.setdefault("data_sources", []).append("GPT-5.5 联网核验")
        intelligence["data_sources"] = list(dict.fromkeys(intelligence["data_sources"]))
        intelligence["intelligence_score"] = self._intelligence_coverage_score(intelligence)
        report.match_intelligence = intelligence
        weather_location = str(verified.get("weather_location") or "").strip()
        if verified.get("venue_confirmed") and weather_location and report.match_data:
            report.match_data.venue = {"city": weather_location, "source": "GPT联网核验"}
            try:
                self._collect_weather_context(report)
                if report.weather_context and "Weather" not in report.data_sources_used:
                    report.data_sources_used.append("Weather")
            except Exception as exc:
                report.data_warnings.append(f"GPT核验场地后的天气补抓失败: {exc}")
        if "GPT-5.5 联网核验" not in report.data_sources_used:
            report.data_sources_used.append("GPT-5.5 联网核验")
        self._assess_data_quality(report)

    @staticmethod
    def _team_mapping_value(mapping: Dict[str, Any], team_name: str) -> Any:
        if team_name in mapping:
            return mapping[team_name]
        for key, value in mapping.items():
            if team_name in str(key) or str(key) in team_name:
                return value
        return None

    def _rest_days_from_records(self, records: List[Dict[str, Any]], match_dt: datetime) -> Optional[int]:
        dates = []
        for record in records:
            raw = str(record.get("日期") or record.get("date") or record.get("比赛日期") or "")
            parsed = self._parse_record_date(raw, match_dt)
            if parsed and parsed.date() < match_dt.date():
                dates.append(parsed)
        return (match_dt.date() - max(dates).date()).days if dates else None

    def _next_match_days(self, records: List[Dict[str, Any]], match_dt: datetime) -> Optional[int]:
        dates = []
        for record in records:
            raw = str(record.get("日期") or record.get("date") or record.get("比赛日期") or "")
            parsed = self._parse_record_date(raw, match_dt)
            if parsed and parsed.date() > match_dt.date():
                dates.append(parsed)
        return (min(dates).date() - match_dt.date()).days if dates else None

    @staticmethod
    def _schedule_density_note(home_rest: Optional[int], away_rest: Optional[int]) -> Optional[str]:
        if home_rest is None and away_rest is None:
            return None
        if home_rest is not None and away_rest is not None:
            return f"主队休息 {home_rest} 天，客队休息 {away_rest} 天"
        return f"主队休息 {home_rest if home_rest is not None else '-'} 天，客队休息 {away_rest if away_rest is not None else '-'} 天"

    @staticmethod
    def _intelligence_coverage_score(intelligence: Dict[str, Any]) -> float:
        home = intelligence.get("home") or {}
        away = intelligence.get("away") or {}
        score = 0
        if home.get("rest_days") is not None and away.get("rest_days") is not None:
            score += 20
        if all((side.get("lineup_status") or "unknown") != "unknown" for side in (home, away)):
            score += 25
        if all((side.get("injury_status") or "unknown") != "unknown" for side in (home, away)):
            score += 25
        if home.get("tactical_tags") and away.get("tactical_tags"):
            score += 15
        if intelligence.get("web_evidence"):
            score += 15
        return float(min(100, score))

    @staticmethod
    def _source_note(sources: List[Any], limit: int = 3) -> str:
        unique = list(dict.fromkeys(str(source) for source in sources if source))
        if len(unique) <= limit:
            return "；".join(unique)
        return f"{'；'.join(unique[:limit])}；另有{len(unique) - limit}个来源"

    def _merge_web_intelligence(self, report: CompleteDataReport):
        if not report.match_intelligence:
            return
        intelligence = report.match_intelligence
        evidence = []
        injury_pattern = re.compile(r'\b(injur|doubt|suspend|lineup|fitness|rotation|miss)\w*\b', re.I)
        tactic_pattern = re.compile(r'\b(press|counter|possession|set[- ]piece|preview|tactic|formation)\w*\b', re.I)
        for result in report.web_search_results[:12]:
            text = f"{result.title} {result.snippet}"
            if injury_pattern.search(text) or tactic_pattern.search(text):
                evidence.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                })
        if evidence:
            intelligence.setdefault("web_evidence", []).extend(evidence)
            intelligence.setdefault("data_sources", []).append("Web Search")
            intelligence["data_sources"] = list(dict.fromkeys(intelligence["data_sources"]))
            intelligence["intelligence_score"] = min(100, (intelligence.get("intelligence_score") or 0) + 10)

    def _build_local_intelligence(self, report: CompleteDataReport, parsed_match: ParsedMatch) -> Dict[str, Any]:
        home_tags = self._infer_local_tactical_tags(report.home_stats)
        away_tags = self._infer_local_tactical_tags(report.away_stats)
        supplemental = self.supplemental_collector.collect(
            home_name=parsed_match.home_team_raw,
            away_name=parsed_match.away_team_raw,
            league=(report.jingcai_match or {}).get("league") or ((report.match_data.league or {}).get("name") if report.match_data else None),
            match_date=(report.jingcai_match or {}).get("match_date") or (report.match_data.match_date.strftime("%Y-%m-%d") if report.match_data else None),
        )
        tactical_notes = []
        if home_tags:
            tactical_notes.append(f"{parsed_match.home_team_raw}: {'、'.join(home_tags)}")
        if away_tags:
            tactical_notes.append(f"{parsed_match.away_team_raw}: {'、'.join(away_tags)}")
        sources = ["500彩票网近况推断"] if tactical_notes else []
        sources.extend(supplemental.data_sources)
        warnings = ["未提供 API-Football Key，伤停/首发/排名/赛程密度未补充"]
        warnings.extend(supplemental.warnings)
        return {
            "home": {
                "team_name": parsed_match.home_team_raw,
                "rest_days": None,
                "rest_days_source": None,
                "injuries": [],
                "injury_status": "unknown",
                "injury_sources": [],
                "lineup": [],
                "lineup_status": "unknown",
                "lineup_sources": [],
                "tactical_tags": home_tags,
                "clubelo_rating": supplemental.home.clubelo_rating,
                "clubelo_rank": supplemental.home.clubelo_rank,
                "fifa_rank": supplemental.home.fifa_rank,
                "market_value_eur": supplemental.home.market_value_eur,
                "supplemental_notes": supplemental.home.source_notes,
            },
            "away": {
                "team_name": parsed_match.away_team_raw,
                "rest_days": None,
                "rest_days_source": None,
                "injuries": [],
                "injury_status": "unknown",
                "injury_sources": [],
                "lineup": [],
                "lineup_status": "unknown",
                "lineup_sources": [],
                "tactical_tags": away_tags,
                "clubelo_rating": supplemental.away.clubelo_rating,
                "clubelo_rank": supplemental.away.clubelo_rank,
                "fifa_rank": supplemental.away.fifa_rank,
                "market_value_eur": supplemental.away.market_value_eur,
                "supplemental_notes": supplemental.away.source_notes,
            },
            "tactical_notes": tactical_notes,
            "supplemental_data": supplemental.to_dict(),
            "data_sources": list(dict.fromkeys(sources)),
            "warnings": list(dict.fromkeys(warnings)),
            "intelligence_score": min(45, (20 if tactical_notes else 0) + (15 if supplemental.data_sources else 0)),
        }

    @staticmethod
    def _infer_local_tactical_tags(stats: Optional[StatisticsData]) -> List[str]:
        if not stats or not stats.matches_played:
            return []
        gf_avg = stats.goals_for / stats.matches_played
        ga_avg = stats.goals_against / stats.matches_played
        tags = []
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
        return tags

    def _search_team(self, *team_names: str) -> Optional[TeamData]:
        """搜索球队"""
        for term in self._team_search_terms(*team_names):
            try:
                data, error = self._api_get('teams', {'search': term})
                if error:
                    print(f"⚠️ 搜索球队失败: {error}")
                    continue

                candidates = data.get('response') or []
                if candidates:
                    exclude_keywords = ['women', ' w ', ' u19', ' u21', ' u23', 'academy', ' ii', ' b']
                    filtered = []
                    for candidate in candidates:
                        name = candidate['team']['name'].lower()
                        if not any(keyword in f" {name} " for keyword in exclude_keywords):
                            filtered.append(candidate)
                    national = [c for c in filtered if (c.get('team') or {}).get('national')]
                    team_info = (national or filtered or candidates)[0]['team']
                    return TeamData(
                        team_id=team_info['id'],
                        name=team_info['name'],
                        name_zh=team_info.get('name_zh', team_info['name']),
                        country=team_info['country'],
                        founded=team_info.get('founded', 0) or 0,
                        logo=team_info.get('logo', '')
                    )
            except Exception as e:
                print(f"⚠️ 搜索球队失败: {e}")

        return None

    @staticmethod
    def _team_search_terms(*team_names: str) -> List[str]:
        terms = []
        for name in team_names:
            if not name:
                continue
            terms.extend(TEAM_API_ALIASES.get(name, []))
            terms.append(name)
        return list(dict.fromkeys([
            cleaned for term in terms
            for cleaned in [DataCollector._api_safe_search_term(term)]
            if cleaned
        ]))

    @staticmethod
    def _api_safe_search_term(term: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", term or "")
        return re.sub(r"\s+", " ", cleaned).strip()

    def _candidate_seasons(self) -> List[int]:
        """Return seasons to try, with current season first."""
        current = datetime.now().year
        return [current, current - 1, current - 2, current - 3]

    def _find_fixture_between_teams(
        self,
        home_team_id: int,
        away_team_id: int,
        report: CompleteDataReport,
        days_back: int = 30,
        days_forward: int = 90
    ) -> Optional[MatchData]:
        """Find a fixture involving both teams without using plan-limited next/last params."""
        today = datetime.now()
        date_from = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        date_to = (today + timedelta(days=days_forward)).strftime('%Y-%m-%d')

        for season in self._candidate_seasons():
            params = {
                'team': home_team_id,
                'season': season,
                'from': date_from,
                'to': date_to,
            }
            data, error = self._api_get('fixtures', params)
            if error:
                report.data_warnings.append(error)
                continue

            fixtures = data.get('response') or []
            matching = []
            for fixture in fixtures:
                teams = fixture.get('teams', {})
                home_id = teams.get('home', {}).get('id')
                away_id = teams.get('away', {}).get('id')
                if {home_id, away_id} == {home_team_id, away_team_id}:
                    matching.append(fixture)

            if matching:
                matching.sort(key=lambda item: item['fixture']['date'])
                return self._parse_fixture(matching[0])

        report.data_warnings.append("未找到双方在当前日期窗口内的 API-Football 赛程")
        return None

    def _parse_fixture(self, fixture: Dict) -> MatchData:
        """解析赛程数据"""
        fixture_info = fixture['fixture']
        teams = fixture['teams']
        league = fixture['league']

        # 解析主客队
        home_team = TeamData(
            team_id=teams['home']['id'],
            name=teams['home']['name'],
            name_zh=teams['home']['name'],
            country=league.get('country', ''),
            founded=0,
            logo=teams['home']['logo']
        )

        away_team = TeamData(
            team_id=teams['away']['id'],
            name=teams['away']['name'],
            name_zh=teams['away']['name'],
            country=league.get('country', ''),
            founded=0,
            logo=teams['away']['logo']
        )

        # 解析日期
        date_str = fixture_info['date']
        try:
            match_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            match_date = datetime.now()

        return MatchData(
            fixture_id=fixture_info['id'],
            match_date=match_date,
            timezone=fixture_info['timezone'],
            venue=fixture_info.get('venue', {}),
            home_team=home_team,
            away_team=away_team,
            league=league,
            status=fixture_info['status']['long'],
            referee=fixture_info.get('referee')
        )

    def _get_odds(self, fixture_id: int) -> List[OddsData]:
        """获取比赛赔率"""
        odds_list = []

        try:
            data, error = self._api_get('odds', {'fixture': fixture_id})
            if error:
                print(f"⚠️ 获取赔率失败: {error}")
                return odds_list

            for odds_payload in data.get('response') or []:
                for bookmaker_data in odds_payload.get('bookmakers', []):
                    bookmaker = bookmaker_data.get('name', 'Unknown')
                    parsed = OddsData(bookmaker=bookmaker, home_win=0, draw=0, away_win=0, timestamp=datetime.now())

                    for bet in bookmaker_data.get('bets', []):
                        values = {v.get('value'): self._safe_float(v.get('odd')) for v in bet.get('values', [])}
                        bet_name = bet.get('name', '').lower()

                        if bet_name in {'match winner', '1x2', 'fulltime result'}:
                            parsed.home_win = values.get('Home') or values.get('1') or 0
                            parsed.draw = values.get('Draw') or values.get('X') or 0
                            parsed.away_win = values.get('Away') or values.get('2') or 0
                        elif 'goals over/under' in bet_name or 'over/under' in bet_name:
                            parsed.over_25 = values.get('Over 2.5') or values.get('Over')
                            parsed.under_25 = values.get('Under 2.5') or values.get('Under')

                    if parsed.home_win and parsed.draw and parsed.away_win:
                        odds_list.append(parsed)
        except Exception as e:
            print(f"⚠️ 获取赔率失败: {e}")

        return odds_list

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_h2h(self, home_team_id: int, away_team_id: int, report: CompleteDataReport) -> List[Dict]:
        """Get head-to-head fixtures. Free plan does not support last, so fetch full allowed response."""
        data, error = self._api_get('fixtures/headtohead', {'h2h': f'{home_team_id}-{away_team_id}'})
        if error:
            report.data_warnings.append(error)
            return []
        return data.get('response') or []

    def _infer_league_and_season(self, report: CompleteDataReport, team_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Infer league/season from matched fixture, or latest API-accessible fixture."""
        if report.match_data:
            return report.match_data.league.get('id'), report.match_data.league.get('season')

        for season in self._candidate_seasons():
            data, error = self._api_get('fixtures', {'team': team_id, 'season': season})
            if error:
                report.data_warnings.append(error)
                continue
            fixtures = data.get('response') or []
            if fixtures:
                fixtures.sort(key=lambda item: item['fixture']['date'], reverse=True)
                league = fixtures[0].get('league', {})
                return league.get('id'), league.get('season') or season
        return None, None

    def _get_team_statistics(self, team_id: int, league_id: int, season: int) -> Optional[StatisticsData]:
        """Get team season statistics and convert them into model-ready averages."""
        data, error = self._api_get('teams/statistics', {
            'team': team_id,
            'league': league_id,
            'season': season,
        })
        if error:
            print(f"⚠️ 获取球队统计失败: {error}")
            return None

        stats = data.get('response') or {}
        fixtures = stats.get('fixtures', {})
        played = fixtures.get('played', {})
        wins = fixtures.get('wins', {})
        draws = fixtures.get('draws', {})
        losses = fixtures.get('loses', {})
        goals = stats.get('goals', {})
        goals_for = goals.get('for', {}).get('total', {})
        goals_against = goals.get('against', {}).get('total', {})
        total_played = played.get('total') or 0
        total_for = goals_for.get('total') or 0
        total_against = goals_against.get('total') or 0

        return StatisticsData(
            matches_played=total_played,
            wins=wins.get('total') or 0,
            draws=draws.get('total') or 0,
            losses=losses.get('total') or 0,
            goals_for=total_for,
            goals_against=total_against,
            xg=(total_for / total_played) if total_played else None,
            xga=(total_against / total_played) if total_played else None,
            clean_sheets=stats.get('clean_sheet', {}).get('total'),
            form=list(stats.get('form') or '')[-5:],
            source='API-Football teams/statistics',
            season=season,
        )

    def _collect_web_search_data(self, report: CompleteDataReport, parsed_match: ParsedMatch):
        """通过联网搜索收集数据"""
        print("   正在执行联网搜索...")

        home_search = self._best_search_name(parsed_match.home_team_raw, parsed_match.home_team_en)
        away_search = self._best_search_name(parsed_match.away_team_raw, parsed_match.away_team_en)
        search_queries = [
            f"{home_search} vs {away_search} football preview prediction",
            f"{home_search} {away_search} football head to head",
            f"{home_search} football injury news",
            f"{away_search} football injury news",
            f"{home_search} vs {away_search} football predicted lineups",
            f"{home_search} vs {away_search} football team news suspensions",
            f"{home_search} vs {away_search} football press conference rotation",
            f"{home_search} vs {away_search} football odds movement",
            f"{home_search} vs {away_search} football venue weather",
        ]

        results: List[WebSearchResult] = []
        for query in search_queries:
            results.extend(self._duckduckgo_search(query, max_results=3))

        seen = set()
        unique_results = []
        for result in results:
            if result.url in seen:
                continue
            seen.add(result.url)
            unique_results.append(result)

        report.web_search_results = unique_results[:10]
        report.web_search_available = bool(report.web_search_results)

        for result in report.web_search_results:
            text = f"{result.title} {result.snippet}"
            if re.search(r'\b(injur|doubt|suspend|lineup|fitness)\w*\b', text, re.I):
                report.injury_updates.setdefault('web_search', []).append(f"{result.title} - {result.url}")
            if re.search(r'\bpreview|prediction|analysis|form\b', text, re.I):
                report.expert_predictions.append(f"{result.title} - {result.url}")

    @staticmethod
    def _best_search_name(raw_name: str, english_name: str) -> str:
        for candidate in [english_name, *(TEAM_API_ALIASES.get(raw_name, [])), raw_name]:
            if candidate and re.search(r"[A-Za-z]", candidate):
                return candidate
        return raw_name

    def _duckduckgo_search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Best-effort no-key web search. Returns only real links, never fabricated content."""
        url = "https://html.duckduckgo.com/html/"
        try:
            response = self.session.get(
                url,
                params={'q': query},
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            return []

        html = response.text
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            re.S,
        )
        results = []
        for match in pattern.finditer(html):
            title = self._strip_html(match.group('title'))
            snippet = self._strip_html(match.group('snippet'))
            result_url = match.group('url')
            results.append(WebSearchResult(
                source='DuckDuckGo',
                title=title,
                url=result_url,
                snippet=snippet,
                relevance_score=0.5,
            ))
            if len(results) >= max_results:
                break
        if results:
            return results
        return self._bing_search(query, max_results=max_results)

    def _bing_search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Fallback no-key web search when DuckDuckGo HTML is throttled or changes markup."""
        try:
            response = self.session.get(
                "https://www.bing.com/search",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            return []

        blocks = re.findall(r'<li class="b_algo".*?</li>', response.text, re.S)
        results = []
        for block in blocks:
            link = re.search(r'<h2[^>]*>\s*<a[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>', block, re.S)
            if not link:
                continue
            snippet_match = re.search(r'<p[^>]*>(?P<snippet>.*?)</p>', block, re.S)
            results.append(WebSearchResult(
                source='Bing',
                title=self._strip_html(link.group('title')),
                url=self._clean_bing_url(link.group('url')),
                snippet=self._strip_html(snippet_match.group('snippet') if snippet_match else ''),
                relevance_score=0.45,
            ))
            if len(results) >= max_results:
                break
        return results

    @staticmethod
    def _clean_bing_url(value: str) -> str:
        url = html_lib.unescape(value)
        match = re.search(r"[?&]u=([^&]+)", url)
        if not match:
            return url
        encoded = match.group(1)
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        try:
            padded = encoded + "=" * (-len(encoded) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode()).decode("utf-8", errors="ignore")
            return decoded or url
        except Exception:
            return url

    @staticmethod
    def _strip_html(value: str) -> str:
        value = re.sub(r'<[^>]+>', '', value)
        return re.sub(r'\s+', ' ', html_lib.unescape(value)).strip()

    def _assess_data_quality(self, report: CompleteDataReport):
        """按来源可靠性加权，避免低质量来源把完整度机械堆到100。"""
        report.data_warnings = list(dict.fromkeys(report.data_warnings))
        intelligence = report.match_intelligence or {}
        home_info = intelligence.get("home") or {}
        away_info = intelligence.get("away") or {}
        jingcai = report.jingcai_match or {}
        breakdown: Dict[str, Dict[str, Any]] = {}

        def add(name: str, maximum: float, earned: float, status: str, source: str = ""):
            breakdown[name] = {
                "earned": round(min(maximum, max(0.0, earned)), 1),
                "max": maximum,
                "status": status,
                "source": source,
            }

        official_odds = bool(jingcai.get("no_handicap_odds") or jingcai.get("handicap_odds"))
        add("jingcai_odds", 20, 20 if official_odds else (14 if report.odds_data else 0),
            "official" if official_odds else ("fallback" if report.odds_data else "missing"),
            "500彩票网竞彩" if official_odds else ("欧赔/API fallback" if report.odds_data else ""))
        deep = bool(jingcai.get("average_europe_odds") and jingcai.get("asian_average"))
        add("deep_market", 15, 15 if deep else 0, "complete" if deep else "missing", "500彩票网欧赔/亚盘" if deep else "")
        form = bool(report.home_stats and report.away_stats)
        add("team_form", 15, 15 if form else 0, "complete" if form else "missing", "500彩票网/API-Football" if form else "")

        lineup_statuses = [home_info.get("lineup_status", "unknown"), away_info.get("lineup_status", "unknown")]
        if all(status == "official" for status in lineup_statuses):
            add("lineups", 15, 15, "official", self._source_note(home_info.get("lineup_sources", []) + away_info.get("lineup_sources", [])))
        elif all(status in {"official", "predicted"} for status in lineup_statuses):
            add("lineups", 15, 10.5, "predicted", self._source_note(home_info.get("lineup_sources", []) + away_info.get("lineup_sources", [])))
        else:
            add("lineups", 15, 0, "missing")

        injury_statuses = [home_info.get("injury_status", "unknown"), away_info.get("injury_status", "unknown")]
        injury_sources = home_info.get("injury_sources", []) + away_info.get("injury_sources", [])
        if all(status in {"confirmed_injuries", "confirmed_clear"} for status in injury_statuses):
            add("injuries", 10, 10, "confirmed", self._source_note(injury_sources))
        elif all(status != "unknown" for status in injury_statuses):
            earned = 8 if any("http" in str(source) or "GPT" in str(source) for source in injury_sources) else 5
            add("injuries", 10, earned, "reported", self._source_note(injury_sources))
        else:
            add("injuries", 10, 0, "missing")

        api_stats = bool(
            form and report.home_stats.source and report.away_stats.source
            and "API-Football" in f"{report.home_stats.source}{report.away_stats.source}"
        )
        add("technical_stats", 10, 10 if api_stats else (5 if form else 0),
            "detailed" if api_stats else ("basic" if form else "missing"),
            "API-Football" if api_stats else ("500彩票网基础赛果统计" if form else ""))
        weather = bool(report.weather_context and report.weather_context.get("temperature_c") is not None)
        venue = bool(report.weather_context and report.weather_context.get("location"))
        add("weather", 5, 5 if weather else (2 if venue else 0), "forecast" if weather else ("venue_only" if venue else "missing"),
            (report.weather_context or {}).get("source", ""))
        schedule = home_info.get("rest_days") is not None and away_info.get("rest_days") is not None
        add("schedule_density", 5, 5 if schedule else 0, "complete" if schedule else "missing",
            self._source_note([home_info.get("rest_days_source"), away_info.get("rest_days_source")]))
        gpt_verified = intelligence.get("gpt_verified") or {}
        gpt_sources = gpt_verified.get("sources") or []
        generic_web = bool(report.web_search_results or intelligence.get("web_evidence"))
        add("web_evidence", 5, 5 if gpt_sources else (2 if generic_web else 0),
            "verified" if gpt_sources else ("generic" if generic_web else "missing"),
            "GPT联网核验" if gpt_sources else ("项目联网搜索" if generic_web else ""))

        score = sum(item["earned"] for item in breakdown.values())
        missing = [name for name, item in breakdown.items() if item["earned"] == 0 and item["max"] >= 10]
        if missing:
            report.data_warnings.append(f"关键数据缺口: {', '.join(missing)}")
        report.data_completeness_breakdown = breakdown
        report.data_completeness_score = round(float(score), 1)

    def _filter_pre_match_jingcai_records(self, match: JingcaiMatch, match_dt: datetime, report: CompleteDataReport):
        """Remove target/future matches from recent and H2H records before model stats are built."""
        removed = 0
        removed_completed_target = False

        def keep(record: Dict[str, Any]) -> bool:
            nonlocal removed, removed_completed_target
            raw_date = str(record.get("日期") or record.get("date") or record.get("比赛日期") or "")
            record_dt = self._parse_record_date(raw_date, match_dt)
            if record.get("home_score") is None or record.get("away_score") is None:
                if record_dt and record_dt.date() >= match_dt.date():
                    removed += 1
                    return False
                return True
            if record_dt and record_dt.date() >= match_dt.date():
                removed += 1
                removed_completed_target = True
                return False
            return True

        match.h2h_records = [record for record in match.h2h_records if keep(record)]
        for key, records in list(match.recent_records.items()):
            match.recent_records[key] = [record for record in records if keep(record)]

        stats_from_records = getattr(self.jingcai_collector, "_stats_from_records", None)
        if removed_completed_target and callable(stats_from_records):
            match.home_stats = None
            match.away_stats = None
            match.home_home_stats = None
            match.away_away_stats = None
            if match.recent_records.get(match.home_team):
                match.home_stats = stats_from_records(match.home_team, match.recent_records[match.home_team], "all")
            if match.recent_records.get(match.away_team):
                match.away_stats = stats_from_records(match.away_team, match.recent_records[match.away_team], "all")
            if match.recent_records.get(f"{match.home_team}_home"):
                match.home_home_stats = stats_from_records(match.home_team, match.recent_records[f"{match.home_team}_home"], "home")
            if match.recent_records.get(f"{match.away_team}_away"):
                match.away_away_stats = stats_from_records(match.away_team, match.recent_records[f"{match.away_team}_away"], "away")
            report.data_warnings.append("检测到目标比赛已完赛数据；仅使用过滤后可重建的赛前统计")
        if removed:
            report.data_warnings.append(f"赛前防泄漏过滤: 已排除 {removed} 条目标比赛/未来/无比分记录")

    @staticmethod
    def _parse_record_date(value: str, anchor: datetime) -> Optional[datetime]:
        cleaned = value.strip()
        for fmt in ("%Y-%m-%d", "%y-%m-%d", "%Y/%m/%d", "%m-%d"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                if fmt == "%m-%d":
                    parsed = parsed.replace(year=anchor.year)
                return parsed
            except ValueError:
                continue
        return None


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'TeamData',
    'MatchData',
    'OddsData',
    'StatisticsData',
    'WebSearchResult',
    'CompleteDataReport',
    'DataCollector',
]
