from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests


OUT = Path("data/finland_20260623/online_review_sources.json")
QUERIES = {
    "周二201": "FC Lahti TPS Turku 23 June 2026 team news injury",
    "周二202": "KuPS Ilves 23 June 2026 team news injury",
    "周二203": "VPS AC Oulu 23 June 2026 team news injury",
    "周二204": "FF Jaro Gnistan 23 June 2026 team news injury",
    "周二205": "Inter Turku SJK 23 June 2026 team news injury",
    "周二206": "Mariehamn HJK 23 June 2026 team news injury",
}


def fetch(query: str) -> tuple[str, list[dict]]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "en", "gl": "FI", "ceid": "FI:en"})
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall("./channel/item")[:15]:
        source = item.find("source")
        items.append({"title": item.findtext("title"), "published": item.findtext("pubDate"),
                      "discovery_url": item.findtext("link"), "source": source.text if source is not None else None,
                      "source_url": source.attrib.get("url") if source is not None else None})
    return url, items


def main() -> None:
    output = {"fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"), "matches": {}}
    for code, query in QUERIES.items():
        url, items = fetch(query)
        output["matches"][code] = {"query": query, "rss_url": url, "items": items}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "top_items": {c: d["items"][:5] for c, d in output["matches"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
