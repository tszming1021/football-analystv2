from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_api as base


base.OUT_DIR = Path("data/worldcup_20260624/api")
base.FIXTURES = {
    "周二045": 1489404,
    "周二046": 1489402,
    "周二047": 1489403,
    "周二048": 1539008,
}


if __name__ == "__main__":
    base.main()
