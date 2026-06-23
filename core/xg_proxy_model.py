#!/usr/bin/env python3
"""Pre-match xG/xGA signal model.

Priority:
1. Use real xG/xGA from configured API data sources when available.
2. Fall back to a transparent pre-match proxy built from project data.

The proxy is not event-data xG. It is a calibrated pre-match attacking and
defensive-strength signal used by Poisson and LEG layers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class XGSignal:
    source: str
    provider: str
    actual_available: bool
    home_xg: float
    away_xg: float
    home_xga: float
    away_xga: float
    xg_edge: float
    xga_edge: float
    total_xg: float
    confidence: str
    components: Dict[str, Any]
    notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PreMatchXGProxyModel:
    """Build xG/xGA signal for pre-match modeling."""

    @staticmethod
    def analyze(data_report: Any, market_signal: Any = None, context: Any = None) -> XGSignal:
        external = PreMatchXGProxyModel._external_actual_xg(data_report)
        if external:
            return external
        return PreMatchXGProxyModel._proxy_xg(data_report, market_signal, context)

    @staticmethod
    def _external_actual_xg(data_report: Any) -> Optional[XGSignal]:
        supplemental = getattr(data_report, "supplemental_data", None) or {}
        xg_payload = supplemental.get("xg_data") or supplemental.get("thestatsapi_xg") or {}
        actual = xg_payload.get("actual_xg") if isinstance(xg_payload, dict) else None
        if not isinstance(actual, dict):
            return None

        home_xg = PreMatchXGProxyModel._safe_float(actual.get("home_xg"))
        away_xg = PreMatchXGProxyModel._safe_float(actual.get("away_xg"))
        if home_xg is None or away_xg is None or (home_xg <= 0 and away_xg <= 0):
            return None

        home_xga = PreMatchXGProxyModel._safe_float(actual.get("home_xga"))
        away_xga = PreMatchXGProxyModel._safe_float(actual.get("away_xga"))
        home_xga = home_xga if home_xga is not None else away_xg
        away_xga = away_xga if away_xga is not None else home_xg

        provider = str(xg_payload.get("provider") or actual.get("provider") or "external_api")
        notes = [f"使用{provider}真实xG数据"]
        if actual.get("source"):
            notes.append(f"xG字段来源: {actual.get('source')}")

        return XGSignal(
            source="api_actual",
            provider=provider,
            actual_available=True,
            home_xg=round(home_xg, 3),
            away_xg=round(away_xg, 3),
            home_xga=round(home_xga, 3),
            away_xga=round(away_xga, 3),
            xg_edge=round(home_xg - away_xg, 3),
            xga_edge=round(away_xga - home_xga, 3),
            total_xg=round(home_xg + away_xg, 3),
            confidence="high",
            components={"actual_xg": actual},
            notes=notes,
            warnings=[],
        )

    @staticmethod
    def _proxy_xg(data_report: Any, market_signal: Any = None, context: Any = None) -> XGSignal:
        notes: List[str] = ["未获取到真实xG/xGA，启用赛前proxy xG"]
        warnings: List[str] = []

        home_stats = getattr(data_report, "home_home_stats", None) or getattr(data_report, "home_stats", None)
        away_stats = getattr(data_report, "away_away_stats", None) or getattr(data_report, "away_stats", None)
        home_gf, home_ga = PreMatchXGProxyModel._stats_rates(home_stats)
        away_gf, away_ga = PreMatchXGProxyModel._stats_rates(away_stats)

        if None in {home_gf, home_ga, away_gf, away_ga}:
            warnings.append("进失球统计不完整，proxy xG使用保守默认值")
        home_gf = home_gf if home_gf is not None else 1.25
        home_ga = home_ga if home_ga is not None else 1.15
        away_gf = away_gf if away_gf is not None else 1.10
        away_ga = away_ga if away_ga is not None else 1.25

        home_gf, home_ga, home_rel = PreMatchXGProxyModel._shrink_tiny_sample_rates(home_stats, home_gf, home_ga)
        away_gf, away_ga, away_rel = PreMatchXGProxyModel._shrink_tiny_sample_rates(away_stats, away_gf, away_ga)
        if home_rel is not None and home_rel < 0.56:
            notes.append(f"主队近况样本偏小，GF/GA按可靠度{home_rel:.2f}收缩")
        if away_rel is not None and away_rel < 0.56:
            notes.append(f"客队近况样本偏小，GF/GA按可靠度{away_rel:.2f}收缩")

        base_home = 0.52 * home_gf + 0.38 * away_ga
        base_away = 0.52 * away_gf + 0.38 * home_ga
        base_home *= 1.06
        base_away *= 0.94

        market_total = PreMatchXGProxyModel._market_total(data_report)
        if market_total is not None:
            market_home_share = PreMatchXGProxyModel._market_home_share(market_signal)
            market_home = market_total * market_home_share
            market_away = market_total * (1 - market_home_share)
            home_xg = 0.68 * base_home + 0.32 * market_home
            away_xg = 0.68 * base_away + 0.32 * market_away
            notes.append(f"proxy xG融合市场总球中枢 {market_total:.2f}")
        else:
            home_xg, away_xg = base_home, base_away
            warnings.append("市场总球中枢缺失，proxy xG仅使用球队统计")

        rank_adjust = PreMatchXGProxyModel._rank_adjustment(data_report)
        home_xg += rank_adjust
        away_xg -= rank_adjust * 0.70
        if abs(rank_adjust) >= 0.03:
            notes.append(f"实力排名修正 {rank_adjust:+.2f}")

        injury_home, injury_away = PreMatchXGProxyModel._injury_adjustment(data_report)
        home_xg += injury_home
        away_xg += injury_away
        if injury_home or injury_away:
            notes.append("proxy xG已纳入伤停/首发不确定性修正")

        tempo = PreMatchXGProxyModel._tempo_factor(data_report, context)
        home_xg *= tempo
        away_xg *= tempo
        if tempo < 0.98:
            notes.append(f"天气/赛制节奏压制: xG乘数 {tempo:.2f}")

        home_xg = PreMatchXGProxyModel._clamp(home_xg, 0.20, 3.80)
        away_xg = PreMatchXGProxyModel._clamp(away_xg, 0.15, 3.20)
        home_xga = PreMatchXGProxyModel._clamp(0.55 * home_ga + 0.45 * away_xg, 0.20, 3.50)
        away_xga = PreMatchXGProxyModel._clamp(0.55 * away_ga + 0.45 * home_xg, 0.20, 3.80)

        confidence = "medium"
        if warnings:
            confidence = "low"
        elif market_total is not None and getattr(data_report, "home_stats", None) and getattr(data_report, "away_stats", None):
            confidence = "medium"

        return XGSignal(
            source="proxy_calculated",
            provider="project_proxy",
            actual_available=False,
            home_xg=round(home_xg, 3),
            away_xg=round(away_xg, 3),
            home_xga=round(home_xga, 3),
            away_xga=round(away_xga, 3),
            xg_edge=round(home_xg - away_xg, 3),
            xga_edge=round(away_xga - home_xga, 3),
            total_xg=round(home_xg + away_xg, 3),
            confidence=confidence,
            components={
                "team_rates": {
                    "home_gf": home_gf,
                    "home_ga": home_ga,
                    "away_gf": away_gf,
                    "away_ga": away_ga,
                    "home_sample_reliability": home_rel,
                    "away_sample_reliability": away_rel,
                },
                "base_xg": {"home": base_home, "away": base_away},
                "market_total": market_total,
                "rank_adjustment": rank_adjust,
                "injury_adjustment": {"home": injury_home, "away": injury_away},
                "tempo_factor": tempo,
            },
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _stats_rates(stats: Any) -> Tuple[Optional[float], Optional[float]]:
        if not stats:
            return None, None
        matches = PreMatchXGProxyModel._safe_float(getattr(stats, "matches_played", None))
        goals_for = PreMatchXGProxyModel._safe_float(getattr(stats, "goals_for", None))
        goals_against = PreMatchXGProxyModel._safe_float(getattr(stats, "goals_against", None))
        xg = PreMatchXGProxyModel._safe_float(getattr(stats, "xg", None))
        xga = PreMatchXGProxyModel._safe_float(getattr(stats, "xga", None))

        if xg is not None and xga is not None:
            return xg, xga
        if matches and matches > 0 and goals_for is not None and goals_against is not None:
            return goals_for / matches, goals_against / matches
        return None, None

    @staticmethod
    def _shrink_tiny_sample_rates(stats: Any, gf: float, ga: float) -> Tuple[float, float, Optional[float]]:
        if not stats:
            return gf, ga, None
        if PreMatchXGProxyModel._safe_float(getattr(stats, "xg", None)) is not None:
            return gf, ga, 1.0
        matches = PreMatchXGProxyModel._safe_float(getattr(stats, "matches_played", None))
        if matches is None or matches <= 0:
            return gf, ga, None
        reliability = PreMatchXGProxyModel._clamp(matches / (matches + 4.0), 0.0, 1.0)
        if reliability >= 0.56:
            return gf, ga, reliability
        baseline_gf = 1.22
        baseline_ga = 1.18
        return (
            reliability * gf + (1.0 - reliability) * baseline_gf,
            reliability * ga + (1.0 - reliability) * baseline_ga,
            reliability,
        )

    @staticmethod
    def _market_total(data_report: Any) -> Optional[float]:
        jingcai = getattr(data_report, "jingcai_match", None) or {}
        mixed = jingcai.get("mixed_market") or {}
        for candidate in [
            mixed.get("total_goals_odds"),
            jingcai.get("total_goals_odds"),
            jingcai.get("total_goals_table"),
            (jingcai.get("trade_table") or {}).get("total_goals_table"),
        ]:
            if isinstance(candidate, dict) and candidate:
                exact = PreMatchXGProxyModel._exact_goal_distribution_from_prices(candidate)
                if exact:
                    return sum((7.5 if key == "7_plus" else float(key)) * value for key, value in exact.items())

        supplemental = getattr(data_report, "supplemental_data", None) or {}
        odds_summary = ((supplemental.get("xg_data") or {}).get("odds_summary") or {})
        over_25 = PreMatchXGProxyModel._safe_float(odds_summary.get("avg_over_25_probability"))
        if over_25 is not None:
            return 2.15 + (over_25 - 0.50) * 1.55
        return None

    @staticmethod
    def _exact_goal_distribution_from_prices(prices: Dict[str, Any]) -> Dict[str, float]:
        implied: Dict[str, float] = {}
        for key, value in prices.items():
            goal = PreMatchXGProxyModel._goal_key(key)
            price = PreMatchXGProxyModel._safe_float(value)
            if goal is None or not price or price <= 1:
                continue
            implied[goal] = implied.get(goal, 0.0) + 1.0 / price
        total = sum(implied.values())
        if total <= 0:
            return {}
        return {key: value / total for key, value in implied.items()}

    @staticmethod
    def _goal_key(key: Any) -> Optional[str]:
        text = str(key).strip().replace("球", "")
        if text in {"7+", "7＋", "7以上"}:
            return "7_plus"
        try:
            value = int(float(text))
        except (TypeError, ValueError):
            return None
        return "7_plus" if value >= 7 else str(value)

    @staticmethod
    def _market_home_share(market_signal: Any) -> float:
        if not market_signal:
            return 0.55
        home = PreMatchXGProxyModel._safe_float(getattr(market_signal, "implied_home", None))
        away = PreMatchXGProxyModel._safe_float(getattr(market_signal, "implied_away", None))
        if home is None or away is None or home + away <= 0:
            return 0.55
        share = home / (home + away)
        return PreMatchXGProxyModel._clamp(share, 0.35, 0.78)

    @staticmethod
    def _rank_adjustment(data_report: Any) -> float:
        jingcai = getattr(data_report, "jingcai_match", None) or {}
        home_rank = PreMatchXGProxyModel._safe_float(jingcai.get("home_rank") or jingcai.get("home_fifa_rank"))
        away_rank = PreMatchXGProxyModel._safe_float(jingcai.get("away_rank") or jingcai.get("away_fifa_rank"))
        if home_rank is None or away_rank is None:
            return 0.0
        # Smaller ranking number means stronger team.
        diff = away_rank - home_rank
        return PreMatchXGProxyModel._clamp(diff / 250.0, -0.22, 0.22)

    @staticmethod
    def _injury_adjustment(data_report: Any) -> Tuple[float, float]:
        intelligence = getattr(data_report, "match_intelligence", None) or {}
        values = []
        for side in ["home", "away"]:
            info = intelligence.get(side) or {}
            injuries = info.get("injuries") or []
            absences = len(injuries) if isinstance(injuries, list) else 0
            values.append(-min(0.12, 0.025 * absences))
        return values[0], values[1]

    @staticmethod
    def _tempo_factor(data_report: Any, context: Any) -> float:
        factor = 1.0
        weather = getattr(data_report, "weather_context", None) or {}
        weather_text = str(weather) + " " + str(getattr(context, "tags", [])) + " " + str(getattr(context, "warnings", []))
        if any(token in weather_text for token in ["高温", "雨", "降雨", "雷雨", "湿", "wind", "precipitation"]):
            factor -= 0.04
        if any(token in weather_text for token in ["高海拔", "altitude"]):
            factor -= 0.03
        if getattr(context, "competition_type", "") == "world_cup" and getattr(context, "friendly_subtype", "") != "world_cup_final_warmup":
            factor -= 0.02
        return PreMatchXGProxyModel._clamp(factor, 0.88, 1.05)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))


__all__ = ["PreMatchXGProxyModel", "XGSignal"]
