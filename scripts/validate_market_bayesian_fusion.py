#!/usr/bin/env python3
"""Smoke-test market dewatering and Bayesian fusion."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.bayesian_fusion import BayesianProbabilityFusion
from core.market_dewater import MarketDewater


def main() -> None:
    market = MarketDewater.dewater_1x2(
        {"home_win": 1.48, "draw": 4.35, "away_win": 6.67},
        source="smoke_test",
    )
    prior = {"home": 0.58, "draw": 0.25, "away": 0.17}
    posterior = BayesianProbabilityFusion.fuse_3way(
        prior,
        market.probabilities,
        prior_strength=13,
        evidence_strength=12,
    )
    payload = {
        "dewatered": market.to_dict(),
        "bayesian": posterior.to_dict(),
        "posterior_sum": round(sum(posterior.posterior_probabilities.values()), 8),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
