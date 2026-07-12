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


BASE = Path("data/nordic_20260704")
MARKET_PATH = BASE / "market/latest_market.json"
OUT_PATH = BASE / "model_analysis.json"
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")

META = {
    "周六204": {
        "home": "拉赫蒂", "away": "赫尔辛基火花", "fixture_id": 1495723,
        "league": "芬超", "rank": (9, 6), "standing": {"home": {"played": 13, "gf": 15, "ga": 15, "points": 13}, "away": {"played": 13, "gf": 19, "ga": 17, "points": 19}},
        "api_prediction": "平或赫尔辛基火花", "weather": "Lahti晚间常规户外条件，天气只做弱修正。",
        "context": {"home": -0.02, "away": 0.01}, "forced_scores": ["1-1", "2-1", "1-2", "2-2", "1-0", "0-1", "2-0", "0-0", "3-2"],
    },
    "周六205": {
        "home": "哈尔姆斯", "away": "韦斯特罗斯", "fixture_id": 1494198,
        "league": "瑞超", "rank": (15, 11), "standing": {"home": {"played": 10, "gf": 9, "ga": 20, "points": 6}, "away": {"played": 10, "gf": 17, "ga": 22, "points": 12}},
        "api_prediction": "平或韦斯特罗斯；韦斯特罗斯M. Diallo存疑", "weather": "Halmstad晚间户外，天气只做弱修正。",
        "context": {"home": -0.02, "away": 0.04}, "forced_scores": ["1-2", "1-1", "0-1", "2-2", "0-2", "2-1", "0-0", "1-3"],
    },
    "周六206": {
        "home": "代格福什", "away": "马尔默", "fixture_id": 1494194,
        "league": "瑞超", "rank": (12, 9), "standing": {"home": {"played": 10, "gf": 12, "ga": 16, "points": 10}, "away": {"played": 10, "gf": 20, "ga": 20, "points": 13}},
        "api_prediction": "平或马尔默；代格福什2人缺席，马尔默Christiansen/Jansson缺席", "weather": "Degerfors晚间户外，天气只做弱修正。",
        "context": {"home": -0.03, "away": 0.02}, "forced_scores": ["1-2", "0-2", "1-1", "0-1", "0-3", "2-2", "1-3", "2-1"],
    },
    "周六207": {
        "home": "塞伊奈", "away": "TPS图尔", "fixture_id": 1495725,
        "league": "芬超", "rank": (10, 7), "standing": {"home": {"played": 13, "gf": 15, "ga": 21, "points": 11}, "away": {"played": 13, "gf": 15, "ga": 13, "points": 19}},
        "api_prediction": "塞伊奈不败", "weather": "Seinajoki晚间常规户外条件，天气只做弱修正。",
        "context": {"home": 0.10, "away": -0.05}, "forced_scores": ["2-1", "2-0", "1-1", "1-0", "3-1", "1-2", "2-2", "3-0"],
    },
    "周六208": {
        "home": "雅罗", "away": "坦佩雷山猫", "fixture_id": 1495724,
        "league": "芬超", "rank": (11, 8), "standing": {"home": {"played": 14, "gf": 13, "ga": 31, "points": 8}, "away": {"played": 14, "gf": 24, "ga": 27, "points": 16}},
        "api_prediction": "平或坦佩雷山猫，且大于1.5球", "weather": "Pietarsaari晚间户外，天气只做弱修正。",
        "context": {"home": -0.02, "away": 0.08}, "forced_scores": ["1-2", "1-3", "0-2", "2-2", "0-1", "0-3", "2-3", "1-1"],
    },
    "周六209": {
        "home": "瓦萨", "away": "玛丽港", "fixture_id": 1495726,
        "league": "芬超", "rank": (5, 12), "standing": {"home": {"played": 13, "gf": 17, "ga": 11, "points": 21}, "away": {"played": 13, "gf": 6, "ga": 25, "points": 4}},
        "api_prediction": "瓦萨胜", "weather": "Vaasa晚间户外，天气只做弱修正。",
        "context": {"home": 0.16, "away": -0.05}, "forced_scores": ["2-0", "3-0", "2-1", "3-1", "1-0", "4-0", "4-1", "1-1"],
    },
}


def poisson(lh: float, la: float, max_goals: int = 7) -> dict[str, float]:
    scores = {}
    for h in range(max_goals + 1):
        ph = math.exp(-lh) * lh**h / math.factorial(h)
        for a in range(max_goals + 1):
            pa = math.exp(-la) * la**a / math.factorial(a)
            scores[f"{h}-{a}"] = ph * pa
    s = sum(scores.values())
    return {k: v / s for k, v in scores.items()}


def dist_result(scores: dict[str, float]) -> dict[str, float]:
    out = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        out["home" if h > a else "away" if a > h else "draw"] += p
    return out


