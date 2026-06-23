#!/usr/bin/env python3
"""Cross-check model layers before report rendering.

This checker is intentionally conservative: it does not overwrite model
probabilities. It records contradictions that should lower confidence or force
the report to explain why a direction is fragile.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ConsistencyCheckReport:
    status: str
    warnings: List[str]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelConsistencyChecker:
    """Detect contradictions between result, handicap, goals, score and LEG."""

    @staticmethod
    def check(
        poisson: Any,
        handicap_signal: Any,
        goals_signal: Any,
        scoreline_signal: Any,
        leg_signal: Any,
        decision: Any,
    ) -> ConsistencyCheckReport:
        warnings: List[str] = []
        notes: List[str] = []

        ModelConsistencyChecker._check_goal_score_alignment(goals_signal, scoreline_signal, warnings, notes)
        ModelConsistencyChecker._check_handicap_score_alignment(handicap_signal, scoreline_signal, warnings, notes)
        ModelConsistencyChecker._check_leg_decision_alignment(leg_signal, decision, warnings, notes)
        ModelConsistencyChecker._check_result_score_alignment(poisson, scoreline_signal, warnings, notes)

        status = "pass"
        if len(warnings) >= 3:
            status = "high_attention"
        elif warnings:
            status = "attention"

        return ConsistencyCheckReport(status=status, warnings=warnings, notes=notes)

    @staticmethod
    def _check_goal_score_alignment(goals_signal: Any, scoreline_signal: Any, warnings: List[str], notes: List[str]) -> None:
        if not goals_signal or not scoreline_signal:
            return
        top_scores = getattr(scoreline_signal, "top_scores", []) or []
        if not top_scores:
            return
        goals_direction = str(getattr(goals_signal, "goals_direction", "") or "")
        top2_totals = [int(item.get("total_goals", 0) or 0) for item in top_scores[:2]]
        top5_totals = [int(item.get("total_goals", 0) or 0) for item in top_scores[:5]]

        if "小" in goals_direction and top2_totals and max(top2_totals) >= 4:
            warnings.append("进球方向偏小，但比分保守位出现4球以上，需要降置信")
        if "大" in goals_direction and top2_totals and max(top2_totals) <= 2:
            warnings.append("进球方向偏大，但比分保守位集中在2球以内，需要解释节奏矛盾")
        if "2-3" in goals_direction and top5_totals and sum(1 for total in top5_totals if total >= 4) >= 3:
            warnings.append("总球方向写2-3球，但比分风险位过多集中4球以上")
        if top2_totals:
            notes.append(f"比分保守位总球: {', '.join(str(total) for total in top2_totals)}")

    @staticmethod
    def _check_handicap_score_alignment(handicap_signal: Any, scoreline_signal: Any, warnings: List[str], notes: List[str]) -> None:
        if not handicap_signal or not scoreline_signal:
            return
        line = ModelConsistencyChecker._safe_float(getattr(handicap_signal, "line", None))
        top_scores = getattr(scoreline_signal, "top_scores", []) or []
        if line is None or not top_scores:
            return

        cover = ModelConsistencyChecker._safe_float(getattr(handicap_signal, "cover_probability", None)) or 0.0
        push = ModelConsistencyChecker._safe_float(getattr(handicap_signal, "push_probability", None)) or 0.0
        fail = ModelConsistencyChecker._safe_float(getattr(handicap_signal, "fail_probability", None)) or 0.0
        best = max([("让胜", cover), ("让平", push), ("让负", fail)], key=lambda item: item[1])[0]
        top2_settlements = [
            ModelConsistencyChecker._settlement(int(item.get("home_goals", 0) or 0), int(item.get("away_goals", 0) or 0), line)
            for item in top_scores[:2]
        ]
        if best not in top2_settlements and abs(line) >= 1:
            warnings.append(f"让球模型首选{best}，但比分保守位指向{ '/'.join(top2_settlements) }")
        if abs(line) >= 1.75 and "让平" in top2_settlements and push < max(cover, fail) - 0.08:
            warnings.append("比分保守位存在卡线，但让球平概率仍偏低")
        notes.append(f"比分保守位让球结算: {'/'.join(top2_settlements)}")

    @staticmethod
    def _check_leg_decision_alignment(leg_signal: Any, decision: Any, warnings: List[str], notes: List[str]) -> None:
        if not leg_signal or not decision:
            return
        depth_direction = str(getattr(leg_signal, "depth_direction", "") or "")
        primary = str(getattr(decision, "primary_pick", "") or "")
        pick = str(getattr(decision, "primary_market", "") or "") + " " + primary
        if "赢深保守" in depth_direction and ("让胜" in pick or "赢深" in pick):
            warnings.append("LEG提示赢深保守，但集成决策仍偏深度方向")
        if "支持赢深" in depth_direction and "让负" in pick:
            warnings.append("LEG支持赢深，但集成决策偏受让方向，需要说明市场分歧")
        notes.append(f"LEG结论: {depth_direction or '-'}")

    @staticmethod
    def _check_result_score_alignment(poisson: Any, scoreline_signal: Any, warnings: List[str], notes: List[str]) -> None:
        if not poisson or not scoreline_signal:
            return
        top_scores = getattr(scoreline_signal, "top_scores", []) or []
        if not top_scores:
            return
        probs = {
            "home": getattr(poisson, "home_win_prob", 0.0),
            "draw": getattr(poisson, "draw_prob", 0.0),
            "away": getattr(poisson, "away_win_prob", 0.0),
        }
        model_top = max(probs.items(), key=lambda item: item[1])[0]
        top2_outcomes = [ModelConsistencyChecker._outcome_key(item) for item in top_scores[:2]]
        if probs[model_top] >= 0.58 and model_top not in top2_outcomes:
            warnings.append("赛果概率优势明显，但比分保守位没有覆盖该赛果方向")

    @staticmethod
    def _settlement(home_goals: int, away_goals: int, line: float) -> str:
        adjusted = home_goals + line - away_goals
        if adjusted > 0:
            return "让胜"
        if adjusted == 0:
            return "让平"
        return "让负"

    @staticmethod
    def _outcome_key(item: Dict[str, Any]) -> str:
        margin = int(item.get("margin", 0) or 0)
        if margin > 0:
            return "home"
        if margin < 0:
            return "away"
        return "draw"

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["ConsistencyCheckReport", "ModelConsistencyChecker"]
