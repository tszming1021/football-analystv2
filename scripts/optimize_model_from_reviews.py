from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.model_optimizer import ModelReviewOptimizer, write_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate reviewed matches and emit model optimization suggestions.")
    parser.add_argument("--input", default="data/model_optimization/review_samples_20260705_0707.json")
    parser.add_argument("--output-json", default="data/model_optimization/model_optimization_report.json")
    parser.add_argument("--output-md", default="data/model_optimization/model_optimization_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    optimizer = ModelReviewOptimizer.from_json(args.input)
    report = optimizer.evaluate()
    write_report(report, args.output_json, args.output_md)
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")
    print(f"samples={report.samples} main_hit={report.main_hit_rate:.1%} result_top={report.result_top_hit_rate:.1%} brier={report.brier:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
