#!/usr/bin/env python3
"""500.com trade-page table source.

This module owns the 500 trade-page table workflow:
- fetch the mixed trade page
- decode gb18030/gb2312 compatible HTML
- parse the main row and hidden extended market row
- fall back to the local JSON supplement when live fetch or parsing is incomplete
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from requests import RequestException


DEFAULT_TRADE_URL = "https://trade.500.com/jczq/index.php?playid={playid}&g={g}"
DEFAULT_DATE_TRADE_URL = "https://trade.500.com/jczq/index.php?playid={playid}&g={g}&date={match_date}"
DEFAULT_LOCAL_SUPPLEMENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "500_trade_supplement_local.json",
)


@dataclass
class TradeTableMatch:
    match_no: str = ""
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""
    league: str = ""
    match_date: str = ""
    match_time: str = ""
    source_url: str = ""
    fetch_time: str = ""
    sale_status: str = ""
    result_3way: Optional[Dict[str, float]] = None
    handicap_3way: Optional[Dict[str, Any]] = None
    score_table: List[Dict[str, Any]] = field(default_factory=list)
    total_goals_table: Dict[str, float] = field(default_factory=dict)
    half_full_table: Dict[str, float] = field(default_factory=dict)
    source: str = "500.com trade page"
    local_supplement: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def fetch_trade_page(
    playid: int = 312,
    g: int = 2,
    match_date: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 20,
) -> str:
    """Fetch 500 trade-page HTML and decode it with tolerant gb18030 handling."""
    client = session or requests.Session()
    client.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://trade.500.com/",
    })
    url = (
        DEFAULT_DATE_TRADE_URL.format(playid=playid, g=g, match_date=match_date)
        if match_date
        else DEFAULT_TRADE_URL.format(playid=playid, g=g)
    )
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    return decode_gb18030(response.content)


def decode_gb18030(raw: bytes) -> str:
    """Decode a 500 page using the site's gb2312/gb18030 compatible encoding."""
    return raw.decode("gb18030", "replace")


def parse_trade_matches(html: str, source_url: str = "") -> List[TradeTableMatch]:
    """Parse all visible match rows from a mixed trade page."""
    soup = BeautifulSoup(html, "html.parser")
    fetch_time = datetime.now().isoformat(timespec="seconds")
    matches = []
    for row in soup.select("tr.bet-tb-tr"):
        parsed = parse_trade_row(row, source_url=source_url, fetch_time=fetch_time)
        if parsed:
            matches.append(parsed)
    return matches


def parse_trade_row(row: Any, source_url: str = "", fetch_time: str = "") -> Optional[TradeTableMatch]:
    fixture_id = row.get("data-fixtureid") or ""
    if not fixture_id:
        return None
    match_date = row.get("data-matchdate") or ""
    match_time = row.get("data-matchtime") or ""
    return TradeTableMatch(
        match_no=row.get("data-matchnum") or "",
        match_id=str(fixture_id),
        home_team=row.get("data-homesxname") or "",
        away_team=row.get("data-awaysxname") or "",
        league=row.get("data-simpleleague") or "",
        match_date=match_date,
        match_time=match_time,
        source_url=source_url,
        fetch_time=fetch_time or datetime.now().isoformat(timespec="seconds"),
        sale_status=sale_status_from_row(row),
        result_3way=extract_result_3way(row),
        handicap_3way=extract_handicap_3way(row),
        score_table=extract_score_table(row),
        total_goals_table=extract_total_goals_table(row),
        half_full_table=extract_half_full_table(row),
    )


def extract_result_3way(row: Any) -> Optional[Dict[str, float]]:
    return _triplet_from_buttons(row.select('p.betbtn[data-type="nspf"]'))


def extract_handicap_3way(row: Any) -> Optional[Dict[str, Any]]:
    values = _triplet_from_buttons(row.select('p.betbtn[data-type="spf"]'))
    if not values:
        return None
    values["handicap"] = str(row.get("data-rangqiu") or "")
    return values


