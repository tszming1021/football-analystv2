from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from core.bayesian_fusion import BayesianProbabilityFusion
from core.decision_iteration import DecisionIterationEngine, DecisionIterationFeatures
from core.leg_model import LEGModel
from core.market_dewater import MarketDewater
from core.math_models import PoissonModel
from core.model_consistency import ModelConsistencyChecker
from core.multi_source_fusion import FusionSource, MultiSourceProbabilityFusion
from core.qimen_assistant import QimenAssistant
from core.worldcup_trained_model import WorldCupTrainedModel
from core.xg_proxy_model import PreMatchXGProxyModel


OUT_PATH = Path("data/worldcup_20260621/model_analysis_1847.json")
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7_plus")


MATCHES = [
    {
        "code": "周六033",
        "home": "荷兰",
        "away": "瑞典",
        "home_en": "Netherlands",
        "away_en": "Sweden",
        "kickoff": "2026-06-21T01:00:00+08:00",
        "fixture_id": 1539007,
        "venue": "NRG Stadium, Houston",
        "rank": (8, 38),
        "recent": ((10, 23, 9), (10, 16, 19)),
        "first_round": "荷兰2-2日本；瑞典5-1突尼斯",
        "market_1x2": (1.53, 3.83, 4.65),
        "market_1x2_source": "500竞彩官方",
        "handicap": -1.0,
        "handicap_3way": (2.72, 3.28, 2.19),
        "total_exact": (16.00, 6.25, 3.70, 3.30, 4.85, 7.80, 14.00, 19.00),
        "score_prices": {
            "1-0": 8.50, "2-0": 8.40, "2-1": 5.40, "3-0": 13.00, "3-1": 10.50,
            "3-2": 16.00, "4-0": 27.00, "4-1": 22.00, "4-2": 35.00, "0-0": 16.00,
            "1-1": 6.80, "2-2": 12.50, "3-3": 38.00, "0-1": 17.00, "0-2": 28.00,
            "1-2": 15.00, "0-3": 80.00, "1-3": 45.00, "2-3": 38.00,
        },
        "market_total_line": 2.76,
        "asian_line": -0.719,
        "weather": "Houston 12:00，29.7C、湿度80%、雷暴代码95；NRG可闭合顶棚，按场地缓释处理",
        "weather_suppression": False,
        "material_absence_team": "home",
        "absence_note": "荷兰中场Quinten Timber因脑震荡/训练伤确认缺席；其余首发未确认",
        "group_direct_rivalry": True,
        "tags": ["organized_transition_underdog", "comeback_equalizer_risk", "open_league_high_variance"],
        "high_scoring_risk": 0.28,
        "volatility": 0.67,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.04, 0.03),
        "proxy_weight": 0.60,
        "forced_scores": ["1-1", "2-2", "2-1", "1-2", "3-2", "2-3", "3-1"],
    },
    {
        "code": "周六034",
        "home": "德国",
        "away": "科特迪瓦",
        "home_en": "Germany",
        "away_en": "Ivory Coast",
        "kickoff": "2026-06-21T04:00:00+08:00",
        "fixture_id": 1489393,
        "venue": "BMO Field, Toronto",
        "rank": (9, 37),
        "recent": ((10, 35, 7), (10, 20, 7)),
        "first_round": "德国7-1库拉索；科特迪瓦1-0厄瓜多尔",
        "market_1x2": (1.34, 4.70, 5.90),
        "market_1x2_source": "500竞彩官方",
        "handicap": -1.0,
        "handicap_3way": (2.04, 3.82, 2.65),
        "total_exact": (19.00, 6.75, 4.00, 3.30, 4.40, 7.50, 12.50, 17.00),
        "score_prices": {
            "1-0": 8.50, "2-0": 7.25, "2-1": 6.40, "3-0": 8.70, "3-1": 8.25,
            "3-2": 20.00, "4-0": 19.00, "4-1": 18.00, "4-2": 40.00, "0-0": 19.00,
            "1-1": 8.50, "2-2": 14.00, "3-3": 40.00, "0-1": 20.00, "0-2": 42.00,
            "1-2": 18.00, "0-3": 110.00, "1-3": 55.00, "2-3": 55.00,
        },
        "market_total_line": 2.90,
        "asian_line": -0.984,
        "weather": "Toronto 16:00，19.3C、湿度59%、降水4%、风速25.2km/h",
        "weather_suppression": False,
        "material_absence_team": "",
        "absence_note": "API伤停/首发端点0行；Transfermarkt未列缺席，但不能视作官方确认全员可用",
        "group_direct_rivalry": False,
        "tags": ["organized_transition_underdog", "set_piece_underdog_threat"],
        "high_scoring_risk": 0.24,
        "volatility": 0.62,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.05, 0.04),
        "proxy_weight": 0.60,
        "forced_scores": ["1-1", "2-1", "2-0", "3-1", "3-0", "0-1", "2-2", "4-1"],
    },
    {
        "code": "周六035",
        "home": "厄瓜多尔",
        "away": "库拉索",
        "home_en": "Ecuador",
        "away_en": "Curaçao",
        "kickoff": "2026-06-21T08:00:00+08:00",
        "fixture_id": 1489392,
        "venue": "Arrowhead Stadium, Kansas City",
        "rank": (23, 82),
        "recent": ((10, 12, 6), (10, 20, 21)),
        "first_round": "厄瓜多尔0-1科特迪瓦；库拉索1-7德国",
        "market_1x2": (1.12, 8.93, 22.01),
        "market_1x2_source": "500百家即时均值（竞彩三向未开售）",
        "handicap": -2.0,
        "handicap_3way": (1.85, 4.00, 2.95),
        "total_exact": (22.00, 7.30, 4.20, 3.50, 4.30, 6.75, 11.00, 13.00),
        "score_prices": {
            "1-0": 7.70, "2-0": 4.30, "2-1": 10.50, "3-0": 4.60, "3-1": 9.00,
            "3-2": 50.00, "4-0": 8.20, "4-1": 16.00, "4-2": 60.00, "5-0": 13.50,
            "5-1": 30.00, "5-2": 100.00, "0-0": 22.00, "1-1": 16.00, "2-2": 50.00,
            "3-3": 150.00, "0-1": 50.00, "0-2": 150.00, "1-2": 60.00, "0-3": 600.00,
            "1-3": 350.00, "2-3": 200.00,
        },
        "market_total_line": 3.04,
        "asian_line": -2.281,
        "weather": "Kansas City 19:00，29.1C、湿度47%、降水11%、风速12.6km/h",
        "weather_suppression": False,
        "material_absence_team": "",
        "absence_note": "API伤停/首发端点0行；Transfermarkt双方均未列缺席",
        "group_direct_rivalry": False,
        "tags": ["massive_favorite_depth", "defensive_collapse_risk", "low_block_opponent"],
        "high_scoring_risk": 0.38,
        "volatility": 0.70,
        "favorite_cover_trigger": True,
        "lambda_context": (0.27, -0.10),
        "proxy_weight": 0.72,
        "forced_scores": ["2-0", "3-0", "4-0", "5-0", "3-1", "4-1", "1-0", "2-1", "1-1", "0-1", "2-2", "5-1"],
    },
    {
        "code": "周六036",
        "home": "突尼斯",
        "away": "日本",
        "home_en": "Tunisia",
        "away_en": "Japan",
        "kickoff": "2026-06-21T12:00:00+08:00",
        "fixture_id": 1489394,
        "venue": "Estadio BBVA, Monterrey",
        "rank": (41, 15),
        "recent": ((10, 12, 17), (10, 15, 8)),
        "first_round": "突尼斯1-5瑞典；日本2-2荷兰",
        "market_1x2": (6.36, 3.95, 1.39),
        "market_1x2_source": "500竞彩官方",
        "handicap": 1.0,
        "handicap_3way": (2.54, 3.54, 2.21),
        "total_exact": (11.00, 4.40, 3.20, 3.50, 5.95, 11.00, 21.00, 32.00),
        "score_prices": {
            "1-0": 14.00, "2-0": 38.00, "2-1": 22.00, "3-0": 120.00, "3-1": 90.00,
            "3-2": 80.00, "0-0": 11.00, "1-1": 7.50, "2-2": 19.00, "3-3": 90.00,
            "0-1": 6.40, "0-2": 5.45, "1-2": 5.80, "0-3": 9.50, "1-3": 9.50,
            "2-3": 29.00,
        },
        "market_total_line": 2.31,
        "asian_line": 0.969,
        "weather": "Monterrey 22:00，24.4C、湿度85%、降水13%、风速8.3km/h",
        "weather_suppression": False,
        "material_absence_team": "",
        "absence_note": "API伤停/首发端点0行；Transfermarkt双方均未列缺席；突尼斯赛前更换主教练",
        "group_direct_rivalry": False,
        "tags": ["home_defensive_leak", "away_depth_upside", "plus_one_cover_risk", "low_block_opponent"],
        "high_scoring_risk": 0.18,
        "volatility": 0.73,
        "favorite_cover_trigger": False,
        "lambda_context": (-0.08, 0.12),
        "proxy_weight": 0.65,
        "forced_scores": ["0-1", "0-2", "1-1", "1-2", "0-3", "1-3", "2-2", "1-0", "2-1", "2-3"],
    },
]


def normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value)) for value in values.values()) or 1.0
    return {key: max(0.0, float(value)) / total for key, value in values.items()}


def total_bucket(home: int, away: int) -> str:
    total = home + away
    return "7_plus" if total >= 7 else str(total)


def outcome_bucket(home: int, away: int) -> str:
    return "home" if home > away else ("draw" if home == away else "away")


def settlement_bucket(home: int, away: int, line: float) -> str:
    value = home + line - away
    return "cover" if value > 0 else ("push" if abs(value) < 1e-9 else "fail")


def distribution_from_scores(scores: dict[tuple[int, int], float], bucket_fn, keys) -> dict[str, float]:
    result = {key: 0.0 for key in keys}
    for score, probability in scores.items():
        result[bucket_fn(*score)] += probability
    return normalize(result)


def score_market_blend(scores: dict[tuple[int, int], float], prices: dict[str, float]) -> dict[tuple[int, int], float]:
    listed = {}
    for label, price in prices.items():
        home, away = (int(value) for value in label.split("-"))
        listed[(home, away)] = 1.0 / price
    market_conditional = normalize(listed)
    model_conditional = normalize({score: scores.get(score, 0.0) for score in listed})
    adjusted = dict(scores)
    for score, market_probability in market_conditional.items():
        model_probability = max(model_conditional.get(score, 0.0), 1e-9)
        adjusted[score] *= (market_probability / model_probability) ** 0.18
    return normalize(adjusted)


