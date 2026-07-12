from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match
from scripts.analyze_worldcup_0629_nine_knockout import META as PREVIOUS_META


BASE = Path("data/worldcup_20260630_nine")
MARKET_PATH = BASE / "market/latest_market.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
OUT_PATH = BASE / "model_analysis.json"


def endpoint_status(code: str) -> dict:
    audit = json.loads(API_AUDIT_PATH.read_text(encoding="utf-8"))
    endpoints = audit["fixtures"][code]["endpoints"]
    status = {}
    for name, payload in endpoints.items():
        if "exception" in payload:
            status[name] = payload["exception"]
        else:
            status[name] = payload.get("results", 0)
    return status


def previous(code: str) -> dict:
    return deepcopy(next(item for item in PREVIOUS_META if item["code"] == code))


def with_updates(code: str, **updates) -> dict:
    item = previous(code)
    item.update(updates)
    item["api_endpoint_status"] = endpoint_status(code)
    return item


META = [
    with_updates(
        "周二077",
        recent=((3, 4, 2), (3, 8, 7)),
        venue="AT&T Stadium, Dallas",
        weather="Dallas午间室外约32-34C；AT&T Stadium可闭合顶棚并有空调，高温影响降至低权重。",
        weather_suppression=False,
        absence_note="API伤停0，正式首发未发布。API prediction给科特迪瓦不败，500三向挪威小热但让球端强保护科特迪瓦+1。",
        high_scoring_risk=0.30,
        lambda_context=(-0.01, 0.03),
    ),
    with_updates(
        "周二078",
        recent=((3, 10, 2), (3, 7, 7)),
        weather="East Rutherford下午有高温风险；MetLife开放球场，热负荷会压低连续冲刺，但法国前场质量仍支撑高上沿。",
        weather_suppression=True,
        absence_note="API伤停0，正式首发未发布。API prediction支持法国不败并倾向法国胜+1.5球以上。",
        high_scoring_risk=0.50,
        lambda_context=(0.18, 0.04),
    ),
    with_updates(
        "周二079",
        recent=((3, 6, 0), (3, 2, 2)),
        absence_note="API伤停0，正式首发未发布。API prediction给墨西哥不败且小于3.5球，500让球端继续强保护厄瓜多尔+1。",
        high_scoring_risk=0.05,
        lambda_context=(-0.15, -0.10),
    ),
    with_updates(
        "周三080",
        recent=((3, 6, 2), (3, 4, 3)),
        absence_note="API确认英格兰R. James腿筋伤缺席；正式首发未发布。API prediction给英格兰不败。",
        high_scoring_risk=0.32,
        lambda_context=(0.08, -0.04),
    ),
    with_updates(
        "周三081",
        recent=((3, 6, 2), (3, 8, 6)),
        absence_note="API确认比利时Z. Debast伤缺、塞内加尔É. Mendy膝伤；正式首发未发布。API prediction给比利时不败，但500让球端强保护塞内加尔+1。",
        high_scoring_risk=0.18,
        lambda_context=(-0.08, -0.03),
    ),
    with_updates(
        "周三082",
        recent=((3, 8, 4), (3, 5, 6)),
        absence_note="API确认美国C. Roldan肌肉挫伤；正式首发未发布。API prediction支持美国胜+1.5球以上。",
        high_scoring_risk=0.34,
        lambda_context=(0.08, -0.02),
    ),
    {
        "code": "周四083", "home": "西班牙", "away": "奥地利", "home_en": "Spain", "away_en": "Austria",
        "kickoff": "2026-07-03T03:00:00+08:00", "fixture_id": 1567311, "venue": "SoFi Stadium, Los Angeles",
        "rank": (3, 22), "recent": ((3, 5, 0), (3, 6, 6)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；西班牙控球和防守稳定性明显占优，奥地利进攻效率不低但防线波动大。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Los Angeles室内/半室内SoFi环境影响低，天气变量降权。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给西班牙不败，500三向与欧赔均值均强支持西班牙。",
        "api_endpoint_status": endpoint_status("周四083"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "low_block_opponent"],
        "high_scoring_risk": 0.34, "volatility": 0.64, "favorite_cover_trigger": True,
        "lambda_context": (0.10, -0.02), "proxy_weight": 0.72,
        "forced_scores": ["2-0", "1-0", "2-1", "3-0", "3-1", "4-0", "1-1", "0-0"],
    },
    {
        "code": "周四084", "home": "葡萄牙", "away": "克罗地亚", "home_en": "Portugal", "away_en": "Croatia",
        "kickoff": "2026-07-03T07:00:00+08:00", "fixture_id": 1567309, "venue": "BMO Field, Toronto",
        "rank": (6, 13), "recent": ((3, 6, 1), (3, 5, 5)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；葡萄牙胜面更高，但克罗地亚经验、控节奏和受让价值明显。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Toronto傍晚有高温和雷暴风险；BMO Field开放球场，湿热和阵雨信号提高90分钟卡线/降速概率。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给葡萄牙不败，500让球端强保护克罗地亚+1。",
        "api_endpoint_status": endpoint_status("周四084"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "strong_defense_opponent", "plus_one_cover_risk", "weather_suppression", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.16, "volatility": 0.64, "favorite_cover_trigger": False,
        "lambda_context": (-0.07, -0.03), "proxy_weight": 0.66,
        "forced_scores": ["1-0", "1-1", "2-1", "2-0", "0-0", "0-1", "1-2", "2-2", "3-1"],
    },
    {
        "code": "周四085", "home": "瑞士", "away": "阿尔及利亚", "home_en": "Switzerland", "away_en": "Algeria",
        "kickoff": "2026-07-03T11:00:00+08:00", "fixture_id": 1567312, "venue": "BC Place, Vancouver",
        "rank": (20, 37), "recent": ((3, 7, 3), (3, 5, 7)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；瑞士整体更稳，但阿尔及利亚反击和受让保护使深追风险高。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Vancouver晚间温和；BC Place可闭合顶棚，天气变量低。",
        "weather_suppression": False, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给瑞士不败并偏向+1.5球以上，500让球端保护阿尔及利亚+1。",
        "api_endpoint_status": endpoint_status("周四085"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "plus_one_cover_risk", "organized_transition_underdog"],
        "high_scoring_risk": 0.24, "volatility": 0.68, "favorite_cover_trigger": False,
        "lambda_context": (0.00, 0.01), "proxy_weight": 0.66,
        "forced_scores": ["1-1", "1-0", "2-1", "0-1", "2-2", "2-0", "1-2", "3-1"],
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
        "model_version": "worldcup-knockout-90min-20260630-nine-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "500 PDF和实时网页均读取；本轮当前PDF共9场：周二077至周四085。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds均已请求；正式首发均未发布。",
            "GPT/联网复核只进入事实层，直接概率权重0%。",
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
