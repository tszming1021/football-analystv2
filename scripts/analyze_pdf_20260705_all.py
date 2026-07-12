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


BASE = Path("data/pdf_20260705_all")
MARKET_PATH = BASE / "market/latest_market.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
OUT_PATH = BASE / "model_analysis.json"
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")


META = {
    "周日091": {"league": "世界杯", "fixture_id": 1568100, "rank": (5, 43), "note": "巴西Raphinha缺席；巴西胜面高但不追-1。"},
    "周日092": {"league": "世界杯", "fixture_id": 1570714, "rank": (19, 4), "note": "墨西哥高海拔主场；英格兰胜面有但+1保护强。"},
    "周日201": {"league": "韩职", "fixture_id": 1506991, "rank": (1, 6), "note": "首尔榜首主场，-1需防卡线。"},
    "周日202": {"league": "韩职", "fixture_id": 1506990, "rank": (12, 4), "note": "蔚山胜面明显，光州+1有卡线风险。"},
    "周日203": {"league": "韩职", "fixture_id": 1506989, "rank": (11, 8), "note": "两队接近，金泉-1不宜深追。"},
    "周日204": {"league": "瑞超", "fixture_id": 1494199, "rank": (12, 16), "note": "卡尔马胜面强，-1仍需防让平。"},
    "周日205": {"league": "瑞超", "fixture_id": 1494196, "rank": (14, 11), "note": "哥德堡主胜略优，索尔纳+1保护清楚。"},
    "周日206": {"league": "瑞超", "fixture_id": 1494195, "rank": (3, 4), "note": "强强战，哈马比胜面但埃夫斯堡+1保护。"},
    "周一093": {"league": "世界杯", "fixture_id": 1576756, "rank": (6, 3), "note": "西班牙胜面，葡萄牙+1保护。"},
    "周一094": {"league": "世界杯", "fixture_id": 1570715, "rank": (16, 8), "note": "美国主场与比利时接近，+1保护优先。"},
    "周一201": {"league": "瑞超", "fixture_id": 1494197, "rank": (2, 10), "note": "赫根主胜略优但-1穿盘弱。"},
    "周一202": {"league": "瑞超", "fixture_id": 1494193, "rank": (8, 7), "note": "盖斯客胜略优，布鲁马波+1保护。"},
}


def poisson(lh: float, la: float, max_goals: int = 7) -> dict[str, float]:
    out = {}
    for h in range(max_goals + 1):
        ph = math.exp(-lh) * lh**h / math.factorial(h)
        for a in range(max_goals + 1):
            pa = math.exp(-la) * la**a / math.factorial(a)
            out[f"{h}-{a}"] = ph * pa
    s = sum(out.values())
    return {k: v / s for k, v in out.items()}


def result_dist(scores: dict[str, float]) -> dict[str, float]:
    out = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        out["home" if h > a else "away" if a > h else "draw"] += p
    return out


