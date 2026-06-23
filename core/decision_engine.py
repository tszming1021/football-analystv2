#!/usr/bin/env python3
"""集成决策层。

把泊松、市场、比赛语境、让球、大小球、数据质量和奇门风险整合为
透明的证据评分。第一版使用规则权重，后续可用复盘库校准权重。
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    factor: str
    weight: float
    direction: str
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResult:
    primary_pick: str
    primary_market: str
    confidence: str
    score: float
    no_bet: bool
    parlay_allowed: bool
    result_pick: str
    handicap_pick: Optional[str]
    goals_pick: str
    evidence: List[EvidenceItem]
    warnings: List[str]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = [item.to_dict() for item in self.evidence]
        return payload


class EnsembleDecisionEngine:
    """Final transparent decision model."""

    @staticmethod
    def decide(
        data_report: Any,
        poisson: Any,
        market_signal: Any,
        context: Any,
        handicap_signal: Any,
        goals_signal: Any,
        fusion_report: Optional[Dict[str, Any]] = None,
        qimen: Optional[Dict[str, Any]] = None,
    ) -> DecisionResult:
        evidence: List[EvidenceItem] = []
        warnings: List[str] = []

        result_pick, result_prob = EnsembleDecisionEngine._top_result(data_report, poisson)
        score = 0.0

        # 1X2 evidence.
        if result_prob >= 0.60:
            evidence.append(EvidenceItem("泊松胜平负", 2.5, result_pick, f"最高赛果概率 {result_prob:.1%}"))
            score += 2.5
        elif result_prob >= 0.45:
            evidence.append(EvidenceItem("泊松胜平负", 1.5, result_pick, f"最高赛果概率 {result_prob:.1%}"))
            score += 1.5
        else:
            evidence.append(EvidenceItem("泊松胜平负", 0.5, result_pick, f"最高赛果概率仅 {result_prob:.1%}"))
            score += 0.5
            warnings.append("胜平负分布不集中，不宜作为高权重核心方向")

        if market_signal.favorite:
            market_pick = EnsembleDecisionEngine._market_pick_label(data_report, market_signal.favorite)
            if market_pick == result_pick:
                evidence.append(EvidenceItem("市场隐含概率", 1.5, market_pick, "市场方向与模型一致"))
                score += 1.5
            else:
                evidence.append(EvidenceItem("市场隐含概率", -1.5, market_pick, "市场方向与模型不一致"))
                score -= 1.5
                warnings.append("市场方向与泊松模型冲突，降低推荐级别")

        deviations = EnsembleDecisionEngine._market_deviations(poisson, market_signal)
        max_deviation = max(deviations.values()) if deviations else 0.0
        if max_deviation >= 0.25:
            evidence.append(EvidenceItem("概率偏差保护", -3.0, "观望", f"模型与市场最大偏差 {max_deviation:.1%}"))
            score -= 3.0
            warnings.append("模型与市场概率偏差过大，禁止把单一风险系数作为核心依据")
        elif max_deviation >= 0.15:
            evidence.append(EvidenceItem("概率偏差保护", -1.5, "降低信心", f"模型与市场最大偏差 {max_deviation:.1%}"))
            score -= 1.5
            warnings.append("模型与市场概率偏差较大，降低推荐级别")

        if fusion_report and fusion_report.get("applied"):
            weights = fusion_report.get("weights") or {}
            historical_weight = weights.get("historical", 0)
            market_weight = weights.get("market", 0)
            note = f"当前/市场/历史权重 {weights.get('current', 0):.0%}/{market_weight:.0%}/{historical_weight:.0%}"
            evidence.append(EvidenceItem("历史融合校准", 0.5, "风险校准", note))
            score += 0.5
            warnings.extend(fusion_report.get("warnings") or [])

        if getattr(context, "motivation_score", 0) >= 0.25:
            evidence.append(EvidenceItem(
                "战意/赛程动机",
                1.0,
                "上调强队主动性",
                f"友谊赛类型 {getattr(context, 'friendly_subtype', '-')}, 动机评分 {getattr(context, 'motivation_score', 0):.1%}",
            ))
            score += 1.0

        if getattr(context, "favorite_cover_trigger", False):
            evidence.append(EvidenceItem(
                "强队打穿触发器",
                1.2,
                "反对机械让负",
                "战意、对手减员/年轻化/旅行疲劳组合出现",
            ))
            score += 1.2

        # Handicap evidence.
        handicap_pick = None
        handicap_vetoed = False
        if handicap_signal.line is not None:
            fail_prob = handicap_signal.fail_probability or 0
            cover_prob = handicap_signal.cover_probability or 0
            push_prob = handicap_signal.push_probability or 0
            handicap_options = [
                ("cover", cover_prob, EnsembleDecisionEngine._handicap_cover_pick(data_report, handicap_signal.line)),
                ("push", push_prob, EnsembleDecisionEngine._handicap_push_pick(data_report, handicap_signal.line)),
                ("fail", fail_prob, EnsembleDecisionEngine._handicap_fail_pick(data_report, handicap_signal.line)),
            ]
            best_key, best_prob, best_pick = max(handicap_options, key=lambda item: item[1])
            second_prob = sorted([item[1] for item in handicap_options], reverse=True)[1]

            if best_prob >= second_prob + 0.06:
                handicap_pick = best_pick
                weight = 1.0 if handicap_signal.confidence == "low" else 1.8
                note = f"让胜/让平/让负 {cover_prob:.1%}/{push_prob:.1%}/{fail_prob:.1%}"
                evidence.append(EvidenceItem("让球三项模型", weight, handicap_pick, note))
                score += weight
                if best_key == "push":
                    warnings.append("让平为最高概率但波动高，不建议作为组合核心")
            else:
                warnings.append("让球胜平负三项差距不大，不建议作为组合核心")

            if abs(handicap_signal.line) >= 2 and context.volatility_score >= 0.65:
                evidence.append(EvidenceItem("深让球风控", -2.0, "降低让球信心", "国际赛/深让球波动高"))
                score -= 2.0
                warnings.append("深让球国际赛不允许只按经验句子进入组合")

            if market_signal.market_strength in {"strong_home_deep_handicap", "strong_away_deep_handicap"}:
                if handicap_pick and "让" in handicap_pick and "负" in handicap_pick:
                    evidence.append(EvidenceItem("市场强度否决", -2.0, "反对让负", "市场强势支持热门方深让球"))
                    score -= 2.0
                    handicap_vetoed = True
                    handicap_pick = None
                    warnings.append("市场数字强度支持热门方，取消机械让负倾向")

        # Goals evidence.
        goals_pick = goals_signal.goals_direction
        goals_note = EnsembleDecisionEngine._goals_note(goals_signal)
        if goals_signal.confidence == "high":
            evidence.append(EvidenceItem("进球模型", 1.5, goals_pick, goals_note))
            score += 1.5
        elif goals_signal.confidence == "medium":
            evidence.append(EvidenceItem("进球模型", 1.0, goals_pick, goals_note))
            score += 1.0
        else:
            evidence.append(EvidenceItem("进球模型", 0.3, goals_pick, goals_note))
            score += 0.3

        # Data quality and qimen risk.
        if data_report.data_completeness_score < 80:
            evidence.append(EvidenceItem("数据完整度", -2.0, "观望", f"完整度 {data_report.data_completeness_score:.0f}%"))
            score -= 2.0
            warnings.append("数据完整度不足，不进入组合思路")

        qimen_pick = (qimen or {}).get("qimen_result_prediction")
        if qimen_pick and qimen_pick not in {"-", None}:
            qimen_side = EnsembleDecisionEngine._qimen_to_result_label(data_report, qimen_pick)
            if qimen_side and qimen_side != result_pick:
                evidence.append(EvidenceItem("奇门风险", -0.5, qimen_side, "奇门与数据模型冲突，仅作为波动提示"))
                score -= 0.5
                warnings.append("奇门与模型冲突，不改变主概率，只降低主观权重")

        all_warnings = list(dict.fromkeys(warnings + (context.warnings or []) + (handicap_signal.warnings or []) + (goals_signal.warnings or [])))
        no_bet = score < 1.0 or len(all_warnings) >= 4 or max_deviation >= 0.25
        parlay_allowed = score >= 3.0 and data_report.data_completeness_score >= 85 and context.volatility_score < 0.7 and max_deviation < 0.15
        confidence = EnsembleDecisionEngine._confidence(score, all_warnings)

        primary_market, primary_pick = EnsembleDecisionEngine._choose_primary(
            result_pick=result_pick,
            handicap_pick=handicap_pick,
            goals_pick=goals_pick,
            no_bet=no_bet,
            handicap_vetoed=handicap_vetoed,
        )

        summary = EnsembleDecisionEngine._summary(primary_pick, confidence, score, parlay_allowed, all_warnings)
        return DecisionResult(
            primary_pick=primary_pick,
            primary_market=primary_market,
            confidence=confidence,
            score=round(score, 2),
            no_bet=no_bet,
            parlay_allowed=parlay_allowed,
            result_pick=result_pick,
            handicap_pick=handicap_pick,
            goals_pick=goals_pick,
            evidence=evidence,
            warnings=all_warnings,
            summary=summary,
        )

    @staticmethod
    def _top_result(data_report: Any, poisson: Any) -> tuple:
        home = data_report.parsed_match.home_team_raw
        away = data_report.parsed_match.away_team_raw
        outcomes = [
            (f"{home}胜", poisson.home_win_prob),
            ("平局", poisson.draw_prob),
            (f"{away}胜", poisson.away_win_prob),
        ]
        return max(outcomes, key=lambda item: item[1])

    @staticmethod
    def _market_pick_label(data_report: Any, favorite: str) -> str:
        if favorite == "home":
            return f"{data_report.parsed_match.home_team_raw}胜"
        if favorite == "away":
            return f"{data_report.parsed_match.away_team_raw}胜"
        return "平局"

    @staticmethod
    def _handicap_fail_pick(data_report: Any, line: float) -> str:
        if line < 0:
            return f"{data_report.parsed_match.home_team_raw}让{int(abs(line))}负"
        if line > 0:
            return f"{data_report.parsed_match.home_team_raw}受让{int(abs(line))}负"
        return "无让球"

    @staticmethod
    def _handicap_push_pick(data_report: Any, line: float) -> str:
        if line < 0:
            return f"{data_report.parsed_match.home_team_raw}让{int(abs(line))}平"
        if line > 0:
            return f"{data_report.parsed_match.home_team_raw}受让{int(abs(line))}平"
        return "无让球"

    @staticmethod
    def _handicap_cover_pick(data_report: Any, line: float) -> str:
        if line < 0:
            return f"{data_report.parsed_match.home_team_raw}让{int(abs(line))}胜"
        if line > 0:
            return f"{data_report.parsed_match.home_team_raw}受让{int(abs(line))}胜"
        return "无让球"

    @staticmethod
    def _qimen_to_result_label(data_report: Any, qimen_pick: str) -> Optional[str]:
        if "主" in qimen_pick:
            return f"{data_report.parsed_match.home_team_raw}胜"
        if "客" in qimen_pick:
            return f"{data_report.parsed_match.away_team_raw}胜"
        if "平" in qimen_pick:
            return "平局"
        return None

    @staticmethod
    def _goals_note(goals_signal: Any) -> str:
        exact = getattr(goals_signal, "exact_distribution", None) or {}
        if exact:
            ordered = ["0", "1", "2", "3", "4", "5", "6", "7_plus"]
            dist = " / ".join(
                f"{('7+' if key == '7_plus' else key)} {exact.get(key, 0):.1%}"
                for key in ordered
            )
            debias = "；已触发500去偏" if getattr(goals_signal, "debias_applied", False) else ""
            return f"{dist}{debias}"
        distribution = getattr(goals_signal, "distribution", None) or {}
        if distribution:
            dist = (
                f"0-1 {distribution.get('0_1', 0):.1%} / "
                f"2 {distribution.get('2', 0):.1%} / "
                f"3 {distribution.get('3', 0):.1%} / "
                f"4+ {distribution.get('4_plus', 0):.1%}"
            )
        else:
            dist = f"大于2.5概率 {getattr(goals_signal, 'over_25_probability', 0):.1%}"
        debias = "；已触发500去偏" if getattr(goals_signal, "debias_applied", False) else ""
        return f"{dist}{debias}"

    @staticmethod
    def _market_deviations(poisson: Any, market_signal: Any) -> Dict[str, float]:
        pairs = {
            "home": (poisson.home_win_prob, getattr(market_signal, "implied_home", None)),
            "draw": (poisson.draw_prob, getattr(market_signal, "implied_draw", None)),
            "away": (poisson.away_win_prob, getattr(market_signal, "implied_away", None)),
        }
        return {
            key: abs(model - market)
            for key, (model, market) in pairs.items()
            if model is not None and market is not None
        }

    @staticmethod
    def _confidence(score: float, warnings: List[str]) -> str:
        if score >= 5 and len(warnings) <= 1:
            return "high"
        if score >= 3 and len(warnings) <= 3:
            return "medium"
        return "low"

    @staticmethod
    def _choose_primary(
        result_pick: str,
        handicap_pick: Optional[str],
        goals_pick: str,
        no_bet: bool,
        handicap_vetoed: bool = False,
    ) -> tuple:
        if no_bet:
            return "观望", "不建议作为核心方向"
        if handicap_vetoed:
            return "胜平负/进球数", f"{result_pick}，{goals_pick}；让负已被市场数字强度否决"
        if handicap_pick and "让负" not in handicap_pick:
            return "让球胜平负", handicap_pick
        return "胜平负/进球数", f"{result_pick}，{goals_pick}"

    @staticmethod
    def _summary(primary_pick: str, confidence: str, score: float, parlay_allowed: bool, warnings: List[str]) -> str:
        parlay_text = "可进入低风险组合思路" if parlay_allowed else "不建议进入组合思路"
        warning_text = f"主要风险：{warnings[0]}" if warnings else "主要风险较少"
        return f"{primary_pick}；综合评分 {score:.1f}，信心 {confidence}，{parlay_text}。{warning_text}"


__all__ = ["EvidenceItem", "DecisionResult", "EnsembleDecisionEngine"]
