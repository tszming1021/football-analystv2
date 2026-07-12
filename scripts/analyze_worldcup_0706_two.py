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


BASE = Path("data/worldcup_20260706_two")
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
        "code": "周日091",
        "home": "巴西",
        "away": "挪威",
        "home_en": "Brazil",
        "away_en": "Norway",
        "kickoff": "2026-07-06T04:00:00+08:00",
        "fixture_id": 1568100,
        "venue": "MetLife Stadium, New Jersey",
        "rank": (5, 43),
        "recent": ((4, 9, 2), (4, 10, 8)),
        "first_round": "世界杯16强淘汰赛，90分钟结算；巴西淘汰日本但过程偏紧，Raphinha缺席且Paqueta/Casemiro需观察；挪威有Haaland连续进球与高转换威胁。",
        "market_1x2_source": "500竞彩官方实时",
        "weather": "MetLife开放球场，夏季户外但非极端气候；节奏主要由巴西控球质量和挪威反击决定。",
        "weather_suppression": False,
        "material_absence_team": "home",
        "lineup_uncertainty": True,
        "absence_note": "API-Football显示巴西Raphinha腿筋伤缺席；公开预览称Paqueta/Casemiro需观察，巴西预计仍保留Vinicius/Cunha等攻击点。",
        "api_endpoint_status": endpoint_status("周日091"),
        "group_direct_rivalry": False,
        "stage": "knockout",
        "round_index": 4,
        "tags": [
            "favorite_win_not_depth",
            "favorite_depth_tail_reactivation",
            "set_piece_underdog_threat",
            "organized_transition_underdog",
            "favorite_rotation_risk",
            "knockout_extra_time_risk",
        ],
        "high_scoring_risk": 0.42,
        "volatility": 0.72,
        "favorite_cover_trigger": False,
        "lambda_context": (0.03, 0.10),
        "proxy_weight": 0.66,
        "forced_scores": ["2-1", "1-1", "2-2", "3-1", "1-0", "2-0", "1-2", "3-2", "4-1", "0-1", "0-0"],
        "opta": {
            "probabilities": {"home": 0.536, "draw": 0.240, "away": 0.224},
            "source": "Opta Analyst Brazil vs Norway preview",
            "published": "2026-07-04",
        },
    },
    {
        "code": "周日092",
        "home": "墨西哥",
        "away": "英格兰",
        "home_en": "Mexico",
        "away_en": "England",
        "kickoff": "2026-07-06T08:00:00+08:00",
        "fixture_id": 1570714,
        "venue": "Estadio Banorte, Mexico City",
        "rank": (19, 4),
        "recent": ((4, 8, 0), (4, 8, 3)),
        "first_round": "世界杯16强淘汰赛，90分钟结算；墨西哥东道主与高海拔主场优势明显，英格兰名气和个体质量更高但右后卫伤疑、旅程和海拔适应是变量。",
        "market_1x2_source": "500竞彩官方实时",
        "weather": "墨西哥城高海拔约2240米，比赛维持晚间时段；高海拔和东道主慢节奏对英格兰客场节奏形成抑制。",
        "weather_suppression": True,
        "material_absence_team": None,
        "lineup_uncertainty": True,
        "absence_note": "API-Football伤停0；公开预览称英格兰Reece James、Jarell Quansah存疑，Saka/Gordon可能进入首发；墨西哥正式首发未发布。",
        "api_endpoint_status": endpoint_status("周日092"),
        "group_direct_rivalry": False,
        "stage": "knockout",
        "round_index": 4,
        "tags": [
            "host_energy",
            "altitude_travel_disruption",
            "favorite_draw_enough",
            "plus_one_push_guard",
            "low_block_opponent",
            "knockout_extra_time_risk",
        ],
        "high_scoring_risk": 0.20,
        "volatility": 0.69,
        "favorite_cover_trigger": False,
        "lambda_context": (0.05, -0.07),
        "proxy_weight": 0.68,
        "forced_scores": ["1-1", "0-1", "1-0", "0-0", "1-2", "0-2", "2-1", "2-2", "0-3", "1-3"],
        "opta": {
            "probabilities": {"home": 0.315, "draw": 0.279, "away": 0.406},
            "source": "Opta Analyst Mexico vs England preview",
            "published": "2026-07-04",
        },
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
    policy = MultiSourceWeightPolicy()
    controls = policy.controls("opta")
    enriched["multi_source_result_fusion"] = {
        "base_weights": policy.result_profile(official_500=True),
        "fivehundred_quality": 1.0,
        "external_sources": [
            {
                "name": "opta",
                "probabilities": meta["opta"]["probabilities"],
                "quality": float(controls.get("default_quality", 1.0)),
                "correlation_discount": 1.0,
                "apply_deviation_discount": bool(controls.get("apply_deviation_discount", False)),
                "source_type": "model",
                "metadata": {
                    "source": meta["opta"]["source"],
                    "published": meta["opta"]["published"],
                    "event": f"{meta['home_en']} vs {meta['away_en']}, World Cup Round of 16",
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
        "model_version": "worldcup-20260706-two-v1",
        "notes": [
            "世界杯16强按90分钟结算，不含加时和点球。",
            "用户PDF已解析，500实时主表、深层欧赔/亚盘/大小球均已读取。",
            "API-Football fixture/predictions/injuries/lineups/statistics/odds均已请求；正式首发和技术统计赛前未开放。",
            "OddsPortal/Flashscore/AiScore已做公共页面补源尝试；赔率变化层仍为phase1_shadow_mode，只影响信心和风险审计，不直接改概率。",
            "昨日复盘新增风险：受让+1保护必须拆分让胜与让平卡线，不能机械把保护写成高优先级让胜。",
            "GPT联网复核只用于事实校验；直接概率权重为0%。",
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
