from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260628")
MARKET_PATH = BASE / "market/latest_market.json"
POLYMARKET_PATH = BASE / "polymarket_snapshot.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周六067", "home": "克罗地亚", "away": "加纳", "home_en": "Croatia", "away_en": "Ghana",
        "kickoff": "2026-06-28T05:00:00+08:00", "fixture_id": 1489420, "venue": "Lincoln Financial Field, Philadelphia",
        "rank": (10, 74), "recent": ((2, 1, 1), (2, 1, 0)),
        "first_round": "L组末轮：英格兰、加纳同积4分，克罗地亚3分，巴拿马0分；克罗地亚必须赢更稳，加纳不败大概率晋级。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Philadelphia 17:00，23.6C、湿度86%、降水概率32%、阴、风速8.2km/h；开放球场，中性偏湿。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0；RotoWire/SportsMole赛前预测克罗地亚可能前场微调，Ghana以Partey/Williams/Semenyo反击为主要威胁。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["direct_qualification_battle", "underdog_draw_enough", "favorite_must_win", "top_table_stalemate_guard", "strong_defense_opponent"],
        "high_scoring_risk": 0.14, "volatility": 0.68, "favorite_cover_trigger": False,
        "lambda_context": (-0.04, -0.02), "proxy_weight": 0.64,
        "forced_scores": ["1-1", "1-0", "2-1", "2-0", "0-0", "0-1", "1-2", "2-2", "3-1"],
    },
    {
        "code": "周六068", "home": "巴拿马", "away": "英格兰", "home_en": "Panama", "away_en": "England",
        "kickoff": "2026-06-28T05:00:00+08:00", "fixture_id": 1489422, "venue": "MetLife Stadium, East Rutherford",
        "rank": (30, 4), "recent": ((2, 0, 2), (2, 1, 1)),
        "first_round": "L组末轮：巴拿马0分已淘汰；英格兰4分仍需结果锁定头名，需避免被Ghana/Croatia名次挤压。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "East Rutherford 17:00，22.4C、湿度82%、强毛毛雨、降水概率18%、风速2.9km/h；开放球场，湿滑但风小。",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "Guardian/AP确认Reece James因腿筋伤缺席，Livramento也缺；Panama训练中出现队内冲突但已淘汰、仍以纪律性低位防守为主。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["massive_favorite_depth", "favorite_win_needed_for_top", "eliminated_opponent_no_pressure", "compact_low_block", "favorite_cover_trigger"],
        "high_scoring_risk": 0.36, "volatility": 0.70, "favorite_cover_trigger": True,
        "lambda_context": (0.14, 0.04), "proxy_weight": 0.72,
        "forced_scores": ["0-2", "0-3", "0-1", "1-3", "0-4", "1-2", "1-1", "1-4", "2-3"],
    },
    {
        "code": "周六069", "home": "哥伦比亚", "away": "葡萄牙", "home_en": "Colombia", "away_en": "Portugal",
        "kickoff": "2026-06-28T07:30:00+08:00", "fixture_id": 1489419, "venue": "Hard Rock Stadium, Miami Gardens",
        "rank": (17, 5), "recent": ((2, 2, 0), (2, 1, 1)),
        "first_round": "K组末轮：哥伦比亚6分已出线且平即可头名；葡萄牙4分已出线，需赢球反超头名。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Miami Gardens 19:00，30.2C、湿度68%、天气代码雷暴但降水概率4%、风速10.9km/h；Hard Rock非全封闭，热湿仍保留。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点未完整落盘；SI/SportsMole称葡萄牙需赢争头名，哥伦比亚平即可头名，双方均已晋级。",
        "api_endpoint_status": {"predictions": 1, "injuries": "not_completed", "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["top_table_direct_rival", "home_draw_enough", "away_must_win_for_top", "heat_humidity", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.24, "volatility": 0.70, "favorite_cover_trigger": False,
        "lambda_context": (-0.02, 0.02), "proxy_weight": 0.66,
        "forced_scores": ["1-1", "1-2", "0-1", "2-2", "2-1", "0-0", "0-2", "1-0", "2-3"],
    },
    {
        "code": "周六070", "home": "刚果(金)", "away": "乌兹别克", "home_en": "DR Congo", "away_en": "Uzbekistan",
        "kickoff": "2026-06-28T07:30:00+08:00", "fixture_id": 1539013, "venue": "Mercedes-Benz Stadium, Atlanta",
        "rank": (61, 57), "recent": ((2, 1, 1), (2, 0, 7)),
        "first_round": "K组末轮：刚果(金)1分仍需赢球争最佳第三；乌兹别克0分且净胜球劣势大，基本为荣誉战。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Atlanta 19:00，32.0C、湿度48%、晴、风速16.0km/h；Mercedes-Benz可闭合顶棚+空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0；TalkSport称刚果(金)需赢争最佳第三，乌兹别克两连败后主要为荣誉战。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["must_chase_goal_difference", "eliminated_opponent_no_pressure", "favorite_cover_trigger", "home_attacking_need", "roof_weather_suppressed"],
        "high_scoring_risk": 0.34, "volatility": 0.74, "favorite_cover_trigger": True,
        "lambda_context": (0.16, 0.03), "proxy_weight": 0.70,
        "forced_scores": ["1-0", "2-0", "2-1", "3-0", "1-1", "3-1", "0-0", "0-1", "2-2"],
    },
    {
        "code": "周六071", "home": "阿尔及利亚", "away": "奥地利", "home_en": "Algeria", "away_en": "Austria",
        "kickoff": "2026-06-28T10:00:00+08:00", "fixture_id": 1489418, "venue": "Arrowhead Stadium, Kansas City",
        "rank": (36, 22), "recent": ((2, 1, 3), (2, 1, 3)),
        "first_round": "J组末轮：阿根廷6分锁头名，奥地利3分列第二、阿尔及利亚3分列第三；平局可能让双方各自保留路径，奥地利更受益。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Kansas City 21:00，25.3C、湿度78%、晴、阵风26.6km/h；开放球场，风对高球和定位球有轻微影响。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点未完整落盘；ESPN指出本场有1982 Gijon历史叙事，FIFA同组末轮同时开球正为降低默契球风险。",
        "api_endpoint_status": {"predictions": 1, "injuries": "not_completed", "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["balanced_direct_match", "draw_mutual_incentive", "top_table_stalemate_guard", "low_total_market", "strong_defense_opponent"],
        "high_scoring_risk": 0.06, "volatility": 0.56, "favorite_cover_trigger": False,
        "lambda_context": (-0.14, -0.08), "proxy_weight": 0.60,
        "forced_scores": ["1-1", "0-0", "0-1", "1-0", "0-2", "2-1", "1-2", "2-2"],
    },
    {
        "code": "周六072", "home": "约旦", "away": "阿根廷", "home_en": "Jordan", "away_en": "Argentina",
        "kickoff": "2026-06-28T10:00:00+08:00", "fixture_id": 1489421, "venue": "AT&T Stadium, Arlington",
        "rank": (63, 1), "recent": ((2, 1, 5), (2, 8, 1)),
        "first_round": "J组末轮：阿根廷6分已锁小组头名；约旦0分基本出局，目标为荣誉战和避免大败。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Arlington 21:00，30.6C、湿度51%、晴、阵风49.7km/h；AT&T可闭合顶棚+空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "The Sun/Times of India称阿根廷已锁头名，Messi预计替补，Scaloni会轮换但仍可能安排他后段保持节奏。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["massive_favorite_depth", "favorite_already_top_rotation", "eliminated_opponent_no_pressure", "favorite_cover_rotation_risk", "roof_weather_suppressed"],
        "high_scoring_risk": 0.34, "volatility": 0.78, "favorite_cover_trigger": False,
        "lambda_context": (-0.02, 0.10), "proxy_weight": 0.72,
        "forced_scores": ["0-2", "0-3", "0-1", "1-3", "0-4", "1-2", "1-1", "1-4", "2-3"],
    },
]


def enrich(meta: dict, market: dict) -> dict:
    current = market["current"]
    deep = market["deep_market"]
    one_x_two = current["one_x_two"] or {
        "3": deep["ouzhi"]["current"][0], "1": deep["ouzhi"]["current"][1], "0": deep["ouzhi"]["current"][2],
    }
    total = current["total_exact"]
    return {
        **meta,
        "market_1x2": (one_x_two["3"], one_x_two["1"], one_x_two["0"]),
        "handicap": current["handicap"],
        "handicap_3way": (current["handicap_three_way"]["3"], current["handicap_three_way"]["1"], current["handicap_three_way"]["0"]),
        "total_exact": tuple(total[str(index)] for index in range(7)) + (total["7"],),
        "score_prices": {label: price for label, price in current["scores"].items() if label[0].isdigit()},
        "market_total_line": deep["daxiao"]["current"][1],
        "asian_line": deep["yazhi"]["current"][1],
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    matches = [enrich(meta, latest[meta["code"]]) for meta in META]
    polymarket = json.loads(POLYMARKET_PATH.read_text(encoding="utf-8"))
    weight_policy = MultiSourceWeightPolicy()
    poly_controls = weight_policy.controls("polymarket")
    for match in matches:
        code = match["code"]
        fallback_500 = "未开售" in match["market_1x2_source"]
        poly = polymarket.get("matches", {}).get(code)
        if not poly:
            continue
        match["multi_source_result_fusion"] = {
            "base_weights": weight_policy.result_profile(official_500=not fallback_500),
            "fivehundred_quality": 1.0,
            "external_sources": [{
                "name": "polymarket",
                "probabilities": poly["normalized_probabilities"],
                "quality": min(1.0, poly["quality_weight"] / 0.30),
                "correlation_discount": float(poly_controls["correlation_discount"]),
                "apply_deviation_discount": bool(poly_controls["apply_deviation_discount"]),
                "source_type": "market",
                "metadata": {
                    "event_url": poly["event_url"],
                    "liquidity": poly["liquidity"],
                    "volume": poly["volume"],
                    "average_spread": poly["average_spread"],
                    "updated_at": poly["updated_at"],
                },
            }],
            "gpt_direct_probability_weight": weight_policy.controls("gpt")["direct_probability_weight"],
        }
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260628-v1",
        "notes": [
            "500 PDF和实时网页均读取；068、072普通竞彩三向未开售，用500百家即时均值降权替代。",
            "API-Football读取fixture/predictions/injuries/odds/standings，部分端点超时或返回0，已记录在meta。",
            "Polymarket完整三向匹配067、068、069、071、072；070未匹配，不直接入概率层。",
            "小组末轮积分、平即可、必须赢、已淘汰荣誉战、轮换、场馆顶棚和天气均进入决策迭代层。",
            "GPT联网复核只进入事实校验和权重修正，不给直接概率；奇门直接概率权重为0%。",
        ],
        "matches": [analyze_match(match, WorldCupTrainedModel()) for match in matches],
    }
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
