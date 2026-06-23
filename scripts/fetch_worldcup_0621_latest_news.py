from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests


OUT = Path("data/worldcup_20260622/update_live/latest_news.json")
QUERIES = {
    "周日037": "Spain Saudi Arabia World Cup 2026 Yamal lineup injury",
    "周日038": "Belgium Iran World Cup 2026 Doku injury lineup",
    "周日039": "Uruguay Cape Verde World Cup 2026 Araujo injury lineup",
    "周日040": "New Zealand Egypt World Cup 2026 Salah lineup",
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
    for item in root.findall("./channel/item")[:12]:
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
        "matches": {},
        "selected_findings": {
            "周日037": "Reuters reported that Saudi Arabia's upset hopes were boosted with Yamal and Nico Williams unavailable. This is a reputable media report but not a final official XI.",
            "周日038": "ESPN reported Jeremy Doku out against Iran. API-Football still returned zero injury and lineup rows, so the report is retained with source-level qualification.",
            "周日039": "No newer authoritative confirmation superseded the existing Araujo/de Arrascaeta injury uncertainty; latest previews continued to treat Uruguay as affected.",
            "周日040": "No new material absence was identified; latest previews kept Salah in the Egypt match context and the coach's denial of a squad rift remains the strongest direct update.",
        },
    }
    for code, query in QUERIES.items():
        url, items = fetch(query)
        output["matches"][code] = {"query": query, "rss_url": url, "items": items}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "fetched_at": output["fetched_at"],
        "top_items": {code: data["items"][:3] for code, data in output["matches"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
