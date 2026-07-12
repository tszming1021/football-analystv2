from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0624_polymarket as base


base.OUT = Path("data/worldcup_20260626/polymarket_snapshot.json")
base.EVENTS = {
    "周四055": {"query": "Ecuador Germany", "slug": "fifwc-ecu-deu-2026-06-25", "home": "Ecuador", "away": "Germany"},
    "周四056": {"query": "Curacao Ivory Coast", "slug": "fifwc-cuw-civ-2026-06-25", "home": "Curacao", "away": "Ivory Coast"},
    "周四057": {"query": "Tunisia Netherlands", "slug": "fifwc-tun-ned-2026-06-25", "home": "Tunisia", "away": "Netherlands"},
    "周四058": {"query": "Japan Sweden", "slug": "fifwc-jpn-swe-2026-06-25", "home": "Japan", "away": "Sweden"},
    "周四059": {"query": "Paraguay Australia", "slug": "fifwc-par-aus-2026-06-25", "home": "Paraguay", "away": "Australia"},
    "周四060": {"query": "Turkiye USA", "slug": "fifwc-tur-usa-2026-06-25", "home": "Turkiye", "away": "USA"},
}


if __name__ == "__main__":
    base.main()
