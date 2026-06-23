#!/usr/bin/env python3
"""Bayesian probability fusion utilities.

This module treats model probabilities as a Dirichlet prior and dewatered
market probabilities as likelihood evidence. It returns an auditable posterior
instead of a black-box weighted average.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass
class BayesianFusionReport:
    market_type: str
    prior_probabilities: Dict[str, float]
    evidence_probabilities: Dict[str, float]
    posterior_probabilities: Dict[str, float]
    prior_strength: float
    evidence_strength: float
    max_deviation: float
    reliability: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BayesianProbabilityFusion:
    """Fuse categorical model probabilities with dewatered market evidence."""

    DEFAULT_PRIOR_STRENGTH = 12.0
    DEFAULT_EVIDENCE_STRENGTH = 10.0

    @staticmethod
    def fuse_3way(
        prior: Mapping[str, Any],
        evidence: Mapping[str, Any],
        *,
        market_type: str = "result_3way",
        prior_strength: float = DEFAULT_PRIOR_STRENGTH,
        evidence_strength: float = DEFAULT_EVIDENCE_STRENGTH,
        keys: Iterable[str] = ("home", "draw", "away"),
    ) -> BayesianFusionReport:
        keys = tuple(keys)
        warnings: List[str] = []
        prior_probs = BayesianProbabilityFusion._normalize(prior, keys)
        evidence_probs = BayesianProbabilityFusion._normalize(evidence, keys)
        if prior_probs is None:
            raise ValueError("prior probabilities are missing or invalid")
        if evidence_probs is None:
            posterior = prior_probs
            evidence_probs = {key: 0.0 for key in keys}
            evidence_strength = 0.0
            warnings.append("market_evidence_missing_use_prior_only")
        max_deviation = max(abs(prior_probs[key] - evidence_probs[key]) for key in keys) if evidence_strength else 0.0
        adjusted_prior_strength = max(0.1, float(prior_strength))
        adjusted_evidence_strength = max(0.0, float(evidence_strength))
        if max_deviation >= 0.22:
            adjusted_evidence_strength *= 0.75
            warnings.append("large_model_market_deviation_market_evidence_discounted")
        elif max_deviation >= 0.14:
            adjusted_evidence_strength *= 0.88
            warnings.append("medium_model_market_deviation")

        if adjusted_evidence_strength:
            posterior_mass = {
                key: prior_probs[key] * adjusted_prior_strength + evidence_probs[key] * adjusted_evidence_strength
                for key in keys
            }
            posterior = BayesianProbabilityFusion._normalize(posterior_mass, keys) or prior_probs
        else:
            posterior = prior_probs

        return BayesianFusionReport(
            market_type=market_type,
            prior_probabilities=prior_probs,
            evidence_probabilities=evidence_probs,
            posterior_probabilities=posterior,
            prior_strength=round(adjusted_prior_strength, 4),
            evidence_strength=round(adjusted_evidence_strength, 4),
            max_deviation=round(max_deviation, 4),
            reliability=BayesianProbabilityFusion._reliability(max_deviation, adjusted_evidence_strength),
            warnings=warnings,
        )

    @staticmethod
    def _normalize(values: Mapping[str, Any], keys: Iterable[str]) -> Optional[Dict[str, float]]:
        parsed: Dict[str, float] = {}
        for key in keys:
            value = BayesianProbabilityFusion._safe_float(values.get(key))
            if value is None or value < 0:
                return None
            parsed[key] = value
        total = sum(parsed.values())
        if total <= 0:
            return None
        return {key: parsed[key] / total for key in parsed}

    @staticmethod
    def _reliability(max_deviation: float, evidence_strength: float) -> str:
        if evidence_strength <= 0:
            return "prior_only"
        if max_deviation >= 0.22:
            return "low"
        if max_deviation >= 0.14:
            return "medium"
        return "high"

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["BayesianFusionReport", "BayesianProbabilityFusion"]
