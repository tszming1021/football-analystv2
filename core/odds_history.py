#!/usr/bin/env python3
"""本地赔率历史与收盘线追踪。

每次抓取 500彩票网赔率时记录一条快照。长期运行后可以评估：
- 赔率是否持续向推荐方向移动
- 推荐是否跑赢收盘赔率 (CLV)
- 不同市场的赔率波动和临场风险
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class OddsSnapshot:
    fixture_id: str
    match_num: str
    league: str
    home_team: str
    away_team: str
    match_datetime: str
    market: str
    home_win: Optional[float]
    draw: Optional[float]
    away_win: Optional[float]
    handicap: Optional[int] = None
    source: str = "500彩票网"
    captured_at: str = ""
    minutes_to_kickoff: Optional[float] = None
    is_closing_candidate: bool = False
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OddsHistoryStore:
    """SQLite-backed odds history store."""

    def __init__(self, db_path: Optional[str] = None):
        root = Path(__file__).resolve().parents[1]
        default_path = root / "data" / "odds_history.sqlite3"
        self.db_path = Path(db_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS odds_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id TEXT NOT NULL,
                    match_num TEXT,
                    league TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    match_datetime TEXT,
                    market TEXT NOT NULL,
                    home_win REAL,
                    draw REAL,
                    away_win REAL,
                    handicap INTEGER,
                    source TEXT,
                    captured_at TEXT NOT NULL,
                    minutes_to_kickoff REAL,
                    is_closing_candidate INTEGER DEFAULT 0,
                    raw_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_odds_snapshots_fixture_market_time
                ON odds_snapshots (fixture_id, market, captured_at)
                """
            )

    def record_jingcai_match(self, match: Any, captured_at: Optional[datetime] = None) -> List[OddsSnapshot]:
        captured = captured_at or datetime.now()
        match_datetime = f"{match.match_date} {match.match_time}"
        minutes_to_kickoff = self._minutes_to_kickoff(match_datetime, captured)
        closing = minutes_to_kickoff is not None and 0 <= minutes_to_kickoff <= 15
        snapshots = []

        if match.no_handicap_odds:
            snapshots.append(OddsSnapshot(
                fixture_id=match.fixture_id,
                match_num=match.match_num,
                league=match.league,
                home_team=match.home_team,
                away_team=match.away_team,
                match_datetime=match_datetime,
                market="nspf",
                home_win=match.no_handicap_odds.home_win,
                draw=match.no_handicap_odds.draw,
                away_win=match.no_handicap_odds.away_win,
                handicap=None,
                source=match.no_handicap_odds.source,
                captured_at=captured.isoformat(timespec="seconds"),
                minutes_to_kickoff=minutes_to_kickoff,
                is_closing_candidate=closing,
                raw=match.no_handicap_odds.__dict__,
            ))

        if match.handicap_odds:
            snapshots.append(OddsSnapshot(
                fixture_id=match.fixture_id,
                match_num=match.match_num,
                league=match.league,
                home_team=match.home_team,
                away_team=match.away_team,
                match_datetime=match_datetime,
                market="spf",
                home_win=match.handicap_odds.home_win,
                draw=match.handicap_odds.draw,
                away_win=match.handicap_odds.away_win,
                handicap=match.handicap,
                source=match.handicap_odds.source,
                captured_at=captured.isoformat(timespec="seconds"),
                minutes_to_kickoff=minutes_to_kickoff,
                is_closing_candidate=closing,
                raw=match.handicap_odds.__dict__,
            ))

        self.record_snapshots(snapshots)
        return snapshots

    def record_snapshots(self, snapshots: List[OddsSnapshot]):
        if not snapshots:
            return
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO odds_snapshots (
                    fixture_id, match_num, league, home_team, away_team,
                    match_datetime, market, home_win, draw, away_win,
                    handicap, source, captured_at, minutes_to_kickoff,
                    is_closing_candidate, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.fixture_id,
                        item.match_num,
                        item.league,
                        item.home_team,
                        item.away_team,
                        item.match_datetime,
                        item.market,
                        item.home_win,
                        item.draw,
                        item.away_win,
                        item.handicap,
                        item.source,
                        item.captured_at,
                        item.minutes_to_kickoff,
                        1 if item.is_closing_candidate else 0,
                        json.dumps(item.raw or {}, ensure_ascii=False),
                    )
                    for item in snapshots
                ],
            )

    def summary_for_fixture(self, fixture_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM odds_snapshots
                WHERE fixture_id = ?
                ORDER BY captured_at ASC
                """,
                (fixture_id,),
            ).fetchall()
        markets: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            market = row["market"]
            markets.setdefault(market, {"snapshots": 0, "first": None, "latest": None, "closing": None})
            payload = self._row_to_dict(row)
            markets[market]["snapshots"] += 1
            markets[market]["first"] = markets[market]["first"] or payload
            markets[market]["latest"] = payload
            if row["is_closing_candidate"]:
                markets[market]["closing"] = payload
        return {
            "db_path": str(self.db_path),
            "fixture_id": fixture_id,
            "snapshot_count": len(rows),
            "markets": markets,
        }

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        return {
            "market": row["market"],
            "home_win": row["home_win"],
            "draw": row["draw"],
            "away_win": row["away_win"],
            "handicap": row["handicap"],
            "captured_at": row["captured_at"],
            "minutes_to_kickoff": row["minutes_to_kickoff"],
            "is_closing_candidate": bool(row["is_closing_candidate"]),
        }

    @staticmethod
    def _minutes_to_kickoff(match_datetime: str, captured_at: datetime) -> Optional[float]:
        try:
            kickoff = datetime.strptime(match_datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        return (kickoff - captured_at.replace(tzinfo=None)).total_seconds() / 60


__all__ = ["OddsHistoryStore", "OddsSnapshot"]
