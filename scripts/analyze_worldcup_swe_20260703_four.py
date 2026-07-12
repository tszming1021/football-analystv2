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
from scripts.analyze_worldcup_0701_nine_knockout import META as PREVIOUS_META


BASE = Path("data/worldcup_swe_20260703_four")
MARKET_PATH = BASE / "market/latest_market.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
SUPPLEMENTAL_PATH = BASE / "supplemental_audit.json"
OUT_PATH = BASE / "model_analysis.json"


def endpoint_status(code: str) -> dict:
    audit = json.loads(API_AUDIT_PATH.read_text(encoding="utf-8"))
    endpoints = audit["fixtures"][code]["endpoints"]
    status = {}
    for name, payload in endpoints.items():
        status[name] = payload["exception"] if "exception" in payload else payload.get("results", 0)
    return status


def previous(code: str) -> dict:
    return deepcopy(next(item for item in PREVIOUS_META if item["code"] == code))


def with_updates(code: str, **updates) -> dict:
    item = previous(code)
    item.update(updates)
    item["api_endpoint_status"] = endpoint_status(code)
    return item


META = [
    {
        **with_updates(
            "周五086",
            recent=((3, 2, 2), (3, 5, 3)),
            material_absence_team="away",
            absence_note=(
                "API确认埃及Hamdi Fathy缺席；Guardian称Salah已经恢复到可出战但首发/替补待定，澳大利亚Mat Leckie、Jacob Italiano缺席。"
                "API prediction仍给澳大利亚不败且小于3.5球，500三向埃及小热。"
            ),
            high_scoring_risk=0.05,
            lambda_context=(-0.16, -0.07),
            forced_scores=["0-0", "1-1", "0-1", "1-0", "1-2", "0-2", "2-1", "2-2"],
        ),
        "market_1x2_source": "500竞彩官方实时",
    },
    {
        **with_updates(
            "周五087",
            absence_note="API伤停0，正式首发未发布。Goal/RotoWire等赛前预览给阿根廷强势阵容，佛得角预计4-5-1低位；500主表胜平负未开售，深层欧赔回填。",
            high_scoring_risk=0.34,
            lambda_context=(0.13, -0.05),
            forced_scores=["2-0", "3-0", "4-0", "2-1", "3-1", "5-0", "1-0", "1-1", "0-0"],
        ),
        "market_1x2_source": "500深层欧赔均值回填",
    },
    {
        **with_updates(
            "周五088",
            absence_note="API伤停0，正式首发未发布。FIFA/Goal/ESPN确认Kansas City场地和哥伦比亚强热门；Ghana FA强调加纳已抵达并完成备战。",
            high_scoring_risk=0.24,
            lambda_context=(0.02, -0.04),
            forced_scores=["2-0", "1-0", "2-1", "3-0", "3-1", "1-1", "4-0", "0-0"],
        ),
        "market_1x2_source": "500竞彩官方实时",
    },
    {
        "code": "周五201", "home": "天狼星", "away": "米亚尔比", "home_en": "Sirius", "away_en": "Mjallby AIF",
        "kickoff": "2026-07-04T01:00:00+08:00", "fixture_id": 1494200, "venue": "Studenternas IP, Uppsala",
        "rank": (1, 6), "recent": ((5, 13, 5), (5, 9, 6)),
        "first_round": "瑞典超常规联赛；天狼星榜首且近5场全胜，米亚尔比排名第6、进攻效率不低。",
        "market_1x2_source": "500竞彩官方实时",
        "weather": "Uppsala晚间户外球场，北欧夏季温和；天气不构成强抑制，开放球场仍保留风雨变量。",
        "weather_suppression": False, "material_absence_team": "home", "lineup_uncertainty": True,
        "absence_note": "API列出天狼星N. Milleskog、M. Soumah缺席，A. Ljungberg、J. Persson存疑；正式首发未发布。API prediction给天狼星不败。",
        "api_endpoint_status": endpoint_status("周五201"),
        "group_direct_rivalry": False, "stage": "league", "round_index": 12,
        "tags": ["favorite_win_not_depth", "home_defensive_leak", "open_league_high_variance", "material_home_absence"],
        "high_scoring_risk": 0.42, "volatility": 0.72, "favorite_cover_trigger": False,
        "lambda_context": (0.10, 0.04), "proxy_weight": 0.66,
        "forced_scores": ["2-1", "2-0", "1-1", "3-1", "2-2", "1-0", "3-2", "1-2"],
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
    supplemental = json.loads(SUPPLEMENTAL_PATH.read_text(encoding="utf-8"))
    model = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-swe-20260703-four-v1",
        "notes": [
            "世界杯淘汰赛按90分钟结算；瑞超201按常规90分钟结算。",
            "500实时主表与深层欧赔/亚盘/大小球已重新抓取。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds与standings已请求；正式首发均未发布。",
            "OddsPortal/Flashscore/AiScore为补源审计；赔率变化层当前phase1_shadow_mode，只影响风险标签，不直接修改最终概率。",
        ],
        "supplemental_audit": supplemental,
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