def ipf(scores: dict[tuple[int, int], float], result_target: dict[str, float], total_target: dict[str, float]) -> dict[tuple[int, int], float]:
    fitted = normalize(scores)
    for _ in range(40):
        current_result = distribution_from_scores(fitted, outcome_bucket, ("home", "draw", "away"))
        for score in fitted:
            fitted[score] *= result_target[outcome_bucket(*score)] / max(current_result[outcome_bucket(*score)], 1e-9)
        fitted = normalize(fitted)
        current_total = distribution_from_scores(fitted, total_bucket, TOTAL_KEYS)
        for score in fitted:
            fitted[score] *= total_target[total_bucket(*score)] / max(current_total[total_bucket(*score)], 1e-9)
        fitted = normalize(fitted)
    return fitted


def score_item(score: tuple[int, int], probability: float) -> dict:
    home, away = score
    return {
        "score": f"{home}-{away}",
        "probability": round(probability, 6),
        "home_goals": home,
        "away_goals": away,
        "margin": home - away,
        "total_goals": home + away,
    }


def candidate_pool(scores: dict[tuple[int, int], float], forced: list[str]) -> list[dict]:
    selected = [score for score, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:14]]
    for label in forced:
        score = tuple(int(value) for value in label.split("-"))
        if score not in selected:
            selected.append(score)
    return [score_item(score, scores.get(score, 0.0)) for score in selected]


