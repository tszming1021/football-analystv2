#!/usr/bin/env python3
"""
大模型分析层 - LLM Analysis Layer
负责整合所有数据，调用大模型进行深度分析
"""

import os
import sys
import json
import re
import shlex
import shutil
import subprocess
import tempfile
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.math_models import PoissonProbabilities, KellyResult
from core.data_collector import CompleteDataReport


@dataclass
class LLMDeepAnalysis:
    """大模型深度分析结果"""
    # 比赛形势分析
    match_situation: str
    home_team_strength_analysis: str
    away_team_strength_analysis: str

    # 历史交锋分析
    h2h_analysis: str

    # 近期状态分析
    recent_form_analysis: str

    # 伤病停赛影响
    injury_impact_analysis: str

    # 战术风格对比
    tactical_analysis: str

    # 关键球员对比
    key_players_analysis: str

    # 综合分析结论
    overall_assessment: str

    # 最可能的比分预测
    predicted_score: str
    predicted_score_probability: float

    # 对数学模型结果的评论
    model_result_commentary: str

    # 风险提示
    risk_factors: List[str]

    # 最终建议
    final_recommendation: str

    # 执行状态
    provider: str = "none"
    model: str = ""
    status: str = "not_run"
    model_agreement: str = "unknown"
    confidence_adjustment: str = "none"
    web_evidence_assessment: str = ""
    web_sources: List[str] = None
    verified_intelligence: Dict[str, Any] = None
    raw_response_excerpt: str = ""
    agent_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComprehensiveAnalysisReport:
    """综合分析报告 - 整合数学模型和大模型分析"""

    # 基本信息
    match_info: Dict[str, str]
    analysis_timestamp: str
    data_sources: List[str]
    data_quality_score: float

    # 数学建模结果
    poisson_probabilities: Optional[Dict] = None
    kelly_analysis: Optional[List[Dict]] = None
    expected_value_analysis: Optional[Dict] = None

    # 大模型深度分析
    llm_deep_analysis: Optional[LLMDeepAnalysis] = None

    # 最终综合建议
    final_betting_strategy: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'match_info': self.match_info,
            'analysis_timestamp': self.analysis_timestamp,
            'data_sources': self.data_sources,
            'data_quality_score': self.data_quality_score,
            'poisson_probabilities': self.poisson_probabilities,
            'kelly_analysis': self.kelly_analysis,
            'expected_value_analysis': self.expected_value_analysis,
            'llm_deep_analysis': asdict(self.llm_deep_analysis) if self.llm_deep_analysis else None,
            'final_betting_strategy': self.final_betting_strategy,
        }


