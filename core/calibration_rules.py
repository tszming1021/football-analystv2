#!/usr/bin/env python3
"""Reusable post-match calibration rules.

The rule book is intentionally data-driven: post-match reviews write JSON
calibration files under data/calibration, and model/report code can request
small weight adjustments from those files without hard-coding one-off lessons.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_JLEAGUE_CALIBRATION = Path("data/calibration/jleague_20260606_rank_playoff_calibration.json")
DEFAULT_INTERNATIONAL_CALIBRATION = Path("data/calibration/international_20260609_three_match_review.json")


@dataclass
class CalibrationAdjustment:
    rule: str
    weight_delta: float
    target: str
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "weight_delta": self.weight_delta,
            "target": self.target,
            "note": self.note,
        }


@dataclass
class MatchCalibrationFeatures:
    league: str = ""
    competition_stage: str = ""
    is_second_leg: bool = False
    is_ranking_or_playoff: bool = False
    home_favorite_low_value: bool = False
    handicap_protects_underdog: bool = False
    away_favorite_with_home_plus_one: bool = False
    top_scores: List[str] = field(default_factory=list)
    top_total_goals: List[str] = field(default_factory=list)
    home_historical_dominance: bool = False
    final_lineup_confirmed: bool = False
    injury_notes_are_material: bool = False
    competition_type: str = ""
    friendly_subtype: str = ""
    handicap_line: Optional[float] = None
    handicap_push_supported_by_scores: bool = False
    deep_favorite_context: bool = False
    four_goal_two_margin_btts_path: bool = False


class CalibrationRuleBook:
    """Load calibration JSON and emit adjustments for similar future matches."""

    def __init__(self, calibration_path: Optional[Path | str] = None):
        self.calibration_path = Path(calibration_path or DEFAULT_JLEAGUE_CALIBRATION)
        self.payload = self._load_payload()

    def _load_payload(self) -> Dict[str, Any]:
        if not self.calibration_path.exists():
            return {}
        return json.loads(self.calibration_path.read_text(encoding="utf-8"))

    @property
    def available(self) -> bool:
        return bool(self.payload)

    def adjustments_for(self, features: MatchCalibrationFeatures) -> List[CalibrationAdjustment]:
        if not self.available:
            return []

        adjustments: List[CalibrationAdjustment] = []
        stage_text = f"{features.league} {features.competition_stage}".lower()
        jleague_like = "日职" in features.league or "jleague" in stage_text
        cautious_context = (
            jleague_like
            and (features.is_second_leg or features.is_ranking_or_playoff or "排名" in features.competition_stage)
        )

        if cautious_context and features.handicap_protects_underdog:
            adjustments.append(CalibrationAdjustment(
                rule="handicap_protection_priority",
                weight_delta=0.18,
                target="handicap_protection",
                note="日职排名赛/次回合样本显示让球保护层比直接赛果更稳定",
            ))

        if features.home_favorite_low_value and features.handicap_protects_underdog:
            adjustments.append(CalibrationAdjustment(
                rule="direct_result_confidence_cap",
                weight_delta=-0.20,
                target="direct_result_confidence",
                note="主胜低位但让球保护客队时，直接赛果最高降为中等置信",
            ))

        low_score_signals = {"0-0", "0-1", "1-0"}
        if cautious_context and (low_score_signals & set(features.top_scores)):
            adjustments.append(CalibrationAdjustment(
                rule="low_score_pool",
                weight_delta=0.12,
                target="low_score_paths",
                note="谨慎盘中0-0/0-1/1-0需要进入比分保护池",
            ))

        if features.away_favorite_with_home_plus_one and {"0-1", "1-2"} & set(features.top_scores):
            adjustments.append(CalibrationAdjustment(
                rule="plus_one_push_split",
                weight_delta=0.10,
                target="plus_one_push",
                note="+1场景需要拆分让平与让胜，一球小负不能并入同一保护层",
            ))

        if features.home_historical_dominance and {"2-0", "3-0"} & set(features.top_scores):
            adjustments.append(CalibrationAdjustment(
                rule="home_depth_recovery",
                weight_delta=0.10,
                target="home_depth_scores",
                note="主场压制强且比分表支持2-0/3-0时，恢复主队深度路径",
            ))

        if features.injury_notes_are_material and not features.final_lineup_confirmed:
            adjustments.append(CalibrationAdjustment(
                rule="injury_note_cap",
                weight_delta=-0.08,
                target="injury_based_downgrade",
                note="未确认首发前，伤停负面修正不应过度放大",
            ))

        return adjustments

    def as_report(self, features: MatchCalibrationFeatures) -> Dict[str, Any]:
        adjustments = self.adjustments_for(features)
        return {
            "calibration_id": self.payload.get("calibration_id"),
            "source": str(self.calibration_path),
            "applied": bool(adjustments),
            "adjustments": [item.to_dict() for item in adjustments],
        }


class ProjectCalibrationRuleBook:
    """Apply all available project calibration files."""

    def __init__(self, calibration_dir: Path | str = Path("data/calibration")):
        self.calibration_dir = Path(calibration_dir)
        self.jleague = CalibrationRuleBook(DEFAULT_JLEAGUE_CALIBRATION)
        self.international_payload = self._load_json(DEFAULT_INTERNATIONAL_CALIBRATION)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def as_report(self, features: MatchCalibrationFeatures) -> Dict[str, Any]:
        adjustments: List[CalibrationAdjustment] = []
        sources: List[str] = []

        if self.jleague.available:
            adjustments.extend(self.jleague.adjustments_for(features))
            sources.append(str(self.jleague.calibration_path))

        international_adjustments = self._international_adjustments(features)
        if international_adjustments:
            adjustments.extend(international_adjustments)
            sources.append(str(DEFAULT_INTERNATIONAL_CALIBRATION))

        return {
            "applied": bool(adjustments),
            "sources": sources,
            "adjustments": [item.to_dict() for item in adjustments],
            "warnings": self._warnings(features),
        }

    def _international_adjustments(self, features: MatchCalibrationFeatures) -> List[CalibrationAdjustment]:
        if not self.international_payload:
            return []
        adjustments: List[CalibrationAdjustment] = []
        is_international = (
            features.competition_type == "international_friendly"
            or "国际" in features.league
            or "friendly" in features.friendly_subtype
        )
        if not is_international:
            return adjustments

        if features.handicap_line is not None and 1.75 <= abs(features.handicap_line) <= 2.25:
            if features.handicap_push_supported_by_scores:
                adjustments.append(CalibrationAdjustment(
                    rule="international_two_goal_push_guard",
                    weight_delta=0.10,
                    target="handicap_push",
                    note="国际赛复盘显示±2场景需提高两球卡线保护",
                ))

        if features.four_goal_two_margin_btts_path:
            adjustments.append(CalibrationAdjustment(
                rule="three_one_one_three_risk_tier",
                weight_delta=0.08,
                target="scoreline_risk_tier",
                note="国际赛复盘显示3-1/1-3应保留在Top3-Top5风险比分池",
            ))

        if features.deep_favorite_context and features.friendly_subtype == "world_cup_final_warmup":
            adjustments.append(CalibrationAdjustment(
                rule="deep_favorite_context_crosscheck",
                weight_delta=0.06,
                target="LEG_context",
                note="大赛前热身深让球需由LEG确认，不只看强弱排名",
            ))
        return adjustments

    @staticmethod
    def _warnings(features: MatchCalibrationFeatures) -> List[str]:
        warnings: List[str] = []
        if features.competition_type == "international_friendly" and not features.final_lineup_confirmed:
            warnings.append("国际赛首发未确认，复盘规则只做降置信提示")
        if features.handicap_line is not None and abs(features.handicap_line) >= 2:
            warnings.append("深让球场景必须同步检查比分Top2与让球结算")
        return warnings


__all__ = [
    "CalibrationAdjustment",
    "CalibrationRuleBook",
    "MatchCalibrationFeatures",
    "ProjectCalibrationRuleBook",
]
