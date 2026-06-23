from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scripts.analyze_worldcup_0621_strict import MATCHES


MAIN_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2"
OUT_DIR = Path("data/worldcup_20260622/update_live")
OUT_JSON = OUT_DIR / "latest_market.json"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/136.0 Safari/537.36"


def get_html(url: str) -> tuple[str, dict]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, verify=False)
    response.raise_for_status()
    return response.content.decode("gb18030", errors="replace"), dict(response.headers)


def price_map(container, data_type: str) -> dict[str, float]:
    result = {}
    if not container:
        return result
    for item in container.select(f'[data-type="{data_type}"]'):
        result[item.get("data-value")] = float(item.get("data-sp"))
    return result


def parse_main(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    matches = {}
    for row in soup.select("tr.bet-tb-tr[data-matchnum]"):
        code = row.get("data-matchnum")
        if code not in {match["code"] for match in MATCHES}:
            continue
        more = row.find_next_sibling("tr", class_="bet-more-wrap")
        matches[code] = {
            "fixture_page_id": row.get("data-fixtureid"),
            "home": row.get("data-homesxname"),
            "away": row.get("data-awaysxname"),
            "kickoff": f"{row.get('data-matchdate')} {row.get('data-matchtime')}",
            "handicap": float(row.get("data-rangqiu")),
            "one_x_two": price_map(row, "nspf"),
            "handicap_three_way": price_map(row, "spf"),
            "half_full": price_map(more, "bqc"),
            "scores": {key.replace(":", "-"): value for key, value in price_map(more, "bf").items()},
            "total_exact": price_map(more, "jqs"),
        }
    return matches


def average_row(html: str, kind: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    cell = soup.find("td", string=lambda text: text and text.strip() == "平均值")
    if not cell:
        raise ValueError(f"average row not found for {kind}")
    values = list(cell.find_parent("tr").stripped_strings)
    index = values.index("平均值") + 1
    numbers = []
    for value in values[index:]:
        try:
            numbers.append(float(value.rstrip("%")))
        except ValueError:
            continue
    if kind in {"yazhi", "daxiao"}:
        return {"current": numbers[:3], "opening": numbers[3:6]}
    return {"opening": numbers[:3], "current": numbers[3:6]}


def baseline(match: dict) -> dict:
    return {
        "one_x_two": {"3": match["market_1x2"][0], "1": match["market_1x2"][1], "0": match["market_1x2"][2]},
        "handicap_three_way": {"3": match["handicap_3way"][0], "1": match["handicap_3way"][1], "0": match["handicap_3way"][2]},
        "scores": dict(match["score_prices"]),
        "total_exact": {str(index): value for index, value in enumerate(match["total_exact"][:7])} | {"7": match["total_exact"][7]},
        "asian_average": match["asian_line"],
        "total_average": match["market_total_line"],
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    main_path = OUT_DIR / "500_trade_live.html"
    if main_path.exists():
        main_html = main_path.read_text(encoding="utf-8")
        headers = {}
    else:
        main_html, headers = get_html(MAIN_URL)
        main_path.write_text(main_html, encoding="utf-8")
    current = parse_main(main_html)
    old_by_code = {match["code"]: match for match in MATCHES}
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
                page_path = OUT_DIR / f"{page_id}_{kind}.html"
                if page_path.exists():
                    html = page_path.read_text(encoding="utf-8")
                else:
                    html, _ = get_html(url)
                    page_path.write_text(html, encoding="utf-8")
                deep[kind] = {"url": url, **average_row(html, kind)}
            except Exception as exc:
                output["errors"][f"{code}_{kind}"] = repr(exc)
        output["matches"][code] = {
            "baseline": baseline(old_by_code[code]),
            "current": match,
            "deep_market": deep,
        }
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_JSON),
        "fetched_at": output["fetched_at"],
        "http_date": output["source_http_date"],
        "matches": {
            code: {
                "one_x_two": item["current"]["one_x_two"],
                "handicap": item["current"]["handicap_three_way"],
                "asian_average": item["deep_market"].get("yazhi", {}).get("current"),
                "total_average": item["deep_market"].get("daxiao", {}).get("current"),
                "europe_average": item["deep_market"].get("ouzhi", {}).get("current"),
            }
            for code, item in output["matches"].items()
        },
        "errors": output["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
