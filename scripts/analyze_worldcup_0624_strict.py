from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260624")
MARKET_PATH = BASE / "market/latest_market.json"
POLYMARKET_PATH = BASE / "polymarket_snapshot.json"
ONLINE_PATH = BASE / "online_review_sources.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周二045", "home": "葡萄牙", "away": "乌兹别克斯坦", "home_en": "Portugal", "away_en": "Uzbekistan",
        "kickoff": "2026-06-24T01:00:00+08:00", "fixture_id": 1489404, "venue": "NRG Stadium, Houston",
        "rank": (5, 50), "recent": ((10, 22, 10), (10, 14, 14)),
        "first_round": "葡萄牙1-1刚果(金)；乌兹别克斯坦1-3哥伦比亚",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Houston 12:00，33.3C、湿度51%、降水1%、风速13.6km/h；NRG可闭合顶棚但屋顶状态未确认",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停与正式首发端点均0行；500与Opta仅给预计阵容，不能视作官方确认",
        "group_direct_rivalry": True,
        "tags": ["massive_favorite_depth", "low_block_opponent", "defensive_collapse_risk", "favorite_rotation_risk"],
        "high_scoring_risk": 0.38, "volatility": 0.69, "favorite_cover_trigger": True,
        "lambda_context": (0.18, -0.06), "proxy_weight": 0.70,
        "forced_scores": ["2-0", "3-0", "3-1", "4-0", "4-1", "2-1", "1-0", "1-1", "5-0", "5-1", "0-1"],
    },
    {
        "code": "周二046", "home": "英格兰", "away": "加纳", "home_en": "England", "away_en": "Ghana",
        "kickoff": "2026-06-24T04:00:00+08:00", "fixture_id": 1489402, "venue": "Gillette Stadium, Boston",
        "rank": (4, 73), "recent": ((10, 26, 4), (10, 11, 13)),
        "first_round": "英格兰4-2克罗地亚；加纳1-0巴拿马",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Foxborough 16:00，19.8C、湿度88%、降水34%、多云代码3、风速9.0km/h",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停与正式首发端点均0行；赛前媒体只提供预测阵容，最终轮换未知",
        "group_direct_rivalry": True,
        "tags": ["massive_favorite_depth", "organized_transition_underdog", "set_piece_underdog_threat", "favorite_rotation_risk"],
        "high_scoring_risk": 0.25, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (0.10, -0.04), "proxy_weight": 0.68,
        "forced_scores": ["2-0", "2-1", "3-0", "3-1", "1-0", "1-1", "4-0", "4-1", "0-1", "2-2"],
    },
    {
        "code": "周二047", "home": "巴拿马", "away": "克罗地亚", "home_en": "Panama", "away_en": "Croatia",
        "kickoff": "2026-06-24T07:00:00+08:00", "fixture_id": 1489403, "venue": "BMO Field, Toronto",
        "rank": (34, 11), "recent": ((10, 17, 16), (10, 20, 14)),
        "first_round": "巴拿马0-1加纳；克罗地亚2-4英格兰",
        "market_1x2_source": "500竞彩官方",
        "weather": "Toronto 19:00，23.2C、湿度49%、降水0%、晴、风速16.8km/h",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停与正式首发端点均0行；500与Opta预计阵容均保留双方主要骨干",
        "group_direct_rivalry": True,
        "tags": ["away_depth_upside", "organized_transition_underdog", "comeback_equalizer_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.30, "volatility": 0.76, "favorite_cover_trigger": False,
        "lambda_context": (-0.04, 0.11), "proxy_weight": 0.64,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3", "0-4"],
    },
    {
        "code": "周二048", "home": "哥伦比亚", "away": "刚果(金)", "home_en": "Colombia", "away_en": "DR Congo",
        "kickoff": "2026-06-24T10:00:00+08:00", "fixture_id": 1539008, "venue": "Estadio Akron, Guadalajara",
        "rank": (13, 46), "recent": ((10, 25, 11), (10, 10, 2)),
        "first_round": "哥伦比亚3-1乌兹别克斯坦；刚果(金)1-1葡萄牙",
        "market_1x2_source": "500竞彩官方",
        "weather": "Guadalajara 20:00，18.1C、湿度92%、降水54%、小雨代码51、风速8.4km/h",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停与正式首发端点均0行；刚果(金)近10场仅失2球，防守完整性需按事实保留",
        "group_direct_rivalry": True,
        "tags": ["strong_defense_opponent", "organized_transition_underdog", "plus_one_cover_risk", "low_block_opponent"],
        "high_scoring_risk": 0.16, "volatility": 0.64, "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.05), "proxy_weight": 0.64,
        "forced_scores": ["1-0", "1-1", "2-0", "2-1", "0-0", "0-1", "1-2", "2-2", "3-0", "3-1"],
    },
]


