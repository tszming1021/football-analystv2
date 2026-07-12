from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.decision_iteration import DecisionIterationEngine, DecisionIterationFeatures
from core.market_dewater import MarketDewater


BASE = Path("data/worldcup_qf_20260710_12")
API = BASE / "api"
MARKET = BASE / "market/latest_market.json"
MODEL_OUT = BASE / "model_analysis.json"
REPORT_OUT = BASE / "2026-07-10-12_世界杯八强战_铁律分析报告.md"
TABLE_OUT = BASE / "2026-07-10-12_世界杯八强战_核心推荐总表.md"
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")


META = {
    "QF097": {
        "code": "周四097",
        "fixture_id": 1578539,
        "home": "法国",
        "away": "摩洛哥",
        "kickoff": "07-10 04:00",
        "venue": "Gillette Stadium, Boston",
        "source": "500完整市场+API赔率",
        "handicap": -1.0,
        "total_mean_prior": 2.55,
        "tags": ["knockout_90min_draw_risk", "low_block_opponent", "one_goal_margin_risk", "favorite_win_not_clean_sheet"],
        "note": "法国胜面强，但摩洛哥淘汰赛低位纪律强，-1让球层不支持深追。",
        "cold": ["1-1", "0-0", "2-2", "1-2"],
    },
    "QF098": {
        "code": "QF098",
        "fixture_id": 1581821,
        "home": "西班牙",
        "away": "比利时",
        "kickoff": "07-11 03:00",
        "venue": "SoFi Stadium, Los Angeles",
        "source": "API赔率均值；500未开售，市场层降权",
        "handicap": -1.0,
        "total_mean_prior": 2.60,
        "tags": ["knockout_90min_draw_risk", "elite_direct_rival", "one_goal_margin_risk", "favorite_win_not_clean_sheet"],
        "note": "西班牙控球和压迫更稳，比利时4-1淘汰美国后反击效率有上沿；胜面不等于穿盘。",
        "cold": ["1-1", "0-0", "2-2", "1-2"],
    },
    "QF099": {
        "code": "QF099",
        "fixture_id": 1581037,
        "home": "挪威",
        "away": "英格兰",
        "kickoff": "07-12 05:00",
        "venue": "Hard Rock Stadium, Miami",
        "source": "API赔率均值；500未开售，市场层降权",
        "handicap": 1.0,
        "total_mean_prior": 2.70,
        "tags": ["plus_one_cover_risk", "organized_transition_underdog", "set_piece_underdog_threat", "knockout_90min_draw_risk"],
        "note": "英格兰赔率优势明显，但挪威淘汰巴西说明转换和Haaland路径真实存在，+1保护强。",
        "cold": ["1-1", "2-2", "1-0", "2-1"],
    },
    "QF100": {
        "code": "QF100",
        "fixture_id": 1582681,
        "home": "阿根廷",
        "away": "瑞士",
        "kickoff": "07-12 09:00",
        "venue": "Kansas City Stadium",
        "source": "API预测；500/API赔率未开售，置信度最低",
        "handicap": -1.0,
        "total_mean_prior": 2.35,
        "tags": ["knockout_90min_draw_risk", "low_block_opponent", "one_goal_margin_risk", "strong_defense_opponent"],
        "note": "阿根廷名气和进攻上限占优，但刚3-2逆转消耗大；瑞士0-0淘汰哥伦比亚，低节奏和平局路径要优先。",
        "cold": ["1-1", "0-0", "2-2", "0-1"],
    },
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def api_percent(fid: int) -> dict[str, float]:
    data = load(API / f"{fid}_predictions.json")
    if not data.get("response"):
        return {"home": 0.45, "draw": 0.30, "away": 0.25}
    p = data["response"][0].get("predictions", {}).get("percent", {})
    out = {
        "home": float(str(p.get("home", "0")).rstrip("%")) / 100,
        "draw": float(str(p.get("draw", "0")).rstrip("%")) / 100,
        "away": float(str(p.get("away", "0")).rstrip("%")) / 100,
    }
    s = sum(out.values()) or 1
    return {k: v / s for k, v in out.items()}


def api_1x2_odds(fid: int) -> dict[str, float] | None:
    data = load(API / f"{fid}_odds.json")
    rows = []
    for item in data.get("response", []):
        for bm in item.get("bookmakers", []):
            for bet in bm.get("bets", []):
                if bet.get("name") == "Match Winner":
                    vals = {v["value"]: float(v["odd"]) for v in bet.get("values", [])}
                    if {"Home", "Draw", "Away"} <= set(vals):
                        rows.append(vals)
    if not rows:
        return None
    return {
        "home": sum(r["Home"] for r in rows) / len(rows),
        "draw": sum(r["Draw"] for r in rows) / len(rows),
        "away": sum(r["Away"] for r in rows) / len(rows),
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


def hcap_dist(scores: dict[str, float], line: float) -> dict[str, float]:
    out = {"cover": 0.0, "push": 0.0, "fail": 0.0}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        x = h + line - a
        out["cover" if x > 0 else "fail" if x < 0 else "push"] += p
    return out


def total_dist(scores: dict[str, float]) -> dict[str, float]:
    out = {k: 0.0 for k in TOTAL_KEYS}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        t = h + a
        out["7_plus" if t >= 7 else str(t)] += p
    return out


def mean_total(dist: dict[str, float]) -> float:
    return sum((7.5 if k == "7_plus" else float(k)) * v for k, v in dist.items())


def norm(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values()) or 1
    return {k: v / s for k, v in d.items()}


def fit_lambdas(target: dict[str, float], mean: float) -> tuple[float, float]:
    best = (99, 1.2, 1.1)
    for hi in range(30, 350, 5):
        lh = hi / 100
        for ai in range(30, 330, 5):
            la = ai / 100
            if abs(lh + la - mean) > 0.5:
                continue
            rd = result_dist(poisson(lh, la))
            err = sum((rd[k] - target[k]) ** 2 for k in target) + 0.18 * (lh + la - mean) ** 2
            if err < best[0]:
                best = (err, lh, la)
    return best[1], best[2]


def scorelines(scores: dict[str, float], result: dict[str, float], total: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        side = "home" if h > a else "away" if a > h else "draw"
        tk = "7_plus" if h + a >= 7 else str(h + a)
        prob = p * (0.72 + result[side]) * (0.72 + total[tk])
        rows.append({"score": score, "probability": prob, "home_goals": h, "away_goals": a, "total_goals": h + a, "margin": h - a})
    s = sum(r["probability"] for r in rows)
    for r in rows:
        r["probability"] /= s
    return sorted(rows, key=lambda x: x["probability"], reverse=True)


def market_probs(meta: dict[str, Any], market: dict[str, Any]) -> tuple[dict[str, float], float, str]:
    if meta["code"] == "周四097" and "周四097" in market.get("matches", {}):
        cur = market["matches"]["周四097"]["current"]
        one = MarketDewater.dewater_1x2({"home": cur["one_x_two"]["3"], "draw": cur["one_x_two"]["1"], "away": cur["one_x_two"]["0"]}).probabilities
        total = MarketDewater.dewater_total_goals_exact({k: cur["total_exact"]["7" if k == "7_plus" else k] for k in TOTAL_KEYS}).probabilities
        api = api_percent(meta["fixture_id"])
        blended = norm({k: 0.82 * one[k] + 0.18 * api[k] for k in one})
        return blended, mean_total(total), "500主表/总球完整 + API预测18%"
    odds = api_1x2_odds(meta["fixture_id"])
    api = api_percent(meta["fixture_id"])
    if odds:
        dewater = MarketDewater.dewater_1x2(odds).probabilities
        return norm({k: 0.70 * dewater[k] + 0.30 * api[k] for k in dewater}), meta["total_mean_prior"], "API赔率均值70% + API预测30%"
    return api, meta["total_mean_prior"], "仅API预测，低置信"


def apply_decision(meta: dict[str, Any], result: dict[str, float], hcap: dict[str, float], total: dict[str, float], rows: list[dict[str, Any]]) -> dict[str, Any]:
    fav, favp = max(result.items(), key=lambda kv: kv[1])
    vals = sorted(result.values(), reverse=True)
    f = DecisionIterationFeatures(
        match_id=meta["code"],
        home=meta["home"],
        away=meta["away"],
        competition_type="world_cup",
        stage="knockout",
        round_index=5,
        favorite_side=fav,
        favorite_win_prob=favp,
        favorite_edge=vals[0] - vals[1],
        handicap_line=meta["handicap"],
        handicap_cover=hcap["cover"],
        handicap_push=hcap["push"],
        handicap_fail=hcap["fail"],
        result_probabilities=result,
        handicap_probabilities=hcap,
        total_distribution=total,
        scorelines=rows[:12],
        tags=meta["tags"],
        high_scoring_risk=sum(total.get(k, 0) for k in ["4", "5", "6", "7_plus"]),
        volatility_score=0.70,
        lineup_uncertainty=True,
    )
    return DecisionIterationEngine().apply(f).to_dict()


def analyze() -> dict[str, Any]:
    market = load(MARKET)
    matches = []
    for meta in META.values():
        result, mean, source = market_probs(meta, market)
        lh, la = fit_lambdas(result, mean)
        raw = poisson(lh, la)
        hcap = hcap_dist(raw, meta["handicap"])
        total = total_dist(raw)
        rows = scorelines(raw, result, total)
        decision = apply_decision(meta, result, hcap, total, rows)
        matches.append({
            "identity": meta,
            "market_source": source,
            "lambda": {"home": round(lh, 3), "away": round(la, 3)},
            "before": {"result": result, "handicap": hcap, "total": total, "scorelines": rows[:8]},
            "decision_iteration": decision,
        })
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "matches": matches}


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def total_text(m: dict[str, Any]) -> str:
    d = m["decision_iteration"]["after_total_distribution"]
    low = d.get("0", 0) + d.get("1", 0) + d.get("2", 0)
    mid = d.get("2", 0) + d.get("3", 0)
    high = d.get("4", 0) + d.get("5", 0) + d.get("6", 0) + d.get("7_plus", 0)
    mean = mean_total(d)
    if low >= 0.50:
        return f"1-2球，防3球；均值{mean:.2f}"
    if high >= 0.34:
        return f"3-4球，防5球；均值{mean:.2f}"
    return f"2-3球，防4球；均值{mean:.2f}"


def pick(m: dict[str, Any]) -> tuple[str, float, str]:
    meta = m["identity"]
    r = m["decision_iteration"]["after_result"]
    h = m["decision_iteration"]["after_handicap"]
    if meta["code"] == "QF099":
        return "挪威+1让胜，防让平", h["cover"], pct(h["cover"] + h["push"])
    if meta["code"] in {"QF098", "QF100", "周四097"}:
        side, prob = max(r.items(), key=lambda kv: kv[1])
        name = meta["home"] if side == "home" else meta["away"] if side == "away" else "平局"
        return f"{name}胜" if side != "draw" else "平局", prob, pct(prob + r.get("draw", 0) if side != "draw" else prob)
    side, prob = max(r.items(), key=lambda kv: kv[1])
    return side, prob, pct(prob)


def top_scores(m: dict[str, Any], n: int = 3) -> str:
    return " / ".join(f"{s['score']}({pct(s['probability'])})" for s in m["decision_iteration"]["after_scorelines"][:n])


def render(model: dict[str, Any]) -> tuple[str, str]:
    rows = []
    for m in model["matches"]:
        meta = m["identity"]
        p, prob, cover = pick(m)
        r = m["decision_iteration"]["after_result"]
        h = m["decision_iteration"]["after_handicap"]
        line = meta["handicap"]
        htxt = f"{meta['home']}{line:+g}: {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])}"
        rows.append(f"| {meta['code']} {meta['home']}vs{meta['away']} | **{p}** | {pct(prob)} | {cover} | {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {htxt} | {total_text(m)} | {top_scores(m)} |")
    table = "\n".join([
        "# 2026世界杯八强战核心推荐总表",
        "",
        f"> 生成时间：{model['generated_at']}。097有500完整市场；098/099/100因500未开售，降权使用API赔率/预测。",
        "",
        "| 场次 | 主推 | 概率 | 保护覆盖 | 胜/平/负 | 让球胜/平/负 | 总球 | 比分Top3 |",
        "|---|---|---:|---:|---:|---:|---|---|",
        *rows,
    ]) + "\n"
    report = [
        "# 2026世界杯四场八强战铁律分析报告",
        "",
        f"> 数据截点：{model['generated_at']}；500仅开售097，后三场市场层降权。全部按90分钟常规时间，不含加时和点球。",
        "",
        "## 总推荐表",
        "",
        table,
        "## 单场要点",
        "",
    ]
    for m in model["matches"]:
        meta = m["identity"]
        p, prob, cover = pick(m)
        report += [
            f"### {meta['code']} {meta['home']} vs {meta['away']}",
            "",
            f"- **主推**：{p}，概率{pct(prob)}；保护覆盖{cover}。",
            f"- **数据层**：{m['market_source']}；proxy均值 {m['lambda']['home']:.2f}-{m['lambda']['away']:.2f}。",
            f"- **总球/比分**：{total_text(m)}；Top3 {top_scores(m)}。",
            f"- **决策迭代**：触发 {', '.join(m['decision_iteration']['applied_rules']) or '无'}。",
            f"- **判断**：{meta['note']}",
            "",
        ]
    report += [
        "## 执行摘要",
        "",
        "- 稳健方向：法国胜、西班牙胜、挪威+1保护。",
        "- 低置信方向：阿根廷vs瑞士，因500/API赔率未开售，只能按API预测和淘汰赛低节奏先验处理。",
        "- 总球最稳：阿根廷vs瑞士、法国vs摩洛哥偏1-2/2-3低中位；挪威vs英格兰防2-2和转换上沿。",
        "",
        "## 来源审计",
        "",
        "- 500竞彩：097主表、让球、比分、总球、半全场及深层欧赔/亚盘/大小球已读取。",
        "- API-Football：四场fixture/predictions/injuries/lineups/statistics/odds已请求；首发和技术统计赛前未开放。",
        "- Al Jazeera确认八强完整赛程；ESPN/FIFA赛程页作为交叉核验。",
    ]
    return "\n".join(report) + "\n", table


def main() -> None:
    model = analyze()
    MODEL_OUT.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    report, table = render(model)
    REPORT_OUT.write_text(report, encoding="utf-8")
    TABLE_OUT.write_text(table, encoding="utf-8")
    print(json.dumps({"model": str(MODEL_OUT), "report": str(REPORT_OUT), "table": str(TABLE_OUT), "summary": [
        {"match": f"{m['identity']['home']}vs{m['identity']['away']}", "pick": pick(m)[0], "total": total_text(m), "scores": [s["score"] for s in m["decision_iteration"]["after_scorelines"][:3]]}
        for m in model["matches"]
    ]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
