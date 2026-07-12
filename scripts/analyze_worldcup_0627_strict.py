from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260627")
MARKET_PATH = BASE / "market/latest_market.json"
POLYMARKET_PATH = BASE / "polymarket_snapshot.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周五061", "home": "挪威", "away": "法国", "home_en": "Norway", "away_en": "France",
        "kickoff": "2026-06-27T03:00:00+08:00", "fixture_id": 1489416, "venue": "Gillette Stadium, Boston",
        "rank": (33, 2), "recent": ((2, 7, 3), (2, 6, 1)),
        "first_round": "I组：法国6分/+5，挪威6分/+4，双方已锁前二；法国平局即可头名，挪威需赢争头名。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Boston 15:00，24.0C、湿度75%、降水3%、少云、风速12.6km/h；开放球场，天气影响中低",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停端点SSL失败；联网复核聚焦Haaland与Mbappe均状态火热，正式首发未发布。",
        "api_endpoint_status": {"predictions": 1, "injuries": "ssl_failed", "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["top_table_direct_rival", "favorite_draw_enough", "favorite_conservative_qualification_path", "set_piece_underdog_threat", "favorite_win_not_clean_sheet", "open_league_high_variance"],
        "high_scoring_risk": 0.38, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (0.08, 0.04), "proxy_weight": 0.62,
        "forced_scores": ["1-2", "1-1", "0-2", "2-2", "2-1", "0-1", "1-3", "2-3", "3-2", "0-3"],
    },
    {
        "code": "周五062", "home": "塞内加尔", "away": "伊拉克", "home_en": "Senegal", "away_en": "Iraq",
        "kickoff": "2026-06-27T03:00:00+08:00", "fixture_id": 1539074, "venue": "BMO Field, Toronto",
        "rank": (18, 58), "recent": ((2, 3, 6), (2, 1, 7)),
        "first_round": "I组：塞内加尔0分/-3，伊拉克0分/-6；两队已无前二路径，塞内加尔需大胜争最佳第三理论机会。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Toronto 15:00，19.3C、湿度87%、降水1%、阴、风速12.2km/h；湿度偏高但温度舒适",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认塞内加尔门将E. Mendy膝伤缺席；Guardian提到塞内加尔内部管理和选人压力巨大。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["massive_favorite_depth", "must_chase_goal_difference", "eliminated_opponent_no_pressure", "favorite_win_not_clean_sheet", "favorite_rotation_risk"],
        "high_scoring_risk": 0.44, "volatility": 0.78, "favorite_cover_trigger": True,
        "lambda_context": (0.24, -0.05), "proxy_weight": 0.70,
        "forced_scores": ["2-0", "3-0", "3-1", "4-0", "4-1", "2-1", "1-0", "1-1", "2-2", "5-1"],
    },
    {
        "code": "周五063", "home": "佛得角", "away": "沙特阿拉伯", "home_en": "Cape Verde", "away_en": "Saudi Arabia",
        "kickoff": "2026-06-27T08:00:00+08:00", "fixture_id": 1489413, "venue": "NRG Stadium, Houston",
        "rank": (71, 59), "recent": ((2, 2, 2), (2, 1, 5)),
        "first_round": "H组：佛得角2分/0，沙特1分/-4；佛得角赢球大概率晋级，沙特必须赢并看另一场。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Houston 19:00，30.8C、湿度56%、雷暴代码95、风速19.2km/h；NRG Stadium可闭合顶棚并具备现代HVAC，若顶棚关闭，降水/雷暴对场内节奏影响大幅降权",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认佛得角S. Lopes Cabral黄牌停赛；Climate Central提示本场高概率出现影响表现的热负荷。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["balanced_direct_match", "underdog_must_win", "opponent_must_win", "plus_one_cover_risk", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.16, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (-0.01, 0.00), "proxy_weight": 0.62,
        "forced_scores": ["1-1", "1-0", "0-1", "2-1", "1-2", "0-0", "2-2", "2-0", "0-2"],
    },
    {
        "code": "周五064", "home": "乌拉圭", "away": "西班牙", "home_en": "Uruguay", "away_en": "Spain",
        "kickoff": "2026-06-27T08:00:00+08:00", "fixture_id": 1489417, "venue": "Estadio Akron, Zapopan",
        "rank": (14, 1), "recent": ((2, 3, 3), (2, 4, 0)),
        "first_round": "H组：西班牙4分/+4，乌拉圭2分/0；西班牙不败基本头名，乌拉圭需要抢分确保晋级。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Zapopan 18:00，18.9C、湿度85%、降水98%、雷暴代码95、风速13.1km/h；雨战/雷暴显著压低传控稳定性",
        "weather_suppression": True, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认乌拉圭G. de Arrascaeta、R. Araujo肌肉挫伤缺席；Al Jazeera/媒体称西班牙伤停较少。",
        "api_endpoint_status": {"predictions": 1, "injuries": 2, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["favorite_draw_enough", "favorite_conservative_qualification_path", "underdog_must_win", "opponent_must_win", "weather_suppression", "material_home_absence", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.20, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (-0.08, -0.04), "proxy_weight": 0.64,
        "forced_scores": ["0-1", "0-2", "1-1", "1-2", "0-0", "0-3", "1-3", "2-1", "2-2"],
    },
    {
        "code": "周五065", "home": "埃及", "away": "伊朗", "home_en": "Egypt", "away_en": "Iran",
        "kickoff": "2026-06-27T11:00:00+08:00", "fixture_id": 1489414, "venue": "Lumen Field, Seattle",
        "rank": (32, 20), "recent": ((2, 4, 2), (2, 2, 2)),
        "first_round": "G组：埃及4分/+2，伊朗2分/0；埃及不败晋级，伊朗取胜可反超并锁定晋级。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Seattle 20:00，16.9C、湿度67%、降水15%、晴、风速18.3km/h；环境稳定",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认埃及Hossam Abdelmaguid停赛；RacingPost称Hamdy Fathy腿筋伤缺，Egypt/Iran场外Pride Match舆论升温但教练强调专注比赛。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": True, "stage": "group", "round_index": 3,
        "tags": ["favorite_draw_enough", "favorite_conservative_qualification_path", "underdog_must_win", "opponent_must_win", "top_table_direct_rival", "strong_defense_opponent"],
        "high_scoring_risk": 0.08, "volatility": 0.58, "favorite_cover_trigger": False,
        "lambda_context": (-0.08, -0.02), "proxy_weight": 0.60,
        "forced_scores": ["1-1", "1-0", "0-0", "0-1", "2-1", "1-2", "2-0", "2-2"],
    },
    {
        "code": "周五066", "home": "新西兰", "away": "比利时", "home_en": "New Zealand", "away_en": "Belgium",
        "kickoff": "2026-06-27T11:00:00+08:00", "fixture_id": 1489415, "venue": "BC Place, Vancouver",
        "rank": (89, 8), "recent": ((2, 3, 5), (2, 1, 1)),
        "first_round": "G组：比利时2分/0，新西兰1分/-2；比利时必须赢才稳，新西兰也需要胜利才有生路。",
        "market_1x2_source": "500百家即时均值（竞彩普通三向未开售）",
        "weather": "Vancouver 20:00，16.4C、湿度71%、降水18%、阴、风速15.3km/h；BC Place可闭合顶棚，天气影响低",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API确认比利时Z. Debast腿伤、J. Doku illness、N. Ngoy红牌停赛；Belgium两连平但必须赢。",
        "api_endpoint_status": {"predictions": 1, "injuries": 3, "lineups": 0, "statistics": 0},
        "group_direct_rivalry": False, "stage": "group", "round_index": 3,
        "tags": ["massive_favorite_depth", "must_chase_goal_difference", "favorite_win_not_clean_sheet", "material_away_absence", "underdog_must_win", "opponent_must_win", "home_defensive_leak"],
        "high_scoring_risk": 0.42, "volatility": 0.78, "favorite_cover_trigger": True,
        "lambda_context": (0.02, 0.18), "proxy_weight": 0.70,
        "forced_scores": ["0-2", "0-3", "1-3", "0-4", "1-2", "1-4", "0-1", "1-1", "2-2", "2-3", "2-4"],
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
        "model_version": "worldcup-strict-20260627-v1",
        "notes": [
            "500 PDF和实时网页均读取；062、066普通竞彩三向未开售，用500百家即时均值降权替代。",
            "API-Football读取fixture/predictions/injuries/odds/standings；061 injuries和066 fixture存在SSL失败，已记录并使用替代来源。",
            "Polymarket仅061、062、066完整匹配并进入一次性多源融合；063、064、065未完整匹配，不直接入概率层。",
            "小组末轮积分、平即可、必须赢、已淘汰荣誉战、场馆天气和伤停均进入决策迭代层。",
            "GPT联网复核和奇门直接概率权重为0%。",
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
