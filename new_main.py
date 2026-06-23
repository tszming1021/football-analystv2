#!/usr/bin/env python3
"""
足球大数据精算分析智能体 v5.0 - 新工作流程主入口
基于重构的5层架构：输入层、数据获取层、数学建模层、大模型分析层、风险管理层
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.workflow_new import InputParser, ParsedMatch
from core.workflow_coordinator import WorkflowCoordinator, FinalOutput
from core.risk_manager import UserRiskParameters
from core.report_renderer import StandardReportRenderer
from core.parlay_risk import ParlayRiskController


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              ⚽️ 足球大数据精算分析智能体 v5.0 ⚽️                            ║
║                                                                              ║
║         Football Big Data Actuarial Analysis Agent                           ║
║                                                                              ║
║     新架构: 数据获取 → 数学建模 → 大模型分析 → 风险管理                      ║
║     新特性: API + 联网搜索双源数据 / 禁止模拟数据                           ║
║             本地数据库 + 大模型深度分析                                        ║
║             用户自定义风险管理参数                                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_workflow_diagram():
    """打印工作流程图"""
    diagram = """
📊 新工作流程架构图:

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 输入层 + 实体识别层 (Input & Entity Recognition)                       │
│  ─────────────────────────────────────────────────────────────────────────────  │
│  • 用户输入: "巴薩 vs 馬競" / "Barcelona vs Atletico Madrid"                    │
│  • 解析分隔符: vs / VS / - / 对                                                  │
│  • 中文→英文转换: 150+ 球队名映射                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 数据获取层 (Data Collection) - ⚠️ 禁止模拟数据                          │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐    │
│  │  方法A: API-Football 数据获取  │ OR │  方法B: 联网搜索数据获取        │    │
│  │  ─────────────────────────────  │    │  ─────────────────────────────  │    │
│  │  • 球队信息 API                │    │  • Google Search 搜索结果      │    │
│  │  • 赛程信息 API                │    │  • 球队新闻和动态              │    │
│  │  • 实时市场数字 API                │    │  • 伤病停赛更新                │    │
│  │  • 统计数据 API                │    │  • 专家预测和评论              │    │
│  │  • 历史交锋 API                │    │  • 天气和场地条件              │    │
│  └─────────────────────────────────┘    └─────────────────────────────────┘    │
│                                                                                 │
│  ⚠️ 如果 API 不可用且用户未提供 API Key:                                          │
│      → 只使用联网搜索获取数据                                                     │
│      → 不允许使用模拟数据                                                          │
│      → 在报告中说明数据来源限制                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 3: 比赛分析层 (Match Analysis)                                              │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐    │
│  │  模块A: 数学建模模块        │ →  │  模块B: 大模型深度分析模块          │    │
│  │  ─────────────────────────  │    │  ─────────────────────────────────  │    │
│  │  • 泊松分布模型             │    │  • 输入数据整合:                  │    │
│  │    - 计算比分概率           │    │    - 联赛数据库历史数据            │    │
│  │    - P(X=k) 公式            │    │    - 数据获取层最新数据            │    │
│  │                             │    │    - 数学建模模块分析结果          │    │
│  │  • 凯利公式                 │    │                                 │    │
│  │    - f* = (bp - q) / b     │    │  • Claude/OpenAI API 调用         │    │
│  │    - 资金分配建议           │    │                                 │    │
│  │                             │    │  • 深度分析内容:                 │    │
│  │  • EV 期望值分析            │    │    - 比赛形势分析                │    │
│  │    - EV = p*odds - q        │    │    - 主客队实力对比              │    │
│  │    - 识别正期望值           │    │    - 历史交锋分析                │    │
│  │                             │    │    - 近期状态分析                │    │
│  │                             │    │    - 伤病停赛影响                │    │
│  │                             │    │    - 战术风格对比                │    │
│  │                             │    │    - 关键球员对比                │    │
│  │                             │    │    - 综合结论                    │    │
│  │                             │    │    - 比分预测                    │    │
│  │                             │    │    - 模型结果评论                │    │
│  │                             │    │    - 风险因素                    │    │
│  │                             │    │    - 最终建议                    │    │
│  │                             │    │                                 │    │
│  │                             │    │  • 生成深度分析报告               │    │
│  └─────────────────────────────┘    └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 4: 风险管理层 (Risk Management)                                          │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  • 用户参数输入:                                                                │
│    - 总资金                                                                    │
│    - 单注最大核心方向比例 (%%)                                                       │
│    - 市场数字上下限                                                                │
│    - 凯利分数选择 (1/4, 1/2, 全)                                                │
│    - 是否组合过关                                                              │
│    - 核心方向倍数 (足彩2元一注，5倍=10元)                                             │
│                                                                                 │
│  • 核心方向策略生成:                                                                │
│    - 根据比赛分析层输出                                                          │
│    - 应用用户风险参数                                                            │
│    - 计算最优核心方向组合                                                            │
│    - 生成核心方向策略报告                                                            │
│                                                                                 │
│  • 输出层 (原有输出):                                                             │
│    - 模型概率: 主胜/平局/客胜                                                     │
│    - EV 分析: 各选项期望值                                                        │
│    - 凯利建议: 核心方向比例和金额                                                    │
│    - 最佳选项标记                                                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
"""
    print(diagram)


def main():
    """主入口"""
    print_banner()

    parser = argparse.ArgumentParser(
        description='足球大数据精算分析智能体 v5.0 - 新工作流程',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 交互式分析
  python new_main.py --interactive

  # 快速分析 (预设参数)
  python new_main.py --match "巴薩 vs 馬競" --api-key YOUR_API_KEY

  # 显示工作流程图
  python new_main.py --show-workflow

环境变量:
  API_FOOTBALL_KEY    API-Football API Key (可选)
  ANTHROPIC_API_KEY   Anthropic API Key (用于大模型分析，可选)
        """
    )

    parser.add_argument('--match', '-m',
                        help='比赛输入，格式: "主隊 vs 客隊"')
    parser.add_argument('--matches',
                        help='多场比赛，逗号分隔，例如 "德国 vs 芬兰,美国 vs 塞内加尔"')
    parser.add_argument('--api-key', '-k',
                        help='API-Football API Key')
    parser.add_argument('--interactive', '-i',
                        action='store_true',
                        help='交互式模式')
    parser.add_argument('--show-workflow', '-w',
                        action='store_true',
                        help='显示工作流程图')
    parser.add_argument('--version', '-v',
                        action='version',
                        version='%(prog)s 5.0.0')

    args = parser.parse_args()

    # 显示工作流程图
    if args.show_workflow:
        print_workflow_diagram()
        return 0

    if args.matches:
        return run_multi_match(args)

    # 交互式模式
    if args.interactive or not args.match:
        print("\n🎮 交互式分析模式")
        print("-" * 60)

        # 获取比赛输入
        while True:
            match_input = input("\n请输入比赛 (格式: 主隊 vs 客隊): ").strip()
            if match_input:
                break
            print("❌ 比赛信息不能为空")

        try:
            parsed_match = InputParser.parse_match_input(match_input)
            print(f"✅ 解析成功: {parsed_match.home_team_raw} vs {parsed_match.away_team_raw}")
            print(f"   英文: {parsed_match.home_team_en} vs {parsed_match.away_team_en}")
        except ValueError as e:
            print(f"❌ 解析失败: {e}")
            return 1

        # 获取API Key (可选)
        api_key = args.api_key or os.getenv('API_FOOTBALL_KEY')
        if not api_key:
            print("\n⚠️  未提供 API-Football Key")
            print("   将只使用联网搜索获取数据 (可能有数据限制)")
            print("   获取 API Key: https://www.api-football.com/")
            continue_anyway = input("\n是否继续? (y/n): ").strip().lower()
            if continue_anyway != 'y':
                return 0

        # 执行工作流程
        try:
            coordinator = WorkflowCoordinator(api_key)
            result = coordinator.execute_workflow(
                parsed_match=parsed_match,
                interactive=True
            )

            # 保存报告
            report_file = f"analysis_report_{parsed_match.home_team_en}_vs_{parsed_match.away_team_en}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            result.save_to_file(report_file)
            print(f"\n💾 报告已保存到: {report_file}")

            return 0

        except Exception as e:
            print(f"\n❌ 分析过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # 快速分析模式 (命令行参数)
    if args.match:
        try:
            parsed_match = InputParser.parse_match_input(args.match)
            print(f"\n✅ 解析比赛: {parsed_match.home_team_raw} vs {parsed_match.away_team_raw}")

            api_key = args.api_key or os.getenv('API_FOOTBALL_KEY')

            coordinator = WorkflowCoordinator(api_key)
            result = coordinator.execute_workflow(
                parsed_match=parsed_match,
                interactive=False,
                user_params=UserRiskParameters()  # 使用默认参数
            )

            return 0

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


def run_multi_match(args) -> int:
    """Run multiple matches and append parlay risk control."""
    match_inputs = [item.strip() for item in (args.matches or "").split(",") if item.strip()]
    if not match_inputs:
        print("❌ --matches 不能为空")
        return 1

    api_key = args.api_key or os.getenv('API_FOOTBALL_KEY')
    coordinator = WorkflowCoordinator(api_key)
    params = UserRiskParameters()
    reports = []
    rows = []
    parlay_candidates = []

    for idx, match_input in enumerate(match_inputs, 1):
        try:
            parsed = InputParser.parse_match_input(match_input)
            print(f"\n{'=' * 80}\n多场分析 {idx}/{len(match_inputs)}: {parsed.home_team_raw} vs {parsed.away_team_raw}")
            result = coordinator.execute_workflow(parsed, interactive=False, user_params=params)
            reports.append((match_input, result))
            row = _summary_row(match_input, result)
            rows.append(row)
            decision = ((result.math_modeling_report or {}).get("decision") or {})
            jingcai = ((result.data_collection_report or {}).get("jingcai_match") or {})
            parlay_candidates.append({
                "match": match_input,
                "pick": decision.get("primary_pick") or row.get("recommendation"),
                "recommendation": row.get("recommendation"),
                "handicap": jingcai.get("handicap"),
                "competition_type": (((result.math_modeling_report or {}).get("match_context") or {}).get("competition_type")),
                "score": decision.get("score", 0),
                "parlay_allowed": decision.get("parlay_allowed", False),
                "no_bet": decision.get("no_bet", True),
            })
        except Exception as exc:
            print(f"❌ {match_input} 分析失败: {exc}")

    parlay_report = ParlayRiskController.evaluate(parlay_candidates, max_legs=3)
    combined = [
        "# 多场竞彩分析报告",
        "",
        f"> 生成时间: {datetime.now().isoformat(timespec='seconds')}",
        "> 包含单场报告、汇总表和组合相关性风控。",
        "",
    ]
    for match_input, result in reports:
        combined.extend(["---", "", f"<!-- {match_input} -->", "", result.full_report_text, ""])
    combined.extend([
        "---",
        "",
        StandardReportRenderer.render_multi_match_summary(rows),
        "",
        "## 组合相关性风控",
        "",
        f"- 风险等级: {parlay_report.risk_level}",
        f"- 是否允许组合: {'允许' if parlay_report.allowed else '不建议'}",
        f"- 最大建议场数: {parlay_report.max_legs}",
        "",
        "**风险提示：**",
        *[f"- {warning}" for warning in (parlay_report.warnings or ["无额外组合相关性风险"])],
        "",
        "**建议组合：**",
        *[f"- {' × '.join(group)}" for group in (parlay_report.suggested_groups or [])],
    ])

    output = f"multi_match_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(combined))
    print(f"\n💾 多场报告已保存到: {output}")
    print(f"组合风控: {parlay_report.risk_level}, {'允许' if parlay_report.allowed else '不建议'}")
    for warning in parlay_report.warnings:
        print(f"- {warning}")
    return 0


def _summary_row(match_input: str, result: FinalOutput) -> dict:
    decision = ((result.math_modeling_report or {}).get("decision") or {})
    poisson = ((result.math_modeling_report or {}).get("poisson") or {})
    data = result.data_collection_report or {}
    jingcai = data.get("jingcai_match") or {}
    return {
        "match_num": jingcai.get("match_num", "-"),
        "match": match_input,
        "model_lean": decision.get("result_pick", "-"),
        "recommendation": decision.get("primary_pick", "-"),
        "probability": "-",
        "odds": _summary_odds(jingcai),
        "score_direction": "-",
        "goals": decision.get("goals_pick", "-"),
        "tier": 1 if decision.get("confidence") == "high" else (2 if decision.get("confidence") == "medium" else 3),
    }


def _summary_odds(jingcai: dict) -> str:
    odds = jingcai.get("no_handicap_odds") or jingcai.get("handicap_odds") or {}
    if not odds:
        return "-"
    return f"{odds.get('home_win', '-')}/{odds.get('draw', '-')}/{odds.get('away_win', '-')}"


if __name__ == "__main__":
    sys.exit(main())
