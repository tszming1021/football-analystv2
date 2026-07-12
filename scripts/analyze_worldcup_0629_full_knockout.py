from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260629_full")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周日073", "home": "南非", "away": "加拿大", "home_en": "South Africa", "away_en": "Canada",
        "kickoff": "2026-06-29T03:00:00+08:00", "fixture_id": 1561329, "venue": "SoFi Stadium, Inglewood",
        "rank": (57, 31), "recent": ((3, 3, 3), (3, 5, 4)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；加拿大市场升温，南非目标是拖入加时。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Inglewood 12:00，23.6C、湿度55%、局部多云、降水0%、风速8.1km/h；SoFi固定顶棚但侧面开放，天气影响降权。",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API确认加拿大I. Kone小腿骨折缺席；正式首发未发布。API prediction与500客胜热度分歧较大。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "favorite_win_not_depth", "plus_one_cover_risk", "organized_transition_underdog", "material_away_absence"],
        "high_scoring_risk": 0.20, "volatility": 0.70, "favorite_cover_trigger": False,
        "lambda_context": (-0.06, -0.03), "proxy_weight": 0.62,
        "forced_scores": ["0-1", "1-1", "0-2", "0-0", "1-2", "1-0", "2-1", "2-2", "0-3", "1-3"],
    },
    {
        "code": "周一074", "home": "巴西", "away": "日本", "home_en": "Brazil", "away_en": "Japan",
        "kickoff": "2026-06-30T01:00:00+08:00", "fixture_id": 1562344, "venue": "NRG Stadium, Houston",
        "rank": (5, 15), "recent": ((3, 5, 2), (3, 5, 4)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；巴西晋级优势高于90分钟穿盘优势。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Houston 12:00，33.9C、湿度52%、雷暴代码但降水1%；NRG可闭合顶棚+空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认巴西Raphinha腿筋伤缺席；正式首发未发布。API prediction提示巴西不败但90分钟平局权重高。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "favorite_win_not_depth", "low_block_opponent", "organized_transition_underdog", "material_home_absence"],
        "high_scoring_risk": 0.27, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (-0.04, -0.01), "proxy_weight": 0.66,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "3-0", "3-1", "0-0", "0-1", "1-2", "2-2"],
    },
    {
        "code": "周一075", "home": "德国", "away": "巴拉圭", "home_en": "Germany", "away_en": "Paraguay",
        "kickoff": "2026-06-30T04:30:00+08:00", "fixture_id": 1565176, "venue": "Gillette Stadium, Foxborough",
        "rank": (10, 53), "recent": ((3, 10, 4), (3, 2, 6)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；德国实力和深度优势明显，但后防伤停降低零封稳定性。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Foxborough 16:00，28.1C、湿度43%、大部晴、降水1%、风速5.0km/h；开放球场，天气中性。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认德国N. Brown内收肌伤、N. Schlotterbeck韧带伤缺席；巴拉圭D. Gomez黄牌停赛。正式首发未发布。",
        "api_endpoint_status": {"predictions": 1, "injuries": 3, "lineups": "timeout", "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "material_home_absence", "defensive_collapse_risk"],
        "high_scoring_risk": 0.42, "volatility": 0.70, "favorite_cover_trigger": True,
        "lambda_context": (0.15, 0.05), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "2-1", "3-1", "1-0", "4-0", "4-1", "1-1", "0-0", "1-2"],
    },
    {
        "code": "周一076", "home": "荷兰", "away": "摩洛哥", "home_en": "Netherlands", "away_en": "Morocco",
        "kickoff": "2026-06-30T09:00:00+08:00", "fixture_id": 1562345, "venue": "Estadio BBVA, Monterrey",
        "rank": (7, 14), "recent": ((3, 6, 2), (3, 4, 2)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；双方排名接近，摩洛哥防守韧性使加时路径权重上升。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Monterrey 19:00，31.3C、湿度41%、晴、风速29.9km/h、阵风60.8km/h；开放球场，强风压低连续进攻稳定性。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。市场为荷兰小优，但让球明显保护摩洛哥+1。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.12, "volatility": 0.62, "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.07), "proxy_weight": 0.62,
        "forced_scores": ["1-1", "1-0", "0-0", "0-1", "2-1", "1-2", "2-0", "0-2", "2-2", "3-1"],
    },
    {
        "code": "周二077", "home": "科特迪瓦", "away": "挪威", "home_en": "Ivory Coast", "away_en": "Norway",
        "kickoff": "2026-07-01T01:00:00+08:00", "fixture_id": 1564789, "venue": "Dallas Stadium / AT&T Stadium",
        "rank": (53, 43), "recent": ((3, 4, 4), (3, 6, 5)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；挪威名气与锋线更热，但科特迪瓦身体对抗和受让保护很强。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Arlington 12:00，33.1C、湿度39%、晴、风速18.1km/h；AT&T可闭合顶棚+空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction反而给科特迪瓦不败，和500挪威小热存在分歧。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "plus_one_cover_risk", "set_piece_underdog_threat", "favorite_win_not_depth", "open_league_high_variance"],
        "high_scoring_risk": 0.28, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (-0.02, 0.02), "proxy_weight": 0.64,
        "forced_scores": ["1-1", "0-1", "1-2", "2-2", "1-0", "0-0", "0-2", "2-1", "0-3", "2-3"],
    },
    {
        "code": "周二078", "home": "法国", "away": "瑞典", "home_en": "France", "away_en": "Sweden",
        "kickoff": "2026-07-01T05:00:00+08:00", "fixture_id": 1565177, "venue": "MetLife Stadium, East Rutherford",
        "rank": (2, 27), "recent": ((3, 9, 2), (3, 6, 4)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；法国强度最高，市场升至深盘，但瑞典锋线反击需防不零封。",
        "market_1x2_source": "500竞彩官方",
        "weather": "East Rutherford 17:00，30.1C、湿度56%、阴、降水6%、风速5.7km/h；开放球场，天气中性偏热。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。FIFA确认比赛在New York/New Jersey Stadium，法国小组赛进攻火力强。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "defensive_collapse_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.48, "volatility": 0.72, "favorite_cover_trigger": True,
        "lambda_context": (0.20, 0.06), "proxy_weight": 0.74,
        "forced_scores": ["2-0", "3-0", "3-1", "2-1", "4-0", "4-1", "1-0", "1-1", "2-2", "1-2"],
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
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-knockout-90min-20260629-full-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "晋级概率不进入胜平负概率；90分钟平局代表进入加时/点球路径。",
            "500 PDF和实时网页均读取；本轮073-078共6场。",
            "正式首发均未发布；API injuries和联网复核只作为事实修正。",
            "GPT联网复核只进入事实层，直接概率权重0%。",
        ],
        "matches": [analyze_match(enrich(meta, latest[meta["code"]]), WorldCupTrainedModel()) for meta in META],
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
