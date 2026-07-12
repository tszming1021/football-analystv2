from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import scripts.fetch_worldcup_0622_latest_market as base


base.OUT_DIR = Path("data/pdf_20260705_all/market")
base.OUT_JSON = base.OUT_DIR / "latest_market.json"
base.CODES = {
    "周日091",
    "周日092",
    "周日201",
    "周日202",
    "周日203",
    "周日204",
    "周日205",
    "周日206",
    "周一093",
    "周一094",
    "周一201",
    "周一202",
}


if __name__ == "__main__":
    base.main()
