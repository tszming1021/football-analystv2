from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_latest_market as base


base.OUT_DIR = Path("data/worldcup_20260624/market")
base.OUT_JSON = base.OUT_DIR / "latest_market.json"
base.CODES = {"周二045", "周二046", "周二047", "周二048"}


if __name__ == "__main__":
    base.main()
