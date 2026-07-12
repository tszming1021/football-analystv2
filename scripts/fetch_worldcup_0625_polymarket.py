from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0624_polymarket as base


base.OUT = Path("data/worldcup_20260625/polymarket_snapshot.json")
base.EVENTS = {
    "周三049": {"query": "Switzerland Canada", "slug": "fifwc-che-can-2026-06-24", "home": "Switzerland", "away": "Canada"},
    "周三050": {"query": "Bosnia Qatar", "slug": "fifwc-bih-qat-2026-06-24", "home": "Bosnia and Herzegovina", "away": "Qatar"},
    "周三051": {"query": "Scotland Brazil", "slug": "fifwc-sco-bra-2026-06-24", "home": "Scotland", "away": "Brazil"},
    "周三052": {"query": "Morocco Haiti", "slug": "fifwc-mar-hai-2026-06-24", "home": "Morocco", "away": "Haiti"},
    "周三053": {"query": "South Africa South Korea", "slug": "fifwc-rsa-kr-2026-06-24", "home": "South Africa", "away": "Korea Republic"},
    "周三054": {"query": "Czechia Mexico", "slug": "fifwc-cze-mex-2026-06-24", "home": "Czechia", "away": "Mexico"},
}


if __name__ == "__main__":
    base.main()
