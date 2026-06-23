#!/usr/bin/env python3
"""比赛语境、让球打穿和总球辅助模型。"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MatchContext:
    competition_type: str
    friendly_subtype: str
    importance_score: float
    volatility_score: float
    motivation_score: float
    home_motivation_score: float
    away_vulnerability_score: float
    high_scoring_risk: float
    favorite_cover_trigger: bool
    motivation_note: str
    tags: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HandicapCoverSignal:
    line: Optional[float]
    cover_side: str
    cover_probability: Optional[float]
    fail_probability: Optional[float]
    push_probability: Optional[float]
    confidence: str
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GoalsSignal:
    expected_total_goals: float
    over_25_probability: float
    goals_direction: str
    confidence: str
    distribution: Dict[str, float]
    exact_distribution: Dict[str, float]
    independent_goal_mean: float
    market_goal_mean: Optional[float]
    final_goal_mean: float
    debias_applied: bool
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScorelineSignal:
    top_scores: List[Dict[str, Any]]
    market_weight: float
    total_goals_weight: float
    handicap_weight: float
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MatchContextModel:
    """Classify match context so friendlies are not treated like league matches."""

    @staticmethod
    def analyze(data_report: Any) -> MatchContext:
        jingcai = data_report.jingcai_match or {}
        league = jingcai.get("league") or ((data_report.match_data or {}).league.get("name") if data_report.match_data else "")
        match_dt = data_report.match_data.match_date if data_report.match_data else None
        tags: List[str] = []
        warnings: List[str] = []
        importance = 0.5
        volatility = 0.35
        competition_type = "unknown"
        motivation_note = "常规比赛语境"
        friendly_subtype = "none"
        motivation_score = 0.0
        home_motivation_score = 0.0
        away_vulnerability_score = 0.0
        high_scoring_risk = 0.0
        favorite_cover_trigger = False
        dynamics = MatchContextModel._match_dynamics(data_report)
        home_info = ((data_report.match_intelligence or {}).get("home") or {})
        away_info = ((data_report.match_intelligence or {}).get("away") or {})

        if "国际赛" in league or "友谊" in league or "Friendly" in league:
            competition_type = "international_friendly"
            friendly_subtype = "ordinary_friendly"
            importance = 0.45
            volatility = 0.70
            tags.append("国际赛/友谊赛")
            warnings.append("国际赛阵容和换人波动高，不能只按近10场均值判断")
            motivation_note = "国际赛波动高，需重点确认主力出场和轮换动机"

        if "世界杯" in league or "World Cup" in league:
            competition_type = "world_cup"
            friendly_subtype = "none"
            importance = max(importance, 0.82)
            volatility = max(volatility, 0.50)
            tags.append("世界杯")
            motivation_note = "世界杯小组赛语境，必须结合出线形势、东道主情绪、场馆天气和开局策略"

            if dynamics:
                high_scoring_risk += MatchContextModel._safe_float(dynamics.get("high_scoring_risk")) or 0.0
                favorite_cover_trigger = bool(dynamics.get("favorite_cover_trigger"))
                if dynamics.get("host_high_press"):
                    tags.append("host_high_press")
                    high_scoring_risk += 0.10
                    motivation_score += 0.10
                    warnings.append("东道主高压和快速转换触发早段进球放大检查")
                if dynamics.get("host_inexperienced_finishing_risk"):
                    tags.append("host_inexperienced_finishing_risk")
                    warnings.append("东道主热度与终结稳定性存在冲突，平局保护需上调")
                if dynamics.get("set_piece_underdog_threat"):
                    tags.append("set_piece_underdog_threat")
                    warnings.append("弱势方定位球威胁触发一球边界和失球风险检查")

        if match_dt and isinstance(match_dt, datetime):
            # 世界杯前 30 天左右的热身赛：强队可能主动找状态，不能机械买让负。
            if match_dt.year == 2026 and match_dt.month in {5, 6} and competition_type == "international_friendly":
                tags.append("大赛前热身赛")
                importance += 0.15
                volatility += 0.10
                motivation_note = "大赛前热身赛可能出现主力磨合和进攻演练，强队打穿深让球概率不可机械压低"
                warnings.append("大赛前热身赛需加入主力磨合和刷进攻状态因子")

        if competition_type == "international_friendly":
            next_days = home_info.get("next_match_days")
            if MatchContextModel._safe_float(next_days) is not None and float(next_days) <= 10:
                friendly_subtype = "world_cup_final_warmup"
                tags.append("世界杯前最后热身/强动机")
                importance += 0.18
                motivation_score += 0.22
                home_motivation_score += 0.22
                motivation_note = "世界杯前最后热身或临近大赛演练，不能默认小比分和热门方不打穿"

            if dynamics:
                friendly_subtype = dynamics.get("friendly_subtype") or friendly_subtype
                home_motivation_score += MatchContextModel._safe_float(dynamics.get("home_motivation_score")) or 0.0
                away_vulnerability_score += MatchContextModel._safe_float(dynamics.get("away_vulnerability_score")) or 0.0
                high_scoring_risk += MatchContextModel._safe_float(dynamics.get("high_scoring_risk")) or 0.0
                favorite_cover_trigger = bool(dynamics.get("favorite_cover_trigger"))
                if dynamics.get("travel_fatigue_side") in {"away", "both"}:
                    away_vulnerability_score += 0.10
                    tags.append("客队旅行疲劳")
                if dynamics.get("young_squad_side") in {"away", "both"}:
                    away_vulnerability_score += 0.10
                    tags.append("客队年轻化/练兵")
                if dynamics.get("note"):
                    motivation_note = str(dynamics.get("note"))[:180]

            away_absences = away_info.get("injuries") or []
            if away_absences:
                away_vulnerability_score += min(0.18, 0.04 * len(away_absences))
                tags.append("客队减员")

            if friendly_subtype == "world_cup_final_warmup":
                motivation_score += home_motivation_score + 0.5 * away_vulnerability_score
                high_scoring_risk += 0.10 if away_vulnerability_score >= 0.18 else 0.0

            if home_motivation_score >= 0.25 and away_vulnerability_score >= 0.20:
                favorite_cover_trigger = True
                high_scoring_risk += 0.08
                warnings.append("强队战意与对手脆弱性同时出现，打穿让球和高总球概率需上调")

        if data_report.weather_context:
            tags.append("天气已确认")
        else:
            warnings.append("天气或真实比赛地未确认")

        if not data_report.match_intelligence or (data_report.match_intelligence or {}).get("intelligence_score", 0) < 40:
            warnings.append("伤停、首发、轮换情报不足，降低让球和组合信心")

        return MatchContext(
            competition_type=competition_type,
            friendly_subtype=friendly_subtype,
            importance_score=min(1.0, importance),
            volatility_score=min(1.0, volatility),
            motivation_score=min(1.0, motivation_score),
            home_motivation_score=min(1.0, home_motivation_score),
            away_vulnerability_score=min(1.0, away_vulnerability_score),
            high_scoring_risk=min(1.0, high_scoring_risk),
            favorite_cover_trigger=favorite_cover_trigger,
            motivation_note=motivation_note,
            tags=tags,
            warnings=warnings,
        )

    @staticmethod
    def _match_dynamics(data_report: Any) -> Dict[str, Any]:
        intelligence = data_report.match_intelligence or {}
        dynamics = intelligence.get("match_dynamics")
        if isinstance(dynamics, dict):
            return dynamics
        verified = intelligence.get("gpt_verified") or {}
        dynamics = verified.get("match_dynamics")
        return dynamics if isinstance(dynamics, dict) else {}

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


class HandicapCoverModel:
    """Estimate cover/fail probability for Jingcai handicap."""

    @staticmethod
    def analyze(poisson: Any, data_report: Any, market_signal: Any, context: MatchContext) -> HandicapCoverSignal:
        handicap = (data_report.jingcai_match or {}).get("handicap")
        if handicap is None:
            return HandicapCoverSignal(None, "none", None, None, None, "low", [], ["未提供竞彩让球"])

        line = float(handicap)
        cover_probability = 0.0
        push_probability = 0.0
        fail_probability = 0.0
        notes: List[str] = []
        warnings: List[str] = []

        for (home_goals, away_goals), prob in poisson.score_probs.items():
            adjusted_margin = home_goals + line - away_goals
            if adjusted_margin > 0:
                cover_probability += prob
            elif adjusted_margin == 0:
                push_probability += prob
            else:
                fail_probability += prob

        if line < 0:
            cover_side = "主队打穿让球"
        elif line > 0:
            cover_side = "客队受让打穿"
        else:
            cover_side = "无让球"

        if abs(line) >= 2:
            warnings.append("深让球波动高，禁止只因名气强弱做组合核心")
            if context.competition_type == "international_friendly":
                warnings.append("国际赛深让球必须确认首发和市场强度")
            if market_signal.market_strength in {"strong_home_deep_handicap", "strong_away_deep_handicap"}:
                notes.append("市场数字强度支持热门方打穿让球，不能机械选择受让方向")

        if context.favorite_cover_trigger and abs(line) >= 1:
            shift = min(0.12, 0.06 + 0.08 * context.away_vulnerability_score)
            if line < 0 and getattr(market_signal, "favorite", None) == "home":
                moved = min(shift, fail_probability * 0.65 + push_probability * 0.35)
                fail_take = min(fail_probability, moved * 0.70)
                push_take = min(push_probability, moved - fail_take)
                cover_probability += fail_take + push_take
                fail_probability -= fail_take
                push_probability -= push_take
                notes.append("战意/减员/旅行疲劳触发主队打穿让球上调")
            elif line > 0 and getattr(market_signal, "favorite", None) == "away":
                moved = min(shift, fail_probability * 0.65 + push_probability * 0.35)
                fail_take = min(fail_probability, moved * 0.70)
                push_take = min(push_probability, moved - fail_take)
                cover_probability += fail_take + push_take
                fail_probability -= fail_take
                push_probability -= push_take
                notes.append("战意/减员/旅行疲劳触发客队打穿让球上调")

        push_signal = HandicapCoverModel._score_market_push_signal(data_report, line)
        if push_signal and 1.75 <= abs(line) <= 2.25:
            strength = push_signal.get("strength", 0.0)
            shift = min(0.10, 0.055 + 0.045 * strength)
            dominant = "cover" if cover_probability >= fail_probability else "fail"
            dominant_take = min(cover_probability if dominant == "cover" else fail_probability, shift * 0.72)
            secondary_take = min(fail_probability if dominant == "cover" else cover_probability, shift - dominant_take)
            if dominant == "cover":
                cover_probability -= dominant_take
                fail_probability -= secondary_take
            else:
                fail_probability -= dominant_take
                cover_probability -= secondary_take
            push_probability += dominant_take + secondary_take
            notes.append(
                f"比分表支持两球卡线保护，已上调让球平权重: {', '.join(push_signal.get('scores') or [])}"
            )

        confidence = "low"
        edge = abs(cover_probability - fail_probability)
        if edge >= 0.18 and context.volatility_score < 0.65:
            confidence = "high"
        elif edge >= 0.10:
            confidence = "medium"

        return HandicapCoverSignal(
            line=line,
            cover_side=cover_side,
            cover_probability=cover_probability,
            fail_probability=fail_probability,
            push_probability=push_probability,
            confidence=confidence,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _score_market_push_signal(data_report: Any, line: float) -> Dict[str, Any]:
        jingcai = data_report.jingcai_match or {}
        mixed = jingcai.get("mixed_market") or {}
        score_market = jingcai.get("score_market") or {}
        score_odds = (
            mixed.get("score_odds")
            or score_market.get("jingcai_score_odds")
            or score_market.get("average_score_odds")
            or {}
        )
        if not isinstance(score_odds, dict) or not score_odds:
            return {}

        implied = []
        target_margin = -line
        for key, value in score_odds.items():
            score = HandicapCoverModel._parse_score_key(key)
            price = MatchContextModel._safe_float(value)
            if not score or not price or price <= 1:
                continue
            home_goals, away_goals = score
            if abs((home_goals - away_goals) - target_margin) < 1e-9:
                implied.append((f"{home_goals}-{away_goals}", 1.0 / price))
        if not implied:
            return {}

        total_implied = 0.0
        for value in score_odds.values():
            price = MatchContextModel._safe_float(value)
            if price and price > 1:
                total_implied += 1.0 / price
        if total_implied <= 0:
            return {}
        implied.sort(key=lambda item: item[1], reverse=True)
        share = sum(value for _, value in implied[:3]) / total_implied
        if share < 0.14:
            return {}
        return {
            "strength": min(1.0, share / 0.24),
            "scores": [score for score, _ in implied[:3]],
        }

    @staticmethod
    def _parse_score_key(key: Any) -> Optional[tuple]:
        text = str(key).strip().replace(":", "-")
        parts = text.split("-")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None


class GoalsModel:
    """Independent goals direction wrapper around Poisson plus context adjustments."""

    @staticmethod
    def analyze(poisson: Any, data_report: Any, context: MatchContext, market_signal: Any) -> GoalsSignal:
        independent_total = poisson.expected_home_goals + poisson.expected_away_goals
        over_prob = poisson.over_25_prob
        notes: List[str] = []
        warnings: List[str] = []
        debias_applied = False

        distribution = GoalsModel._goal_distribution(poisson)
        exact_distribution = GoalsModel._goal_exact_distribution(poisson)
        market_distribution = GoalsModel._market_goal_distribution(data_report)
        market_exact_distribution = GoalsModel._market_goal_exact_distribution(data_report)
        market_total = GoalsModel._exact_goal_mean(market_exact_distribution) if market_exact_distribution else GoalsModel._market_goal_mean(market_distribution)
        final_total = independent_total

        if market_total is not None:
            delta = independent_total - market_total
            market_weight = 0.35
            if abs(delta) >= 0.55:
                market_weight = 0.20
                debias_applied = True
                notes.append(
                    f"500总球中枢与独立进球均值差异{abs(delta):.2f}，已降低500总球权重"
                )
            final_total = (1 - market_weight) * independent_total + market_weight * market_total
            distribution = GoalsModel._blend_distribution(distribution, market_distribution, market_weight)
            if market_exact_distribution:
                exact_distribution = GoalsModel._blend_distribution(exact_distribution, market_exact_distribution, market_weight)
        else:
            warnings.append("500总球表缺失，进球分布仅使用独立模型")

        if (
            context.competition_type == "international_friendly"
            and context.friendly_subtype != "world_cup_final_warmup"
            and context.importance_score >= 0.55
        ):
            over_prob = 0.72 * over_prob + 0.28 * 0.50
            notes.append("国际友谊赛进球方向向中性概率收缩，避免仅凭近况均值追大")

        if context.friendly_subtype == "world_cup_final_warmup":
            notes.append("世界杯前最后热身不默认降温，需识别强队演练与后段失控")

        if context.high_scoring_risk >= 0.12:
            lift_target = 0.62 if context.high_scoring_risk < 0.30 else 0.68
            if context.favorite_cover_trigger and context.high_scoring_risk >= 0.30:
                lift_target = 0.72
                over_prob = min(0.80, 0.70 * over_prob + 0.30 * lift_target)
            else:
                over_prob = min(0.78, 0.82 * over_prob + 0.18 * lift_target)
            distribution = GoalsModel._shift_distribution_to_high(distribution, context.high_scoring_risk)
            exact_distribution = GoalsModel._shift_exact_distribution_to_high(exact_distribution, context.high_scoring_risk)
            notes.append("年轻化/减员/旅行疲劳触发后段崩盘因子，大球概率上调")

        low_tempo_guard = GoalsModel._ordinary_friendly_low_tempo_guard(context, final_total, market_total)
        if low_tempo_guard > 0:
            distribution = GoalsModel._shift_distribution_to_low(distribution, low_tempo_guard)
            exact_distribution = GoalsModel._shift_exact_distribution_to_low(exact_distribution, low_tempo_guard)
            final_total = GoalsModel._exact_goal_mean(exact_distribution) or final_total
            over_prob = GoalsModel._over_25_from_exact_distribution(exact_distribution) or over_prob
            notes.append(
                f"普通国际赛情报不足触发低节奏保护，总球分布向0-2球收缩{low_tempo_guard:.2f}"
            )

        if market_signal.market_strength in {"strong_home_deep_handicap", "strong_away_deep_handicap"}:
            notes.append("深让球热门方若早早领先，比赛可能转向高总球或让球分歧")

        distribution = GoalsModel._exact_to_bucket_distribution(exact_distribution) or distribution
        calibrated_over_prob = GoalsModel._over_25_from_exact_distribution(exact_distribution)
        calibrated_total = GoalsModel._exact_goal_mean(exact_distribution)
        if calibrated_over_prob is not None:
            over_prob = calibrated_over_prob
            notes.append("大2.5概率已由最终精确总球分布反推")
        if calibrated_total is not None:
            final_total = calibrated_total

        if over_prob >= 0.58:
            direction = "大2.5"
            confidence = "medium" if over_prob < 0.66 else "high"
        elif over_prob <= 0.42:
            direction = "小2.5"
            confidence = "medium" if over_prob > 0.34 else "high"
        else:
            direction = GoalsModel._exact_distribution_direction(exact_distribution) or GoalsModel._distribution_direction(distribution)
            confidence = "low"

        if direction == "2-3球区间" and max(distribution.get("0_1", 0), distribution.get("4_plus", 0)) >= 0.24:
            direction = GoalsModel._exact_distribution_direction(exact_distribution, force_detail=True) or GoalsModel._distribution_direction(distribution, force_detail=True)
            notes.append("总球中位不再直接等同2-3球，已展示两端概率")

        if context.volatility_score >= 0.7 and context.high_scoring_risk < 0.25:
            confidence = "low"
            warnings.append("比赛语境波动高，进球数信心下调")

        return GoalsSignal(
            expected_total_goals=final_total,
            over_25_probability=over_prob,
            goals_direction=direction,
            confidence=confidence,
            distribution=distribution,
            exact_distribution=exact_distribution,
            independent_goal_mean=independent_total,
            market_goal_mean=market_total,
            final_goal_mean=final_total,
            debias_applied=debias_applied,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _goal_distribution(poisson: Any) -> Dict[str, float]:
        return GoalsModel._exact_to_bucket_distribution(GoalsModel._goal_exact_distribution(poisson))

    @staticmethod
    def _goal_exact_distribution(poisson: Any) -> Dict[str, float]:
        buckets = {str(goal): 0.0 for goal in range(7)}
        buckets["7_plus"] = 0.0
        for (home_goals, away_goals), prob in getattr(poisson, "score_probs", {}).items():
            total = home_goals + away_goals
            if total >= 7:
                buckets["7_plus"] += prob
            else:
                buckets[str(total)] += prob
        return GoalsModel._normalize_distribution(buckets)

    @staticmethod
    def _market_goal_distribution(data_report: Any) -> Dict[str, float]:
        return GoalsModel._exact_to_bucket_distribution(GoalsModel._market_goal_exact_distribution(data_report))

    @staticmethod
    def _market_goal_exact_distribution(data_report: Any) -> Dict[str, float]:
        odds = GoalsModel._total_goals_odds(data_report)
        if not odds:
            return {}
        buckets = {str(goal): 0.0 for goal in range(7)}
        buckets["7_plus"] = 0.0
        for key, value in odds.items():
            goal = GoalsModel._goal_key_to_int(key)
            price = MatchContextModel._safe_float(value)
            if goal is None or not price or price <= 1:
                continue
            implied = 1.0 / price
            if goal >= 7:
                buckets["7_plus"] += implied
            else:
                buckets[str(goal)] += implied
        return GoalsModel._normalize_distribution(buckets)

    @staticmethod
    def _exact_to_bucket_distribution(exact_distribution: Dict[str, float]) -> Dict[str, float]:
        if not exact_distribution:
            return {}
        return GoalsModel._normalize_distribution({
            "0_1": exact_distribution.get("0", 0.0) + exact_distribution.get("1", 0.0),
            "2": exact_distribution.get("2", 0.0),
            "3": exact_distribution.get("3", 0.0),
            "4_plus": (
                exact_distribution.get("4", 0.0)
                + exact_distribution.get("5", 0.0)
                + exact_distribution.get("6", 0.0)
                + exact_distribution.get("7_plus", 0.0)
            ),
        })

    @staticmethod
    def _total_goals_odds(data_report: Any) -> Dict[str, Any]:
        jingcai = data_report.jingcai_match or {}
        mixed = jingcai.get("mixed_market") or {}
        for candidate in [
            mixed.get("total_goals_odds"),
            jingcai.get("total_goals_odds"),
            jingcai.get("total_goals_table"),
        ]:
            if isinstance(candidate, dict) and candidate:
                return candidate
        trade = jingcai.get("trade_table") or {}
        candidate = trade.get("total_goals_table")
        return candidate if isinstance(candidate, dict) else {}

    @staticmethod
    def _goal_key_to_int(key: Any) -> Optional[int]:
        text = str(key).strip().replace("球", "")
        if text in {"7+", "7＋", "7以上"}:
            return 7
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _market_goal_mean(distribution: Dict[str, float]) -> Optional[float]:
        if not distribution:
            return None
        return (
            0.7 * distribution.get("0_1", 0.0)
            + 2.0 * distribution.get("2", 0.0)
            + 3.0 * distribution.get("3", 0.0)
            + 4.5 * distribution.get("4_plus", 0.0)
        )

    @staticmethod
    def _exact_goal_mean(distribution: Dict[str, float]) -> Optional[float]:
        if not distribution:
            return None
        return sum(
            (7.5 if key == "7_plus" else float(key)) * value
            for key, value in distribution.items()
        )

    @staticmethod
    def _over_25_from_exact_distribution(distribution: Dict[str, float]) -> Optional[float]:
        if not distribution:
            return None
        return sum(
            value
            for key, value in distribution.items()
            if key == "7_plus" or MatchContextModel._safe_float(key) is not None and float(key) >= 3
        )

    @staticmethod
    def _blend_distribution(independent: Dict[str, float], market: Dict[str, float], market_weight: float) -> Dict[str, float]:
        if not market:
            return GoalsModel._normalize_distribution(independent)
        keys = set(independent) | set(market)
        blended = {
            key: (1 - market_weight) * independent.get(key, 0.0) + market_weight * market.get(key, 0.0)
            for key in keys
        }
        return GoalsModel._normalize_distribution(blended)

    @staticmethod
    def _shift_distribution_to_high(distribution: Dict[str, float], risk: float) -> Dict[str, float]:
        lift = min(0.10, 0.04 + 0.12 * risk)
        low_take = min(distribution.get("0_1", 0.0), lift * 0.45)
        mid_take = min(distribution.get("2", 0.0), lift * 0.35)
        shifted = dict(distribution)
        shifted["0_1"] -= low_take
        shifted["2"] -= mid_take
        shifted["3"] += lift * 0.25
        shifted["4_plus"] += low_take + mid_take + lift * 0.75
        return GoalsModel._normalize_distribution(shifted)

    @staticmethod
    def _shift_exact_distribution_to_high(distribution: Dict[str, float], risk: float) -> Dict[str, float]:
        if not distribution:
            return {}
        lift = min(0.08, 0.03 + 0.10 * risk)
        shifted = dict(distribution)
        low_take = min(shifted.get("0", 0.0) + shifted.get("1", 0.0), lift * 0.45)
        two_take = min(shifted.get("2", 0.0), lift * 0.30)
        take_0 = min(shifted.get("0", 0.0), low_take * 0.35)
        take_1 = min(shifted.get("1", 0.0), low_take - take_0)
        shifted["0"] = shifted.get("0", 0.0) - take_0
        shifted["1"] = shifted.get("1", 0.0) - take_1
        shifted["2"] = shifted.get("2", 0.0) - two_take
        shifted["3"] = shifted.get("3", 0.0) + lift * 0.35
        shifted["4"] = shifted.get("4", 0.0) + low_take + two_take + lift * 0.45
        shifted["5"] = shifted.get("5", 0.0) + lift * 0.15
        shifted["6"] = shifted.get("6", 0.0) + lift * 0.05
        return GoalsModel._normalize_distribution(shifted)

    @staticmethod
    def _ordinary_friendly_low_tempo_guard(context: MatchContext, final_total: float, market_total: Optional[float]) -> float:
        if context.competition_type != "international_friendly":
            return 0.0
        if context.friendly_subtype == "world_cup_final_warmup":
            return 0.0
        if context.favorite_cover_trigger or context.high_scoring_risk >= 0.18:
            return 0.0
        weak_info = any("伤停、首发、轮换情报不足" in warning for warning in context.warnings)
        high_rotation = context.volatility_score >= 0.65
        modest_total = final_total <= 2.65 or (market_total is not None and market_total <= 2.70)
        if not (weak_info or high_rotation):
            return 0.0
        if not modest_total:
            return 0.0
        guard = 0.035
        if weak_info:
            guard += 0.020
        if high_rotation:
            guard += 0.015
        if context.high_scoring_risk <= 0.08:
            guard += 0.010
        return min(0.085, guard)

    @staticmethod
    def _shift_distribution_to_low(distribution: Dict[str, float], guard: float) -> Dict[str, float]:
        if not distribution:
            return {}
        shifted = dict(distribution)
        high_available = shifted.get("3", 0.0) + shifted.get("4_plus", 0.0)
        if high_available <= 0:
            return GoalsModel._normalize_distribution(shifted)
        move = min(guard, high_available * 0.30)
        take_3 = min(shifted.get("3", 0.0), move * 0.45)
        take_4 = min(shifted.get("4_plus", 0.0), move - take_3)
        shifted["3"] = shifted.get("3", 0.0) - take_3
        shifted["4_plus"] = shifted.get("4_plus", 0.0) - take_4
        shifted["0_1"] = shifted.get("0_1", 0.0) + move * 0.45
        shifted["2"] = shifted.get("2", 0.0) + move * 0.55
        return GoalsModel._normalize_distribution(shifted)

    @staticmethod
    def _shift_exact_distribution_to_low(distribution: Dict[str, float], guard: float) -> Dict[str, float]:
        if not distribution:
            return {}
        shifted = dict(distribution)
        high_keys = ["3", "4", "5", "6", "7_plus"]
        high_available = sum(shifted.get(key, 0.0) for key in high_keys)
        if high_available <= 0:
            return GoalsModel._normalize_distribution(shifted)
        move = min(guard, high_available * 0.28)
        for key in high_keys:
            share = shifted.get(key, 0.0) / high_available
            shifted[key] = shifted.get(key, 0.0) - move * share
        shifted["0"] = shifted.get("0", 0.0) + move * 0.18
        shifted["1"] = shifted.get("1", 0.0) + move * 0.34
        shifted["2"] = shifted.get("2", 0.0) + move * 0.48
        return GoalsModel._normalize_distribution(shifted)

    @staticmethod
    def _distribution_direction(distribution: Dict[str, float], force_detail: bool = False) -> str:
        top_key, top_prob = max(distribution.items(), key=lambda item: item[1])
        labels = {
            "0_1": "0-1球",
            "2": "2球",
            "3": "3球",
            "4_plus": "4+球",
        }
        if not force_detail:
            two_three = distribution.get("2", 0.0) + distribution.get("3", 0.0)
            edge = abs(distribution.get("2", 0.0) - distribution.get("3", 0.0))
            if two_three >= 0.50 and edge <= 0.08 and distribution.get("4_plus", 0.0) < 0.24:
                return "2-3球区间"
        return labels.get(top_key, "总球分布待定")

    @staticmethod
    def _exact_distribution_direction(distribution: Dict[str, float], force_detail: bool = False) -> str:
        if not distribution:
            return ""
        ordered = sorted(distribution.items(), key=lambda item: item[1], reverse=True)
        top_key, top_prob = ordered[0]
        second_key, second_prob = ordered[1] if len(ordered) > 1 else ("", 0.0)
        label = lambda key: "7+球" if key == "7_plus" else f"{key}球"

        two_three = distribution.get("2", 0.0) + distribution.get("3", 0.0)
        four_five = distribution.get("4", 0.0) + distribution.get("5", 0.0)
        six_plus = distribution.get("6", 0.0) + distribution.get("7_plus", 0.0)

        if not force_detail and two_three >= 0.38 and two_three >= four_five + 0.04:
            return "2-3球区间"
        if not force_detail and four_five >= 0.34 and four_five >= two_three + 0.04:
            return "4-5球区间"
        if six_plus >= 0.20 and top_key in {"5", "6", "7_plus"}:
            return "上沿偏高，重点防5+球"
        if top_prob - second_prob <= 0.035 and second_key:
            return f"{label(top_key)} / {label(second_key)}并列"
        return f"{label(top_key)}优先"

    @staticmethod
    def _normalize_distribution(distribution: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(0.0, value) for value in distribution.values())
        if total <= 0:
            return {"0_1": 0.0, "2": 0.0, "3": 0.0, "4_plus": 0.0}
        return {key: max(0.0, value) / total for key, value in distribution.items()}


class ScorelineModel:
    """Blend Poisson scores with 500 score table and score-shape constraints."""

    @staticmethod
    def analyze(
        poisson: Any,
        data_report: Any,
        goals_signal: GoalsSignal,
        handicap_signal: HandicapCoverSignal,
        market_signal: Any,
        context: MatchContext,
        top_n: int = 8,
    ) -> ScorelineSignal:
        notes: List[str] = []
        warnings: List[str] = []
        market_scores = ScorelineModel._market_score_probabilities(data_report)
        market_weight = 0.34 if market_scores else 0.0
        total_weight = 0.18 if goals_signal and goals_signal.exact_distribution else 0.0
        handicap_weight = 0.14 if handicap_signal and handicap_signal.line is not None else 0.0

        if market_scores:
            notes.append("500比分表已进入比分融合排序")
        else:
            warnings.append("500比分表缺失，比分仅使用泊松和约束层")
        if total_weight:
            notes.append("精确总球分布用于约束比分总进球")
        if handicap_weight:
            notes.append("让球结算层用于约束比分差")
        notes.append("比分Top1/Top2采用保守命中率排序，Top3-Top5允许上沿风险比分进入")

        poisson_scores = {
            score: prob
            for score, prob in getattr(poisson, "score_probs", {}).items()
            if score[0] <= 8 and score[1] <= 8
        }
        poisson_total_probs = ScorelineModel._poisson_total_probs(poisson_scores)
        outcome_targets = ScorelineModel._outcome_targets(poisson, market_signal)
        handicap_targets = ScorelineModel._handicap_targets(poisson_scores, handicap_signal)

        raw_scores: Dict[tuple, Dict[str, Any]] = {}
        for score, poisson_prob in poisson_scores.items():
            market_prob = market_scores.get(score)
            blended = poisson_prob
            if market_prob is not None:
                blended = (1 - market_weight) * poisson_prob + market_weight * market_prob
            elif market_weight:
                blended = (1 - market_weight * 0.45) * poisson_prob

            total_factor = ScorelineModel._total_factor(
                score,
                goals_signal.exact_distribution if goals_signal else {},
                poisson_total_probs,
                total_weight,
            )
            outcome_factor = ScorelineModel._outcome_factor(score, outcome_targets)
            handicap_factor = ScorelineModel._handicap_factor(score, handicap_signal, handicap_targets, handicap_weight)

            raw_probability = max(0.0, blended * total_factor * outcome_factor * handicap_factor)
            raw_scores[score] = {
                "score": f"{score[0]}-{score[1]}",
                "home_goals": score[0],
                "away_goals": score[1],
                "total_goals": score[0] + score[1],
                "margin": score[0] - score[1],
                "outcome": ScorelineModel._outcome_label(score),
                "poisson_probability": poisson_prob,
                "market_probability": market_prob,
                "raw_probability": raw_probability,
                "total_factor": total_factor,
                "outcome_factor": outcome_factor,
                "handicap_factor": handicap_factor,
            }

        total = sum(item["raw_probability"] for item in raw_scores.values()) or 1.0
        ranked = ScorelineModel._tiered_rank_scores(
            list(raw_scores.values()),
            context=context,
            conservative_count=min(2, top_n),
            top_n=top_n,
        )
        top_scores = []
        for index, item in enumerate(ranked[:top_n], 1):
            item = dict(item)
            item["rank"] = index
            item["final_probability"] = item.pop("raw_probability") / total
            top_scores.append(item)

        if context.volatility_score >= 0.70:
            warnings.append("比赛语境波动高，比分层只保留区间和前二保护")

        return ScorelineSignal(
            top_scores=top_scores,
            market_weight=market_weight,
            total_goals_weight=total_weight,
            handicap_weight=handicap_weight,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _tiered_rank_scores(
        scores: List[Dict[str, Any]],
        context: MatchContext,
        conservative_count: int,
        top_n: int,
    ) -> List[Dict[str, Any]]:
        conservative_ranked = sorted(
            scores,
            key=lambda item: ScorelineModel._conservative_score(item, context),
            reverse=True,
        )
        selected: List[Dict[str, Any]] = []
        seen = set()
        for item in conservative_ranked:
            if len(selected) >= conservative_count:
                break
            selected.append({**item, "risk_tier": "保守位", "selection_score": ScorelineModel._conservative_score(item, context)})
            seen.add(item["score"])

        remaining = [item for item in scores if item["score"] not in seen]
        upside_ranked = sorted(
            remaining,
            key=lambda item: ScorelineModel._upside_score(item, context),
            reverse=True,
        )
        for item in upside_ranked:
            if len(selected) >= top_n:
                break
            selected.append({**item, "risk_tier": "风险位", "selection_score": ScorelineModel._upside_score(item, context)})
            seen.add(item["score"])
        return selected

    @staticmethod
    def _conservative_score(item: Dict[str, Any], context: MatchContext) -> float:
        score = item.get("raw_probability", 0.0)
        total_goals = item.get("total_goals", 0)
        margin = abs(item.get("margin", 0))
        market_probability = item.get("market_probability")

        if market_probability is not None:
            score *= 1.12
        if total_goals in {2, 3}:
            score *= 1.14
        elif total_goals == 4:
            score *= 0.98
        elif total_goals <= 1:
            score *= 0.94
        elif total_goals == 5:
            score *= 0.78
        else:
            score *= 0.62

        if margin <= 2:
            score *= 1.08
        elif margin == 3:
            score *= 0.92
        else:
            score *= 0.72

        if context.volatility_score >= 0.70 and total_goals >= 5:
            score *= 0.78
        return score

    @staticmethod
    def _upside_score(item: Dict[str, Any], context: MatchContext) -> float:
        score = item.get("raw_probability", 0.0)
        total_goals = item.get("total_goals", 0)
        margin = abs(item.get("margin", 0))
        market_probability = item.get("market_probability")

        if market_probability is not None:
            score *= 1.08
        if total_goals == 4:
            score *= 1.16
            if margin == 2 and item.get("home_goals", 0) > 0 and item.get("away_goals", 0) > 0:
                score *= 1.12
        elif total_goals == 5:
            score *= 1.08
        elif total_goals >= 6:
            score *= 0.72
        elif total_goals <= 1:
            score *= 0.82

        if margin == 3:
            score *= 1.10
        elif margin >= 4:
            score *= 0.82

        if context.high_scoring_risk >= 0.25 and total_goals in {4, 5}:
            score *= 1.08
        if context.competition_type == "international_friendly" and total_goals == 4 and margin == 2:
            score *= 1.06
        if (
            context.competition_type == "international_friendly"
            and total_goals in {4, 5}
            and margin in {2, 3}
            and (context.away_vulnerability_score >= 0.16 or context.favorite_cover_trigger)
        ):
            score *= 1.10
        if (
            context.competition_type == "world_cup"
            and "host_high_press" in context.tags
            and total_goals in {4, 5}
            and margin in {2, 3}
        ):
            score *= 1.12
        if (
            context.competition_type == "world_cup"
            and "set_piece_underdog_threat" in context.tags
            and item.get("home_goals", 0) > 0
            and item.get("away_goals", 0) > 0
            and total_goals in {2, 3, 4}
        ):
            score *= 1.08
        return score

    @staticmethod
    def _market_score_probabilities(data_report: Any) -> Dict[tuple, float]:
        jingcai = data_report.jingcai_match or {}
        mixed = jingcai.get("mixed_market") or {}
        score_market = jingcai.get("score_market") or {}
        candidates = [
            mixed.get("score_odds"),
            score_market.get("jingcai_score_odds"),
            score_market.get("average_score_odds"),
        ]
        odds = next((item for item in candidates if isinstance(item, dict) and item), {})
        implied: Dict[tuple, float] = {}
        for key, value in odds.items():
            score = ScorelineModel._parse_score_key(key)
            price = MatchContextModel._safe_float(value)
            if score is None or not price or price <= 1:
                continue
            implied[score] = implied.get(score, 0.0) + 1.0 / price
        return GoalsModel._normalize_distribution(implied)

    @staticmethod
    def _parse_score_key(key: Any) -> Optional[tuple]:
        text = str(key).strip().replace(":", "-")
        parts = text.split("-")
        if len(parts) != 2:
            return None
        try:
            home = int(parts[0])
            away = int(parts[1])
        except ValueError:
            return None
        if home < 0 or away < 0:
            return None
        return home, away

    @staticmethod
    def _poisson_total_probs(score_probs: Dict[tuple, float]) -> Dict[str, float]:
        exact = {str(goal): 0.0 for goal in range(7)}
        exact["7_plus"] = 0.0
        for (home, away), prob in score_probs.items():
            total = home + away
            key = "7_plus" if total >= 7 else str(total)
            exact[key] += prob
        return GoalsModel._normalize_distribution(exact)

    @staticmethod
    def _total_factor(score: tuple, exact_distribution: Dict[str, float], poisson_total_probs: Dict[str, float], weight: float) -> float:
        if not exact_distribution or not weight:
            return 1.0
        total = score[0] + score[1]
        key = "7_plus" if total >= 7 else str(total)
        target = exact_distribution.get(key, 0.0)
        current = poisson_total_probs.get(key, 0.0)
        if current <= 0 or target <= 0:
            return 1.0
        ratio = max(0.70, min(1.35, target / current))
        return (1 - weight) + weight * ratio

    @staticmethod
    def _outcome_targets(poisson: Any, market_signal: Any) -> Dict[str, float]:
        targets = {
            "home": getattr(poisson, "home_win_prob", 0.0),
            "draw": getattr(poisson, "draw_prob", 0.0),
            "away": getattr(poisson, "away_win_prob", 0.0),
        }
        market_values = {
            "home": getattr(market_signal, "implied_home", None),
            "draw": getattr(market_signal, "implied_draw", None),
            "away": getattr(market_signal, "implied_away", None),
        }
        if all(value is not None for value in market_values.values()):
            targets = {
                key: 0.62 * targets[key] + 0.38 * float(market_values[key])
                for key in targets
            }
        total = sum(targets.values()) or 1.0
        return {key: value / total for key, value in targets.items()}

    @staticmethod
    def _outcome_factor(score: tuple, targets: Dict[str, float]) -> float:
        key = "home" if score[0] > score[1] else ("draw" if score[0] == score[1] else "away")
        target = targets.get(key, 0.0)
        baseline = {"home": 0.45, "draw": 0.26, "away": 0.29}.get(key, 0.33)
        ratio = target / baseline if baseline else 1.0
        return max(0.80, min(1.22, 0.78 + 0.22 * ratio))

    @staticmethod
    def _handicap_targets(score_probs: Dict[tuple, float], handicap_signal: HandicapCoverSignal) -> Dict[str, float]:
        if not handicap_signal or handicap_signal.line is None:
            return {}
        current = {"cover": 0.0, "push": 0.0, "fail": 0.0}
        line = float(handicap_signal.line)
        for (home, away), prob in score_probs.items():
            adjusted = home + line - away
            if adjusted > 0:
                current["cover"] += prob
            elif adjusted == 0:
                current["push"] += prob
            else:
                current["fail"] += prob
        targets = {
            "cover": handicap_signal.cover_probability,
            "push": handicap_signal.push_probability,
            "fail": handicap_signal.fail_probability,
        }
        return {
            key: (float(targets[key]) / current[key] if targets.get(key) is not None and current[key] > 0 else 1.0)
            for key in current
        }

    @staticmethod
    def _handicap_factor(score: tuple, handicap_signal: HandicapCoverSignal, targets: Dict[str, float], weight: float) -> float:
        if not targets or not weight or handicap_signal.line is None:
            return 1.0
        adjusted = score[0] + float(handicap_signal.line) - score[1]
        key = "cover" if adjusted > 0 else ("push" if adjusted == 0 else "fail")
        ratio = max(0.78, min(1.25, targets.get(key, 1.0)))
        return (1 - weight) + weight * ratio

    @staticmethod
    def _outcome_label(score: tuple) -> str:
        if score[0] > score[1]:
            return "主胜"
        if score[0] == score[1]:
            return "平局"
        return "客胜"


__all__ = [
    "MatchContext",
    "HandicapCoverSignal",
    "GoalsSignal",
    "ScorelineSignal",
    "MatchContextModel",
    "HandicapCoverModel",
    "GoalsModel",
    "ScorelineModel",
]
