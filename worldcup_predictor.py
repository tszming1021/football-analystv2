#!/usr/bin/env python3
"""CLI for the World Cup prediction module."""

import argparse
import json

from core.worldcup_predictor import WorldCupPredictor


def main() -> int:
    parser = argparse.ArgumentParser(description="世界杯数据获取与预测模块")
    parser.add_argument("home_team", help="主队/球队A，如 Argentina")
    parser.add_argument("away_team", help="客队/球队B，如 France")
    parser.add_argument("--season", type=int, default=2026, help="世界杯赛季，默认 2026")
    parser.add_argument("--bankroll", type=float, default=10000, help="用于凯利计算的资金池")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = parser.parse_args()

    predictor = WorldCupPredictor(season=args.season)
    result = predictor.predict_match(args.home_team, args.away_team, bankroll=args.bankroll)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print("=" * 72)
    print(f"世界杯预测: {args.home_team} vs {args.away_team}")
    print("=" * 72)
    if result.fixture:
        print(f"比赛: {result.fixture.home_team} vs {result.fixture.away_team}")
        print(f"时间: {result.fixture.match_date or '未知'}")
        print(f"赛程来源: {result.fixture.source}")
    else:
        print("比赛: 未找到赛程，使用球队名称直接预测")

    print("\n模型输入:")
    print(f"  {result.home_form.team}: {result.home_form.source}, GF={result.home_form.goals_for_avg}, GA={result.home_form.goals_against_avg}")
    print(f"  {result.away_form.team}: {result.away_form.source}, GF={result.away_form.goals_for_avg}, GA={result.away_form.goals_against_avg}")

    print("\n泊松预测:")
    print(f"  预期进球: {result.expected_home_goals:.2f} - {result.expected_away_goals:.2f}")
    print(f"  主胜: {result.probabilities['home_win']:.1%}")
    print(f"  平局: {result.probabilities['draw']:.1%}")
    print(f"  客胜: {result.probabilities['away_win']:.1%}")
    print(f"  最可能比分: {result.most_likely_score[0]}-{result.most_likely_score[1]}")

    if result.odds:
        print("\n赔率:")
        for odds in result.odds[:5]:
            print(f"  {odds.bookmaker}: {odds.home_win:.2f} / {odds.draw:.2f} / {odds.away_win:.2f} ({odds.source})")
    else:
        print("\n赔率: 未获取到真实赔率，已跳过 EV/凯利")

    if result.kelly:
        print("\n凯利/EV:")
        for item in result.kelly[:5]:
            print(f"  {item['bet_type']}: EV {item['expected_value']:+.1%}, 凯利 {item['kelly_fraction']:.2%}, {item['reason']}")

    if result.warnings:
        print("\n数据限制:")
        for warning in result.warnings[:10]:
            print(f"  - {warning}")

    print("\n数据源:")
    print("  " + (", ".join(result.sources_used) if result.sources_used else "无"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
