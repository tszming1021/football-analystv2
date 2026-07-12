from __future__ import annotations

from pathlib import Path

import scripts.fetch_worldcup_0622_api as base


base.OUT_DIR = Path("data/worldcup_20260626/api")
base.FIXTURES = {
    "周四055": 1489410,
    "周四056": 1489409,
    "周四057": 1489412,
    "周四058": 1539011,
    "周四059": 1489411,
    "周四060": 1539012,
}


if __name__ == "__main__":
    base.main()
