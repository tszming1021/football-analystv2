#!/usr/bin/env python3
"""赛后复盘 CLI。

用于把赛前推荐和赛后结果落库，持续统计命中率、ROI 和错误归因。
"""

import argparse
import json
from typing import Optional

from core.post_match_review import PredictionReviewRecord, PostMatchReviewStore, ReviewEvaluator


def add_prediction(args) -> int:
    store = PostMatchReviewStore(args.db)
    record = PredictionReviewRecord(
        match_key=args.match_key,
        match_date=args.match_date or "",
        home_team=args.home,
        away_team=args.away,
        recommendation=args.recommendation,
        recommended_market=args.market,
        recommended_odds=args.odds,
        model_probability=args.probability,
        predicted_score=args.predicted_score,
        predicted_goals=args.predicted_goals,
        error_tags=[],
        notes=args.notes or "",
    )
    row_id = store.save_prediction(record)
    print(f"已保存赛前预测: id={row_id}, match_key={args.match_key}")
    return 0


def update_result(args) -> int:
    store = PostMatchReviewStore(args.db)
    record = store.latest_by_match_key(args.match_key)
    if not record:
        raise SystemExit(f"未找到 match_key={args.match_key} 的赛前预测")

    odds = args.odds if args.odds is not None else record.get("recommended_odds")
    market = args.market or record.get("recommended_market") or ""
    recommendation = args.recommendation or record.get("recommendation") or ""
    evaluated = ReviewEvaluator.evaluate(
        recommendation=recommendation,
        market=market,
        odds=odds,
        actual_score=args.actual_score,
        handicap=args.handicap,
        stake=args.stake,
    )
    store.update_result(
        match_key=args.match_key,
        actual_score=args.actual_score,
        actual_result=evaluated["actual_result"],
        recommendation_hit=evaluated["recommendation_hit"],
        roi=evaluated["roi"],
        error_tags=args.error_tags or evaluated["error_tags"],
        notes=args.notes or "",
    )
    print(json.dumps(evaluated, ensure_ascii=False, indent=2))
    return 0


def show_summary(args) -> int:
    store = PostMatchReviewStore(args.db)
    print(json.dumps(store.summary(), ensure_ascii=False, indent=2))
    return 0


def list_recent(args) -> int:
    store = PostMatchReviewStore(args.db)
    rows = store.list_recent(args.limit)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="赛后复盘、命中率和ROI统计")
    parser.add_argument("--db", default="data/post_match_reviews.sqlite3", help="复盘数据库路径")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="保存一条赛前预测")
    add.add_argument("--match-key", required=True)
    add.add_argument("--match-date", default="")
    add.add_argument("--home", required=True)
    add.add_argument("--away", required=True)
    add.add_argument("--recommendation", required=True)
    add.add_argument("--market", required=True)
    add.add_argument("--odds", type=float)
    add.add_argument("--probability", type=float)
    add.add_argument("--predicted-score", default="")
    add.add_argument("--predicted-goals", default="")
    add.add_argument("--notes", default="")
    add.set_defaults(func=add_prediction)

    result = sub.add_parser("result", help="录入赛后结果并自动判断命中")
    result.add_argument("--match-key", required=True)
    result.add_argument("--actual-score", required=True)
    result.add_argument("--handicap", type=float)
    result.add_argument("--odds", type=float)
    result.add_argument("--stake", type=float, default=1.0)
    result.add_argument("--recommendation")
    result.add_argument("--market")
    result.add_argument("--error-tags", nargs="*")
    result.add_argument("--notes", default="")
    result.set_defaults(func=update_result)

    summary = sub.add_parser("summary", help="显示总体复盘统计")
    summary.set_defaults(func=show_summary)

    recent = sub.add_parser("list", help="显示最近记录")
    recent.add_argument("--limit", type=int, default=20)
    recent.set_defaults(func=list_recent)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
