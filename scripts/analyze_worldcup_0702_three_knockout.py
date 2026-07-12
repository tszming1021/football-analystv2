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


BASE = Path("data/worldcup_20260702_three")
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
        "周四083",
        material_absence_team="home",
        absence_note=(
            "API伤停0、正式首发未发布；联网复核显示西班牙Yeremy Pino、Nico Williams缺席/高度存疑，"
            "Victor Muñoz腿筋不适但已部分恢复训练。奥地利暂无确认缺席。500主胜继续压低，-1让胜热度升温。"
        ),
        tags=[
            "knockout_90min_draw_risk",
            "massive_favorite_depth",
            "favorite_win_not_clean_sheet",
            "low_block_opponent",
            "material_home_absence",
            "favorite_rotation_risk",
        ],
        high_scoring_risk=0.30,
        lambda_context=(0.06, -0.02),
        forced_scores=["2-0", "2-1", "1-0", "3-0", "3-1", "1-1", "2-2", "0-0"],
    ),
    with_updates(
        "周四084",
        absence_note=(
            "API伤停0、正式首发未发布；联网复核未见葡萄牙/克罗地亚重大新增伤停。"
            "葡萄牙Rúben Dias回归后防线更稳，但赛前报道持续强调对Ronaldo终结和Croatia淘汰赛韧性的博弈。"
        ),
        tags=[
            "knockout_90min_draw_risk",
            "strong_defense_opponent",
            "plus_one_cover_risk",
            "weather_suppression",
            "top_table_stalemate_guard",
            "organized_transition_underdog",
            "comeback_equalizer_risk",
        ],
        high_scoring_risk=0.20,
        lambda_context=(-0.05, -0.02),
        forced_scores=["1-1", "2-1", "1-0", "2-2", "0-1", "2-0", "1-2", "3-1"],
    ),
    with_updates(
        "周四085",
        material_absence_team="away",
        absence_note=(
            "API伤停0、正式首发未发布；Goal称双方暂无确认伤停，但WhoScored/SportsMole口径提示阿尔及利亚Mohamed Amoura腿筋问题/存疑。"
            "500三向瑞士小热，让球端继续保护阿尔及利亚+1。"
        ),
        tags=[
            "knockout_90min_draw_risk",
            "balanced_direct_match",
            "plus_one_cover_risk",
            "organized_transition_underdog",
            "material_away_absence",
            "top_table_stalemate_guard",
        ],
        high_scoring_risk=0.18,
        lambda_context=(-0.04, -0.03),
        forced_scores=["1-1", "1-0", "2-1", "0-0", "2-0", "0-1", "2-2", "1-2"],
    ),
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
        "model_version": "worldcup-knockout-90min-20260702-three-v1",
        "notes": [
            "淘汰赛口径：胜平负、让球胜平负、比分、总球均按90分钟常规时间结算。",
            "500主表来自用户提供的2026-07-02 14:40 PDF；500网页DNS失败，深层欧赔/亚盘/大小球沿用2026-07-01缓存并降权披露。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds已请求；085 statistics代理断开，正式首发均未发布。",
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