def audit_scoreline_tiers(scorelines: list[dict], favorite: str, favorite_probability: float, line: float) -> list[dict]:
    """Keep decision adjustments, then enforce the report tier contract."""
    pool = [dict(item) for item in scorelines]
    by_probability = sorted(pool, key=lambda item: item["probability"], reverse=True)
    chosen: list[dict] = []

    def take(predicate) -> None:
        for item in by_probability:
            if item in chosen or not predicate(item):
                continue
            chosen.append(item)
            return

    # The engine's first two are the conservative tier; retain them exactly.
    for item in pool[:2]:
        if item not in chosen:
            chosen.append(item)

    favorite_test = (lambda item: item["margin"] > 0) if favorite == "home" else (lambda item: item["margin"] < 0)
    take(
        lambda item: favorite_test(item)
        and abs(item["margin"]) == 1
        and item["home_goals"] > 0
        and item["away_goals"] > 0
        and item["probability"] >= 0.085
    )
    if favorite == "home" and 0.42 <= favorite_probability <= 0.56 and abs(line) >= 1.0:
        take(
            lambda item: item["margin"] > 0
            and item["away_goals"] == 0
            and item["total_goals"] in {1, 2}
            and item["probability"] >= 0.09
        )
    if 0.48 <= favorite_probability <= 0.62 and abs(line) >= 1.0:
        take(
            lambda item: favorite_test(item)
            and abs(item["margin"]) == 1
            and item["home_goals"] > 0
            and item["away_goals"] > 0
            and item["probability"] >= 0.055
        )
    if favorite_probability >= 0.68 and abs(line) >= 1.75:
        required_margin = int(math.floor(abs(line))) + 1
        take(lambda item: favorite_test(item) and abs(item["margin"]) >= required_margin)
        take(lambda item: favorite_test(item) and item["away_goals"] == 0 and abs(item["margin"]) >= 2 and item["probability"] >= 0.07)
        take(lambda item: favorite_test(item) and item["away_goals"] == 0 and abs(item["margin"]) >= 3 and item["probability"] >= 0.06)
        take(lambda item: favorite_test(item) and item["total_goals"] >= 4)
        take(lambda item: favorite_test(item) and item["away_goals"] > 0 and item["total_goals"] >= 4)
    elif favorite_probability >= 0.60 or abs(line) >= 1.0:
        take(lambda item: favorite_test(item) and item["away_goals"] == 0 and abs(item["margin"]) >= 2 and item["probability"] >= 0.07)
        take(lambda item: favorite_test(item) and item["away_goals"] == 0 and abs(item["margin"]) >= 3 and item["probability"] >= 0.06)
        take(
            lambda item: favorite_test(item)
            and (
                (abs(item["margin"]) >= 2 and item["total_goals"] >= 3)
                or item["total_goals"] >= 4
            )
            and item["probability"] >= 0.04
        )
        take(lambda item: item["margin"] == 0 and item["total_goals"] >= 2)
        take(lambda item: favorite_test(item) and item["total_goals"] >= 4 and item["probability"] >= 0.04)
    else:
        take(favorite_test)
        take(lambda item: item["margin"] == 0 and item["total_goals"] >= 2)
        take(lambda item: favorite_test(item) and item["total_goals"] >= 4)

    for item in pool:
        if len(chosen) >= 7:
            break
        if item not in chosen:
            chosen.append(item)

    for rank, item in enumerate(chosen, start=1):
        item["consistency_audit_rank"] = rank
        item["consistency_audit_tier"] = "conservative" if rank <= 2 else "risk"
    return chosen


def exact_mean(distribution: dict[str, float]) -> float:
    return sum((7.5 if key == "7_plus" else float(key)) * value for key, value in distribution.items())


def make_stats(values: tuple[int, int, int], xg_values: tuple[float, float] | None = None) -> SimpleNamespace:
    matches, goals_for, goals_against = values
    xg, xga = xg_values if xg_values is not None else (None, None)
    return SimpleNamespace(matches_played=matches, goals_for=goals_for, goals_against=goals_against, xg=xg, xga=xga)


def map_favorite_handicap(home_settlement: dict[str, float], favorite: str) -> dict[str, float]:
    if favorite == "home":
        return dict(home_settlement)
    return {"cover": home_settlement["fail"], "push": home_settlement["push"], "fail": home_settlement["cover"]}


