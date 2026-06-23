#!/usr/bin/env python3
"""Blend current match model, market probabilities and offline history priors."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.bayesian_fusion import BayesianFusionReport, BayesianProbabilityFusion
from core.math_models import PoissonModel, PoissonProbabilities
from core.worldcup_trained_model import DEFAULT_MODEL_PATH, WorldCupTrainedModel


@dataclass
class ProbabilityFusionReport:
    applied: bool
    weights: Dict[str, float]
    source_model_path: Optional[str]
    components: Dict[str, Dict[str, float]]
    bayesian: Optional[Dict[str, Any]] = None
    adjustments: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProbabilityFusionCalibrator:
    """Calibrate match probabilities without letting historical priors dominate."""

    DEFAULT_WEIGHTS = {
        "current": 0.55,
        "market": 0.25,
        "historical": 0.20,
    }

    FRIENDLY_GOAL_SHRINK = 0.88
    FRIENDLY_STRONG_XG_CAP = 2.80
    FRIENDLY_STRONG_XG_CAP_WITH_MARKET = 3.05
    FINAL_WARMUP_STRONG_XG_CAP = 3.35

    def __init__(
        self,
        trained_model: Optional[WorldCupTrainedModel] = None,
        trained_model_path: Optional[str] = None,
    ):
        self.trained_model = trained_model or WorldCupTrainedModel(trained_model_path or DEFAULT_MODEL_PATH)

    def fuse(
        self,
        base_poisson: PoissonProbabilities,
        data_report: Any,
        market_signal: Any,
        context: Any,
        max_goals: int = 10,
    ) -> Tuple[PoissonProbabilities, ProbabilityFusionReport]:
        home = data_report.parsed_match.home_team_en or data_report.parsed_match.home_team_raw
        away = data_report.parsed_match.away_team_en or data_report.parsed_match.away_team_raw
        components: Dict[str, PoissonProbabilities] = {"current": base_poisson}
        adjustments: List[str] = []
        warnings: List[str] = []

        bayesian_report: Optional[BayesianFusionReport] = None
        market_poisson = base_poisson
        if self._has_market(market_signal):
            bayesian_report = self._bayesian_market_report(base_poisson, market_signal, context)
            posterior = bayesian_report.posterior_probabilities
            market_poisson = PoissonModel.calibrate_with_market(
                base_poisson,
                posterior.get("home"),
                posterior.get("draw"),
                posterior.get("away"),
                model_weight=0.0,
            )
            components["market"] = market_poisson
            adjustments.append(
                "市场数字已先去水，再用贝叶斯后验进入融合层"
            )
        else:
            warnings.append("市场胜平负隐含概率缺失，融合权重回流到当前模型")

        historical_poisson = self._historical_poisson(home, away, context, market_signal, max_goals)
        if historical_poisson:
            components["historical"] = historical_poisson
            adjustments.append("历史国家队模型作为20%校准层，不单独替代当前模型")
        else:
            warnings.append("历史国家队训练模型未覆盖双方，历史权重回流到当前模型")

        weights = self._effective_weights(components)
        score_probs: Dict[Tuple[int, int], float] = {}
        for name, poisson in components.items():
            weight = weights.get(name, 0.0)
            for score, prob in poisson.score_probs.items():
                score_probs[score] = score_probs.get(score, 0.0) + weight * prob

        expected_home = sum(home_goals * prob for (home_goals, _), prob in score_probs.items())
        expected_away = sum(away_goals * prob for (_, away_goals), prob in score_probs.items())
        fused = PoissonModel._from_score_probs(score_probs, expected_home, expected_away)

        if self._is_international_friendly(context):
            fused, friendly_notes = self._friendly_total_goals_guard(fused, context)
            adjustments.extend(friendly_notes)

        report = ProbabilityFusionReport(
            applied=True,
            weights=weights,
            source_model_path=str(self.trained_model.model_path) if self.trained_model else None,
            components={name: self._component_summary(poisson) for name, poisson in components.items()},
            bayesian=bayesian_report.to_dict() if bayesian_report else None,
            adjustments=adjustments,
            warnings=warnings,
        )
        return fused, report

    def _bayesian_market_report(
        self,
        base_poisson: PoissonProbabilities,
        market_signal: Any,
        context: Any,
    ) -> BayesianFusionReport:
        prior_strength, evidence_strength = self._bayesian_strengths(context, market_signal)
        return BayesianProbabilityFusion.fuse_3way(
            {
                "home": base_poisson.home_win_prob,
                "draw": base_poisson.draw_prob,
                "away": base_poisson.away_win_prob,
            },
            {
                "home": getattr(market_signal, "implied_home", None),
                "draw": getattr(market_signal, "implied_draw", None),
                "away": getattr(market_signal, "implied_away", None),
            },
            market_type="result_3way",
            prior_strength=prior_strength,
            evidence_strength=evidence_strength,
        )

    @staticmethod
    def _bayesian_strengths(context: Any, market_signal: Any) -> Tuple[float, float]:
        prior_strength = 12.0
        evidence_strength = 10.0
        if getattr(context, "competition_type", "") == "world_cup":
            evidence_strength += 2.0
            if getattr(context, "round_index", None) == 1 or getattr(context, "stage", "") == "group":
                prior_strength += 1.0
                evidence_strength += 1.0
        if getattr(market_signal, "disagreement", "") == "high":
            evidence_strength *= 0.75
        elif getattr(market_signal, "disagreement", "") == "medium":
            evidence_strength *= 0.88
        if getattr(context, "data_quality_score", 100) < 80:
            evidence_strength += 2.0
            prior_strength -= 1.0
        return max(6.0, prior_strength), max(4.0, evidence_strength)

    def _historical_poisson(
        self,
        home: str,
        away: str,
        context: Any,
        market_signal: Any,
        max_goals: int,
    ) -> Optional[PoissonProbabilities]:
        if not self.trained_model or not self.trained_model.available:
            return None
        neutral = self._is_international_friendly(context)
        lambdas = self.trained_model.lambdas(home, away, neutral=neutral)
        if not lambdas:
            return None
        home_lambda, away_lambda = self._cap_lambdas(lambdas[0], lambdas[1], context, market_signal)
        return PoissonModel.calculate_match_probabilities(
            home_lambda,
            away_lambda,
            max_goals=max_goals,
            low_score_rho=-0.08,
            zero_inflation=0.08 if self._is_international_friendly(context) else 0.02,
        )

    def _cap_lambdas(
        self,
        home_lambda: float,
        away_lambda: float,
        context: Any,
        market_signal: Any,
    ) -> Tuple[float, float]:
        if not self._is_international_friendly(context):
            return home_lambda, away_lambda

        cap = self.FRIENDLY_STRONG_XG_CAP
        shrink = self.FRIENDLY_GOAL_SHRINK
        if getattr(context, "friendly_subtype", "") == "world_cup_final_warmup" and getattr(context, "favorite_cover_trigger", False):
            cap = self.FINAL_WARMUP_STRONG_XG_CAP
            shrink = 0.96
        if getattr(market_signal, "market_strength", "") in {"strong_home_deep_handicap", "strong_away_deep_handicap"}:
            cap = max(cap, self.FRIENDLY_STRONG_XG_CAP_WITH_MARKET)
        total = home_lambda + away_lambda
        if total > 0:
            home_lambda *= shrink
            away_lambda *= shrink
        return min(home_lambda, cap), min(away_lambda, cap)

    def _friendly_total_goals_guard(self, poisson: PoissonProbabilities, context: Any) -> Tuple[PoissonProbabilities, List[str]]:
        notes: List[str] = []
        total = poisson.expected_home_goals + poisson.expected_away_goals
        threshold = 3.20
        if getattr(context, "friendly_subtype", "") == "world_cup_final_warmup" and getattr(context, "high_scoring_risk", 0) >= 0.20:
            threshold = 3.70
        if total <= threshold:
            return poisson, notes
        shrink = threshold / total
        notes.append(f"国际友谊赛总进球期望超过{threshold:.2f}，已做低比分保护")
        adjusted = {}
        for (home_goals, away_goals), prob in poisson.score_probs.items():
            total_goals = home_goals + away_goals
            factor = 1.0
            if total_goals >= 4:
                factor = 0.82
            elif total_goals <= 2:
                factor = 1.08
            adjusted[(home_goals, away_goals)] = prob * factor
        return PoissonModel._from_score_probs(
            adjusted,
            poisson.expected_home_goals * shrink,
            poisson.expected_away_goals * shrink,
        ), notes

    def _effective_weights(self, components: Dict[str, PoissonProbabilities]) -> Dict[str, float]:
        weights = {name: weight for name, weight in self.DEFAULT_WEIGHTS.items() if name in components}
        missing = 1.0 - sum(weights.values())
        weights["current"] = weights.get("current", 0.0) + max(0.0, missing)
        total = sum(weights.values()) or 1.0
        return {name: round(weight / total, 4) for name, weight in weights.items()}

    @staticmethod
    def _has_market(market_signal: Any) -> bool:
        return all(
            getattr(market_signal, attr, None) is not None
            for attr in ["implied_home", "implied_draw", "implied_away"]
        )

    @staticmethod
    def _is_international_friendly(context: Any) -> bool:
        return getattr(context, "competition_type", "") == "international_friendly"

    @staticmethod
    def _component_summary(poisson: PoissonProbabilities) -> Dict[str, float]:
        return {
            "home_win": round(poisson.home_win_prob, 4),
            "draw": round(poisson.draw_prob, 4),
            "away_win": round(poisson.away_win_prob, 4),
            "expected_home_goals": round(poisson.expected_home_goals, 4),
            "expected_away_goals": round(poisson.expected_away_goals, 4),
            "over_25": round(poisson.over_25_prob, 4),
        }


__all__ = ["ProbabilityFusionReport", "ProbabilityFusionCalibrator"]
