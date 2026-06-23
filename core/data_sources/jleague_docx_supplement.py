#!/usr/bin/env python3
"""Local JLeague 2026-06-06 DOCX supplement loader."""

import json
import os
import re
from typing import Any, Dict, Optional


DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "jleague_20260606",
    "docx_supplement.json",
)


def load_jleague_docx_supplement(
    fixture_id: Optional[str] = None,
    home_team: str = "",
    away_team: str = "",
    path: str = DEFAULT_PATH,
) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    for item in payload.get("matches") or []:
        if fixture_id and str(item.get("match_id") or "") == str(fixture_id):
            return {**item, "_source_meta": _source_meta(payload)}

    for item in payload.get("matches") or []:
        if _team_matches(item.get("home_team", ""), home_team) and _team_matches(item.get("away_team", ""), away_team):
            return {**item, "_source_meta": _source_meta(payload)}
    return None


def _source_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_docx": payload.get("source_docx"),
        "fetch_time": payload.get("fetch_time"),
        "data_sources": payload.get("data_sources") or [],
    }


def _team_matches(source: str, target: str) -> bool:
    source_norm = _normalize_team(source)
    target_norm = _normalize_team(target)
    return source_norm == target_norm or source_norm in target_norm or target_norm in source_norm


def _normalize_team(name: str) -> str:
    aliases = {
        "神户胜利": "神户胜利船",
        "町田泽维": "町田泽维亚",
        "名古屋鲸": "名古屋鲸鱼",
        "京都": "京都不死鸟",
    }
    name = aliases.get(name, name)
    return re.sub(r"[\s·\-.]", "", name or "").lower()


__all__ = ["load_jleague_docx_supplement"]
