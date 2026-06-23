#!/usr/bin/env python3
"""Order-independent categorical probability fusion for multiple sources."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "data/calibration/multi_source_weight_policy.json"


@dataclass
class FusionSource:
    name: str
    probabilities: Mapping[str, Any]
    base_weight: float
    quality: float = 1.0
    correlation_discount: float = 1.0
    apply_deviation_discount: bool = False
    source_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiSourceFusionReport:
    market_type: str
    posterior_probabilities: Dict[str, float]
    sources: Dict[str, Dict[str, Any]]
    anchor_source: str
    max_deviation: float
    reliability: str
    warnings: List[str] = field(default_factory=list)
    method: str = "quality_adjusted_dirichlet_pool"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiSourceProbabilityFusion:
    """Fuse all active sources in one pass after quality and correlation controls."""

    @classmethod
    def fuse(
        cls,
        sources: Sequence[FusionSource],
        *,
        market_type: str = "result_3way_multi_source",
        anchor_source: str = "poisson",
        keys: Iterable[str] = ("home", "draw", "away"),
    ) -> MultiSourceFusionReport:
        keys = tuple(keys)
        parsed: Dict[str, Dict[str, float]] = {}
        warnings: List[str] = []
        source_inputs = {source.name: source for source in sources}
        if anchor_source not in source_inputs:
            raise ValueError(f"anchor source is missing: {anchor_source}")

        for source in sources:
            probabilities = cls._normalize(source.probabilities, keys)
            if probabilities is None:
                warnings.append(f"invalid_source_excluded:{source.name}")
                continue
            parsed[source.name] = probabilities
        if anchor_source not in parsed:
            raise ValueError(f"anchor probabilities are invalid: {anchor_source}")

        anchor = parsed[anchor_source]
        details: Dict[str, Dict[str, Any]] = {}
        raw_weights: Dict[str, float] = {}
        max_deviation = 0.0
        for source in sources:
            if source.name not in parsed:
                continue
            deviation = max(abs(parsed[source.name][key] - anchor[key]) for key in keys)
            max_deviation = max(max_deviation, deviation)
            deviation_discount = cls._deviation_discount(deviation) if source.apply_deviation_discount else 1.0
            quality = cls._clamp(float(source.quality), 0.0, 1.0)
            correlation = cls._clamp(float(source.correlation_discount), 0.0, 1.0)
            raw_weight = max(0.0, float(source.base_weight)) * quality * correlation * deviation_discount
            raw_weights[source.name] = raw_weight
            details[source.name] = {
                "source_type": source.source_type,
                "probabilities": parsed[source.name],
                "base_weight": round(float(source.base_weight), 6),
                "quality": round(quality, 6),
                "correlation_discount": round(correlation, 6),
                "deviation_from_anchor": round(deviation, 6),
                "deviation_discount": round(deviation_discount, 6),
                "raw_effective_weight": round(raw_weight, 6),
                "metadata": dict(source.metadata),
            }
            if deviation_discount < 1.0:
                warnings.append(f"source_deviation_discounted:{source.name}")

        weight_total = sum(raw_weights.values())
        if weight_total <= 0:
            raise ValueError("all source weights are zero")
        normalized_weights = {name: value / weight_total for name, value in raw_weights.items()}
        posterior = {
            key: sum(normalized_weights[name] * parsed[name][key] for name in normalized_weights)
            for key in keys
        }
        posterior = cls._normalize(posterior, keys) or anchor
        for name, value in normalized_weights.items():
            details[name]["normalized_weight"] = round(value, 6)

        active_count = len(normalized_weights)
        if active_count < 3:
            warnings.append("limited_independent_sources")
        reliability = "high"
        if max_deviation >= 0.22 or active_count < 3:
            reliability = "low"
        elif max_deviation >= 0.14:
            reliability = "medium"
        return MultiSourceFusionReport(
            market_type=market_type,
            posterior_probabilities=posterior,
            sources=details,
            anchor_source=anchor_source,
            max_deviation=round(max_deviation, 6),
            reliability=reliability,
            warnings=warnings,
        )

    @staticmethod
    def _deviation_discount(deviation: float) -> float:
        if deviation >= 0.22:
            return 0.75
        if deviation >= 0.14:
            return 0.88
        return 1.0

    @staticmethod
    def _normalize(values: Mapping[str, Any], keys: Iterable[str]) -> Optional[Dict[str, float]]:
        parsed: Dict[str, float] = {}
        for key in keys:
            try:
                value = float(values.get(key))
            except (TypeError, ValueError):
                return None
            if value < 0:
                return None
            parsed[key] = value
        total = sum(parsed.values())
        if total <= 0:
            return None
        return {key: parsed[key] / total for key in parsed}

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))


class MultiSourceWeightPolicy:
    """Load reusable result-fusion profiles and source controls."""

    def __init__(self, path: Path | str = DEFAULT_POLICY_PATH):
        self.path = Path(path)
        self.payload = json.loads(self.path.read_text(encoding="utf-8"))

    def result_profile(self, *, official_500: bool) -> Dict[str, float]:
        name = "official_500" if official_500 else "fallback_500"
        profile = self.payload["profiles"][name]
        return {key: float(value) for key, value in profile.items()}

    def controls(self, source: str) -> Dict[str, Any]:
        return dict(self.payload.get("controls", {}).get(source, {}))


__all__ = [
    "DEFAULT_POLICY_PATH", "FusionSource", "MultiSourceFusionReport",
    "MultiSourceProbabilityFusion", "MultiSourceWeightPolicy",
]