def enrich(meta: dict, market: dict) -> dict:
    current = market["current"]
    deep = market["deep_market"]
    one_x_two = current["one_x_two"] or {
        "3": deep["ouzhi"]["current"][0], "1": deep["ouzhi"]["current"][1], "0": deep["ouzhi"]["current"][2],
    }
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
    polymarket = json.loads(POLYMARKET_PATH.read_text(encoding="utf-8"))["matches"]
    online = json.loads(ONLINE_PATH.read_text(encoding="utf-8"))["matches"]
    weight_policy = MultiSourceWeightPolicy()
    polymarket_controls = weight_policy.controls("polymarket")
    opta_controls = weight_policy.controls("opta")
    for match in matches:
        code = match["code"]
        external = polymarket[code]
        opta = online[code]["opta"]
        fallback_500 = "未开售" in match["market_1x2_source"]
        match["multi_source_result_fusion"] = {
            "base_weights": weight_policy.result_profile(official_500=not fallback_500),
            "fivehundred_quality": 1.0,
            "external_sources": [
                {
                    "name": "opta",
                    "probabilities": {"home": opta["home"], "draw": opta["draw"], "away": opta["away"]},
                    "quality": float(opta_controls["default_quality"]),
                    "correlation_discount": 1.0,
                    "apply_deviation_discount": bool(opta_controls["apply_deviation_discount"]),
                    "source_type": "external_model",
                    "metadata": {"url": opta["url"], "simulations": opta["simulations"], "direct_probability_weight": True},
                },
                {
                    "name": "polymarket",
                    "probabilities": external["normalized_probabilities"],
                    "quality": min(1.0, external["quality_weight"] / 0.30),
                    "correlation_discount": float(polymarket_controls["correlation_discount"]),
                    "apply_deviation_discount": bool(polymarket_controls["apply_deviation_discount"]),
                    "source_type": "market",
                    "metadata": {
                        "event_url": external["event_url"], "liquidity": external["liquidity"],
                        "volume": external["volume"], "average_spread": external["average_spread"],
                        "updated_at": external["updated_at"],
                    },
                },
            ],
            "gpt_direct_probability_weight": weight_policy.controls("gpt")["direct_probability_weight"],
        }
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260624-v1",
        "notes": [
            "真实赛前xG/xGA不可用，使用项目proxy xG并与离线世界杯模型融合。",
            "API-Football prediction的Poisson字段异常或无样本，不输入最终概率；Opta仅作独立复核。",
            "普通三向、让球三向、总进球先去水，再做贝叶斯融合；正式首发均未发布。",
            "赛果使用Poisson、500、Opta、Polymarket一次性多源融合，消除顺序依赖。",
            "Polymarket按流动性、成交量和价差评分，再施加与500的相关性折扣；GPT保持0%直接概率权重。",
            "第二轮积分与净胜球约束进入战意、节奏和决策迭代层。",
        ],
        "matches": [analyze_match(match, trained) for match in matches],
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "summary": [{
            "code": item["identity"]["code"], "result": item["final"]["result"],
            "handicap": item["final"]["handicap_home_settlement"], "mean": item["means"]["decision_final"],
            "scores": [score["score"] for score in item["final"]["scorelines"][:7]],
            "rules": item["decision_iteration"]["applied_rules"], "consistency": item["consistency"]["status"],
        } for item in output["matches"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
