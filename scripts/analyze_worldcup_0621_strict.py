from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from scripts.analyze_worldcup_0620_strict_1847 import analyze_match
from core.worldcup_trained_model import WorldCupTrainedModel


OUT_PATH = Path("data/worldcup_20260622/model_analysis.json")

MATCHES = [
    {
        "code": "周日037",
        "home": "西班牙",
        "away": "沙特阿拉伯",
        "home_en": "Spain",
        "away_en": "Saudi Arabia",
        "kickoff": "2026-06-22T00:00:00+08:00",
        "fixture_id": 1489397,
        "venue": "Mercedes-Benz Stadium, Atlanta",
        "rank": (2, 61),
        "recent": ((10, 25, 4), (10, 10, 13)),
        "first_round": "西班牙0-0佛得角；沙特阿拉伯1-1乌拉圭",
        "market_1x2": (1.10, 10.27, 24.89),
        "market_1x2_source": "500百家即时均值（竞彩三向未开售）",
        "handicap": -2.0,
        "handicap_3way": (1.63, 4.50, 3.40),
        "total_exact": (28.00, 8.50, 4.80, 3.80, 4.10, 5.90, 8.80, 9.75),
        "score_prices": {
            "1-0": 8.75, "2-0": 6.00, "2-1": 10.00, "3-0": 5.50, "3-1": 9.50,
            "3-2": 38.00, "4-0": 6.85, "4-1": 13.00, "4-2": 45.00, "5-0": 10.00,
            "5-1": 22.00, "5-2": 60.00, "0-0": 28.00, "1-1": 19.00, "2-2": 45.00,
            "3-3": 150.00, "0-1": 70.00, "0-2": 200.00, "1-2": 50.00, "0-3": 500.00,
            "1-3": 300.00, "2-3": 200.00,
        },
        "market_total_line": 3.43,
        "asian_line": -2.578,
        "weather": "Atlanta 12:00，26.6C、湿度69%、降水0%、风速13.3km/h；Mercedes-Benz Stadium可闭合顶棚",
        "weather_suppression": False,
        "material_absence_team": "home",
        "absence_note": "API伤停/首发0行；Transfermarkt未列缺席；Al Jazeera引述亚马尔称腿后肌恢复中，暂不适合踢满90分钟",
        "group_direct_rivalry": True,
        "tags": ["massive_favorite_depth", "favorite_rotation_risk", "low_block_opponent", "group_draw_wave"],
        "high_scoring_risk": 0.42,
        "volatility": 0.72,
        "favorite_cover_trigger": True,
        "lambda_context": (0.12, -0.08),
        "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "4-0", "5-0", "3-1", "4-1", "5-1", "1-0", "2-1", "1-1", "2-2", "1-2", "3-2"],
    },
    {
        "code": "周日038",
        "home": "比利时",
        "away": "伊朗",
        "home_en": "Belgium",
        "away_en": "Iran",
        "kickoff": "2026-06-22T03:00:00+08:00",
        "fixture_id": 1489395,
        "venue": "SoFi Stadium, Los Angeles",
        "rank": (9, 20),
        "recent": ((10, 32, 7), (10, 16, 7)),
        "first_round": "比利时1-1埃及；伊朗2-2新西兰",
        "market_1x2": (1.28, 4.61, 7.60),
        "market_1x2_source": "500竞彩官方",
        "handicap": -1.0,
        "handicap_3way": (1.92, 3.72, 2.94),
        "total_exact": (13.00, 5.40, 3.65, 3.40, 4.90, 9.00, 15.00, 24.00),
        "score_prices": {
            "1-0": 6.50, "2-0": 6.50, "2-1": 6.50, "3-0": 8.50, "3-1": 8.75,
            "3-2": 25.00, "4-0": 16.00, "4-1": 19.00, "4-2": 45.00, "5-0": 35.00,
            "5-1": 40.00, "5-2": 80.00, "0-0": 13.00, "1-1": 8.00, "2-2": 18.50,
            "3-3": 70.00, "0-1": 20.00, "0-2": 50.00, "1-2": 23.00, "0-3": 150.00,
            "1-3": 80.00, "2-3": 70.00,
        },
        "market_total_line": 2.63,
        "asian_line": -1.281,
        "weather": "Los Angeles 12:00，22.5C、湿度64%、降水0%、风速13.1km/h；SoFi Stadium顶棚覆盖，天气影响较低",
        "weather_suppression": False,
        "material_absence_team": "home",
        "absence_note": "API伤停/首发0行；Transfermarkt列多库患病、德巴斯特腿后肌受伤，未获球队官方二次确认",
        "group_direct_rivalry": True,
        "tags": ["organized_transition_underdog", "set_piece_underdog_threat", "favorite_rotation_risk", "group_draw_wave"],
        "high_scoring_risk": 0.26,
        "volatility": 0.68,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.05, 0.06),
        "proxy_weight": 0.82,
        "forced_scores": ["1-0", "2-0", "2-1", "3-0", "3-1", "4-0", "4-1", "1-1", "2-2", "1-2", "2-3", "3-2"],
    },
    {
        "code": "周日039",
        "home": "乌拉圭",
        "away": "佛得角",
        "home_en": "Uruguay",
        "away_en": "Cape Verde",
        "kickoff": "2026-06-22T06:00:00+08:00",
        "fixture_id": 1489398,
        "venue": "Hard Rock Stadium, Miami",
        "rank": (16, 67),
        "recent": ((10, 11, 8), (10, 17, 9)),
        "first_round": "乌拉圭1-1沙特阿拉伯；佛得角0-0西班牙",
        "market_1x2": (1.30, 4.05, 8.80),
        "market_1x2_source": "500竞彩官方",
        "handicap": -1.0,
        "handicap_3way": (2.14, 3.23, 2.84),
        "total_exact": (8.50, 3.90, 3.15, 3.85, 6.50, 13.00, 24.00, 32.00),
        "score_prices": {
            "1-0": 4.90, "2-0": 5.00, "2-1": 7.25, "3-0": 7.50, "3-1": 12.00,
            "3-2": 50.00, "4-0": 17.00, "4-1": 29.00, "4-2": 80.00, "5-0": 45.00,
            "5-1": 65.00, "5-2": 200.00, "0-0": 8.50, "1-1": 7.30, "2-2": 27.00,
            "3-3": 120.00, "0-1": 15.00, "0-2": 45.00, "1-2": 26.00, "0-3": 175.00,
            "1-3": 120.00, "2-3": 120.00,
        },
        "market_total_line": 2.29,
        "asian_line": -1.047,
        "weather": "Miami 18:00，30.3C、湿度68%、降水25%、雷暴代码95、风速11.9km/h；Hard Rock Stadium为开放式场地",
        "weather_suppression": True,
        "material_absence_team": "home",
        "absence_note": "API伤停/首发0行；Transfermarkt列德阿拉斯凯塔、阿劳霍肌肉伤，未获球队官方二次确认",
        "group_direct_rivalry": True,
        "tags": ["organized_transition_underdog", "low_block_opponent", "favorite_rotation_risk", "group_draw_wave"],
        "high_scoring_risk": 0.14,
        "volatility": 0.61,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.05),
        "proxy_weight": 0.72,
        "forced_scores": ["1-0", "2-0", "2-1", "3-0", "3-1", "4-0", "4-1", "0-0", "1-1", "2-2", "0-1", "1-2", "3-2"],
    },
    {
        "code": "周日040",
        "home": "新西兰",
        "away": "埃及",
        "home_en": "New Zealand",
        "away_en": "Egypt",
        "kickoff": "2026-06-22T09:00:00+08:00",
        "fixture_id": 1489396,
        "venue": "BC Place, Vancouver",
        "rank": (85, 29),
        "recent": ((10, 9, 19), (10, 11, 7)),
        "first_round": "新西兰2-2伊朗；埃及1-1比利时",
        "market_1x2": (5.85, 3.80, 1.44),
        "market_1x2_source": "500竞彩官方",
        "handicap": 1.0,
        "handicap_3way": (2.40, 3.34, 2.42),
        "total_exact": (10.00, 4.30, 3.20, 3.60, 6.00, 12.00, 21.00, 30.00),
        "score_prices": {
            "1-0": 14.00, "2-0": 30.00, "2-1": 17.00, "3-0": 100.00, "3-1": 70.00,
            "3-2": 70.00, "4-0": 400.00, "4-1": 250.00, "4-2": 250.00, "5-0": 700.00,
            "5-1": 500.00, "5-2": 700.00, "0-0": 10.00, "1-1": 6.80, "2-2": 17.00,
            "3-3": 70.00, "0-1": 5.75, "0-2": 5.80, "1-2": 6.75, "0-3": 10.00,
            "1-3": 12.00, "2-3": 30.00,
        },
        "market_total_line": 2.31,
        "asian_line": 0.953,
        "weather": "Vancouver 18:00，23.7C、湿度42%、降水1%、风速16.0km/h；BC Place可闭合顶棚",
        "weather_suppression": False,
        "material_absence_team": "",
        "absence_note": "API伤停/首发0行；Transfermarkt双方未列缺席；埃及主帅公开否认萨拉赫不和传闻",
        "group_direct_rivalry": True,
        "tags": ["organized_transition_underdog", "plus_one_cover_risk", "away_depth_upside", "group_draw_wave"],
        "high_scoring_risk": 0.22,
        "volatility": 0.69,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.02, 0.05),
        "proxy_weight": 0.72,
        "forced_scores": ["0-1", "0-2", "1-1", "1-2", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3", "3-2"],
    },
]


def main() -> None:
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260621-v1",
        "notes": [
            "真实赛前xG/xGA不可用，使用项目proxy xG并与离线世界杯历史模型融合。",
            "API-Football prediction只有首轮单场样本，且部分goals字段为负数，异常字段不输入模型。",
            "三向、让球三向、总进球均先去水，再与模型先验进行贝叶斯融合。",
            "小组出线形势进入G层与决策迭代，但不直接覆盖市场和数学概率。",
        ],
        "matches": [analyze_match(match, trained) for match in MATCHES],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "matches": len(output["matches"]),
        "summary": [
            {
                "code": item["identity"]["code"],
                "result": item["final"]["result"],
                "handicap": item["final"]["handicap_home_settlement"],
                "mean": item["means"]["decision_final"],
                "scores": [score["score"] for score in item["final"]["scorelines"][:5]],
                "rules": item["decision_iteration"]["applied_rules"],
                "consistency": item["consistency"]["status"],
                "warnings": item["consistency"]["warnings"],
            }
            for item in output["matches"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
