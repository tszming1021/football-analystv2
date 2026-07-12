from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260625")
MARKET_PATH = BASE / "market/latest_market.json"
POLYMARKET_PATH = BASE / "polymarket_snapshot.json"
ONLINE_PATH = BASE / "online_review_sources.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周三049", "home": "瑞士", "away": "加拿大", "home_en": "Switzerland", "away_en": "Canada",
        "kickoff": "2026-06-25T03:00:00+08:00", "fixture_id": 1489408, "venue": "BC Place, Vancouver",
        "rank": (19, 30), "recent": ((10, 20, 10), (10, 15, 4)),
        "real_xg_shrunk": ((1.690, 0.925), (1.785, 0.983)),
        "first_round": "两轮后同积4分；瑞士5进2失，加拿大7进1失",
        "market_1x2_source": "500竞彩官方",
        "weather": "Vancouver 12:00，25.2C、湿度54%、降水1%、多云、风速8.7km/h；BC Place可闭合顶棚，状态未确认",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API确认加拿大I. Kone小腿骨折，并新增A. Jones伤停记录（原因字段为空）；正式首发均未发布",
        "api_endpoint_status": {"predictions": 1, "injuries": 2, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group_final", "round_index": 3,
        "tags": ["top_table_direct_rival", "strong_defense_opponent", "organized_transition_underdog"],
        "high_scoring_risk": 0.16, "volatility": 0.54, "favorite_cover_trigger": False,
        "lambda_context": (-0.05, -0.04), "proxy_weight": 0.70,
        "forced_scores": ["1-1", "2-1", "1-2", "2-2", "1-0", "0-1", "2-0", "0-2", "3-1", "2-3"],
    },
    {
        "code": "周三050", "home": "波黑", "away": "卡塔尔", "home_en": "Bosnia-Herzegovina", "away_en": "Qatar",
        "kickoff": "2026-06-25T03:00:00+08:00", "fixture_id": 1539009, "venue": "Lumen Field, Seattle",
        "rank": (64, 56), "recent": ((10, 15, 13), (10, 5, 16)),
        "real_xg_shrunk": ((1.012, 1.335), (0.950, 2.087)),
        "first_round": "两轮后同积1分；波黑净胜球-3，卡塔尔-6，均必须取胜",
        "market_1x2_source": "500竞彩官方",
        "weather": "Seattle 12:00，26.7C、湿度41%、无降水、晴、风速7.3km/h",
        "weather_suppression": False, "material_absence_team": "both", "lineup_uncertainty": True,
        "absence_note": "API确认波黑T. Muharemovic停赛；卡塔尔Homam Ahmed、Assim Madibo停赛；正式首发未发布",
        "api_endpoint_status": {"predictions": 1, "injuries": 3, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group_final", "round_index": 3,
        "tags": ["massive_favorite_depth", "defensive_collapse_risk", "open_league_high_variance", "home_defensive_leak"],
        "high_scoring_risk": 0.38, "volatility": 0.78, "favorite_cover_trigger": True,
        "lambda_context": (0.16, 0.02), "proxy_weight": 0.68,
        "forced_scores": ["2-0", "2-1", "3-0", "3-1", "4-0", "4-1", "1-0", "1-1", "1-2", "2-2", "2-3"],
    },
    {
        "code": "周三051", "home": "苏格兰", "away": "巴西", "home_en": "Scotland", "away_en": "Brazil",
        "kickoff": "2026-06-25T06:00:00+08:00", "fixture_id": 1489406, "venue": "Hard Rock Stadium, Miami",
        "rank": (42, 6), "recent": ((10, 20, 11), (10, 26, 11)),
        "real_xg_shrunk": ((1.073, 1.127), (1.315, 1.053)),
        "first_round": "巴西4分净胜球+3，苏格兰3分净胜球0；巴西一分基本晋级，苏格兰需抢分",
        "market_1x2_source": "500竞彩官方",
        "weather": "Miami 18:00，31.3C、湿度58%、强阵雨代码82、降水概率15%、风速22.9km/h",
        "weather_suppression": True, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API列巴西Neymar小腿伤、Raphinha腿后侧肌肉伤；正式首发未发布，巴西存在避免伤停和停赛的轮换风险",
        "api_endpoint_status": {"predictions": 1, "injuries": 2, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group_final", "round_index": 3,
        "tags": ["favorite_rotation_risk", "organized_transition_underdog", "set_piece_underdog_threat", "plus_one_cover_risk"],
        "high_scoring_risk": 0.21, "volatility": 0.65, "favorite_cover_trigger": False,
        "lambda_context": (0.02, -0.06), "proxy_weight": 0.66,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3", "0-4"],
    },
    {
        "code": "周三052", "home": "摩洛哥", "away": "海地", "home_en": "Morocco", "away_en": "Haiti",
        "kickoff": "2026-06-25T06:00:00+08:00", "fixture_id": 1489405, "venue": "Mercedes-Benz Stadium, Atlanta",
        "rank": (7, 83), "recent": ((10, 20, 4), (10, 12, 11)),
        "real_xg_shrunk": ((1.207, 1.082), (1.027, 1.163)),
        "first_round": "摩洛哥4分净胜球+1，与巴西争头名；海地0分已出局",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Atlanta 18:00，30.5C、湿度33%、无降水、多云、风速3.3km/h；Mercedes-Benz Stadium可闭合顶棚，状态未确认",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点0行；双方正式首发未发布，0行不等于确认全员健康",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group_final", "round_index": 3,
        "tags": ["massive_favorite_depth", "defensive_collapse_risk", "low_block_opponent"],
        "high_scoring_risk": 0.42, "volatility": 0.69, "favorite_cover_trigger": True,
        "lambda_context": (0.28, -0.10), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "3-1", "4-0", "4-1", "5-0", "5-1", "1-0", "2-1", "1-1", "0-1", "2-2", "6-0"],
    },
    {
        "code": "周三053", "home": "南非", "away": "韩国", "home_en": "South Africa", "away_en": "South Korea",
        "kickoff": "2026-06-25T09:00:00+08:00", "fixture_id": 1489407, "venue": "Estadio BBVA, Monterrey",
        "rank": (60, 25), "recent": ((10, 10, 13), (10, 13, 12)),
        "real_xg_shrunk": ((1.055, 1.200), (1.348, 1.013)),
        "first_round": "韩国3分净胜球0，取胜锁定第二；南非1分净胜球-2，必须取胜",
        "market_1x2_source": "500竞彩官方",
        "weather": "Monterrey 19:00，30.8C、湿度44%、无降水、风速22.9km/h",
        "weather_suppression": True, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认南非T. Mokoena累积黄牌停赛；正式首发未发布",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group_final", "round_index": 3,
        "tags": ["away_depth_upside", "home_defensive_leak", "open_league_high_variance", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.28, "volatility": 0.77, "favorite_cover_trigger": False,
        "lambda_context": (0.02, 0.08), "proxy_weight": 0.65,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3", "0-4"],
    },
    {
        "code": "周三054", "home": "捷克", "away": "墨西哥", "home_en": "Czech Republic", "away_en": "Mexico",
        "kickoff": "2026-06-25T09:00:00+08:00", "fixture_id": 1539010, "venue": "Estadio Azteca, Mexico City",
        "rank": (40, 14), "recent": ((10, 18, 10), (10, 18, 2)),
        "real_xg_shrunk": ((1.122, 1.400), (1.145, 0.950)),
        "first_round": "墨西哥6分净胜球+3已锁定头名；捷克1分净胜球-1，必须取胜",
        "market_1x2_source": "500竞彩官方",
        "weather": "Mexico City 19:00，16.8C、湿度81%、细雨概率94%、风速1.9km/h",
        "weather_suppression": True, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API列捷克D. Jurasek大腿问题；墨西哥已锁定头名，避免伤停/停赛的轮换动机显著，正式首发未发布",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group_final", "round_index": 3,
        "tags": ["favorite_rotation_risk", "organized_transition_underdog", "plus_one_cover_risk", "weather_suppression"],
        "high_scoring_risk": 0.17, "volatility": 0.75, "favorite_cover_trigger": False,
        "lambda_context": (0.10, -0.10), "proxy_weight": 0.66,
        "forced_scores": ["0-1", "1-1", "1-0", "1-2", "0-2", "2-1", "2-2", "0-0", "0-3", "1-3", "2-3"],
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
        external_sources = []
        if opta.get("verified"):
            external_sources.append({
                "name": "opta",
                "probabilities": {"home": opta["home"], "draw": opta["draw"], "away": opta["away"]},
                "quality": float(opta_controls["default_quality"]),
                "correlation_discount": 1.0,
                "apply_deviation_discount": bool(opta_controls["apply_deviation_discount"]),
                "source_type": "external_model",
                "metadata": {"url": opta["url"], "simulations": opta["simulations"], "verified": True},
            })
        external_sources.append({
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
        })
        match["multi_source_result_fusion"] = {
            "base_weights": weight_policy.result_profile(official_500=not fallback_500),
            "fivehundred_quality": 1.0,
            "external_sources": external_sources,
            "gpt_direct_probability_weight": weight_policy.controls("gpt")["direct_probability_weight"],
        }
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260625-v1",
        "notes": [
            "前两轮API真实xG/xGA按两场样本可靠度0.33向国家队基准收缩，再进入proxy xG与离线世界杯模型融合。",
            "赛果使用Poisson、500、可核验Opta和Polymarket一次性融合；周三053无可核验Opta页面，Opta权重为0并自动归一。",
            "普通三向、让球三向、总进球先去水，再做贝叶斯融合；正式首发均未发布。",
            "末轮积分、净胜球、同时开球和已锁定名次的轮换风险进入比赛语境；淘汰赛对手选择不直接改变概率。",
            "GPT和奇门保持0%直接概率权重。",
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
