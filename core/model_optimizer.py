#!/usr/bin/env python3
"""Model optimization from post-match review samples.

This module does not train a black-box model. It turns reviewed matches into
auditable calibration metrics and conservative optimization suggestions for
the decision-iteration layer.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


RESULT_KEYS = ("home", "draw", "away")


@dataclass
class ReviewSample:
    match_id: str
    competition_type: str
    stage: str
    home: str
    away: str
    actual_score: str
    result_probabilities: Dict[str, float]
    handicap_line: Optional[float] = None
    handicap_probabilities: Dict[str, float] = field(default_factory=dict)
    total_distribution: Dict[str, float] = field(default_factory=dict)
    scorelines: List[str] = field(default_factory=list)
    main_pick: str = ""
    main_market: str = ""
    main_probability: Optional[float] = None
    applied_rules: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ReviewSample":
        return cls(
            match_id=str(payload["match_id"]),
            competition_type=str(payload.get("competition_type") or ""),
            stage=str(payload.get("stage") or ""),
            home=str(payload.get("home") or ""),
            away=str(payload.get("away") or ""),
            actual_score=str(payload["actual_score"]),
            result_probabilities=_normalize_result(payload.get("result_probabilities") or {}),
            handicap_line=_optional_float(payload.get("handicap_line")),
            handicap_probabilities=_normalize(payload.get("handicap_probabilities") or {}),
            total_distribution=_normalize(payload.get("total_distribution") or {}),
            scorelines=[str(item) for item in payload.get("scorelines", [])],
            main_pick=str(payload.get("main_pick") or ""),
            main_market=str(payload.get("main_market") or ""),
            main_probability=_optional_float(payload.get("main_probability")),
            applied_rules=[str(item) for item in payload.get("applied_rules", [])],
            tags=[str(item) for item in payload.get("tags", [])],
            notes=str(payload.get("notes") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SampleEvaluation:
    match_id: str
    fixture: str
    actual_score: str
    actual_result: str
    result_top_pick: str
    result_top_hit: bool
    main_pick: str
    main_hit: Optional[bool]
    score_top3_hit: bool
    total_bucket_hit: bool
    brier: float
    log_loss: float
    applied_rules: List[str]
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationReport:
    samples: int
    result_top_hit_rate: float
    main_hit_rate: Optional[float]
    score_top3_hit_rate: float
    total_bucket_hit_rate: float
    brier: float
    log_loss: float
    by_competition: Dict[str, Dict[str, Any]]
    rule_diagnostics: Dict[str, Dict[str, Any]]
    tag_diagnostics: Dict[str, Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    evaluations: List[SampleEvaluation]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["evaluations"] = [item.to_dict() for item in self.evaluations]
        return payload


class ModelReviewOptimizer:
    """Evaluate reviewed samples and propose conservative calibration actions."""

    def __init__(self, samples: Sequence[ReviewSample]):
        self.samples = list(samples)

    @classmethod
    def from_json(cls, path: Path | str) -> "ModelReviewOptimizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        items = payload.get("samples", payload if isinstance(payload, list) else [])
        return cls([ReviewSample.from_dict(item) for item in items])

    def evaluate(self) -> OptimizationReport:
        evaluations = [self._evaluate_sample(sample) for sample in self.samples]
        samples = len(evaluations)
        if not samples:
            return OptimizationReport(
                samples=0,
                result_top_hit_rate=0.0,
                main_hit_rate=None,
                score_top3_hit_rate=0.0,
                total_bucket_hit_rate=0.0,
                brier=0.0,
                log_loss=0.0,
                by_competition={},
                rule_diagnostics={},
                tag_diagnostics={},
                suggestions=[],
                evaluations=[],
            )

        main_hits = [item.main_hit for item in evaluations if item.main_hit is not None]
        by_competition = self._bucket(evaluations, key_fn=lambda item: self._sample_by_id(item.match_id).competition_type or "unknown")
        rule_diagnostics = self._diagnostics(evaluations, attr="applied_rules")
        tag_diagnostics = self._diagnostics(evaluations, attr="tags")
        suggestions = self._suggestions(evaluations, rule_diagnostics, tag_diagnostics)

        return OptimizationReport(
            samples=samples,
            result_top_hit_rate=_rate(item.result_top_hit for item in evaluations),
            main_hit_rate=_rate(main_hits) if main_hits else None,
            score_top3_hit_rate=_rate(item.score_top3_hit for item in evaluations),
            total_bucket_hit_rate=_rate(item.total_bucket_hit for item in evaluations),
            brier=sum(item.brier for item in evaluations) / samples,
            log_loss=sum(item.log_loss for item in evaluations) / samples,
            by_competition=by_competition,
            rule_diagnostics=rule_diagnostics,
            tag_diagnostics=tag_diagnostics,
            suggestions=suggestions,
            evaluations=evaluations,
        )

    def _evaluate_sample(self, sample: ReviewSample) -> SampleEvaluation:
        home_goals, away_goals = _parse_score(sample.actual_score)
        actual_result = _actual_result_key(home_goals, away_goals)
        result_top_pick = max(RESULT_KEYS, key=lambda key: sample.result_probabilities.get(key, 0.0))
        y = {key: 1.0 if key == actual_result else 0.0 for key in RESULT_KEYS}
        brier = sum((sample.result_probabilities.get(key, 0.0) - y[key]) ** 2 for key in RESULT_KEYS)
        actual_probability = min(1 - 1e-6, max(1e-6, sample.result_probabilities.get(actual_result, 0.0)))
        log_loss = -math.log(actual_probability)
        actual_total = home_goals + away_goals

        return SampleEvaluation(
            match_id=sample.match_id,
            fixture=f"{sample.home} vs {sample.away}",
            actual_score=sample.actual_score,
            actual_result=actual_result,
            result_top_pick=result_top_pick,
            result_top_hit=result_top_pick == actual_result,
            main_pick=sample.main_pick,
            main_hit=_evaluate_main_pick(sample, home_goals, away_goals),
            score_top3_hit=sample.actual_score.replace(":", "-") in [score.replace(":", "-") for score in sample.scorelines[:3]],
            total_bucket_hit=_total_bucket_hit(sample, actual_total),
            brier=brier,
            log_loss=log_loss,
            applied_rules=list(sample.applied_rules),
            tags=list(sample.tags),
        )

    def _sample_by_id(self, match_id: str) -> ReviewSample:
        for sample in self.samples:
            if sample.match_id == match_id:
                return sample
        raise KeyError(match_id)

    @staticmethod
    def _bucket(evaluations: Sequence[SampleEvaluation], key_fn) -> Dict[str, Dict[str, Any]]:
        buckets: Dict[str, List[SampleEvaluation]] = {}
        for evaluation in evaluations:
            buckets.setdefault(str(key_fn(evaluation)), []).append(evaluation)
        return {key: _summary_for(items) for key, items in buckets.items()}

    @staticmethod
    def _diagnostics(evaluations: Sequence[SampleEvaluation], attr: str) -> Dict[str, Dict[str, Any]]:
        buckets: Dict[str, List[SampleEvaluation]] = {}
        for evaluation in evaluations:
            values = getattr(evaluation, attr)
            for value in values:
                buckets.setdefault(str(value), []).append(evaluation)
        return {key: _summary_for(items) for key, items in sorted(buckets.items())}

    @staticmethod
    def _suggestions(
        evaluations: Sequence[SampleEvaluation],
        rule_diagnostics: Dict[str, Dict[str, Any]],
        tag_diagnostics: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []

        if _rate(item.result_top_hit for item in evaluations) < _rate(item.main_hit for item in evaluations if item.main_hit is not None):
            suggestions.append({
                "action": "keep_decision_iteration_as_active_overlay",
                "reason": "主推命中率高于胜平负Top1，说明让球/保护层仍在纠正三向模型偏差。",
                "implementation": "正式报告继续同时输出原模型Top1和迭代后主推，复盘分别计分。",
            })

        for rule, stats in rule_diagnostics.items():
            if stats["matches"] < 5:
                suggestions.append({
                    "action": "observe_rule",
                    "rule": rule,
                    "reason": f"样本数{stats['matches']}不足，暂不升权，只保留影子/提示效果。",
                })
            elif stats["main_hit_rate"] is not None and stats["main_hit_rate"] >= 0.60:
                suggestions.append({
                    "action": "promote_rule_weight",
                    "rule": rule,
                    "reason": f"样本数{stats['matches']}且主推命中率{stats['main_hit_rate']:.1%}，可小幅提高该规则输出权重。",
                    "max_delta": 0.015,
                })
            elif stats["main_hit_rate"] is not None and stats["main_hit_rate"] < 0.45:
                suggestions.append({
                    "action": "downgrade_rule_weight",
                    "rule": rule,
                    "reason": f"样本数{stats['matches']}且主推命中率{stats['main_hit_rate']:.1%}偏低，需要降权或收紧触发条件。",
                    "max_delta": -0.015,
                })

        if tag_diagnostics.get("plus_one_push_split"):
            suggestions.append({
                "action": "split_plus_one_reporting",
                "reason": "+1卡线类样本已出现，报告和复盘必须拆分让胜/让平。",
                "implementation": "总推荐表新增让平卡线字段，主推命中和方向接近分开统计。",
            })

        if tag_diagnostics.get("open_league_high_variance"):
            suggestions.append({
                "action": "expand_open_league_score_tail",
                "reason": "开放联赛高比分尾部容易漏掉精确比分。",
                "implementation": "瑞超/开放联赛Top5风险池固定检查2-3、2-4、3-2、3-3。",
            })

        return suggestions


def write_report(report: OptimizationReport, output_json: Path | str, output_md: Path | str) -> None:
    output_json = Path(output_json)
    output_md = Path(output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_render_markdown(report), encoding="utf-8")


def _render_markdown(report: OptimizationReport) -> str:
    lines = [
        "# 模型优化评估报告",
        "",
        "## 一、总体指标",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 样本数 | {report.samples} |",
        f"| 主推命中率 | {_fmt_rate(report.main_hit_rate)} |",
        f"| 胜平负Top1命中率 | {_fmt_rate(report.result_top_hit_rate)} |",
        f"| 比分Top3命中率 | {_fmt_rate(report.score_top3_hit_rate)} |",
        f"| 总球区间命中率 | {_fmt_rate(report.total_bucket_hit_rate)} |",
        f"| 三向Brier | {report.brier:.3f} |",
        f"| 三向LogLoss | {report.log_loss:.3f} |",
        "",
        "## 二、赛事分组",
        "",
        "| 分组 | 样本 | 主推 | 胜平负Top1 | 比分Top3 | 总球 | Brier |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, stats in report.by_competition.items():
        lines.append(
            f"| {key} | {stats['matches']} | {_fmt_rate(stats['main_hit_rate'])} | "
            f"{_fmt_rate(stats['result_top_hit_rate'])} | {_fmt_rate(stats['score_top3_hit_rate'])} | "
            f"{_fmt_rate(stats['total_bucket_hit_rate'])} | {stats['brier']:.3f} |"
        )
    lines += [
        "",
        "## 三、规则诊断",
        "",
        "| 规则 | 样本 | 主推 | 胜平负Top1 | Brier | 建议状态 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for rule, stats in report.rule_diagnostics.items():
        state = "观察"
        if stats["matches"] >= 5 and (stats["main_hit_rate"] or 0) >= 0.60:
            state = "可小幅升权"
        elif stats["matches"] >= 5 and (stats["main_hit_rate"] or 0) < 0.45:
            state = "需降权/收紧"
        lines.append(
            f"| `{rule}` | {stats['matches']} | {_fmt_rate(stats['main_hit_rate'])} | "
            f"{_fmt_rate(stats['result_top_hit_rate'])} | {stats['brier']:.3f} | {state} |"
        )
    lines += [
        "",
        "## 四、优化建议",
        "",
    ]
    for index, suggestion in enumerate(report.suggestions, start=1):
        target = suggestion.get("rule") or suggestion.get("action")
        lines.append(f"{index}. **{target}**：{suggestion.get('reason', '')}")
        if suggestion.get("implementation"):
            lines.append(f"   - 执行：{suggestion['implementation']}")
    lines += [
        "",
        "## 五、逐场样本",
        "",
        "| 场次 | 比分 | 主推 | 主推命中 | 胜平负Top1 | Top1命中 | 比分Top3 | 总球 | Brier |",
        "|---|---|---|---|---|---|---|---|---:|",
    ]
    for item in report.evaluations:
        lines.append(
            f"| {item.match_id} {item.fixture} | {item.actual_score} | {item.main_pick} | "
            f"{_yes_no(item.main_hit)} | {item.result_top_pick} | {_yes_no(item.result_top_hit)} | "
            f"{_yes_no(item.score_top3_hit)} | {_yes_no(item.total_bucket_hit)} | {item.brier:.3f} |"
        )
    return "\n".join(lines) + "\n"


def _summary_for(items: Sequence[SampleEvaluation]) -> Dict[str, Any]:
    main_hits = [item.main_hit for item in items if item.main_hit is not None]
    return {
        "matches": len(items),
        "main_hit_rate": _rate(main_hits) if main_hits else None,
        "result_top_hit_rate": _rate(item.result_top_hit for item in items),
        "score_top3_hit_rate": _rate(item.score_top3_hit for item in items),
        "total_bucket_hit_rate": _rate(item.total_bucket_hit for item in items),
        "brier": sum(item.brier for item in items) / len(items),
    }


def _evaluate_main_pick(sample: ReviewSample, home_goals: int, away_goals: int) -> Optional[bool]:
    pick = sample.main_pick
    if not pick:
        return None
    primary_pick = pick.split("防", 1)[0].replace("，", "").replace(",", "").strip() or pick
    if "让" in pick and sample.handicap_line is not None:
        adjusted = home_goals + sample.handicap_line - away_goals
        if "让胜" in primary_pick:
            if _mentions_away(sample, primary_pick):
                return adjusted < 0
            return adjusted > 0
        if "让平" in primary_pick:
            return adjusted == 0
        if "让负" in primary_pick:
            if _mentions_away(sample, primary_pick):
                return adjusted > 0
            return adjusted < 0
    if "主胜" in pick or (_mentions_home(sample, pick) and "胜" in pick):
        return home_goals > away_goals
    if "客胜" in pick or (_mentions_away(sample, pick) and "胜" in pick):
        return away_goals > home_goals
    if "胜" in pick and "平" not in pick:
        return home_goals > away_goals
    if "平" in pick and "让" not in pick:
        return home_goals == away_goals
    return None


def _mentions_home(sample: ReviewSample, text: str) -> bool:
    return _team_token(sample.home) in text


def _mentions_away(sample: ReviewSample, text: str) -> bool:
    return _team_token(sample.away) in text


def _team_token(team: str) -> str:
    token = team.replace("FC", "").replace("IF", "").replace("BK", "")
    return token.strip()


def _total_bucket_hit(sample: ReviewSample, actual_total: int) -> bool:
    if not sample.scorelines:
        return False
    predicted_totals = set()
    for score in sample.scorelines[:3]:
        try:
            home, away = _parse_score(score)
        except ValueError:
            continue
        predicted_totals.add(home + away)
    return actual_total in predicted_totals


def _parse_score(score: str) -> Tuple[int, int]:
    parts = score.replace(":", "-").split("-")
    if len(parts) != 2:
        raise ValueError(f"invalid score: {score}")
    return int(parts[0]), int(parts[1])


def _actual_result_key(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


def _normalize_result(payload: Dict[str, Any]) -> Dict[str, float]:
    return {key: float(payload.get(key, 0.0) or 0.0) for key in RESULT_KEYS}


def _normalize(payload: Dict[str, Any]) -> Dict[str, float]:
    return {str(key): float(value or 0.0) for key, value in payload.items()}


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    return float(value)


def _rate(values: Iterable[Optional[bool]]) -> float:
    values = [value for value in values if value is not None]
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)


def _fmt_rate(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.1%}"


def _yes_no(value: Optional[bool]) -> str:
    if value is None:
        return "-"
    return "是" if value else "否"


__all__ = [
    "ModelReviewOptimizer",
    "OptimizationReport",
    "ReviewSample",
    "SampleEvaluation",
    "write_report",
]
