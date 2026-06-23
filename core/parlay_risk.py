#!/usr/bin/env python3
"""组合风险控制。

用于多场汇总时识别同一逻辑重复暴露，例如多场“强队深盘让负”
同时进组合导致一类判断错误全灭。
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class ParlayRiskReport:
    allowed: bool
    max_legs: int
    risk_level: str
    warnings: List[str]
    suggested_groups: List[List[str]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ParlayRiskController:
    """Analyze correlated risk across candidate picks."""

    @staticmethod
    def evaluate(candidates: List[Dict[str, Any]], max_legs: int = 3) -> ParlayRiskReport:
        warnings: List[str] = []
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        allowed_candidates = []

        for item in candidates:
            if item.get("no_bet") or item.get("parlay_allowed") is False:
                warnings.append(f"{item.get('match', '-')}: 单场决策不允许进组合")
                continue
            key = ParlayRiskController._logic_key(item)
            grouped.setdefault(key, []).append(item)
            allowed_candidates.append(item)

        for key, group in grouped.items():
            if len(group) >= 3:
                warnings.append(f"同类逻辑 {key} 出现 {len(group)} 场，禁止全串")
            if key == "deep_handicap_fail" and len(group) >= 2:
                warnings.append("强队深盘让负逻辑最多保留1场，避免同一假设集中暴露")

        suggested = ParlayRiskController._suggest_groups(grouped, max_legs)
        risk_level = "High" if len(warnings) >= 3 else ("Medium" if warnings else "Low")
        return ParlayRiskReport(
            allowed=bool(suggested) and risk_level != "High",
            max_legs=max_legs,
            risk_level=risk_level,
            warnings=list(dict.fromkeys(warnings)),
            suggested_groups=suggested,
        )

    @staticmethod
    def _logic_key(item: Dict[str, Any]) -> str:
        pick = item.get("pick") or item.get("recommendation") or ""
        handicap = item.get("handicap")
        competition = item.get("competition_type") or ""
        if "让" in pick and "负" in pick and handicap is not None and abs(float(handicap)) >= 2:
            return "deep_handicap_fail"
        if "大" in pick:
            return "goals_over"
        if "小" in pick:
            return "goals_under"
        if "客胜" in pick:
            return "away_win"
        if "胜" in pick:
            return "favorite_result"
        if "international" in competition:
            return "international_context"
        return "mixed"

    @staticmethod
    def _suggest_groups(grouped: Dict[str, List[Dict[str, Any]]], max_legs: int) -> List[List[str]]:
        selected = []
        for key, group in grouped.items():
            limit = 1 if key == "deep_handicap_fail" else 2
            selected.extend(group[:limit])
        selected.sort(key=lambda item: item.get("score", 0), reverse=True)
        if len(selected) < 2:
            return []
        names = [item.get("match", "-") for item in selected[:max_legs]]
        return [names]


__all__ = ["ParlayRiskReport", "ParlayRiskController"]
