from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


MAIN_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2"
OUT_DIR = Path("data/worldcup_20260623/market")
OUT_JSON = OUT_DIR / "latest_market.json"
CODES = {"周一041", "周一042", "周一043", "周一044"}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/136.0 Safari/537.36"


def get_html(url: str) -> tuple[str, dict]:
    with tempfile.NamedTemporaryFile() as body_file, tempfile.NamedTemporaryFile() as header_file:
        command = [
            "curl", "-k", "-L", "-sS", "--compressed", "--retry", "3",
            "--retry-all-errors", "--max-time", "45", "-A", USER_AGENT,
            "-D", header_file.name, "-o", body_file.name, url,
        ]
        subprocess.run(command, check=True)
        body = Path(body_file.name).read_bytes()
        header_bytes = Path(header_file.name).read_bytes()
    headers = {}
    for line in header_bytes.decode("latin1", errors="replace").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return body.decode("gb18030", errors="replace"), headers


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
        if code not in CODES:
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
    numbers = []
    for value in values[values.index("平均值") + 1:]:
        try:
            numbers.append(float(value.rstrip("%")))
        except ValueError:
            continue
    if kind in {"yazhi", "daxiao"}:
        return {"current": numbers[:3], "opening": numbers[3:6]}
    return {"opening": numbers[:3], "current": numbers[3:6]}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    main_html, headers = get_html(MAIN_URL)
    (OUT_DIR / "500_trade_live.html").write_text(main_html, encoding="utf-8")
    current = parse_main(main_html)
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
                html, _ = get_html(url)
                (OUT_DIR / f"{page_id}_{kind}.html").write_text(html, encoding="utf-8")
                deep[kind] = {"url": url, **average_row(html, kind)}
            except Exception as exc:
                output["errors"][f"{code}_{kind}"] = repr(exc)
        output["matches"][code] = {"current": match, "deep_market": deep}
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_JSON),
        "fetched_at": output["fetched_at"],
        "matches": output["matches"],
        "errors": output["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
