#!/usr/bin/env python3
"""Decision iteration layer.

This module turns post-match review lessons into a transparent pre-report
calibration pass. It accepts already-fused model probabilities and returns
small, auditable adjustments for result, handicap, total-goal buckets and
scoreline ranking.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


DEFAULT_RULEBOOK = Path("data/calibration/decision_iteration_rules.json")


@dataclass
class DecisionIterationFeatures:
    match_id: str = ""
    home: str = ""
    away: str = ""
    competition_type: str = ""
    stage: str = ""
    round_index: Optional[int] = None
    is_host: bool = False
    is_opening_match: bool = False
    group_direct_rivalry: bool = False
    weather_suppression: bool = False
    material_absence_team: str = ""
    lineup_uncertainty: bool = False
    qimen_conflict: bool = False
    favorite_side: str = ""
    favorite_win_prob: float = 0.0
    favorite_edge: float = 0.0
    handicap_line: Optional[float] = None
    handicap_cover: float = 0.0
    handicap_push: float = 0.0
    handicap_fail: float = 0.0
    result_probabilities: Dict[str, float] = field(default_factory=dict)
    handicap_probabilities: Dict[str, float] = field(default_factory=dict)
    total_distribution: Dict[str, float] = field(default_factory=dict)
    scorelines: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    volatility_score: float = 0.0
    high_scoring_risk: float = 0.0
    favorite_cover_trigger: bool = False

    @property
    def material_absence(self) -> bool:
        return bool(self.material_absence_team)

    @property
    def handicap_push_or_fail(self) -> float:
        return self.handicap_push + self.handicap_fail

    @classmethod
    def from_structured_match(
        cls,
        match: Dict[str, Any],
        *,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> "DecisionIterationFeatures":
        overrides = overrides or {}
        final_three = _as_float_list(match.get("final_three") or match.get("three_final"), 3)
        result = {
            "home": final_three[0],
            "draw": final_three[1],
            "away": final_three[2],
        }
        favorite_side, favorite_win_prob = max(result.items(), key=lambda item: item[1])
        sorted_probs = sorted(result.values(), reverse=True)
        favorite_edge = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) >= 2 else 0.0

        handicap_probs = _as_float_list(match.get("handicap_probs"), 3)
        handicap = {
            "cover": handicap_probs[0],
            "push": handicap_probs[1],
            "fail": handicap_probs[2],
        }
        tags = list(overrides.get("tags") or [])
        text_blob = " ".join(
            str(match.get(key, ""))
            for key in ["id", "dt", "venue", "weather_context", "deep_notes", "web"]
        )
        if "世界杯" in text_blob or "World Cup" in text_blob:
            competition_type = "world_cup"
        else:
            competition_type = str(overrides.get("competition_type") or "")
        if "第1轮" in text_blob or "Group Stage - 1" in text_blob or "揭幕" in text_blob:
            stage = "group"
            round_index = 1
        else:
            stage = str(overrides.get("stage") or "")
            round_index = overrides.get("round_index")

        weather_suppression = bool(overrides.get("weather_suppression", False))
        weather_text = str(match.get("venue", "")) + " " + str(match.get("weather_context", ""))
        if any(token in weather_text for token in ["高海拔", "31℃", "高温", "雨", "雷雨", "湿"]):
            weather_suppression = True

        qimen = match.get("qimen") or {}
        qimen_bias = str(qimen.get("qimen_bias") or "")
        qimen_conflict = bool(overrides.get("qimen_conflict", False))
        if qimen_bias:
            qimen_side = {"home": "home", "away": "away", "draw": "draw"}.get(qimen_bias)
            qimen_conflict = qimen_side is not None and qimen_side != favorite_side
        context = match.get("context") or {}

        return cls(
            match_id=str(match.get("id") or overrides.get("match_id") or ""),
            home=str(match.get("home") or ""),
            away=str(match.get("away") or ""),
            competition_type=str(overrides.get("competition_type") or competition_type),
            stage=str(overrides.get("stage") or stage),
            round_index=round_index if round_index is not None else overrides.get("round_index"),
            is_host=bool(overrides.get("is_host", False)),
            is_opening_match=bool(overrides.get("is_opening_match", "揭幕" in text_blob)),
            group_direct_rivalry=bool(overrides.get("group_direct_rivalry", False)),
            weather_suppression=weather_suppression,
            material_absence_team=str(overrides.get("material_absence_team") or ""),
            lineup_uncertainty=bool(overrides.get("lineup_uncertainty", False)),
            qimen_conflict=qimen_conflict,
            favorite_side=favorite_side,
            favorite_win_prob=favorite_win_prob,
            favorite_edge=favorite_edge,
            handicap_line=_safe_float(match.get("handicap")),
            handicap_cover=handicap["cover"],
            handicap_push=handicap["push"],
            handicap_fail=handicap["fail"],
            result_probabilities=result,
            handicap_probabilities=handicap,
            total_distribution=_normalize_distribution(match.get("exact_total_distribution") or {}),
            scorelines=list(match.get("scoreline") or []),
            tags=tags,
            volatility_score=float(overrides.get("volatility_score", context.get("volatility_score", 0.0)) or 0.0),
            high_scoring_risk=float(overrides.get("high_scoring_risk", context.get("high_scoring_risk", 0.0)) or 0.0),
            favorite_cover_trigger=bool(overrides.get("favorite_cover_trigger", context.get("favorite_cover_trigger", False))),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionIterationAdjustment:
    rule: str
    description: str
    target: str
    delta: float
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionIterationReport:
    match_id: str
    home: str
    away: str
    before_result: Dict[str, float]
    after_result: Dict[str, float]
    before_handicap: Dict[str, float]
    after_handicap: Dict[str, float]
    before_total_distribution: Dict[str, float]
    after_total_distribution: Dict[str, float]
    before_scorelines: List[Dict[str, Any]]
    after_scorelines: List[Dict[str, Any]]
    applied_rules: List[str]
    adjustments: List[DecisionIterationAdjustment]
    warnings: List[str]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["adjustments"] = [item.to_dict() for item in self.adjustments]
        return payload


class DecisionIterationEngine:
    """Apply a small rule-based calibration pass after model fusion."""

    def __init__(self, rulebook_path: Path | str = DEFAULT_RULEBOOK):
        self.rulebook_path = Path(rulebook_path)
        self.rulebook = self._load_rulebook()
        defaults = self.rulebook.get("defaults") or {}
        self.max_prob_delta = float(defaults.get("max_single_probability_delta", 0.08))
        self.max_total_delta = float(defaults.get("max_total_bucket_delta", 0.10))

    def apply(self, features: DecisionIterationFeatures) -> DecisionIterationReport:
        result = dict(features.result_probabilities)
        handicap = dict(features.handicap_probabilities)
        total = dict(features.total_distribution)
        before_scorelines = [dict(item) for item in features.scorelines]
        score_preferences: List[str] = []
        boost_low_scores: List[str] = []
        risk_score_preferences: List[str] = []
        adjustments: List[DecisionIterationAdjustment] = []
        applied_rules: List[str] = []
        notes: List[str] = []
        warnings: List[str] = []

        for rule_id, rule in (self.rulebook.get("rules") or {}).items():
            if not self._rule_matches(rule_id, features):
                continue
            applied_rules.append(rule_id)
            description = str(rule.get("description") or rule_id)
            adj = rule.get("adjustments") or {}
            self._apply_result_adjustments(rule_id, description, adj, features, result, adjustments)
            self._apply_handicap_adjustments(rule_id, description, adj, features, handicap, adjustments)
            self._apply_total_adjustments(rule_id, description, adj, total, adjustments)
            score_preferences.extend(adj.get("prefer_scores") or [])
            boost_low_scores.extend(adj.get("boost_low_score_scores") or [])
            risk_score_preferences.extend(adj.get("prefer_risk_scores") or [])

        result = _normalize_distribution(result)
        handicap = _normalize_distribution(handicap)
        result = self._cap_distribution_shift(features.result_probabilities, result)
        handicap = self._cap_distribution_shift(features.handicap_probabilities, handicap)
        result = _normalize_distribution(result)
        handicap = _normalize_distribution(handicap)
        total = _normalize_distribution(total)
        after_scorelines = self._rerank_scorelines(before_scorelines, score_preferences, boost_low_scores, risk_score_preferences)

        if not applied_rules:
            notes.append("未触发决策迭代规则，沿用原模型输出")
        else:
            notes.append("决策迭代层只做小幅校准，不替代原始模型概率")
        if features.lineup_uncertainty:
            warnings.append("首发仍有不确定性，临场名单发布后需要二次校准")
        if features.weather_suppression:
            notes.append("天气/场地触发节奏压制检查")
        if features.qimen_conflict:
            notes.append("奇门与数据模型冲突，仅做低权重风险提示")

        return DecisionIterationReport(
            match_id=features.match_id,
            home=features.home,
            away=features.away,
            before_result=_round_distribution(features.result_probabilities),
            after_result=_round_distribution(result),
            before_handicap=_round_distribution(features.handicap_probabilities),
            after_handicap=_round_distribution(handicap),
            before_total_distribution=_round_distribution(features.total_distribution),
            after_total_distribution=_round_distribution(total),
            before_scorelines=before_scorelines[:7],
            after_scorelines=after_scorelines[:7],
            applied_rules=applied_rules,
            adjustments=adjustments,
            warnings=warnings,
            notes=notes,
        )

    def _load_rulebook(self) -> Dict[str, Any]:
        if not self.rulebook_path.exists():
            return {"rules": {}, "defaults": {}}
        return json.loads(self.rulebook_path.read_text(encoding="utf-8"))

    def _rule_matches(self, rule_id: str, features: DecisionIterationFeatures) -> bool:
        if rule_id == "worldcup_group_opening":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
            )
        if rule_id == "worldcup_group_opening_favorite_heat_discount":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.favorite_win_prob >= 0.50
                and features.handicap_push_or_fail >= 0.48
            )
        if rule_id == "worldcup_handicap_over_result_preference":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.handicap_push_or_fail >= 0.55
            )
        if rule_id == "host_opener_pressure":
            return features.is_host and features.is_opening_match
        if rule_id == "host_high_press_opening_upside":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.is_host
                and self._has_tag(features, "host_high_press")
                and not features.weather_suppression
            )
        if rule_id == "host_inexperienced_finishing_discount":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.is_host
                and self._has_tag(features, "host_inexperienced_finishing_risk")
                and features.favorite_side == "home"
            )
        if rule_id == "set_piece_underdog_equalizer_risk":
            return self._has_tag(features, "set_piece_underdog_threat")
        if rule_id == "favorite_win_not_depth":
            return features.favorite_win_prob >= 0.55 and features.handicap_push_or_fail >= 0.52
        if rule_id == "weak_handicap_depth":
            return features.handicap_fail >= 0.55
        if rule_id == "weather_suppresses_tempo":
            return features.weather_suppression
        if rule_id == "material_absence_uncertain_lineup":
            return features.material_absence
        if rule_id == "balanced_direct_match":
            return features.group_direct_rivalry and features.favorite_edge <= 0.12
        if rule_id == "top_table_stalemate_guard":
            return (
                (self._has_tag(features, "top_table_direct_rival") or self._has_tag(features, "strong_defense_opponent"))
                and features.favorite_win_prob <= 0.58
                and features.favorite_edge <= 0.25
            )
        if rule_id == "qimen_conflict_low_weight":
            return features.qimen_conflict
        if rule_id == "ordinary_friendly_low_tempo_guard":
            return (
                features.competition_type == "international_friendly"
                and features.lineup_uncertainty
                and features.high_scoring_risk <= 0.15
                and not features.favorite_cover_trigger
                and features.volatility_score >= 0.62
            )
        if rule_id == "favorite_late_collapse_upside":
            four_plus = self._total_4plus(features)
            return (
                features.favorite_win_prob >= 0.68
                and features.handicap_line is not None
                and abs(features.handicap_line) >= 1.75
                and (features.high_scoring_risk >= 0.12 or four_plus >= 0.22 or features.favorite_cover_trigger)
            )
        if rule_id == "worldcup_massive_favorite_blowout_override":
            four_plus = self._total_4plus(features)
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.favorite_win_prob >= 0.78
                and features.handicap_line is not None
                and abs(features.handicap_line) >= 2.5
                and (
                    features.high_scoring_risk >= 0.18
                    or four_plus >= 0.30
                    or self._has_tag(features, "massive_favorite_depth")
                )
            )
        if rule_id == "worldcup_transition_2_2_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and 0.40 <= features.favorite_win_prob <= 0.62
                and (
                    self._has_tag(features, "organized_transition_underdog")
                    or self._has_tag(features, "set_piece_underdog_threat")
                    or self._has_tag(features, "comeback_equalizer_risk")
                )
            )
        if rule_id == "worldcup_knockout_favorite_draw_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and 0.62 <= features.favorite_win_prob <= 0.76
                and features.result_probabilities.get("draw", 0.0) >= 0.16
                and features.handicap_push >= 0.20
                and (
                    self._has_tag(features, "knockout_90min_draw_risk")
                    or self._has_tag(features, "favorite_win_not_clean_sheet")
                    or self._has_tag(features, "material_home_absence")
                    or self._has_tag(features, "low_block_opponent")
                )
            )
        if rule_id == "worldcup_knockout_one_goal_favorite_both_score_guard":
            three_plus = sum(float(features.total_distribution.get(key, 0.0) or 0.0) for key in ["3", "4", "5", "6", "7_plus", "7+"])
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and 0.48 <= features.favorite_win_prob <= 0.62
                and three_plus >= 0.28
                and (
                    self._has_tag(features, "favorite_win_not_depth")
                    or self._has_tag(features, "organized_transition_underdog")
                    or self._has_tag(features, "favorite_win_not_clean_sheet")
                    or self._has_tag(features, "material_home_absence")
                )
            )
        if rule_id == "worldcup_knockout_plus_one_draw_anchor":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and features.handicap_fail >= 0.50
                and features.result_probabilities.get("draw", 0.0) >= 0.30
                and features.favorite_win_prob <= 0.43
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "strong_defense_opponent")
                    or self._has_tag(features, "top_table_stalemate_guard")
                )
            )
        if rule_id == "worldcup_knockout_home_favorite_clean_sheet_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and features.favorite_side == "home"
                and 0.43 <= features.favorite_win_prob <= 0.55
                and features.handicap_fail >= 0.45
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "weather_suppression")
                    or self._has_tag(features, "top_table_stalemate_guard")
                )
            )
        if rule_id == "worldcup_knockout_favorite_cold_loss_guard":
            three_plus = sum(float(features.total_distribution.get(key, 0.0) or 0.0) for key in ["3", "4", "5", "6", "7_plus", "7+"])
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and 0.50 <= features.favorite_win_prob <= 0.62
                and features.result_probabilities.get("draw", 0.0) >= 0.22
                and three_plus >= 0.35
                and (
                    self._has_tag(features, "organized_transition_underdog")
                    or self._has_tag(features, "set_piece_underdog_threat")
                    or self._has_tag(features, "favorite_flat_attack")
                    or self._has_tag(features, "late_game_volatility")
                )
            )
        if rule_id == "plus_one_push_split_guard":
            return (
                features.handicap_line is not None
                and abs(features.handicap_line) == 1
                and features.handicap_push >= 0.23
                and features.handicap_cover >= 0.45
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "one_goal_margin_risk")
                    or self._has_tag(features, "knockout_90min_draw_risk")
                    or self._has_tag(features, "derby_or_direct_rival")
                )
            )
        if rule_id == "plus_one_away_push_not_main_guard":
            return (
                features.handicap_line is not None
                and features.handicap_line == -1
                and features.handicap_fail >= 0.56
                and features.handicap_push >= 0.20
                and features.favorite_side == "home"
                and features.favorite_win_prob >= 0.36
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "one_goal_margin_risk")
                    or self._has_tag(features, "weak_handicap_depth")
                    or self._has_tag(features, "derby_or_direct_rival")
                )
            )
        if rule_id == "league_away_favorite_draw_anchor":
            return (
                features.competition_type in {"league", "kleague", "allsvenskan"}
                and features.favorite_side == "away"
                and 0.55 <= features.favorite_win_prob <= 0.66
                and features.result_probabilities.get("draw", 0.0) >= 0.20
                and (
                    self._has_tag(features, "away_favorite_draw_risk")
                    or self._has_tag(features, "bottom_home_resistance")
                    or self._has_tag(features, "post_break_rust")
                    or self._has_tag(features, "low_block_opponent")
                )
            )
        if rule_id == "league_clear_favorite_upper_score_guard":
            return (
                features.competition_type in {"league", "kleague", "allsvenskan"}
                and features.favorite_win_prob >= 0.60
                and (
                    features.high_scoring_risk >= 0.18
                    or self._total_4plus(features) >= 0.30
                    or self._has_tag(features, "clear_favorite_depth")
                    or self._has_tag(features, "opponent_defensive_collapse")
                )
            )
        if rule_id == "ucl_first_leg_heavy_favorite_total_temper_guard":
            return (
                features.competition_type in {"league", "ucl", "champions_league"}
                and features.stage in {"qualifying", "first_leg"}
                and features.favorite_win_prob >= 0.70
                and features.result_probabilities.get("away", 0.0) <= 0.12
                and (
                    self._has_tag(features, "first_leg_control")
                    or self._has_tag(features, "travel_disruption")
                    or self._has_tag(features, "clear_favorite_depth")
                )
            )
        if rule_id == "worldcup_knockout_elite_rival_low_total_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and 0.48 <= features.favorite_win_prob <= 0.56
                and features.result_probabilities.get("draw", 0.0) >= 0.22
                and features.handicap_push >= 0.22
                and (
                    self._has_tag(features, "elite_direct_rival")
                    or self._has_tag(features, "tactical_derby")
                    or self._has_tag(features, "knockout_90min_draw_risk")
                )
            )
        if rule_id == "worldcup_knockout_balanced_goalless_draw_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and features.result_probabilities.get("draw", 0.0) >= 0.27
                and features.favorite_edge <= 0.14
                and features.handicap_cover >= 0.50
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "elite_direct_rival")
                    or self._has_tag(features, "knockout_90min_draw_risk")
                    or self._has_tag(features, "strong_defense_opponent")
                )
            )
        if rule_id == "worldcup_knockout_favorite_concedes_high_tail_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "knockout"
                and features.favorite_win_prob >= 0.64
                and features.high_scoring_risk >= 0.22
                and self._total_4plus(features) >= 0.28
                and (
                    self._has_tag(features, "favorite_win_not_clean_sheet")
                    or self._has_tag(features, "organized_transition_underdog")
                    or self._has_tag(features, "set_piece_underdog_threat")
                    or self._has_tag(features, "low_block_opponent")
                )
            )
        if rule_id == "balanced_open_league_six_goal_tail_guard":
            return (
                features.competition_type in {"league", "allsvenskan"}
                and features.favorite_edge <= 0.08
                and (
                    self._total_4plus(features) >= 0.38
                    or self._has_tag(features, "open_league_high_variance")
                    or self._has_tag(features, "both_teams_score_tail")
                )
            )
        if rule_id == "worldcup_group_draw_wave_guard":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and self._has_tag(features, "group_draw_wave")
            )
        if rule_id == "worldcup_group_final_favorite_draw_enough_discount":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 3
                and features.favorite_win_prob >= 0.45
                and (
                    self._has_tag(features, "favorite_draw_enough")
                    or self._has_tag(features, "favorite_conservative_qualification_path")
                )
            )
        if rule_id == "worldcup_group_final_underdog_must_win_low_score":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 3
                and (
                    self._has_tag(features, "underdog_must_win")
                    or self._has_tag(features, "opponent_must_win")
                )
            )
        if rule_id == "worldcup_group_final_locked_top_host_depth":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 3
                and self._has_tag(features, "locked_top")
                and (
                    self._has_tag(features, "host_depth")
                    or self._has_tag(features, "bench_depth_advantage")
                    or self._has_tag(features, "opponent_must_win")
                )
            )
        if rule_id == "worldcup_group_final_favorite_win_both_score_tail":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 3
                and features.favorite_win_prob >= 0.58
                and (
                    features.high_scoring_risk >= 0.18
                    or self._has_tag(features, "eliminated_opponent_no_pressure")
                    or self._has_tag(features, "favorite_win_not_clean_sheet")
                    or self._has_tag(features, "must_chase_goal_difference")
                )
            )
        if rule_id == "favorite_rotation_low_block_depth_discount":
            return (
                features.competition_type == "world_cup"
                and features.stage == "group"
                and features.round_index == 1
                and features.favorite_win_prob >= 0.65
                and (
                    self._has_tag(features, "favorite_rotation_risk")
                    or self._has_tag(features, "low_block_opponent")
                    or self._has_tag(features, "elite_goalkeeper_risk")
                )
            )
        if rule_id == "plus_one_underdog_cover_guard":
            return (
                features.handicap_line is not None
                and features.handicap_line == 1
                and (
                    self._has_tag(features, "plus_one_cover_risk")
                    or self._has_tag(features, "travel_disruption")
                    or self._has_tag(features, "low_block_opponent")
                )
            )
        if rule_id == "cold_low_score_near_top_promote":
            return self._has_tag(features, "cold_low_score_near_top") and features.favorite_edge <= 0.18
        if rule_id == "away_depth_undervalued":
            return (
                features.favorite_side == "away"
                and (self._has_tag(features, "away_depth_upside") or self._has_tag(features, "home_defensive_leak"))
            )
        if rule_id == "open_league_high_score_upside":
            return self._has_tag(features, "open_league_high_variance") or features.high_scoring_risk >= 0.22
        return False

    @staticmethod
    def _has_tag(features: DecisionIterationFeatures, tag: str) -> bool:
        tags = {str(item) for item in features.tags}
        return tag in tags

    @staticmethod
    def _total_4plus(features: DecisionIterationFeatures) -> float:
        return sum(
            float(features.total_distribution.get(key, 0.0) or 0.0)
            for key in ["4", "5", "6", "7_plus", "7+"]
        )

    def _apply_result_adjustments(
        self,
        rule_id: str,
        description: str,
        adj: Dict[str, Any],
        features: DecisionIterationFeatures,
        result: Dict[str, float],
        adjustments: List[DecisionIterationAdjustment],
    ) -> None:
        mapping: List[Tuple[str, str, float]] = []
        if "favorite_result_delta" in adj:
            mapping.append(("favorite_result_delta", features.favorite_side, float(adj["favorite_result_delta"])))
        if "draw_delta" in adj:
            mapping.append(("draw_delta", "draw", float(adj["draw_delta"])))
        if "underdog_delta" in adj:
            underdog = self._underdog_side(features)
            mapping.append(("underdog_delta", underdog, float(adj["underdog_delta"])))
        if "affected_team_result_delta" in adj and features.material_absence_team:
            side = self._team_to_side(features.material_absence_team, features)
            mapping.append(("affected_team_result_delta", side, float(adj["affected_team_result_delta"])))
        if "opposition_result_delta" in adj and features.material_absence_team:
            side = self._opposition_side(self._team_to_side(features.material_absence_team, features))
            mapping.append(("opposition_result_delta", side, float(adj["opposition_result_delta"])))

        for target_name, side, delta in mapping:
            if not side or side not in result:
                continue
            bounded = self._bound_delta(delta)
            result[side] = max(0.0, result.get(side, 0.0) + bounded)
            adjustments.append(DecisionIterationAdjustment(
                rule=rule_id,
                description=description,
                target=f"result.{side}",
                delta=bounded,
                note=target_name,
            ))

    def _apply_handicap_adjustments(
        self,
        rule_id: str,
        description: str,
        adj: Dict[str, Any],
        features: DecisionIterationFeatures,
        handicap: Dict[str, float],
        adjustments: List[DecisionIterationAdjustment],
    ) -> None:
        direct = {
            "handicap_cover_delta": "cover",
            "handicap_push_delta": "push",
            "handicap_fail_delta": "fail",
        }
        for source, target in direct.items():
            if source not in adj:
                continue
            delta = self._bound_delta(float(adj[source]))
            handicap[target] = max(0.0, handicap.get(target, 0.0) + delta)
            adjustments.append(DecisionIterationAdjustment(
                rule=rule_id,
                description=description,
                target=f"handicap.{target}",
                delta=delta,
                note=source,
            ))

        if features.material_absence_team and "affected_handicap_cover_delta" in adj:
            affected_side = self._team_to_side(features.material_absence_team, features)
            affects_cover = affected_side == "home" and (features.handicap_line or 0) < 0
            affects_cover = affects_cover or (affected_side == "away" and (features.handicap_line or 0) > 0)
            cover_key = "cover" if affects_cover else "fail"
            fail_key = "fail" if affects_cover else "cover"
            cover_delta = self._bound_delta(float(adj.get("affected_handicap_cover_delta", 0.0)))
            fail_delta = self._bound_delta(float(adj.get("affected_handicap_fail_delta", 0.0)))
            handicap[cover_key] = max(0.0, handicap.get(cover_key, 0.0) + cover_delta)
            handicap[fail_key] = max(0.0, handicap.get(fail_key, 0.0) + fail_delta)
            adjustments.append(DecisionIterationAdjustment(
                rule=rule_id,
                description=description,
                target=f"handicap.{cover_key}",
                delta=cover_delta,
                note="affected_handicap_cover_delta",
            ))
            adjustments.append(DecisionIterationAdjustment(
                rule=rule_id,
                description=description,
                target=f"handicap.{fail_key}",
                delta=fail_delta,
                note="affected_handicap_fail_delta",
            ))

    def _apply_total_adjustments(
        self,
        rule_id: str,
        description: str,
        adj: Dict[str, Any],
        total: Dict[str, float],
        adjustments: List[DecisionIterationAdjustment],
    ) -> None:
        move = float(adj.get("move_total_from_3plus_to_1_2", 0.0) or 0.0)
        if move <= 0 or not total:
            pass
        else:
            move = min(move, self.max_total_delta)
            high_keys = ["3", "4", "5", "6", "7_plus"]
            low_keys = ["1", "2"]
            high_available = sum(total.get(key, 0.0) for key in high_keys)
            if high_available > 0:
                actual_move = min(move, high_available * 0.35)
                for key in high_keys:
                    share = (total.get(key, 0.0) / high_available) if high_available else 0.0
                    total[key] = max(0.0, total.get(key, 0.0) - actual_move * share)
                low_available = sum(total.get(key, 0.0) for key in low_keys) or 1.0
                for key in low_keys:
                    share = total.get(key, 0.0) / low_available
                    total[key] = total.get(key, 0.0) + actual_move * share
                adjustments.append(DecisionIterationAdjustment(
                    rule=rule_id,
                    description=description,
                    target="total.3plus_to_1_2",
                    delta=actual_move,
                    note="move_total_from_3plus_to_1_2",
                ))

        upside_move = float(adj.get("move_total_from_1_2_to_4_5", 0.0) or 0.0)
        if upside_move <= 0 or not total:
            return
        upside_move = min(upside_move, self.max_total_delta)
        source_keys = ["1", "2"]
        target_keys = ["4", "5"]
        source_available = sum(total.get(key, 0.0) for key in source_keys)
        if source_available <= 0:
            return
        actual_upside_move = min(upside_move, source_available * 0.22)
        for key in source_keys:
            share = total.get(key, 0.0) / source_available
            total[key] = max(0.0, total.get(key, 0.0) - actual_upside_move * share)
        target_available = sum(total.get(key, 0.0) for key in target_keys) or 1.0
        for key in target_keys:
            share = total.get(key, 0.0) / target_available
            total[key] = total.get(key, 0.0) + actual_upside_move * share
        adjustments.append(DecisionIterationAdjustment(
            rule=rule_id,
            description=description,
            target="total.1_2_to_4_5",
            delta=actual_upside_move,
            note="move_total_from_1_2_to_4_5",
        ))

    @staticmethod
    def _rerank_scorelines(
        scorelines: Sequence[Dict[str, Any]],
        preferred_scores: Sequence[str],
        low_score_boosts: Sequence[str],
        risk_preferred_scores: Sequence[str],
    ) -> List[Dict[str, Any]]:
        preferred: Dict[str, int] = {}
        for idx, score in enumerate(preferred_scores):
            preferred.setdefault(score, idx)
        low_boost = set(low_score_boosts)
        risk_preferred: Dict[str, int] = {}
        for idx, score in enumerate(risk_preferred_scores):
            risk_preferred.setdefault(score, idx)

        def sort_key(item: Dict[str, Any]) -> Tuple[int, float]:
            score = str(item.get("score") or "")
            preference_rank = preferred.get(score, 999)
            probability = _scoreline_probability(item)
            return (preference_rank, -probability)

        original_order: Dict[str, int] = {
            str(item.get("score") or ""): idx
            for idx, item in enumerate(scorelines)
        }
        conservative_pool = [
            dict(item)
            for item in scorelines
            if original_order.get(str(item.get("score") or ""), 999) <= 2
        ]
        conservative_seed = [dict(item) for item in sorted(conservative_pool, key=sort_key)]
        conservative = conservative_seed[:2]
        conservative_scores = {str(item.get("score") or "") for item in conservative}
        rest = [dict(item) for item in scorelines if str(item.get("score") or "") not in conservative_scores]

        def risk_sort_key(item: Dict[str, Any]) -> Tuple[int, int, float]:
            score = str(item.get("score") or "")
            risk_rank = risk_preferred.get(score, 999)
            low_rank = 0 if score in low_boost else 1
            probability = _scoreline_probability(item)
            return (risk_rank, low_rank, -probability)

        ranked = conservative + [dict(item) for item in sorted(rest, key=risk_sort_key)]
        conservative_cut = 2
        for idx, item in enumerate(ranked, start=1):
            item["decision_iteration_rank"] = idx
            item["decision_iteration_tier"] = "conservative" if idx <= conservative_cut else "risk"
        return ranked

    def _cap_distribution_shift(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
    ) -> Dict[str, float]:
        capped: Dict[str, float] = {}
        keys = set(before) | set(after)
        for key in keys:
            original = float(before.get(key, 0.0) or 0.0)
            adjusted = float(after.get(key, 0.0) or 0.0)
            lower = max(0.0, original - self.max_prob_delta)
            upper = min(1.0, original + self.max_prob_delta)
            capped[key] = max(lower, min(upper, adjusted))
        return capped

    def _bound_delta(self, delta: float) -> float:
        return max(-self.max_prob_delta, min(self.max_prob_delta, delta))

    @staticmethod
    def _team_to_side(team: str, features: DecisionIterationFeatures) -> str:
        if team in {"home", features.home}:
            return "home"
        if team in {"away", features.away}:
            return "away"
        if team == "draw":
            return "draw"
        return ""

    @staticmethod
    def _opposition_side(side: str) -> str:
        if side == "home":
            return "away"
        if side == "away":
            return "home"
        return "draw"

    @staticmethod
    def _underdog_side(features: DecisionIterationFeatures) -> str:
        sides = ["home", "draw", "away"]
        candidates = [(side, prob) for side, prob in features.result_probabilities.items() if side in sides]
        candidates = [item for item in candidates if item[0] != features.favorite_side and item[0] != "draw"]
        if not candidates:
            return "away" if features.favorite_side == "home" else "home"
        return min(candidates, key=lambda item: item[1])[0]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _scoreline_probability(item: Dict[str, Any]) -> float:
    for key in ["probability", "local_probability", "final_probability", "raw_probability", "poisson_probability"]:
        value = _safe_float(item.get(key))
        if value is not None:
            return value
    market_value = _safe_float(item.get("market_value"))
    if market_value and market_value > 1:
        return 1.0 / market_value
    return 0.0


def _as_float_list(value: Any, length: int) -> List[float]:
    if not isinstance(value, list):
        return [0.0] * length
    items = []
    for idx in range(length):
        items.append(float(value[idx] if idx < len(value) and value[idx] is not None else 0.0))
    return items


def _normalize_distribution(distribution: Dict[str, Any]) -> Dict[str, float]:
    values = {str(key): max(0.0, float(value or 0.0)) for key, value in distribution.items()}
    total = sum(values.values())
    if total <= 0:
        return values
    return {key: value / total for key, value in values.items()}


def _round_distribution(distribution: Dict[str, Any]) -> Dict[str, float]:
    return {str(key): round(float(value or 0.0), 4) for key, value in distribution.items()}


__all__ = [
    "DecisionIterationAdjustment",
    "DecisionIterationEngine",
    "DecisionIterationFeatures",
    "DecisionIterationReport",
]
