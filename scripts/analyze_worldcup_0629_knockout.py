from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260629")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"

META = [
    {
        "code": "周日073", "home": "南非", "away": "加拿大", "home_en": "South Africa", "away_en": "Canada",
        "kickoff": "2026-06-29T03:00:00+08:00", "fixture_id": 1561329, "venue": "SoFi Stadium, Inglewood",
        "rank": (57, 31), "recent": ((3, 3, 3), (3, 5, 4)),
        "first_round": "淘汰赛32强，所有胜平负和比分均按90分钟计算；平局进入加时/点球，不等于晋级结果。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Inglewood 12:00，22.5C、湿度57%、晴、降水0%、风速13.0km/h；SoFi固定顶棚但侧面开放，降水/直晒影响降权。",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API确认加拿大I. Koné小腿骨折缺席；正式首发未发布。API prediction给南非不败35/35/30，与500客胜市场存在明显分歧。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "favorite_win_not_depth", "organized_transition_underdog", "plus_one_cover_risk", "material_away_absence"],
        "high_scoring_risk": 0.18, "volatility": 0.68, "favorite_cover_trigger": False,
        "lambda_context": (-0.07, -0.04), "proxy_weight": 0.62,
        "forced_scores": ["0-1", "1-1", "0-0", "0-2", "1-2", "1-0", "2-1", "2-2", "0-3", "1-3"],
    },
    {
        "code": "周一074", "home": "巴西", "away": "日本", "home_en": "Brazil", "away_en": "Japan",
        "kickoff": "2026-06-30T01:00:00+08:00", "fixture_id": 1562344, "venue": "Houston Stadium / NRG Stadium",
        "rank": (5, 15), "recent": ((3, 5, 2), (3, 5, 4)),
        "first_round": "淘汰赛32强，90分钟胜平负；巴西晋级优势不等同于90分钟大胜，日本抗压和反击需保留。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Houston 12:00，33.8C、湿度48%、晴、降水0%、风速16.5km/h；NRG可闭顶空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认巴西Raphinha腿筋伤缺席；正式首发未发布。API prediction给巴西不败45/45/10，提示90分钟平局权重高。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "favorite_win_not_depth", "organized_transition_underdog", "low_block_opponent", "material_home_absence", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.24, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (-0.06, -0.02), "proxy_weight": 0.66,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "0-0", "0-1", "1-2", "2-2", "3-0", "3-1"],
    },
    {
        "code": "周一076", "home": "荷兰", "away": "摩洛哥", "home_en": "Netherlands", "away_en": "Morocco",
        "kickoff": "2026-06-30T09:00:00+08:00", "fixture_id": 1562345, "venue": "Monterrey Stadium / Estadio BBVA",
        "rank": (7, 14), "recent": ((3, 6, 2), (3, 4, 2)),
        "first_round": "淘汰赛32强，90分钟胜平负；双方排名接近，摩洛哥防守韧性使加时路径权重上升。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Monterrey 19:00，33.0C、湿度36%、晴、降水1%、风速30.9km/h、阵风47.5km/h；开放球场，风和热会压低连续进攻稳定性。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给荷兰不败45/45/10，市场则为荷兰小优但让球明显保护摩洛哥+1。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.12, "volatility": 0.62, "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.07), "proxy_weight": 0.62,
        "forced_scores": ["1-1", "1-0", "0-0", "0-1", "2-1", "1-2", "2-0", "0-2", "2-2", "3-1"],
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
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-knockout-90min-20260629-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "晋级概率不进入胜平负概率；90分钟平局代表进入加时/点球路径。",
            "Polymarket三场未匹配完整市场，不入概率层。",
            "正式首发均未发布；API injuries和联网复核只作为事实修正。",
            "GPT联网复核只进入事实层，直接概率权重0%。",
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