class LLMAnalyzer:
    """大模型分析器"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "").strip().lower()
        auto_review = os.getenv("LLM_AUTO_REVIEW", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if auto_review and shutil.which("codex") and self.provider in {"", "agent_prompt", "prompt", "none"}:
            self.provider = "codex_cli"
        if not self.provider:
            self.provider = (
                "openai" if self.openai_key
                else ("codex_cli" if shutil.which("codex") else ("anthropic" if self.anthropic_key else "none"))
            )
        if self.provider == "anthropic":
            self.api_key = self.anthropic_key
        elif self.provider == "openai":
            self.api_key = self.openai_key
        else:
            self.api_key = None
        configured_model = model or os.getenv("LLM_MODEL")
        if configured_model and configured_model.startswith("optional_"):
            configured_model = None
        self.model = configured_model or (
            "claude-sonnet-4-6" if self.provider == "anthropic"
            else ("gpt-5.5" if self.provider in {"codex", "codex_cli", "agent_cli"} else "gpt-5.4")
        )

    def analyze(
        self,
        data_report: CompleteDataReport,
        poisson_result: Optional[PoissonProbabilities] = None,
        kelly_results: Optional[List[KellyResult]] = None,
        historical_data: Optional[Dict] = None
    ) -> ComprehensiveAnalysisReport:
        """
        执行完整的大模型分析

        整合:
        1. 数据收集层的数据报告
        2. 数学建模层的泊松/凯利结果
        3. 本地历史数据库的相关数据
        """

        report = ComprehensiveAnalysisReport(
            match_info={
                'home_team': data_report.parsed_match.home_team_en,
                'away_team': data_report.parsed_match.away_team_en,
                'home_team_zh': data_report.parsed_match.home_team_raw,
                'away_team_zh': data_report.parsed_match.away_team_raw,
                'input_str': data_report.parsed_match.input_str,
            },
            analysis_timestamp=datetime.now().isoformat(),
            data_sources=data_report.data_sources_used,
            data_quality_score=data_report.data_completeness_score,
        )

        # 准备数学模型结果
        if poisson_result:
            report.poisson_probabilities = {
                'home_win_prob': poisson_result.home_win_prob,
                'draw_prob': poisson_result.draw_prob,
                'away_win_prob': poisson_result.away_win_prob,
                'expected_home_goals': poisson_result.expected_home_goals,
                'expected_away_goals': poisson_result.expected_away_goals,
                'over_25_prob': poisson_result.over_25_prob,
                'under_25_prob': poisson_result.under_25_prob,
                'btts_yes_prob': poisson_result.btts_yes_prob,
                'btts_no_prob': poisson_result.btts_no_prob,
                'most_likely_score': poisson_result.most_likely_score,
            }

        if kelly_results:
            report.kelly_analysis = []
            for kr in kelly_results:
                report.kelly_analysis.append({
                    'bet_type': kr.bet_type,
                    'odds': kr.odds,
                    'probability': kr.probability,
                    'kelly_fraction': kr.kelly_fraction,
                    'kelly_amount': kr.kelly_amount,
                    'expected_value': kr.expected_value,
                    'recommended': kr.recommended,
                    'reason': kr.reason,
                })

        # 调用大模型进行深度分析
        llm_analysis = self._call_llm_for_analysis(
            data_report=data_report,
            poisson_result=poisson_result,
            kelly_results=kelly_results,
            historical_data=historical_data
        )

        report.llm_deep_analysis = llm_analysis

        return report

    def _call_llm_for_analysis(
        self,
        data_report: CompleteDataReport,
        poisson_result: Optional[PoissonProbabilities],
        kelly_results: Optional[List[KellyResult]],
        historical_data: Optional[Dict]
    ) -> LLMDeepAnalysis:
        """
        使用当前Claude大模型进行深度分析

        直接调用当前AI实例的能力进行分析，不使用外部API
        """

        home = data_report.parsed_match.home_team_en
        away = data_report.parsed_match.away_team_en

        # 构建完整的分析提示
        analysis_prompt = f"""
你是一位资深的足球比赛分析专家。请基于以下数据对 {home} vs {away} 的比赛进行深度分析：

你正在执行模型完成后的独立二次复核。必须使用联网搜索核验最新赛前信息，包括伤停、预计首发、主帅发布会、比赛动机和场地；不得把赛后信息用于赛前预测。