def hcap_dist(scores: dict[str, float], handicap: float) -> dict[str, float]:
    out = {"cover": 0.0, "push": 0.0, "fail": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        margin = h + handicap - a
        out["cover" if margin > 0 else "fail" if margin < 0 else "push"] += p
    return out


def total_dist(scores: dict[str, float]) -> dict[str, float]:
    out = {k: 0.0 for k in TOTAL_KEYS}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        t = h + a
        out["7_plus" if t >= 7 else str(t)] += p
    return out


def mean_total(d: dict[str, float]) -> float:
    return sum((7.5 if k == "7_plus" else float(k)) * v for k, v in d.items())


def fit_lambdas(market_result: dict[str, float], target_mean: float) -> tuple[float, float]:
    best = (99.0, 1.2, 1.2)
    for i in range(25, 380, 5):
        lh = i / 100
        for j in range(25, 380, 5):
            la = j / 100
            if abs((lh + la) - target_mean) > 0.55:
                continue
            rd = result_dist(poisson(lh, la, 6))
            err = sum((rd[k] - market_result[k]) ** 2 for k in ("home", "draw", "away")) + 0.18 * ((lh + la) - target_mean) ** 2
            if err < best[0]:
                best = (err, lh, la)
    return best[1], best[2]


def norm(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    return {k: v / s for k, v in d.items()} if s else d


def api_prediction_text(fixture_id: int) -> str:
    p = BASE / f"api/{fixture_id}_predictions.json"
    if not p.exists():
        return "API预测缺失"
    data = json.loads(p.read_text())
    if not data.get("response"):
        return "API预测无结果"
    pred = data["response"][0].get("predictions", {})
    winner = pred.get("winner") or {}
    return f"{winner.get('name', '-')}: {winner.get('comment', '-')}; {pred.get('advice', '-')}; {pred.get('percent', {})}"


def injury_count(fixture_id: int) -> int | str:
    p = BASE / f"api/{fixture_id}_injuries.json"
    if not p.exists():
        return "missing"
    data = json.loads(p.read_text())
    return data.get("results", 0)


def analyze(code: str, item: dict) -> dict:
    cur = item["current"]
    meta = META[code]
    one = MarketDewater.dewater_1x2({"home": cur["one_x_two"]["3"], "draw": cur["one_x_two"]["1"], "away": cur["one_x_two"]["0"]}, source="500实时")
    hcap = MarketDewater.dewater_handicap_3way({"home": cur["handicap_three_way"]["3"], "draw": cur["handicap_three_way"]["1"], "away": cur["handicap_three_way"]["0"]}, source="500让球")
    total = MarketDewater.dewater_total_goals_exact({k: cur["total_exact"]["7" if k == "7_plus" else k] for k in TOTAL_KEYS}, source="500总球")
    target_mean = mean_total(total.probabilities)
    lh, la = fit_lambdas(one.probabilities, target_mean)
    scores = poisson(lh, la)
    res = BayesianProbabilityFusion.fuse_3way(result_dist(scores), one.probabilities, market_type="result_3way", prior_strength=10, evidence_strength=12)
    hd = hcap_dist(scores, cur["handicap"])
    hres = BayesianProbabilityFusion.fuse_3way(hd, {"cover": hcap.probabilities["home"], "push": hcap.probabilities["draw"], "fail": hcap.probabilities["away"]}, market_type="handicap_3way", prior_strength=10, evidence_strength=12, keys=("cover", "push", "fail"))
    td = BayesianProbabilityFusion.fuse_3way(total_dist(scores), total.probabilities, market_type="total_goals_exact", prior_strength=9, evidence_strength=10, keys=TOTAL_KEYS)
    score_market = norm({s: 1 / v for s, v in cur["scores"].items() if isinstance(s, str) and s[:1].isdigit() and v})
    rows = []
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        side = "home" if h > a else "away" if a > h else "draw"
        tkey = "7_plus" if h + a >= 7 else str(h + a)
        blended = (0.58 * p + 0.42 * score_market.get(score, p))
        blended *= (0.75 + res.posterior_probabilities[side]) * (0.75 + td.posterior_probabilities[tkey])
        rows.append({"score": score, "probability": blended, "total_goals": h + a, "margin": h - a})
    rows = sorted(rows, key=lambda x: -x["probability"])[:10]
    return {
        "identity": {"code": code, "home": cur["home"], "away": cur["away"], "league": meta["league"], "fixture_id": meta["fixture_id"], "rank": meta["rank"], "note": meta["note"]},
        "market": {"one_x_two": one.to_dict(), "handicap_three_way": hcap.to_dict(), "total_exact": total.to_dict(), "deep": item.get("deep_market", {})},
        "api": {"prediction": api_prediction_text(meta["fixture_id"]), "injuries_results": injury_count(meta["fixture_id"])},
        "model": {"lambda": {"home": round(lh, 3), "away": round(la, 3)}, "target_total_mean": round(target_mean, 3)},
        "final": {"result": res.posterior_probabilities, "handicap_home_settlement": hres.posterior_probabilities, "total_distribution": td.posterior_probabilities, "total_mean": round(mean_total(td.posterior_probabilities), 3), "scorelines": rows},
        "audit": {"result_reliability": res.reliability, "result_max_deviation": res.max_deviation, "handicap_reliability": hres.reliability},
    }


def main() -> None:
    latest = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    ordered = [code for code in META if code in latest]
    out = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "pdf-20260705-all-v1",
        "notes": [
            "用户PDF可见12场全部纳入。",
            "500主表和深层欧亚大小已抓取；API-Football已抓取并审计。",
            "本全量报告采用市场去水、Poisson网格拟合、贝叶斯融合与比分市场融合。",
            "赔率变化层仍为phase1_shadow_mode，只影响风险标签，不直接改概率。",
        ],
        "matches": [analyze(code, latest[code]) for code in ordered],
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT_PATH), "summary": [{"code": m["identity"]["code"], "match": f"{m['identity']['home']}vs{m['identity']['away']}", "result": {k: round(v*100, 1) for k, v in m["final"]["result"].items()}, "hcap": {k: round(v*100, 1) for k, v in m["final"]["handicap_home_settlement"].items()}, "mean": m["final"]["total_mean"], "scores": [s["score"] for s in m["final"]["scorelines"][:5]]} for m in out["matches"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
