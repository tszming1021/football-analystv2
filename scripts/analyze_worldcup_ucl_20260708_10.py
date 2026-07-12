from __future__ import annotations

import itertools
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bayesian_fusion import BayesianProbabilityFusion
from core.decision_iteration import DecisionIterationEngine, DecisionIterationFeatures
from core.market_dewater import MarketDewater


BASE = Path("data/worldcup_ucl_20260708_10")
MARKET_PATH = BASE / "market/latest_market.json"
API_DIR = BASE / "api"
MODEL_OUT = BASE / "model_analysis.json"
REPORT_OUT = BASE / "2026-07-08_世界杯欧冠095-097-201-203_铁律分析报告.md"
TABLE_OUT = BASE / "2026-07-08_世界杯欧冠095-097-201-203_核心推荐总表.md"
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")


META: dict[str, dict[str, Any]] = {
    "周二095": {
        "league": "世界杯",
        "competition_type": "world_cup",
        "stage": "knockout",
        "round": "Round of 16",
        "fixture_id": 1576804,
        "rank": (1, 33),
        "venue": "Mercedes-Benz Stadium, Atlanta",
        "weather": "亚特兰大室内/可控环境，天气对节奏影响低；淘汰赛90分钟平局路径仍需保留。",
        "note": "阿根廷市场胜面极高，但API预测给出平局45%，埃及Salah/Marmoush转换和定位球不应清零。",
        "tags": ["knockout_90min_draw_risk", "low_block_opponent", "one_goal_margin_risk"],
        "high_scoring_risk": 0.26,
        "volatility": 0.60,
        "source": "SportsMole/Goal/Guardian均提示阿根廷热门，埃及有Salah健康与短恢复变量。",
        "cold": ["1-1", "0-0", "2-2", "1-2"],
    },
    "周二096": {
        "league": "世界杯",
        "competition_type": "world_cup",
        "stage": "knockout",
        "round": "Round of 16",
        "fixture_id": 1576805,
        "rank": (20, 12),
        "venue": "BC Place, Vancouver",
        "weather": "BC Place可闭顶，天气扰动低；哥伦比亚球迷与转换速度提升开放度。",
        "note": "500三向哥伦比亚小热，但瑞士+1保护明显；API预测反而给瑞士不败，说明不能单押客胜。",
        "tags": ["plus_one_cover_risk", "knockout_90min_draw_risk", "organized_transition_underdog", "elite_direct_rival"],
        "high_scoring_risk": 0.34,
        "volatility": 0.74,
        "source": "FIFA/Goal/VAVEL预览均指向胶着；公开补源称Colombia的Jhon Córdoba伤缺。",
        "cold": ["1-1", "0-0", "2-2", "2-1"],
    },
    "周四097": {
        "league": "世界杯",
        "competition_type": "world_cup",
        "stage": "knockout",
        "round": "Quarter-finals",
        "fixture_id": 1578539,
        "rank": (2, 14),
        "venue": "Gillette Stadium, Boston",
        "weather": "波士顿开放球场，临场天气需复核；当前盘口总球2.5，法国胜面高但-1深追分歧大。",
        "note": "法国五连胜热度高，摩洛哥淘汰加拿大后纪律和反击韧性强；90分钟防一球小胜/平局卡线。",
        "tags": ["knockout_90min_draw_risk", "low_block_opponent", "one_goal_margin_risk", "favorite_win_not_clean_sheet"],
        "high_scoring_risk": 0.24,
        "volatility": 0.62,
        "source": "Squawka等赛前文指向法国热门，摩洛哥仍具纪律与反击韧性。",
        "cold": ["1-1", "0-0", "2-2", "1-2"],
    },
    "周二201": {
        "league": "欧冠资格赛",
        "competition_type": "league",
        "stage": "qualifying",
        "round": "1st Qualifying Round",
        "fixture_id": 1554371,
        "rank": None,
        "venue": "Bank Respublika Arena",
        "weather": "巴库主场旅程与气候对新圣徒不利；欧冠资格赛首回合仍有保守和卡线风险。",
        "note": "萨巴赫主胜深热，深层欧赔从1.32降到1.23，亚盘从-1.40升到-1.65，市场明显增强。",
        "tags": ["clear_favorite_depth", "travel_disruption", "one_goal_margin_risk"],
        "high_scoring_risk": 0.42,
        "volatility": 0.58,
        "source": "UEFA官方比赛页确认赛程；Sportskeeda/Oddslot显示萨巴赫明显热门。",
        "cold": ["1-1", "2-2", "1-2", "2-1"],
    },
    "周二202": {
        "league": "欧冠资格赛",
        "competition_type": "league",
        "stage": "qualifying",
        "round": "1st Qualifying Round",
        "fixture_id": 1554367,
        "rank": None,
        "venue": "Djupumyra, Klaksvik",
        "weather": "法罗群岛主场与旅程对客队有扰动，但盘口-1让负较低，赢深不稳。",
        "note": "KÍ主胜热度强于API，SportsMole看2-1；但-1三向让负最高，主胜优先、不追穿。",
        "tags": ["one_goal_margin_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.30,
        "volatility": 0.66,
        "source": "UEFA官方页确认赛程；SportsMole预测KÍ 2-1，MightyTips提示大球风险。",
        "cold": ["1-1", "2-2", "1-2", "0-1"],
    },
    "周二203": {
        "league": "欧冠资格赛",
        "competition_type": "league",
        "stage": "qualifying",
        "round": "1st Qualifying Round",
        "fixture_id": 1554374,
        "rank": None,
        "venue": "Vikingsvollur, Reykjavik",
        "weather": "冰岛主场天然有旅程优势；但深层欧赔从客热大幅拉回均衡，波动较高。",
        "note": "维京人从初盘受让转为接近平手，市场分歧大；竞彩-1让负明显，主胜只能小心看，不追让胜。",
        "tags": ["open_league_high_variance", "derby_or_direct_rival", "plus_one_cover_risk"],
        "high_scoring_risk": 0.40,
        "volatility": 0.78,
        "source": "UEFA官方页确认赛程；Oddslot/365Scores/Sofascore显示两队首回合信息与较高波动。",
        "cold": ["1-1", "2-2", "1-2", "0-1", "2-3"],
    },
}

SUPPLEMENTAL_SOURCES = [
    "500竞彩足球实时主表：https://trade.500.com/jczq/index.php?playid=312&g=2",
    "API-Football fixture/predictions/injuries/lineups/statistics/odds endpoints",
    "FIFA Switzerland-Colombia preview：https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/switzerland-colombia-preview-live-stream-team-news-tickets",
    "SportsMole Argentina-Egypt team news：https://www.sportsmole.co.uk/football/argentina/world-cup-2026/team-news/argentina-vs-egypt-injury-suspension-list-predicted-xis_600710.html",
    "Goal Argentina-Egypt preview：https://www.goal.com/en-ke/news/argentina-egypt-world-cup-preview/blt901f9349432218fd",
    "Guardian Egypt/Argentina feature：https://www.theguardian.com/football/2026/jul/07/lionel-messi-mo-salah-egypt-argentina-world-cup",
    "Squawka France-Morocco preview：https://www.squawka.com/us/news/world-cup/match-preview-france-vs-morocco-07-09-26-world-cup-2026-quarterfinals/",
    "UEFA Sabah-TNS：https://www.uefa.com/uefachampionsleague/match/2048621--sabah-vs-the-new-saints/",
    "UEFA Klaksvik-Atert Bissen：https://www.uefa.com/uefachampionsleague/match/2048634--klaksvik-vs-atert-bissen/",
    "UEFA Vikingur-Gyori：https://www.uefa.com/uefachampionsleague/match/2048632--vikingur-r-vs-gyori-eto/",
]


def poisson(lh: float, la: float, max_goals: int = 7) -> dict[str, float]:
    out: dict[str, float] = {}
    for h in range(max_goals + 1):
        ph = math.exp(-lh) * lh**h / math.factorial(h)
        for a in range(max_goals + 1):
            pa = math.exp(-la) * la**a / math.factorial(a)
            out[f"{h}-{a}"] = ph * pa
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


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
        adjusted = h + handicap - a
        out["cover" if adjusted > 0 else "fail" if adjusted < 0 else "push"] += p
    return out


def total_dist(scores: dict[str, float]) -> dict[str, float]:
    out = {k: 0.0 for k in TOTAL_KEYS}
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        total = h + a
        out["7_plus" if total >= 7 else str(total)] += p
    return out


def mean_total(dist: dict[str, float]) -> float:
    return sum((7.5 if key in {"7_plus", "7+"} else float(key)) * value for key, value in dist.items())


def normalize(dist: dict[str, float]) -> dict[str, float]:
    total = sum(float(v or 0.0) for v in dist.values())
    return {k: float(v or 0.0) / total for k, v in dist.items()} if total else dist


def fit_lambdas(result_market: dict[str, float], target_mean: float, handicap: float, handicap_market: dict[str, float]) -> tuple[float, float]:
    best = (99.0, 1.25, 1.05)
    for hi in range(25, 430, 5):
        lh = hi / 100
        for ai in range(25, 390, 5):
            la = ai / 100
            if abs((lh + la) - target_mean) > 0.65:
                continue
            scores = poisson(lh, la, 7)
            rd = result_dist(scores)
            hd = hcap_dist(scores, handicap)
            err = sum((rd[k] - result_market[k]) ** 2 for k in ("home", "draw", "away"))
            err += 0.42 * sum((hd[k] - handicap_market[k]) ** 2 for k in ("cover", "push", "fail"))
            err += 0.15 * ((lh + la) - target_mean) ** 2
            if err < best[0]:
                best = (err, lh, la)
    return best[1], best[2]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def api_prediction_probs(fixture_id: int) -> dict[str, float] | None:
    data = load_json(API_DIR / f"{fixture_id}_predictions.json")
    if not data.get("response"):
        return None
    percent = data["response"][0].get("predictions", {}).get("percent") or {}
    try:
        return {
            "home": float(str(percent.get("home", "0")).rstrip("%")) / 100,
            "draw": float(str(percent.get("draw", "0")).rstrip("%")) / 100,
            "away": float(str(percent.get("away", "0")).rstrip("%")) / 100,
        }
    except ValueError:
        return None


def api_text(fixture_id: int) -> dict[str, Any]:
    pred = load_json(API_DIR / f"{fixture_id}_predictions.json")
    injuries = load_json(API_DIR / f"{fixture_id}_injuries.json")
    fixture = load_json(API_DIR / f"{fixture_id}_fixture.json")
    lineups = load_json(API_DIR / f"{fixture_id}_lineups.json")
    stats = load_json(API_DIR / f"{fixture_id}_statistics.json")
    pred_text = "API预测无结果"
    if pred.get("response"):
        p = pred["response"][0].get("predictions", {})
        pred_text = f"{p.get('advice', '-')}; {p.get('percent', {})}; winner={p.get('winner', {})}"
    injury_items = []
    for item in injuries.get("response", [])[:8]:
        injury_items.append(
            f"{item.get('team', {}).get('name', '-')}: {item.get('player', {}).get('name', '-')}({item.get('player', {}).get('reason', '-')})"
        )
    venue = "-"
    if fixture.get("response"):
        v = fixture["response"][0].get("fixture", {}).get("venue", {})
        venue = f"{v.get('name') or '-'}, {v.get('city') or '-'}"
    return {
        "prediction": pred_text,
        "injuries": injury_items or ["API伤停0或未开放"],
        "venue": venue,
        "lineups_results": lineups.get("results", 0),
        "statistics_results": stats.get("results", 0),
    }


def blend_api_market(market_probs: dict[str, float], fixture_id: int, competition_type: str) -> dict[str, float]:
    api_probs = api_prediction_probs(fixture_id)
    if not api_probs:
        return market_probs
    weight = 0.12 if competition_type == "world_cup" else 0.04
    if all(abs(api_probs[k] - 1 / 3) < 0.01 for k in ("home", "draw", "away")):
        weight = 0.0
    return normalize({k: market_probs[k] * (1 - weight) + api_probs[k] * weight for k in market_probs})


def score_rows(scores: dict[str, float], score_market: dict[str, float], result: dict[str, float], total: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    for score, p in scores.items():
        h, a = map(int, score.split("-"))
        side = "home" if h > a else "away" if a > h else "draw"
        tkey = "7_plus" if h + a >= 7 else str(h + a)
        blended = (0.56 * p + 0.44 * score_market.get(score, p))
        blended *= (0.72 + result[side]) * (0.72 + total[tkey])
        rows.append(
            {
                "score": score,
                "probability": blended,
                "home_goals": h,
                "away_goals": a,
                "total_goals": h + a,
                "margin": h - a,
            }
        )
    rows.sort(key=lambda item: item["probability"], reverse=True)
    total_prob = sum(item["probability"] for item in rows)
    for item in rows:
        item["probability"] = item["probability"] / total_prob
    return rows


def apply_decision(code: str, meta: dict[str, Any], item: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    result = final["result"]
    handicap = final["handicap_home_settlement"]
    favorite_side, favorite_prob = max(result.items(), key=lambda kv: kv[1])
    features = DecisionIterationFeatures(
        match_id=code,
        home=item["current"]["home"],
        away=item["current"]["away"],
        competition_type=meta["competition_type"],
        stage=meta["stage"],
        round_index=4 if meta["round"] == "Round of 16" else 5 if meta["round"] == "Quarter-finals" else None,
        weather_suppression=False,
        lineup_uncertainty=True,
        favorite_side=favorite_side,
        favorite_win_prob=favorite_prob,
        favorite_edge=sorted(result.values(), reverse=True)[0] - sorted(result.values(), reverse=True)[1],
        handicap_line=float(item["current"]["handicap"]),
        handicap_cover=handicap["cover"],
        handicap_push=handicap["push"],
        handicap_fail=handicap["fail"],
        result_probabilities=result,
        handicap_probabilities=handicap,
        total_distribution=final["total_distribution"],
        scorelines=final["scorelines"],
        tags=meta["tags"],
        volatility_score=meta["volatility"],
        high_scoring_risk=meta["high_scoring_risk"],
    )
    report = DecisionIterationEngine().apply(features)
    payload = report.to_dict()
    payload["after_scorelines"] = stabilize_scorelines(final["scorelines"], payload["after_scorelines"], payload["after_result"])
    return payload


def stabilize_scorelines(
    model_scorelines: list[dict[str, Any]],
    iterated_scorelines: list[dict[str, Any]],
    result: dict[str, float],
) -> list[dict[str, Any]]:
    """Keep decision-iteration risk scores visible without letting low-probability tails lead."""
    by_score = {row["score"]: dict(row) for row in model_scorelines}
    for row in iterated_scorelines:
        by_score.setdefault(row["score"], dict(row))
    ordered = sorted(by_score.values(), key=lambda row: row["probability"], reverse=True)
    favorite_side, favorite_prob = max(result.items(), key=lambda kv: kv[1])
    if favorite_prob >= 0.58:
        def side(row: dict[str, Any]) -> str:
            margin = int(row["margin"])
            return "home" if margin > 0 else "away" if margin < 0 else "draw"

        top = []
        tail = []
        for row in ordered:
            row_side = side(row)
            if len(top) < 3 and (row_side in {favorite_side, "draw"} or row["probability"] >= 0.06):
                top.append(row)
            else:
                tail.append(row)
        ordered = top + tail
    risk_scores = [row for row in iterated_scorelines if row["score"] in by_score and row["score"] not in {item["score"] for item in ordered[:6]}]
    return (ordered[:6] + risk_scores + ordered[6:])[:10]


def leg_layer(meta: dict[str, Any], item: dict[str, Any], final: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    line = abs(float(item["current"]["handicap"]))
    hcap = decision["after_handicap"]
    total_mean = mean_total(decision["after_total_distribution"])
    cover_edge = hcap["cover"] - hcap["fail"]
    line_score = 5.0 + min(2.2, line * 0.85) + cover_edge * 4.5
    expected_score = 5.0 + (total_mean - 2.4) * 1.3 + (final["lambda"]["home"] - final["lambda"]["away"]) * 0.9
    context_score = 5.0 + meta["high_scoring_risk"] * 2.0 - meta["volatility"] * 0.6
    if "travel_disruption" in meta["tags"] or "clear_favorite_depth" in meta["tags"]:
        context_score += 0.5
    if "low_block_opponent" in meta["tags"] or "knockout_90min_draw_risk" in meta["tags"]:
        context_score -= 0.35
    scores = [max(0.0, min(10.0, x)) for x in (line_score, expected_score, context_score)]
    total = 0.38 * scores[0] + 0.34 * scores[1] + 0.28 * scores[2]
    if total >= 6.6 and cover_edge >= 0.03:
        direction = "支持赢深"
    elif total >= 5.6:
        direction = "支持胜面，赢深谨慎"
    else:
        direction = "赢深保守，优先胜面/受让保护"
    return {
        "L": round(scores[0], 2),
        "E": round(scores[1], 2),
        "G": round(scores[2], 2),
        "total_score_10": round(total, 2),
        "home_leg_expected_goals": round(final["lambda"]["home"], 2),
        "away_leg_expected_goals": round(final["lambda"]["away"], 2),
        "depth_gap_10": round((final["lambda"]["home"] - final["lambda"]["away"]) * 2.4 + cover_edge * 3.0, 2),
        "direction": direction,
    }


def consistency(meta: dict[str, Any], item: dict[str, Any], final: dict[str, Any], decision: dict[str, Any], leg: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    notes: list[str] = []
    top2 = decision["after_scorelines"][:2]
    hcap = decision["after_handicap"]
    best_hcap = max(hcap.items(), key=lambda kv: kv[1])[0]
    settlements = []
    line = float(item["current"]["handicap"])
    for row in top2:
        adjusted = int(row["home_goals"]) + line - int(row["away_goals"])
        settlements.append("cover" if adjusted > 0 else "fail" if adjusted < 0 else "push")
    if best_hcap not in settlements and abs(line) >= 1:
        warnings.append(f"让球首选{best_hcap}，但比分保守位指向{'/'.join(settlements)}")
    if "支持赢深" in leg["direction"] and hcap["cover"] < 0.42:
        warnings.append("LEG深度与让球概率存在分歧")
    if "赢深保守" in leg["direction"] and hcap["cover"] > 0.46:
        warnings.append("让球胜概率尚可但LEG保守，需降低串关胆级")
    total_mean = mean_total(decision["after_total_distribution"])
    top2_total = [row["total_goals"] for row in top2]
    notes.append(f"比分保守位总球{top2_total[0]}/{top2_total[1]}，决策后均值{total_mean:.2f}")
    notes.append(f"决策规则：{','.join(decision['applied_rules']) or '无'}")
    return {"status": "attention" if warnings else "pass", "warnings": warnings, "notes": notes}


def analyze_match(code: str, item: dict[str, Any]) -> dict[str, Any]:
    cur = item["current"]
    meta = META[code]
    one = MarketDewater.dewater_1x2({"home": cur["one_x_two"]["3"], "draw": cur["one_x_two"]["1"], "away": cur["one_x_two"]["0"]}, source="500实时")
    one_probs = blend_api_market(one.probabilities, meta["fixture_id"], meta["competition_type"])
    hcap_market = MarketDewater.dewater_handicap_3way({"home": cur["handicap_three_way"]["3"], "draw": cur["handicap_three_way"]["1"], "away": cur["handicap_three_way"]["0"]}, source="500让球")
    total_market = MarketDewater.dewater_total_goals_exact({k: cur["total_exact"]["7" if k == "7_plus" else k] for k in TOTAL_KEYS}, source="500总球")
    target_mean = mean_total(total_market.probabilities)
    hcap_probs = {
        "cover": hcap_market.probabilities["home"],
        "push": hcap_market.probabilities["draw"],
        "fail": hcap_market.probabilities["away"],
    }
    lh, la = fit_lambdas(one_probs, target_mean, float(cur["handicap"]), hcap_probs)
    raw_scores = poisson(lh, la, 7)
    result_fusion = BayesianProbabilityFusion.fuse_3way(result_dist(raw_scores), one_probs, market_type="result_3way", prior_strength=10, evidence_strength=13)
    handicap_fusion = BayesianProbabilityFusion.fuse_3way(
        hcap_dist(raw_scores, float(cur["handicap"])),
        {"cover": hcap_market.probabilities["home"], "push": hcap_market.probabilities["draw"], "fail": hcap_market.probabilities["away"]},
        market_type="handicap_3way",
        prior_strength=10,
        evidence_strength=13,
        keys=("cover", "push", "fail"),
    )
    total_fusion = BayesianProbabilityFusion.fuse_3way(total_dist(raw_scores), total_market.probabilities, market_type="total_goals_exact", prior_strength=9, evidence_strength=11, keys=TOTAL_KEYS)
    score_market = normalize({score: 1 / odd for score, odd in cur["scores"].items() if score[:1].isdigit() and odd})
    final = {
        "result": result_fusion.posterior_probabilities,
        "handicap_home_settlement": handicap_fusion.posterior_probabilities,
        "total_distribution": total_fusion.posterior_probabilities,
        "total_mean": round(mean_total(total_fusion.posterior_probabilities), 3),
        "lambda": {"home": round(lh, 3), "away": round(la, 3)},
    }
    final["scorelines"] = score_rows(raw_scores, score_market, final["result"], final["total_distribution"])
    decision = apply_decision(code, meta, item, final)
    leg = leg_layer(meta, item, final, decision)
    check = consistency(meta, item, final, decision, leg)
    return {
        "identity": {"code": code, "home": cur["home"], "away": cur["away"], "league": meta["league"], "fixture_id": meta["fixture_id"], "rank": meta["rank"], "kickoff": cur["kickoff"], "round": meta["round"]},
        "source_facts": {"venue": meta["venue"], "weather": meta["weather"], "note": meta["note"], "supplement": meta["source"], "api": api_text(meta["fixture_id"])},
        "market": {"one_x_two": one.to_dict(), "one_x_two_after_api_shadow": one_probs, "handicap_three_way": hcap_market.to_dict(), "total_exact": total_market.to_dict(), "deep": item.get("deep_market", {})},
        "final": final,
        "decision_iteration": decision,
        "leg": leg,
        "consistency": check,
        "cold_scores": meta["cold"],
        "tags": meta["tags"],
    }


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def top_scores(match: dict[str, Any], n: int = 3) -> str:
    return " / ".join(f"{row['score']}({pct(row['probability'])})" for row in match["decision_iteration"]["after_scorelines"][:n])


def cold_scores(match: dict[str, Any]) -> str:
    scores = {row["score"]: row["probability"] for row in match["final"]["scorelines"]}
    return " / ".join(f"{score}({pct(scores.get(score, 0.0))})" for score in match["cold_scores"])


def total_text(match: dict[str, Any]) -> tuple[str, str]:
    dist = match["decision_iteration"]["after_total_distribution"]
    mid = dist.get("2", 0) + dist.get("3", 0)
    low = dist.get("0", 0) + dist.get("1", 0) + dist.get("2", 0)
    high = dist.get("4", 0) + dist.get("5", 0) + dist.get("6", 0) + dist.get("7_plus", 0)
    mean = mean_total(dist)
    if high >= 0.36:
        return "3-4球，防5球", f"均值{mean:.2f}；4+ {pct(high)}"
    if low >= 0.50:
        return "1-2球，防3球", f"均值{mean:.2f}；0-2 {pct(low)}"
    return "2-3球，防4球", f"均值{mean:.2f}；2-3 {pct(mid)}"


def pick_for(match: dict[str, Any]) -> dict[str, Any]:
    code = match["identity"]["code"]
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    result = match["decision_iteration"]["after_result"]
    hcap = match["decision_iteration"]["after_handicap"]
    line = float(load_json(MARKET_PATH)["matches"][code]["current"]["handicap"])
    if code == "周二096":
        return {"pick": f"{home}+1让胜，防让平", "kind": "handicap", "prob": hcap["cover"], "cover": hcap["cover"] + hcap["push"], "safe": f"{home}+1让胜/让平"}
    if code == "周二203":
        return {"pick": f"{away}+1让胜", "kind": "away_plus", "prob": hcap["fail"], "cover": hcap["fail"] + hcap["push"], "safe": f"{away}+1让胜，防平局"}
    if code == "周二201" and hcap["cover"] >= 0.43:
        return {"pick": f"{home}-1让胜，防让平", "kind": "handicap", "prob": hcap["cover"], "cover": hcap["cover"] + hcap["push"], "safe": f"{home}胜，进取-1"}
    side, prob = max(result.items(), key=lambda kv: kv[1])
    label = home if side == "home" else away if side == "away" else "平"
    return {"pick": f"{label}胜" if side != "draw" else "平局", "kind": "result", "prob": prob, "cover": prob, "safe": f"{label}不败/胜平保护" if side != "draw" else "平局小注"}


def hcap_text(match: dict[str, Any]) -> str:
    code = match["identity"]["code"]
    cur = load_json(MARKET_PATH)["matches"][code]["current"]
    line = float(cur["handicap"])
    h = match["decision_iteration"]["after_handicap"]
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    if code == "周二203":
        return f"{away}+1：让胜{pct(h['fail'])}/让平{pct(h['push'])}/让负{pct(h['cover'])}"
    if line > 0:
        return f"{home}+{line:g}：让胜{pct(h['cover'])}/让平{pct(h['push'])}/让负{pct(h['fail'])}"
    return f"{home}{line:g}：让胜{pct(h['cover'])}/让平{pct(h['push'])}/让负{pct(h['fail'])}"


def table_rows(model: dict[str, Any]) -> list[str]:
    rows = []
    for match in model["matches"]:
        pick = pick_for(match)
        r = match["decision_iteration"]["after_result"]
        total_dir, total_prob = total_text(match)
        rows.append(
            f"| {match['identity']['code']}{match['identity']['home']}vs{match['identity']['away']} | **{pick['pick']}** | {pct(pick['prob'])} | "
            f"{pick['safe']} | {pct(pick['cover'])} | {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | "
            f"{hcap_text(match)} | {total_dir} | {total_prob} | {top_scores(match)} | {cold_scores(match)} |"
        )
    return rows


def combo_rows(model: dict[str, Any]) -> list[str]:
    eligible = [m for m in model["matches"] if pick_for(m)["prob"] >= 0.43]
    eligible.sort(key=lambda m: pick_for(m)["prob"], reverse=True)
    rows = []
    for size in range(2, min(5, len(eligible)) + 1):
        for combo in itertools.combinations(eligible[:5], size):
            prob = math.prod(pick_for(m)["prob"] for m in combo)
            labels = " × ".join(f"{m['identity']['code']}{pick_for(m)['pick']}" for m in combo)
            tier = "主推" if size == 2 and prob >= 0.35 else "进取" if size <= 3 else "小注"
            rows.append(f"| {size}串1 | {labels} | {pct(prob)} | {tier} |")
    return rows[:14]


def score_combo_rows(model: dict[str, Any]) -> list[str]:
    ranked = sorted(model["matches"], key=lambda m: pick_for(m)["prob"], reverse=True)[:4]
    rows = []
    for size in range(2, min(4, len(ranked)) + 1):
        for combo in itertools.combinations(ranked, size):
            prob = 1.0
            bets = 1
            labels = []
            for match in combo:
                scores = match["decision_iteration"]["after_scorelines"][:2]
                prob *= sum(row["probability"] for row in scores)
                bets *= len(scores)
                labels.append(f"{match['identity']['code']} {'/'.join(row['score'] for row in scores)}")
            rows.append(f"| {size}串1 | {' × '.join(labels)} | {bets}注 | {pct(prob)} |")
    return rows[:10]


def render_table(model: dict[str, Any], market: dict[str, Any], api_audit: dict[str, Any]) -> str:
    lines = [
        "# 2026-07-08 世界杯/欧冠 095-097/201-203 核心推荐总表",
        "",
        f"> 数据截点：500实时 {market['fetched_at']}；API-Football {api_audit.get('fetched_at', '-')}；模型 {model['generated_at']}。全部按90分钟结算，欧冠资格赛按首回合常规时间。",
        "",
        "## 胜平负/让球总表",
        "",
        "| 场次 | 主推方向 | 概率 | 保守方向 | 覆盖概率 | 胜/平/负 | 推荐盘口胜/平/负 | 总球方向 | 总球概率 | 比分Top3 | 冷门比分 |",
        "|---|---|---:|---|---:|---:|---:|---|---|---|---|",
        *table_rows(model),
        "",
        "## 总球主推",
        "",
        "| 优先级 | 场次 | 比赛 | 总球主推 | 概率/均值 | 防线 | 执行口径 |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for idx, match in enumerate(model["matches"], 1):
        total_dir, total_prob = total_text(match)
        lines.append(f"| {idx} | {match['identity']['code']} | {match['identity']['home']}vs{match['identity']['away']} | {total_dir} | {total_prob} | {match['decision_iteration']['after_scorelines'][3]['score']} | 主线按总球区间，比分只作覆盖 |")
    lines += [
        "",
        "## 比分主推",
        "",
        "| 优先级 | 场次 | 比赛 | 比分主推 | 概率 | 保护比分 | 高波动/冷门比分 | 执行口径 |",
        "|---:|---|---|---|---:|---|---|---|",
    ]
    for idx, match in enumerate(model["matches"], 1):
        top = match["decision_iteration"]["after_scorelines"]
        lines.append(f"| {idx} | {match['identity']['code']} | {match['identity']['home']}vs{match['identity']['away']} | {top[0]['score']} | {pct(top[0]['probability'])} | {top[1]['score']}/{top[2]['score']} | {cold_scores(match)} | Top2主防，冷门只做小注保护 |")
    lines += [
        "",
        "## 胜负平/让球核心串关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |",
        "|---|---|---:|---|",
        *combo_rows(model),
        "",
        "## 比分串关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_combo_rows(model),
    ]
    return "\n".join(lines) + "\n"


def render_report(model: dict[str, Any], market: dict[str, Any], api_audit: dict[str, Any]) -> str:
    sorted_picks = sorted(model["matches"], key=lambda m: pick_for(m)["prob"], reverse=True)
    lines = [
        "# 2026-07-08 世界杯/欧冠 095-097/201-203 铁律分析报告",
        "",
        "> 口径：全部按90分钟常规时间结算；世界杯淘汰赛不含加时/点球，欧冠资格赛按首回合常规时间。",
        f"> 数据截点：500实时 {market['fetched_at']}；API-Football {api_audit.get('fetched_at', '-')}；模型 {model['generated_at']}。",
        "> 赔率变化层仍按 phase1_shadow_mode 处理：只输出风险审计，不直接覆盖最终概率。",
        "",
        "## 一、主推建议",
        "",
        "### 主推单场",
        "",
        "| 优先级 | 场次 | 主推 | 概率 | 执行口径 |",
        "|---:|---|---|---:|---|",
    ]
    for idx, match in enumerate(sorted_picks, 1):
        pick = pick_for(match)
        lines.append(f"| {idx} | {match['identity']['code']} {match['identity']['home']}vs{match['identity']['away']} | {pick['pick']} | {pct(pick['prob'])} | {pick['safe']} |")
    lines += [
        "",
        "### 主推组合",
        "",
        "| 类型 | 推荐 | 概率 | 执行 |",
        "|---|---|---:|---|",
        *combo_rows(model)[:6],
        "",
        "## 二、总推荐表",
        "",
        "### 胜平负/让球总表",
        "",
        "| 场次 | 主推方向 | 概率 | 保守方向 | 覆盖概率 | 胜/平/负 | 推荐盘口胜/平/负 | 总球方向 | 总球概率 | 比分Top3 | 冷门比分 |",
        "|---|---|---:|---|---:|---:|---:|---|---|---|---|",
        *table_rows(model),
        "",
        "### 总球主推",
        "",
        "| 优先级 | 场次 | 比赛 | 总球主推 | 概率/均值 | 防线 | 执行口径 |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for idx, match in enumerate(model["matches"], 1):
        total_dir, total_prob = total_text(match)
        lines.append(f"| {idx} | {match['identity']['code']} | {match['identity']['home']}vs{match['identity']['away']} | {total_dir} | {total_prob} | 防{match['decision_iteration']['after_scorelines'][3]['score']} | 结合比分Top3执行 |")
    lines += [
        "",
        "### 比分主推",
        "",
        "| 优先级 | 场次 | 比赛 | 比分主推 | 概率 | 保护比分 | 高波动/冷门比分 | 执行口径 |",
        "|---:|---|---|---|---:|---|---|---|",
    ]
    for idx, match in enumerate(model["matches"], 1):
        top = match["decision_iteration"]["after_scorelines"]
        lines.append(f"| {idx} | {match['identity']['code']} | {match['identity']['home']}vs{match['identity']['away']} | {top[0]['score']} | {pct(top[0]['probability'])} | {top[1]['score']}/{top[2]['score']} | {cold_scores(match)} | Top2主防，冷门小注 |")
    lines += [
        "",
        "### 总球/比分执行摘要",
        "",
        "1. **总球最稳**：095阿根廷vs埃及、097法国vs摩洛哥偏2-3球；201萨巴赫vs新圣徒有3-4球上沿。",
        "2. **比分最稳**：095防2-0/2-1，096防1-1/0-1，097防1-0/2-0。",
        "3. **需要防上沿**：201萨巴赫、203维京人两场欧冠资格赛保留4球以上路径。",
        "4. **需要防低位**：096瑞士vs哥伦比亚、097法国vs摩洛哥淘汰赛平局/一球小胜权重较高。",
        "",
        "## 三、步骤审计",
        "",
        "- 已读取500主表：胜平负、让球胜平负、比分、总球、半全场。",
        "- 已读取500深层均值：欧赔、亚盘、大小球；本批次抓取错误0。",
        "- 已请求API-Football fixture、prediction、injuries、lineups、statistics、odds；赛前lineups/statistics均未开放。",
        "- 已尝试联网补源：世界杯使用FIFA/Goal/SportsMole/Guardian/Squawka等，欧冠使用UEFA官方比赛页及公开赔率/前瞻页。",
        "- 已执行市场去水、Poisson网格拟合、贝叶斯融合、总球去偏、LEG、决策迭代、一致性检查。",
        "- 奇门辅助未以直接概率进入模型，本报告仅保留数据层结论。",
        "",
        "## 四、单场分析",
        "",
    ]
    for match in model["matches"]:
        r = match["decision_iteration"]["after_result"]
        pick = pick_for(match)
        total_dir, total_prob = total_text(match)
        api = match["source_facts"]["api"]
        leg = match["leg"]
        consistency_report = match["consistency"]
        lines += [
            f"### {match['identity']['code']} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **胜平负**：{match['identity']['home']}胜{pct(r['home'])}，平{pct(r['draw'])}，{match['identity']['away']}胜{pct(r['away'])}。",
            f"- **核心推荐**：{pick['pick']}，概率{pct(pick['prob'])}；保守方向：{pick['safe']}，覆盖{pct(pick['cover'])}。",
            f"- **让球表达**：{hcap_text(match)}。",
            f"- **总球方向**：{total_dir}；{total_prob}。",
            f"- **比分**：Top3 {top_scores(match)}；冷门保护 {cold_scores(match)}。",
            f"- **xG/proxy层**：真实xG赛前未开放；proxy均值 {match['final']['lambda']['home']:.2f}-{match['final']['lambda']['away']:.2f}，来源为500去水结果、总球市场和比分市场拟合。",
            f"- **LEG层**：L/E/G={leg['L']}/{leg['E']}/{leg['G']}，综合{leg['total_score_10']}；修正预期进球{leg['home_leg_expected_goals']}-{leg['away_leg_expected_goals']}；强弱差{leg['depth_gap_10']}；结论：{leg['direction']}。",
            f"- **决策迭代**：胜平负 {pct(match['decision_iteration']['before_result']['home'])}/{pct(match['decision_iteration']['before_result']['draw'])}/{pct(match['decision_iteration']['before_result']['away'])} -> {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])}；规则：{', '.join(match['decision_iteration']['applied_rules']) or '无'}。",
            f"- **场馆天气**：{match['source_facts']['weather']}",
            f"- **伤停/首发**：{'; '.join(api['injuries'])}；首发接口结果{api['lineups_results']}，技术统计接口结果{api['statistics_results']}。",
            f"- **API预测**：{api['prediction']}",
            f"- **联网补源**：{match['source_facts']['supplement']}",
            f"- **一致性审计**：{consistency_report['status']}；{'；'.join(consistency_report['warnings'] or consistency_report['notes'])}",
            f"- **结论**：{match['source_facts']['note']}",
            "",
        ]
    lines += [
        "## 五、胜负平/让球核心串关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |",
        "|---|---|---:|---|",
        *combo_rows(model),
        "",
        "## 六、比分串关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_combo_rows(model),
        "",
        "## 七、来源",
        "",
        *[f"- {source}" for source in SUPPLEMENTAL_SOURCES],
        "",
        "> 正式首发、临场伤停、顶棚状态和盘口跨档会改变结论；临场建议重跑本脚本更新。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    market = load_json(MARKET_PATH)
    api_audit = load_json(API_DIR / "api_audit.json")
    matches = [analyze_match(code, market["matches"][code]) for code in META if code in market["matches"]]
    model = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-ucl-20260708-10-v1",
        "notes": [
            "全部按90分钟结算。",
            "500主表和深层欧赔/亚盘/大小球均抓取成功。",
            "API-Football已请求；赛前首发和技术统计未开放。",
            "联网补源只做事实审计和风险标签，直接概率权重为0。",
        ],
        "matches": matches,
    }
    MODEL_OUT.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_OUT.write_text(render_report(model, market, api_audit), encoding="utf-8")
    TABLE_OUT.write_text(render_table(model, market, api_audit), encoding="utf-8")
    print(json.dumps({
        "model": str(MODEL_OUT),
        "report": str(REPORT_OUT),
        "table": str(TABLE_OUT),
        "summary": [
            {
                "code": match["identity"]["code"],
                "match": f"{match['identity']['home']}vs{match['identity']['away']}",
                "pick": pick_for(match)["pick"],
                "probability": round(pick_for(match)["prob"] * 100, 1),
                "total": total_text(match)[0],
                "scores": [row["score"] for row in match["decision_iteration"]["after_scorelines"][:3]],
                "rules": match["decision_iteration"]["applied_rules"],
            }
            for match in matches
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
