from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import requests

from core.multi_source_fusion import MultiSourceWeightPolicy


OUT = Path("data/worldcup_20260624/polymarket_snapshot.json")
WEIGHT_POLICY = MultiSourceWeightPolicy()
EVENTS = {
    "周二045": {"query": "Portugal Uzbekistan", "slug": "fifwc-prt-uzb-2026-06-23", "home": "Portugal", "away": "Uzbekistan"},
    "周二046": {"query": "England Ghana", "slug": "fifwc-eng-gha-2026-06-23", "home": "England", "away": "Ghana"},
    "周二047": {"query": "Panama Croatia", "slug": "fifwc-pan-hrv-2026-06-23", "home": "Panama", "away": "Croatia"},
    "周二048": {"query": "Colombia DR Congo", "slug": "fifwc-col-cdr-2026-06-23", "home": "Colombia", "away": "DR Congo"},
}


def yes_price(market: dict) -> float:
    outcomes = json.loads(market["outcomes"])
    prices = [float(value) for value in json.loads(market["outcomePrices"])]
    return prices[outcomes.index("Yes")]


def side(question: str, home: str, away: str) -> str | None:
    if "end in a draw" in question:
        return "draw"
    if f"Will {home} win" in question:
        return "home"
    if f"Will {away} win" in question:
        return "away"
    return None


def quality_weight(event: dict) -> dict:
    liquidity = float(event.get("liquidity") or 0.0)
    volume = float(event.get("volume") or 0.0)
    spreads = []
    for market in event.get("markets", []):
        bid, ask = market.get("bestBid"), market.get("bestAsk")
        if bid is not None and ask is not None:
            spreads.append(max(0.0, float(ask) - float(bid)))
    average_spread = sum(spreads) / len(spreads) if spreads else 0.05
    liquidity_score = min(1.0, math.log10(liquidity + 1.0) / 6.5)
    volume_score = min(1.0, math.log10(volume + 1.0) / 6.5)
    spread_score = max(0.0, min(1.0, 1.0 - average_spread / 0.05))
    raw_quality_weight = 0.30 * (0.50 * liquidity_score + 0.30 * volume_score + 0.20 * spread_score)
    correlation_discount = float(WEIGHT_POLICY.controls("polymarket")["correlation_discount"])
    quality_factor = raw_quality_weight / 0.30
    return {
        "liquidity": liquidity, "volume": volume, "average_spread": round(average_spread, 4),
        "liquidity_score": round(liquidity_score, 4), "volume_score": round(volume_score, 4),
        "spread_score": round(spread_score, 4), "quality_weight": round(raw_quality_weight, 4),
        "quality_factor": round(quality_factor, 4), "correlation_discount": correlation_discount,
        "official_profile_raw_contribution": round(10.0 * quality_factor * correlation_discount, 4),
        "fallback_profile_raw_contribution": round(12.0 * quality_factor * correlation_discount, 4),
    }


def main() -> None:
    output = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "Polymarket Gamma public-search API",
        "weight_method": "quality factor from liquidity/volume/spread, then policy correlation discount versus 500; final normalized weight is calculated jointly with Poisson, 500 and Opta",
        "matches": {}, "errors": {},
    }
    for code, config in EVENTS.items():
        try:
            response = requests.get("https://gamma-api.polymarket.com/public-search", params={"q": config["query"]}, timeout=30)
            response.raise_for_status()
            events = response.json().get("events", [])
            event = next(item for item in events if item.get("slug") == config["slug"])
            prices, markets = {}, {}
            for market in event.get("markets", []):
                result_side = side(market["question"], config["home"], config["away"])
                if not result_side:
                    continue
                prices[result_side] = yes_price(market)
                markets[result_side] = {
                    "question": market["question"], "yes_price": prices[result_side],
                    "best_bid": market.get("bestBid"), "best_ask": market.get("bestAsk"),
                    "last_trade_price": market.get("lastTradePrice"),
                    "liquidity": float(market.get("liquidity") or 0.0), "volume": float(market.get("volume") or 0.0),
                }
            if set(prices) != {"home", "draw", "away"}:
                raise ValueError(f"incomplete outcome markets: {sorted(prices)}")
            total = sum(prices.values())
            output["matches"][code] = {
                "event_id": event["id"], "slug": event["slug"], "title": event["title"],
                "event_url": f"https://polymarket.com/event/{event['slug']}",
                "active": event.get("active"), "closed": event.get("closed"), "updated_at": event.get("updatedAt"),
                "raw_yes_prices": prices, "raw_sum": round(total, 6),
                "normalized_probabilities": {key: value / total for key, value in prices.items()},
                "markets": markets, **quality_weight(event),
            }
        except Exception as exc:
            output["errors"][code] = repr(exc)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
