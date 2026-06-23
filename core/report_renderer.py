#!/usr/bin/env python3
"""标准报告渲染器。

按 report_template_jingcai_qimen.md 的章节顺序生成单场报告。
多场汇总可使用 render_multi_match_summary 追加在多个单场报告之后。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class StandardReportRenderer:
    """Render standard Jingcai + Qimen reports."""

    @staticmethod
    def _as_dict(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return {}

    @staticmethod
    def render_single_match(
        data_report: Any,
        math_results: Dict[str, Any],
        kelly_results: List[Any],
        betting_strategy: Optional[Any],
    ) -> str:
        parsed = data_report.parsed_match
        match = data_report.match_data
        jingcai = data_report.jingcai_match or {}
        intelligence = data_report.match_intelligence or {}
        supplemental = data_report.supplemental_data or intelligence.get("supplemental_data") or {}
        weather = data_report.weather_context or {}
        odds_history = data_report.odds_history or {}
        qimen = data_report.qimen_analysis or {}
        poisson = math_results.get("poisson")
        odds = math_results.get("odds") or {}
        market_signal = StandardReportRenderer._as_dict(math_results.get("market_signal"))
        odds_movement = StandardReportRenderer._as_dict(math_results.get("odds_movement"))
        match_context = StandardReportRenderer._as_dict(math_results.get("match_context"))
        handicap_signal = StandardReportRenderer._as_dict(math_results.get("handicap_signal"))
        goals_signal = StandardReportRenderer._as_dict(math_results.get("goals_signal"))
        scoreline_signal = StandardReportRenderer._as_dict(math_results.get("scoreline_signal"))
        leg_signal = StandardReportRenderer._as_dict(math_results.get("leg_signal"))
        xg_signal = StandardReportRenderer._as_dict(math_results.get("xg_signal") or (math_results.get("model_input") or {}).get("xg_signal"))
        calibration = StandardReportRenderer._as_dict(math_results.get("calibration_report"))
        consistency = StandardReportRenderer._as_dict(math_results.get("consistency_report"))
        decision = StandardReportRenderer._as_dict(math_results.get("decision"))
        fusion = StandardReportRenderer._as_dict(math_results.get("probability_fusion"))
        llm_analysis = StandardReportRenderer._as_dict(math_results.get("llm_analysis"))

        home = parsed.home_team_raw
        away = parsed.away_team_raw
        report_lines = [
            f"# {home} vs {away} 赛事深度分析报告（竞彩数据 + 奇门辅助版）",
            "",
            f"> 报告生成时间: {datetime.now().isoformat(timespec='seconds')}  ",
            f"> 数据来源: {', '.join(data_report.data_sources_used) if data_report.data_sources_used else '无'}  ",
            "> 分析师: AI Football Analyst  ",
            "> 模型版本: v5.0 Jingcai-Qimen  ",
            f"> 置信度: {data_report.data_completeness_score:.0f}%",
            "",
            "---",
            "",
            "## 一、核心数据与基本面更新",
            "",
            "### 1. 比赛基本信息",
            "",
            "| 数据维度 | 详细信息 |",
            "|----------|----------|",
            f"| **场次** | {jingcai.get('match_num', '-')} |",
            f"| **赛事** | {jingcai.get('league') or (match.league.get('name') if match else '-')} |",
            f"| **比赛时间** | {jingcai.get('match_date', '')} {jingcai.get('match_time', '')} |",
            f"| **对阵** | {home} vs {away} |",
            f"| **竞彩让球** | {jingcai.get('handicap', '-')} |",
            f"| **数据完整度** | {data_report.data_completeness_score:.0f}% |",
            f"| **数据来源** | {', '.join(data_report.data_sources_used) if data_report.data_sources_used else '无'} |",
            "",
            "#### 数据完整度明细",
            "",
            "| 数据项 | 得分 | 状态 | 来源 |",
            "|--------|------|------|------|",
            *StandardReportRenderer._completeness_rows(getattr(data_report, "data_completeness_breakdown", {})),
            "",
            "### 2. 中国竞彩与市场数字",
            "",
            "| 市场 | 主胜/让胜 | 平/让平 | 客胜/让负 | 说明 |",
            "|------|----------|---------|----------|------|",
            StandardReportRenderer._odds_row("胜平负", jingcai.get("no_handicap_odds"), "竞彩普通胜平负"),
            StandardReportRenderer._odds_row("让球胜平负", jingcai.get("handicap_odds"), f"让球 {jingcai.get('handicap', '-')}"),
            StandardReportRenderer._odds_row("欧赔均值", jingcai.get("average_europe_odds"), "百家欧赔即时均值"),
            StandardReportRenderer._asian_row(jingcai.get("asian_average")),
            "",
            "### 2.1 500深层市场数据",
            "",
            "| 数据项 | 覆盖 | 核心信号 | 风险提示 |",
            "|--------|------|----------|----------|",
            *StandardReportRenderer._deep_market_rows(jingcai),
            "",
            "### 3. 球队基本面数据",
            "",
            StandardReportRenderer._team_section("主队", home, data_report.home_stats, data_report.home_home_stats, intelligence.get("home") or {}),
            "",
            StandardReportRenderer._team_section("客队", away, data_report.away_stats, data_report.away_away_stats, intelligence.get("away") or {}),
            "",
            "### 4. 500数据源单场分析页补充资料",
            "",
            "| 资料项 | 主队 | 客队 | 解读 |",
            "|--------|------|------|------|",
            *StandardReportRenderer._jingcai_profile_rows(jingcai, home, away),
            "",
            "#### 交锋与近期明细",
            "",
            "| 维度 | 摘要 |",
            "|------|------|",
            f"| **交锋概览** | {jingcai.get('h2h_summary') or '-'} |",
            f"| **近次交锋** | {StandardReportRenderer._match_records_note(jingcai.get('h2h_records'))} |",
            f"| **主队近期** | {StandardReportRenderer._match_records_note((jingcai.get('recent_records') or {}).get(home))} |",
            f"| **客队近期** | {StandardReportRenderer._match_records_note((jingcai.get('recent_records') or {}).get(away))} |",
            "",
            "#### 阵容、伤停与推荐",
            "",
            "| 维度 | 主队 | 客队 |",
            "|------|------|------|",
            *StandardReportRenderer._lineup_rows(jingcai.get("predicted_lineups"), home, away),
            f"| **500澳门心水** | {StandardReportRenderer._macau_note(jingcai.get('macau_recommendation'))} | {StandardReportRenderer._macau_reason(jingcai.get('macau_recommendation'))} |",
            "",
            "---",
            "",
            "## 二、赛事情报、环境与市场数字变化",
            "",
            "### 1. 战术对位分析",
            "",
            "| 维度 | 主队 | 客队 | 对比分析 |",
            "|------|------|------|----------|",
            StandardReportRenderer._comparison_row("进攻效率", data_report.home_stats, data_report.away_stats, "goals_for"),
            StandardReportRenderer._comparison_row("防线稳定性", data_report.home_stats, data_report.away_stats, "goals_against", lower_better=True),
            StandardReportRenderer._tag_row("战术风格", intelligence),
            "",
            f"**战术预测**：{StandardReportRenderer._tactical_summary(data_report)}",
            "",
            "### 1.1 补充数据覆盖",
            "",
            "| 字段 | 获取状态 | 数据源/下一步 |",
            "|------|----------|---------------|",
            *StandardReportRenderer._supplemental_rows(supplemental),
            "",
            "### 2. 市场数字历史与收盘线观察",
            "",
            "| 市场 | 快照数 | 初始/首次 | 最新 | 临场候选 | 解读 |",
            "|------|--------|-----------|------|----------|------|",
            *StandardReportRenderer._odds_history_rows(odds_history),
            "",
            f"**CLV/收盘线提示**：{StandardReportRenderer._clv_note(odds_history)}",
            "",
            f"**市场数字变化信号**：{StandardReportRenderer._odds_movement_note(odds_movement)}",
            "",
            "### 3. 天气与场地影响",
            "",
            "| 因素 | 详情 | 影响分析 |",
            "|------|------|----------|",
            f"| **比赛地点** | {weather.get('location', '-')} | {weather.get('source', '-')} |",
            f"| **当地开赛时间** | {weather.get('local_match_datetime', '-')} | {weather.get('timezone', '-')} |",
            f"| **温度** | {weather.get('temperature_c', '-')}°C | {StandardReportRenderer._weather_temp_note(weather)} |",
            f"| **降雨** | {weather.get('precipitation_mm', '-')}mm | {weather.get('risk_note', '-')} |",
            f"| **风速** | {weather.get('wind_speed_kmh', '-')}km/h | {StandardReportRenderer._weather_wind_note(weather)} |",
            "",
            "---",
            "",
            "## 三、集成决策与风控校验",
            "",
            "### 1. 市场信号与比赛语境",
            "",
            "| 模块 | 结果 | 解读 |",
            "|------|------|------|",
            f"| **市场热门方** | {StandardReportRenderer._market_favorite(market_signal, home, away)} | 强度: {market_signal.get('market_strength', '-')}，分歧: {market_signal.get('disagreement', '-')} |",
            f"| **亚盘/竞彩让球** | {market_signal.get('asian_handicap', '-')} / {market_signal.get('handicap', '-')} | {market_signal.get('pressure_side', '-')} |",
            f"| **市场数字变化方向** | {odds_movement.get('market_bias', '-')} | {odds_movement.get('strongest_move') or odds_movement.get('clv_note', '-')} |",
            f"| **比赛语境** | {match_context.get('competition_type', '-')} | {match_context.get('motivation_note', '-')} |",
            f"| **xG/xGA源** | {StandardReportRenderer._xg_source_label(xg_signal)} | 主队xG {StandardReportRenderer._num(xg_signal.get('home_xg'))} / 客队xG {StandardReportRenderer._num(xg_signal.get('away_xg'))}；xG差 {StandardReportRenderer._num(xg_signal.get('xg_edge'))}；xGA差 {StandardReportRenderer._num(xg_signal.get('xga_edge'))} |",
            f"| **友谊赛子类型** | {match_context.get('friendly_subtype', '-')} | 战意 {StandardReportRenderer._pct(match_context.get('motivation_score'))} / 客队脆弱 {StandardReportRenderer._pct(match_context.get('away_vulnerability_score'))} |",
            f"| **高总球/打穿触发** | 高总球风险 {StandardReportRenderer._pct(match_context.get('high_scoring_risk'))} | 强队打穿触发: {'是' if match_context.get('favorite_cover_trigger') else '否'} |",
            f"| **波动等级** | {match_context.get('volatility_score', '-')} | {'、'.join(match_context.get('tags') or []) or '-'} |",
            "",
            "### 1.1 LEG赢深校验",
            "",
            "| 维度 | 评分 | 判断 |",
            "|------|------|------|",
            *StandardReportRenderer._leg_rows(leg_signal),
            "",
            f"**LEG提示**：{leg_signal.get('scoreline_hint', '-') if leg_signal else '-'}",
            "",
            "### 1.2 LEG强弱深度量化",
            "",
            "| 量化维度 | 主队 | 客队 | 解读 |",
            "|------|------:|------:|------|",
            *StandardReportRenderer._leg_depth_rows(leg_signal, home, away),
            "",
            "### 1.3 概率融合校准",
            "",
            "| 来源 | 权重 | 主胜 | 平局 | 客胜 | 预期进球 | 大2.5 |",
            "|------|------|------|------|------|----------|------|",
            *StandardReportRenderer._fusion_rows(fusion),
            "",
            f"**融合说明**：{'；'.join((fusion.get('adjustments') or []) + (fusion.get('warnings') or [])) or '未启用历史/市场融合校准'}",
            "",
            "### 1.4 复盘校准与一致性检查",
            "",
            "| 检查项 | 状态 | 说明 |",
            "|------|------|------|",
            *StandardReportRenderer._calibration_rows(calibration),
            *StandardReportRenderer._consistency_rows(consistency),
            "",
            "### 2. 让球与进球独立模型",
            "",
            "| 模型 | 预测 | 概率/信心 | 风险备注 |",
            "|------|------|-----------|----------|",
            f"| **让球胜平负** | {handicap_signal.get('cover_side', '-')} | 让胜 {StandardReportRenderer._pct(handicap_signal.get('cover_probability'))} / 让平 {StandardReportRenderer._pct(handicap_signal.get('push_probability'))} / 让负 {StandardReportRenderer._pct(handicap_signal.get('fail_probability'))} / 信心 {handicap_signal.get('confidence', '-')} | {'；'.join(handicap_signal.get('warnings') or []) or '-'} |",
            f"| **进球数** | {goals_signal.get('goals_direction', '-')} | 大于2.5 {StandardReportRenderer._pct(goals_signal.get('over_25_probability'))} / 信心 {goals_signal.get('confidence', '-')} | {'；'.join(goals_signal.get('warnings') or []) or '-'} |",
            f"| **总球去偏** | {StandardReportRenderer._goals_debias_label(goals_signal)} | 独立均值 {StandardReportRenderer._num(goals_signal.get('independent_goal_mean'))} / 500均值 {StandardReportRenderer._num(goals_signal.get('market_goal_mean'))} / 最终均值 {StandardReportRenderer._num(goals_signal.get('final_goal_mean'))} | {'；'.join(goals_signal.get('notes') or []) or '-'} |",
            "",
            "#### 总球分布",
            "",
            "| 区间 | 概率 | 解读 |",
            "|------|------|------|",
            *StandardReportRenderer._goals_distribution_rows(goals_signal),
            "",
            "| 精确总球 | 概率 |",
            "|------|------|",
            *StandardReportRenderer._goals_exact_distribution_rows(goals_signal),
            "",
            "### 3. 最终证据评分",
            "",
            f"**综合结论**：{decision.get('summary', '未生成集成决策')}  ",
            f"**核心推荐**：{decision.get('primary_pick', '-')}  ",
            f"**是否进入组合思路**：{'允许' if decision.get('parlay_allowed') else '不建议'}",
            "",
            "| 证据 | 权重 | 方向 | 说明 |",
            "|------|------|------|------|",
            *StandardReportRenderer._decision_evidence_rows(decision),
            "",
            "**决策风险提示**：",
            *[f"- {item}" for item in (decision.get("warnings") or ["无额外风险提示"])[:6]],
            "",
            "---",
            "",
            "## 四、泊松分布模型预测",
            "",
            "### 1. 基础数据输入",
            "",
            "| 指标 | 主队 | 客队 | 说明 |",
            "|------|------|------|------|",
            f"| **场均进球（xG近似）** | {StandardReportRenderer._avg(data_report.home_stats, 'goals_for')} | {StandardReportRenderer._avg(data_report.away_stats, 'goals_for')} | 近况进攻火力 |",
            f"| **场均失球（xGA近似）** | {StandardReportRenderer._avg(data_report.home_stats, 'goals_against')} | {StandardReportRenderer._avg(data_report.away_stats, 'goals_against')} | 近况防守稳定性 |",
            f"| **主客场拆分** | {StandardReportRenderer._split_desc(data_report.home_home_stats)} | {StandardReportRenderer._split_desc(data_report.away_away_stats)} | 优先用于模型输入 |",
            "",
            "### 2. 赛果概率分布",
            "",
            "| 结果 | 概率 | 置信度 | 说明 |",
            "|------|------|--------|------|",
            f"| **{home}胜** | **{poisson.home_win_prob:.1%}** | {StandardReportRenderer._prob_conf(poisson.home_win_prob)} | 模型主胜概率 |",
            f"| **平局** | **{poisson.draw_prob:.1%}** | {StandardReportRenderer._prob_conf(poisson.draw_prob)} | 模型平局概率 |",
            f"| **{away}胜** | **{poisson.away_win_prob:.1%}** | {StandardReportRenderer._prob_conf(poisson.away_win_prob)} | 模型客胜概率 |",
            "",
            "### 3. 进球数预测",
            "",
            "| 预测维度 | 概率 | 说明 |",
            "|----------|------|------|",
            f"| **大2.5球** | {StandardReportRenderer._pct(goals_signal.get('over_25_probability'))} | {StandardReportRenderer._over_note(goals_signal.get('over_25_probability') or poisson.over_25_prob)} |",
            f"| **小2.5球** | {StandardReportRenderer._pct(1 - goals_signal.get('over_25_probability')) if goals_signal.get('over_25_probability') is not None else f'{poisson.under_25_prob:.1%}'} | {StandardReportRenderer._over_note(1 - goals_signal.get('over_25_probability')) if goals_signal.get('over_25_probability') is not None else StandardReportRenderer._over_note(poisson.under_25_prob)} |",
            f"| **双方进球** | {poisson.btts_yes_prob:.1%} | BTTS yes 概率 |",
            f"| **总进球区间** | {goals_signal.get('goals_direction') or StandardReportRenderer._goal_range(poisson)} | 基于独立模型、500总球表与比分分布 |",
            "",
            "### 4. 比分概率分布（Top 5）",
            "",
            f"**比分融合说明**：{'；'.join((scoreline_signal.get('notes') or []) + (scoreline_signal.get('warnings') or [])) or '未启用比分融合层'}",
            "",
            "| 比分 | 融合排序权重 | 泊松概率 | 500表概率 | 排名 | 分层 | 说明 |",
            "|------|------|------|------|------|------|------|",
            *StandardReportRenderer._score_rows(poisson, scoreline_signal),
            "",
            "---",
            "",
            "## 五、奇门遁甲辅助分析",
            "",
            "> 奇门结果只作为低权重辅助和风险提示，不直接改变泊松概率、风险系数或风险分层。",
            "",
            "### 1. 奇门局像",
            "",
            "| 维度 | 结果 |",
            "|------|------|",
            f"| **局象** | {qimen.get('dun_type', '-')}{qimen.get('ju_number', '-')}局 |",
            f"| **日时** | {qimen.get('day_stem', '-') }日 {qimen.get('hour_stem', '-')}{qimen.get('hour_branch', '-')}时 |",
            f"| **局像总断** | {qimen.get('image_summary', '-')} |",
            f"| **奇门胜平负** | {qimen.get('qimen_result_prediction', '-')} |",
            f"| **奇门预测比分** | {qimen.get('predicted_score', '-')} |",
            f"| **波动等级** | {qimen.get('volatility', '-')} |",
            f"| **奇门信心** | {qimen.get('confidence', '-')} |",
            "",
            "### 2. 主客与平局象",
            "",
            "| 象位 | 八门 | 九星 | 八神 | 解读 |",
            "|------|------|------|------|------|",
            StandardReportRenderer._qimen_symbol_row("主队宫", qimen.get("home_symbol") or {}),
            StandardReportRenderer._qimen_symbol_row("客队宫", qimen.get("away_symbol") or {}),
            StandardReportRenderer._qimen_symbol_row("平局象", qimen.get("draw_symbol") or {}),
            "",
            "**奇门风险提示**：",
            *[f"- {flag}" for flag in (qimen.get("risk_flags") or ["无额外奇门风险提示"])[:5]],
            "",
            "---",
            "",
            "## 六、风险系数与风险分层",
            "",
            "### 1. 核心方向",
            "",
            "| 方向选项 | 表格数值 | 模型概率 | EV | 风险系数 | 建议风险分层 | 说明 |",
            "|----------|------|----------|----|----------|--------------|------|",
            *StandardReportRenderer._kelly_rows(kelly_results),
            "",
            "### 2. 风险分层方案",
            "",
            *StandardReportRenderer._strategy_lines(betting_strategy),
            "",
            "---",
            "",
            "## 七、原有模型分析与 GPT-5.5 联网复核",
            "",
            "> 原有模型先独立完成计算；随后 Codex GPT-5.5 使用联网搜索进行二次复核。两套结果分别保留，不互相覆盖。",
            "",
            "### 1. 原有模型分析结果",
            "",
            "| 维度 | 原有模型结论 |",
            "|------|--------------|",
            *StandardReportRenderer._model_result_rows(home, away, poisson, decision, handicap_signal, goals_signal),
            "",
            "### 2. GPT-5.5 联网复核结果",
            "",
            "| 维度 | AI复核结论 |",
            "|------|------------|",
            *StandardReportRenderer._llm_analysis_rows(llm_analysis),
            "",
            "**AI复核风险提示**：",
            *[f"- {item}" for item in (llm_analysis.get("risk_factors") or ["大模型复核未提供额外风险提示"])[:6]],
            "",
            "### 3. 模型与 GPT 复核对照",
            "",
            *StandardReportRenderer._model_gpt_comparison(decision, llm_analysis),
            "",
            *StandardReportRenderer._agent_prompt_block(llm_analysis),
            "",
            "---",
            "",
            "## 八、最终结论与核心观点",
            "",
            "### 1. 模型预测汇总",
            "",
            "| 预测维度 | 预测结果 | 概率 | 置信度 |",
            "|----------|----------|------|--------|",
            *StandardReportRenderer._prediction_summary_rows(home, away, poisson, qimen),
            "",
            "### 2. 最终赛事建议",
            "",
            f"**核心方向**：{decision.get('primary_pick') or StandardReportRenderer._core_bet(kelly_results)}  ",
            f"**博取选项**：{StandardReportRenderer._longshot_bet(kelly_results)}  ",
            f"**规避方向**：{StandardReportRenderer._avoid_note(kelly_results)}；{('不进组合' if not decision.get('parlay_allowed') else '可低权重进入组合')}",
            "",
            "**风险提示**：",
            "- 竞彩市场数字会随临场变化，建议结合收盘线复核。",
            "- AI二次分析只做复核和解释，不直接替代模型概率、表格事实和风控规则。",
            "- 奇门遁甲仅作辅助参考，不应替代数据模型和风控。",
            "- 多场组合波动显著高于单场，建议控制投入比例。",
            "",
            "---",
            "",
            "**免责声明**: 本报告仅供学习和研究使用，不构成任何保证性结论。请理性对待赛事分析，遵守当地法律法规。",
        ]
        return StandardReportRenderer._sanitize_user_text("\n".join(report_lines))

    @staticmethod
    def _sanitize_user_text(text: str) -> str:
        replacements = {
            "投注": "核心方向",
            "下注": "核心方向",
            "赌博": "高风险行为",
            "串关": "组合",
            "加仓": "提高权重",
            "赔率": "市场数字",
            "博彩": "赛事市场",
            "重仓": "高权重",
            "凯利": "风险系数",
            "金额": "权重",
            "奖金": "回报",
            "购彩": "参与",
            "彩票": "赛事票据",
            "盘口": "让球信息",
            "投资": "赛事分析",
            "资金": "风险权重",
            "穿盘": "打穿让球",
            "深盘": "深让球",
            "大比分": "高总球",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text

    @staticmethod
    def _llm_analysis_rows(llm: Dict[str, Any]) -> List[str]:
        if not llm:
            return [
                "| **执行状态** | 未执行或未写入 math_results |",
                "| **复核建议** | 沿用模型和风控结论 |",
            ]
        return [
            f"| **执行状态** | {llm.get('status', '-')} / {llm.get('provider', '-')} / {llm.get('model', '-')} |",
            f"| **模型一致性** | {llm.get('model_agreement', '-')} |",
            f"| **信心调整** | {llm.get('confidence_adjustment', '-')} |",
            f"| **联网搜索评价** | {llm.get('web_evidence_assessment', '-')} |",
            f"| **比赛形势** | {llm.get('match_situation', '-')} |",
            f"| **主队分析** | {llm.get('home_team_strength_analysis', '-')} |",
            f"| **客队分析** | {llm.get('away_team_strength_analysis', '-')} |",
            f"| **伤停/首发可信度** | {llm.get('injury_impact_analysis', '-')} |",
            f"| **战术与阵容** | {llm.get('tactical_analysis', '-')} |",
            f"| **AI比分方向** | {llm.get('predicted_score', '-')} / 概率 {StandardReportRenderer._pct(llm.get('predicted_score_probability'))} |",
            f"| **模型评论** | {llm.get('model_result_commentary', '-')} |",
            f"| **AI最终复核建议** | {llm.get('final_recommendation', '-')} |",
        ]

    @staticmethod
    def _model_result_rows(
        home: str,
        away: str,
        poisson: Any,
        decision: Dict[str, Any],
        handicap: Dict[str, Any],
        goals: Dict[str, Any],
    ) -> List[str]:
        if not poisson:
            return ["| **执行状态** | 原有模型未生成结果 |"]
        likely = poisson.most_likely_score
        return [
            "| **执行状态** | 已完成，结果在 GPT 复核前生成 |",
            f"| **胜平负概率** | {home}胜 {poisson.home_win_prob:.1%} / 平 {poisson.draw_prob:.1%} / {away}胜 {poisson.away_win_prob:.1%} |",
            f"| **模型比分** | {likely[0]}-{likely[1]} |",
            f"| **让球结论** | {decision.get('handicap_pick') or handicap.get('cover_side') or '-'} |",
            f"| **进球结论** | {decision.get('goals_pick') or goals.get('goals_direction') or '-'} |",
            f"| **原有核心建议** | {decision.get('primary_pick', '-')} |",
            f"| **原有信心/组合** | {decision.get('confidence', '-')} / {'允许' if decision.get('parlay_allowed') else '不建议'} |",
        ]

    @staticmethod
    def _model_gpt_comparison(decision: Dict[str, Any], llm: Dict[str, Any]) -> List[str]:
        status = llm.get("status", "未执行")
        agreement = llm.get("model_agreement", "unknown")
        adjustment = llm.get("confidence_adjustment", "none")
        return [
            "| 对照项 | 结果 |",
            "|--------|------|",
            f"| **原有模型建议** | {decision.get('primary_pick', '-')} |",
            f"| **GPT复核建议** | {llm.get('final_recommendation', '-')} |",
            f"| **一致性** | {agreement} |",
            f"| **信心调整** | {adjustment} |",
            f"| **复核执行状态** | {status} / {llm.get('provider', '-')} / {llm.get('model', '-')} |",
        ]

    @staticmethod
    def _agent_prompt_block(llm: Dict[str, Any]) -> List[str]:
        prompt = (llm or {}).get("agent_prompt") or ""
        if not prompt:
            return []
        max_chars = 8000
        suffix = "\n\n[提示：Prompt 已按报告展示长度截断，完整内容可在 JSON 的 llm_analysis.agent_prompt 字段查看。]" if len(prompt) > max_chars else ""
        visible = prompt[:max_chars] + suffix
        return [
            "### Agent 二次复核 Prompt",
            "",
            "将下面这段内容交给 Codex、OpenClaw 或其他可联网 Agent，可让它在不需要项目内大模型 key 的情况下继续复核：",
            "",
            "```text",
            visible,
            "```",
        ]

    @staticmethod
    def render_multi_match_summary(rows: List[Dict[str, Any]]) -> str:
        lines = [
            "# 多场比赛汇总",
            "",
            "## 单场结论",
            "",
            "| 场次 | 比赛 | 模型倾向 | 推荐玩法 | 参考概率 | 表格数值 | 比分方向 | 球数 |",
            "|------|------|----------|----------|----------|------|----------|------|",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('match_num', '-')} | {row.get('match', '-')} | {row.get('model_lean', '-')} | "
                f"{row.get('recommendation', '-')} | {row.get('probability', '-')} | {row.get('odds', '-')} | "
                f"{row.get('score_direction', '-')} | {row.get('goals', '-')} |"
            )
        lines.extend([
            "",
            "## 最值得关注的价值点",
            "",
            "**第一档：**",
            *[f"- {item}" for item in StandardReportRenderer._tier_items(rows, 1)],
            "",
            "**第二档：**",
            *[f"- {item}" for item in StandardReportRenderer._tier_items(rows, 2)],
            "",
            "**第三档，小注搏：**",
            *[f"- {item}" for item in StandardReportRenderer._tier_items(rows, 3)],
            "",
            "## 爆款 n 串 1 建议",
            "",
            "### 稳健 2 场组合",
            "```text",
            "{稳健组合思路}",
            "理论表格数值约：{稳健理论表格数值}",
            "```",
            "",
            "### 进取 3 场组合",
            "```text",
            "{进取组合思路}",
            "理论表格数值约：{进取理论表格数值}",
            "```",
            "",
            "### 高关注 4 场组合",
            "```text",
            "{高关注组合思路}",
            "理论表格数值约：{高关注理论表格数值}",
            "```",
        ])
        return "\n".join(lines)

    @staticmethod
    def _odds_row(label: str, odds: Optional[Dict[str, Any]], note: str) -> str:
        if not odds:
            return f"| **{label}** | - | - | - | 暂无该市场竞彩表格数值 |"
        return f"| **{label}** | {odds.get('home_win', '-')} | {odds.get('draw', '-')} | {odds.get('away_win', '-')} | {note} |"

    @staticmethod
    def _asian_row(asian: Optional[Dict[str, Any]]) -> str:
        if not asian:
            return "| **亚盘均值** | - | - | - | 暂无亚盘均值 |"
        return (
            f"| **亚盘均值** | {asian.get('current_home_water', '-')} | "
            f"{asian.get('current_handicap_numeric', '-')} | {asian.get('current_away_water', '-')} | 即时亚盘均值 |"
        )

    @staticmethod
    def _deep_market_rows(jingcai: Dict[str, Any]) -> List[str]:
        europe = jingcai.get("europe_market") or {}
        asian = jingcai.get("asian_market") or {}
        handicap = jingcai.get("handicap_market") or {}
        score = jingcai.get("score_market") or {}
        mixed = jingcai.get("mixed_market") or {}
        return [
            (
                f"| 百家欧赔 | {europe.get('company_count', 0)}家公司 | "
                f"{StandardReportRenderer._market_average_note(europe)}；分歧指数 {StandardReportRenderer._cv_note((europe.get('kelly_cv') or {}))} | "
                f"{StandardReportRenderer._market_warning(europe)} |"
            ),
            (
                f"| 亚盘对比 | {asian.get('company_count', 0)}家公司 | "
                f"{StandardReportRenderer._asian_market_note(asian)}；水位分歧 {StandardReportRenderer._cv_note((asian.get('water_cv') or {}))} | "
                f"{StandardReportRenderer._market_warning(asian)} |"
            ),
            (
                f"| 让球指数 | {handicap.get('company_count', 0)}家公司 | "
                f"{StandardReportRenderer._market_average_note(handicap)}；分歧指数 {StandardReportRenderer._cv_note((handicap.get('kelly_cv') or {}))} | "
                f"{StandardReportRenderer._market_warning(handicap)} |"
            ),
            (
                f"| 比分表格数值/指数 | {len(mixed.get('score_odds') or {})}个竞彩选项 / {score.get('company_count', 0)}家公司 | "
                f"{StandardReportRenderer._score_market_note(score)} | {StandardReportRenderer._market_warning(score)} |"
            ),
            (
                f"| 总进球数表格数值 | {len(mixed.get('total_goals_odds') or {})}个竞彩选项 | "
                f"{StandardReportRenderer._lowest_odds_note(mixed.get('total_goals_odds') or {})} | "
                f"{'-' if mixed.get('total_goals_odds') else '混合过关页暂未提供'} |"
            ),
            (
                f"| 半全场表格数值 | {len(mixed.get('half_full_odds') or {})}个竞彩选项 | "
                f"{StandardReportRenderer._lowest_odds_note(mixed.get('half_full_odds') or {})} | "
                f"{'-' if mixed.get('half_full_odds') else '混合过关页暂未提供'} |"
            ),
        ]

    @staticmethod
    def _market_average_note(market: Dict[str, Any]) -> str:
        avg = ((market.get("stats") or {}).get("average") or {})
        current = avg.get("current_odds")
        opening = avg.get("opening_odds")
        if not current:
            records = market.get("records") or []
            current = (records[0] or {}).get("current_odds") if records else None
            opening = (records[0] or {}).get("opening_odds") if records else None
        if not current:
            return "暂无均值"
        current_text = f"{current.get('home')}/{current.get('draw')}/{current.get('away')}"
        if opening:
            opening_text = f"{opening.get('home')}/{opening.get('draw')}/{opening.get('away')}"
            return f"即时 {current_text}，初始 {opening_text}"
        return f"即时 {current_text}"

    @staticmethod
    def _asian_market_note(market: Dict[str, Any]) -> str:
        avg = ((market.get("stats") or {}).get("average") or {})
        if avg:
            return (
                f"即时 {avg.get('current_home_water', '-')}/{avg.get('current_handicap', '-')}/{avg.get('current_away_water', '-')}，"
                f"初始 {avg.get('opening_home_water', '-')}/{avg.get('opening_handicap', '-')}/{avg.get('opening_away_water', '-')}"
            )
        records = market.get("records") or []
        if not records:
            return "暂无亚盘公司行"
        row = records[0]
        return (
            f"{row.get('company', '-')}: 即时 {row.get('current_home_water', '-')}/{row.get('current_handicap', '-')}/{row.get('current_away_water', '-')}"
        )

    @staticmethod
    def _score_market_note(market: Dict[str, Any]) -> str:
        jingcai_scores = (market.get("jingcai_top_scores") or [])[:5]
        if jingcai_scores:
            return "竞彩比分最低表格数值: " + "；".join(
                f"{score} @{odd:.2f}" for score, odd in jingcai_scores
            )
        top_scores = (((market.get("aggregate") or {}).get("top_scores")) or [])[:3]
        if not top_scores:
            return "暂无比分公司表格数值"
        return "；".join(
            f"{item.get('score')} {StandardReportRenderer._pct(item.get('probability'))}"
            for item in top_scores
        )

    @staticmethod
    def _lowest_odds_note(odds: Dict[str, Any], limit: int = 5) -> str:
        if not odds:
            return "暂无竞彩表格数值"
        valid = []
        for selection, odd in odds.items():
            try:
                valid.append((selection, float(odd)))
            except (TypeError, ValueError):
                continue
        return "；".join(
            f"{selection} @{odd:.2f}"
            for selection, odd in sorted(valid, key=lambda item: item[1])[:limit]
        ) or "暂无竞彩表格数值"

    @staticmethod
    def _cv_note(values: Dict[str, Any]) -> str:
        valid = []
        for key, value in values.items():
            if value is None:
                continue
            try:
                valid.append(f"{key}:{float(value):.3f}")
            except (TypeError, ValueError):
                continue
        return "、".join(valid) if valid else "暂无"

    @staticmethod
    def _market_warning(market: Dict[str, Any]) -> str:
        warnings = market.get("warnings") or []
        return "；".join(warnings[:2]) if warnings else "-"

    @staticmethod
    def _completeness_rows(breakdown: Dict[str, Any]) -> List[str]:
        labels = {
            "jingcai_odds": "竞彩市场数字",
            "deep_market": "深层市场数字",
            "team_form": "近期状态",
            "lineups": "首发阵容",
            "injuries": "伤停确认",
            "technical_stats": "技术统计",
            "weather": "天气场地",
            "schedule_density": "赛程密度",
            "web_evidence": "联网证据",
        }
        if not breakdown:
            return ["| - | 0/0 | missing | - |"]
        return [
            f"| **{labels.get(key, key)}** | {item.get('earned', 0)}/{item.get('max', 0)} | "
            f"{item.get('status', '-')} | {item.get('source') or '-'} |"
            for key, item in breakdown.items()
        ]

    @staticmethod
    def _team_section(label: str, team: str, stats: Any, split_stats: Any, info: Dict[str, Any]) -> str:
        tags = "、".join(info.get("tactical_tags") or []) or "-"
        injuries = info.get("injuries") or []
        injury_text = f"{len(injuries)}人" if injuries else "暂无可靠伤停"
        rank = info.get("league_rank") or "-"
        elo = info.get("clubelo_rating")
        elo_text = f"{elo:.0f}" if isinstance(elo, (int, float)) else "-"
        supplemental_notes = "；".join(info.get("supplemental_notes") or []) or "-"
        rest = f"{info.get('rest_days')}天" if info.get("rest_days") is not None else "-"
        return "\n".join([
            f"#### {team}（{label}）",
            "",
            "| 数据维度 | 详细信息 |",
            "|----------|----------|",
            f"| **联赛排名** | {rank} |",
            f"| **Elo/强弱基准** | {elo_text} |",
            f"| **近期状态** | {StandardReportRenderer._record(stats)}，场均进球{StandardReportRenderer._avg(stats, 'goals_for')}个，场均失球{StandardReportRenderer._avg(stats, 'goals_against')}个 |",
            f"| **主/客表现** | {StandardReportRenderer._record(split_stats)}，场均进球{StandardReportRenderer._avg(split_stats, 'goals_for')}个，场均失球{StandardReportRenderer._avg(split_stats, 'goals_against')}个 |",
            f"| **伤停情况** | {injury_text} |",
            f"| **战术标签** | {tags} |",
            f"| **补源备注** | {supplemental_notes} |",
            f"| **赛程密度** | {rest} |",
        ])

    @staticmethod
    def _jingcai_profile_rows(jingcai: Dict[str, Any], home: str, away: str) -> List[str]:
        rankings = jingcai.get("fifa_rankings") or {}
        standings = jingcai.get("league_standings") or {}
        future = jingcai.get("future_fixtures") or {}
        return [
            (
                f"| FIFA排名 | {StandardReportRenderer._latest_rank(rankings.get(home))} | "
                f"{StandardReportRenderer._latest_rank(rankings.get(away))} | 国家队比赛优先参考 |"
            ),
            (
                f"| 联赛/赛事积分 | {StandardReportRenderer._standings_note(standings.get(home))} | "
                f"{StandardReportRenderer._standings_note(standings.get(away))} | 有些友谊赛页面该项为空 |"
            ),
            (
                f"| 未来赛程 | {StandardReportRenderer._future_note(future.get(home))} | "
                f"{StandardReportRenderer._future_note(future.get(away))} | 用于判断轮换和赛程压力 |"
            ),
        ]

    @staticmethod
    def _latest_rank(rows: Optional[List[Dict[str, Any]]]) -> str:
        if not rows:
            return "-"
        row = rows[0]
        month = row.get("月份", "")
        rank = row.get("世界排名", "-")
        points = row.get("积分", "-")
        change = row.get("排名变化", "")
        return f"{month} 第{rank}位，积分{points}，变化{change}".strip()

    @staticmethod
    def _standings_note(rows: Optional[List[Dict[str, Any]]]) -> str:
        if not rows:
            return "-"
        non_empty = [row for row in rows if any(value for key, value in row.items() if key != "类别")]
        if not non_empty:
            return "页面为空"
        row = non_empty[0]
        return f"{row.get('类别', '-')}: {row.get('比赛', '-')}场，排名{row.get('排名', '-')}"

    @staticmethod
    def _future_note(rows: Optional[List[Dict[str, Any]]]) -> str:
        if not rows:
            return "-"
        first = rows[0]
        return f"{first.get('date', '-')} {first.get('home_team', '-')} vs {first.get('away_team', '-')}，相隔{first.get('days_gap', '-')}"

    @staticmethod
    def _match_records_note(rows: Optional[List[Dict[str, Any]]]) -> str:
        if not rows:
            return "-"
        snippets = []
        for row in rows[:3]:
            score = "-"
            if row.get("home_score") is not None and row.get("away_score") is not None:
                score = f"{row.get('home_score')}-{row.get('away_score')}"
            snippets.append(
                f"{row.get('date', '-')}{row.get('competition', '')}: {row.get('home_team', '-')} {score} {row.get('away_team', '-')}"
            )
        return "；".join(snippets)

    @staticmethod
    def _lineup_rows(lineups: Optional[Dict[str, Dict[str, List[str]]]], home: str, away: str) -> List[str]:
        lineups = lineups or {}
        home_lineup = lineups.get(home) or {}
        away_lineup = lineups.get(away) or {}
        return [
            (
                f"| **预计首发** | {StandardReportRenderer._players_note(home_lineup.get('starting'))} | "
                f"{StandardReportRenderer._players_note(away_lineup.get('starting'))} |"
            ),
            (
                f"| **替补名单** | {StandardReportRenderer._players_note(home_lineup.get('substitutes'))} | "
                f"{StandardReportRenderer._players_note(away_lineup.get('substitutes'))} |"
            ),
            (
                f"| **伤病/停赛** | {StandardReportRenderer._absences_note(home_lineup)} | "
                f"{StandardReportRenderer._absences_note(away_lineup)} |"
            ),
        ]

    @staticmethod
    def _players_note(players: Optional[List[str]]) -> str:
        if not players:
            return "-"
        suffix = f" 等{len(players)}人" if len(players) > 3 else ""
        return "、".join(players[:3]) + suffix

    @staticmethod
    def _absences_note(lineup: Dict[str, List[str]]) -> str:
        injuries = lineup.get("injuries") or []
        suspensions = lineup.get("suspensions") or []
        if not injuries and not suspensions:
            return "页面无记录"
        parts = []
        if injuries:
            parts.append("伤病: " + StandardReportRenderer._players_note(injuries))
        if suspensions:
            parts.append("停赛: " + StandardReportRenderer._players_note(suspensions))
        return "；".join(parts)

    @staticmethod
    def _macau_note(recommendation: Optional[Dict[str, Any]]) -> str:
        if not recommendation:
            return "-"
        pick = recommendation.get("pick") or "-"
        h2h = recommendation.get("h2h") or "-"
        return f"{pick}；对赛{h2h}"

    @staticmethod
    def _macau_reason(recommendation: Optional[Dict[str, Any]]) -> str:
        if not recommendation:
            return "-"
        return recommendation.get("reason") or "-"

    @staticmethod
    def _record(stats: Any) -> str:
        if not stats:
            return "-"
        return f"{stats.wins}胜{stats.draws}平{stats.losses}负"

    @staticmethod
    def _avg(stats: Any, field: str) -> str:
        if not stats or not stats.matches_played:
            return "-"
        return f"{getattr(stats, field) / stats.matches_played:.2f}"

    @staticmethod
    def _comparison_row(label: str, home_stats: Any, away_stats: Any, field: str, lower_better: bool = False) -> str:
        home = StandardReportRenderer._avg(home_stats, field)
        away = StandardReportRenderer._avg(away_stats, field)
        note = "主队更优" if home != "-" and away != "-" and ((float(home) < float(away)) if lower_better else (float(home) > float(away))) else "客队或均衡"
        return f"| **{label}** | {home} | {away} | {note} |"

    @staticmethod
    def _tag_row(label: str, intelligence: Dict[str, Any]) -> str:
        home = "、".join((intelligence.get("home") or {}).get("tactical_tags") or []) or "-"
        away = "、".join((intelligence.get("away") or {}).get("tactical_tags") or []) or "-"
        return f"| **{label}** | {home} | {away} | 风格标签来自赛事情报与近况推断 |"

    @staticmethod
    def _tactical_summary(data_report: Any) -> str:
        notes = ((data_report.match_intelligence or {}).get("tactical_notes") or [])
        return "；".join(notes[:3]) if notes else "暂无额外战术情报，主要依据近况与主客场拆分。"

    @staticmethod
    def _supplemental_rows(supplemental: Dict[str, Any]) -> List[str]:
        if not supplemental:
            return ["| 补充数据源 | 未执行 | 检查 SupplementalDataCollector 配置 |"]
        rows = []
        sources = "、".join(supplemental.get("data_sources") or [])
        home = supplemental.get("home") or {}
        away = supplemental.get("away") or {}
        rows.append(
            f"| ClubElo强弱基准 | {StandardReportRenderer._coverage_status(home.get('clubelo_rating'), away.get('clubelo_rating'))} | {sources or 'ClubElo'} |"
        )
        historical = supplemental.get("historical_league") or {}
        rows.append(
            f"| 历史联赛市场数字/赛果 | {historical.get('matches_loaded', 0)}场样本 | {historical.get('source_url') or historical.get('warning') or '-'} |"
        )
        external = supplemental.get("external_sources") or {}
        rows.append(
            f"| 免费事件/场地补源 | {StandardReportRenderer._external_event_status(external)} | TheSportsDB / Open-Meteo定位兜底 |"
        )
        rows.append(
            f"| 外部市场数字补源 | {StandardReportRenderer._external_odds_status(external)} | Odds-API.io / The Odds API，有key自动启用 |"
        )
        missing = supplemental.get("missing_field_suggestions") or {}
        rows.append(
            f"| 伤停/首发缺口 | 待补 | {'、'.join(missing.get('injuries', [])[:3])} / {'、'.join(missing.get('lineups', [])[:3])} |"
        )
        rows.append(
            f"| 技术统计缺口 | 待补 | {'、'.join(missing.get('technical_stats', [])[:3])} |"
        )
        return rows

    @staticmethod
    def _external_event_status(external: Dict[str, Any]) -> str:
        event = (external or {}).get("thesportsdb") or {}
        if not event:
            return "未匹配"
        parts = [event.get("event"), event.get("date"), event.get("venue")]
        return " / ".join(str(part) for part in parts if part) or "已匹配"

    @staticmethod
    def _external_odds_status(external: Dict[str, Any]) -> str:
        if not external:
            return "未启用"
        statuses = []
        for key, label in [("odds_api_io", "Odds-API.io"), ("the_odds_api", "The Odds API")]:
            payload = external.get(key)
            if not payload:
                continue
            if payload.get("available"):
                bookmakers = payload.get("bookmakers")
                odds = payload.get("odds") or {}
                markets = payload.get("markets") or odds.get("markets")
                detail = f"{markets}市场" if markets else "已匹配事件"
                if bookmakers:
                    detail = f"{bookmakers}家公司/{detail}"
                statuses.append(f"{label}:{detail}")
            else:
                statuses.append(f"{label}:未匹配")
        return "；".join(statuses) if statuses else "未启用"

    @staticmethod
    def _coverage_status(home_value: Any, away_value: Any) -> str:
        if home_value is not None and away_value is not None:
            return "双方已获取"
        if home_value is not None or away_value is not None:
            return "单方已获取"
        return "未获取"

    @staticmethod
    def _odds_history_rows(history: Dict[str, Any]) -> List[str]:
        markets = history.get("markets") or {}
        rows = []
        for key, label in [("nspf", "胜平负"), ("spf", "让球胜平负")]:
            payload = markets.get(key) or {}
            first = payload.get("first") or {}
            latest = payload.get("latest") or {}
            closing = "是" if payload.get("closing") else "否"
            rows.append(
                f"| **{label}** | {payload.get('snapshots', 0)} | "
                f"{StandardReportRenderer._odds_triplet(first)} | {StandardReportRenderer._odds_triplet(latest)} | "
                f"{closing} | {'已有历史记录' if payload else '暂无记录'} |"
            )
        return rows

    @staticmethod
    def _odds_triplet(payload: Dict[str, Any]) -> str:
        if not payload:
            return "-"
        return f"{payload.get('home_win')}/{payload.get('draw')}/{payload.get('away_win')}"

    @staticmethod
    def _clv_note(history: Dict[str, Any]) -> str:
        if not history:
            return "暂无市场数字历史，无法判断是否跑赢收盘线。"
        return "已记录市场数字快照，可在临场后比较核心方向与收盘线。"

    @staticmethod
    def _odds_movement_note(signal: Dict[str, Any]) -> str:
        if not signal:
            return "未执行市场数字变化分析。"
        if not signal.get("available"):
            warnings = "；".join(signal.get("warnings") or [])
            return warnings or signal.get("clv_note") or "快照不足，暂无法判断。"
        notes = "；".join(signal.get("notes") or [])
        return notes or signal.get("strongest_move") or "已有变化，但方向不明显。"

    @staticmethod
    def _weather_temp_note(weather: Dict[str, Any]) -> str:
        temp = weather.get("temperature_c")
        if temp is None:
            return "-"
        if temp >= 30:
            return "高温可能降低节奏"
        if temp <= 2:
            return "低温可能增加失误"
        return "温度影响有限"

    @staticmethod
    def _weather_wind_note(weather: Dict[str, Any]) -> str:
        wind = weather.get("wind_speed_kmh")
        if wind is None:
            return "-"
        return "大风需关注传中和定位球" if wind >= 25 else "风速影响有限"

    @staticmethod
    def _market_favorite(signal: Dict[str, Any], home: str, away: str) -> str:
        favorite = signal.get("favorite")
        if favorite == "home":
            return home
        if favorite == "away":
            return away
        if favorite == "draw":
            return "平局"
        return "-"

    @staticmethod
    def _fusion_rows(fusion: Dict[str, Any]) -> List[str]:
        components = fusion.get("components") or {}
        weights = fusion.get("weights") or {}
        if not components:
            return ["| - | - | - | - | - | - | - |"]
        labels = {
            "current": "当前基础模型",
            "market": "市场隐含概率",
            "historical": "历史国家队模型",
        }
        rows = []
        for key in ["current", "market", "historical"]:
            item = components.get(key)
            if not item:
                continue
            goals = f"{item.get('expected_home_goals', 0):.2f}-{item.get('expected_away_goals', 0):.2f}"
            rows.append(
                f"| **{labels.get(key, key)}** | {weights.get(key, 0):.0%} | "
                f"{StandardReportRenderer._pct(item.get('home_win'))} | "
                f"{StandardReportRenderer._pct(item.get('draw'))} | "
                f"{StandardReportRenderer._pct(item.get('away_win'))} | "
                f"{goals} | {StandardReportRenderer._pct(item.get('over_25'))} |"
            )
        return rows or ["| - | - | - | - | - | - | - |"]

    @staticmethod
    def _pct(value: Any) -> str:
        if value is None:
            return "-"
        try:
            return f"{float(value):.1%}"
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def _num(value: Any) -> str:
        if value is None:
            return "-"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def _goals_debias_label(goals_signal: Dict[str, Any]) -> str:
        if not goals_signal:
            return "-"
        return "已触发500去偏" if goals_signal.get("debias_applied") else "未触发去偏"

    @staticmethod
    def _goals_distribution_rows(goals_signal: Dict[str, Any]) -> List[str]:
        distribution = (goals_signal or {}).get("distribution") or {}
        if not distribution:
            return ["| - | - | 未生成总球分布 |"]
        labels = [
            ("0_1", "0-1球", "低比分/节奏受限"),
            ("2", "2球", "低中位"),
            ("3", "3球", "中位打开"),
            ("4_plus", "4+球", "上沿与开放局"),
        ]
        return [
            f"| **{label}** | {StandardReportRenderer._pct(distribution.get(key))} | {note} |"
            for key, label, note in labels
        ]

    @staticmethod
    def _goals_exact_distribution_rows(goals_signal: Dict[str, Any]) -> List[str]:
        distribution = (goals_signal or {}).get("exact_distribution") or {}
        if not distribution:
            return ["| - | - |"]
        labels = [
            ("0", "0球"),
            ("1", "1球"),
            ("2", "2球"),
            ("3", "3球"),
            ("4", "4球"),
            ("5", "5球"),
            ("6", "6球"),
            ("7_plus", "7+球"),
        ]
        return [
            f"| **{label}** | {StandardReportRenderer._pct(distribution.get(key))} |"
            for key, label in labels
        ]

    @staticmethod
    def _leg_rows(leg_signal: Dict[str, Any]) -> List[str]:
        if not leg_signal:
            return ["| - | - | 未生成LEG校验 |"]
        notes = leg_signal.get("notes") or []
        warnings = leg_signal.get("warnings") or []
        detail = "；".join((notes + warnings)[:4]) or "-"
        return [
            f"| **L 让球线** | {StandardReportRenderer._pct(leg_signal.get('line_score'))} | 市场深度与让球结算支持度 |",
            f"| **E 预期进球** | {StandardReportRenderer._pct(leg_signal.get('expected_goals_score'))} | 总球精确分布与比分层支持度 |",
            f"| **G 比赛语境** | {StandardReportRenderer._pct(leg_signal.get('game_context_score'))} | 出战、轮换、动机、天气与波动 |",
            f"| **综合** | {StandardReportRenderer._pct(leg_signal.get('total_score'))} | {leg_signal.get('depth_direction', '-')}；信心 {leg_signal.get('confidence', '-')}；{detail} |",
        ]

    @staticmethod
    def _xg_source_label(xg_signal: Dict[str, Any]) -> str:
        if not xg_signal:
            return "未生成"
        source = xg_signal.get("source")
        provider = xg_signal.get("provider") or "-"
        confidence = xg_signal.get("confidence") or "-"
        if source == "api_actual":
            return f"真实xG ({provider})，信心 {confidence}"
        if source == "proxy_calculated":
            return f"赛前proxy xG，信心 {confidence}"
        return f"{source or '-'} ({provider})"

    @staticmethod
    def _leg_depth_rows(leg_signal: Dict[str, Any], home: str, away: str) -> List[str]:
        if not leg_signal:
            return ["| - | - | - | 未生成LEG强弱深度量化 |"]

        home_depth = StandardReportRenderer._num(leg_signal.get("home_depth_score_10"))
        away_depth = StandardReportRenderer._num(leg_signal.get("away_depth_score_10"))
        gap = StandardReportRenderer._num(leg_signal.get("depth_gap_10"))
        leader = home if (leg_signal.get("depth_gap_10") or 0) >= 0 else away
        rows = [
            (
                "| **L 市场深度分** | "
                f"{StandardReportRenderer._num(leg_signal.get('home_line_score_10'))}/10 | "
                f"{StandardReportRenderer._num(leg_signal.get('away_line_score_10'))}/10 | "
                "市场深度、让球结算和分歧综合量化 |"
            ),
            (
                "| **E xG创造力分** | "
                f"{StandardReportRenderer._num(leg_signal.get('home_xg_score_10'))}/10 | "
                f"{StandardReportRenderer._num(leg_signal.get('away_xg_score_10'))}/10 | "
                "真实/proxy xG、xGA与总球空间综合量化 |"
            ),
            (
                "| **G 比赛语境分** | "
                f"{StandardReportRenderer._num(leg_signal.get('home_context_score_10'))}/10 | "
                f"{StandardReportRenderer._num(leg_signal.get('away_context_score_10'))}/10 | "
                "战意、天气、伤停、赛制与波动综合量化 |"
            ),
            (
                "| **综合强弱深度** | "
                f"**{home_depth}/10** | **{away_depth}/10** | "
                f"{leader} 深度优势差 {gap} 分；{leg_signal.get('depth_direction', '-')} |"
            ),
            (
                "| **LEG修正预期进球** | "
                f"**{StandardReportRenderer._num(leg_signal.get('home_leg_expected_goals'))}** | "
                f"**{StandardReportRenderer._num(leg_signal.get('away_leg_expected_goals'))}** | "
                "由xG/proxy xG叠加L/E/G深度后得到，用于解释比分Top和总球 |"
            ),
        ]
        return rows

    @staticmethod
    def _calibration_rows(calibration: Dict[str, Any]) -> List[str]:
        if not calibration:
            return ["| **复盘校准** | 未启用 | 未读取复盘规则 |"]
        adjustments = calibration.get("adjustments") or []
        warnings = calibration.get("warnings") or []
        if not adjustments:
            detail = "；".join(warnings[:2]) or "未命中特定复盘规则"
            return [f"| **复盘校准** | 未命中特定规则 | {detail} |"]
        rows = []
        for item in adjustments[:4]:
            rows.append(
                f"| **复盘校准** | {item.get('target', '-')} {item.get('weight_delta', '-')} | "
                f"{item.get('note', '-')} |"
            )
        if warnings:
            rows.append(f"| **复盘校准提示** | 注意 | {'；'.join(warnings[:3])} |")
        return rows

    @staticmethod
    def _consistency_rows(consistency: Dict[str, Any]) -> List[str]:
        if not consistency:
            return ["| **一致性检查** | 未启用 | 未生成层间一致性检查 |"]
        warnings = consistency.get("warnings") or []
        notes = consistency.get("notes") or []
        status = consistency.get("status", "-")
        if warnings:
            return [
                f"| **一致性检查** | {status} | {'；'.join(warnings[:4])} |",
                f"| **一致性备注** | - | {'；'.join(notes[:3]) or '-'} |",
            ]
        return [f"| **一致性检查** | {status} | {'；'.join(notes[:4]) or '各模型层未发现明显冲突'} |"]

    @staticmethod
    def _decision_evidence_rows(decision: Dict[str, Any]) -> List[str]:
        evidence = decision.get("evidence") or []
        if not evidence:
            return ["| - | - | - | 未生成证据评分 |"]
        rows = []
        for item in evidence[:8]:
            rows.append(
                f"| **{item.get('factor', '-')}** | {item.get('weight', '-')} | "
                f"{item.get('direction', '-')} | {item.get('note', '-')} |"
            )
        return rows

    @staticmethod
    def _split_desc(stats: Any) -> str:
        return StandardReportRenderer._record(stats) if stats else "未获取，使用总近况"

    @staticmethod
    def _prob_conf(prob: float) -> str:
        if prob >= 0.6:
            return "高"
        if prob >= 0.45:
            return "中"
        return "低"

    @staticmethod
    def _over_note(prob: float) -> str:
        if prob >= 0.58:
            return "倾向较明显"
        if prob >= 0.52:
            return "轻微倾向"
        return "倾向不强"

    @staticmethod
    def _goal_range(poisson: Any) -> str:
        expected = poisson.expected_home_goals + poisson.expected_away_goals
        if expected >= 3.0:
            return "3球+"
        if expected >= 2.2:
            return "2-3球"
        return "0-2球"

    @staticmethod
    def _score_rows(poisson: Any, scoreline_signal: Optional[Dict[str, Any]] = None) -> List[str]:
        rows = []
        fused_scores = (scoreline_signal or {}).get("top_scores") or []
        if fused_scores:
            for item in fused_scores[:5]:
                rows.append(
                    f"| **{item.get('score', '-')}** | **{StandardReportRenderer._pct(item.get('final_probability'))}** | "
                    f"{StandardReportRenderer._pct(item.get('poisson_probability'))} | "
                    f"{StandardReportRenderer._pct(item.get('market_probability'))} | "
                    f"{item.get('rank', '-')} | {item.get('risk_tier', '-')} | "
                    f"{item.get('outcome', '-')} / 总球{item.get('total_goals', '-')} |"
                )
            return rows
        top = sorted(poisson.score_probs.items(), key=lambda item: item[1], reverse=True)[:5]
        for idx, ((home_goals, away_goals), prob) in enumerate(top, 1):
            rows.append(f"| **{home_goals}-{away_goals}** | **{prob:.1%}** | {prob:.1%} | - | {idx} | - | 泊松比分分布 |")
        return rows

    @staticmethod
    def _qimen_symbol_row(label: str, symbol: Dict[str, Any]) -> str:
        return f"| **{label}** | {symbol.get('door', '-')} | {symbol.get('star', '-')} | {symbol.get('god', '-')} | {symbol.get('meaning', '-')} |"

    @staticmethod
    def _kelly_rows(kelly_results: List[Any]) -> List[str]:
        if not kelly_results:
            return ["| - | - | - | - | - | - | 未获取真实市场数字或无可计算方向 |"]
        rows = []
        for result in kelly_results[:5]:
            rows.append(
                f"| **{result.bet_type}** | {result.odds:.2f} | {result.probability:.1%} | "
                f"{result.expected_value:+.1%} | {result.kelly_fraction:.2%} | {result.kelly_amount:.0f} | {result.reason} |"
            )
        return rows

    @staticmethod
    def _strategy_lines(strategy: Any) -> List[str]:
        if not strategy:
            return ["暂无风险分层方案。"]
        lines = [
            f"**总风险权重**：{strategy.total_stake:.0f}",
            f"**预期ROI**：{strategy.expected_roi:+.1%}",
            f"**风险等级**：{strategy.risk_level}",
            "",
            "**推荐方向**：",
        ]
        if strategy.recommended_bets:
            for bet in strategy.recommended_bets:
                lines.append(f"- {bet.get('bet_type', 'Unknown')}，表格数值{bet.get('odds', 0):.2f}，风险权重{bet.get('stake', 0):.0f}")
        else:
            lines.append("- 当前参数下没有符合条件的核心方向。")
        return lines

    @staticmethod
    def _prediction_summary_rows(home: str, away: str, poisson: Any, qimen: Dict[str, Any]) -> List[str]:
        outcomes = [
            (f"{home}胜", poisson.home_win_prob),
            ("平局", poisson.draw_prob),
            (f"{away}胜", poisson.away_win_prob),
        ]
        outcomes.sort(key=lambda item: item[1], reverse=True)
        top_score, top_prob = max(poisson.score_probs.items(), key=lambda item: item[1])
        return [
            f"| **最可能赛果** | {outcomes[0][0]} | {outcomes[0][1]:.1%} | {StandardReportRenderer._prob_conf(outcomes[0][1])} |",
            f"| **次可能赛果** | {outcomes[1][0]} | {outcomes[1][1]:.1%} | {StandardReportRenderer._prob_conf(outcomes[1][1])} |",
            f"| **最可能比分** | {top_score[0]}-{top_score[1]} | {top_prob:.1%} | 低 |",
            f"| **进球数方向** | {StandardReportRenderer._goal_range(poisson)} | - | 参考 |",
            f"| **奇门辅助方向** | {qimen.get('qimen_result_prediction', '-')} / {qimen.get('predicted_score', '-')} | - | {qimen.get('confidence', '-')} |",
        ]

    @staticmethod
    def _core_bet(kelly_results: List[Any]) -> str:
        positives = [item for item in kelly_results if item.expected_value > 0]
        return positives[0].bet_type if positives else "无明确正EV核心方向"

    @staticmethod
    def _longshot_bet(kelly_results: List[Any]) -> str:
        candidates = [item for item in kelly_results if item.expected_value > 0 and item.odds >= 2.5]
        return candidates[0].bet_type if candidates else "无合适博取选项"

    @staticmethod
    def _avoid_note(kelly_results: List[Any]) -> str:
        negatives = [item.bet_type for item in kelly_results if item.expected_value <= 0]
        return "、".join(negatives[:3]) if negatives else "避免过度组合和临场大幅变盘场次"

    @staticmethod
    def _tier_items(rows: List[Dict[str, Any]], tier: int) -> List[str]:
        items = [row for row in rows if row.get("tier") == tier]
        return [f"{item.get('match')}: {item.get('recommendation')}" for item in items] or ["-"]


__all__ = ["StandardReportRenderer"]