def extract_score_table(row: Any) -> List[Dict[str, Any]]:
    score_values = _extended_market_values(row, "bf")
    return [
        {"score": score, "value": value, "rank": index + 1}
        for index, (score, value) in enumerate(score_values.items())
    ]


def extract_total_goals_table(row: Any) -> Dict[str, float]:
    return _extended_market_values(row, "jqs")


def extract_half_full_table(row: Any) -> Dict[str, float]:
    return _extended_market_values(row, "bqc")


def find_trade_match(
    home_team: str,
    away_team: str,
    match_date: Optional[str] = None,
    match_time: Optional[str] = None,
    fixture_id: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 20,
    local_path: str = DEFAULT_LOCAL_SUPPLEMENT,
) -> Optional[TradeTableMatch]:
    """Find a single match from live 500 trade data, then local supplement fallback."""
    live = None
    try:
        html = fetch_trade_page(match_date=match_date, session=session, timeout=timeout)
        source_url = (
            DEFAULT_DATE_TRADE_URL.format(playid=312, g=2, match_date=match_date)
            if match_date
            else DEFAULT_TRADE_URL.format(playid=312, g=2)
        )
        live = _find_in_matches(
            parse_trade_matches(html, source_url=source_url),
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            match_time=match_time,
            fixture_id=fixture_id,
        )
    except RequestException:
        live = None
    if live and _has_core_tables(live):
        return live

    local = load_local_trade_supplement(
        local_path=local_path,
        home_team=home_team,
        away_team=away_team,
        fixture_id=fixture_id or (live.match_id if live else None),
    )
    return merge_trade_matches(live, local) if live or local else None


