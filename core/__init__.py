#!/usr/bin/env python3
"""
足球大数据精算分析智能体 - 核心模块
Core Modules for Football Big Data Actuarial Analysis Agent
"""

from core.workflow_new import (
    ParsedMatch,
    TeamNameTranslator,
    InputParser,
)

from core.math_models import (
    PoissonProbabilities,
    KellyResult,
    MatchAnalysis,
    PoissonModel,
    KellyCriterion,
    BetType,
)

from core.data_collector import (
    TeamData,
    MatchData,
    OddsData,
    StatisticsData,
    WebSearchResult,
    CompleteDataReport,
    DataCollector,
)

from core.match_intelligence import (
    MatchIntelligenceCollector,
    MatchIntelligenceReport,
    TeamIntelligence,
)

from core.odds_history import (
    OddsHistoryStore,
    OddsSnapshot,
)

from core.odds_movement_analyzer import (
    OddsMovementSignal,
    OddsMovementAnalyzer,
)

from core.weather_context import (
    WeatherContextCollector,
    WeatherContext,
)

from core.source_registry import (
    DataSourceRegistry,
    DataSourceProfile,
)

from core.supplemental_data import (
    SupplementalDataCollector,
    TeamSupplementalData,
    HistoricalLeagueData,
    MatchSupplementalData,
)

from core.qimen_assistant import (
    QimenAssistant,
    QimenAssistantResult,
)

from core.report_renderer import (
    StandardReportRenderer,
)

from core.market_signal_model import (
    MarketSignal,
    MarketSignalModel,
)

from core.market_dewater import (
    DewateredMarket,
    MarketDewater,
)

from core.bayesian_fusion import (
    BayesianFusionReport,
    BayesianProbabilityFusion,
)

from core.context_models import (
    MatchContext,
    HandicapCoverSignal,
    GoalsSignal,
    MatchContextModel,
    HandicapCoverModel,
    GoalsModel,
)

from core.decision_engine import (
    EvidenceItem,
    DecisionResult,
    EnsembleDecisionEngine,
)

from core.probability_fusion import (
    ProbabilityFusionReport,
    ProbabilityFusionCalibrator,
)

from core.calibration_rules import (
    CalibrationAdjustment,
    CalibrationRuleBook,
    MatchCalibrationFeatures,
    ProjectCalibrationRuleBook,
)

from core.model_consistency import (
    ConsistencyCheckReport,
    ModelConsistencyChecker,
)

from core.decision_iteration import (
    DecisionIterationAdjustment,
    DecisionIterationEngine,
    DecisionIterationFeatures,
    DecisionIterationReport,
)

from core.post_match_review import (
    PredictionReviewRecord,
    PostMatchReviewStore,
    ReviewEvaluator,
)

from core.parlay_risk import (
    ParlayRiskReport,
    ParlayRiskController,
)

from core.worldcup_trained_model import (
    NationalTeamProfile,
    WorldCupModelArtifact,
    WorldCupOfflineTrainer,
    WorldCupTrainedModel,
)

from core.xg_proxy_model import (
    PreMatchXGProxyModel,
    XGSignal,
)

__version__ = '5.1.0'
__author__ = 'AI Assistant'

__all__ = [
    # 输入/实体识别
    'ParsedMatch',
    'TeamNameTranslator',
    'InputParser',

    # 数据收集
    'TeamData',
    'MatchData',
    'OddsData',
    'StatisticsData',
    'WebSearchResult',
    'CompleteDataReport',
    'DataCollector',
    'MatchIntelligenceCollector',
    'MatchIntelligenceReport',
    'TeamIntelligence',
    'OddsHistoryStore',
    'OddsSnapshot',
    'OddsMovementSignal',
    'OddsMovementAnalyzer',
    'WeatherContextCollector',
    'WeatherContext',
    'DataSourceRegistry',
    'DataSourceProfile',
    'SupplementalDataCollector',
    'TeamSupplementalData',
    'HistoricalLeagueData',
    'MatchSupplementalData',
    'QimenAssistant',
    'QimenAssistantResult',
    'StandardReportRenderer',
    'MarketSignal',
    'MarketSignalModel',
    'DewateredMarket',
    'MarketDewater',
    'BayesianFusionReport',
    'BayesianProbabilityFusion',
    'MatchContext',
    'HandicapCoverSignal',
    'GoalsSignal',
    'MatchContextModel',
    'HandicapCoverModel',
    'GoalsModel',
    'EvidenceItem',
    'DecisionResult',
    'EnsembleDecisionEngine',
    'ProbabilityFusionReport',
    'ProbabilityFusionCalibrator',
    'CalibrationAdjustment',
    'CalibrationRuleBook',
    'MatchCalibrationFeatures',
    'ProjectCalibrationRuleBook',
    'ConsistencyCheckReport',
    'ModelConsistencyChecker',
    'DecisionIterationAdjustment',
    'DecisionIterationEngine',
    'DecisionIterationFeatures',
    'DecisionIterationReport',
    'PredictionReviewRecord',
    'PostMatchReviewStore',
    'ReviewEvaluator',
    'ParlayRiskReport',
    'ParlayRiskController',
    'NationalTeamProfile',
    'WorldCupModelArtifact',
    'WorldCupOfflineTrainer',
    'WorldCupTrainedModel',
    'PreMatchXGProxyModel',
    'XGSignal',

    # 数学模型
    'PoissonProbabilities',
    'KellyResult',
    'MatchAnalysis',
    'PoissonModel',
    'KellyCriterion',
    'BetType',

    # 版本信息
    '__version__',
    '__author__',
]
