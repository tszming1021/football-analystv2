from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import scripts.fetch_worldcup_0622_latest_market as base


MAIN_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2"
OUT_DIR = Path("data/finland_20260623/market")
OUT_JSON = OUT_DIR / "latest_market.json"
CODES = {"周二201", "周二202", "周二203", "周二204", "周二205", "周二206"}


def main() -> None:
    base.CODES = CODES
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    main_html, headers = base.get_html(MAIN_URL)
    (OUT_DIR / "500_trade_live.html").write_text(main_html, encoding="utf-8")
    current = base.parse_main(main_html)
    output = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_url": MAIN_URL,
        "source_http_date": headers.get("date"),
        "matches": {},
        "errors": {},
    }
    for code, match in current.items():
        page_id = match["fixture_page_id"]
        deep = {}
        for kind in ["ouzhi", "yazhi", "daxiao"]:
            url = f"https://odds.500.com/fenxi/{kind}-{page_id}.shtml"
            try:
                html, _ = base.get_html(url)
                (OUT_DIR / f"{page_id}_{kind}.html").write_text(html, encoding="utf-8")
                deep[kind] = {"url": url, **base.average_row(html, kind)}
            except Exception as exc:
                output["errors"][f"{code}_{kind}"] = repr(exc)
        output["matches"][code] = {"current": match, "deep_market": deep}
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_JSON), "fetched_at": output["fetched_at"],
        "matches": {code: {
            "one_x_two": item["current"]["one_x_two"],
            "handicap": item["current"]["handicap_three_way"],
            "asian": item["deep_market"].get("yazhi", {}).get("current"),
            "total": item["deep_market"].get("daxiao", {}).get("current"),
            "europe": item["deep_market"].get("ouzhi", {}).get("current"),
        } for code, item in output["matches"].items()},
        "errors": output["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