def load_local_trade_supplement(
    local_path: str = DEFAULT_LOCAL_SUPPLEMENT,
    home_team: str = "",
    away_team: str = "",
    fixture_id: Optional[str] = None,
) -> Optional[TradeTableMatch]:
    if not os.path.exists(local_path):
        return None
    try:
        with open(local_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    for item in payload.get("matches") or []:
        if fixture_id and str(item.get("match_id") or "") == str(fixture_id):
            return _local_item_to_trade_match(item, payload)
    for item in payload.get("matches") or []:
        if _team_matches(str(item.get("home_team") or ""), home_team) and _team_matches(str(item.get("away_team") or ""), away_team):
            return _local_item_to_trade_match(item, payload)
    return None


def merge_trade_matches(live: Optional[TradeTableMatch], local: Optional[TradeTableMatch]) -> Optional[TradeTableMatch]:
    if not live:
        return local
    if not local:
        return live
    live.result_3way = live.result_3way or local.result_3way
    live.handicap_3way = live.handicap_3way or local.handicap_3way
    live.score_table = live.score_table or local.score_table
    live.total_goals_table = live.total_goals_table or local.total_goals_table
    live.half_full_table = live.half_full_table or local.half_full_table
    live.sale_status = live.sale_status or local.sale_status
    live.local_supplement = not _has_core_tables(live) or local.local_supplement
    return live


def sale_status_from_row(row: Any) -> str:
    value = row.get("data-isend")
    if value == "1":
        return "closed"
    if value == "0":
        return "available_or_displayed"
    return row.get("data-subactive") or ""


def _find_in_matches(
    matches: List[TradeTableMatch],
    home_team: str,
    away_team: str,
    match_date: Optional[str],
    match_time: Optional[str],
    fixture_id: Optional[str],
) -> Optional[TradeTableMatch]:
    for item in matches:
        if fixture_id and str(item.match_id) == str(fixture_id):
            return item
    for item in matches:
        if not _team_matches(item.home_team, home_team) or not _team_matches(item.away_team, away_team):
            continue
        if match_date and item.match_date and item.match_date != match_date:
            continue
        if match_time and item.match_time and item.match_time != match_time:
            continue
        return item
    return None


def _local_item_to_trade_match(item: Dict[str, Any], payload: Dict[str, Any]) -> TradeTableMatch:
    table = item.get("table_data") or {}
    kickoff = str(item.get("kickoff_time") or "")
    kickoff_date, kickoff_time = _split_kickoff(kickoff)
    return TradeTableMatch(
        match_no=str(item.get("match_no") or ""),
        match_id=str(item.get("match_id") or ""),
        home_team=str(item.get("home_team") or ""),
        away_team=str(item.get("away_team") or ""),
        league=str(item.get("league") or ""),
        match_date=kickoff_date,
        match_time=kickoff_time,
        source_url=str(item.get("source_url") or ""),
        fetch_time=str(payload.get("fetch_time") or ""),
        sale_status=str((table.get("sale_status") or "")),
        result_3way=_float_triplet(table.get("result_3way") or {}),
        handicap_3way=_handicap_triplet(table.get("handicap_3way") or {}),
        score_table=[
            {
                "score": str(row.get("score") or ""),
                "value": _safe_float(row.get("value")),
                "rank": row.get("rank") or index + 1,
            }
            for index, row in enumerate(table.get("score_table") or [])
            if row.get("score") and _safe_float(row.get("value")) is not None
        ],
        total_goals_table={
            str(key): value_float
            for key, value in (table.get("total_goals_table") or {}).items()
            for value_float in [_safe_float(value)]
            if value_float is not None
        },
        half_full_table={
            str(key): value_float
            for key, value in (table.get("half_full_table") or {}).items()
            for value_float in [_safe_float(value)]
            if value_float is not None
        },
        source="500.com local trade supplement",
        local_supplement=True,
    )


def _extended_market_values(row: Any, market_type: str) -> Dict[str, float]:
    more_row = row.find_next_sibling("tr", class_="bet-more-wrap")
    container = more_row or row
    values: Dict[str, float] = {}
    for button in container.select(f'p.sbetbtn[data-type="{market_type}"][data-value][data-sp]'):
        selection = (button.get("data-value") or "").strip().replace(":", "-")
        value = _safe_float(button.get("data-sp"))
        if selection and value is not None:
            values[selection] = value
    return values


def _triplet_from_buttons(buttons: List[Any]) -> Optional[Dict[str, float]]:
    values: Dict[str, float] = {}
    for button in buttons:
        value = _safe_float(button.get("data-sp"))
        if value is not None:
            values[button.get("data-value")] = value
    if all(key in values for key in ("3", "1", "0")):
        return {"home": values["3"], "draw": values["1"], "away": values["0"]}
    return None


def _float_triplet(values: Dict[str, Any]) -> Optional[Dict[str, float]]:
    triplet = {key: _safe_float(values.get(key)) for key in ("home", "draw", "away")}
    if all(value is not None for value in triplet.values()):
        return triplet  # type: ignore[return-value]
    return None


def _handicap_triplet(values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    triplet = _float_triplet(values)
    if not triplet:
        return None
    triplet["handicap"] = str(values.get("handicap") or "")
    return triplet


def _has_core_tables(item: TradeTableMatch) -> bool:
    return bool(
        item.result_3way
        and item.handicap_3way
        and item.score_table
        and item.total_goals_table
        and item.half_full_table
    )


def _team_matches(source: str, target: str) -> bool:
    return _normalize_team(source) == _normalize_team(target)


def _normalize_team(name: str) -> str:
    return re.sub(r"[\s·\-.]", "", name or "").lower()


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_kickoff(value: str) -> tuple[str, str]:
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", value)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


__all__ = [
    "TradeTableMatch",
    "decode_gb18030",
    "extract_half_full_table",
    "extract_handicap_3way",
    "extract_result_3way",
    "extract_score_table",
    "extract_total_goals_table",
    "fetch_trade_page",
    "find_trade_match",
    "load_local_trade_supplement",
    "merge_trade_matches",
    "parse_trade_matches",
]
