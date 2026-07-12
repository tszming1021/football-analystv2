from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_latest_market as base


base.OUT_DIR = Path("data/worldcup_20260625/market")
base.OUT_JSON = base.OUT_DIR / "latest_market.json"
base.CODES = {"周三049", "周三050", "周三051", "周三052", "周三053", "周三054"}


if __name__ == "__main__":
    base.main()