【数据收集报告】
- 数据来源: {', '.join(data_report.data_sources_used)}
- 数据完整度: {data_report.data_completeness_score:.0f}%
- API可用: {data_report.api_available}
- 联网搜索: {data_report.web_search_available}
"""

        if data_report.match_intelligence:
            intelligence = data_report.match_intelligence
            analysis_prompt += "\n【赛事情报】\n"
            analysis_prompt += f"- 情报完整度: {intelligence.get('intelligence_score', 0):.0f}%\n"
            sources = intelligence.get('data_sources') or []
            if sources:
                analysis_prompt += f"- 情报来源: {', '.join(sources)}\n"
            for side in ["home", "away"]:
                info = intelligence.get(side) or {}
                tags = info.get("tactical_tags") or []
                pieces = []
                if info.get("league_rank"):
                    pieces.append(f"排名{info.get('league_rank')}")
                if info.get("rest_days") is not None:
                    pieces.append(f"休息{info.get('rest_days')}天")
                if info.get("injuries"):
                    pieces.append(f"伤停{len(info.get('injuries'))}人")
                if tags:
                    pieces.append("标签:" + "、".join(tags))
                if pieces:
                    analysis_prompt += f"- {info.get('team_name', side)}: {'；'.join(pieces)}\n"
            for note in (intelligence.get("tactical_notes") or [])[:6]:
                analysis_prompt += f"- {note}\n"

        if data_report.weather_context:
            weather = data_report.weather_context
            analysis_prompt += "\n【天气上下文】\n"
            analysis_prompt += (
                f"- 地点: {weather.get('location')}, 温度: {weather.get('temperature_c')}°C, "
                f"降雨: {weather.get('precipitation_mm')}mm, 风速: {weather.get('wind_speed_kmh')}km/h\n"
            )
            if weather.get("risk_note"):
                analysis_prompt += f"- 天气影响: {weather.get('risk_note')}\n"

        if data_report.odds_history:
            odds_history = data_report.odds_history
            analysis_prompt += "\n【赔率历史/收盘线】\n"
            analysis_prompt += f"- 本场已记录赔率快照: {odds_history.get('snapshot_count', 0)} 条\n"
            for market, payload in (odds_history.get("markets") or {}).items():
                latest = payload.get("latest") or {}
                analysis_prompt += (
                    f"- {market}: 最新 {latest.get('home_win')}/"
                    f"{latest.get('draw')}/{latest.get('away_win')}\n"
                )

        qimen = getattr(data_report, "qimen_analysis", None)
        if qimen:
            analysis_prompt += "\n【奇门辅助分析】\n"
            analysis_prompt += (
                f"- 辅助倾向: {qimen.get('qimen_bias')}, "
                f"波动: {qimen.get('volatility')}, 信心: {qimen.get('confidence')}\n"
            )
            if qimen.get("image_summary"):
                analysis_prompt += f"- 局像总断: {qimen.get('image_summary')}\n"
            if qimen.get("qimen_result_prediction") or qimen.get("predicted_score"):
                analysis_prompt += (
                    f"- 奇门胜平负: {qimen.get('qimen_result_prediction')}, "
                    f"奇门比分: {qimen.get('predicted_score')}\n"
                )
            for note in (qimen.get("notes") or [])[:4]:
                analysis_prompt += f"- {note}\n"
            for flag in (qimen.get("risk_flags") or [])[:3]:
                analysis_prompt += f"- 风险提示: {flag}\n"

        analysis_prompt += f"""
【泊松分布模型结果】
- 主队预期进球: {poisson_result.expected_home_goals:.2f}
- 客队预期进球: {poisson_result.expected_away_goals:.2f}
- 主胜概率: {poisson_result.home_win_prob:.1%}
- 平局概率: {poisson_result.draw_prob:.1%}
- 客胜概率: {poisson_result.away_win_prob:.1%}
- 最可能比分: {poisson_result.most_likely_score}

【凯利公式分析】
"""

        if kelly_results:
            for kr in kelly_results[:5]:
                status = "✅推荐" if kr.recommended else "❌不推荐"
                analysis_prompt += f"\n- {kr.bet_type}: 赔率{kr.odds:.2f}, 凯利{kr.kelly_fraction:.2%}, EV{kr.expected_value:+.1%}, {status}"

        if historical_data:
            analysis_prompt += "\n\n【已生成的模型与决策结果】\n"
            for key, label in [
                ("market_signal", "市场信号"),
                ("match_context", "比赛语境"),
                ("handicap_signal", "让球穿盘模型"),
                ("goals_signal", "大小球模型"),
                ("decision", "集成决策"),
                ("odds_movement", "赔率变化"),
            ]:
                payload = historical_data.get(key)
                if payload:
                    analysis_prompt += f"- {label}: {json.dumps(payload, ensure_ascii=False, default=str)[:1800]}\n"

        analysis_prompt += f"""

【球队新闻与动态】
"""

        if data_report.team_news:
            for team, news in data_report.team_news.items():
                analysis_prompt += f"\n{team}: {', '.join(news)}"

        if data_report.injury_updates:
            analysis_prompt += "\n\n【伤病情况】\n"
            for team, injuries in data_report.injury_updates.items():
                analysis_prompt += f"{team}: {', '.join(injuries)}\n"

        if data_report.web_search_results:
            analysis_prompt += "\n\n【联网搜索证据】\n"
            for item in data_report.web_search_results[:10]:
                analysis_prompt += (
                    f"- 来源:{item.source} 标题:{item.title} URL:{item.url} "
                    f"摘要:{item.snippet}\n"
                )

        if data_report.jingcai_match:
            jingcai = data_report.jingcai_match
            analysis_prompt += "\n\n【500彩票网竞彩/赔率/情报】\n"
            analysis_prompt += (
                f"- 场次:{jingcai.get('match_num')} 赛事:{jingcai.get('league')} "
                f"时间:{jingcai.get('match_date')} {jingcai.get('match_time')} 让球:{jingcai.get('handicap')}\n"
            )
            analysis_prompt += f"- 欧赔均值:{jingcai.get('average_europe_odds')}\n"
            analysis_prompt += f"- 亚盘均值:{jingcai.get('asian_average')}\n"
            analysis_prompt += f"- FIFA排名:{jingcai.get('fifa_rankings')}\n"
            analysis_prompt += f"- 交锋:{jingcai.get('h2h_summary')} / {(jingcai.get('h2h_records') or [])[:3]}\n"
            analysis_prompt += f"- 预计阵容:{jingcai.get('predicted_lineups')}\n"

        if data_report.data_warnings:
            analysis_prompt += "\n\n【数据风险与缺口】\n"
            for warning in data_report.data_warnings[:12]:
                analysis_prompt += f"- {warning}\n"

        analysis_prompt += f"""

