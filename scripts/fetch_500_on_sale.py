#!/usr/bin/env python3
"""Fetch currently available Jingcai matches from 500.com.

The trade page is GBK/GB18030 encoded and may present a local certificate
chain that Python rejects. This script shells out to curl with the same
tolerant behavior used by the older market-fetch scripts in this repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/136.0 Safari/537.36"
)
DEEP_KINDS = ("ouzhi", "yazhi", "daxiao")


def fetch_html(url: str, timeout: int = 45) -> tuple[str, dict[str, str], bytes]:
    """Fetch a 500 page through curl and decode it as GB18030-compatible text."""
    with tempfile.NamedTemporaryFile() as body_file, tempfile.NamedTemporaryFile() as header_file:
        command = [
            "curl",
            "-k",
            "-L",
            "-sS",
            "--compressed",
            "--retry",
            "3",
            "--retry-all-errors",
            "--max-time",
            str(timeout),
            "-A",
            USER_AGENT,
            "-D",
            header_file.name,
            "-o",
            body_file.name,
            url,
        ]
        subprocess.run(command, check=True)
        raw_body = Path(body_file.name).read_bytes()
        raw_headers = Path(header_file.name).read_bytes()

    headers: dict[str, str] = {}
    for line in raw_headers.decode("latin1", errors="replace").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return raw_body.decode("gb18030", errors="replace"), headers, raw_body


def price_map(container: Any, data_type: str) -> dict[str, float]:
    result: dict[str, float] = {}
    if not container:
        return result
    for item in container.select(f'[data-type="{data_type}"]'):
        key = item.get("data-value")
        value = item.get("data-sp")
        if key is None or value is None:
            continue
        try:
            result[str(key)] = float(value)
        except ValueError:
            continue
    return result


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_matches(html: str, include_ended: bool = False) -> tuple[list[dict[str, Any]], dict[str, int]]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.bet-tb-tr[data-matchnum]")
    matches: list[dict[str, Any]] = []
    counts = {"rows": len(rows), "on_sale": 0, "ended": 0, "included": 0}

    for row in rows:
        is_end = row.get("data-isend") == "1"
        if is_end:
            counts["ended"] += 1
        else:
            counts["on_sale"] += 1
        if is_end and not include_ended:
            continue

        more = row.find_next_sibling("tr", class_="bet-more-wrap")
        match = {
            "match_num": row.get("data-matchnum") or "",
            "fixture_page_id": row.get("data-fixtureid") or "",
            "league": row.get("data-simpleleague") or "",
            "home": row.get("data-homesxname") or "",
            "away": row.get("data-awaysxname") or "",
            "kickoff": f"{row.get('data-matchdate') or ''} {row.get('data-matchtime') or ''}".strip(),
            "match_date": row.get("data-matchdate") or "",
            "match_time": row.get("data-matchtime") or "",
            "handicap": parse_float(row.get("data-rangqiu")),
            "sale": {
                "is_end": is_end,
                "is_active": row.get("data-isactive") == "1",
                "subactive": row.get("data-subactive") or "",
                "buy_end_time": row.get("data_buyendtime") or "",
                "display_style": row.get("style") or "",
            },
            "one_x_two": price_map(row, "nspf"),
            "handicap_three_way": price_map(row, "spf"),
            "half_full": price_map(more, "bqc"),
            "scores": {key.replace(":", "-"): value for key, value in price_map(more, "bf").items()},
            "total_exact": price_map(more, "jqs"),
        }
        matches.append(match)

    counts["included"] = len(matches)
    return matches, counts


def average_row(html: str, kind: str) -> dict[str, list[float]]:
    soup = BeautifulSoup(html, "html.parser")
    cell = soup.find("td", string=lambda text: text and text.strip() == "平均值")
    if not cell:
        raise ValueError(f"average row not found for {kind}")

    values = list(cell.find_parent("tr").stripped_strings)
    numbers: list[float] = []
    for value in values[values.index("平均值") + 1 :]:
        try:
            numbers.append(float(value.rstrip("%")))
        except ValueError:
            continue

    if kind in {"yazhi", "daxiao"}:
        return {"current": numbers[:3], "opening": numbers[3:6]}
    return {"opening": numbers[:3], "current": numbers[3:6]}


def enrich_deep_market(match: dict[str, Any], out_dir: Path, timeout: int) -> tuple[dict[str, Any], dict[str, str]]:
    deep: dict[str, Any] = {}
    errors: dict[str, str] = {}
    fixture_id = match.get("fixture_page_id") or ""
    for kind in DEEP_KINDS:
        url = f"https://odds.500.com/fenxi/{kind}-{fixture_id}.shtml"
        try:
            html, _, _ = fetch_html(url, timeout=timeout)
            (out_dir / f"{fixture_id}_{kind}.html").write_text(html, encoding="utf-8")
            deep[kind] = {"url": url, **average_row(html, kind)}
        except Exception as exc:  # Page structures vary; keep the main scrape useful.
            errors[f"{match.get('match_num')}_{kind}"] = repr(exc)
    return deep, errors


def build_output(args: argparse.Namespace) -> dict[str, Any]:
    html, headers, raw_body = fetch_html(args.url, timeout=args.timeout)
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "500_trade_live.html").write_text(html, encoding="utf-8")
    (out_dir / "500_trade_live.raw").write_bytes(raw_body)

    matches, counts = parse_matches(html, include_ended=args.include_ended)
    output: dict[str, Any] = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_url": args.url,
        "source_http_date": headers.get("date"),
        "counts": counts,
        "matches": matches,
        "errors": {},
    }

    if args.with_deep:
        for match in output["matches"]:
            deep, errors = enrich_deep_market(match, out_dir=out_dir, timeout=args.timeout)
            match["deep_market"] = deep
            output["errors"].update(errors)

    (out_dir / "on_sale_matches.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch current on-sale matches from 500.com.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / f"500_on_sale_{datetime.now():%Y%m%d}"),
        help="Output directory for raw page and parsed JSON.",
    )
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--include-ended", action="store_true", help="Include hidden/ended rows too.")
    parser.add_argument("--with-deep", action="store_true", help="Also fetch ouzhi/yazhi/daxiao average pages.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = build_output(args)
    summary = {
        "output": str(Path(args.out).expanduser().resolve() / "on_sale_matches.json"),
        "fetched_at": output["fetched_at"],
        "counts": output["counts"],
        "matches": [
            {
                "match_num": item["match_num"],
                "league": item["league"],
                "home": item["home"],
                "away": item["away"],
                "kickoff": item["kickoff"],
                "handicap": item["handicap"],
            }
            for item in output["matches"]
        ],
        "errors": output["errors"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
