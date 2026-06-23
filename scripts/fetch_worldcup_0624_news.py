from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

import scripts.fetch_worldcup_0622_news as base


OUT = Path("data/worldcup_20260624/online_review_sources.json")
HTML_DIR = Path("data/worldcup_20260624/opta")
QUERIES = {
    "周二045": "Portugal Uzbekistan World Cup 2026 team news injury lineup",
    "周二046": "England Ghana World Cup 2026 team news injury lineup",
    "周二047": "Panama Croatia World Cup 2026 team news injury lineup",
    "周二048": "Colombia DR Congo World Cup 2026 team news injury lineup",
}
OPTA = {
    "周二045": {"url": "https://theanalyst.com/articles/portugal-vs-uzbekistan-prediction-world-cup-2026", "home": 0.831, "draw": 0.110, "away": 0.060},
    "周二046": {"url": "https://theanalyst.com/articles/england-vs-ghana-prediction-world-cup-2026", "home": 0.788, "draw": 0.133, "away": 0.079},
    "周二047": {"url": "https://theanalyst.com/articles/panama-vs-croatia-prediction-world-cup-2026", "home": 0.149, "draw": 0.222, "away": 0.630},
    "周二048": {"url": "https://theanalyst.com/articles/colombia-vs-dr-congo-prediction-world-cup-2026", "home": 0.580, "draw": 0.210, "away": 0.210},
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
        opta = {**OPTA[code], "simulations": 25000}
        try:
            response = requests.get(opta["url"], timeout=30)
            response.raise_for_status()
            html_path = HTML_DIR / f"{code}.html"
            html_path.write_bytes(response.content)
            opta["html"] = str(html_path)
        except Exception as exc:
            opta["exception"] = repr(exc)
        output["matches"][code] = {"query": query, "rss_url": rss_url, "items": items, "opta": opta}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT), "fetched_at": output["fetched_at"],
        "top_items": {code: data["items"][:6] for code, data in output["matches"].items()},
        "opta": OPTA,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
