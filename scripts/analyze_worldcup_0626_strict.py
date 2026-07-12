from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260626")
MARKET_PATH = BASE / "market/latest_market.json"
POLYMARKET_PATH = BASE / "polymarket_snapshot.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周四055", "home": "厄瓜多尔", "away": "德国", "home_en": "Ecuador", "away_en": "Germany",
        "kickoff": "2026-06-26T04:00:00+08:00", "fixture_id": 1489410, "venue": "MetLife Stadium, New York/New Jersey",
        "rank": (24, 9), "recent": ((2, 0, 1), (2, 9, 2)),
        "first_round": "E组：德国6分/+7已锁定头名；厄瓜多尔1分/-1，必须抢分，取胜才最稳。",
        "market_1x2_source": "500竞彩官方",
        "weather": "New York/New Jersey 16:00，29.0C、湿度37%、降水3%、晴、风速15.6km/h；开放球场但天气可控",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点0行；德国已锁头名，联网复核显示可能轮换，但Undav等替补状态热。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["locked_top", "bench_depth_advantage", "favorite_rotation_risk", "favorite_win_not_clean_sheet", "underdog_must_win", "opponent_must_win", "organized_transition_underdog"],
        "high_scoring_risk": 0.30, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (0.03, -0.03), "proxy_weight": 0.64,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-1", "1-0", "2-2", "2-3", "3-1"],
    },
    {
        "code": "周四056", "home": "库拉索", "away": "科特迪瓦", "home_en": "Curacao", "away_en": "Ivory Coast",
        "kickoff": "2026-06-26T04:00:00+08:00", "fixture_id": 1489409, "venue": "Lincoln Financial Field, Philadelphia",
        "rank": (86, 41), "recent": ((2, 1, 7), (2, 2, 2)),
        "first_round": "E组：科特迪瓦3分/0，平局基本锁定第二；库拉索1分/-6，必须大胜并等待德国帮助。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Philadelphia 16:00，30.3C、湿度30%、降水1%、晴、风速11.9km/h；炎热但湿度较低",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点0行；库拉索门将Eloy Room上一轮高扑救负荷，科特迪瓦平局即可出线。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["favorite_draw_enough", "favorite_conservative_qualification_path", "underdog_must_win", "opponent_must_win", "home_defensive_leak", "away_depth_upside"],
        "high_scoring_risk": 0.36, "volatility": 0.78, "favorite_cover_trigger": True,
        "lambda_context": (0.02, 0.12), "proxy_weight": 0.68,
        "forced_scores": ["0-1", "0-2", "1-2", "0-3", "1-3", "0-4", "1-1", "2-1", "1-0", "2-2", "1-4"],
    },
    {
        "code": "周四057", "home": "突尼斯", "away": "荷兰", "home_en": "Tunisia", "away_en": "Netherlands",
        "kickoff": "2026-06-26T07:00:00+08:00", "fixture_id": 1489412, "venue": "Arrowhead Stadium, Kansas City",
        "rank": (49, 7), "recent": ((2, 1, 9), (2, 7, 3)),
        "first_round": "F组：荷兰4分/+4，与日本同分争头名；突尼斯0分/-8已出局。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Kansas City 18:00，21.9C、湿度90%、降水54%、天气代码53、风速19.3km/h；雨战和高湿压低连续冲刺，但不抹掉实力差。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点0行；突尼斯两轮丢9球且已出局，荷兰仍需争头名。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["massive_favorite_depth", "home_defensive_leak", "away_depth_upside", "eliminated_opponent_no_pressure", "favorite_win_not_clean_sheet", "must_chase_goal_difference"],
        "high_scoring_risk": 0.48, "volatility": 0.82, "favorite_cover_trigger": True,
        "lambda_context": (-0.08, 0.26), "proxy_weight": 0.72,
        "forced_scores": ["0-2", "0-3", "0-4", "1-3", "1-4", "0-5", "1-2", "1-1", "2-1", "2-4", "2-5"],
    },
    {
        "code": "周四058", "home": "日本", "away": "瑞典", "home_en": "Japan", "away_en": "Sweden",
        "kickoff": "2026-06-26T07:00:00+08:00", "fixture_id": 1539011, "venue": "AT&T Stadium, Dallas",
        "rank": (15, 28), "recent": ((2, 6, 2), (2, 6, 6)),
        "first_round": "F组：日本4分/+4，瑞典3分/0。日本不败大概率出线并争头名；瑞典取胜可反超。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Dallas 18:00，32.9C、湿度45%、降水1%、多云、风速22.0km/h；AT&T Stadium可闭合顶棚，顶棚状态未确认",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认日本S. Machino illness缺席；正式首发未发布。Polymarket与500均支持日本方向。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["top_table_direct_rival", "favorite_draw_enough", "favorite_conservative_qualification_path", "set_piece_underdog_threat", "organized_transition_underdog"],
        "high_scoring_risk": 0.27, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (0.03, 0.02), "proxy_weight": 0.66,
        "forced_scores": ["2-1", "1-1", "1-0", "2-0", "2-2", "3-1", "1-2", "0-1", "3-2", "3-0"],
    },
    {
        "code": "周四059", "home": "巴拉圭", "away": "澳大利亚", "home_en": "Paraguay", "away_en": "Australia",
        "kickoff": "2026-06-26T10:00:00+08:00", "fixture_id": 1489411, "venue": "Levi's Stadium, San Francisco Bay Area",
        "rank": (43, 24), "recent": ((2, 2, 4), (2, 2, 2)),
        "first_round": "D组：澳大利亚3分/0，巴拉圭3分/-2。澳大利亚打平锁定第二；巴拉圭必须赢才能反超第二。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Santa Clara 19:00，18.3C、湿度61%、无降水、晴、风速18.8km/h；比赛条件良好",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认巴拉圭M. Almiron红牌停赛；Guardian提到澳大利亚打平即可晋级，RacingPost称澳大利亚Matthew Leckie腿筋伤缺。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["favorite_draw_enough", "favorite_conservative_qualification_path", "underdog_must_win", "opponent_must_win", "material_home_absence", "top_table_direct_rival"],
        "high_scoring_risk": 0.12, "volatility": 0.58, "favorite_cover_trigger": False,
        "lambda_context": (-0.08, -0.04), "proxy_weight": 0.62,
        "forced_scores": ["0-0", "1-1", "1-0", "0-1", "2-1", "1-2", "2-2", "2-0", "0-2"],
    },
    {
        "code": "周四060", "home": "土耳其", "away": "美国", "home_en": "Turkiye", "away_en": "USA",
        "kickoff": "2026-06-26T10:00:00+08:00", "fixture_id": 1539012, "venue": "SoFi Stadium, Los Angeles",
        "rank": (22, 17), "recent": ((2, 0, 3), (2, 6, 1)),
        "first_round": "D组：美国6分/+5已锁定头名；土耳其0分/-3已出局。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Inglewood 19:00，17.9C、湿度82%、无降水、多云、风速12.1km/h；SoFi Stadium顶棚环境稳定",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点0行；联网复核显示美国可能轮换黄牌风险球员，但球队公开口径是不放松，土耳其为荣誉战。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["locked_top", "host_depth", "bench_depth_advantage", "favorite_rotation_risk", "eliminated_opponent_no_pressure", "favorite_win_not_clean_sheet"],
        "high_scoring_risk": 0.30, "volatility": 0.70, "favorite_cover_trigger": False,
        "lambda_context": (0.00, 0.05), "proxy_weight": 0.64,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "0-3", "1-3", "2-2", "2-1", "1-0", "2-3"],
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
    polymarket = json.loads(POLYMARKET_PATH.read_text(encoding="utf-8"))
    weight_policy = MultiSourceWeightPolicy()
    polymarket_controls = weight_policy.controls("polymarket")
    for match in matches:
        code = match["code"]
        fallback_500 = "未开售" in match["market_1x2_source"]
        external_sources = []
        poly = polymarket.get("matches", {}).get(code)
        if poly:
            external_sources.append({
                "name": "polymarket",
                "probabilities": poly["normalized_probabilities"],
                "quality": min(1.0, poly["quality_weight"] / 0.30),
                "correlation_discount": float(polymarket_controls["correlation_discount"]),
                "apply_deviation_discount": bool(polymarket_controls["apply_deviation_discount"]),
                "source_type": "market",
                "metadata": {
                    "event_url": poly["event_url"], "liquidity": poly["liquidity"],
                    "volume": poly["volume"], "average_spread": poly["average_spread"],
                    "updated_at": poly["updated_at"],
                },
            })
        if external_sources:
            match["multi_source_result_fusion"] = {
                "base_weights": weight_policy.result_profile(official_500=not fallback_500),
                "fivehundred_quality": 1.0,
                "external_sources": external_sources,
                "gpt_direct_probability_weight": weight_policy.controls("gpt")["direct_probability_weight"],
            }
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260626-v1",
        "notes": [
            "500主表PDF与实时500网页均读取；056、057普通竞彩三向未开售，用500百家欧赔即时均值降权替代。",
            "API-Football fixture/predictions/odds/injuries/standings已读取；lineups/statistics未发布，正式首发仍不确定。",
            "Polymarket仅058、059匹配到完整三向市场并进入一次性多源融合；其他场外部市场仅作联网复核，不直接给概率权重。",
            "小组末轮积分、平即可、已锁头名、必须赢和已出局荣誉战均进入决策迭代层。",
            "GPT联网复核和奇门直接概率权重为0%。",
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
