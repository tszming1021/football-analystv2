from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests


OUT = Path("data/worldcup_20260623/online_review_sources.json")
QUERIES = {
    "周一041": "Argentina Austria World Cup 2026 team news injury lineup",
    "周一042": "France Iraq World Cup 2026 team news injury lineup",
    "周一043": "Norway Senegal World Cup 2026 team news injury lineup",
    "周一044": "Jordan Algeria World Cup 2026 team news injury lineup",
}

OPTA = {
    "周一041": {"url": "https://theanalyst.com/articles/argentina-vs-austria-prediction-world-cup-2026", "home": 0.611, "draw": 0.219, "away": 0.170, "simulations": 25000},
    "周一042": {"url": "https://theanalyst.com/articles/france-vs-iraq-prediction-world-cup-2026", "home": 0.881, "draw": 0.081, "away": 0.038, "simulations": 25000},
    "周一043": {"url": "https://theanalyst.com/articles/norway-vs-senegal-prediction-world-cup-2026", "home": 0.450, "draw": 0.254, "away": 0.296, "simulations": 25000},
    "周一044": {"url": "https://theanalyst.com/articles/jordan-vs-algeria-prediction-world-cup-2026", "home": 0.177, "draw": 0.222, "away": 0.601, "simulations": 25000},
}


def fetch(query: str) -> tuple[str, list[dict]]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    })
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall("./channel/item")[:20]:
        source = item.find("source")
        items.append({
            "title": item.findtext("title"),
            "published": item.findtext("pubDate"),
            "discovery_url": item.findtext("link"),
            "source": source.text if source is not None else None,
            "source_url": source.attrib.get("url") if source is not None else None,
        })
    return url, items


def main() -> None:
    output = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "method": "Google News RSS discovery after generic web search returned HTTP 403",
        "matches": {},
    }
    for code, query in QUERIES.items():
        url, items = fetch(query)
        output["matches"][code] = {"query": query, "rss_url": url, "items": items, "opta": OPTA[code]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "fetched_at": output["fetched_at"],
        "top_items": {code: data["items"][:8] for code, data in output["matches"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
