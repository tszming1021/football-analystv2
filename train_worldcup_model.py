#!/usr/bin/env python3
"""Train the offline World Cup/national-team model.

Historical CSV/JSON files are read only during this command. The runtime
prediction module then uses the generated JSON artifact.
"""

import argparse
import json
from pathlib import Path

from core.worldcup_trained_model import DEFAULT_DATA_DIR, DEFAULT_MODEL_PATH, WorldCupOfflineTrainer


def main() -> int:
    parser = argparse.ArgumentParser(description="训练世界杯/国家队离线模型")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="历史数据目录")
    parser.add_argument("--output", default=str(DEFAULT_MODEL_PATH), help="训练产物 JSON 输出路径")
    parser.add_argument("--cutoff-date", help="只使用该日期之前的比赛，格式 YYYY-MM-DD，用于防止赛后泄漏")
    parser.add_argument("--json", action="store_true", help="输出完整训练元数据")
    args = parser.parse_args()

    trainer = WorldCupOfflineTrainer(Path(args.data_dir), cutoff_date=args.cutoff_date)
    artifact = trainer.save(Path(args.output))
    payload = artifact.to_dict()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=" * 72)
    print("世界杯/国家队离线模型训练完成")
    print("=" * 72)
    print(f"输出文件: {args.output}")
    print(f"历史数据目录: {args.data_dir}")
    print(f"比赛样本: {payload['metadata'].get('matches_loaded')}")
    print(f"球队数量: {payload['metadata'].get('teams')}")
    print(f"全球场均进球(单队): {payload['global_goals_per_team']}")
    top = sorted(
        payload["team_profiles"].values(),
        key=lambda item: item["elo"],
        reverse=True,
    )[:10]
    print("\nElo Top 10:")
    for idx, team in enumerate(top, 1):
        print(f"{idx:>2}. {team['team']:<18} Elo={team['elo']:.1f} GF={team['goals_for_avg']:.2f} GA={team['goals_against_avg']:.2f}")
    print("\n运行时说明: 之后预测只需要读取这个 JSON，不再读取历史 CSV。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
