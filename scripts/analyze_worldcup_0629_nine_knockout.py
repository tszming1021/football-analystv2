from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260629_nine")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"


META = [
    {
        "code": "周一074", "home": "巴西", "away": "日本", "home_en": "Brazil", "away_en": "Japan",
        "kickoff": "2026-06-30T01:00:00+08:00", "fixture_id": 1562344, "venue": "NRG Stadium, Houston",
        "rank": (5, 15), "recent": ((3, 5, 2), (3, 5, 4)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；巴西实力上限明确，但日本的组织纪律把穿盘赔率压低。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Houston中午约31C、局部晴；NRG Stadium可闭合顶棚并有空调，降雨和雷暴影响降至低权重。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认巴西Raphinha腿筋伤缺席；正式首发未发布。API prediction给巴西不败，但90分钟平局权重不低。",
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
        "first_round": "Round of 32淘汰赛，90分钟胜平负；德国实力和阵容厚度优势明显，后防伤停使零封稳定性下降。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Foxborough下午约30C以内、晴到少云；Gillette开放球场，天气中性偏热。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认德国N. Brown内收肌伤、N. Schlotterbeck韧带伤缺席；巴拉圭D. Gomez黄牌停赛。正式首发未发布。",
        "api_endpoint_status": {"predictions": 1, "injuries": 3, "lineups": 0, "statistics": 0, "odds": 1},
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
        "first_round": "Round of 32淘汰赛，90分钟胜平负；双方排名接近，摩洛哥防守韧性使90分钟不败路径上升。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Monterrey晚间约31C，赛前后有雷暴信号；Estadio BBVA开放球场，湿热和阵风压低连续进攻质量。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。市场为荷兰小优，但让球端明显保护摩洛哥+1。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.12, "volatility": 0.62, "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.07), "proxy_weight": 0.62,
        "forced_scores": ["1-1", "1-0", "0-0", "0-1", "2-1", "1-2", "2-0", "0-2", "2-2", "3-1"],
    },
    {
        "code": "周二077", "home": "科特迪瓦", "away": "挪威", "home_en": "Ivory Coast", "away_en": "Norway",
        "kickoff": "2026-07-01T01:00:00+08:00", "fixture_id": 1564789, "venue": "AT&T Stadium, Arlington",
        "rank": (53, 43), "recent": ((3, 4, 4), (3, 6, 5)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；挪威锋线更热，科特迪瓦身体对抗和受让保护强。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Arlington中午室外高温约33C以上；AT&T Stadium可闭合顶棚并有空调，天气影响大幅降权。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给科特迪瓦不败，和500挪威小热存在分歧。",
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
        "first_round": "Round of 32淘汰赛，90分钟胜平负；法国强度最高，市场升至深盘，瑞典反击需要防丢球。",
        "market_1x2_source": "500竞彩官方",
        "weather": "East Rutherford下午约29C、晴到少云；MetLife开放球场，天气中性偏热。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停接口本次SSL失败，预测和赔率接口正常；正式首发未发布。",
        "api_endpoint_status": {"predictions": 1, "injuries": "ssl_retry_failed", "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "defensive_collapse_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.48, "volatility": 0.72, "favorite_cover_trigger": True,
        "lambda_context": (0.20, 0.06), "proxy_weight": 0.74,
        "forced_scores": ["2-0", "3-0", "3-1", "2-1", "4-0", "4-1", "1-0", "1-1", "2-2", "1-2"],
    },
    {
        "code": "周二079", "home": "墨西哥", "away": "厄瓜多尔", "home_en": "Mexico", "away_en": "Ecuador",
        "kickoff": "2026-07-01T09:00:00+08:00", "fixture_id": 1567306, "venue": "Estadio Banorte, Mexico City",
        "rank": (19, 24), "recent": ((3, 4, 2), (3, 4, 3)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；双方实力接近，Mexico City高海拔强化主场适应优势但也压低节奏。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Mexico City晚间约17C、有阵雨信号；Estadio Banorte开放球场，高海拔和湿滑草皮共同压低总进球。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给墨西哥不败且小球，500让球端保护厄瓜多尔+1。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.06, "volatility": 0.60, "favorite_cover_trigger": False,
        "lambda_context": (-0.14, -0.08), "proxy_weight": 0.62,
        "forced_scores": ["1-0", "1-1", "0-0", "0-1", "2-0", "2-1", "1-2", "2-2"],
    },
    {
        "code": "周三080", "home": "英格兰", "away": "刚果(金)", "home_en": "England", "away_en": "Congo DR",
        "kickoff": "2026-07-02T00:00:00+08:00", "fixture_id": 1567307, "venue": "Mercedes-Benz Stadium, Atlanta",
        "rank": (4, 61), "recent": ((3, 7, 2), (3, 3, 5)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；英格兰阵容厚度优势极大，刚果(金)主要威胁来自身体对抗和定位球。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Atlanta中午室外约32C；Mercedes-Benz Stadium可闭合顶棚并有空调，天气对比赛节奏影响降至低权重。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认英格兰R. James腿筋伤缺席；prediction接口本次SSL失败，赔率和伤停接口正常。",
        "api_endpoint_status": {"predictions": "ssl_retry_failed", "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "low_block_opponent", "material_home_absence"],
        "high_scoring_risk": 0.34, "volatility": 0.66, "favorite_cover_trigger": True,
        "lambda_context": (0.10, -0.04), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "1-0", "2-1", "3-1", "4-0", "1-1", "0-0"],
    },
    {
        "code": "周三081", "home": "比利时", "away": "塞内加尔", "home_en": "Belgium", "away_en": "Senegal",
        "kickoff": "2026-07-02T04:00:00+08:00", "fixture_id": 1567308, "venue": "Lumen Field, Seattle",
        "rank": (8, 17), "recent": ((3, 6, 4), (3, 4, 2)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；比利时名气和控球更强，塞内加尔防线和转换速度使受让价值更高。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Seattle午后约16C、阴到多云；Lumen Field开放球场，低温和草皮节奏利于防守端。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给比利时不败，500让球端强保护塞内加尔+1。",
        "api_endpoint_status": {"predictions": 1, "injuries": 0, "lineups": "ssl_retry_failed", "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.12, "volatility": 0.62, "favorite_cover_trigger": False,
        "lambda_context": (-0.10, -0.06), "proxy_weight": 0.62,
        "forced_scores": ["1-1", "1-0", "0-1", "0-0", "2-1", "1-2", "2-2", "2-0"],
    },
    {
        "code": "周三082", "home": "美国", "away": "波黑", "home_en": "USA", "away_en": "Bosnia & Herzegovina",
        "kickoff": "2026-07-02T08:00:00+08:00", "fixture_id": 1562586, "venue": "Levi's Stadium / San Francisco Bay Area Stadium, Santa Clara",
        "rank": (16, 74), "recent": ((3, 8, 4), (3, 2, 5)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；美国主场和体能路线优势明显，波黑第三名晋级后更重视低位防守。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Santa Clara傍晚约24C、晴；Levi's Stadium开放球场，天气稳定，主场氛围权重高于天气权重。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API确认美国C. Roldan肌肉挫伤；正式首发未发布。FIFA/US Soccer确认比赛在Santa Clara举行。",
        "api_endpoint_status": {"predictions": 1, "injuries": 1, "lineups": 0, "statistics": 0, "odds": 1},
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "host_depth", "favorite_win_not_clean_sheet", "low_block_opponent"],
        "high_scoring_risk": 0.30, "volatility": 0.64, "favorite_cover_trigger": True,
        "lambda_context": (0.08, -0.03), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "1-0", "2-1", "3-0", "1-1", "3-1", "0-0"],
    },
]


def enrich(meta: dict, market: dict) -> dict:
    current = market["current"]
    deep = market["deep_market"]
    one_x_two = current["one_x_two"] or {
        "3": deep["ouzhi"]["current"][0],
        "1": deep["ouzhi"]["current"][1],
        "0": deep["ouzhi"]["current"][2],
    }
    total = current["total_exact"]
    return {
        **meta,
        "market_1x2": (one_x_two["3"], one_x_two["1"], one_x_two["0"]),
        "handicap": current["handicap"],
        "handicap_3way": (
            current["handicap_three_way"]["3"],
            current["handicap_three_way"]["1"],
            current["handicap_three_way"]["0"],
        ),
        "total_exact": tuple(total[str(index)] for index in range(7)) + (total["7"],),
        "score_prices": {label: price for label, price in current["scores"].items() if label[0].isdigit()},
        "market_total_line": deep["daxiao"]["current"][1],
        "asian_line": deep["yazhi"]["current"][1],
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    model = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-knockout-90min-20260629-nine-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "晋级概率不进入胜平负概率；90分钟平局代表进入加时/点球路径。",
            "500 PDF和实时网页均读取；本轮当前PDF共9场：周一074至周三082。",
            "正式首发均未发布；API injuries和联网复核只作为事实修正。",
            "GPT联网复核只进入事实层，直接概率权重0%。",
        ],
        "matches": [analyze_match(enrich(meta, latest[meta["code"]]), model) for meta in META],
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "summary": [{
            "code": item["identity"]["code"],
            "fixture": f"{item['identity']['home']}vs{item['identity']['away']}",
            "result": item["final"]["result"],
            "handicap": item["final"]["handicap_home_settlement"],
            "mean": item["means"]["decision_final"],
            "scores": [score["score"] for score in item["final"]["scorelines"][:5]],
            "rules": item["decision_iteration"]["applied_rules"],
            "consistency": item["consistency"]["status"],
        } for item in output["matches"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
