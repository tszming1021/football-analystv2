#!/usr/bin/env python3
"""Apply decision-iteration calibration to a structured analysis JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from core.decision_iteration import DecisionIterationEngine, DecisionIterationFeatures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply the project decision iteration layer.")
    parser.add_argument("--input", required=True, help="Structured analysis JSON containing a matches array.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--worldcup-a-group-overrides",
        action="store_true",
        help="Use known A-group overrides for 2026-06-12 Mexico/South Africa and Korea/Czechia sample.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    engine = DecisionIterationEngine()

    reports = []
    for match in payload.get("matches", []):
        overrides: Dict[str, Any] = {}
        if args.worldcup_a_group_overrides:
            overrides = _worldcup_a_group_overrides(match)
        features = DecisionIterationFeatures.from_structured_match(match, overrides=overrides)
        reports.append(engine.apply(features).to_dict())

    output = {
        "generated_from": str(input_path),
        "rulebook": str(engine.rulebook_path),
        "matches": reports,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def _worldcup_a_group_overrides(match: Dict[str, Any]) -> Dict[str, Any]:
    home = match.get("home")
    away = match.get("away")
    overrides: Dict[str, Any] = {
        "competition_type": "world_cup",
        "stage": "group",
        "round_index": 1,
        "group_direct_rivalry": True,
    }
    if home == "墨西哥" and away == "南非":
        overrides.update({
            "is_host": True,
            "is_opening_match": True,
            "weather_suppression": True,
            "material_absence_team": "墨西哥",
            "lineup_uncertainty": True,
            "tags": ["FIFA确认Malagon伤缺", "南非Modiba疑点", "揭幕战", "高海拔/雨战风险"],
        })
    elif home == "韩国" and away == "捷克":
        overrides.update({
            "weather_suppression": True,
            "material_absence_team": "韩国",
            "lineup_uncertainty": True,
            "tags": ["韩国Kim Min-jae/Hwang In-beom疑点", "捷克中轴完整", "小组直接竞争"],
        })
    return overrides


if __name__ == "__main__":
    raise SystemExit(main())
