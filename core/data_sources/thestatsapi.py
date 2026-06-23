#!/usr/bin/env python3
"""TheStatsAPI football data source.

Used as an optional source for real match xG/shotmap data. For scheduled
fixtures TheStatsAPI often returns fixture and market data but no xG yet, so
callers should treat missing xG as normal and fall back to the proxy model.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class TheStatsAPIMatchProbe:
    provider: str
    available: bool
    match_id: Optional[str]
    competition_id: Optional[str]
    season_id: Optional[str]
    status: Optional[str]
    home_team_id: Optional[str]
    away_team_id: Optional[str]
    venue: Dict[str, Any]
    referee: Dict[str, Any]
    xg_available: bool
    actual_xg: Dict[str, Optional[float]]
    odds_summary: Dict[str, Any]
    endpoint_statuses: Dict[str, Any]
    warnings: List[str]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TheStatsAPIClient:
    """Small wrapper around TheStatsAPI endpoints used by this project."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 12,
    ):
        self.api_key = api_key or os.getenv("THESTATSAPI_KEY")
        self.base_url = "https://api.thestatsapi.com/api"
        self.session = session or requests.Session()
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def probe_match(
        self,
        home_name: str,
        away_name: str,
        match_date: Optional[str] = None,
        competition_hint: Optional[str] = None,
    ) -> TheStatsAPIMatchProbe:
        warnings: List[str] = []
        endpoint_statuses: Dict[str, Any] = {}
        raw: Dict[str, Any] = {}

        if not self.available:
            return self._empty_probe(["未提供 THESTATSAPI_KEY"])

        match, search_warnings, search_raw = self._find_match(home_name, away_name, match_date, competition_hint)
        warnings.extend(search_warnings)
        raw.update(search_raw)
        if not match:
            return self._empty_probe(warnings or ["TheStatsAPI 未匹配到比赛"], raw=raw)

        match_id = match.get("id")
        details = self._get(f"/football/matches/{match_id}")
        raw["match_details"] = details
        endpoint_statuses["match_details"] = details.get("status_code")
        detail_data = self._data(details) or match

        stats = self._get(f"/football/matches/{match_id}/stats")
        raw["match_stats"] = stats
        endpoint_statuses["match_stats"] = stats.get("status_code")

        shotmap = self._get(f"/football/matches/{match_id}/shotmap")
        raw["shotmap"] = shotmap
        endpoint_statuses["shotmap"] = shotmap.get("status_code")

        odds = self._get(f"/football/matches/{match_id}/odds")
        raw["odds"] = odds
        endpoint_statuses["odds"] = odds.get("status_code")

        lineups = self._get(f"/football/matches/{match_id}/lineups")
        raw["lineups"] = lineups
        endpoint_statuses["lineups"] = lineups.get("status_code")

        actual_xg = self._extract_actual_xg(stats, shotmap)
        if actual_xg.get("home_xg") is None or actual_xg.get("away_xg") is None:
            warnings.append("TheStatsAPI 当前未返回可用真实xG，后续使用赛前proxy xG")

        return TheStatsAPIMatchProbe(
            provider="TheStatsAPI",
            available=True,
            match_id=match_id,
            competition_id=detail_data.get("competition_id"),
            season_id=detail_data.get("season_id"),
            status=detail_data.get("status"),
            home_team_id=(detail_data.get("home_team") or {}).get("id"),
            away_team_id=(detail_data.get("away_team") or {}).get("id"),
            venue=detail_data.get("venue") or {},
            referee=detail_data.get("referee") or {},
            xg_available=bool(detail_data.get("xg_available")) and actual_xg.get("home_xg") is not None,
            actual_xg=actual_xg,
            odds_summary=self._extract_odds_summary(odds),
            endpoint_statuses=endpoint_statuses,
            warnings=warnings,
            raw={
                "match": detail_data,
                "stats_error": self._error_message(stats),
                "shotmap_error": self._error_message(shotmap),
                "lineups_error": self._error_message(lineups),
                "odds_error": self._error_message(odds),
            },
        )

    def _find_match(
        self,
        home_name: str,
        away_name: str,
        match_date: Optional[str],
        competition_hint: Optional[str],
    ) -> Tuple[Optional[Dict[str, Any]], List[str], Dict[str, Any]]:
        warnings: List[str] = []
        raw: Dict[str, Any] = {}
        home_l = home_name.lower()
        away_l = away_name.lower()

        queries: List[Dict[str, Any]] = []
        if match_date:
            for date in self._date_candidates(match_date):
                queries.append({"date": date, "per_page": 100})
            dates = self._date_candidates(match_date)
            if len(dates) >= 2:
                queries.append({"date_from": dates[0], "date_to": dates[-1], "per_page": 100})
        queries.extend([
            {"search": f"{home_name} {away_name}", "per_page": 100},
            {"search": home_name, "per_page": 100},
            {"search": away_name, "per_page": 100},
        ])

        if competition_hint:
            competition = self._competition_search(competition_hint)
            raw["competition_search"] = competition
            for item in self._list_data(competition):
                comp_id = item.get("id")
                if comp_id:
                    queries.append({"competition_id": comp_id, "season": 2026, "per_page": 100})

        for idx, params in enumerate(queries):
            response = self._get("/football/matches", params)
            raw[f"match_search_{idx}"] = {
                "params": params,
                "status_code": response.get("status_code"),
                "error": self._error_message(response),
            }
            data = self._list_data(response)
            for match in data:
                blob = str(match).lower()
                if home_l in blob and away_l in blob:
                    return match, warnings, raw

        warnings.append("TheStatsAPI 比赛搜索未命中")
        return None, warnings, raw

    def _competition_search(self, text: str) -> Dict[str, Any]:
        return self._get("/football/competitions", {"search": text, "per_page": 50})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                params=params or {},
                timeout=self.timeout,
            )
            try:
                body = response.json()
            except ValueError:
                body = {"_raw_text": response.text[:1000]}
            return {"status_code": response.status_code, "body": body}
        except requests.RequestException as exc:
            return {"error": str(exc)}

    @staticmethod
    def _data(response: Dict[str, Any]) -> Any:
        body = response.get("body")
        if isinstance(body, dict):
            return body.get("data")
        return None

    @staticmethod
    def _list_data(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = TheStatsAPIClient._data(response)
        return data if isinstance(data, list) else []

    @staticmethod
    def _error_message(response: Dict[str, Any]) -> Optional[str]:
        if response.get("error"):
            return str(response["error"])
        body = response.get("body")
        if isinstance(body, dict) and body.get("error"):
            err = body["error"]
            if isinstance(err, dict):
                return err.get("message") or str(err)
            return str(err)
        return None

    @staticmethod
    def _date_candidates(match_date: str) -> List[str]:
        try:
            dt = datetime.strptime(match_date[:10], "%Y-%m-%d")
        except ValueError:
            return [match_date[:10]]
        return [
            (dt - timedelta(days=1)).strftime("%Y-%m-%d"),
            dt.strftime("%Y-%m-%d"),
            (dt + timedelta(days=1)).strftime("%Y-%m-%d"),
        ]

    @staticmethod
    def _extract_actual_xg(stats: Dict[str, Any], shotmap: Dict[str, Any]) -> Dict[str, Optional[float]]:
        values = {
            "home_xg": None,
            "away_xg": None,
            "home_npxg": None,
            "away_npxg": None,
            "source": None,
        }

        data = TheStatsAPIClient._data(stats)
        if isinstance(data, dict):
            overview = data.get("overview") or data
            xg = overview.get("expected_goals") or overview.get("xg")
            npxg = overview.get("np_expected_goals") or overview.get("npxg")
            parsed_xg = TheStatsAPIClient._parse_home_away_value(xg)
            parsed_npxg = TheStatsAPIClient._parse_home_away_value(npxg)
            if parsed_xg:
                values["home_xg"], values["away_xg"] = parsed_xg
                values["source"] = "match_stats"
            if parsed_npxg:
                values["home_npxg"], values["away_npxg"] = parsed_npxg

        body = shotmap.get("body") if isinstance(shotmap, dict) else None
        if isinstance(body, dict):
            summary = body.get("np_xg_summary") or {}
            stored = summary.get("stored") or {}
            live = summary.get("live") or {}
            source_summary = stored if any(stored.values()) else live
            home = TheStatsAPIClient._safe_float(source_summary.get("home_team"))
            away = TheStatsAPIClient._safe_float(source_summary.get("away_team"))
            if home is not None and away is not None and (home > 0 or away > 0):
                values["home_npxg"] = home
                values["away_npxg"] = away
                if values["home_xg"] is None:
                    values["home_xg"] = home
                    values["away_xg"] = away
                    values["source"] = "shotmap_np_xg_summary"

        return values

    @staticmethod
    def _parse_home_away_value(value: Any) -> Optional[Tuple[float, float]]:
        if isinstance(value, dict):
            home = TheStatsAPIClient._safe_float(value.get("home") or value.get("home_team"))
            away = TheStatsAPIClient._safe_float(value.get("away") or value.get("away_team"))
            if home is not None and away is not None:
                return home, away
        if isinstance(value, list) and len(value) >= 2:
            home = TheStatsAPIClient._safe_float(value[0])
            away = TheStatsAPIClient._safe_float(value[1])
            if home is not None and away is not None:
                return home, away
        return None

    @staticmethod
    def _extract_odds_summary(odds: Dict[str, Any]) -> Dict[str, Any]:
        data = TheStatsAPIClient._data(odds)
        if not isinstance(data, dict):
            return {}
        bookmakers = data.get("bookmakers") or []
        match_values: List[List[float]] = []
        total_values: List[float] = []
        for bookmaker in bookmakers:
            markets = bookmaker.get("markets") or {}
            match_odds = markets.get("match_odds") or {}
            try:
                match_values.append([
                    float(match_odds["home"]["last_seen"]),
                    float(match_odds["draw"]["last_seen"]),
                    float(match_odds["away"]["last_seen"]),
                ])
            except (KeyError, TypeError, ValueError):
                pass
            total_goals = markets.get("total_goals") or {}
            if "2.5" in total_goals:
                try:
                    over = float(total_goals["2.5"]["over"]["last_seen"])
                    under = float(total_goals["2.5"]["under"]["last_seen"])
                    implied_over = 1 / over
                    implied_under = 1 / under
                    total_values.append(implied_over / (implied_over + implied_under))
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    pass
        summary: Dict[str, Any] = {"bookmaker_count": len(bookmakers)}
        if match_values:
            avg = [sum(row[i] for row in match_values) / len(match_values) for i in range(3)]
            inv = [1 / value for value in avg]
            total = sum(inv)
            summary["avg_match_odds"] = {"home": avg[0], "draw": avg[1], "away": avg[2]}
            summary["devig_match_probabilities"] = {
                "home": inv[0] / total,
                "draw": inv[1] / total,
                "away": inv[2] / total,
            }
        if total_values:
            summary["avg_over_25_probability"] = sum(total_values) / len(total_values)
        return summary

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _empty_probe(warnings: List[str], raw: Optional[Dict[str, Any]] = None) -> TheStatsAPIMatchProbe:
        return TheStatsAPIMatchProbe(
            provider="TheStatsAPI",
            available=False,
            match_id=None,
            competition_id=None,
            season_id=None,
            status=None,
            home_team_id=None,
            away_team_id=None,
            venue={},
            referee={},
            xg_available=False,
            actual_xg={"home_xg": None, "away_xg": None, "home_npxg": None, "away_npxg": None, "source": None},
            odds_summary={},
            endpoint_statuses={},
            warnings=warnings,
            raw=raw or {},
        )


__all__ = ["TheStatsAPIClient", "TheStatsAPIMatchProbe"]
