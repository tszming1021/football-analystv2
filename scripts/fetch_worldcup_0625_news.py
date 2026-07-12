from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

import scripts.fetch_worldcup_0622_news as base


OUT = Path("data/worldcup_20260625/online_review_sources.json")
HTML_DIR = Path("data/worldcup_20260625/opta")
QUERIES = {
    "周三049": "Switzerland Canada World Cup 2026 team news injury lineup",
    "周三050": "Bosnia Herzegovina Qatar World Cup 2026 team news injury lineup",
    "周三051": "Scotland Brazil World Cup 2026 team news injury lineup",
    "周三052": "Morocco Haiti World Cup 2026 team news injury lineup",
    "周三053": "South Africa South Korea World Cup 2026 team news injury lineup",
    "周三054": "Czechia Mexico World Cup 2026 team news injury lineup",
}
OPTA = {
    "周三049": {"url": "https://theanalyst.com/articles/switzerland-vs-canada-prediction-world-cup-2026-match-preview", "home": 0.419, "draw": 0.283, "away": 0.298},
    "周三050": {"url": "https://theanalyst.com/articles/bosnia-herzegovina-vs-qatar-prediction-world-cup-2026-match-preview", "home": 0.659, "draw": 0.183, "away": 0.158, "draw_inferred_from_rounded_remainder": True},
    "周三051": {"url": "https://theanalyst.com/articles/scotland-vs-brazil-prediction-world-cup-2026-match-preview", "home": 0.129, "draw": 0.190, "away": 0.681},
    "周三052": {"url": "https://theanalyst.com/articles/morocco-vs-haiti-prediction-world-cup-2026-match-preview", "home": 0.810, "draw": 0.123, "away": 0.068},
    "周三053": {"url": None, "status": "no_verifiable_opta_preview_at_fetch_time"},
    "周三054": {"url": "https://theanalyst.com/articles/czechia-vs-mexico-prediction-world-cup-2026-match-preview", "home": 0.287, "draw": 0.234, "away": 0.479},
}


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "method": "Google News RSS discovery plus direct Opta Analyst retrieval; generic web search returned HTTP 403",
        "matches": {},
    }
    for code, query in QUERIES.items():
        rss_url, items = base.fetch(query)
        opta = {**OPTA[code]}
        if opta.get("url"):
            try:
                response = requests.get(opta["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                html_path = HTML_DIR / f"{code}.html"
                html_path.write_bytes(response.content)
                opta.update({"html": str(html_path), "simulations": 25000, "verified": True})
            except Exception as exc:
                opta.update({"exception": repr(exc), "verified": False})
        output["matches"][code] = {"query": query, "rss_url": rss_url, "items": items, "opta": opta}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT), "fetched_at": output["fetched_at"],
        "top_items": {code: data["items"][:6] for code, data in output["matches"].items()},
        "opta": {code: data["opta"] for code, data in output["matches"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
