from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.fetch_worldcup_0622_latest_market as base


base.OUT_DIR = Path("data/kleague_20260704/market")
base.OUT_JSON = base.OUT_DIR / "latest_market.json"
base.CODES = {"周六201", "周六202", "周六203"}


if __name__ == "__main__":
    base.main()
