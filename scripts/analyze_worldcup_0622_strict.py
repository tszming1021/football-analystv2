from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260623")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周一041", "home": "阿根廷", "away": "奥地利", "home_en": "Argentina", "away_en": "Austria",
        "kickoff": "2026-06-23T01:00:00+08:00", "fixture_id": 1489399, "venue": "AT&T Stadium, Dallas",
        "rank": (1, 24), "recent": ((10, 27, 2), (10, 26, 5)),
        "first_round": "阿根廷3-0阿尔及利亚；奥地利3-1约旦",
        "market_1x2_source": "500竞彩官方", "weather": "Dallas 12:00，31.8C、湿度61%、降水1%、雷暴代码95；AT&T可闭合顶棚但屋顶状态未确认",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": False,
        "absence_note": "API已返回双方官方首发：阿根廷梅西、劳塔罗、德保罗、麦卡利斯特、恩佐同场首发；奥地利Posch实际首发，撤销此前Transfermarkt缺席假设",
        "group_direct_rivalry": True,
        "tags": ["top_table_direct_rival", "strong_defense_opponent", "organized_transition_underdog"],
        "high_scoring_risk": 0.22, "volatility": 0.62, "favorite_cover_trigger": False,
        "lambda_context": (0.02, 0.00), "proxy_weight": 0.62,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "3-0", "3-1", "2-2", "0-1", "3-2", "1-2", "4-1"],
    },
    {
        "code": "周一042", "home": "法国", "away": "伊拉克", "home_en": "France", "away_en": "Iraq",
        "kickoff": "2026-06-23T05:00:00+08:00", "fixture_id": 1539017, "venue": "Lincoln Financial Field, Philadelphia",
        "rank": (3, 57), "recent": ((10, 26, 10), (10, 11, 13)),
        "first_round": "法国3-1塞内加尔；伊拉克1-4挪威",
        "market_1x2_source": "500百家即时均值（竞彩三向未开售）", "weather": "Philadelphia 17:00，33.6C、湿度36%、降水19%、风速22.1km/h",
        "weather_suppression": True, "material_absence_team": "",
        "absence_note": "API伤停、首发和统计端点均0行；Transfermarkt未列缺席，不等同于官方确认全员可用",
        "group_direct_rivalry": False,
        "tags": ["massive_favorite_depth", "defensive_collapse_risk", "low_block_opponent", "favorite_rotation_risk"],
        "high_scoring_risk": 0.44, "volatility": 0.68, "favorite_cover_trigger": True,
        "lambda_context": (0.20, -0.08), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "4-0", "5-0", "3-1", "4-1", "5-1", "1-0", "2-1", "1-1", "0-1", "6-0", "6-1"],
    },
    {
        "code": "周一043", "home": "挪威", "away": "塞内加尔", "home_en": "Norway", "away_en": "Senegal",
        "kickoff": "2026-06-23T08:00:00+08:00", "fixture_id": 1489401, "venue": "MetLife Stadium, New York New Jersey",
        "rank": (31, 15), "recent": ((10, 34, 9), (10, 16, 11)),
        "first_round": "挪威4-1伊拉克；塞内加尔1-3法国",
        "market_1x2_source": "500竞彩官方", "weather": "New York New Jersey 20:00，21.8C、湿度91%、降水31%、风速9.2km/h",
        "weather_suppression": True, "material_absence_team": "",
        "absence_note": "API伤停与首发端点均0行；Transfermarkt双方未列缺席，最终首发未确认",
        "group_direct_rivalry": False,
        "tags": ["organized_transition_underdog", "set_piece_underdog_threat", "comeback_equalizer_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.27, "volatility": 0.74, "favorite_cover_trigger": False,
        "lambda_context": (-0.06, 0.02), "proxy_weight": 0.62,
        "forced_scores": ["1-0", "2-1", "1-1", "2-0", "0-1", "1-2", "2-2", "3-1", "3-2", "2-3", "0-2"],
    },
    {
        "code": "周一044", "home": "约旦", "away": "阿尔及利亚", "home_en": "Jordan", "away_en": "Algeria",
        "kickoff": "2026-06-23T11:00:00+08:00", "fixture_id": 1489400, "venue": "Levi's Stadium, San Francisco Bay Area",
        "rank": (63, 28), "recent": ((10, 16, 16), (10, 19, 6)),
        "first_round": "约旦1-3奥地利；阿尔及利亚0-3阿根廷",
        "market_1x2_source": "500竞彩官方", "weather": "Santa Clara 20:00，16.6C、湿度79%、降水0%、风速13.7km/h",
        "weather_suppression": False, "material_absence_team": "",
        "absence_note": "API伤停与首发端点均0行；Transfermarkt双方未列缺席，最终首发未确认",
        "group_direct_rivalry": True,
        "tags": ["away_depth_upside", "home_defensive_leak", "plus_one_cover_risk", "organized_transition_underdog"],
        "high_scoring_risk": 0.24, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (-0.04, 0.12), "proxy_weight": 0.66,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3", "0-4"],
    },
]


def enrich(meta: dict, market: dict) -> dict:
    current = market["current"]
    deep = market["deep_market"]
    one_x_two = current["one_x_two"]
    if not one_x_two:
        one_x_two = {"3": deep["ouzhi"]["current"][0], "1": deep["ouzhi"]["current"][1], "0": deep["ouzhi"]["current"][2]}
    scores = {label: price for label, price in current["scores"].items() if label[0].isdigit()}
    total = current["total_exact"]
    return {
        **meta,
        "market_1x2": (one_x_two["3"], one_x_two["1"], one_x_two["0"]),
        "handicap": current["handicap"],
        "handicap_3way": (current["handicap_three_way"]["3"], current["handicap_three_way"]["1"], current["handicap_three_way"]["0"]),
        "total_exact": tuple(total[str(index)] for index in range(7)) + (total["7"],),
        "score_prices": scores,
        "market_total_line": deep["daxiao"]["current"][1],
        "asian_line": deep["yazhi"]["current"][1],
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    matches = [enrich(meta, latest[meta["code"]]) for meta in META]
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260622-v1",
        "notes": [
            "真实赛前xG/xGA不可用，使用项目proxy xG并按样本可靠度收缩，再与离线世界杯模型融合。",
            "API-Football prediction仅单场样本且Poisson字段为0%，不输入最终概率。",
            "法国竞彩普通三向未开售，使用500百家即时均值并降低市场证据强度。",
            "三向、让球三向、总进球均先去水，再做贝叶斯融合；奇门仅低权重提示。",
        ],
        "matches": [analyze_match(match, trained) for match in matches],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "summary": [{
            "code": item["identity"]["code"],
            "result": item["final"]["result"],
            "handicap": item["final"]["handicap_home_settlement"],
            "mean": item["means"]["decision_final"],
            "scores": [score["score"] for score in item["final"]["scorelines"][:7]],
            "rules": item["decision_iteration"]["applied_rules"],
            "consistency": item["consistency"]["status"],
        } for item in output["matches"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
