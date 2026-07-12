from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_latest_market as base


base.OUT_DIR = Path("data/worldcup_20260626/market")
base.OUT_JSON = base.OUT_DIR / "latest_market.json"
base.CODES = {"周四055", "周四056", "周四057", "周四058", "周四059", "周四060"}


if __name__ == "__main__":
    base.main()