def map_home_handicap(favorite_settlement: dict[str, float], favorite: str) -> dict[str, float]:
    if favorite == "home":
        return dict(favorite_settlement)
    return {"cover": favorite_settlement["fail"], "push": favorite_settlement["push"], "fail": favorite_settlement["cover"]}


def analyze_match(match: dict, trained: WorldCupTrainedModel) -> dict:
    one_x_two = MarketDewater.dewater_1x2(
        {"home": match["market_1x2"][0], "draw": match["market_1x2"][1], "away": match["market_1x2"][2]},
        source=match["market_1x2_source"],
    )
    handicap_market = MarketDewater.dewater_handicap_3way(
        {"home": match["handicap_3way"][0], "draw": match["handicap_3way"][1], "away": match["handicap_3way"][2]},
        source="500竞彩官方让球三向",
    )
    total_market = MarketDewater.dewater_total_goals_exact(
        {key: price for key, price in zip(TOTAL_KEYS, match["total_exact"])},
        source="500竞彩官方总进球",
    )

    real_xg_shrunk = match.get("real_xg_shrunk") or (None, None)
    report = SimpleNamespace(
        home_stats=make_stats(match["recent"][0], real_xg_shrunk[0]),
        away_stats=make_stats(match["recent"][1], real_xg_shrunk[1]),
        home_home_stats=make_stats(match["recent"][0], real_xg_shrunk[0]),
        away_away_stats=make_stats(match["recent"][1], real_xg_shrunk[1]),
        jingcai_match={
            "home_fifa_rank": match["rank"][0],
            "away_fifa_rank": match["rank"][1],
            "total_goals_odds": {key: price for key, price in zip(TOTAL_KEYS, match["total_exact"])},
        },
        supplemental_data={},
        match_intelligence={"home": {"injuries": []}, "away": {"injuries": []}},
        weather_context={"text": match["weather"]},
    )
    market_signal_for_xg = SimpleNamespace(
        implied_home=one_x_two.probabilities["home"],
        implied_away=one_x_two.probabilities["away"],
    )
    competition_type = match.get("competition_type", "world_cup")
    context_for_xg = SimpleNamespace(competition_type=competition_type, friendly_subtype="", tags=match["tags"], warnings=[])
    proxy_xg = PreMatchXGProxyModel.analyze(report, market_signal_for_xg, context_for_xg)
    historical_lambda = trained.lambdas(match["home_en"], match["away_en"], neutral=True)
    if historical_lambda is None:
        historical_lambda = (proxy_xg.home_xg, proxy_xg.away_xg)
    weight = match["proxy_weight"]
    independent_lambda = (
        weight * proxy_xg.home_xg + (1 - weight) * historical_lambda[0],
        weight * proxy_xg.away_xg + (1 - weight) * historical_lambda[1],
    )
    final_lambda = (
        max(0.15, independent_lambda[0] + match["lambda_context"][0]),
        max(0.15, independent_lambda[1] + match["lambda_context"][1]),
    )
    poisson = PoissonModel.calculate_match_probabilities(*final_lambda, max_goals=10, low_score_rho=-0.06)

    prior_result = {"home": poisson.home_win_prob, "draw": poisson.draw_prob, "away": poisson.away_win_prob}
    result_fusion_500 = BayesianProbabilityFusion.fuse_3way(
        prior_result,
        one_x_two.probabilities,
        market_type="result_3way",
        prior_strength=12.0,
        evidence_strength=7.0 if "未开售" in match["market_1x2_source"] else 10.0,
    )
    result_fusion = result_fusion_500
    external_market_audit = None
    multi_source_result_audit = None
    multi_source_config = match.get("multi_source_result_fusion")
    if multi_source_config:
        base_weights = multi_source_config["base_weights"]
        sources = [
            FusionSource(
                name="poisson", probabilities=prior_result,
                base_weight=base_weights["poisson"], source_type="model",
                metadata={"includes": "proxy_or_real_xg_plus_historical_lambda_plus_context"},
            ),
            FusionSource(
                name="500", probabilities=one_x_two.probabilities,
                base_weight=base_weights["500"], source_type="market",
                quality=float(multi_source_config.get("fivehundred_quality", 1.0)),
                apply_deviation_discount=True,
                metadata={"source": match["market_1x2_source"]},
            ),
        ]
        for item in multi_source_config.get("external_sources", []):
            sources.append(FusionSource(
                name=item["name"], probabilities=item["probabilities"],
                base_weight=base_weights[item["name"]],
                quality=float(item.get("quality", 1.0)),
                correlation_discount=float(item.get("correlation_discount", 1.0)),
                apply_deviation_discount=bool(item.get("apply_deviation_discount", False)),
                source_type=item.get("source_type", "external"),
                metadata=dict(item.get("metadata") or {}),
            ))
        result_fusion = MultiSourceProbabilityFusion.fuse(sources)
        multi_source_result_audit = result_fusion.to_dict()
    else:
        external_market = match.get("external_result_market")
    if not multi_source_config and external_market:
        external_probabilities = normalize(external_market["probabilities"])
        effective_weight = min(0.20, max(0.0, float(external_market["effective_weight"])))
        prior_strength = 22.0
        evidence_strength = prior_strength * effective_weight / max(1.0 - effective_weight, 1e-9)
        result_fusion = BayesianProbabilityFusion.fuse_3way(
            result_fusion_500.posterior_probabilities,
            external_probabilities,
            market_type="external_result_market",
            prior_strength=prior_strength,
            evidence_strength=evidence_strength,
        )
        external_market_audit = {
            "source": external_market["source"],
            "event_url": external_market.get("event_url"),
            "raw_probabilities": external_market["probabilities"],
            "normalized_probabilities": external_probabilities,
            "quality_weight_before_correlation_discount": external_market.get("quality_weight"),
            "correlation_discount": external_market.get("correlation_discount"),
            "effective_weight": effective_weight,
            "prior_strength": prior_strength,
            "evidence_strength": round(evidence_strength, 4),
            "liquidity": external_market.get("liquidity"),
            "volume": external_market.get("volume"),
            "updated_at": external_market.get("updated_at"),
        }

    model_total = distribution_from_scores(poisson.score_probs, total_bucket, TOTAL_KEYS)
    total_fusion = BayesianProbabilityFusion.fuse_3way(
        model_total,
        total_market.probabilities,
        market_type="total_goals_exact",
        prior_strength=12.0,
        evidence_strength=9.0,
        keys=TOTAL_KEYS,
    )

    score_blended = score_market_blend(poisson.score_probs, match["score_prices"])
    fitted_scores = ipf(score_blended, result_fusion.posterior_probabilities, total_fusion.posterior_probabilities)
    home_handicap_prior = distribution_from_scores(
        fitted_scores,
        lambda home, away: settlement_bucket(home, away, match["handicap"]),
        ("cover", "push", "fail"),
    )
    home_handicap_fusion = BayesianProbabilityFusion.fuse_3way(
        home_handicap_prior,
        {
            "cover": handicap_market.probabilities["home"],
            "push": handicap_market.probabilities["draw"],
            "fail": handicap_market.probabilities["away"],
        },
        market_type="handicap_3way",
        prior_strength=11.0,
        evidence_strength=10.0,
        keys=("cover", "push", "fail"),
    )

    favorite = max(result_fusion.posterior_probabilities, key=result_fusion.posterior_probabilities.get)
    favorite_handicap = map_favorite_handicap(home_handicap_fusion.posterior_probabilities, favorite)
    candidates = candidate_pool(fitted_scores, match["forced_scores"])
    top_for_signals = sorted(candidates, key=lambda item: item["probability"], reverse=True)
    goals_direction = "3-4球" if exact_mean(total_fusion.posterior_probabilities) >= 3.15 else ("2-3球" if exact_mean(total_fusion.posterior_probabilities) >= 2.35 else "1-2球")

    market_signal = SimpleNamespace(
        favorite=favorite,
        market_strength="deep_handicap" if abs(match["asian_line"]) >= 1.75 else ("medium_handicap" if abs(match["asian_line"]) >= 0.65 else "shallow"),
        disagreement="high" if result_fusion.max_deviation >= 0.22 else ("medium" if result_fusion.max_deviation >= 0.14 else "low"),
        asian_handicap=match["asian_line"],
    )
    favorite_handicap_signal = SimpleNamespace(
        line=match["handicap"],
        cover_probability=favorite_handicap["cover"],
        push_probability=favorite_handicap["push"],
        fail_probability=favorite_handicap["fail"],
    )
    goals_signal = SimpleNamespace(
        final_goal_mean=exact_mean(total_fusion.posterior_probabilities),
        exact_distribution=total_fusion.posterior_probabilities,
        goals_direction=goals_direction,
    )
    scoreline_signal = SimpleNamespace(top_scores=top_for_signals)
    game_context = SimpleNamespace(
        competition_type=competition_type,
        friendly_subtype="",
        motivation_score=0.40,
        volatility_score=match["volatility"],
        high_scoring_risk=match["high_scoring_risk"],
        favorite_cover_trigger=match["favorite_cover_trigger"],
    )
    leg = LEGModel.analyze(market_signal, favorite_handicap_signal, goals_signal, scoreline_signal, game_context, proxy_xg)

    qimen = QimenAssistant().analyze(
        datetime.fromisoformat(match["kickoff"]),
        match["home"],
        match["away"],
        poisson=poisson,
        odds={"home": match["market_1x2"][0], "draw": match["market_1x2"][1], "away": match["market_1x2"][2]},
    )
    qimen_side = {"home": "home", "draw": "draw", "away": "away"}.get(qimen.qimen_bias)

    features = DecisionIterationFeatures(
        match_id=match["code"],
        home=match["home"],
        away=match["away"],
        competition_type=competition_type,
        stage=match.get("stage", "group"),
        round_index=match.get("round_index", 2),
        group_direct_rivalry=match["group_direct_rivalry"],
        weather_suppression=match["weather_suppression"],
        material_absence_team=match["material_absence_team"],
        lineup_uncertainty=match.get("lineup_uncertainty", True),
        qimen_conflict=qimen_side is not None and qimen_side != favorite,
        favorite_side=favorite,
        favorite_win_prob=result_fusion.posterior_probabilities[favorite],
        favorite_edge=sorted(result_fusion.posterior_probabilities.values(), reverse=True)[0] - sorted(result_fusion.posterior_probabilities.values(), reverse=True)[1],
        handicap_line=match["handicap"],
        handicap_cover=favorite_handicap["cover"],
        handicap_push=favorite_handicap["push"],
        handicap_fail=favorite_handicap["fail"],
        result_probabilities=result_fusion.posterior_probabilities,
        handicap_probabilities=favorite_handicap,
        total_distribution=total_fusion.posterior_probabilities,
        scorelines=candidates,
        tags=match["tags"],
        volatility_score=match["volatility"],
        high_scoring_risk=match["high_scoring_risk"],
        favorite_cover_trigger=match["favorite_cover_trigger"],
    )
    decision = DecisionIterationEngine().apply(features)
    audit_pool = list(decision.after_scorelines)
    seen_scores = {item["score"] for item in audit_pool}
    audit_pool.extend(item for item in candidates if item["score"] not in seen_scores)
    audited_scorelines = audit_scoreline_tiers(
        audit_pool,
        favorite,
        decision.after_result[favorite],
        match["handicap"],
    )
    after_home_handicap = map_home_handicap(decision.after_handicap, favorite)
    final_scoreline_signal = SimpleNamespace(top_scores=audited_scorelines)
    final_home_handicap_signal = SimpleNamespace(
        line=match["handicap"],
        cover_probability=after_home_handicap["cover"],
        push_probability=after_home_handicap["push"],
        fail_probability=after_home_handicap["fail"],
    )
    final_poisson = SimpleNamespace(
        home_win_prob=decision.after_result["home"],
        draw_prob=decision.after_result["draw"],
        away_win_prob=decision.after_result["away"],
    )
    home_labels = {"cover": "让胜", "push": "让平", "fail": "让负"}
    primary_handicap_key = max(after_home_handicap, key=after_home_handicap.get)
    if favorite == "away" and primary_handicap_key == "cover":
        integrated_decision = SimpleNamespace(primary_market="受让保护", primary_pick=f"{match['home']}+1")
    else:
        integrated_decision = SimpleNamespace(primary_market="让球", primary_pick=home_labels[primary_handicap_key])
    consistency = ModelConsistencyChecker.check(
        final_poisson,
        final_home_handicap_signal,
        SimpleNamespace(final_goal_mean=exact_mean(decision.after_total_distribution), exact_distribution=decision.after_total_distribution, goals_direction=goals_direction),
        final_scoreline_signal,
        leg,
        integrated_decision,
    )

    return {
        "identity": {key: match[key] for key in ["code", "home", "away", "kickoff", "fixture_id", "venue", "first_round"]},
        "source_facts": {
            "fifa_rank": {"home": match["rank"][0], "away": match["rank"][1]},
            "recent_10": {
                "home": {"goals_for": match["recent"][0][1], "goals_against": match["recent"][0][2]},
                "away": {"goals_for": match["recent"][1][1], "goals_against": match["recent"][1][2]},
            },
            "weather": match["weather"],
            "absence_note": match["absence_note"],
            "api_endpoint_status": match.get(
                "api_endpoint_status",
                {"predictions": 1, "injuries": 0, "lineups": 0, "statistics": 0},
            ),
        },
        "market": {
            "one_x_two": one_x_two.to_dict(),
            "handicap_three_way": handicap_market.to_dict(),
            "total_exact": total_market.to_dict(),
            "asian_average_line": match["asian_line"],
            "total_average_line": match["market_total_line"],
        },
        "xg": {
            "proxy": proxy_xg.to_dict(),
            "historical_lambda": {"home": round(historical_lambda[0], 4), "away": round(historical_lambda[1], 4)},
            "independent_lambda": {"home": round(independent_lambda[0], 4), "away": round(independent_lambda[1], 4)},
            "context_adjustment": {"home": match["lambda_context"][0], "away": match["lambda_context"][1]},
            "final_lambda": {"home": round(final_lambda[0], 4), "away": round(final_lambda[1], 4)},
        },
        "fusion": {
            "result": result_fusion.to_dict(),
            "result_before_external_market": result_fusion_500.to_dict(),
            "external_result_market": external_market_audit,
            "multi_source_result": multi_source_result_audit,
            "handicap_home_settlement": home_handicap_fusion.to_dict(),
            "total": total_fusion.to_dict(),
        },
        "means": {
            "historical_independent": round(sum(historical_lambda), 3),
            "proxy": round(proxy_xg.total_xg, 3),
            "poisson_contextual": round(sum(final_lambda), 3),
            "market_exact": round(exact_mean(total_market.probabilities), 3),
            "final_fused": round(exact_mean(total_fusion.posterior_probabilities), 3),
            "decision_final": round(exact_mean(decision.after_total_distribution), 3),
        },
        "leg": leg.to_dict(),
        "qimen": qimen.to_dict(),
        "decision_iteration": decision.to_dict(),
        "final": {
            "result": decision.after_result,
            "favorite": favorite,
            "handicap_home_settlement": after_home_handicap,
            "total_distribution": decision.after_total_distribution,
            "scorelines": audited_scorelines,
            "score_candidate_pool": candidates,
            "goals_direction": goals_direction,
            "primary_handicap": home_labels[primary_handicap_key],
        },
        "consistency": consistency.to_dict(),
    }


def main() -> None:
    trained = WorldCupTrainedModel()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260620-1847-v2",
        "notes": [
            "真实赛前xG/xGA不可用，全部使用项目proxy xG并与离线世界杯历史模型融合。",
            "API-Football预测端点只有单场小样本，其负数goals字段视为异常，不输入模型。",
            "三向、让球三向、总进球均先去水，再与模型先验进行贝叶斯融合。",
        ],
        "matches": [analyze_match(match, trained) for match in MATCHES],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "matches": len(output["matches"]),
        "summary": [
            {
                "code": item["identity"]["code"],
                "result": item["final"]["result"],
                "handicap": item["final"]["handicap_home_settlement"],
                "mean": item["means"]["decision_final"],
                "scores": [score["score"] for score in item["final"]["scorelines"][:5]],
                "rules": item["decision_iteration"]["applied_rules"],
                "consistency": item["consistency"]["status"],
            }
            for item in output["matches"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
