#!/usr/bin/env python3
"""赛后复盘和模型校准数据记录。

这个模块不做赛果抓取，只提供结构化记录和统计。以后可以把真实赛果
从 API-Football、500彩票网或手动录入后写入这里，用来校准推荐策略。
"""

import json
import math
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PredictionReviewRecord:
    match_key: str
    match_date: str
    home_team: str
    away_team: str
    recommendation: str
    recommended_market: str
    recommended_odds: Optional[float]
    model_probability: Optional[float]
    predicted_score: Optional[str]
    predicted_goals: Optional[str]
    actual_score: Optional[str] = None
    actual_result: Optional[str] = None
    recommendation_hit: Optional[bool] = None
    roi: Optional[float] = None
    error_tags: List[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["error_tags"] = self.error_tags or []
        return payload


class PostMatchReviewStore:
    """Persist prediction records for later calibration."""

    def __init__(self, db_path: str = "data/post_match_reviews.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    match_key TEXT NOT NULL,
                    match_date TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    recommendation TEXT,
                    recommended_market TEXT,
                    recommended_odds REAL,
                    model_probability REAL,
                    predicted_score TEXT,
                    predicted_goals TEXT,
                    actual_score TEXT,
                    actual_result TEXT,
                    recommendation_hit INTEGER,
                    roi REAL,
                    error_tags TEXT,
                    notes TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prediction_reviews_match_key ON prediction_reviews(match_key)")

    def save_prediction(self, record: PredictionReviewRecord) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO prediction_reviews (
                    created_at, match_key, match_date, home_team, away_team,
                    recommendation, recommended_market, recommended_odds,
                    model_probability, predicted_score, predicted_goals,
                    actual_score, actual_result, recommendation_hit, roi,
                    error_tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    record.match_key,
                    record.match_date,
                    record.home_team,
                    record.away_team,
                    record.recommendation,
                    record.recommended_market,
                    record.recommended_odds,
                    record.model_probability,
                    record.predicted_score,
                    record.predicted_goals,
                    record.actual_score,
                    record.actual_result,
                    None if record.recommendation_hit is None else int(record.recommendation_hit),
                    record.roi,
                    json.dumps(record.error_tags or [], ensure_ascii=False),
                    record.notes,
                ),
            )
            return int(cursor.lastrowid)

    def latest_by_match_key(self, match_key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM prediction_reviews
                WHERE match_key = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (match_key,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_result(
        self,
        match_key: str,
        actual_score: str,
        actual_result: str,
        recommendation_hit: bool,
        roi: float,
        error_tags: Optional[List[str]] = None,
        notes: str = "",
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE prediction_reviews
                SET actual_score = ?,
                    actual_result = ?,
                    recommendation_hit = ?,
                    roi = ?,
                    error_tags = ?,
                    notes = ?
                WHERE match_key = ?
                """,
                (
                    actual_score,
                    actual_result,
                    int(recommendation_hit),
                    roi,
                    json.dumps(error_tags or [], ensure_ascii=False),
                    notes,
                    match_key,
                ),
            )

    def summary(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM prediction_reviews WHERE recommendation_hit IS NOT NULL").fetchall()
        if not rows:
            return {
                "reviewed_matches": 0,
                "hit_rate": None,
                "total_roi": None,
                "avg_roi": None,
                "brier_score": None,
                "log_loss": None,
                "by_market": {},
                "top_error_tags": [],
            }

        hits = sum(1 for row in rows if row["recommendation_hit"])
        rois = [row["roi"] or 0 for row in rows]
        tag_counts: Dict[str, int] = {}
        brier_values = []
        log_losses = []
        by_market: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            probability = row["model_probability"]
            outcome = 1.0 if row["recommendation_hit"] else 0.0
            if probability is not None:
                probability = min(1 - 1e-6, max(1e-6, float(probability)))
                brier_values.append((probability - outcome) ** 2)
                log_losses.append(-(outcome * math.log(probability) + (1 - outcome) * math.log(1 - probability)))
            market = row["recommended_market"] or "unknown"
            bucket = by_market.setdefault(market, {"matches": 0, "hits": 0, "roi": 0.0})
            bucket["matches"] += 1
            bucket["hits"] += int(bool(row["recommendation_hit"]))
            bucket["roi"] += row["roi"] or 0.0
            try:
                tags = json.loads(row["error_tags"] or "[]")
            except json.JSONDecodeError:
                tags = []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        for bucket in by_market.values():
            bucket["hit_rate"] = bucket["hits"] / bucket["matches"] if bucket["matches"] else None
            bucket["avg_roi"] = bucket["roi"] / bucket["matches"] if bucket["matches"] else None
        return {
            "reviewed_matches": len(rows),
            "hit_rate": hits / len(rows),
            "total_roi": sum(rois),
            "avg_roi": sum(rois) / len(rois),
            "brier_score": sum(brier_values) / len(brier_values) if brier_values else None,
            "log_loss": sum(log_losses) / len(log_losses) if log_losses else None,
            "by_market": by_market,
            "top_error_tags": sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:8],
        }

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM prediction_reviews
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        payload = dict(row)
        try:
            payload["error_tags"] = json.loads(payload.get("error_tags") or "[]")
        except json.JSONDecodeError:
            payload["error_tags"] = []
        return payload


class ReviewEvaluator:
    """Evaluate actual result against a stored recommendation."""

    @staticmethod
    def evaluate(
        recommendation: str,
        market: str,
        odds: Optional[float],
        actual_score: str,
        handicap: Optional[float] = None,
        stake: float = 1.0,
    ) -> Dict[str, Any]:
        home_goals, away_goals = ReviewEvaluator._parse_score(actual_score)
        actual_result = ReviewEvaluator._actual_result(home_goals, away_goals)
        hit = ReviewEvaluator._hit(recommendation, market, home_goals, away_goals, handicap)
        roi = ReviewEvaluator._roi(hit, odds, stake)
        return {
            "actual_result": actual_result,
            "recommendation_hit": hit,
            "roi": roi,
            "error_tags": ReviewEvaluator._error_tags(recommendation, market, hit, home_goals, away_goals, handicap),
        }

    @staticmethod
    def _parse_score(score: str) -> tuple:
        normalized = score.replace(":", "-").strip()
        parts = normalized.split("-")
        if len(parts) != 2:
            raise ValueError("比分格式应为 2-1 或 2:1")
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _actual_result(home_goals: int, away_goals: int) -> str:
        if home_goals > away_goals:
            return "主胜"
        if home_goals < away_goals:
            return "客胜"
        return "平局"

    @staticmethod
    def _hit(recommendation: str, market: str, home_goals: int, away_goals: int, handicap: Optional[float]) -> bool:
        text = recommendation or ""
        if "观望" in text or "不建议" in text:
            return False

        # 先结算让球市场，避免“让球胜平负”被普通胜平负分支提前匹配。
        if "让" in text and handicap is not None:
            adjusted = home_goals + handicap - away_goals
            if re.search(r"(?:受?让)[+-]?\d*(?:\.\d+)?胜", text):
                return adjusted > 0
            if re.search(r"(?:受?让)[+-]?\d*(?:\.\d+)?平", text):
                return adjusted == 0
            if re.search(r"(?:受?让)[+-]?\d*(?:\.\d+)?负", text):
                return adjusted < 0

        if market in {"1X2", "胜平负"} or ("胜平负" in market and "让球" not in market):
            if "主胜" in text or ("胜" in text and "客" not in text and "平" not in text):
                return home_goals > away_goals
            if "客胜" in text:
                return away_goals > home_goals
            if "平" in text:
                return home_goals == away_goals

        if "大" in text:
            return home_goals + away_goals > 2.5
        if "小" in text:
            return home_goals + away_goals < 2.5

        return False

    @staticmethod
    def _roi(hit: bool, odds: Optional[float], stake: float) -> float:
        if stake <= 0:
            stake = 1.0
        if hit and odds and odds > 1:
            return (stake * (odds - 1)) / stake
        return -1.0

    @staticmethod
    def _error_tags(
        recommendation: str,
        market: str,
        hit: bool,
        home_goals: int,
        away_goals: int,
        handicap: Optional[float],
    ) -> List[str]:
        if hit:
            return []
        tags = ["推荐未命中"]
        total = home_goals + away_goals
        if handicap is not None and abs(handicap) >= 2 and "让负" in (recommendation or ""):
            tags.append("深盘让负误判")
        if total >= 4:
            tags.append("低估进球数")
        if "客胜" in (recommendation or "") and home_goals > away_goals:
            tags.append("客队方向误判")
        return tags


__all__ = ["PredictionReviewRecord", "PostMatchReviewStore", "ReviewEvaluator"]
