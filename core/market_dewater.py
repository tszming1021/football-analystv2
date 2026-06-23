#!/usr/bin/env python3
"""Market-number dewatering helpers.

Convert decimal market numbers into normalized implied probabilities and keep an
auditable report about overround and source quality.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


OUTCOME_KEYS = ("home", "draw", "away")
ODDS_KEYS = {
    "home": ("home", "home_win", "win", "胜"),
    "draw": ("draw", "tie", "平"),
    "away": ("away", "away_win", "loss", "负"),
}


@dataclass
class DewateredMarket:
    """Normalized market probabilities for a single market."""

    market_type: str
    raw_numbers: Dict[str, Optional[float]]
    raw_implied: Dict[str, Optional[float]]
    probabilities: Dict[str, Optional[float]]
    overround: Optional[float]
    method: str = "multiplicative"
    source: str = "unknown"
    warnings: List[str] = field(default_factory=list)

    @property
    def favorite(self) -> Optional[str]:
        valid = {key: value for key, value in self.probabilities.items() if value is not None}
        return max(valid.items(), key=lambda item: item[1])[0] if valid else None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketDewater:
    """Utility functions for removing overround from decimal market numbers."""

    @staticmethod
    def dewater_1x2(
        odds: Mapping[str, Any],
        *,
        source: str = "unknown",
        method: str = "multiplicative",
    ) -> DewateredMarket:
        return MarketDewater.dewater_decimal_market(
            odds,
            market_type="result_3way",
            key_map=ODDS_KEYS,
            source=source,
            method=method,
        )

    @staticmethod
    def dewater_handicap_3way(
        odds: Mapping[str, Any],
        *,
        source: str = "unknown",
        method: str = "multiplicative",
    ) -> DewateredMarket:
        return MarketDewater.dewater_decimal_market(
            odds,
            market_type="handicap_3way",
            key_map=ODDS_KEYS,
            source=source,
            method=method,
        )

    @staticmethod
    def dewater_total_goals_exact(
        odds_by_total: Mapping[Any, Any],
        *,
        source: str = "unknown",
        method: str = "multiplicative",
    ) -> DewateredMarket:
        normalized_input = {str(key): value for key, value in odds_by_total.items()}
        key_map = {str(key): (str(key),) for key in normalized_input}
        return MarketDewater.dewater_decimal_market(
            normalized_input,
            market_type="total_goals_exact",
            key_map=key_map,
            source=source,
            method=method,
        )

    @staticmethod
    def dewater_decimal_market(
        odds: Mapping[str, Any],
        *,
        market_type: str,
        key_map: Mapping[str, Iterable[str]],
        source: str = "unknown",
        method: str = "multiplicative",
    ) -> DewateredMarket:
        warnings: List[str] = []
        raw_numbers = {
            normalized_key: MarketDewater._first_decimal(odds, aliases)
            for normalized_key, aliases in key_map.items()
        }
        raw_implied = {
            key: (1.0 / value if value is not None and value > 1.0 else None)
            for key, value in raw_numbers.items()
        }
        valid_implied = {key: value for key, value in raw_implied.items() if value is not None}
        if len(valid_implied) != len(raw_implied):
            missing = [key for key, value in raw_implied.items() if value is None]
            warnings.append(f"missing_or_invalid_market_numbers: {','.join(missing)}")
        implied_sum = sum(valid_implied.values())
        if implied_sum <= 0:
            return DewateredMarket(
                market_type=market_type,
                raw_numbers=raw_numbers,
                raw_implied=raw_implied,
                probabilities={key: None for key in raw_numbers},
                overround=None,
                method=method,
                source=source,
                warnings=warnings + ["market_dewater_failed"],
            )
        probabilities = {
            key: (value / implied_sum if value is not None else None)
            for key, value in raw_implied.items()
        }
        overround = implied_sum - 1.0
        if overround < -0.03:
            warnings.append("negative_overround_check_source")
        if overround > 0.20:
            warnings.append("high_overround_market_numbers")
        return DewateredMarket(
            market_type=market_type,
            raw_numbers=raw_numbers,
            raw_implied=raw_implied,
            probabilities=probabilities,
            overround=overround,
            method=method,
            source=source,
            warnings=warnings,
        )

    @staticmethod
    def _first_decimal(odds: Mapping[str, Any], aliases: Iterable[str]) -> Optional[float]:
        for alias in aliases:
            if alias in odds:
                value = MarketDewater._safe_float(odds.get(alias))
                if value is not None:
                    return value
        return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["DewateredMarket", "MarketDewater"]
