#!/usr/bin/env python3
"""LEG depth-check model.

LEG = Line + Expected Goals + Game Context.

This layer answers one focused question:
whether a favorite is supported to win deep, or only supported to win.
It does not replace result, handicap, goals, scoreline, qimen, or LLM layers.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class LEGSignal:
    line_score: float
    expected_goals_score: float
    game_context_score: float
    total_score: float
    home_leg_expected_goals: float
    away_leg_expected_goals: float
    home_depth_score_10: float
    away_depth_score_10: float
    home_line_score_10: float
    away_line_score_10: float
    home_xg_score_10: float
    away_xg_score_10: float
    home_context_score_10: float
    away_context_score_10: float
    depth_gap_10: float
    depth_direction: str
    scoreline_hint: str
    confidence: str
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LEGModel:
    """Lightweight favorite-depth validator."""

    @staticmethod
    def analyze(
        market_signal: Any,
        handicap_signal: Any,
        goals_signal: Any,
        scoreline_signal: Any,
        context: Any,
        xg_signal: Any = None,
    ) -> LEGSignal:
        notes: List[str] = []
        warnings: List[str] = []

        line_score = LEGModel._line_score(market_signal, handicap_signal, notes, warnings)
        expected_goals_score = LEGModel._expected_goals_score(goals_signal, scoreline_signal, notes, warnings, xg_signal)
        game_context_score = LEGModel._game_context_score(context, notes, warnings)

        total_score = 0.38 * line_score + 0.34 * expected_goals_score + 0.28 * game_context_score
        depth_direction = LEGModel._depth_direction(total_score, line_score, expected_goals_score, game_context_score)
        scoreline_hint = LEGModel._scoreline_hint(depth_direction, scoreline_signal, goals_signal)
        confidence = LEGModel._confidence(total_score, line_score, expected_goals_score, game_context_score, warnings)
        quant = LEGModel._quantify_team_depth(
            market_signal=market_signal,
            line_score=line_score,
            expected_goals_score=expected_goals_score,
            game_context_score=game_context_score,
            total_score=total_score,
            goals_signal=goals_signal,
            xg_signal=xg_signal,
        )

        if abs(line_score - expected_goals_score) >= 0.28:
            warnings.append("L与E分歧较大，强弱深度需要降一级处理")
        if game_context_score <= 0.42:
            warnings.append("G语境偏弱，需防轮换、节奏控制或临场降速")

        return LEGSignal(
            line_score=round(line_score, 3),
            expected_goals_score=round(expected_goals_score, 3),
            game_context_score=round(game_context_score, 3),
            total_score=round(total_score, 3),
            home_leg_expected_goals=quant["home_leg_expected_goals"],
            away_leg_expected_goals=quant["away_leg_expected_goals"],
            home_depth_score_10=quant["home_depth_score_10"],
            away_depth_score_10=quant["away_depth_score_10"],
            home_line_score_10=quant["home_line_score_10"],
            away_line_score_10=quant["away_line_score_10"],
            home_xg_score_10=quant["home_xg_score_10"],
            away_xg_score_10=quant["away_xg_score_10"],
            home_context_score_10=quant["home_context_score_10"],
            away_context_score_10=quant["away_context_score_10"],
            depth_gap_10=quant["depth_gap_10"],
            depth_direction=depth_direction,
            scoreline_hint=scoreline_hint,
            confidence=confidence,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _line_score(market_signal: Any, handicap_signal: Any, notes: List[str], warnings: List[str]) -> float:
        score = 0.50
        market_strength = getattr(market_signal, "market_strength", "") if market_signal else ""
        disagreement = getattr(market_signal, "disagreement", "") if market_signal else ""
        asian_handicap = LEGModel._safe_float(getattr(market_signal, "asian_handicap", None)) if market_signal else None
        line = LEGModel._safe_float(getattr(handicap_signal, "line", None)) if handicap_signal else None
        cover_probability = LEGModel._safe_float(getattr(handicap_signal, "cover_probability", None)) if handicap_signal else None
        fail_probability = LEGModel._safe_float(getattr(handicap_signal, "fail_probability", None)) if handicap_signal else None
        push_probability = LEGModel._safe_float(getattr(handicap_signal, "push_probability", None)) if handicap_signal else None

        if market_strength in {"strong_home_deep_handicap", "strong_away_deep_handicap"}:
            score += 0.18
            notes.append("L: 市场深度强，支持热门方赢深")
        elif market_strength == "deep_handicap":
            score += 0.10
            notes.append("L: 市场深度较深，但需要结算层确认")
        elif market_strength == "medium_handicap":
            score += 0.04
            notes.append("L: 市场深度中等")
        else:
            notes.append("L: 市场深度不强")

        if asian_handicap is not None and line is not None:
            if abs(asian_handicap) >= abs(line) - 0.15:
                score += 0.07
                notes.append("L: 亚洲线与让球层接近，深度一致性较好")
            else:
                score -= 0.07
                warnings.append("L: 亚洲线浅于让球层，赢深信号打折")

        if cover_probability is not None and fail_probability is not None:
            edge = cover_probability - fail_probability
            if edge >= 0.12:
                score += 0.15
                notes.append("L: 让球胜端优势明显")
            elif edge >= 0.04:
                score += 0.07
                notes.append("L: 让球胜端略优")
            elif edge <= -0.12:
                score -= 0.16
                warnings.append("L: 让球负端更高，热门方赢深不稳")
            elif edge <= -0.04:
                score -= 0.08
                warnings.append("L: 让球负端略高，赢深需保守")
            if push_probability is not None and push_probability >= 0.22:
                score -= 0.03
                notes.append("L: 让球平占比不低，提示卡线")

        if disagreement == "high":
            score -= 0.13
            warnings.append("L: 市场分歧高")
        elif disagreement == "medium":
            score -= 0.06
            warnings.append("L: 市场分歧中等")

        return LEGModel._clamp(score)

    @staticmethod
    def _expected_goals_score(
        goals_signal: Any,
        scoreline_signal: Any,
        notes: List[str],
        warnings: List[str],
        xg_signal: Any = None,
    ) -> float:
        score = 0.50
        final_mean = LEGModel._safe_float(getattr(goals_signal, "final_goal_mean", None)) if goals_signal else None
        exact = getattr(goals_signal, "exact_distribution", {}) if goals_signal else {}
        top_scores = getattr(scoreline_signal, "top_scores", []) if scoreline_signal else []
        xg_edge = LEGModel._safe_float(getattr(xg_signal, "xg_edge", None)) if xg_signal else None
        xga_edge = LEGModel._safe_float(getattr(xg_signal, "xga_edge", None)) if xg_signal else None
        xg_source = getattr(xg_signal, "source", "") if xg_signal else ""

        if final_mean is not None:
            if final_mean >= 3.35:
                score += 0.16
                notes.append("E: 总球均值偏高")
            elif final_mean >= 3.00:
                score += 0.09
                notes.append("E: 总球均值接近3球")
            elif final_mean <= 2.35:
                score -= 0.11
                warnings.append("E: 总球均值偏低")

        if exact:
            high_share = sum(float(exact.get(key, 0.0) or 0.0) for key in ["4", "5", "6", "7_plus"])
            mid_share = sum(float(exact.get(key, 0.0) or 0.0) for key in ["2", "3"])
            if high_share >= 0.42:
                score += 0.10
                notes.append("E: 4球以上合计占比高")
            elif high_share >= 0.34:
                score += 0.04
                notes.append("E: 4球以上有上沿")
            if mid_share >= 0.40 and high_share < 0.38:
                score -= 0.04
                notes.append("E: 2-3球中枢较稳，深度不过度放大")

        if top_scores:
            conservative = top_scores[:2]
            risk = top_scores[2:5]
            conservative_margins = [abs(int(item.get("margin", 0) or 0)) for item in conservative]
            risk_margins = [abs(int(item.get("margin", 0) or 0)) for item in risk]
            if conservative_margins and max(conservative_margins) >= 3:
                score += 0.10
                notes.append("E: 保守比分位已支持三球差")
            elif conservative_margins and max(conservative_margins) <= 2:
                score -= 0.04
                notes.append("E: 保守比分位更偏1-2球差")
            if risk_margins and max(risk_margins) >= 3:
                score += 0.04
                notes.append("E: 风险比分位保留赢深路径")

        if xg_edge is not None:
            if xg_edge >= 0.75:
                score += 0.12
                notes.append("E: xG/proxy xG优势明显，支持热门方创造力")
            elif xg_edge >= 0.35:
                score += 0.06
                notes.append("E: xG/proxy xG有优势")
            elif xg_edge <= 0.10:
                score -= 0.08
                warnings.append("E: xG/proxy xG优势不足，强队深度需降级")
        if xga_edge is not None:
            if xga_edge >= 0.45:
                score += 0.06
                notes.append("E: 对手防守风险更高，深度条件增强")
            elif xga_edge <= -0.20:
                score -= 0.05
                warnings.append("E: 热门方防守风险不低，需防丢球")
        if xg_signal:
            if xg_source == "api_actual":
                notes.append("E: 已优先采用API真实xG/xGA")
            else:
                notes.append("E: 真实xG缺失，采用赛前proxy xG/xGA")

        return LEGModel._clamp(score)

    @staticmethod
    def _game_context_score(context: Any, notes: List[str], warnings: List[str]) -> float:
        score = 0.50
        if not context:
            warnings.append("G: 比赛语境缺失")
            return score

        friendly_subtype = getattr(context, "friendly_subtype", "")
        motivation = LEGModel._safe_float(getattr(context, "motivation_score", 0.0)) or 0.0
        volatility = LEGModel._safe_float(getattr(context, "volatility_score", 0.0)) or 0.0
        high_scoring_risk = LEGModel._safe_float(getattr(context, "high_scoring_risk", 0.0)) or 0.0
        favorite_cover_trigger = bool(getattr(context, "favorite_cover_trigger", False))

        if friendly_subtype == "world_cup_final_warmup":
            score += 0.08
            notes.append("G: 大赛前最后热身，不默认降温")
        elif "friendly" in str(friendly_subtype):
            score -= 0.04
            warnings.append("G: 普通友谊赛轮换风险较高")

        if motivation >= 0.35:
            score += 0.10
            notes.append("G: 战意/演练动机较强")
        elif motivation <= 0.12:
            score -= 0.04

        if high_scoring_risk >= 0.25:
            score += 0.07
            notes.append("G: 后段开放风险较高")
        elif high_scoring_risk <= 0.08:
            score -= 0.03

        if favorite_cover_trigger:
            score += 0.08
            notes.append("G: 强队深度触发条件成立")

        if volatility >= 0.75:
            score -= 0.09
            warnings.append("G: 阵容/换人波动高")
        elif volatility >= 0.65:
            score -= 0.04
            notes.append("G: 波动中等偏高")

        return LEGModel._clamp(score)

    @staticmethod
    def _depth_direction(total: float, line: float, expected: float, context: float) -> str:
        if total >= 0.70 and min(line, expected) >= 0.58:
            return "支持赢深"
        if total >= 0.58:
            return "胜面清楚，赢深可看"
        if total >= 0.45:
            return "只支持取胜，赢深保守"
        return "强队胜面有，但深度风险高"

    @staticmethod
    def _scoreline_hint(direction: str, scoreline_signal: Any, goals_signal: Any) -> str:
        top_scores = getattr(scoreline_signal, "top_scores", []) if scoreline_signal else []
        conservative = [item.get("score") for item in top_scores[:2] if item.get("score")]
        risk = [item.get("score") for item in top_scores[2:5] if item.get("score")]
        goals_direction = getattr(goals_signal, "goals_direction", "") if goals_signal else ""
        if direction in {"支持赢深", "胜面清楚，赢深可看"} and risk:
            return f"保守比分 {'/'.join(conservative) or '-'}；赢深看 {'/'.join(risk[:2])}；总球 {goals_direction or '-'}"
        return f"保守比分 {'/'.join(conservative) or '-'}；风险比分 {'/'.join(risk[:2]) or '-'}；总球 {goals_direction or '-'}"

    @staticmethod
    def _confidence(total: float, line: float, expected: float, context: float, warnings: List[str]) -> str:
        spread = max(line, expected, context) - min(line, expected, context)
        if len(warnings) >= 3 or spread >= 0.34:
            return "low"
        if total >= 0.62 and spread <= 0.20:
            return "medium"
        return "low"

    @staticmethod
    def _quantify_team_depth(
        market_signal: Any,
        line_score: float,
        expected_goals_score: float,
        game_context_score: float,
        total_score: float,
        goals_signal: Any,
        xg_signal: Any,
    ) -> Dict[str, float]:
        favorite = getattr(market_signal, "favorite", "") if market_signal else ""
        home_xg = LEGModel._safe_float(getattr(xg_signal, "home_xg", None)) if xg_signal else None
        away_xg = LEGModel._safe_float(getattr(xg_signal, "away_xg", None)) if xg_signal else None
        home_xga = LEGModel._safe_float(getattr(xg_signal, "home_xga", None)) if xg_signal else None
        away_xga = LEGModel._safe_float(getattr(xg_signal, "away_xga", None)) if xg_signal else None
        xg_edge = LEGModel._safe_float(getattr(xg_signal, "xg_edge", None)) if xg_signal else None

        if favorite not in {"home", "away"}:
            if xg_edge is not None:
                favorite = "home" if xg_edge >= 0 else "away"
            else:
                favorite = "home"

        home_xg = home_xg if home_xg is not None else 1.25
        away_xg = away_xg if away_xg is not None else 1.05
        home_xga = home_xga if home_xga is not None else away_xg
        away_xga = away_xga if away_xga is not None else home_xg

        final_goal_mean = LEGModel._safe_float(getattr(goals_signal, "final_goal_mean", None)) if goals_signal else None
        xg_total = max(0.35, home_xg + away_xg)
        target_total = 0.65 * xg_total + 0.35 * final_goal_mean if final_goal_mean else xg_total
        home_share = LEGModel._clamp_range(home_xg / xg_total, 0.18, 0.82)
        away_share = 1 - home_share

        home_leg = target_total * home_share
        away_leg = target_total * away_share
        shift = 0.0
        shift += (line_score - 0.50) * 0.22
        shift += (expected_goals_score - 0.50) * 0.12
        shift += (game_context_score - 0.50) * 0.08
        shift = LEGModel._clamp_range(shift, -0.12, 0.18)
        if favorite == "home":
            moved = min(max(0.0, away_leg - 0.15), max(0.0, shift))
            home_leg += moved
            away_leg -= moved
        else:
            moved = min(max(0.0, home_leg - 0.15), max(0.0, shift))
            away_leg += moved
            home_leg -= moved

        home_line = LEGModel._side_score_from_favorite(line_score, favorite, "home")
        away_line = LEGModel._side_score_from_favorite(line_score, favorite, "away")
        home_context = LEGModel._side_score_from_favorite(game_context_score, favorite, "home")
        away_context = LEGModel._side_score_from_favorite(game_context_score, favorite, "away")
        home_xg_score = LEGModel._team_xg_score(home_leg, home_xga, away_xga)
        away_xg_score = LEGModel._team_xg_score(away_leg, away_xga, home_xga)

        home_depth = 0.35 * home_line + 0.35 * home_xg_score + 0.30 * home_context
        away_depth = 0.35 * away_line + 0.35 * away_xg_score + 0.30 * away_context

        return {
            "home_leg_expected_goals": round(home_leg, 2),
            "away_leg_expected_goals": round(away_leg, 2),
            "home_depth_score_10": round(LEGModel._clamp_range(home_depth, 0.0, 10.0), 1),
            "away_depth_score_10": round(LEGModel._clamp_range(away_depth, 0.0, 10.0), 1),
            "home_line_score_10": round(home_line, 1),
            "away_line_score_10": round(away_line, 1),
            "home_xg_score_10": round(home_xg_score, 1),
            "away_xg_score_10": round(away_xg_score, 1),
            "home_context_score_10": round(home_context, 1),
            "away_context_score_10": round(away_context, 1),
            "depth_gap_10": round(home_depth - away_depth, 1),
        }

    @staticmethod
    def _side_score_from_favorite(score: float, favorite: str, side: str) -> float:
        favorite_score = 10.0 * LEGModel._clamp(score)
        underdog_score = 10.0 * LEGModel._clamp(1.0 - score)
        # Do not make the non-favorite look artificially dead in balanced matches.
        underdog_score = 0.72 * underdog_score + 1.4
        return LEGModel._clamp_range(favorite_score if side == favorite else underdog_score, 0.0, 10.0)

    @staticmethod
    def _team_xg_score(team_leg_xg: float, team_xga: float, opponent_xga: float) -> float:
        attack = LEGModel._clamp_range(team_leg_xg / 2.25, 0.0, 1.0)
        opponent_vulnerability = LEGModel._clamp_range(opponent_xga / 2.25, 0.0, 1.0)
        own_risk_penalty = LEGModel._clamp_range((team_xga - 1.0) / 2.0, 0.0, 0.35)
        return LEGModel._clamp_range(10.0 * (0.62 * attack + 0.38 * opponent_vulnerability - own_risk_penalty), 0.0, 10.0)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp_range(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))


__all__ = ["LEGSignal", "LEGModel"]
