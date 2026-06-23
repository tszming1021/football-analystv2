#!/usr/bin/env python3
"""
数学建模层 - Mathematical Modeling Layer
包含泊松分布模型、凯利公式、期望值分析
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class BetType(Enum):
    """投注类型"""
    HOME_WIN = "1"
    DRAW = "X"
    AWAY_WIN = "2"
    OVER_25 = "Over 2.5"
    UNDER_25 = "Under 2.5"
    BTTS_YES = "BTTS Yes"
    BTTS_NO = "BTTS No"


@dataclass
class PoissonProbabilities:
    """泊松概率分布"""
    score_probs: Dict[Tuple[int, int], float]  # (home_goals, away_goals) -> probability
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    over_25_prob: float
    under_25_prob: float
    btts_yes_prob: float
    btts_no_prob: float
    most_likely_score: Tuple[int, int]


@dataclass
class KellyResult:
    """凯利公式计算结果"""
    bet_type: str
    odds: float
    probability: float
    kelly_fraction: float  # 建议投注比例
    kelly_amount: float    # 建议投注金额
    expected_value: float  # 期望值
    recommended: bool      # 是否推荐投注
    reason: str           # 推荐理由/不推荐理由


@dataclass
class MatchAnalysis:
    """比赛分析结果"""
    # 泊松分布结果
    poisson: PoissonProbabilities

    # 凯利公式计算
    kelly_results: List[KellyResult]

    # 模型总结
    model_summary: Dict[str, any]

    # 数据使用说明
    data_sources_used: List[str]
    data_quality_score: float  # 0-100


class PoissonModel:
    """泊松分布模型"""

    @staticmethod
    def calculate_lambda(
        goals_scored: float,
        goals_conceded_opponent: float,
        home_advantage: float = 1.36,
        injury_factor: float = 1.0
    ) -> float:
        """
        计算泊松分布的 λ 参数

        λ = 进攻强度 × 对手防守弱点 × 主客场调整 × 伤停调整

        Args:
            goals_scored: 场均进球数
            goals_conceded_opponent: 对手场均失球数
            home_advantage: 主场优势系数 (默认 1.36)
            injury_factor: 伤病调整系数 (1.0 表示无影响)
        """
        lambda_val = (
            goals_scored *
            (goals_conceded_opponent / 1.3) *
            home_advantage *
            injury_factor
        )
        return max(lambda_val, 0.1)  # 最小值 0.1

    @staticmethod
    def poisson_probability(k: int, lam: float) -> float:
        """
        泊松概率质量函数
        P(X = k) = (e^(-λ) * λ^k) / k!
        """
        if k < 0:
            return 0.0
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)

    @staticmethod
    def calculate_match_probabilities(
        home_lambda: float,
        away_lambda: float,
        max_goals: int = 10,
        low_score_rho: float = -0.08,
        zero_inflation: float = 0.0,
    ) -> PoissonProbabilities:
        """
        计算比赛概率分布

        Args:
            home_lambda: 主队预期进球数
            away_lambda: 客队预期进球数
            max_goals: 最大计算进球数

        Returns:
            PoissonProbabilities: 完整的概率分布
        """
        score_probs = {}
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        over_25_prob = 0.0
        under_25_prob = 0.0
        btts_yes_prob = 0.0
        btts_no_prob = 0.0

        max_prob = 0.0
        most_likely_score = (0, 0)

        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # 计算这个比分的概率
                prob = (
                    PoissonModel.poisson_probability(home_goals, home_lambda) *
                    PoissonModel.poisson_probability(away_goals, away_lambda)
                )
                prob *= PoissonModel._dixon_coles_factor(
                    home_goals, away_goals, home_lambda, away_lambda, low_score_rho
                )
                if home_goals == 0 or away_goals == 0:
                    prob *= 1 + max(0.0, zero_inflation)

                score_probs[(home_goals, away_goals)] = prob

                # 累计各种结果的概率
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob

                total_goals = home_goals + away_goals
                if total_goals > 2.5:
                    over_25_prob += prob
                else:
                    under_25_prob += prob

                if home_goals > 0 and away_goals > 0:
                    btts_yes_prob += prob
                else:
                    btts_no_prob += prob

                # 记录最可能的比分
                if prob > max_prob:
                    max_prob = prob
                    most_likely_score = (home_goals, away_goals)

        return PoissonModel._from_score_probs(score_probs, home_lambda, away_lambda)

    @staticmethod
    def calibrate_with_market(
        poisson: PoissonProbabilities,
        implied_home: Optional[float],
        implied_draw: Optional[float],
        implied_away: Optional[float],
        model_weight: float = 0.58,
    ) -> PoissonProbabilities:
        market = [implied_home, implied_draw, implied_away]
        if any(value is None for value in market):
            return poisson
        targets = [
            poisson.home_win_prob * model_weight + float(implied_home) * (1 - model_weight),
            poisson.draw_prob * model_weight + float(implied_draw) * (1 - model_weight),
            poisson.away_win_prob * model_weight + float(implied_away) * (1 - model_weight),
        ]
        total = sum(targets)
        targets = [value / total for value in targets]
        current = [poisson.home_win_prob, poisson.draw_prob, poisson.away_win_prob]
        factors = [targets[i] / current[i] if current[i] > 0 else 1.0 for i in range(3)]
        adjusted = {}
        for (home_goals, away_goals), prob in poisson.score_probs.items():
            idx = 0 if home_goals > away_goals else (1 if home_goals == away_goals else 2)
            adjusted[(home_goals, away_goals)] = prob * factors[idx]
        return PoissonModel._from_score_probs(
            adjusted, poisson.expected_home_goals, poisson.expected_away_goals
        )

    @staticmethod
    def friendly_lambda_adjustment(home_lambda: float, away_lambda: float) -> Tuple[float, float]:
        """Shrink international-friendly scoring estimates and reduce assumed home advantage."""
        mean = (home_lambda + away_lambda) / 2
        home = 0.82 * home_lambda + 0.18 * mean
        away = 0.88 * away_lambda + 0.12 * mean
        return max(0.2, home * 0.96), max(0.2, away * 0.98)

    @staticmethod
    def _dixon_coles_factor(home_goals: int, away_goals: int, home_lambda: float, away_lambda: float, rho: float) -> float:
        if home_goals == 0 and away_goals == 0:
            return max(0.2, 1 - home_lambda * away_lambda * rho)
        if home_goals == 0 and away_goals == 1:
            return max(0.2, 1 + home_lambda * rho)
        if home_goals == 1 and away_goals == 0:
            return max(0.2, 1 + away_lambda * rho)
        if home_goals == 1 and away_goals == 1:
            return max(0.2, 1 - rho)
        return 1.0

    @staticmethod
    def _from_score_probs(
        score_probs: Dict[Tuple[int, int], float],
        home_lambda: float,
        away_lambda: float,
    ) -> PoissonProbabilities:
        total = sum(score_probs.values()) or 1.0
        normalized = {score: prob / total for score, prob in score_probs.items()}
        home_win = sum(prob for (h, a), prob in normalized.items() if h > a)
        draw = sum(prob for (h, a), prob in normalized.items() if h == a)
        away_win = sum(prob for (h, a), prob in normalized.items() if h < a)
        over = sum(prob for (h, a), prob in normalized.items() if h + a > 2.5)
        btts = sum(prob for (h, a), prob in normalized.items() if h > 0 and a > 0)
        likely = max(normalized.items(), key=lambda item: item[1])[0]
        return PoissonProbabilities(
            score_probs=normalized,
            home_win_prob=home_win,
            draw_prob=draw,
            away_win_prob=away_win,
            expected_home_goals=home_lambda,
            expected_away_goals=away_lambda,
            over_25_prob=over,
            under_25_prob=1 - over,
            btts_yes_prob=btts,
            btts_no_prob=1 - btts,
            most_likely_score=likely,
        )


class KellyCriterion:
    """凯利公式计算器"""

    @staticmethod
    def calculate(
        probability: float,
        odds: float,
        bankroll: float,
        kelly_fraction: float = 0.25
    ) -> KellyResult:
        """
        计算凯利公式

        Args:
            probability: 真实胜率 (0-1)
            odds: 赔率 (十进制)
            bankroll: 总资金
            kelly_fraction: 凯利分数 (0.25 表示 1/4 凯利)

        Returns:
            KellyResult: 计算结果
        """
        # 净赔率
        b = odds - 1
        p = probability
        q = 1 - p

        # 凯利公式: f* = (bp - q) / b
        if b <= 0:
            kelly_fraction_value = 0
        else:
            kelly_fraction_value = (b * p - q) / b

        # 应用凯利分数
        kelly_fraction_value = kelly_fraction_value * kelly_fraction

        # 计算投注金额
        kelly_amount = bankroll * max(0, kelly_fraction_value)

        # 计算期望值
        expected_value = (p * b) - q

        # 决定是否推荐
        recommended = kelly_fraction_value > 0 and expected_value > 0

        # 生成理由
        if recommended:
            reason = f"正EV (+{expected_value:.1%})，凯利建议投注 {kelly_fraction_value:.2%}"
        elif expected_value <= 0:
            reason = f"负EV ({expected_value:.1%})，不建议投注"
        else:
            reason = "凯利值为负，不建议投注"

        return KellyResult(
            bet_type="Unknown",
            odds=odds,
            probability=probability,
            kelly_fraction=kelly_fraction_value,
            kelly_amount=kelly_amount,
            expected_value=expected_value,
            recommended=recommended,
            reason=reason
        )

    @staticmethod
    def calculate_all(
        poisson_probs: PoissonProbabilities,
        odds: Dict[str, float],
        bankroll: float,
        kelly_fraction: float = 0.25
    ) -> List[KellyResult]:
        """
        计算所有投注选项的凯利值

        Args:
            poisson_probs: 泊松概率分布
            odds: 赔率字典 {'home': 1.65, 'draw': 3.5, 'away': 5.4}
            bankroll: 总资金
            kelly_fraction: 凯利分数

        Returns:
            List[KellyResult]: 各选项的计算结果
        """
        results = []

        # 定义投注选项
        bets = [
            ('主胜', poisson_probs.home_win_prob, odds.get('home', 0)),
            ('平局', poisson_probs.draw_prob, odds.get('draw', 0)),
            ('客胜', poisson_probs.away_win_prob, odds.get('away', 0)),
            ('大球 2.5', poisson_probs.over_25_prob, odds.get('over_25', 0)),
            ('小球 2.5', poisson_probs.under_25_prob, odds.get('under_25', 0)),
            ('双方进球', poisson_probs.btts_yes_prob, odds.get('btts_yes', 0)),
            ('双方不进球', poisson_probs.btts_no_prob, odds.get('btts_no', 0)),
        ]

        for bet_name, prob, odd in bets:
            if odd <= 0:
                continue

            result = KellyCriterion.calculate(
                probability=prob,
                odds=odd,
                bankroll=bankroll,
                kelly_fraction=kelly_fraction
            )
            result.bet_type = bet_name

            results.append(result)

        # 按期望值排序
        results.sort(key=lambda x: x.expected_value, reverse=True)

        return results


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'PoissonProbabilities',
    'KellyResult',
    'MatchAnalysis',
    'PoissonModel',
    'KellyCriterion',
    'BetType',
]