def dist_hcap(scores: dict[str, float], handicap: float) -> dict[str, float]:
    out = {"cover": 0.0, "push": 0.0, "fail": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        margin = h + handicap - a
        out["cover" if margin > 0 else "fail" if margin < 0 else "push"] += p
    return out


def dist_total(scores: dict[str, float]) -> dict[str, float]:
    out = {k: 0.0 for k in TOTAL_KEYS}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        t = h + a
        out["7_plus" if t >= 7 else str(t)] += p
    return out


def total_mean(d: dict[str, float]) -> float:
    return sum((7.5 if k == "7_plus" else float(k)) * v for k, v in d.items())


def norm(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    return {k: v / s for k, v in d.items()} if s else d


def lambdas(meta: dict) -> tuple[float, float]:
    h, a = meta["standing"]["home"], meta["standing"]["away"]
    league_avg = 1.35 if meta["league"] == "瑞超" else 1.45
    lh = 0.55 * (h["gf"] / h["played"]) + 0.45 * (a["ga"] / a["played"])
    la = 0.55 * (a["gf"] / a["played"]) + 0.45 * (h["ga"] / h["played"])
    # shrink toward league average to avoid overfitting short samples
    lh = 0.78 * lh + 0.22 * league_avg
    la = 0.78 * la + 0.22 * league_avg
    return max(0.25, lh + meta["context"]["home"]), max(0.25, la + meta["context"]["away"])


def analyze(code: str, item: dict) -> dict:
    meta = META[code]
    cur = item["current"]
    one = cur["one_x_two"]
    hcap = cur["handicap_three_way"]
    total = cur["total_exact"]
    one_m = MarketDewater.dewater_1x2({"home": one["3"], "draw": one["1"], "away": one["0"]}, source="500竞彩官方实时")
    hcap_m = MarketDewater.dewater_handicap_3way({"home": hcap["3"], "draw": hcap["1"], "away": hcap["0"]}, source="500竞彩官方让球三向")
    total_m = MarketDewater.dewater_total_goals_exact({k: total["7" if k == "7_plus" else k] for k in TOTAL_KEYS}, source="500竞彩官方总进球")
    lh, la = lambdas(meta)
    scores = poisson(lh, la)
    res_f = BayesianProbabilityFusion.fuse_3way(dist_result(scores), one_m.probabilities, market_type="result_3way", prior_strength=10, evidence_strength=11)
    hcap_f = BayesianProbabilityFusion.fuse_3way(dist_hcap(scores, cur["handicap"]), {"cover": hcap_m.probabilities["home"], "push": hcap_m.probabilities["draw"], "fail": hcap_m.probabilities["away"]}, market_type="handicap_3way", prior_strength=9, evidence_strength=11, keys=("cover", "push", "fail"))
    total_f = BayesianProbabilityFusion.fuse_3way(dist_total(scores), total_m.probabilities, market_type="total_goals_exact", prior_strength=9, evidence_strength=9, keys=TOTAL_KEYS)
    score_market = {}
    for score, price in cur.get("scores", {}).items():
        if isinstance(score, str) and score[:1].isdigit():
            try:
                score_market[score] = 1.0 / float(price)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    score_market = norm(score_market)
    rows = []
    for score in set(list(scores) + meta["forced_scores"]):
        if score not in scores:
            continue
        h, a = map(int, score.split("-"))
        side = "home" if h > a else "away" if a > h else "draw"
        tkey = "7_plus" if h + a >= 7 else str(h + a)
        blended = (0.58 * scores[score] + 0.42 * score_market.get(score, scores[score]))
        blended *= (0.72 + res_f.posterior_probabilities[side]) * (0.72 + total_f.posterior_probabilities[tkey])
        rows.append({"score": score, "probability": blended, "home_goals": h, "away_goals": a, "total_goals": h + a})
    rows = sorted(rows, key=lambda x: (x["score"] not in meta["forced_scores"], -x["probability"]))[:10]
    return {
        "identity": {"code": code, **{k: meta[k] for k in ["home", "away", "league", "rank", "fixture_id", "api_prediction", "weather"]}},
        "market": {"one_x_two": one_m.to_dict(), "handicap_three_way": hcap_m.to_dict(), "total_exact": total_m.to_dict(), "deep": item["deep_market"]},
        "model": {"lambda": {"home": round(lh, 3), "away": round(la, 3)}, "standing": meta["standing"]},
        "final": {"result": res_f.posterior_probabilities, "handicap_home_settlement": hcap_f.posterior_probabilities, "total_distribution": total_f.posterior_probabilities, "total_mean": round(total_mean(total_f.posterior_probabilities), 3), "scorelines": rows},
        "audit": {"result_reliability": res_f.reliability, "result_max_deviation": res_f.max_deviation, "notes": ["真实xG缺失，使用联赛进失球proxy并与500去水市场融合。", "赔率变化层phase1，仅进入风险解释，不直接改概率。"]},
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    output = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "model_version": "nordic-20260704-v1", "matches": [analyze(code, latest[code]) for code in ["周六204", "周六205", "周六206", "周六207", "周六208", "周六209"]]}
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT_PATH), "summary": [{"code": m["identity"]["code"], "match": f"{m['identity']['home']}vs{m['identity']['away']}", "result": m["final"]["result"], "handicap": m["final"]["handicap_home_settlement"], "mean": m["final"]["total_mean"], "scores": [s["score"] for s in m["final"]["scorelines"][:5]]} for m in output["matches"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
