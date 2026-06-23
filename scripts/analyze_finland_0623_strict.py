from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from scripts.analyze_worldcup_0620_strict_1847 import analyze_match


BASE = Path("data/finland_20260623")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"


class ProxyOnlyModel:
    def lambdas(self, home: str, away: str, neutral: bool = False):
        return None


META = [
    {
        "code": "周二201", "home": "拉赫蒂", "away": "TPS图尔库", "home_en": "Lahti", "away_en": "Turku PS",
        "kickoff": "2026-06-23T23:00:00+08:00", "fixture_id": 1495710, "venue": "Lahden Stadion, Lahti",
        "rank": (9, 7), "recent": ((10, 16, 15), (10, 10, 10)),
        "first_round": "联赛第12-14轮阶段；拉赫蒂11场11分，TPS 11场15分",
        "market_1x2_source": "500竞彩官方", "weather": "Lahti 18:00，18.9C、湿度33%、降水0%、风17.6km/h",
        "weather_suppression": False, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容，无官方最终首发",
        "group_direct_rivalry": False, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["low_block_opponent", "favorite_rotation_risk"], "high_scoring_risk": 0.14, "volatility": 0.57,
        "favorite_cover_trigger": False, "lambda_context": (-0.05, -0.03), "proxy_weight": 1.0,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "0-0", "0-1", "1-2", "2-2", "3-0", "3-1"],
    },
    {
        "code": "周二202", "home": "库奥皮奥", "away": "坦佩雷山猫", "home_en": "KuPS", "away_en": "Ilves",
        "kickoff": "2026-06-23T23:00:00+08:00", "fixture_id": 1495709, "venue": "Vare Areena, Kuopio",
        "rank": (3, 8), "recent": ((10, 13, 5), (10, 22, 12)),
        "first_round": "库普斯13场24分主场不败；埃尔维斯12场15分且客场0胜",
        "market_1x2_source": "500竞彩官方", "weather": "Kuopio 18:00，18.1C、湿度42%、降水2%、风16.6km/h",
        "weather_suppression": False, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容",
        "group_direct_rivalry": False, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["organized_transition_underdog", "comeback_equalizer_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.28, "volatility": 0.68, "favorite_cover_trigger": False,
        "lambda_context": (0.02, 0.04), "proxy_weight": 1.0,
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "3-0", "3-1", "2-2", "1-2", "3-2", "2-3", "4-1"],
    },
    {
        "code": "周二203", "home": "瓦萨", "away": "AC奥卢", "home_en": "VPS", "away_en": "AC Oulu",
        "kickoff": "2026-06-23T23:00:00+08:00", "fixture_id": 1495711, "venue": "Lemonsoft Stadion, Vaasa",
        "rank": (6, 2), "recent": ((10, 19, 6), (10, 12, 8)),
        "first_round": "瓦萨11场17分主场不败；奥卢12场25分排名第2",
        "market_1x2_source": "500竞彩官方", "weather": "Vaasa 18:00，15.4C、湿度55%、降水0%、风21.2km/h",
        "weather_suppression": True, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容",
        "group_direct_rivalry": True, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["top_table_direct_rival", "strong_defense_opponent", "organized_transition_underdog"],
        "high_scoring_risk": 0.10, "volatility": 0.52, "favorite_cover_trigger": False,
        "lambda_context": (-0.10, -0.10), "proxy_weight": 1.0,
        "forced_scores": ["0-0", "1-0", "0-1", "1-1", "2-0", "0-2", "2-1", "1-2", "2-2", "3-2", "2-3"],
    },
    {
        "code": "周二204", "home": "雅罗", "away": "格尼斯坦", "home_en": "FF Jaro", "away_en": "Gnistan",
        "kickoff": "2026-06-24T00:00:00+08:00", "fixture_id": 1495713, "venue": "Project Liv Arena, Pietarsaari",
        "rank": (11, 5), "recent": ((10, 13, 29), (10, 18, 9)),
        "first_round": "雅罗12场仅7分、失27球；格尼斯坦11场17分",
        "market_1x2_source": "500竞彩官方", "weather": "Pietarsaari 19:00，15.2C、湿度59%、降水0%、风16.9km/h",
        "weather_suppression": False, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容",
        "group_direct_rivalry": False, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["home_defensive_leak", "away_depth_upside", "open_league_high_variance", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.36, "volatility": 0.76, "favorite_cover_trigger": False,
        "lambda_context": (0.00, 0.12), "proxy_weight": 1.0,
        "forced_scores": ["0-1", "0-2", "1-2", "1-1", "1-3", "0-3", "2-2", "1-0", "2-1", "2-3", "3-2"],
    },
    {
        "code": "周二205", "home": "国际图尔库", "away": "塞伊奈", "home_en": "Inter Turku", "away_en": "SJK",
        "kickoff": "2026-06-24T00:00:00+08:00", "fixture_id": 1495712, "venue": "Veritas Stadion, Turku",
        "rank": (1, 10), "recent": ((10, 26, 9), (10, 17, 14)),
        "first_round": "国际图尔库13场26分榜首且主场不败；塞伊奈11场仅9分",
        "market_1x2_source": "500竞彩官方", "weather": "Turku 19:00，16.6C、湿度54%、降水15%、毛毛雨代码51、风4km/h",
        "weather_suppression": True, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容",
        "group_direct_rivalry": False, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["home_defensive_leak", "low_block_opponent", "open_league_high_variance"],
        "high_scoring_risk": 0.30, "volatility": 0.64, "favorite_cover_trigger": True,
        "lambda_context": (0.10, -0.03), "proxy_weight": 1.0,
        "forced_scores": ["1-0", "2-0", "2-1", "3-0", "3-1", "1-1", "2-2", "0-1", "3-2", "4-0", "4-1"],
    },
    {
        "code": "周二206", "home": "玛丽港", "away": "赫尔辛基", "home_en": "Mariehamn", "away_en": "HJK Helsinki",
        "kickoff": "2026-06-24T01:00:00+08:00", "fixture_id": 1495714, "venue": "Mariehamn",
        "rank": (12, 4), "recent": ((10, 8, 14), (10, 35, 12)),
        "first_round": "玛丽港11场0胜仅4分、进6球；赫尔辛基12场19分",
        "market_1x2_source": "500竞彩官方", "weather": "Mariehamn 20:00，16.1C、湿度76%、降水11%、风16.9km/h",
        "weather_suppression": False, "material_absence_team": "", "absence_note": "API伤停与首发均0行；附件仅预计阵容",
        "group_direct_rivalry": False, "competition_type": "league", "stage": "regular", "round_index": 14,
        "tags": ["massive_favorite_depth", "home_defensive_leak", "away_depth_upside", "defensive_collapse_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.48, "volatility": 0.76, "favorite_cover_trigger": True,
        "lambda_context": (-0.08, 0.22), "proxy_weight": 1.0,
        "forced_scores": ["0-1", "0-2", "0-3", "1-2", "1-3", "0-4", "1-4", "1-1", "2-2", "1-0", "2-3", "0-5"],
    },
]


def enrich(meta: dict, item: dict) -> dict:
    current = item["current"]
    deep = item["deep_market"]
    one = current["one_x_two"] or {"3": deep["ouzhi"]["current"][0], "1": deep["ouzhi"]["current"][1], "0": deep["ouzhi"]["current"][2]}
    scores = {label: price for label, price in current["scores"].items() if label[0].isdigit()}
    total = current["total_exact"]
    return {
        **meta, "market_1x2": (one["3"], one["1"], one["0"]),
        "handicap": current["handicap"],
        "handicap_3way": (current["handicap_three_way"]["3"], current["handicap_three_way"]["1"], current["handicap_three_way"]["0"]),
        "total_exact": tuple(total[str(i)] for i in range(7)) + (total["7"],),
        "score_prices": scores, "market_total_line": deep["daxiao"]["current"][1],
        "asian_line": deep["yazhi"]["current"][1], "lineup_uncertainty": True,
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    matches = [enrich(meta, latest[meta["code"]]) for meta in META]
    model = ProxyOnlyModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "veikkausliiga-strict-20260623-v1",
        "notes": [
            "真实赛前xG/xGA不可用；使用联赛主客拆分、近10场和500市场构建proxy xG。",
            "API prediction作为旁证，不直接输入最终概率；其固定45/45/10结构信息量有限。",
            "三向、让球三向、总进球均先去水再做贝叶斯融合。",
            "本轮未提供投注分析PDF或Transfermarkt比赛页，交易热度与缺席层降权。",
        ],
        "matches": [analyze_match(match, model) for match in matches],
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT_PATH), "summary": [{
        "code": x["identity"]["code"], "result": x["final"]["result"],
        "handicap": x["final"]["handicap_home_settlement"], "mean": x["means"]["decision_final"],
        "scores": [s["score"] for s in x["final"]["scorelines"][:7]],
        "rules": x["decision_iteration"]["applied_rules"], "consistency": x["consistency"]["status"],
    } for x in output["matches"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