请基于以上所有数据，进行“大模型复核分析”。要求：
- 必须主动联网搜索这场比赛的最新赛前信息，重点核验伤停、预计首发、轮换、主帅表态、比赛动机与场地。
- 联网信息必须附上实际访问过的来源 URL；无法验证的消息不得作为结论。
- 把确实核验成功的伤停、阵容和休息天数写入 verified_intelligence；没有可靠URL时保持 unknown/null。
- 必须判断比赛动机类型：普通友谊赛、世界杯/大赛前最后热身、练兵考察、长途旅行疲劳、年轻化名单、主力缺席。
- 不能编造未给出的伤停、首发、赔率或新闻。
- 必须指出联网搜索证据是否有用、是否偏泛化/赛后污染。
- 不能直接覆盖数学模型，只能给出同意、反对或降低信心的复核意见。
- 必须结合上方已经生成的泊松、凯利、让球、大小球、市场信号、比赛语境、奇门辅助和风控结论。
- 如果发现赛后数据、搜索结果泛化、API权限缺失、赔率源缺失等问题，必须降低信心或给出避险建议。
- 输出必须是 JSON，不要使用 Markdown，不要输出 JSON 之外的文字。

JSON schema:
{{
  "match_situation": "比赛形势分析",
  "home_team_strength_analysis": "主队实力分析",
  "away_team_strength_analysis": "客队实力分析",
  "h2h_analysis": "交锋分析",
  "recent_form_analysis": "近期状态分析",
  "injury_impact_analysis": "伤停/首发可信度分析",
  "tactical_analysis": "战术与风格分析",
  "key_players_analysis": "关键球员与阵容分析",
  "overall_assessment": "综合评估",
  "predicted_score": "预测比分",
  "predicted_score_probability": 0.0,
  "model_result_commentary": "对泊松/凯利/让球/大小球模型的评论",
  "risk_factors": ["风险1", "风险2"],
  "final_recommendation": "最终复核建议",
  "model_agreement": "agree|disagree|mixed|reduce_confidence",
  "confidence_adjustment": "raise|none|reduce|avoid",
  "web_evidence_assessment": "联网搜索证据评价",
  "web_sources": ["实际访问过的来源URL"],
  "verified_intelligence": {{
    "home": {{
      "injury_status": "confirmed_injuries|confirmed_clear|reported_injuries|reported_clear|unknown",
      "absences": [],
      "lineup_status": "official|predicted|unknown",
      "rest_days": null
    }},
    "away": {{
      "injury_status": "confirmed_injuries|confirmed_clear|reported_injuries|reported_clear|unknown",
      "absences": [],
      "lineup_status": "official|predicted|unknown",
      "rest_days": null
    }},
    "venue_confirmed": false,
    "weather_location": "",
    "match_dynamics": {{
      "friendly_subtype": "ordinary_friendly|world_cup_final_warmup|rotation_friendly|youth_evaluation|unknown",
      "home_motivation_score": 0.0,
      "away_vulnerability_score": 0.0,
      "travel_fatigue_side": "home|away|both|none|unknown",
      "young_squad_side": "home|away|both|none|unknown",
      "high_scoring_risk": 0.0,
      "favorite_cover_trigger": false,
      "note": "战意、旅行、年轻化、减员和大比分风险的简短依据"
    }},
    "sources": ["支持上述结构化情报的实际URL"]
  }}
}}
"""

        print(f"\n🤖 正在进行大模型深度分析...")
        print(f"   分析对象: {home} vs {away}")
        print(f"   数据完整度: {data_report.data_completeness_score:.0f}%")
        print(f"   LLM provider: {self.provider}, model: {self.model}")

        if self.provider in {"agent_prompt", "prompt"}:
            return self._agent_prompt_analysis(home, away, analysis_prompt)

        if self.provider in {"codex", "codex_cli", "agent_cli", "openclaw", "openclaw_cli"}:
            try:
                raw_text = self._request_agent_cli(analysis_prompt)
                parsed = self._parse_llm_response(raw_text)
                parsed.provider = self.provider
                parsed.model = self.model
                return parsed
            except Exception as exc:
                return self._unavailable_analysis(home, away, f"Agent CLI 调用失败: {exc}")

        if self.provider == "none" or not self.api_key:
            return self._unavailable_analysis(
                home, away,
                "未检测到 ANTHROPIC_API_KEY 或 OPENAI_API_KEY，已跳过大模型复核。"
            )

        try:
            raw_text = self._request_llm(analysis_prompt)
            return self._parse_llm_response(raw_text)
        except Exception as exc:
            return self._unavailable_analysis(home, away, f"大模型调用失败: {exc}")

    def _request_llm(self, prompt: str) -> str:
        if self.provider == "anthropic":
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1800")),
                    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=int(os.getenv("LLM_TIMEOUT", "45")),
            )
            response.raise_for_status()
            payload = response.json()
            return "\n".join(
                block.get("text", "")
                for block in payload.get("content", [])
                if block.get("type") == "text"
            ).strip()

        if self.provider == "openai":
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": prompt,
                    "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "1800")),
                    "tools": [{"type": "web_search"}],
                },
                timeout=int(os.getenv("LLM_TIMEOUT", "45")),
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("output_text"):
                return payload["output_text"].strip()
            texts = []
            for item in payload.get("output", []) or []:
                for content in item.get("content", []) or []:
                    if content.get("type") in ("output_text", "text"):
                        texts.append(content.get("text", ""))
            return "\n".join(texts).strip()

        raise ValueError(f"未知 LLM_PROVIDER: {self.provider}")

    def _request_agent_cli(self, prompt: str) -> str:
        command = self._agent_cli_command()
        timeout = int(os.getenv("AGENT_CLI_TIMEOUT", os.getenv("LLM_TIMEOUT", "120")))
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".txt") as output_file:
            command = self._with_agent_output_file(command, output_file.name)
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=os.getcwd(),
                check=False,
            )
            output_file.seek(0)
            last_message = output_file.read().strip()
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(stderr[:1200] or f"Agent CLI 返回码 {completed.returncode}")
        return last_message or (completed.stdout or "").strip()

    def _agent_cli_command(self) -> List[str]:
        custom = os.getenv("AGENT_CLI_COMMAND")
        if custom:
            return shlex.split(custom)
        if self.provider in {"openclaw", "openclaw_cli"}:
            return ["openclaw", "exec", "-"]
        return [
            "codex",
            "--search",
            "--model",
            self.model,
            "exec",
            "--ephemeral",
            "--sandbox",
            os.getenv("AGENT_CLI_SANDBOX", "read-only"),
            "--skip-git-repo-check",
            "-",
        ]

    @staticmethod
    def _with_agent_output_file(command: List[str], output_path: str) -> List[str]:
        if command and command[0] == "codex" and "exec" in command:
            return command[:-1] + ["-o", output_path, command[-1]] if command[-1] == "-" else command + ["-o", output_path]
        return command

    def _parse_llm_response(self, raw_text: str) -> LLMDeepAnalysis:
        payload = self._extract_json(raw_text)
        if not payload:
            return LLMDeepAnalysis(
                match_situation="大模型已返回文本，但不是合法 JSON。",
                home_team_strength_analysis="-",
                away_team_strength_analysis="-",
                h2h_analysis="-",
                recent_form_analysis="-",
                injury_impact_analysis="-",
                tactical_analysis="-",
                key_players_analysis="-",
                overall_assessment=raw_text[:800],
                predicted_score="-",
                predicted_score_probability=0.0,
                model_result_commentary="无法结构化解析大模型结果，请查看 raw_response_excerpt。",
                risk_factors=["大模型输出格式异常"],
                final_recommendation="-",
                provider=self.provider,
                model=self.model,
                status="parse_failed",
                raw_response_excerpt=raw_text[:1000],
            )
        return LLMDeepAnalysis(
            match_situation=str(payload.get("match_situation") or "-"),
            home_team_strength_analysis=str(payload.get("home_team_strength_analysis") or "-"),
            away_team_strength_analysis=str(payload.get("away_team_strength_analysis") or "-"),
            h2h_analysis=str(payload.get("h2h_analysis") or "-"),
            recent_form_analysis=str(payload.get("recent_form_analysis") or "-"),
            injury_impact_analysis=str(payload.get("injury_impact_analysis") or "-"),
            tactical_analysis=str(payload.get("tactical_analysis") or "-"),
            key_players_analysis=str(payload.get("key_players_analysis") or "-"),
            overall_assessment=str(payload.get("overall_assessment") or "-"),
            predicted_score=str(payload.get("predicted_score") or "-"),
            predicted_score_probability=self._safe_float(payload.get("predicted_score_probability")) or 0.0,
            model_result_commentary=str(payload.get("model_result_commentary") or "-"),
            risk_factors=[str(item) for item in (payload.get("risk_factors") or [])][:8],
            final_recommendation=str(payload.get("final_recommendation") or "-"),
            provider=self.provider,
            model=self.model,
            status="completed",
            model_agreement=str(payload.get("model_agreement") or "unknown"),
            confidence_adjustment=str(payload.get("confidence_adjustment") or "none"),
            web_evidence_assessment=str(payload.get("web_evidence_assessment") or "-"),
            web_sources=[str(item) for item in (payload.get("web_sources") or [])][:10],
            verified_intelligence=payload.get("verified_intelligence") if isinstance(payload.get("verified_intelligence"), dict) else {},
            raw_response_excerpt=raw_text[:1000],
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _unavailable_analysis(self, home: str, away: str, reason: str) -> LLMDeepAnalysis:
        return LLMDeepAnalysis(
            match_situation=reason,
            home_team_strength_analysis="-",
            away_team_strength_analysis="-",
            h2h_analysis="-",
            recent_form_analysis="-",
            injury_impact_analysis="-",
            tactical_analysis="-",
            key_players_analysis="-",
            overall_assessment=f"{home} vs {away} 未执行大模型复核。",
            predicted_score="-",
            predicted_score_probability=0.0,
            model_result_commentary=reason,
            risk_factors=[reason],
            final_recommendation="沿用数学模型和风控引擎结论；大模型复核未参与。",
            provider=self.provider,
            model=self.model,
            status="unavailable",
            model_agreement="unknown",
            confidence_adjustment="none",
            web_evidence_assessment=reason,
            web_sources=[],
            verified_intelligence={},
        )

    def _agent_prompt_analysis(self, home: str, away: str, prompt: str) -> LLMDeepAnalysis:
        return LLMDeepAnalysis(
            match_situation="已生成外部 Agent 二次复核 Prompt，项目未直接调用大模型。",
            home_team_strength_analysis="-",
            away_team_strength_analysis="-",
            h2h_analysis="-",
            recent_form_analysis="-",
            injury_impact_analysis="待 Codex/OpenClaw 等外部 Agent 结合联网能力复核。",
            tactical_analysis="待外部 Agent 基于下方 Prompt 复核。",
            key_players_analysis="待外部 Agent 复核。",
            overall_assessment=f"{home} vs {away} 已完成基础模型分析，等待外部 Agent 二次判断。",
            predicted_score="-",
            predicted_score_probability=0.0,
            model_result_commentary="agent_prompt 模式不会自动改写模型结论；请把下方 Prompt 交给 Codex/OpenClaw 生成最终复核意见。",
            risk_factors=[
                "agent_prompt 模式未直接调用大模型，最终 AI 复核需要外部 Agent 执行",
                "外部 Agent 应重点核验联网搜索结果是否最新、是否存在赛后数据污染",
            ],
            final_recommendation="把报告中的 Agent Prompt 交给 Codex/OpenClaw 后，再决定是否采纳或降低基础模型结论。",
            provider=self.provider,
            model=self.model,
            status="agent_prompt",
            model_agreement="pending",
            confidence_adjustment="pending",
            web_evidence_assessment="已把联网搜索证据与数据缺口写入 Agent Prompt，待外部 Agent 复核。",
            web_sources=[],
            verified_intelligence={},
            raw_response_excerpt=prompt[:1000],
            agent_prompt=prompt,
        )
