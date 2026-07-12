from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multi_source_fusion import MultiSourceWeightPolicy
from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/worldcup_20260705_two")
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


META = [
    {
        "code": "周六089",
        "home": "加拿大",
        "away": "摩洛哥",
        "home_en": "Canada",
        "away_en": "Morocco",
        "kickoff": "2026-07-05T01:00:00+08:00",
        "fixture_id": 1567824,
        "venue": "NRG Stadium, Houston",
        "rank": (31, 14),
        "recent": ((4, 9, 3), (4, 8, 4)),
        "first_round": "世界杯16强淘汰赛，90分钟结算；加拿大主场氛围强但Koné缺席，摩洛哥阵容完整且不败势头更稳。",
        "market_1x2_source": "500竞彩官方实时",
        "weather": "Houston NRG Stadium可闭合顶棚，炎热天气影响降权；比赛节奏更多由摩洛哥控球和加拿大转换质量决定。",
        "weather_suppression": False,
        "material_absence_team": "home",
        "lineup_uncertainty": True,
        "absence_note": "API-Football确认加拿大I. Koné因下肢骨折缺席；Al Jazeera赛前信息称Davies已复出并可能首发，摩洛哥暂无伤停报告。",
        "api_endpoint_status": endpoint_status("周六089"),
        "group_direct_rivalry": False,
        "stage": "knockout",
        "round_index": 4,
        "tags": [
            "host_energy",
            "material_home_absence",
            "organized_transition_underdog",
            "favorite_win_not_depth",
            "low_block_opponent",
            "knockout_extra_time_risk",
        ],
        "high_scoring_risk": 0.22,
        "volatility": 0.66,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.06, 0.02),
        "proxy_weight": 0.68,
        "forced_scores": ["0-1", "1-1", "1-2", "0-2", "0-0", "1-0", "2-2", "2-1", "0-3", "1-3"],
    },
    {
        "code": "周六090",
        "home": "巴拉圭",
        "away": "法国",
        "home_en": "Paraguay",
        "away_en": "France",
        "kickoff": "2026-07-05T05:00:00+08:00",
        "fixture_id": 1569870,
        "venue": "Lincoln Financial Field, Philadelphia",
        "rank": (53, 2),
        "recent": ((4, 4, 5), (4, 13, 2)),
        "first_round": "世界杯16强淘汰赛，90分钟结算；法国攻击层级和阵容深度明显领先，巴拉圭淘汰德国后仍以低位防守和拖入加时为主线。",
        "market_1x2_source": "500深层欧赔均值回填",
        "weather": "Philadelphia开放球场，夏季炎热可能略降节奏；法国控球压制和巴拉圭低位防守是主变量。",
        "weather_suppression": True,
        "material_absence_team": None,
        "lineup_uncertainty": True,
        "absence_note": "API-Football伤停0；SI赛前预测法国基本沿用强阵，Saliba有背部问题但未确认缺席。正式首发未发布。",
        "api_endpoint_status": endpoint_status("周六090"),
        "group_direct_rivalry": False,
        "stage": "knockout",
        "round_index": 4,
        "tags": [
            "massive_favorite_depth",
            "low_block_opponent",
            "favorite_rotation_risk",
            "knockout_extra_time_risk",
            "favorite_win_not_clean_sheet",
        ],
        "high_scoring_risk": 0.39,
        "volatility": 0.58,
        "favorite_cover_trigger": True,
        "lambda_context": (-0.08, 0.16),
        "proxy_weight": 0.66,
        "forced_scores": ["0-2", "0-3", "1-3", "0-1", "0-4", "1-2", "1-4", "0-0", "1-1", "2-2"],
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
    enriched = {
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
    if meta["code"] == "周六089":
        policy = MultiSourceWeightPolicy()
        controls = policy.controls("opta")
        enriched["multi_source_result_fusion"] = {
            "base_weights": policy.result_profile(official_500=True),
            "fivehundred_quality": 1.0,
            "external_sources": [
                {
                    "name": "opta",
                    "probabilities": {"home": 0.217, "draw": 0.256, "away": 0.527},
                    "quality": float(controls.get("default_quality", 1.0)),
                    "correlation_discount": 1.0,
                    "apply_deviation_discount": bool(controls.get("apply_deviation_discount", False)),
                    "source_type": "model",
                    "metadata": {
                        "source": "Al Jazeera published Opta supercomputer 90-minute probabilities",
                        "published": "2026-07-03",
                        "event": "Canada vs Morocco, World Cup Round of 16",
                    },
                }
            ],
            "gpt_direct_probability_weight": policy.controls("gpt")["direct_probability_weight"],
        }
    return enriched


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    supplemental = json.loads(SUPPLEMENTAL_PATH.read_text(encoding="utf-8")) if SUPPLEMENTAL_PATH.exists() else {}
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-20260705-two-v1",
        "notes": [
            "世界杯16强按90分钟结算，不含加时和点球。",
            "500 PDF、500实时主表、深层欧赔/亚盘/大小球均已读取。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds均已请求；正式首发和技术统计赛前未开放。",
            "OddsPortal/Flashscore/AiScore已做公共页面补源尝试；赔率变化层仍为phase1_shadow_mode，只影响信心和风险审计，不直接改概率。",
            "GPT联网复核只用于事实校验；奇门直接概率权重为0%。",
        ],
        "supplemental_audit": supplemental,
        "matches": [analyze_match(enrich(meta, latest[meta["code"]]), WorldCupTrainedModel()) for meta in META],
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
            "scores": [score["score"] for score in item["final"]["scorelines"][:6]],
            "rules": item["decision_iteration"]["applied_rules"],
            "consistency": item["consistency"]["status"],
        } for item in output["matches"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
