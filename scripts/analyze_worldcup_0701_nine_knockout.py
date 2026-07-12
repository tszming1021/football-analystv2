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
from scripts.analyze_worldcup_0630_nine_knockout import META as PREVIOUS_META


BASE = Path("data/worldcup_20260701_nine")
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
        "周三080",
        recent=((3, 6, 2), (3, 4, 3)),
        absence_note="API确认英格兰R. James伤缺；Sky/ESPN赛前报道同时确认J. Quansah缺席。正式首发未发布。API prediction给英格兰不败，500三向和欧赔均值强支持英格兰。",
        high_scoring_risk=0.32,
        lambda_context=(0.08, -0.04),
    ),
    with_updates(
        "周三081",
        recent=((3, 6, 2), (3, 8, 6)),
        absence_note="API确认比利时Z. Debast伤缺、塞内加尔É. Mendy伤缺；正式首发未发布。API prediction给比利时不败，但500让球端强保护塞内加尔+1。",
        high_scoring_risk=0.18,
        lambda_context=(-0.08, -0.03),
    ),
    with_updates(
        "周三082",
        recent=((3, 8, 4), (3, 5, 6)),
        absence_note="API确认美国C. Roldan伤缺；正式首发未发布。API prediction支持美国胜+1.5球以上。",
        high_scoring_risk=0.34,
        lambda_context=(0.08, -0.02),
    ),
    with_updates(
        "周四083",
        recent=((3, 5, 0), (3, 6, 6)),
        absence_note="API伤停0，正式首发未发布。API prediction给西班牙不败，500三向与欧赔均值均强支持西班牙。",
        high_scoring_risk=0.34,
        lambda_context=(0.10, -0.02),
    ),
    with_updates(
        "周四084",
        recent=((3, 6, 1), (3, 5, 5)),
        absence_note="API伤停0，正式首发未发布。API prediction给葡萄牙不败，500让球端强保护克罗地亚+1。",
        high_scoring_risk=0.16,
        lambda_context=(-0.07, -0.03),
    ),
    with_updates(
        "周四085",
        recent=((3, 7, 3), (3, 5, 7)),
        absence_note="API伤停0，正式首发未发布。API prediction给瑞士不败并偏向+1.5球以上，500让球端保护阿尔及利亚+1。",
        high_scoring_risk=0.24,
        lambda_context=(0.00, 0.01),
    ),
    {
        "code": "周五086", "home": "澳大利亚", "away": "埃及", "home_en": "Australia", "away_en": "Egypt",
        "kickoff": "2026-07-04T02:00:00+08:00", "fixture_id": 1565178, "venue": "AT&T Stadium, Dallas",
        "rank": (26, 33), "recent": ((3, 2, 2), (3, 5, 3)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；埃及个体进攻更有热度，但澳大利亚防守、身体对抗和+1保护明显。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Dallas午后室外高温；AT&T Stadium可闭合顶棚并有空调，天气影响降至低权重。",
        "weather_suppression": False, "material_absence_team": "away", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布；CAF/FIFA与澳媒赛前报道显示埃及队长Mohamed Salah及多名球员存在伤情观察/出场疑云。API prediction给澳大利亚不败且小于3.5球，和500埃及小热形成分歧。",
        "api_endpoint_status": endpoint_status("周五086"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "balanced_direct_match", "plus_one_cover_risk", "organized_transition_underdog", "top_table_stalemate_guard"],
        "high_scoring_risk": 0.08, "volatility": 0.66, "favorite_cover_trigger": False,
        "lambda_context": (-0.12, -0.05), "proxy_weight": 0.62,
        "forced_scores": ["0-0", "1-1", "0-1", "1-0", "1-2", "2-1", "0-2", "2-2"],
    },
    {
        "code": "周五087", "home": "阿根廷", "away": "佛得角", "home_en": "Argentina", "away_en": "Cape Verde Islands",
        "kickoff": "2026-07-04T06:00:00+08:00", "fixture_id": 1565179, "venue": "Hard Rock Stadium, Miami",
        "rank": (1, 72), "recent": ((3, 8, 1), (3, 2, 2)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；阿根廷实力和防守稳定性压倒性占优，但-2深盘需要防2球卡线。",
        "market_1x2_source": "500竞彩官方；主表胜平负未开售时用欧赔均值回填去水",
        "weather": "Miami傍晚炎热潮湿并有阵雨/雷暴季节风险；Hard Rock Stadium开放球场，湿热提高降速和换人变量。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction支持阿根廷胜且小于3.5球；500主表胜平负空缺，深度欧赔支持阿根廷强胜。",
        "api_endpoint_status": endpoint_status("周五087"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "low_block_opponent", "weather_suppression"],
        "high_scoring_risk": 0.30, "volatility": 0.64, "favorite_cover_trigger": True,
        "lambda_context": (0.10, -0.07), "proxy_weight": 0.74,
        "forced_scores": ["2-0", "3-0", "2-1", "3-1", "4-0", "1-0", "4-1", "0-0", "1-1"],
    },
    {
        "code": "周五088", "home": "哥伦比亚", "away": "加纳", "home_en": "Colombia", "away_en": "Ghana",
        "kickoff": "2026-07-04T09:30:00+08:00", "fixture_id": 1567310, "venue": "Arrowhead Stadium, Kansas City",
        "rank": (12, 77), "recent": ((3, 4, 1), (3, 2, 2)),
        "first_round": "Round of 32淘汰赛，90分钟胜平负；哥伦比亚整体实力、攻守均衡和低失球更好，加纳低位反击主要制造卡线。",
        "market_1x2_source": "500竞彩官方",
        "weather": "Kansas City晚间开放球场，夏季热湿和阵雨风险需纳入；盘口总进球偏低，天气只作小幅抑制。",
        "weather_suppression": True, "material_absence_team": "", "lineup_uncertainty": True,
        "absence_note": "API伤停0，正式首发未发布。API prediction给哥伦比亚不败且小于3.5球，500三向强支持哥伦比亚。",
        "api_endpoint_status": endpoint_status("周五088"),
        "group_direct_rivalry": False, "stage": "knockout", "round_index": 4,
        "tags": ["knockout_90min_draw_risk", "massive_favorite_depth", "favorite_win_not_clean_sheet", "low_block_opponent", "weather_suppression"],
        "high_scoring_risk": 0.18, "volatility": 0.62, "favorite_cover_trigger": True,
        "lambda_context": (-0.02, -0.05), "proxy_weight": 0.70,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "3-0", "3-1", "0-0", "0-1"],
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
        "model_version": "worldcup-knockout-90min-20260701-nine-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "500 PDF和实时网页均读取；本轮当前PDF共9场：周三080至周五088。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds均已请求；087 odds首轮SSL失败后重试成功。",
            "正式首发均未发布，赛前statistics为空；GPT/联网复核只进入事实层，直接概率权重0%。",
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
