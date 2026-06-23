#!/usr/bin/env python3
"""市场数字和让球信号模型。

把三向表、欧赔均值、让球均值和历史快照转成可解释的市场信号。
该模型不直接替代泊松概率，而是用于修正信心和否决脆弱推荐。
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from core.market_dewater import DewateredMarket, MarketDewater


@dataclass
class MarketSignal:
    implied_home: Optional[float] = None
    implied_draw: Optional[float] = None
    implied_away: Optional[float] = None
    favorite: Optional[str] = None
    handicap: Optional[float] = None
    asian_handicap: Optional[float] = None
    market_strength: str = "unknown"
    pressure_side: str = "unknown"
    disagreement: str = "unknown"
    dewater_report: Optional[Dict[str, Any]] = None
    notes: List[str] = None
    warnings: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["notes"] = self.notes or []
        payload["warnings"] = self.warnings or []
        return payload


class MarketSignalModel:
    """Analyze market odds and handicap pressure."""

    @staticmethod
    def analyze(data_report: Any) -> MarketSignal:
        jingcai = data_report.jingcai_match or {}
        nspf = jingcai.get("no_handicap_odds") or {}
        europe = jingcai.get("average_europe_odds") or {}
        asian = jingcai.get("asian_average") or {}
        europe_market = jingcai.get("europe_market") or {}
        asian_market = jingcai.get("asian_market") or {}
        handicap = jingcai.get("handicap")
        notes: List[str] = []
        warnings: List[str] = []

        odds_source = nspf or europe
        odds_source_name = "main_table" if nspf else "europe_average"
        dewatered = MarketDewater.dewater_1x2(odds_source, source=odds_source_name)
        implied = dewatered.probabilities
        favorite = MarketSignalModel._favorite(implied)
        if dewatered.overround is not None:
            notes.append(f"三向表去水完成，水分 {dewatered.overround:.2%}")
        warnings.extend(dewatered.warnings)

        asian_handicap = MarketSignalModel._safe_float(asian.get("current_handicap_numeric"))
        market_strength = MarketSignalModel._market_strength(europe, asian_handicap, handicap)
        pressure_side = MarketSignalModel._pressure_side(favorite, asian_handicap, market_strength)

        if not nspf:
            warnings.append("竞彩普通胜平负缺失，市场隐含概率优先使用欧赔均值")
        if asian_handicap is None:
            warnings.append("让球均值缺失，无法判断让球升降强度")
        else:
            notes.append(f"亚盘均值约 {asian_handicap:+.2f}")

        if handicap is not None:
            notes.append(f"竞彩让球 {handicap:+d}")

        disagreement = MarketSignalModel._disagreement(handicap, asian_handicap)
        deep_disagreement = MarketSignalModel._deep_market_disagreement(europe_market, asian_market)
        disagreement = MarketSignalModel._max_disagreement(disagreement, deep_disagreement)
        if disagreement != "low":
            warnings.append("竞彩让球与亚盘深度存在差异，需降低让球单一判断权重")
        if deep_disagreement != "low":
            warnings.append("500深层市场数字分歧偏高，组合和高权重方向需降权")

        return MarketSignal(
            implied_home=implied.get("home"),
            implied_draw=implied.get("draw"),
            implied_away=implied.get("away"),
            favorite=favorite,
            handicap=float(handicap) if handicap is not None else None,
            asian_handicap=asian_handicap,
            market_strength=market_strength,
            pressure_side=pressure_side,
            disagreement=disagreement,
            dewater_report=dewatered.to_dict(),
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _normalized_implied(odds: Dict[str, Any]) -> Dict[str, Optional[float]]:
        values = {
            "home": MarketSignalModel._safe_float(odds.get("home_win")),
            "draw": MarketSignalModel._safe_float(odds.get("draw")),
            "away": MarketSignalModel._safe_float(odds.get("away_win")),
        }
        raw = {key: (1 / value if value and value > 1 else None) for key, value in values.items()}
        total = sum(value for value in raw.values() if value is not None)
        if not total:
            return {"home": None, "draw": None, "away": None}
        return {key: (value / total if value is not None else None) for key, value in raw.items()}

    @staticmethod
    def _favorite(implied: Dict[str, Optional[float]]) -> Optional[str]:
        valid = {key: value for key, value in implied.items() if value is not None}
        if not valid:
            return None
        return max(valid.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _market_strength(europe: Dict[str, Any], asian_handicap: Optional[float], handicap: Optional[int]) -> str:
        home_odds = MarketSignalModel._safe_float(europe.get("home_win"))
        away_odds = MarketSignalModel._safe_float(europe.get("away_win"))
        abs_line = abs(asian_handicap or handicap or 0)
        if home_odds and home_odds <= 1.20 and abs_line >= 2:
            return "strong_home_deep_handicap"
        if away_odds and away_odds <= 1.20 and abs_line >= 2:
            return "strong_away_deep_handicap"
        if abs_line >= 1.5:
            return "deep_handicap"
        if abs_line >= 0.75:
            return "medium_handicap"
        return "balanced"

    @staticmethod
    def _pressure_side(favorite: Optional[str], asian_handicap: Optional[float], market_strength: str) -> str:
        if not favorite:
            return "unknown"
        if market_strength in {"strong_home_deep_handicap", "deep_handicap"} and (asian_handicap or 0) < 0:
            return "home_cover_pressure"
        if market_strength in {"strong_away_deep_handicap", "deep_handicap"} and (asian_handicap or 0) > 0:
            return "away_cover_pressure"
        return f"{favorite}_result_pressure"

    @staticmethod
    def _disagreement(handicap: Optional[int], asian_handicap: Optional[float]) -> str:
        if handicap is None or asian_handicap is None:
            return "unknown"
        diff = abs(float(handicap) - asian_handicap)
        if diff >= 0.75:
            return "high"
        if diff >= 0.35:
            return "medium"
        return "low"

    @staticmethod
    def _deep_market_disagreement(europe_market: Dict[str, Any], asian_market: Dict[str, Any]) -> str:
        values = []
        for payload in [(europe_market.get("kelly_cv") or {}), (asian_market.get("water_cv") or {})]:
            for value in payload.values():
                try:
                    if value is not None:
                        values.append(float(value))
                except (TypeError, ValueError):
                    continue
        if not values:
            return "low"
        max_value = max(values)
        if max_value >= 0.16:
            return "high"
        if max_value >= 0.09:
            return "medium"
        return "low"

    @staticmethod
    def _max_disagreement(a: str, b: str) -> str:
        order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["MarketSignal", "MarketSignalModel"]
