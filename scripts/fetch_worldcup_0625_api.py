from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_api as base


base.OUT_DIR = Path("data/worldcup_20260625/api")
base.FIXTURES = {
    "周三049": 1489408,
    "周三050": 1539009,
    "周三051": 1489406,
    "周三052": 1489405,
    "周三053": 1489407,
    "周三054": 1539010,
}


if __name__ == "__main__":
    base.main()

