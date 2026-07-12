from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.fetch_worldcup_0622_latest_market import get_html


BASE = Path("data/worldcup_20260625")


def main() -> None:
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    out_dir = BASE / "deep_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "pages": {}}
    for code, item in market["matches"].items():
        page_id = item["current"]["fixture_page_id"]
        url = f"https://odds.500.com/fenxi/shuju-{page_id}.shtml"
        try:
            html, _ = get_html(url)
            text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
            html_path = out_dir / f"{code}_{page_id}_shuju.html"
            text_path = out_dir / f"{code}_{page_id}_shuju.txt"
            html_path.write_text(html, encoding="utf-8")
            text_path.write_text(text, encoding="utf-8")
            audit["pages"][code] = {"url": url, "html": str(html_path), "text": str(text_path)}
        except Exception as exc:
            audit["pages"][code] = {"url": url, "exception": repr(exc)}
    (out_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
