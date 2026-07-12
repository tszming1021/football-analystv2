#!/usr/bin/env python3
"""Audit whether World Cup group-stage backtests can use true T-2h data.

The script is intentionally strict: a match is eligible only when a stored odds
snapshot is within 120 +/- 30 minutes before kickoff. Result-only files or
current 500.com odds without a capture timestamp are marked as reconstruction
candidates, not valid T-2h evidence.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = Path("/Users/jamesm/Desktop/football-analyst2")
RESULTS_JSON = LEGACY_ROOT / "tmp/500_worldcup_2026_group_matches.json"
API_FIXTURES_JSON = LEGACY_ROOT / "data/worldcup_batch_20260610/api/worldcup_fixtures.json"
ODDS_DB = LEGACY_ROOT / "data/odds_history.sqlite3"
OUT_DIR = ROOT / "data/backtest"
STRICT_TARGET_MINUTES = 120
STRICT_TOLERANCE_MINUTES = 30


@dataclass(frozen=True)
class OddsSnapshot:
    match_num: str | None
    league: str | None
    home_team: str
    away_team: str
    match_datetime: str | None
    market: str | None
    captured_at: str | None
    minutes_to_kickoff: float | None
    source: str | None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def norm_team(name: str | None) -> str:
    if not name:
        return ""
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
    )


def result_label(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "主胜"
    if home_goals == away_goals:
        return "平局"
    return "客胜"


def implied_probs(win: float | None, draw: float | None, lost: float | None) -> dict[str, float] | None:
    if not win or not draw or not lost:
        return None
    inv = {"home": 1 / win, "draw": 1 / draw, "away": 1 / lost}
    total = sum(inv.values())
    return {k: round(v / total, 4) for k, v in inv.items()}


def load_odds_snapshots(path: Path) -> list[OddsSnapshot]:
    if not path.exists():
        return []
    con = sqlite3.connect(path)
    cur = con.cursor()
    rows = cur.execute(
        """
        select match_num, league, home_team, away_team, match_datetime, market,
               captured_at, minutes_to_kickoff, source
        from odds_snapshots
        """
    ).fetchall()
    con.close()
    return [
        OddsSnapshot(
            match_num=row[0],
            league=row[1],
            home_team=row[2],
            away_team=row[3],
            match_datetime=row[4],
            market=row[5],
            captured_at=row[6],
            minutes_to_kickoff=row[7],
            source=row[8],
        )
        for row in rows
    ]


def find_nearest_snapshot(match: dict[str, Any], snapshots: list[OddsSnapshot]) -> OddsSnapshot | None:
    home = norm_team(match.get("hname"))
    away = norm_team(match.get("gname"))
    candidates = [
        s
        for s in snapshots
        if norm_team(s.home_team) == home and norm_team(s.away_team) == away
    ]
    candidates = [s for s in candidates if s.minutes_to_kickoff is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda s: abs((s.minutes_to_kickoff or 0) - STRICT_TARGET_MINUTES))


def api_fixture_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = load_json(path)
    out = {}
    for row in data.get("response") or []:
        teams = row.get("teams") or {}
        home = ((teams.get("home") or {}).get("name")) or ""
        away = ((teams.get("away") or {}).get("name")) or ""
        date = (row.get("fixture") or {}).get("date")
        key = f"{norm_team(home)}::{norm_team(away)}::{date[:10] if date else ''}"
        out[key] = row
    return out


def build_audit() -> dict[str, Any]:
    matches = load_json(RESULTS_JSON) if RESULTS_JSON.exists() else []
    snapshots = load_odds_snapshots(ODDS_DB)
    api_index = api_fixture_index(API_FIXTURES_JSON)

    rows = []
    for i, match in enumerate(matches, start=1):
        nearest = find_nearest_snapshot(match, snapshots)
        minutes = nearest.minutes_to_kickoff if nearest else None
        strict_ok = bool(
            nearest
            and minutes is not None
            and abs(minutes - STRICT_TARGET_MINUTES) <= STRICT_TOLERANCE_MINUTES
        )
        finished = match.get("status") == 5 and match.get("hscore") is not None and match.get("gscore") is not None
        api_key = f"{norm_team(match.get('hname'))}::{norm_team(match.get('gname'))}::{str(match.get('stime', ''))[:10]}"
        api_row = api_index.get(api_key)
        rows.append(
            {
                "seq": i,
                "fid": match.get("fid"),
                "group": match.get("_group"),
                "round": match.get("round"),
                "kickoff": match.get("stime"),
                "home": match.get("hname"),
                "away": match.get("gname"),
                "result_status": "finished" if finished else f"not_finished_or_stale_status_{match.get('status')}",
                "score": f"{match.get('hscore')}-{match.get('gscore')}" if finished else None,
                "result_label": result_label(match.get("hscore"), match.get("gscore")) if finished else None,
                "fivehundred_display_odds": {
                    "win": match.get("win"),
                    "draw": match.get("draw"),
                    "lost": match.get("lost"),
                    "handline": match.get("handline"),
                    "pan": match.get("pan"),
                    "implied_probs": implied_probs(match.get("win"), match.get("draw"), match.get("lost")),
                    "capture_time_evidence": None,
                    "t_minus_2h_valid": False,
                    "note": "500 result JSON has odds fields but no captured_at; usable only as reconstruction candidate.",
                },
                "nearest_stored_snapshot": {
                    "found": nearest is not None,
                    "market": nearest.market if nearest else None,
                    "captured_at": nearest.captured_at if nearest else None,
                    "minutes_to_kickoff": round(minutes, 2) if minutes is not None else None,
                    "source": nearest.source if nearest else None,
                    "strict_t_minus_2h_ok": strict_ok,
                },
                "api_fixture_status": ((api_row or {}).get("fixture") or {}).get("status") if api_row else None,
            }
        )

    result_counter = Counter(row["result_status"] for row in rows)
    strict_rows = [row for row in rows if row["nearest_stored_snapshot"]["strict_t_minus_2h_ok"]]
    reconstruction_candidates = [
        row for row in rows if row["fivehundred_display_odds"]["win"] and row["fivehundred_display_odds"]["draw"] and row["fivehundred_display_odds"]["lost"]
    ]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "strict_t_minus_2h_audit",
        "criteria": {
            "target_minutes_before_kickoff": STRICT_TARGET_MINUTES,
            "tolerance_minutes": STRICT_TOLERANCE_MINUTES,
            "rule": "Only stored snapshots with capture timestamp near T-2h qualify for strict backtest.",
        },
        "sources": {
            "results_json": str(RESULTS_JSON),
            "api_fixtures_json": str(API_FIXTURES_JSON),
            "odds_history_db": str(ODDS_DB),
        },
        "summary": {
            "matches_in_results_json": len(rows),
            "finished_results_available": result_counter.get("finished", 0),
            "unfinished_or_stale_results": len(rows) - result_counter.get("finished", 0),
            "stored_odds_snapshots_total": len(snapshots),
            "strict_t_minus_2h_eligible_matches": len(strict_rows),
            "reconstruction_candidates_with_500_display_odds": len(reconstruction_candidates),
            "strict_backtest_status": "blocked_no_valid_t_minus_2h_worldcup_snapshots" if not strict_rows else "partially_available",
        },
        "rows": rows,
    }


def write_markdown(audit: dict[str, Any], path: Path) -> None:
    summary = audit["summary"]
    rows = audit["rows"]
    unfinished = [r for r in rows if r["result_status"] != "finished"]
    lines = [
        "# 世界杯小组赛T-2h严格回测审计",
        "",
        f"- 生成时间：{audit['generated_at']}",
        f"- 严格口径：开赛前{STRICT_TARGET_MINUTES}分钟，容忍±{STRICT_TOLERANCE_MINUTES}分钟；必须有 `captured_at` 或等价采集时间证据。",
        f"- 比赛清单：{audit['sources']['results_json']}",
        f"- 赔率快照库：{audit['sources']['odds_history_db']}",
        "",
        "## 结论",
        "",
        f"- 小组赛记录：{summary['matches_in_results_json']}场",
        f"- 已有比分结果：{summary['finished_results_available']}场",
        f"- 未完赛或旧状态待确认：{summary['unfinished_or_stale_results']}场",
        f"- 本地赔率快照总数：{summary['stored_odds_snapshots_total']}条",
        f"- 符合T-2h严格口径的世界杯小组赛：{summary['strict_t_minus_2h_eligible_matches']}场",
        f"- 仅可做重构候选的500展示赔率：{summary['reconstruction_candidates_with_500_display_odds']}场",
        "",
        "严格回测当前被阻断：本地赔率快照库没有世界杯小组赛的赛前2小时采集记录。500小组赛结果JSON带有胜平负赔率字段，但没有采集时间，不能被记为T-2h样本。",
        "",
        "## 后续执行口径",
        "",
        "1. 严格模式：只纳入有T-2h时间戳证据的样本；当前样本数为0，不能产出准确率。",
        "2. 重构模式：可用500展示赔率和赛果做探索性复盘，但报告必须标注“非T-2h、不可用于正式模型校准”。",
        "3. 补数模式：从500、OddsPortal、Flashscore、AiScore或API-Football补到历史盘口时间序列后，再按本脚本重跑。",
        "",
        "## 待确认赛果",
        "",
    ]
    if unfinished:
        lines.append("| 场次 | 小组 | 时间 | 比赛 | 本地状态 |")
        lines.append("|---|---:|---|---|---|")
        for row in unfinished:
            lines.append(
                f"| {row['seq']} | {row['group']} | {row['kickoff']} | {row['home']} vs {row['away']} | {row['result_status']} |"
            )
    else:
        lines.append("本地结果文件72场均已完赛。")
    lines.extend(
        [
            "",
            "## 全量样本审计",
            "",
            "| 场次 | 小组 | 轮次 | 时间 | 比赛 | 比分 | 500赔率是否有时间戳 | 最近快照 | T-2h合格 |",
            "|---:|---:|---:|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        snap = row["nearest_stored_snapshot"]
        nearest = "无"
        if snap["found"]:
            nearest = f"{snap['minutes_to_kickoff']}分钟/{snap['source']}"
        lines.append(
            f"| {row['seq']} | {row['group']} | {row['round']} | {row['kickoff']} | "
            f"{row['home']} vs {row['away']} | {row['score'] or '待确认'} | "
            f"无 | {nearest} | {'是' if snap['strict_t_minus_2h_ok'] else '否'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    json_path = OUT_DIR / "worldcup_group_stage_tminus2h_audit.json"
    md_path = OUT_DIR / "worldcup_group_stage_tminus2h_audit.md"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(audit, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": audit["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
