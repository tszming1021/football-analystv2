#!/usr/bin/env python3
"""赔率变化分析。

基于 OddsHistoryStore 的快照摘要，判断赔率是否明显向某一方向移动。
数据不足时明确返回缺口，而不是臆造临场趋势。
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class OddsMovementSignal:
    available: bool
    movement_count: int
    strongest_move: Optional[str]
    market_bias: str
    clv_note: str
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OddsMovementAnalyzer:
    """Analyze first/latest odds movement from local snapshots."""

    @staticmethod
    def analyze(odds_history: Optional[Dict[str, Any]]) -> OddsMovementSignal:
        if not odds_history:
            return OddsMovementSignal(False, 0, None, "unknown", "暂无赔率历史", [], ["未记录赔率快照"])

        markets = odds_history.get("markets") or {}
        notes: List[str] = []
        warnings: List[str] = []
        moves = []

        for key, label in [("nspf", "胜平负"), ("spf", "让球胜平负")]:
            payload = markets.get(key) or {}
            first = payload.get("first") or {}
            latest = payload.get("latest") or {}
            if not first or not latest or payload.get("snapshots", 0) < 2:
                warnings.append(f"{label}快照不足，无法判断变化")
                continue
            for side, side_label in [("home_win", "主/让胜"), ("draw", "平/让平"), ("away_win", "客/让负")]:
                start = OddsMovementAnalyzer._safe_float(first.get(side))
                end = OddsMovementAnalyzer._safe_float(latest.get(side))
                if start is None or end is None:
                    continue
                delta = end - start
                if abs(delta) >= 0.03:
                    moves.append((abs(delta), f"{label}{side_label} {start:.2f}->{end:.2f}", side, delta))

        moves.sort(reverse=True, key=lambda item: item[0])
        for _, desc, _, delta in moves[:5]:
            direction = "赔率上调" if delta > 0 else "赔率下调"
            notes.append(f"{desc}，{direction}")

        market_bias = OddsMovementAnalyzer._market_bias(moves)
        clv_note = "已有多次快照，可继续比较临场收盘线" if odds_history.get("snapshot_count", 0) >= 2 else "快照不足，CLV判断弱"
        return OddsMovementSignal(
            available=bool(moves),
            movement_count=len(moves),
            strongest_move=moves[0][1] if moves else None,
            market_bias=market_bias,
            clv_note=clv_note,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _market_bias(moves: List[tuple]) -> str:
        if not moves:
            return "unknown"
        # Decimal odds dropping means market support.
        support = {"home": 0.0, "draw": 0.0, "away": 0.0}
        for magnitude, _, side, delta in moves:
            if delta >= 0:
                continue
            if side == "home_win":
                support["home"] += magnitude
            elif side == "draw":
                support["draw"] += magnitude
            elif side == "away_win":
                support["away"] += magnitude
        best = max(support.items(), key=lambda item: item[1])
        return best[0] if best[1] > 0 else "unknown"

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["OddsMovementSignal", "OddsMovementAnalyzer"]
