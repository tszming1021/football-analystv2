#!/usr/bin/env python3
"""
工作流程协调器 - Workflow Coordinator
负责协调数据收集、数学建模、大模型分析、风险管理各层的工作流程
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_new import ParsedMatch, InputParser
from core.data_collector import (
    DataCollector, CompleteDataReport, TeamData, MatchData, OddsData
)
from core.math_models import (
    PoissonModel, KellyCriterion, PoissonProbabilities, KellyResult, MatchAnalysis
)
from core.llm_analyzer import LLMAnalyzer, ComprehensiveAnalysisReport, LLMDeepAnalysis
from core.risk_manager import RiskManager, UserRiskParameters, BettingStrategy
from core.qimen_assistant import QimenAssistant
from core.report_renderer import StandardReportRenderer
from core.market_signal_model import MarketSignalModel
from core.context_models import MatchContextModel, HandicapCoverModel, GoalsModel, ScorelineModel
from core.decision_engine import EnsembleDecisionEngine
from core.odds_movement_analyzer import OddsMovementAnalyzer
from core.post_match_review import PredictionReviewRecord, PostMatchReviewStore
from core.probability_fusion import ProbabilityFusionCalibrator
from core.leg_model import LEGModel
from core.calibration_rules import MatchCalibrationFeatures, ProjectCalibrationRuleBook
from core.model_consistency import ModelConsistencyChecker


@dataclass
class FinalOutput:
    """最终输出报告"""
    # 比赛信息
    match_info: Dict[str, str]
    analysis_timestamp: str
    data_quality_summary: Dict[str, Any]

    # 数据获取层报告
    data_collection_report: Optional[Dict] = None

    # 数学建模层报告
    math_modeling_report: Optional[Dict] = None

    # 大模型分析层报告
    llm_analysis_report: Optional[Dict] = None

    # 风险管理层报告
    risk_management_report: Optional[Dict] = None

    # 最终风险分层策略
    final_betting_strategy: Optional[Dict] = None

    # 完整报告文本
    full_report_text: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class WorkflowCoordinator:
    """工作流程协调器"""

    def __init__(
        self,
        api_football_key: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None
    ):
        self.api_key = api_football_key or os.getenv('API_FOOTBALL_KEY')
        self.llm_api_key = llm_api_key or os.getenv('ANTHROPIC_API_KEY')
        self.llm_model = llm_model

        # 初始化各层组件
        self.data_collector = DataCollector(self.api_key)
        self.llm_analyzer = LLMAnalyzer(self.llm_api_key, self.llm_model)
        self.risk_manager = RiskManager()
        self.qimen_assistant = QimenAssistant()
        self.calibration_rules = ProjectCalibrationRuleBook()

    def execute_workflow(
        self,
        parsed_match: ParsedMatch,
        user_params: Optional[UserRiskParameters] = None,
        interactive: bool = True
    ) -> FinalOutput:
        """
        执行完整的工作流程

        Args:
            parsed_match: 解析后的比赛信息
            user_params: 用户风险参数（可选，默认交互式获取）
            interactive: 是否交互式获取用户输入

        Returns:
            FinalOutput: 完整的工作流程输出
        """

        print("\n" + "=" * 80)
        print("⚽️ 足球大数据精算分析智能体 v5.0")
        print("=" * 80)
        print(f"\n📋 分析比赛: {parsed_match.home_team_raw} vs {parsed_match.away_team_raw}")
        print(f"   英文名称: {parsed_match.home_team_en} vs {parsed_match.away_team_en}")

        # ============================================================
        # 步骤1: 数据获取层 (Data Collection Layer)
        # ============================================================
        print("\n" + "-" * 80)
        print("🔍 步骤 1/4: 数据获取层")
        print("-" * 80)

        try:
            data_report = self.data_collector.collect_data(parsed_match)
            print(f"\n✅ 数据收集完成")
            sources_str = ", ".join(data_report.data_sources_used) if data_report.data_sources_used else "无"
            print(f"   数据来源: {sources_str}")
            print(f"   数据完整度: {data_report.data_completeness_score:.0f}%")
        except Exception as e:
            print(f"\n❌ 数据收集失败: {e}")
            raise

        # ============================================================
        # 步骤2: 数学建模层 (Math Modeling Layer)
        # ============================================================
        print("\n" + "-" * 80)
        print("🧮 步骤 2/4: 数学建模层 (赔率主导 + Elo/泊松 + EV/凯利 + LEG)")
        print("-" * 80)

        math_modeling_results = {}
        final_kelly_results = []
        betting_strategy = None
        qimen_result = None
        market_signal = None
        match_context = None
        handicap_signal = None
        goals_signal = None
        scoreline_signal = None
        leg_signal = None
        decision_result = None
        odds_movement = None
        llm_report = None
        fusion_report = None

        try:
            if not data_report.home_stats or not data_report.away_stats:
                raise ValueError("缺少球队统计数据，无法运行泊松模型")

            home_model_stats = data_report.home_home_stats or data_report.home_stats
            away_model_stats = data_report.away_away_stats or data_report.away_stats
            split_model_used = bool(data_report.home_home_stats and data_report.away_away_stats)

            market_signal = MarketSignalModel.analyze(data_report)
            match_context = MatchContextModel.analyze(data_report)
            lambda_input = self._build_elo_poisson_lambdas(
                data_report=data_report,
                home_stats=home_model_stats,
                away_stats=away_model_stats,
                market_signal=market_signal,
            )
            home_lambda = lambda_input["home_lambda"]
            away_lambda = lambda_input["away_lambda"]
            if match_context.competition_type == "international_friendly":
                home_lambda, away_lambda = PoissonModel.friendly_lambda_adjustment(home_lambda, away_lambda)

            # 泊松低比分修正 + 国际赛零进球膨胀。
            base_poisson_probs = PoissonModel.calculate_match_probabilities(
                home_lambda=home_lambda,
                away_lambda=away_lambda,
                max_goals=10,
                low_score_rho=-0.08,
                zero_inflation=0.08 if match_context.competition_type == "international_friendly" else 0.02,
            )
            poisson_probs, fusion_report = ProbabilityFusionCalibrator().fuse(
                base_poisson=base_poisson_probs,
                data_report=data_report,
                market_signal=market_signal,
                context=match_context,
            )

            print(f"\n📊 泊松分布模型结果:")
            if split_model_used:
                print("   使用主队主场/客队客场拆分数据")
            print(f"   主队预期进球: {poisson_probs.expected_home_goals:.2f}")
            print(f"   客队预期进球: {poisson_probs.expected_away_goals:.2f}")
            print(f"   λ来源: {lambda_input['source']}")
            print(f"   主胜概率: {poisson_probs.home_win_prob:.1%}")
            print(f"   平局概率: {poisson_probs.draw_prob:.1%}")
            print(f"   客胜概率: {poisson_probs.away_win_prob:.1%}")
            print(f"   最可能比分: {poisson_probs.most_likely_score[0]}-{poisson_probs.most_likely_score[1]}")

            odds = {}
            if data_report.odds_data:
                pinnacle = next(
                    (o for o in data_report.odds_data if 'pinnacle' in o.bookmaker.lower()),
                    data_report.odds_data[0] if data_report.odds_data else None
                )
                if pinnacle:
                    odds['home'] = pinnacle.home_win
                    odds['draw'] = pinnacle.draw
                    odds['away'] = pinnacle.away_win
                    if pinnacle.over_25:
                        odds['over_25'] = pinnacle.over_25
                    if pinnacle.under_25:
                        odds['under_25'] = pinnacle.under_25

            kelly_results = []
            if odds:
                print(f"\n📌 参考市场数字:")
                print(f"   主胜: {odds['home']:.2f}")
                print(f"   平局: {odds['draw']:.2f}")
                print(f"   客胜: {odds['away']:.2f}")

                temp_bankroll = 10000
                kelly_results = KellyCriterion.calculate_all(
                    poisson_probs=poisson_probs,
                    odds=odds,
                    bankroll=temp_bankroll,
                    kelly_fraction=0.25
                )
                self._apply_market_deviation_guard(kelly_results, poisson_probs, market_signal)

                print(f"\n📈 风险系数分析 (临时基准 {temp_bankroll:.0f}):")
                for i, kr in enumerate(kelly_results[:5], 1):
                    status = "✅" if kr.recommended else "❌"
                    print(f"   {status} {kr.bet_type}: 风险系数 {kr.kelly_fraction:.2%}, EV {kr.expected_value:+.1%}, {kr.reason}")
            else:
                print("\n⚠️ 未获取到真实市场数字，跳过 EV/风险系数/风险分层计算")

            math_modeling_results = {
                'poisson': poisson_probs,
                'kelly': kelly_results,
                'odds': odds,
                'model_input': {
                    'home_attack_avg': lambda_input["home_attack_avg"],
                    'home_defense_avg': lambda_input["home_defense_avg"],
                    'away_attack_avg': lambda_input["away_attack_avg"],
                    'away_defense_avg': lambda_input["away_defense_avg"],
                    'lambda_input': lambda_input,
                    'season_used': data_report.season_used,
                    'home_away_split_used': split_model_used,
                    'competition_type': match_context.competition_type,
                    'market_calibrated': market_signal.implied_home is not None,
                    'probability_fusion': fusion_report.to_dict() if fusion_report else None,
                }
            }

            if data_report.match_data:
                qimen_result = self.qimen_assistant.analyze(
                    match_datetime=data_report.match_data.match_date,
                    home_team=data_report.match_data.home_team.name_zh or parsed_match.home_team_raw,
                    away_team=data_report.match_data.away_team.name_zh or parsed_match.away_team_raw,
                    poisson=poisson_probs,
                    odds=odds,
                )
                math_modeling_results['qimen'] = qimen_result
                data_report.qimen_analysis = qimen_result.to_dict()

            odds_movement = OddsMovementAnalyzer.analyze(data_report.odds_history)
            handicap_signal = HandicapCoverModel.analyze(poisson_probs, data_report, market_signal, match_context)
            goals_signal = GoalsModel.analyze(poisson_probs, data_report, match_context, market_signal)
            scoreline_signal = ScorelineModel.analyze(
                poisson=poisson_probs,
                data_report=data_report,
                goals_signal=goals_signal,
                handicap_signal=handicap_signal,
                market_signal=market_signal,
                context=match_context,
            )
            leg_signal = LEGModel.analyze(
                market_signal=market_signal,
                handicap_signal=handicap_signal,
                goals_signal=goals_signal,
                scoreline_signal=scoreline_signal,
                context=match_context,
            )
            decision_result = EnsembleDecisionEngine.decide(
                data_report=data_report,
                poisson=poisson_probs,
                market_signal=market_signal,
                context=match_context,
                handicap_signal=handicap_signal,
                goals_signal=goals_signal,
                fusion_report=fusion_report.to_dict() if fusion_report else None,
                qimen=qimen_result.to_dict() if qimen_result else None,
            )
            calibration_report = self.calibration_rules.as_report(
                self._calibration_features(data_report, market_signal, match_context, handicap_signal, scoreline_signal)
            )
            consistency_report = ModelConsistencyChecker.check(
                poisson=poisson_probs,
                handicap_signal=handicap_signal,
                goals_signal=goals_signal,
                scoreline_signal=scoreline_signal,
                leg_signal=leg_signal,
                decision=decision_result,
            )
            math_modeling_results.update({
                'market_signal': market_signal,
                'match_context': match_context,
                'handicap_signal': handicap_signal,
                'goals_signal': goals_signal,
                'scoreline_signal': scoreline_signal,
                'leg_signal': leg_signal,
                'calibration_report': calibration_report,
                'consistency_report': consistency_report,
                'decision': decision_result,
                'odds_movement': odds_movement,
                'probability_fusion': fusion_report,
            })

            print("\n" + "-" * 80)
            print("🤖 步骤 2.5/4: 大模型复核层")
            print("-" * 80)
            llm_report = self.llm_analyzer.analyze(
                data_report=data_report,
                poisson_result=poisson_probs,
                kelly_results=kelly_results,
                historical_data={
                    "market_signal": market_signal.to_dict() if market_signal else None,
                    "match_context": match_context.to_dict() if match_context else None,
                    "handicap_signal": handicap_signal.to_dict() if handicap_signal else None,
                    "goals_signal": goals_signal.to_dict() if goals_signal else None,
                    "scoreline_signal": scoreline_signal.to_dict() if scoreline_signal else None,
                    "leg_signal": leg_signal.to_dict() if leg_signal else None,
                    "calibration_report": calibration_report,
                    "consistency_report": consistency_report.to_dict() if consistency_report else None,
                    "decision": decision_result.to_dict() if decision_result else None,
                    "odds_movement": odds_movement.to_dict() if odds_movement else None,
                    "probability_fusion": fusion_report.to_dict() if fusion_report else None,
                },
            )
            math_modeling_results["llm_analysis"] = (
                llm_report.llm_deep_analysis.to_dict()
                if hasattr(llm_report.llm_deep_analysis, "to_dict")
                else asdict(llm_report.llm_deep_analysis)
                if llm_report and llm_report.llm_deep_analysis
                else None
            )
            if llm_report and llm_report.llm_deep_analysis:
                print(
                    f"   LLM状态: {llm_report.llm_deep_analysis.status}, "
                    f"复核意见: {llm_report.llm_deep_analysis.model_agreement}, "
                    f"信心调整: {llm_report.llm_deep_analysis.confidence_adjustment}"
                )
                before_score = data_report.data_completeness_score
                self.data_collector.apply_llm_verified_intelligence(
                    data_report,
                    llm_report.llm_deep_analysis.to_dict(),
                )
                verified_payload = llm_report.llm_deep_analysis.verified_intelligence or {}
                if data_report.data_completeness_score != before_score:
                    print(
                        f"   GPT核验情报已回写: 数据完整度 "
                        f"{before_score:.0f}% -> {data_report.data_completeness_score:.0f}%"
                    )
                if data_report.data_completeness_score != before_score or verified_payload:
                    match_context = MatchContextModel.analyze(data_report)
                    lambda_input = self._build_elo_poisson_lambdas(
                        data_report=data_report,
                        home_stats=home_model_stats,
                        away_stats=away_model_stats,
                        market_signal=market_signal,
                    )
                    updated_home_lambda = lambda_input["home_lambda"]
                    updated_away_lambda = lambda_input["away_lambda"]
                    if match_context.competition_type == "international_friendly":
                        updated_home_lambda, updated_away_lambda = PoissonModel.friendly_lambda_adjustment(
                            updated_home_lambda,
                            updated_away_lambda,
                        )
                    base_poisson_probs = PoissonModel.calculate_match_probabilities(
                        home_lambda=updated_home_lambda,
                        away_lambda=updated_away_lambda,
                        max_goals=10,
                        low_score_rho=-0.08,
                        zero_inflation=0.08 if match_context.competition_type == "international_friendly" else 0.02,
                    )
                    poisson_probs, fusion_report = ProbabilityFusionCalibrator().fuse(
                        base_poisson=base_poisson_probs,
                        data_report=data_report,
                        market_signal=market_signal,
                        context=match_context,
                    )
                    handicap_signal = HandicapCoverModel.analyze(poisson_probs, data_report, market_signal, match_context)
                    goals_signal = GoalsModel.analyze(poisson_probs, data_report, match_context, market_signal)
                    scoreline_signal = ScorelineModel.analyze(
                        poisson=poisson_probs,
                        data_report=data_report,
                        goals_signal=goals_signal,
                        handicap_signal=handicap_signal,
                        market_signal=market_signal,
                        context=match_context,
                    )
                    leg_signal = LEGModel.analyze(
                        market_signal=market_signal,
                        handicap_signal=handicap_signal,
                        goals_signal=goals_signal,
                        scoreline_signal=scoreline_signal,
                        context=match_context,
                    )
                    decision_result = EnsembleDecisionEngine.decide(
                        data_report=data_report,
                        poisson=poisson_probs,
                        market_signal=market_signal,
                        context=match_context,
                        handicap_signal=handicap_signal,
                        goals_signal=goals_signal,
                        fusion_report=fusion_report.to_dict() if fusion_report else None,
                        qimen=qimen_result.to_dict() if qimen_result else None,
                    )
                    calibration_report = self.calibration_rules.as_report(
                        self._calibration_features(data_report, market_signal, match_context, handicap_signal, scoreline_signal)
                    )
                    consistency_report = ModelConsistencyChecker.check(
                        poisson=poisson_probs,
                        handicap_signal=handicap_signal,
                        goals_signal=goals_signal,
                        scoreline_signal=scoreline_signal,
                        leg_signal=leg_signal,
                        decision=decision_result,
                    )
                    math_modeling_results["match_context"] = match_context
                    math_modeling_results["poisson"] = poisson_probs
                    math_modeling_results["model_input"]["probability_fusion"] = fusion_report.to_dict() if fusion_report else None
                    math_modeling_results["model_input"]["lambda_input"] = lambda_input
                    math_modeling_results["handicap_signal"] = handicap_signal
                    math_modeling_results["goals_signal"] = goals_signal
                    math_modeling_results["scoreline_signal"] = scoreline_signal
                    math_modeling_results["leg_signal"] = leg_signal
                    math_modeling_results["calibration_report"] = calibration_report
                    math_modeling_results["consistency_report"] = consistency_report
                    math_modeling_results["probability_fusion"] = fusion_report
                    math_modeling_results["decision"] = decision_result

        except Exception as e:
            print(f"\n❌ 数学建模失败: {e}")
            import traceback
            traceback.print_exc()
            raise

        # ============================================================
        # 步骤3: 风险管理层 (Risk Management Layer)
        # ============================================================
        print("\n" + "-" * 80)
        print("🛡️ 步骤 3/4: 风险管理层")
        print("-" * 80)

        final_kelly_results = []
        try:
            # 获取用户风险参数
            if user_params:
                params = user_params
                print(f"\n✅ 使用预设风险参数")
            elif interactive:
                print(f"\n📝 请设置风险参数:")
                params = RiskManager.get_user_parameters_interactive()
            else:
                # 使用默认参数
                params = UserRiskParameters()
                print(f"\n⚠️ 使用默认风险参数")

            print(f"\n📋 风险参数确认:")
            print(f"   风险基准: {params.bankroll:.0f}")
            print(f"   单项最大占比: {params.max_bet_percentage:.0f}%")
            print(f"   市场数字范围: {params.min_odds:.2f} - {params.max_odds:.2f}")
            print(f"   风险系数折扣: {params.kelly_fraction:.0%}")
            print(f"   组合思路: {'允许' if params.allow_parlay else '不允许'}")
            print(f"   权重倍率: {params.bet_multiplier}倍")

            if math_modeling_results.get('odds'):
                final_kelly_results = KellyCriterion.calculate_all(
                    poisson_probs=math_modeling_results['poisson'],
                    odds=math_modeling_results['odds'],
                    bankroll=params.bankroll,
                    kelly_fraction=params.kelly_fraction
                )
                self._apply_market_deviation_guard(final_kelly_results, math_modeling_results["poisson"], market_signal)

                betting_strategy = RiskManager.generate_betting_strategy(
                    user_params=params,
                    kelly_results=final_kelly_results,
                    llm_analysis=llm_report.llm_deep_analysis if llm_report else None,
                    data_quality_score=data_report.data_completeness_score
                )
            else:
                betting_strategy = BettingStrategy(
                    recommended_bets=[],
                    total_stake=0.0,
                    stake_breakdown={},
                    expected_return=0.0,
                    expected_roi=0.0,
                    risk_level='No Bet',
                    risk_warnings=[
                        "未获取到真实市场数字，系统不会基于默认数字生成核心方向",
                        "请接入可用市场数字源或手动提供后再计算 EV"
                    ],
                    strategy_summary="数据层未返回真实市场数字，因此本次只输出概率模型，不生成风险分层策略。"
                )

            print(f"\n📊 风险分层策略生成完成:")
            print(f"   推荐方向数: {len(betting_strategy.recommended_bets)}")
            print(f"   总风险权重: {betting_strategy.total_stake:.0f}")
            print(f"   预期回报指标: {betting_strategy.expected_return:.0f}")
            print(f"   预期ROI: {betting_strategy.expected_roi:+.1%}")
            print(f"   风险等级: {betting_strategy.risk_level}")

        except Exception as e:
            print(f"\n❌ 风险管理层失败: {e}")
            import traceback
            traceback.print_exc()
            raise

        # ============================================================
        # 步骤4: 输出层 (Output Layer)
        # ============================================================
        print("\n" + "-" * 80)
        print("📤 步骤 4/4: 输出层 - 生成最终报告")
        print("-" * 80)

        final_output = FinalOutput(
            match_info={
                'home_team': data_report.parsed_match.home_team_en,
                'away_team': data_report.parsed_match.away_team_en,
                'home_team_zh': data_report.parsed_match.home_team_raw,
                'away_team_zh': data_report.parsed_match.away_team_raw,
            },
            analysis_timestamp=datetime.now().isoformat(),
            data_quality_summary={
                'score': data_report.data_completeness_score,
                'sources': data_report.data_sources_used,
                'api_available': data_report.api_available,
                'web_search_available': data_report.web_search_available,
                'warnings': data_report.data_warnings,
                'season_used': data_report.season_used,
                'match_intelligence': data_report.match_intelligence,
                'weather_context': data_report.weather_context,
                'odds_history': data_report.odds_history,
                'qimen': qimen_result.to_dict() if qimen_result else None,
                'market_signal': market_signal.to_dict() if market_signal else None,
                'match_context': match_context.to_dict() if match_context else None,
                'handicap_signal': handicap_signal.to_dict() if handicap_signal else None,
                'goals_signal': goals_signal.to_dict() if goals_signal else None,
                'scoreline_signal': scoreline_signal.to_dict() if scoreline_signal else None,
                'leg_signal': leg_signal.to_dict() if leg_signal else None,
                'calibration_report': calibration_report if 'calibration_report' in locals() else None,
                'consistency_report': consistency_report.to_dict() if 'consistency_report' in locals() and consistency_report else None,
                'decision': decision_result.to_dict() if decision_result else None,
                'odds_movement': odds_movement.to_dict() if odds_movement else None,
                'probability_fusion': fusion_report.to_dict() if fusion_report else None,
                'llm_analysis': llm_report.to_dict() if llm_report else None,
            }
        )

        # 构建完整报告文本。以后单场报告统一使用 report_template_jingcai_qimen.md 对应结构。
        try:
            final_output.full_report_text = StandardReportRenderer.render_single_match(
                data_report=data_report,
            math_results=math_modeling_results,
            kelly_results=final_kelly_results,
            betting_strategy=betting_strategy,
            )
        except Exception as render_error:
            data_report.data_warnings.append(f"标准报告模板渲染失败: {render_error}")
            final_output.data_quality_summary['warnings'] = data_report.data_warnings
            final_output.full_report_text = "\n".join([
                f"# {final_output.match_info['home_team_zh']} vs {final_output.match_info['away_team_zh']} 赛事分析报告",
                "",
                f"数据完整度: {data_report.data_completeness_score:.0f}%",
                f"数据来源: {', '.join(data_report.data_sources_used)}",
                "",
                "标准报告模板渲染失败，已输出兜底摘要。",
                f"错误: {render_error}",
            ])

        # 保存各层报告
        final_output.data_collection_report = data_report.to_dict() if data_report else None
        final_output.math_modeling_report = {
            'poisson': {
                'home_win_prob': poisson_probs.home_win_prob if 'poisson_probs' in locals() else 0,
                'draw_prob': poisson_probs.draw_prob if 'poisson_probs' in locals() else 0,
                'away_win_prob': poisson_probs.away_win_prob if 'poisson_probs' in locals() else 0,
                'expected_home_goals': poisson_probs.expected_home_goals if 'poisson_probs' in locals() else 0,
                'expected_away_goals': poisson_probs.expected_away_goals if 'poisson_probs' in locals() else 0,
                'over_25_prob': poisson_probs.over_25_prob if 'poisson_probs' in locals() else 0,
                'under_25_prob': poisson_probs.under_25_prob if 'poisson_probs' in locals() else 0,
                'btts_yes_prob': poisson_probs.btts_yes_prob if 'poisson_probs' in locals() else 0,
                'most_likely_score': poisson_probs.most_likely_score if 'poisson_probs' in locals() else None,
            },
            'kelly_count': len(final_kelly_results) if 'final_kelly_results' in locals() else 0,
            'qimen': qimen_result.to_dict() if qimen_result else None,
            'market_signal': market_signal.to_dict() if market_signal else None,
            'match_context': match_context.to_dict() if match_context else None,
            'handicap_signal': handicap_signal.to_dict() if handicap_signal else None,
            'goals_signal': goals_signal.to_dict() if goals_signal else None,
            'scoreline_signal': scoreline_signal.to_dict() if scoreline_signal else None,
            'leg_signal': leg_signal.to_dict() if leg_signal else None,
            'calibration_report': calibration_report if 'calibration_report' in locals() else None,
            'consistency_report': consistency_report.to_dict() if 'consistency_report' in locals() and consistency_report else None,
            'decision': decision_result.to_dict() if decision_result else None,
            'odds_movement': odds_movement.to_dict() if odds_movement else None,
            'probability_fusion': fusion_report.to_dict() if fusion_report else None,
            'llm_analysis': (
                asdict(llm_report.llm_deep_analysis)
                if llm_report and llm_report.llm_deep_analysis else None
            ),
        }
        final_output.llm_analysis_report = llm_report.to_dict() if llm_report else None
        final_output.risk_management_report = {
            'total_stake': betting_strategy.total_stake if 'betting_strategy' in locals() else 0,
            'expected_roi': betting_strategy.expected_roi if 'betting_strategy' in locals() else 0,
            'risk_level': betting_strategy.risk_level if 'betting_strategy' in locals() else 'Unknown'
        }
        final_output.final_betting_strategy = betting_strategy.__dict__ if betting_strategy else None

        try:
            review_id = self._save_prediction_review(data_report, decision_result, final_kelly_results, math_modeling_results)
            final_output.data_quality_summary['review_record_id'] = review_id
            print(f"\n🧾 已保存赛前预测到复盘库: id={review_id}")
        except Exception as review_error:
            final_output.data_quality_summary.setdefault('warnings', []).append(f"复盘库保存失败: {review_error}")
            print(f"\n⚠️ 复盘库保存失败: {review_error}")

        # 打印最终报告
        print(final_output.full_report_text)

        return final_output

    def _build_elo_poisson_lambdas(
        self,
        data_report: CompleteDataReport,
        home_stats: Any,
        away_stats: Any,
        market_signal: Any,
    ) -> Dict[str, Any]:
        home_attack = self._per_match(getattr(home_stats, "goals_for", None), getattr(home_stats, "matches_played", None), 1.25)
        home_defense = self._per_match(getattr(home_stats, "goals_against", None), getattr(home_stats, "matches_played", None), 1.25)
        away_attack = self._per_match(getattr(away_stats, "goals_for", None), getattr(away_stats, "matches_played", None), 1.15)
        away_defense = self._per_match(getattr(away_stats, "goals_against", None), getattr(away_stats, "matches_played", None), 1.25)

        home_lambda = max(0.20, (0.62 * home_attack + 0.38 * away_defense) * 1.08)
        away_lambda = max(0.20, (0.62 * away_attack + 0.38 * home_defense) * 0.94)

        home_elo, away_elo = self._clubelo_pair(data_report)
        elo_adjustment = 1.0
        if home_elo is not None and away_elo is not None:
            elo_adjustment = self._clamp_range(math.exp((home_elo - away_elo) / 1100.0), 0.84, 1.18)
            home_lambda *= elo_adjustment
            away_lambda /= elo_adjustment

        raw_total = max(0.40, home_lambda + away_lambda)
        market_total = self._market_total_goal_mean(data_report)
        total_after_market = raw_total
        if market_total is not None:
            total_after_market = 0.55 * raw_total + 0.45 * market_total

        home_share = self._clamp_range(home_lambda / raw_total, 0.24, 0.76)
        implied_home = self._safe_float(getattr(market_signal, "implied_home", None)) if market_signal else None
        implied_away = self._safe_float(getattr(market_signal, "implied_away", None)) if market_signal else None
        if implied_home is not None and implied_away is not None:
            home_share = self._clamp_range(home_share + 0.18 * (implied_home - implied_away), 0.22, 0.78)

        home_lambda = max(0.20, total_after_market * home_share)
        away_lambda = max(0.20, total_after_market * (1.0 - home_share))
        source_parts = ["历史进失球"]
        if home_elo is not None and away_elo is not None:
            source_parts.append("ClubElo温和修正")
        if market_total is not None or (implied_home is not None and implied_away is not None):
            source_parts.append("赔率去水/总球盘校准")

        return {
            "home_lambda": round(home_lambda, 4),
            "away_lambda": round(away_lambda, 4),
            "home_attack_avg": round(home_attack, 4),
            "home_defense_avg": round(home_defense, 4),
            "away_attack_avg": round(away_attack, 4),
            "away_defense_avg": round(away_defense, 4),
            "home_clubelo": home_elo,
            "away_clubelo": away_elo,
            "elo_adjustment": round(elo_adjustment, 4),
            "raw_total_goals": round(raw_total, 4),
            "market_total_goals": round(market_total, 4) if market_total is not None else None,
            "source": " + ".join(source_parts),
        }

    @staticmethod
    def _per_match(total: Any, matches: Any, fallback: float) -> float:
        try:
            total_value = float(total)
            match_count = float(matches)
            if match_count > 0:
                return max(0.05, total_value / match_count)
        except (TypeError, ValueError):
            pass
        return fallback

    @staticmethod
    def _clubelo_pair(data_report: CompleteDataReport) -> Tuple[Optional[float], Optional[float]]:
        intelligence = data_report.match_intelligence or {}
        home = intelligence.get("home") or {}
        away = intelligence.get("away") or {}
        return (
            WorkflowCoordinator._safe_float(home.get("clubelo_rating")),
            WorkflowCoordinator._safe_float(away.get("clubelo_rating")),
        )

    @staticmethod
    def _market_total_goal_mean(data_report: CompleteDataReport) -> Optional[float]:
        jingcai = data_report.jingcai_match or {}
        mixed = jingcai.get("mixed_market") or {}
        candidates = [
            mixed.get("total_goals_odds"),
            jingcai.get("total_goals_odds"),
            (jingcai.get("goals_market") or {}).get("total_goals_odds"),
        ]
        odds = next((item for item in candidates if isinstance(item, dict) and item), None)
        if not odds:
            return None
        weighted = 0.0
        total_prob = 0.0
        for key, value in odds.items():
            decimal = WorkflowCoordinator._safe_float(value)
            goal_value = WorkflowCoordinator._goal_bucket_value(key)
            if decimal is None or decimal <= 1.0 or goal_value is None:
                continue
            implied = 1.0 / decimal
            weighted += goal_value * implied
            total_prob += implied
        if total_prob <= 0:
            return None
        return weighted / total_prob

    @staticmethod
    def _goal_bucket_value(key: Any) -> Optional[float]:
        text = str(key).strip().lower().replace("球", "")
        if text in {"7+", "7_plus", "7 plus", "7及以上"}:
            return 7.5
        digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if not digits:
            return None
        try:
            return float(digits)
        except ValueError:
            return None

    @staticmethod
    def _clamp_range(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _calibration_features(
        self,
        data_report: CompleteDataReport,
        market_signal: Any,
        match_context: Any,
        handicap_signal: Any,
        scoreline_signal: Any,
    ) -> MatchCalibrationFeatures:
        jingcai = data_report.jingcai_match or {}
        league = jingcai.get("league") or ""
        top_scores = [item.get("score") for item in (getattr(scoreline_signal, "top_scores", []) or []) if item.get("score")]
        top_total_goals = [str(item.get("total_goals")) for item in (getattr(scoreline_signal, "top_scores", []) or []) if item.get("total_goals") is not None]
        line = self._safe_float(getattr(handicap_signal, "line", None)) if handicap_signal else None
        push = self._safe_float(getattr(handicap_signal, "push_probability", None)) if handicap_signal else 0.0
        cover = self._safe_float(getattr(handicap_signal, "cover_probability", None)) if handicap_signal else 0.0
        fail = self._safe_float(getattr(handicap_signal, "fail_probability", None)) if handicap_signal else 0.0
        top2 = (getattr(scoreline_signal, "top_scores", []) or [])[:2] if scoreline_signal else []
        push_supported_by_scores = False
        if line is not None:
            for item in top2:
                home_goals = int(item.get("home_goals", 0) or 0)
                away_goals = int(item.get("away_goals", 0) or 0)
                if home_goals + line - away_goals == 0:
                    push_supported_by_scores = True
                    break
        four_goal_two_margin_btts = any(
            int(item.get("total_goals", 0) or 0) == 4
            and abs(int(item.get("margin", 0) or 0)) == 2
            and int(item.get("home_goals", 0) or 0) > 0
            and int(item.get("away_goals", 0) or 0) > 0
            for item in (getattr(scoreline_signal, "top_scores", []) or [])[:5]
        ) if scoreline_signal else False
        favorite = getattr(market_signal, "favorite", None) if market_signal else None
        no_handicap = jingcai.get("no_handicap_odds") or {}
        home_value = self._safe_float(no_handicap.get("home_win"))
        home_low_value = favorite == "home" and home_value is not None and home_value <= 1.65
        away_plus_one = favorite == "away" and line is not None and abs(line - 1.0) < 0.01

        return MatchCalibrationFeatures(
            league=league,
            competition_stage=str(jingcai.get("round") or jingcai.get("match_stage") or ""),
            is_second_leg="次回合" in str(jingcai),
            is_ranking_or_playoff=any(token in league for token in ["排名", "附加", "杯"]),
            home_favorite_low_value=home_low_value,
            handicap_protects_underdog=(fail or 0.0) >= max(cover or 0.0, push or 0.0),
            away_favorite_with_home_plus_one=away_plus_one,
            top_scores=top_scores,
            top_total_goals=top_total_goals,
            final_lineup_confirmed=bool((data_report.match_intelligence or {}).get("lineups_confirmed")),
            injury_notes_are_material=bool((data_report.match_intelligence or {}).get("injuries_material")),
            competition_type=getattr(match_context, "competition_type", ""),
            friendly_subtype=getattr(match_context, "friendly_subtype", ""),
            handicap_line=line,
            handicap_push_supported_by_scores=push_supported_by_scores,
            deep_favorite_context=bool(line is not None and abs(line) >= 1.75 and favorite in {"home", "away"}),
            four_goal_two_margin_btts_path=four_goal_two_margin_btts,
        )

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _save_prediction_review(
        self,
        data_report: CompleteDataReport,
        decision_result: Any,
        kelly_results: List[KellyResult],
        math_results: Dict[str, Any],
    ) -> int:
        if not decision_result:
            raise ValueError("缺少集成决策结果")

        parsed = data_report.parsed_match
        jingcai = data_report.jingcai_match or {}
        match_date = jingcai.get("match_date") or (
            data_report.match_data.match_date.strftime("%Y-%m-%d") if data_report.match_data else ""
        )
        match_key = "_".join([
            match_date or datetime.now().strftime("%Y-%m-%d"),
            jingcai.get("match_num") or "",
            parsed.home_team_raw,
            parsed.away_team_raw,
        ]).replace(" ", "")
        odds, probability = self._review_odds_probability(decision_result.primary_pick, data_report, math_results, kelly_results)
        score = ""
        scoreline_signal = math_results.get("scoreline_signal")
        if scoreline_signal and getattr(scoreline_signal, "top_scores", None):
            score = str(scoreline_signal.top_scores[0].get("score") or "")
        poisson = math_results.get("poisson")
        if not score and poisson:
            score = f"{poisson.most_likely_score[0]}-{poisson.most_likely_score[1]}"
        goals = (math_results.get("goals_signal").goals_direction if math_results.get("goals_signal") else "")
        record = PredictionReviewRecord(
            match_key=match_key,
            match_date=match_date,
            home_team=parsed.home_team_raw,
            away_team=parsed.away_team_raw,
            recommendation=decision_result.primary_pick,
            recommended_market=decision_result.primary_market,
            recommended_odds=odds,
            model_probability=probability,
            predicted_score=score,
            predicted_goals=goals,
            error_tags=[],
            notes=decision_result.summary,
        )
        return PostMatchReviewStore().save_prediction(record)

    @staticmethod
    def _review_odds_probability(
        recommendation: str,
        data_report: CompleteDataReport,
        math_results: Dict[str, Any],
        kelly_results: List[KellyResult],
    ) -> Tuple[Optional[float], Optional[float]]:
        if "让" in recommendation:
            handicap_odds = (data_report.jingcai_match or {}).get("handicap_odds") or {}
            handicap_signal = math_results.get("handicap_signal")
            if hasattr(handicap_signal, "to_dict"):
                handicap_signal = handicap_signal.to_dict()
            handicap_signal = handicap_signal or {}
            if "胜" in recommendation:
                return handicap_odds.get("home_win"), handicap_signal.get("cover_probability")
            if "平" in recommendation:
                return handicap_odds.get("draw"), handicap_signal.get("push_probability")
            if "负" in recommendation or "失败" in recommendation:
                return handicap_odds.get("away_win"), handicap_signal.get("fail_probability")

        for item in kelly_results:
            if item.bet_type and item.bet_type in recommendation:
                return item.odds, item.probability
        poisson = math_results.get("poisson")
        odds = data_report.odds_data[0] if data_report.odds_data else None
        if not poisson:
            return None, None
        if data_report.parsed_match.home_team_raw in recommendation:
            return (odds.home_win if odds else None), poisson.home_win_prob
        if data_report.parsed_match.away_team_raw in recommendation or "客胜" in recommendation:
            return (odds.away_win if odds else None), poisson.away_win_prob
        if "平" in recommendation:
            return (odds.draw if odds else None), poisson.draw_prob
        if "大" in recommendation:
            return None, poisson.over_25_prob
        if "小" in recommendation:
            return None, poisson.under_25_prob
        return None, None

    @staticmethod
    def _apply_market_deviation_guard(kelly_results: List[KellyResult], poisson: Any, market_signal: Any):
        implied = {
            "主胜": getattr(market_signal, "implied_home", None),
            "平局": getattr(market_signal, "implied_draw", None),
            "客胜": getattr(market_signal, "implied_away", None),
        }
        probs = {
            "主胜": poisson.home_win_prob,
            "平局": poisson.draw_prob,
            "客胜": poisson.away_win_prob,
        }
        for result in kelly_results:
            market_prob = implied.get(result.bet_type)
            model_prob = probs.get(result.bet_type)
            if market_prob is None or model_prob is None:
                continue
            deviation = abs(model_prob - market_prob)
            if deviation >= 0.15:
                result.recommended = False
                result.kelly_fraction = 0.0
                result.kelly_amount = 0.0
                result.reason += f"；模型与市场概率偏差 {deviation:.1%}，触发偏差保护"


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'FinalOutput',
    'WorkflowCoordinator',
]
