#!/usr/bin/env python3
"""500彩票网竞彩足球数据采集器。

用于中国竞彩分析场景。主数据来自 500 网页：
- 竞彩足球胜平负/让球胜平负列表页
- 单场数据分析页（近况、交锋、欧赔均值、亚盘均值）

注意：这不是官方 API，页面结构变化时需要更新解析逻辑。
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException
from bs4 import BeautifulSoup

from core.data_sources.fivehundred_trade import TradeTableMatch, find_trade_match
from core.data_sources.jleague_docx_supplement import load_jleague_docx_supplement


@dataclass
class JingcaiOdds:
    home_win: float
    draw: float
    away_win: float
    source: str
    updated_at: Optional[str] = None


@dataclass
class JingcaiTeamStats:
    team_name: str
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    win_rate: Optional[float] = None
    handicap_win_rate: Optional[float] = None
    over_rate: Optional[float] = None
    form: List[str] = field(default_factory=list)
    source: str = "500彩票网"
    scope: str = "all"


@dataclass
class JingcaiMatch:
    fixture_id: str
    match_num: str
    league: str
    home_team: str
    away_team: str
    match_date: str
    match_time: str
    handicap: Optional[int]
    no_handicap_odds: Optional[JingcaiOdds]
    handicap_odds: Optional[JingcaiOdds]
    analysis_url: str
    europe_url: str
    asian_url: str
    average_europe_odds: Optional[JingcaiOdds] = None
    opening_average_europe_odds: Optional[JingcaiOdds] = None
    asian_average: Optional[Dict[str, Any]] = None
    europe_market: Optional[Dict[str, Any]] = None
    asian_market: Optional[Dict[str, Any]] = None
    handicap_market: Optional[Dict[str, Any]] = None
    score_market: Optional[Dict[str, Any]] = None
    mixed_market: Optional[Dict[str, Any]] = None
    home_stats: Optional[JingcaiTeamStats] = None
    away_stats: Optional[JingcaiTeamStats] = None
    home_home_stats: Optional[JingcaiTeamStats] = None
    away_away_stats: Optional[JingcaiTeamStats] = None
    fifa_rankings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    league_standings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    h2h_records: List[Dict[str, Any]] = field(default_factory=list)
    h2h_summary: Optional[str] = None
    recent_records: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    future_fixtures: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    predicted_lineups: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    macau_recommendation: Optional[Dict[str, Any]] = None
    recommendation_text: Optional[str] = None
    raw_recent_tables: List[str] = field(default_factory=list)
    docx_supplement: Optional[Dict[str, Any]] = None


class Jingcai500Collector:
    """500彩票网竞彩数据采集器。"""

    TRADE_URL = "https://trade.500.com/jczq/?playid=269&g=2"
    DATE_TRADE_URL = "https://trade.500.com/jczq/index.php?date={match_date}&playid=312"
    MIXED_TRADE_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2&date={match_date}"
    ANALYSIS_URL = "https://odds.500.com/fenxi/shuju-{fixture_id}.shtml"
    EUROPE_URL = "https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml"
    ASIAN_URL = "https://odds.500.com/fenxi/yazhi-{fixture_id}.shtml"
    HANDICAP_URL = "https://odds.500.com/fenxi/rangqiu-{fixture_id}.shtml?lot=jczq"
    SCORE_URL = "https://odds.500.com/fenxi/bifen-{fixture_id}.shtml"
    NAVIGATION_SEED_FIXTURES = ["1412367"]

    TEAM_ALIASES = {
        "清水鼓动": ["清水鼓动", "清水心跳"],
        "清水心跳": ["清水鼓动", "清水心跳"],
        "横滨水手": ["横滨水手"],
        "神户胜利": ["神户胜利", "神户胜利船", "神户"],
        "神户胜利船": ["神户胜利", "神户胜利船", "神户"],
        "町田泽维": ["町田泽维", "町田泽维亚", "町田"],
        "町田泽维亚": ["町田泽维", "町田泽维亚", "町田"],
        "名古屋鲸": ["名古屋鲸", "名古屋鲸鱼", "名古屋"],
        "名古屋鲸鱼": ["名古屋鲸", "名古屋鲸鱼", "名古屋"],
        "京都": ["京都", "京都不死鸟"],
        "京都不死鸟": ["京都", "京都不死鸟"],
        "鹿岛": ["鹿岛", "鹿岛鹿角"],
        "鹿岛鹿角": ["鹿岛", "鹿岛鹿角"],
        "浦和": ["浦和", "浦和红钻"],
        "浦和红钻": ["浦和", "浦和红钻"],
        "冈山": ["冈山", "冈山绿雉"],
        "冈山绿雉": ["冈山", "冈山绿雉"],
        "横滨": ["横滨", "横滨水手"],
        "横滨水手": ["横滨", "横滨水手"],
        "清水": ["清水", "清水鼓动", "清水心跳"],
        "川崎": ["川崎", "川崎前锋"],
        "川崎前锋": ["川崎", "川崎前锋"],
        "广岛": ["广岛", "广岛三箭"],
        "广岛三箭": ["广岛", "广岛三箭"],
    }

    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://trade.500.com/",
        })

    def find_match(
        self,
        home_team: str,
        away_team: str,
        match_date: Optional[str] = None,
        match_time: Optional[str] = None,
    ) -> Optional[JingcaiMatch]:
        """从竞彩列表页或 500 单场导航中查找比赛，并补充深层数据。"""
        for url in self._candidate_trade_urls(match_date):
            try:
                html = self._fetch_text(url)
            except RequestException:
                continue
            match = self._find_match_in_trade_html(html, home_team, away_team, match_date, match_time)
            if match:
                self.enrich_match(match)
                return match

        match = self._find_match_from_navigation(home_team, away_team, match_date, match_time)
        if match:
            self.enrich_match(match)
            return match

        return None

    def enrich_match(self, match: JingcaiMatch) -> JingcaiMatch:
        """抓取分析页、欧赔页、亚盘页并填充数据。"""
        try:
            analysis_html = self._fetch_text(match.analysis_url, referer=self.TRADE_URL)
            self._parse_analysis_page(match, analysis_html)
        except requests.RequestException:
            pass

        try:
            europe_html = self._fetch_text(match.europe_url, referer=match.analysis_url)
            self._parse_europe_page(match, europe_html)
        except requests.RequestException:
            pass

        try:
            asian_html = self._fetch_text(match.asian_url, referer=match.analysis_url)
            self._parse_asian_page(match, asian_html)
        except requests.RequestException:
            pass

        try:
            handicap_url = self.HANDICAP_URL.format(fixture_id=match.fixture_id)
            handicap_html = self._fetch_text(handicap_url, referer=match.analysis_url)
            self._parse_handicap_page(match, handicap_html)
        except requests.RequestException:
            pass

        try:
            score_url = self.SCORE_URL.format(fixture_id=match.fixture_id)
            score_html = self._fetch_text(score_url, referer=match.analysis_url)
            self._parse_score_page(match, score_html)
        except requests.RequestException:
            pass

        self._enrich_trade_page_table(match)
        self._apply_jleague_docx_supplement(match)
        return match

    def _enrich_trade_page_table(self, match: JingcaiMatch):
        """补充 500 主表格中的三向表、让球方向、比分、总球和半全场表格数值。"""
        trade_match = find_trade_match(
            home_team=match.home_team,
            away_team=match.away_team,
            match_date=match.match_date or None,
            match_time=match.match_time or None,
            fixture_id=match.fixture_id,
            session=self.session,
            timeout=self.timeout,
        )
        if trade_match:
            self._apply_trade_table_match(match, trade_match)

    def _apply_trade_table_match(self, match: JingcaiMatch, trade_match: TradeTableMatch):
        if trade_match.result_3way and not match.no_handicap_odds:
            match.no_handicap_odds = JingcaiOdds(
                trade_match.result_3way["home"],
                trade_match.result_3way["draw"],
                trade_match.result_3way["away"],
                source="500彩票网主表三向表",
                updated_at=trade_match.fetch_time,
            )
        if trade_match.handicap_3way:
            if match.handicap is None:
                match.handicap = self._safe_int(trade_match.handicap_3way.get("handicap"))
            if not match.handicap_odds:
                match.handicap_odds = JingcaiOdds(
                    trade_match.handicap_3way["home"],
                    trade_match.handicap_3way["draw"],
                    trade_match.handicap_3way["away"],
                    source="500彩票网主表让球方向",
                    updated_at=trade_match.fetch_time,
                )

        score_odds = {
            str(item["score"]).replace(":", "-"): float(item["value"])
            for item in trade_match.score_table
            if item.get("score") and item.get("value") is not None
        }
        mixed = {
            "source": trade_match.source,
            "fixture_id": trade_match.match_id or match.fixture_id,
            "updated_at": trade_match.fetch_time,
            "score_odds": score_odds,
            "total_goals_odds": trade_match.total_goals_table,
            "half_full_odds": trade_match.half_full_table,
            "availability": trade_match.sale_status,
            "local_supplement": trade_match.local_supplement,
            "source_url": trade_match.source_url,
        }
        existing_mixed = match.mixed_market or {}
        match.mixed_market = {
            **mixed,
            "score_odds": existing_mixed.get("score_odds") or mixed["score_odds"],
            "total_goals_odds": existing_mixed.get("total_goals_odds") or mixed["total_goals_odds"],
            "half_full_odds": existing_mixed.get("half_full_odds") or mixed["half_full_odds"],
        }

        score_market = match.score_market or {
            "source": "500彩票网比分指数",
            "company_count": 0,
            "records": [],
            "warnings": [],
        }
        if score_odds and not score_market.get("jingcai_score_odds"):
            score_market["jingcai_score_odds"] = score_odds
            score_market["jingcai_score_implied"] = self._normalized_implied_odds(score_odds)
            score_market["jingcai_top_scores"] = sorted(score_odds.items(), key=lambda item: item[1])[:8]
            score_market["warnings"] = [
                warning for warning in (score_market.get("warnings") or [])
                if "比分指数" not in warning
            ]
        if trade_match.local_supplement:
            score_market["local_supplement"] = True
        match.score_market = score_market

    def _apply_jleague_docx_supplement(self, match: JingcaiMatch):
        supplement = load_jleague_docx_supplement(
            fixture_id=match.fixture_id,
            home_team=match.home_team,
            away_team=match.away_team,
        )
        if not supplement:
            return
        match.docx_supplement = supplement

        official = supplement.get("official_odds") or {}
        result_3way = official.get("result_3way") or {}
        if self._has_triplet(result_3way):
            match.no_handicap_odds = JingcaiOdds(
                result_3way["home"],
                result_3way["draw"],
                result_3way["away"],
                source="DOCX补充-中国竞彩网官方三向表",
                updated_at=(supplement.get("_source_meta") or {}).get("fetch_time"),
            )
        handicap_3way = official.get("handicap_3way") or {}
        if self._has_triplet(handicap_3way):
            if match.handicap is None:
                match.handicap = self._safe_int(handicap_3way.get("handicap"))
            match.handicap_odds = JingcaiOdds(
                handicap_3way["home"],
                handicap_3way["draw"],
                handicap_3way["away"],
                source="DOCX补充-中国竞彩网让球方向",
                updated_at=(supplement.get("_source_meta") or {}).get("fetch_time"),
            )

        europe = supplement.get("europe_average") or {}
        current = europe.get("current") or {}
        opening = europe.get("opening") or {}
        if self._has_triplet(current):
            match.average_europe_odds = JingcaiOdds(
                current["home"],
                current["draw"],
                current["away"],
                source="DOCX补充-500百家欧赔即时均值",
                updated_at=(supplement.get("_source_meta") or {}).get("fetch_time"),
            )
        if self._has_triplet(opening):
            match.opening_average_europe_odds = JingcaiOdds(
                opening["home"],
                opening["draw"],
                opening["away"],
                source="DOCX补充-500百家欧赔初始均值",
                updated_at=(supplement.get("_source_meta") or {}).get("fetch_time"),
            )

        self._merge_docx_injury_notes(match, supplement)
        self._merge_docx_records_and_notes(match, supplement)

    def _merge_docx_injury_notes(self, match: JingcaiMatch, supplement: Dict[str, Any]):
        notes = supplement.get("injury_notes") or []
        if not notes:
            return
        lineups = match.predicted_lineups or {}
        for note in notes:
            team, detail = self._split_team_note(note)
            if not team:
                continue
            target_team = self._resolve_docx_team_key(match, team)
            if not target_team:
                continue
            lineups.setdefault(target_team, {}).setdefault("injuries", [])
            if detail and detail not in lineups[target_team]["injuries"]:
                lineups[target_team]["injuries"].append(detail)
        match.predicted_lineups = lineups

    def _merge_docx_records_and_notes(self, match: JingcaiMatch, supplement: Dict[str, Any]):
        if supplement.get("h2h_summary"):
            match.h2h_summary = supplement["h2h_summary"]
        if supplement.get("h2h_records"):
            match.h2h_records = supplement["h2h_records"][:12]
        notes = []
        for key in ("market_notes", "context_notes", "recent_notes", "injury_notes"):
            notes.extend(supplement.get(key) or [])
        if notes:
            prefix = "DOCX补充: "
            existing = match.recommendation_text or ""
            match.recommendation_text = existing or prefix + "；".join(notes[:6])

    @staticmethod
    def _split_team_note(note: str) -> tuple[str, str]:
        if "：" in note:
            team, detail = note.split("：", 1)
        elif ":" in note:
            team, detail = note.split(":", 1)
        else:
            return "", note
        return team.strip(), detail.strip()

    def _resolve_docx_team_key(self, match: JingcaiMatch, team: str) -> Optional[str]:
        if self._team_matches(team, match.home_team):
            return match.home_team
        if self._team_matches(team, match.away_team):
            return match.away_team
        for key in (match.predicted_lineups or {}).keys():
            if self._team_matches(team, key):
                return key
        return None

    @staticmethod
    def _has_triplet(values: Dict[str, Any]) -> bool:
        return all(values.get(key) is not None for key in ("home", "draw", "away"))

    def _parse_mixed_trade_row(self, row) -> Dict[str, Any]:
        markets = {"bf": {}, "jqs": {}, "bqc": {}}
        # 500 的更多玩法位于比赛行之后的隐藏兄弟行，而不是比赛行子节点。
        more_row = row.find_next_sibling("tr", class_="bet-more-wrap")
        container = more_row or row
        for button in container.select("p.sbetbtn[data-type][data-value][data-sp]"):
            market_type = button.get("data-type")
            if market_type not in markets:
                continue
            odd = self._safe_float(button.get("data-sp"))
            value = (button.get("data-value") or "").strip()
            if value and odd:
                markets[market_type][value.replace(":", "-")] = odd
        return {
            "source": "500彩票网混合过关",
            "fixture_id": row.get("data-fixtureid"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "score_odds": markets["bf"],
            "total_goals_odds": markets["jqs"],
            "half_full_odds": markets["bqc"],
            "availability": row.get("data-subactive", ""),
        }

    @staticmethod
    def _normalized_implied_odds(odds: Dict[str, float]) -> Dict[str, float]:
        raw = {key: 1 / odd for key, odd in odds.items() if odd and odd > 1}
        total = sum(raw.values())
        return {key: value / total for key, value in raw.items()} if total else {}

    def _candidate_trade_urls(self, match_date: Optional[str]) -> List[str]:
        urls = [self.TRADE_URL]
        if match_date:
            urls.append(self.DATE_TRADE_URL.format(match_date=match_date))
        return list(dict.fromkeys(urls))

    def _find_match_in_trade_html(
        self,
        html: str,
        home_team: str,
        away_team: str,
        match_date: Optional[str],
        match_time: Optional[str],
    ) -> Optional[JingcaiMatch]:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("tr.bet-tb-tr"):
            home = row.get("data-homesxname", "")
            away = row.get("data-awaysxname", "")
            if not self._team_matches(home, home_team) or not self._team_matches(away, away_team):
                continue
            if match_date and row.get("data-matchdate") != match_date:
                continue
            if match_time and row.get("data-matchtime") != match_time:
                continue
            return self._parse_match_row(row)
        return None

    def _find_match_from_navigation(
        self,
        home_team: str,
        away_team: str,
        match_date: Optional[str],
        match_time: Optional[str],
    ) -> Optional[JingcaiMatch]:
        """Use 500 same-issue navigation links to discover fixture ids missing from trade pages."""
        for fixture_id in self._navigation_seed_fixture_ids(match_date):
            url = self.ANALYSIS_URL.format(fixture_id=fixture_id)
            try:
                html = self._fetch_text(url, referer=self.TRADE_URL)
            except RequestException:
                continue
            candidate = self._parse_navigation_match(html, home_team, away_team, match_date, match_time)
            if candidate:
                return candidate
        return None

    def _navigation_seed_fixture_ids(self, match_date: Optional[str]) -> List[str]:
        seed_ids: List[str] = []
        for url in self._candidate_trade_urls(match_date):
            try:
                html = self._fetch_text(url)
            except RequestException:
                continue
            soup = BeautifulSoup(html, "html.parser")
            for row in soup.select("tr.bet-tb-tr"):
                fixture_id = row.get("data-fixtureid")
                if fixture_id:
                    seed_ids.append(fixture_id)
        seed_ids.extend(self.NAVIGATION_SEED_FIXTURES)
        return list(dict.fromkeys(seed_ids))

    def _parse_navigation_match(
        self,
        html: str,
        home_team: str,
        away_team: str,
        match_date: Optional[str],
        match_time: Optional[str],
    ) -> Optional[JingcaiMatch]:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link.get("href") or ""
            fixture = re.search(r"shuju-(\d+)\.shtml", href)
            if not fixture:
                continue
            left = link.select_one("em.l")
            right = link.select_one("em.r")
            home = left.get_text(" ", strip=True) if left else ""
            away = right.get_text(" ", strip=True) if right else ""
            if not home or not away:
                text = link.get_text(" ", strip=True)
                parts = re.split(r"\s+(?:VS|\d+\s*:\s*\d+)\s+", text)
                if len(parts) >= 2:
                    home, away = parts[0], parts[-1]
            if not self._team_matches(home, home_team) or not self._team_matches(away, away_team):
                continue
            match_num = self._match_num_near_navigation_link(link)
            fixture_id = fixture.group(1)
            return JingcaiMatch(
                fixture_id=fixture_id,
                match_num=match_num,
                league="",
                home_team=home,
                away_team=away,
                match_date=match_date or "",
                match_time=match_time or "",
                handicap=None,
                no_handicap_odds=None,
                handicap_odds=None,
                analysis_url=self.ANALYSIS_URL.format(fixture_id=fixture_id),
                europe_url=self.EUROPE_URL.format(fixture_id=fixture_id),
                asian_url=self.ASIAN_URL.format(fixture_id=fixture_id),
            )
        return None

    @staticmethod
    def _match_num_near_navigation_link(link) -> str:
        row = link.find_parent("tr")
        if not row:
            return ""
        text = row.get_text(" ", strip=True)
        match = re.search(r"(周[一二三四五六日]\d{3})", text)
        return match.group(1) if match else ""

    def _fetch_text(self, url: str, referer: Optional[str] = None) -> str:
        headers = {}
        if referer:
            headers["Referer"] = referer

        urls = [url]
        if url.startswith("https://"):
            urls.append("http://" + url[len("https://"):])

        last_error: Optional[Exception] = None
        for attempt in range(3):
            for candidate in urls:
                try:
                    response = self.session.get(candidate, headers=headers, timeout=self.timeout)
                    response.raise_for_status()
                    return response.content.decode("gb18030", errors="ignore")
                except RequestException as exc:
                    last_error = exc
            time.sleep(0.8 * (attempt + 1))

        if last_error:
            raise last_error
        raise RuntimeError(f"无法获取页面: {url}")

    def _parse_match_row(self, row) -> JingcaiMatch:
        fixture_id = row.get("data-fixtureid", "")
        buttons = row.select("p.betbtn")
        no_handicap = self._parse_button_odds(buttons, "nspf")
        handicap = self._parse_button_odds(buttons, "spf")

        raw_handicap = row.get("data-rangqiu")
        try:
            handicap_value = int(raw_handicap) if raw_handicap not in (None, "") else None
        except ValueError:
            handicap_value = None

        return JingcaiMatch(
            fixture_id=fixture_id,
            match_num=row.get("data-matchnum", ""),
            league=row.get("data-simpleleague", ""),
            home_team=row.get("data-homesxname", ""),
            away_team=row.get("data-awaysxname", ""),
            match_date=row.get("data-matchdate", ""),
            match_time=row.get("data-matchtime", ""),
            handicap=handicap_value,
            no_handicap_odds=JingcaiOdds(*no_handicap, source="500彩票网竞彩胜平负") if no_handicap else None,
            handicap_odds=JingcaiOdds(*handicap, source="500彩票网竞彩让球胜平负") if handicap else None,
            analysis_url=self.ANALYSIS_URL.format(fixture_id=fixture_id),
            europe_url=self.EUROPE_URL.format(fixture_id=fixture_id),
            asian_url=self.ASIAN_URL.format(fixture_id=fixture_id),
        )

    @staticmethod
    def _parse_button_odds(buttons, odds_type: str) -> Optional[tuple]:
        values = {}
        for button in buttons:
            if button.get("data-type") != odds_type:
                continue
            values[button.get("data-value")] = Jingcai500Collector._safe_float(button.get("data-sp"))

        if all(values.get(key) for key in ["3", "1", "0"]):
            return values["3"], values["1"], values["0"]
        return None

    def _parse_analysis_page(self, match: JingcaiMatch, html: str):
        soup = BeautifulSoup(html, "html.parser")
        table_texts = [table.get_text(" ", strip=True) for table in soup.find_all("table")]

        self._parse_header_info(match, soup)
        self._parse_fifa_rankings(match, soup)
        self._parse_standings(match, soup)
        self._parse_h2h_records(match, soup)
        self._parse_recent_records(match, soup)
        self._parse_future_fixtures(match, soup)
        self._parse_predicted_lineups(match, soup)
        self._parse_macau_recommendation(match, soup)

        recent_tables = []
        for text in table_texts:
            if "近10场" in text and ("进" in text and "失" in text):
                recent_tables.append(text)

        match.raw_recent_tables = recent_tables[:4]
        if recent_tables:
            match.home_stats = self._parse_recent_summary(recent_tables[0], match.home_team, "all")
        if len(recent_tables) > 1:
            match.away_stats = self._parse_recent_summary(recent_tables[1], match.away_team, "all")
        if len(recent_tables) > 2:
            match.home_home_stats = self._parse_recent_summary(recent_tables[2], match.home_team, "home")
        if len(recent_tables) > 3:
            match.away_away_stats = self._parse_recent_summary(recent_tables[3], match.away_team, "away")

        home_split_candidates = []
        away_split_candidates = []
        for table in soup.find_all("table"):
            home_split = self._parse_detail_record_table(table, match.home_team, "home", expected_side="home")
            away_split = self._parse_detail_record_table(table, match.away_team, "away", expected_side="away")
            if home_split:
                home_split_candidates.append(home_split)
            if away_split:
                away_split_candidates.append(away_split)
        if home_split_candidates:
            match.home_home_stats = max(home_split_candidates, key=lambda item: item.matches_played)
        if away_split_candidates:
            match.away_away_stats = max(away_split_candidates, key=lambda item: item.matches_played)
        if not match.home_stats and match.recent_records.get(match.home_team):
            match.home_stats = self._stats_from_records(match.home_team, match.recent_records[match.home_team], "all")
        if not match.away_stats and match.recent_records.get(match.away_team):
            match.away_stats = self._stats_from_records(match.away_team, match.recent_records[match.away_team], "all")
        if not match.home_home_stats and match.recent_records.get(f"{match.home_team}_home"):
            match.home_home_stats = self._stats_from_records(match.home_team, match.recent_records[f"{match.home_team}_home"], "home")
        if not match.away_away_stats and match.recent_records.get(f"{match.away_team}_away"):
            match.away_away_stats = self._stats_from_records(match.away_team, match.recent_records[f"{match.away_team}_away"], "away")

        for text in table_texts:
            if "对赛成绩" in text or ("清水" in text and "横滨" in text and "近况走势" in text):
                h2h_match = re.search(r"对赛成绩\s*-\s*(.+?\d+胜\d+和\d+负)", text)
                if h2h_match:
                    match.h2h_summary = h2h_match.group(1).strip()
                rec_match = re.search(r"推介\s*-\s*(.+?)(?:\s+对赛成绩|$)", text)
                if rec_match:
                    match.recommendation_text = rec_match.group(1).strip()

        if match.macau_recommendation:
            match.recommendation_text = match.macau_recommendation.get("pick") or match.recommendation_text

    def _parse_header_info(self, match: JingcaiMatch, soup: BeautifulSoup):
        header = soup.select_one(".odds_header") or soup.select_one(".odds_hd_cont")
        text = header.get_text(" ", strip=True) if header else (soup.title.get_text(" ", strip=True) if soup.title else "")
        time_match = re.search(r"比赛时间\s*(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})", text)
        if time_match:
            match.match_date = match.match_date or time_match.group(1)
            match.match_time = match.match_time or time_match.group(2)
        league_match = re.search(r"\((\d{4}[^)]+)\)", soup.title.get_text(" ", strip=True) if soup.title else "")
        if league_match and not match.league:
            match.league = league_match.group(1).replace("2026", "").strip() or league_match.group(1)

    def _parse_fifa_rankings(self, match: JingcaiMatch, soup: BeautifulSoup):
        """Parse FIFA ranking blocks near the page header."""
        rankings: Dict[str, List[Dict[str, Any]]] = {}
        for title in soup.select("h3.lslayout1_stit"):
            team_label = title.get_text(" ", strip=True)
            team_name = re.sub(r"\[.*?\]", "", team_label).strip()
            if not team_name:
                continue
            table = title.find_next("table")
            if not table:
                continue
            rows = self._table_rows(table)
            if len(rows) < 2 or "世界排名" not in " ".join(rows[0]):
                continue
            rankings[team_name] = self._rows_to_dicts(rows)
        match.fifa_rankings = rankings

    def _parse_standings(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = self._find_box(soup, title_contains="赛前联赛积分排名")
        if not box:
            return
        teams = [node.get_text(" ", strip=True).replace("[", " [") for node in box.select(".team_name")]
        tables = box.find_all("table")
        standings: Dict[str, List[Dict[str, Any]]] = {}
        for idx, table in enumerate(tables[:2]):
            team = self._clean_team_label(teams[idx]) if idx < len(teams) else (match.home_team if idx == 0 else match.away_team)
            rows = self._table_rows(table)
            parsed = self._rows_to_dicts(rows)
            if parsed:
                standings[team] = parsed
        match.league_standings = standings

    def _parse_h2h_records(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = soup.find(id="team_jiaozhan") or self._find_box(soup, class_contains="history")
        if not box:
            return
        title = box.select_one(".M_title")
        if title:
            title_text = title.get_text(" ", strip=True)
            summary = re.search(r"双方近\s*\d+\s*次交战，(.+)", title_text)
            if summary:
                match.h2h_summary = summary.group(1).strip()
        table = box.find("table")
        records = self._parse_match_rows(table) if table else []
        match.h2h_records = records[:12]

    def _parse_recent_records(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = self._find_box(soup, class_contains="record")
        if not box:
            return
        team_tables = []
        for table in box.find_all("table"):
            rows = self._table_rows(table)
            if rows and "盘口" in " ".join(rows[0]) and "主队" in " ".join(rows[0]):
                team_tables.append(table)
        if len(team_tables) >= 1:
            match.recent_records[match.home_team] = self._parse_match_rows(team_tables[0])[:10]
        if len(team_tables) >= 2:
            match.recent_records[match.away_team] = self._parse_match_rows(team_tables[1])[:10]
        if len(team_tables) >= 3:
            match.recent_records[f"{match.home_team}_home"] = self._parse_match_rows(team_tables[-2])[:10]
        if len(team_tables) >= 4:
            match.recent_records[f"{match.away_team}_away"] = self._parse_match_rows(team_tables[-1])[:10]

    def _parse_future_fixtures(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = self._find_box(soup, title_contains="未来赛事")
        if not box:
            return
        teams = [self._clean_team_label(node.get_text(" ", strip=True)) for node in box.select(".team_name")]
        fixtures: Dict[str, List[Dict[str, Any]]] = {}
        for idx, table in enumerate(box.find_all("table")[:2]):
            team = teams[idx] if idx < len(teams) else (match.home_team if idx == 0 else match.away_team)
            fixtures[team] = self._parse_future_table(table)
        match.future_fixtures = fixtures

    def _parse_predicted_lineups(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = self._find_box(soup, class_contains="starting")
        if not box:
            return
        teams = [self._clean_team_label(node.get_text(" ", strip=True).replace("阵型:", "")) for node in box.select(".team_name")]
        lineups: Dict[str, Dict[str, List[str]]] = {}
        for idx, table in enumerate(box.find_all("table")[:2]):
            team = teams[idx] if idx < len(teams) and teams[idx] else (match.home_team if idx == 0 else match.away_team)
            lineups[team] = self._parse_lineup_table(table)
        match.predicted_lineups = lineups

    def _parse_macau_recommendation(self, match: JingcaiMatch, soup: BeautifulSoup):
        box = self._find_box(soup, class_contains="recommend")
        table = box.find("table") if box else None
        if not table:
            return
        rows = self._table_rows(table)
        pick = ""
        h2h = ""
        reason = ""
        form: Dict[str, Dict[str, str]] = {}
        for row in rows:
            joined = " ".join(row)
            if "近况走势" in joined and row:
                form[row[0].replace("(主)", "").strip()] = {
                    "form": row[1].replace("近况走势 -", "").strip() if len(row) > 1 else "",
                    "handicap_form": row[2].replace("盘路赢输 -", "").strip() if len(row) > 2 else "",
                }
            if "推介" in joined:
                pick_match = re.search(r"推介\s*-\s*(.+?)(?:\s+对赛成绩|$)", joined)
                h2h_match = re.search(r"对赛成绩\s*-\s*(.+)$", joined)
                pick = pick_match.group(1).strip() if pick_match else pick
                h2h = h2h_match.group(1).strip() if h2h_match else h2h
            elif row and len(row) == 1 and not row[0].startswith("("):
                reason = row[0].strip()
        match.macau_recommendation = {
            "pick": pick,
            "h2h": h2h,
            "reason": reason,
            "form": form,
            "source": "500彩票网澳门心水推荐",
        }

    def _parse_europe_page(self, match: JingcaiMatch, html: str):
        soup = BeautifulSoup(html, "html.parser")
        current = self._extract_values_by_ids(soup, ["avwinc2", "avdrawc2", "avlostc2"])
        opening = self._extract_values_by_ids(soup, ["avwinj2", "avdrawj2", "avlostj2"])
        if current:
            match.average_europe_odds = JingcaiOdds(*current, source="500彩票网百家欧赔即时均值")
        if opening:
            match.opening_average_europe_odds = JingcaiOdds(*opening, source="500彩票网百家欧赔初始均值")
        match.europe_market = self._parse_europe_like_market(
            soup,
            source="500彩票网百家欧赔",
            market_type="europe",
        )
        average = ((match.europe_market or {}).get("stats") or {}).get("average") or {}
        if not match.average_europe_odds and average.get("current_odds"):
            odds = average["current_odds"]
            match.average_europe_odds = JingcaiOdds(
                odds["home"], odds["draw"], odds["away"], source="500彩票网百家欧赔即时均值"
            )
        if not match.opening_average_europe_odds and average.get("opening_odds"):
            odds = average["opening_odds"]
            match.opening_average_europe_odds = JingcaiOdds(
                odds["home"], odds["draw"], odds["away"], source="500彩票网百家欧赔初始均值"
            )

    def _parse_asian_page(self, match: JingcaiMatch, html: str):
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        avg_idx = text.find("平均值")
        if avg_idx == -1:
            return
        snippet = text[avg_idx:avg_idx + 220]
        nums = re.findall(r"-?\d+\.\d+", snippet)
        if len(nums) >= 6:
            match.asian_average = {
                "current_home_water": float(nums[0]),
                "current_handicap_numeric": float(nums[1]),
                "current_away_water": float(nums[2]),
                "opening_home_water": float(nums[3]),
                "opening_handicap_numeric": float(nums[4]),
                "opening_away_water": float(nums[5]),
                "source": "500彩票网亚盘平均值",
            }
        match.asian_market = self._parse_asian_market(soup)

    def _parse_handicap_page(self, match: JingcaiMatch, html: str):
        soup = BeautifulSoup(html, "html.parser")
        match.handicap_market = self._parse_europe_like_market(
            soup,
            source="500彩票网让球指数",
            market_type="handicap",
            has_handicap_column=True,
        )

    def _parse_score_page(self, match: JingcaiMatch, html: str):
        soup = BeautifulSoup(html, "html.parser")
        match.score_market = self._parse_score_market(soup)

    def _parse_europe_like_market(
        self,
        soup: BeautifulSoup,
        source: str,
        market_type: str,
        has_handicap_column: bool = False,
    ) -> Dict[str, Any]:
        table = soup.find(id="datatb")
        rows = self._table_rows(table)
        records = []
        for row in rows:
            if not row or not row[0].isdigit():
                continue
            record = self._parse_europe_like_row(row, has_handicap_column)
            if record:
                records.append(record)

        stats = self._parse_market_stats_table(soup, has_handicap_column)
        return {
            "source": source,
            "market_type": market_type,
            "company_count": len(records),
            "records": records[:30],
            "main_companies": [record for record in records if record.get("company") in {"威**尔", "*门", "立*", "**t3*5"}][:8],
            "stats": stats,
            "kelly_cv": self._kelly_cv(records),
            "warnings": [] if records else [f"{source}未解析到公司行"],
        }

    def _parse_europe_like_row(self, row: List[str], has_handicap_column: bool = False) -> Optional[Dict[str, Any]]:
        base = 3 if has_handicap_column else 2
        if len(row) < base + 15:
            return None
        company = self._clean_company_name(row[1])
        record = {
            "seq": int(row[0]),
            "company": company,
            "current_odds": self._triplet_from_cells(row, base + 1),
            "opening_odds": self._triplet_from_cells(row, base + 4),
            "current_probabilities": self._percent_triplet_from_cells(row, base + 8),
            "opening_probabilities": self._percent_triplet_from_cells(row, base + 11),
            "return_rate_current": self._parse_percent_value(row[base + 15]) if len(row) > base + 15 else None,
            "return_rate_opening": self._parse_percent_value(row[base + 16]) if len(row) > base + 16 else None,
            "current_kelly": self._triplet_from_cells(row, base + 18) if len(row) > base + 20 else None,
            "opening_kelly": self._triplet_from_cells(row, base + 21) if len(row) > base + 23 else None,
        }
        if has_handicap_column:
            record["handicap"] = row[2]
        return record

    def _parse_market_stats_table(self, soup: BeautifulSoup, has_handicap_column: bool = False) -> Dict[str, Any]:
        for table in soup.find_all("table"):
            rows = self._table_rows(table)
            if not rows or not any("平均值" in " ".join(row) for row in rows[:2]):
                continue
            parsed: Dict[str, Any] = {}
            for row in rows:
                joined = " ".join(row)
                label = ""
                if "平均值" in joined:
                    label = "average"
                elif row and row[0] == "最高值":
                    label = "max"
                elif row and row[0] == "最低值":
                    label = "min"
                if not label:
                    continue
                offset = 2
                parsed[label] = {
                    "current_odds": self._triplet_from_cells(row, offset + 1),
                    "opening_odds": self._triplet_from_cells(row, offset + 4),
                }
                if len(row) > offset + 15:
                    parsed[label]["current_probabilities"] = self._percent_triplet_from_cells(row, offset + 8)
                    parsed[label]["opening_probabilities"] = self._percent_triplet_from_cells(row, offset + 11)
                    parsed[label]["return_rate_current"] = self._parse_percent_value(row[offset + 15])
                    parsed[label]["return_rate_opening"] = self._parse_percent_value(row[offset + 16]) if len(row) > offset + 16 else None
                    parsed[label]["current_kelly"] = self._triplet_from_cells(row, offset + 18) if len(row) > offset + 20 else None
                    parsed[label]["opening_kelly"] = self._triplet_from_cells(row, offset + 21) if len(row) > offset + 23 else None
            return parsed
        return {}

    def _parse_asian_market(self, soup: BeautifulSoup) -> Dict[str, Any]:
        table = soup.find(id="datatb")
        rows = self._table_rows(table)
        records = []
        for row in rows:
            if not row or not row[0].isdigit() or len(row) < 13:
                continue
            records.append({
                "seq": int(row[0]),
                "company": self._clean_company_name(row[1]),
                "current_home_water": self._safe_float(self._strip_arrows(row[3])),
                "current_handicap": row[4],
                "current_away_water": self._safe_float(self._strip_arrows(row[5])),
                "current_change_count": self._safe_float(row[6]),
                "current_change_time": row[7],
                "opening_home_water": self._safe_float(row[9]),
                "opening_handicap": row[10],
                "opening_away_water": self._safe_float(row[11]),
                "opening_change_time": row[12],
            })
        stats = self._parse_asian_stats_table(soup)
        return {
            "source": "500彩票网亚盘对比",
            "company_count": len(records),
            "records": records[:30],
            "stats": stats,
            "water_cv": self._asian_water_cv(records),
            "warnings": [] if records else ["亚盘对比未解析到公司行"],
        }

    def _parse_asian_stats_table(self, soup: BeautifulSoup) -> Dict[str, Any]:
        for table in soup.find_all("table"):
            rows = self._table_rows(table)
            if not rows or not any("平均值" in " ".join(row) for row in rows[:2]):
                continue
            parsed: Dict[str, Any] = {}
            for row in rows:
                joined = " ".join(row)
                label = ""
                if "平均值" in joined:
                    label = "average"
                elif row and row[0] == "最高值":
                    label = "max"
                elif row and row[0] == "最低值":
                    label = "min"
                if not label:
                    continue
                parsed[label] = {
                    "current_home_water": self._safe_float(row[3]) if len(row) > 3 else None,
                    "current_handicap": row[4] if len(row) > 4 else None,
                    "current_away_water": self._safe_float(row[5]) if len(row) > 5 else None,
                    "opening_home_water": self._safe_float(row[9]) if len(row) > 9 else None,
                    "opening_handicap": row[10] if len(row) > 10 else None,
                    "opening_away_water": self._safe_float(row[11]) if len(row) > 11 else None,
                }
            return parsed
        return {}

    def _parse_score_market(self, soup: BeautifulSoup) -> Dict[str, Any]:
        table = None
        for candidate in soup.find_all("table"):
            text = candidate.get_text(" ", strip=True)
            if "1:0" in text and "0:0" in text and "4:4" in text:
                table = candidate
                break
        rows = self._table_rows(table)
        if not rows:
            return {"source": "500彩票网比分指数", "company_count": 0, "records": [], "warnings": ["比分指数表缺失"]}

        score_labels = [cell.replace(":", "-") for cell in rows[0] if re.fullmatch(r"\d+:\d+", cell)]
        records = []
        for row in rows[1:]:
            if not row or not row[0].isdigit() or len(row) < len(score_labels) + 2:
                continue
            company = self._clean_company_name(row[1])
            odds = {}
            for idx, score in enumerate(score_labels):
                value = self._safe_float(row[idx + 2]) if idx + 2 < len(row) else None
                if value:
                    odds[score] = value
            if odds:
                records.append({"seq": int(row[0]), "company": company, "score_odds": odds})

        aggregate = self._aggregate_score_market(records)
        return {
            "source": "500彩票网比分指数",
            "company_count": len(records),
            "score_labels": score_labels,
            "records": records[:20],
            "aggregate": aggregate,
            "warnings": [] if records else ["比分指数当前无公司赔率行"],
        }

    @staticmethod
    def _extract_values_by_ids(soup: BeautifulSoup, ids: List[str]) -> Optional[tuple]:
        values = []
        for item_id in ids:
            node = soup.find(id=item_id)
            if not node:
                return None
            value = Jingcai500Collector._safe_float(node.get_text(strip=True))
            if value is None:
                return None
            values.append(value)
        return tuple(values)

    @staticmethod
    def _parse_recent_summary(text: str, team_name: str, scope: str = "all") -> Optional[JingcaiTeamStats]:
        summary = re.search(
            r"近10场，\s*(\d+)胜\s*(\d+)平\s*(\d+)负\s*进(\d+)球\s*失(\d+)球\s*胜率\s*(\d+)%",
            text,
        )
        if not summary:
            return None

        wins, draws, losses, gf, ga, win_rate = map(int, summary.groups())
        handicap_rate = Jingcai500Collector._extract_percent(text, "赢盘率")
        over_rate = Jingcai500Collector._extract_percent(text, "大球率")

        form = []
        for result in re.findall(r"\s(胜|平|负)\s", text):
            form.append({"胜": "W", "平": "D", "负": "L"}[result])

        return JingcaiTeamStats(
            team_name=team_name,
            matches_played=wins + draws + losses,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=gf,
            goals_against=ga,
            win_rate=win_rate / 100,
            handicap_win_rate=handicap_rate,
            over_rate=over_rate,
            form=form[-5:],
            scope=scope,
        )

    def _parse_detail_record_table(
        self,
        table,
        team_name: str,
        scope: str,
        expected_side: str,
    ) -> Optional[JingcaiTeamStats]:
        rows = table.find_all("tr")
        if not rows:
            return None
        header = rows[0].get_text(" ", strip=True)
        if "主队" not in header or "客队" not in header or "赛果" not in header:
            return None

        wins = draws = losses = goals_for = goals_against = 0
        form: List[str] = []
        handicap_wins = over_count = 0
        handicap_known = over_known = 0

        for row in rows[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 6:
                continue
            teams_score = cells[2]
            if "VS" in teams_score:
                continue
            parsed = re.search(r"(.+?)\s+(\d+)\s*:\s*(\d+)\s+(.+)", teams_score)
            if not parsed:
                continue
            home, home_goals, away_goals, away = parsed.groups()
            side_matches = (
                expected_side == "home" and self._team_matches(home, team_name)
            ) or (
                expected_side == "away" and self._team_matches(away, team_name)
            )
            if not side_matches:
                continue

            home_goals_int = int(home_goals)
            away_goals_int = int(away_goals)
            if expected_side == "home":
                gf, ga = home_goals_int, away_goals_int
            else:
                gf, ga = away_goals_int, home_goals_int

            goals_for += gf
            goals_against += ga
            result = cells[5]
            if result == "胜":
                wins += 1
                form.append("W")
            elif result == "平":
                draws += 1
                form.append("D")
            elif result == "负":
                losses += 1
                form.append("L")

            if len(cells) > 6 and cells[6] in {"赢", "走", "输"}:
                handicap_known += 1
                if cells[6] == "赢":
                    handicap_wins += 1
            if len(cells) > 7 and cells[7] in {"大", "小"}:
                over_known += 1
                if cells[7] == "大":
                    over_count += 1

        played = wins + draws + losses
        if played < 3:
            return None

        return JingcaiTeamStats(
            team_name=team_name,
            matches_played=played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=goals_for,
            goals_against=goals_against,
            win_rate=wins / played if played else None,
            handicap_win_rate=handicap_wins / handicap_known if handicap_known else None,
            over_rate=over_count / over_known if over_known else None,
            form=form[-5:],
            scope=scope,
        )

    @staticmethod
    def _find_box(soup: BeautifulSoup, title_contains: Optional[str] = None, class_contains: Optional[str] = None):
        for box in soup.select("div.M_box"):
            classes = " ".join(box.get("class") or [])
            title_node = box.select_one(".M_title") or box.find("h4")
            title = title_node.get_text(" ", strip=True) if title_node else ""
            if title_contains and title_contains in title:
                return box
            if class_contains and class_contains in classes:
                return box
        return None

    @staticmethod
    def _table_rows(table) -> List[List[str]]:
        rows: List[List[str]] = []
        if not table:
            return rows
        for tr in table.find_all("tr"):
            cells = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip() for cell in tr.find_all(["th", "td"])]
            if cells and any(cell for cell in cells):
                rows.append(cells)
        return rows

    @staticmethod
    def _rows_to_dicts(rows: List[List[str]]) -> List[Dict[str, Any]]:
        if len(rows) < 2:
            return []
        headers = [header or "类别" for header in rows[0]]
        parsed = []
        for row in rows[1:]:
            if not any(cell for cell in row):
                continue
            item = {}
            for idx, header in enumerate(headers):
                item[header] = row[idx] if idx < len(row) else ""
            parsed.append(item)
        return parsed

    def _parse_match_rows(self, table) -> List[Dict[str, Any]]:
        records = []
        rows = self._table_rows(table)
        headers = rows[0] if rows else []
        header_text = " ".join(headers)
        for row in rows[1:]:
            if len(row) < 5:
                continue
            teams = self._parse_score_cell(row[2])
            record = {
                "competition": row[0],
                "date": row[1],
                "raw_match": row[2],
                "home_team": teams.get("home_team"),
                "away_team": teams.get("away_team"),
                "home_score": teams.get("home_score"),
                "away_score": teams.get("away_score"),
            }
            if "盘口" in header_text and len(row) >= 8:
                record["handicap"] = row[3] if len(row) > 7 else ""
                record["half_time"] = row[4] if len(row) > 4 else ""
                record["result"] = row[5] if len(row) > 5 else ""
                record["handicap_result"] = row[6] if len(row) > 6 else ""
                record["goals_size"] = row[7] if len(row) > 7 else ""
            else:
                record["half_time"] = "" if "VS" in row[3] else row[3]
                record["result"] = row[4] if len(row) > 4 else ""
                if len(row) > 5:
                    record["average_europe_odds"] = self._parse_odds_triplet(row[5])
                if len(row) > 6:
                    record["asian_line"] = row[6]
                if len(row) > 7:
                    record["handicap_result"] = row[7]
                if len(row) > 8:
                    record["goals_size"] = row[8]
            records.append(record)
        return records

    @staticmethod
    def _parse_score_cell(value: str) -> Dict[str, Any]:
        cleaned = re.sub(r"\[\d+\]", "", value or "").strip()
        match = re.search(r"(.+?)\s+(\d+)\s*:\s*(\d+)\s+(.+)", cleaned)
        if not match:
            return {}
        home, home_score, away_score, away = match.groups()
        return {
            "home_team": home.strip(),
            "away_team": away.strip(),
            "home_score": int(home_score),
            "away_score": int(away_score),
        }

    @staticmethod
    def _parse_odds_triplet(value: str) -> Optional[Dict[str, float]]:
        nums = re.findall(r"\d+\.\d+|\d+", value or "")
        if len(nums) < 3:
            return None
        return {"home_win": float(nums[0]), "draw": float(nums[1]), "away_win": float(nums[2])}

    def _parse_future_table(self, table) -> List[Dict[str, Any]]:
        fixtures = []
        for row in self._table_rows(table)[1:]:
            if len(row) < 4:
                continue
            sides = re.split(r"\s+VS\s+", row[2])
            fixtures.append({
                "competition": row[0],
                "date": row[1],
                "home_team": sides[0].strip() if sides else row[2],
                "away_team": sides[1].strip() if len(sides) > 1 else "",
                "days_gap": row[3],
            })
        return fixtures

    def _parse_lineup_table(self, table) -> Dict[str, List[str]]:
        rows = self._table_rows(table)
        lineup = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}
        if not rows:
            return lineup
        headers = rows[0]
        header_map = []
        for header in headers:
            if "首发" in header:
                header_map.append("starting")
            elif "替补" in header:
                header_map.append("substitutes")
            elif "伤病" in header:
                header_map.append("injuries")
            elif "停赛" in header:
                header_map.append("suspensions")
            else:
                header_map.append("")
        for row in rows[1:]:
            for idx, cell in enumerate(row):
                if not cell or idx >= len(header_map) or not header_map[idx]:
                    continue
                if cell.startswith("- ") and cell.endswith(" -"):
                    continue
                lineup[header_map[idx]].append(cell)
        return lineup

    def _stats_from_records(self, team_name: str, records: List[Dict[str, Any]], scope: str) -> Optional[JingcaiTeamStats]:
        wins = draws = losses = goals_for = goals_against = 0
        handicap_wins = over_count = 0
        handicap_known = over_known = 0
        form: List[str] = []
        for record in records:
            if record.get("home_score") is None or record.get("away_score") is None:
                continue
            is_home = self._team_matches(record.get("home_team") or "", team_name)
            is_away = self._team_matches(record.get("away_team") or "", team_name)
            if not is_home and not is_away:
                continue
            home_score = int(record["home_score"])
            away_score = int(record["away_score"])
            gf = home_score if is_home else away_score
            ga = away_score if is_home else home_score
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
                form.append("W")
            elif gf == ga:
                draws += 1
                form.append("D")
            else:
                losses += 1
                form.append("L")
            handicap_result = record.get("handicap_result")
            if handicap_result in {"赢", "走", "输"}:
                handicap_known += 1
                if handicap_result == "赢":
                    handicap_wins += 1
            goals_size = record.get("goals_size")
            if goals_size in {"大", "小"}:
                over_known += 1
                if goals_size == "大":
                    over_count += 1
        played = wins + draws + losses
        if not played:
            return None
        return JingcaiTeamStats(
            team_name=team_name,
            matches_played=played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=goals_for,
            goals_against=goals_against,
            win_rate=wins / played,
            handicap_win_rate=handicap_wins / handicap_known if handicap_known else None,
            over_rate=over_count / over_known if over_known else None,
            form=form[-5:],
            scope=scope,
        )

    @staticmethod
    def _triplet_from_cells(row: List[str], start: int) -> Optional[Dict[str, float]]:
        if len(row) <= start + 2:
            return None
        values = [Jingcai500Collector._safe_float(row[start + idx]) for idx in range(3)]
        if any(value is None for value in values):
            return None
        return {"home": values[0], "draw": values[1], "away": values[2]}

    @staticmethod
    def _percent_triplet_from_cells(row: List[str], start: int) -> Optional[Dict[str, float]]:
        if len(row) <= start + 2:
            return None
        values = [Jingcai500Collector._parse_percent_value(row[start + idx]) for idx in range(3)]
        if any(value is None for value in values):
            return None
        return {"home": values[0], "draw": values[1], "away": values[2]}

    @staticmethod
    def _parse_percent_value(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        text = str(value).replace("%", "").strip()
        parsed = Jingcai500Collector._safe_float(text)
        return parsed / 100 if parsed is not None else None

    @staticmethod
    def _clean_company_name(value: str) -> str:
        text = re.sub(r"\s+", " ", value or "").strip()
        if not text:
            return ""
        parts = text.split()
        return parts[0]

    @staticmethod
    def _strip_arrows(value: str) -> str:
        return (value or "").replace("↑", "").replace("↓", "").strip()

    @staticmethod
    def _coefficient_variation(values: List[float]) -> Optional[float]:
        values = [value for value in values if value is not None]
        if len(values) < 2:
            return None
        mean = sum(values) / len(values)
        if not mean:
            return None
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return (variance ** 0.5) / mean

    def _kelly_cv(self, records: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
        result = {}
        for side in ["home", "draw", "away"]:
            values = [
                (record.get("current_kelly") or {}).get(side)
                for record in records
                if (record.get("current_kelly") or {}).get(side) is not None
            ]
            result[side] = self._coefficient_variation(values)
        return result

    def _asian_water_cv(self, records: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
        return {
            "home_water": self._coefficient_variation([
                record.get("current_home_water") for record in records if record.get("current_home_water") is not None
            ]),
            "away_water": self._coefficient_variation([
                record.get("current_away_water") for record in records if record.get("current_away_water") is not None
            ]),
        }

    def _aggregate_score_market(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        score_to_odds: Dict[str, List[float]] = {}
        for record in records:
            for score, odd in (record.get("score_odds") or {}).items():
                score_to_odds.setdefault(score, []).append(odd)

        average_odds = {
            score: sum(values) / len(values)
            for score, values in score_to_odds.items()
            if values
        }
        implied_raw = {
            score: 1 / odd
            for score, odd in average_odds.items()
            if odd and odd > 1
        }
        total = sum(implied_raw.values())
        implied = {
            score: value / total
            for score, value in implied_raw.items()
            if total
        }
        top_scores = sorted(implied.items(), key=lambda item: item[1], reverse=True)[:8]
        return {
            "average_score_odds": average_odds,
            "implied_probabilities": implied,
            "top_scores": [{"score": score, "probability": probability} for score, probability in top_scores],
            "score_odds_cv": {
                score: self._coefficient_variation(values)
                for score, values in score_to_odds.items()
            },
        }

    @staticmethod
    def _clean_team_label(value: str) -> str:
        value = re.sub(r"\[.*?\]", "", value or "")
        return value.replace("阵型:", "").strip()

    @staticmethod
    def _extract_percent(text: str, label: str) -> Optional[float]:
        match = re.search(label + r"\s*(\d+)%", text)
        return int(match.group(1)) / 100 if match else None

    def _team_matches(self, source: str, target: str) -> bool:
        source_norm = self._normalize_team(source)
        aliases = self.TEAM_ALIASES.get(target, [target])
        return any(source_norm == self._normalize_team(alias) for alias in aliases)

    @staticmethod
    def _normalize_team(name: str) -> str:
        return re.sub(r"[\s·\-.]", "", name or "").lower()

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        match = re.search(r"[+-]?\d+", str(value))
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None


__all__ = [
    "Jingcai500Collector",
    "JingcaiMatch",
    "JingcaiOdds",
    "JingcaiTeamStats",
]
