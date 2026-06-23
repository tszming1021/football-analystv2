#!/usr/bin/env python3
"""
风险管理层 - Risk Management Layer
负责用户参数设置和投注策略生成
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class KellyFractionOption(Enum):
    """凯利分数选项"""
    QUARTER = 0.25    # 1/4 凯利
    HALF = 0.50       # 1/2 凯利
    FULL = 1.00       # 全凯利 (不推荐)


@dataclass
class UserRiskParameters:
    """用户风险参数设置"""
    # 资金管理
    bankroll: float = 10000.0              # 总资金
    max_bet_percentage: float = 5.0        # 单注最大占资金比例(%)

    # 赔率范围
    min_odds: float = 1.50                 # 赔率下限
    max_odds: float = 3.50                 # 赔率上限

    # 凯利公式设置
    kelly_fraction: float = 0.25           # 凯利分数 (默认1/4凯利)

    # 串关设置
    allow_parlay: bool = False               # 是否允许串关
    max_parlay_leg: int = 3                  # 最大串关场数

    # 投注倍数 (足彩2元一注)
    bet_multiplier: int = 1                  # 投注倍数 (1倍=2元, 5倍=10元)

    # EV阈值
    min_ev_threshold: float = 0.03           # 最小EV阈值 (3%)

    # 其他设置
    preferred_bet_types: List[str] = field(default_factory=lambda: ['1X2', 'AH', 'OU'])  # 偏好的投注类型

    def validate(self) -> Tuple[bool, str]:
        """验证参数设置是否合理"""
        errors = []

        if self.bankroll <= 0:
            errors.append("总资金必须大于0")

        if self.max_bet_percentage <= 0 or self.max_bet_percentage > 100:
            errors.append("单注最大占比必须在0-100之间")

        if self.min_odds <= 1.0:
            errors.append("赔率下限必须大于1.0")

        if self.max_odds <= self.min_odds:
            errors.append("赔率上限必须大于赔率下限")

        if self.kelly_fraction <= 0 or self.kelly_fraction > 2:
            errors.append("凯利分数不合理")

        if self.bet_multiplier < 1:
            errors.append("投注倍数必须至少为1")

        if errors:
            return False, "; ".join(errors)

        return True, "参数验证通过"


@dataclass
class BettingStrategy:
    """投注策略"""
    # 推荐投注
    recommended_bets: List[Dict]  # 每条推荐包含类型、赔率、金额、理由

    # 资金分配
    total_stake: float
    stake_breakdown: Dict[str, float]

    # 预期收益
    expected_return: float
    expected_roi: float

    # 风险提示
    risk_level: str  # 'Low', 'Medium', 'High'
    risk_warnings: List[str]

    # 策略说明
    strategy_summary: str


class RiskManager:
    """风险管理器 - 主类"""

    @staticmethod
    def get_user_parameters_interactive() -> UserRiskParameters:
        """交互式获取用户风险参数"""
        print("\n" + "=" * 60)
        print("⚙️  风险参数设置")
        print("=" * 60)

        params = UserRiskParameters()

        # 1. 总资金
        while True:
            try:
                bankroll_input = input(f"\n1. 总资金 (默认 {params.bankroll:.0f}): ").strip()
                if bankroll_input:
                    params.bankroll = float(bankroll_input)
                break
            except ValueError:
                print("请输入有效的数字")

        # 2. 单注最大占比
        while True:
            try:
                max_pct_input = input(f"\n2. 单注最大占资金比例 %% (默认 {params.max_bet_percentage:.0f}%%): ").strip()
                if max_pct_input:
                    params.max_bet_percentage = float(max_pct_input)
                break
            except ValueError:
                print("请输入有效的数字")

        # 3. 赔率范围
        while True:
            try:
                min_odds_input = input(f"\n3. 赔率下限 (默认 {params.min_odds:.2f}): ").strip()
                if min_odds_input:
                    params.min_odds = float(min_odds_input)

                max_odds_input = input(f"   赔率上限 (默认 {params.max_odds:.2f}): ").strip()
                if max_odds_input:
                    params.max_odds = float(max_odds_input)
                break
            except ValueError:
                print("请输入有效的数字")

        # 4. 凯利分数选择
        print(f"\n4. 凯利公式分数选择:")
        print("   [1] 1/4 凯利 (保守，推荐) - 凯利值的25%%")
        print("   [2] 1/2 凯利 (平衡) - 凯利值的50%%")
        print("   [3] 全凯利 (激进，不推荐) - 凯利值的100%%")

        kelly_choice = input("   选择 (默认 1): ").strip() or "1"
        if kelly_choice == "2":
            params.kelly_fraction = 0.50
        elif kelly_choice == "3":
            params.kelly_fraction = 1.00
        else:
            params.kelly_fraction = 0.25

        # 5. 串关设置
        print(f"\n5. 串关设置:")
        parlay_input = input("   是否允许串关过关? (y/n, 默认 n): ").strip().lower()
        params.allow_parlay = parlay_input == 'y'

        if params.allow_parlay:
            max_leg_input = input("   最大串关场数 (默认 3): ").strip()
            if max_leg_input:
                params.max_parlay_leg = int(max_leg_input)

        # 6. 投注倍数
        while True:
            try:
                multiplier_input = input(f"\n6. 投注倍数 (默认 {params.bet_multiplier}倍, 2元/注): ").strip()
                if multiplier_input:
                    params.bet_multiplier = int(multiplier_input)
                break
            except ValueError:
                print("请输入有效的整数")

        print(f"\n   💰 每注金额: {params.bet_multiplier * 2} 元")

        # 验证参数
        valid, message = params.validate()
        if not valid:
            print(f"\n❌ 参数验证失败: {message}")
            return RiskManager.get_user_parameters_interactive()

        print("\n" + "=" * 60)
        print("✅ 风险参数设置完成")
        print("=" * 60)

        return params

    @staticmethod
    def generate_betting_strategy(
        user_params: UserRiskParameters,
        kelly_results: List[KellyResult],
        llm_analysis: Optional[Any] = None,
        data_quality_score: float = 0.0
    ) -> BettingStrategy:
        """
        生成投注策略

        根据用户参数和分析结果，生成最终的投注建议
        """

        strategy = BettingStrategy(
            recommended_bets=[],
            total_stake=0.0,
            stake_breakdown={},
            expected_return=0.0,
            expected_roi=0.0,
            risk_level='Medium',
            risk_warnings=[],
            strategy_summary=""
        )

        # 筛选符合用户条件的推荐
        filtered_bets = []

        for kr in kelly_results:
            # 检查赔率范围
            if not (user_params.min_odds <= kr.odds <= user_params.max_odds):
                continue

            # 检查EV阈值
            if kr.expected_value < user_params.min_ev_threshold:
                continue

            # 检查是否推荐
            if not kr.recommended:
                continue

            # 计算投注金额
            raw_kelly_amount = kr.kelly_amount

            # 应用用户设置的凯利分数
            adjusted_amount = raw_kelly_amount * (user_params.kelly_fraction / 0.25)

            # 应用单注最大限制
            max_allowed = user_params.bankroll * (user_params.max_bet_percentage / 100)
            final_amount = min(adjusted_amount, max_allowed)

            # 应用投注倍数
            final_amount = round(final_amount / (user_params.bet_multiplier * 2)) * (user_params.bet_multiplier * 2)

            if final_amount > 0:
                filtered_bets.append({
                    'bet_type': kr.bet_type,
                    'odds': kr.odds,
                    'probability': kr.probability,
                    'stake': final_amount,
                    'expected_value': kr.expected_value,
                    'reason': kr.reason,
                    'expected_return': final_amount * (kr.odds - 1) * kr.probability - final_amount * (1 - kr.probability)
                })

        # 如果没有符合条件的推荐
        if not filtered_bets:
            strategy.strategy_summary = "根据当前参数设置和数据分析，没有找到符合投注条件的推荐。建议观望或调整参数。"
            strategy.risk_level = 'Low'
            strategy.risk_warnings = [
                "当前赔率范围可能没有正期望值选项",
                "建议关注临场赔率变化",
                "或考虑调整EV阈值"
            ]
            return strategy

        # 串关处理
        if user_params.allow_parlay and len(filtered_bets) >= 2:
            # 选择EV最高的2-3场进行串关
            top_bets = sorted(filtered_bets, key=lambda x: x['expected_value'], reverse=True)[:user_params.max_parlay_leg]

            # 计算串关赔率和EV (简化计算)
            parlay_odds = 1.0
            parlay_ev = 1.0
            for bet in top_bets:
                parlay_odds *= bet['odds']
                parlay_ev *= (1 + bet['expected_value'])

            parlay_stake = min(
                user_params.bankroll * (user_params.max_bet_percentage / 100) * 0.5,  # 串关只投一半
                sum(bet['stake'] for bet in top_bets) * 0.3  # 不超过单场总和的30%
            )

            strategy.recommended_bets.append({
                'type': 'parlay',
                'bets': [b['bet_type'] for b in top_bets],
                'odds': parlay_odds,
                'stake': parlay_stake,
                'expected_value': parlay_ev - 1,
                'reason': f"串关 {len(top_bets)} 场高EV选项",
                'expected_return': parlay_stake * (parlay_odds - 1) * (parlay_ev - 1)
            })

            # 也保留单场选项
            strategy.recommended_bets.extend([{
                'type': 'single',
                'bet_type': bet['bet_type'],
                'odds': bet['odds'],
                'stake': bet['stake'] * 0.5,  # 串关时单场只投一半
                'expected_value': bet['expected_value'],
                'reason': bet['reason'],
                'expected_return': bet['expected_return'] * 0.5
            } for bet in filtered_bets])

        else:
            # 只投注单场
            strategy.recommended_bets = [{
                'type': 'single',
                **bet
            } for bet in filtered_bets]

        # 计算汇总数据
        strategy.total_stake = sum(bet.get('stake', 0) for bet in strategy.recommended_bets)
        strategy.expected_return = sum(bet.get('expected_return', 0) for bet in strategy.recommended_bets)

        if strategy.total_stake > 0:
            strategy.expected_roi = strategy.expected_return / strategy.total_stake

        # 风险评估
        if strategy.expected_roi >= 0.05:
            strategy.risk_level = 'Medium'
        elif strategy.expected_roi >= 0.02:
            strategy.risk_level = 'Low-Medium'
        else:
            strategy.risk_level = 'Low'

        strategy.risk_warnings = [
            f"本次投注涉及 {len(strategy.recommended_bets)} 个选项",
            f"预期收益率 {strategy.expected_roi:+.1%}",
            f"数据完整度 {data_quality_score:.0f}%",
            "请确保投注金额在可承受范围内"
        ]

        # 策略摘要
        strategy.strategy_summary = f"""
基于 {user_params.kelly_fraction:.0%} 凯利分数的资金管理策略，
从 {len(filtered_bets)} 个正EV选项中选择了 {len(strategy.recommended_bets)} 个进行投注。
总投注金额: {strategy.total_stake:.0f} 单位 ({strategy.total_stake/user_params.bankroll:.1%} 的资金池)
预期收益率: {strategy.expected_roi:+.1%}
建议关注临场赔率变化，必要时调整策略。
        """.strip()

        return strategy


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'UserRiskParameters',
    'KellyFractionOption',
    'BettingStrategy',
    'RiskManager',
]
