from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bayesian_fusion import BayesianProbabilityFusion
from core.market_dewater import MarketDewater


BASE = Path("data/kleague_20260704")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"

TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")


META = {
    "周六201": {
        "home": "安养FC",
        "away": "浦项制铁",
        "home_en": "FC Anyang",
        "away_en": "Pohang Steelers",
        "fixture_id": 1506986,
        "venue": "Anyang Stadium",
        "rank": (7, 5),
        "standing": {
            "home": {"played": 15, "gf": 19, "ga": 16, "points": 20},
            "away": {"played": 15, "gf": 12, "ga": 12, "points": 22},
        },
        "weather": "Anyang 18:00-19:00有雷阵雨风险，气温约26-27C，节奏略受抑制。",
        "api_status": {"fixture": 1, "predictions": "SSL failed", "injuries": 0, "lineups": 0, "statistics": "SSL failed", "odds": 1},
        "context": {"home": -0.02, "away": -0.03, "total": -0.05},
        "forced_scores": ["1-1", "1-0", "0-1", "2-1", "0-0", "1-2", "2-2", "2-0"],
    },
    "周六203": {
        "home": "全北现代",
        "away": "江原FC",
        "home_en": "Jeonbuk Motors",
        "away_en": "Gangwon FC",
        "fixture_id": 1506988,
        "venue": "Jeonju World Cup Stadium",
        "rank": (2, 4),
        "standing": {
            "home": {"played": 15, "gf": 21, "ga": 12, "points": 26, "home_gf": 15, "home_ga": 8, "home_played": 7},
            "away": {"played": 15, "gf": 19, "ga": 10, "points": 24, "away_gf": 7, "away_ga": 2, "away_played": 7},
        },
        "weather": "Jeonju 18:00前后阴云为主，20:00后雷阵雨风险；湿热对高强度节奏略不利。",
        "api_status": {"fixture": 1, "predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "context": {"home": -0.01, "away": -0.05, "total": -0.06},
        "forced_scores": ["1-1", "1-0", "2-1", "0-0", "0-1", "2-0", "1-2", "2-2"],
    },
    "周六202": {
        "home": "大田市民",
        "away": "富川FC",
        "home_en": "Daejeon Citizen",
        "away_en": "Bucheon FC 1995",
        "fixture_id": 1506987,
        "venue": "Daejeon World Cup Stadium",
        "rank": (10, 9),
        "standing": {
            "home": {"played": 15, "gf": 17, "ga": 16, "points": 16, "home_gf": 3, "home_ga": 10, "home_played": 8},
            "away": {"played": 15, "gf": 11, "ga": 15, "points": 17, "away_gf": 5, "away_ga": 7, "away_played": 7},
        },
        "weather": "Daejeon 18:30多云约25C，白天有雷阵雨但开赛时强影响较低；湿度仍会压一点节奏。",
        "api_status": {"fixture": 1, "predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0, "odds": 1},
        "context": {"home": 0.06, "away": -0.03, "total": -0.04},
        "forced_scores": ["1-0", "2-0", "2-1", "1-1", "0-0", "0-1", "3-0", "1-2"],
    },
}


def poisson_probs(lh: float, la: float, max_goals: int = 7) -> dict[str, float]:
    scores = {}
    tail = 0.0
    for h in range(max_goals + 1):
        ph = math.exp(-lh) * lh**h / math.factorial(h)
        for a in range(max_goals + 1):
            pa = math.exp(-la) * la**a / math.factorial(a)
            scores[f"{h}-{a}"] = ph * pa
    total = sum(scores.values())
    return {k: v / total for k, v in scores.items()}


def result_from_scores(scores: dict[str, float]) -> dict[str, float]:
    out = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        out["home" if h > a else "away" if a > h else "draw"] += p
    return out


def handicap_from_scores(scores: dict[str, float], handicap: float) -> dict[str, float]:
    out = {"cover": 0.0, "push": 0.0, "fail": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        margin = h + handicap - a
        if margin > 0:
            out["cover"] += p
        elif margin == 0:
            out["push"] += p
        else:
            out["fail"] += p
    return out


def total_from_scores(scores: dict[str, float]) -> dict[str, float]:
    out = {k: 0.0 for k in TOTAL_KEYS}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        total = h + a
        out["7_plus" if total >= 7 else str(total)] += p
    return out


def normalize(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    return {k: round(v / s, 4) for k, v in d.items()}


def implied_total_mean(dist: dict[str, float]) -> float:
    return sum((7.5 if k == "7_plus" else float(k)) * v for k, v in dist.items())


def lambda_from_standing(meta: dict) -> tuple[float, float]:
    h = meta["standing"]["home"]
    a = meta["standing"]["away"]
    if "home_gf" in h and "away_gf" in a:
        home_attack = h["home_gf"] / h["home_played"]
        away_defense = a["away_ga"] / a["away_played"]
        away_attack = a["away_gf"] / a["away_played"]
        home_defense = h["home_ga"] / h["home_played"]
        lh = 0.58 * home_attack + 0.42 * away_defense
        la = 0.58 * away_attack + 0.42 * home_defense
    else:
        lh = 0.55 * (h["gf"] / h["played"]) + 0.45 * (a["ga"] / a["played"]) + 0.10
        la = 0.55 * (a["gf"] / a["played"]) + 0.45 * (h["ga"] / h["played"])
    return max(0.25, lh + meta["context"]["home"]), max(0.25, la + meta["context"]["away"])


def analyze(code: str, item: dict) -> dict:
    meta = META[code]
    current = item["current"]
    deep = item["deep_market"]
    one = current["one_x_two"]
    hcap = current["handicap_three_way"]
    total = current["total_exact"]
    one_market = MarketDewater.dewater_1x2({"home": one["3"], "draw": one["1"], "away": one["0"]}, source="500竞彩官方实时")
    handicap_market = MarketDewater.dewater_handicap_3way({"home": hcap["3"], "draw": hcap["1"], "away": hcap["0"]}, source="500竞彩官方让球三向")
    total_market = MarketDewater.dewater_total_goals_exact({k: total["7" if k == "7_plus" else k] for k in TOTAL_KEYS}, source="500竞彩官方总进球")
    lh, la = lambda_from_standing(meta)
    scores = poisson_probs(lh, la)
    prior_result = result_from_scores(scores)
    result_fusion = BayesianProbabilityFusion.fuse_3way(prior_result, one_market.probabilities, market_type="result_3way", prior_strength=10.0, evidence_strength=11.0)
    prior_hcap = handicap_from_scores(scores, current["handicap"])
    hcap_fusion = BayesianProbabilityFusion.fuse_3way(
        prior_hcap,
        {"cover": handicap_market.probabilities["home"], "push": handicap_market.probabilities["draw"], "fail": handicap_market.probabilities["away"]},
        market_type="handicap_3way",
        prior_strength=9.0,
        evidence_strength=11.0,
        keys=("cover", "push", "fail"),
    )
    prior_total = total_from_scores(scores)
    total_fusion = BayesianProbabilityFusion.fuse_3way(prior_total, total_market.probabilities, market_type="total_goals_exact", prior_strength=9.0, evidence_strength=9.0, keys=TOTAL_KEYS)
    score_market_raw = {}
    for score, price in current.get("scores", {}).items():
        if not isinstance(score, str) or not score[:1].isdigit():
            continue
        try:
            score_market_raw[score] = 1.0 / float(price)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    score_market = normalize(score_market_raw) if score_market_raw else {}
    score_rows = []
    for score, p in scores.items():
        if score in meta["forced_scores"] or len(score_rows) < 12:
            h, a = map(int, score.split("-"))
            result_boost = result_fusion.posterior_probabilities["home" if h > a else "away" if a > h else "draw"]
            total_key = "7_plus" if h + a >= 7 else str(h + a)
            market_boost = score_market.get(score, p)
            blended = (0.58 * p + 0.42 * market_boost) * (0.7 + result_boost) * (0.7 + total_fusion.posterior_probabilities[total_key])
            score_rows.append({"score": score, "probability": blended, "home_goals": h, "away_goals": a, "total_goals": h + a})
    forced = {row["score"] for row in score_rows}
    for score in meta["forced_scores"]:
        if score not in forced and score in scores:
            h, a = map(int, score.split("-"))
            score_rows.append({"score": score, "probability": 0.58 * scores[score] + 0.42 * score_market.get(score, scores[score]), "home_goals": h, "away_goals": a, "total_goals": h + a})
    score_rows = sorted(score_rows, key=lambda x: (x["score"] not in meta["forced_scores"], -x["probability"]))[:8]
    return {
        "identity": {"code": code, **{k: meta[k] for k in ["home", "away", "fixture_id", "venue", "rank", "weather"]}},
        "api_status": meta["api_status"],
        "market": {
            "one_x_two": one_market.to_dict(),
            "handicap_three_way": handicap_market.to_dict(),
            "total_exact": total_market.to_dict(),
            "deep": deep,
        },
        "model": {"lambda": {"home": round(lh, 3), "away": round(la, 3)}, "prior_result": normalize(prior_result)},
        "final": {
            "result": result_fusion.posterior_probabilities,
            "handicap_home_settlement": hcap_fusion.posterior_probabilities,
            "total_distribution": total_fusion.posterior_probabilities,
            "total_mean": round(implied_total_mean(total_fusion.posterior_probabilities), 3),
            "scorelines": score_rows,
        },
        "audit": {
            "result_max_deviation": result_fusion.max_deviation,
            "result_reliability": result_fusion.reliability,
            "handicap_reliability": hcap_fusion.reliability,
            "notes": [
                "真实xG缺失，使用联赛进失球proxy并向市场去水概率融合。",
                "Odds movement phase1: 赔率变化只进入风险标签，不直接改概率。",
            ],
        },
    }


def main() -> None:
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "kleague-20260704-v1",
        "matches": [analyze(code, market[code]) for code in ["周六201", "周六202", "周六203"]],
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "summary": [{
            "code": m["identity"]["code"],
            "match": f"{m['identity']['home']}vs{m['identity']['away']}",
            "result": m["final"]["result"],
            "handicap": m["final"]["handicap_home_settlement"],
            "mean": m["final"]["total_mean"],
            "scores": [s["score"] for s in m["final"]["scorelines"][:5]],
        } for m in output["matches"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
