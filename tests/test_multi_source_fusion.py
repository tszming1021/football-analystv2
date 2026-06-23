from __future__ import annotations

import unittest

from core.multi_source_fusion import FusionSource, MultiSourceProbabilityFusion, MultiSourceWeightPolicy


class MultiSourceFusionTests(unittest.TestCase):
    def sources(self):
        return [
            FusionSource("poisson", {"home": 0.55, "draw": 0.25, "away": 0.20}, 45, source_type="model"),
            FusionSource("500", {"home": 0.65, "draw": 0.22, "away": 0.13}, 30, apply_deviation_discount=True, source_type="market"),
            FusionSource("opta", {"home": 0.60, "draw": 0.24, "away": 0.16}, 15, source_type="external_model"),
            FusionSource("polymarket", {"home": 0.63, "draw": 0.23, "away": 0.14}, 10, quality=0.9, correlation_discount=0.75, apply_deviation_discount=True, source_type="market"),
        ]

    def test_probabilities_and_weights_normalize(self):
        report = MultiSourceProbabilityFusion.fuse(self.sources())
        self.assertAlmostEqual(sum(report.posterior_probabilities.values()), 1.0)
        self.assertAlmostEqual(sum(item["normalized_weight"] for item in report.sources.values()), 1.0, places=5)
        self.assertLess(report.sources["polymarket"]["normalized_weight"], 0.10)

    def test_fusion_is_order_independent(self):
        first = MultiSourceProbabilityFusion.fuse(self.sources()).posterior_probabilities
        second = MultiSourceProbabilityFusion.fuse(list(reversed(self.sources()))).posterior_probabilities
        for key in first:
            self.assertAlmostEqual(first[key], second[key], places=12)

    def test_large_market_deviation_is_discounted(self):
        sources = self.sources()
        sources[1] = FusionSource("500", {"home": 0.90, "draw": 0.07, "away": 0.03}, 30, apply_deviation_discount=True)
        report = MultiSourceProbabilityFusion.fuse(sources)
        self.assertEqual(report.sources["500"]["deviation_discount"], 0.75)
        self.assertIn("source_deviation_discounted:500", report.warnings)

    def test_weight_policy_profiles(self):
        policy = MultiSourceWeightPolicy()
        self.assertEqual(policy.result_profile(official_500=True), {"poisson": 45.0, "500": 30.0, "opta": 15.0, "polymarket": 10.0})
        self.assertEqual(policy.result_profile(official_500=False)["500"], 20.0)
        self.assertEqual(policy.controls("gpt")["direct_probability_weight"], 0.0)


if __name__ == "__main__":
    unittest.main()
