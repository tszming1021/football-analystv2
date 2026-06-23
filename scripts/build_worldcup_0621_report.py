from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260622")
MODEL_PATH = BASE / "model_analysis.json"
SOURCE_PATH = BASE / "source_extract_summary.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
ONLINE_PATH = BASE / "online_review_sources.json"
OUT = BASE / "2026-06-22世界杯周日037-040_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-22世界杯周日037-040_推荐总表.md"

GROUP_CONTEXT = {
    "周日037": {
        "group": "H组",
        "standings": "乌拉圭1分(1-1)、沙特1分(1-1)、西班牙1分(0-0)、佛得角1分(0-0)",
        "shape": "西班牙若胜升至4分并掌握前二主动权；再平则两轮2分且净胜球仍可能为0，末轮对乌拉圭压力陡增；失利将陷入必须末轮取胜并比较第三名的局面。沙特首轮逼平乌拉圭，平局并非无价值，但胜者将直接占据前二主动。",
    },
    "周日038": {
        "group": "G组",
        "standings": "新西兰1分(2-2)、伊朗1分(2-2)、比利时1分(1-1)、埃及1分(1-1)",
        "shape": "比利时和伊朗都以1分进入第二轮；胜者升至4分，出线概率显著提升。比利时若再平，末轮对新西兰仍有主动但容错变小；伊朗若守住平局，凭首轮进球数仍保留第三名竞争力。",
    },
    "周日039": {
        "group": "H组",
        "standings": "乌拉圭1分(1-1)、沙特1分(1-1)、西班牙1分(0-0)、佛得角1分(0-0)",
        "shape": "乌拉圭与佛得角同为1分。乌拉圭若胜升至4分，但末轮还要对西班牙，因此本场争胜价值很高；佛得角首轮0-0逼平西班牙，平局会把悬念留到末轮对沙特，低位防守动机充分。",
    },
    "周日040": {
        "group": "G组",
        "standings": "新西兰1分(2-2)、伊朗1分(2-2)、比利时1分(1-1)、埃及1分(1-1)",
        "shape": "新西兰与埃及同积1分，胜者升至4分。埃及末轮对伊朗，新西兰末轮对比利时；双方都不愿把主动权留到末轮，因此比赛后段可能比开局更开放。",
    },
}

MARKET = {
    "周日037": {
        "one_x_two": "竞彩未开售；百家即时均值1.10 / 10.27 / 24.89",
        "handicap": "西班牙-2：1.63 / 4.50 / 3.40",
        "asian": "亚洲均线-2.578（初始-2.125），明显升深",
        "total": "大小均线3.43（初始3.07），总进球数字同步升高",
        "heat": "交易主胜90.0%，百家概率86.7%，热度略高但差距不大",
    },
    "周日038": {
        "one_x_two": "竞彩1.28 / 4.61 / 7.60",
        "handicap": "比利时-1：1.92 / 3.72 / 2.94",
        "asian": "亚洲均线-1.281（初始-1.109），小幅升深",
        "total": "大小均线2.63（初始2.50）",
        "heat": "交易主胜81.8%，百家概率66.6%，主胜热度显著偏高",
    },
    "周日039": {
        "one_x_two": "竞彩1.30 / 4.05 / 8.80",
        "handicap": "乌拉圭-1：2.14 / 3.23 / 2.84",
        "asian": "亚洲均线-1.047（初始-1.063），深度基本不升",
        "total": "大小均线2.29（初始2.49），总球明显下修",
        "heat": "交易主胜91.4%，百家概率65.3%，四场中过热最明显",
    },
    "周日040": {
        "one_x_two": "竞彩5.85 / 3.80 / 1.44",
        "handicap": "新西兰+1：2.40 / 3.34 / 2.42",
        "asian": "亚洲均线新西兰+0.953（初始+0.672），客队方向升深",
        "total": "大小均线2.31（初始2.29），基本稳定",
        "heat": "交易客胜75.7%，百家概率59.5%，埃及客胜偏热",
    },
}

ONLINE = {
    "周日037": "Opta 87.4% / 8.8% / 3.8%；Al Jazeera确认西班牙需要取胜掌控H组，并引述亚马尔称尚不适合踢满90分钟。",
    "周日038": "Opta 67.5% / 19.3% / 13.2%；比利时出线概率90.9%。伊朗旅行限制属于场外背景，不按球员缺阵处理。",
    "周日039": "Opta 67.2% / 20.6% / 12.2%；乌拉圭出线概率74.7%，佛得角47.6%。本模型因伤缺、低位对手、天气和过热信号更保守。",
    "周日040": "Opta新西兰17.7%、平22.7%、埃及59.6%；与本模型15.9% / 25.9% / 58.2%高度接近。埃及主帅否认萨拉赫不和。",
}

CORE = {
    "周日037": ("西班牙胜", "西班牙-2让胜，防让负", "3-4球核心，2/5球保护"),
    "周日038": ("比利时胜，防平", "比利时-1让负", "2-4球，3球核心"),
    "周日039": ("乌拉圭胜，平局重点保护", "乌拉圭-1让负；三项接近，不单挑", "1-3球，1/2球核心"),
    "周日040": ("埃及胜", "新西兰+1让胜，防让负", "2-3球，1/4球保护"),
}

SCORE_SETS = {
    "周日037": (["2-0", "3-0", "1-0"], ["1-0", "2-0", "3-0"], ["1-1", "2-2"]),
    "周日038": (["1-0", "2-1", "2-0"], ["2-1", "1-0", "3-1"], ["1-1", "2-2"]),
    "周日039": (["1-0", "2-0", "0-0"], ["1-0", "2-0", "3-0"], ["0-0", "2-2"]),
    "周日040": (["0-1", "0-2", "1-1"], ["1-1", "0-1", "0-3"], ["1-0", "2-2"]),
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def score_map(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def fmt_scores(match: dict, scores: list[str]) -> str:
    mapping = score_map(match)
    return " / ".join(f"{score}({pct(mapping.get(score, 0.0))})" for score in scores)


def build_table(matches: list[dict]) -> str:
    lines = [
        "# 2026-06-22 世界杯周日037-040 推荐总表",
        "",
        "> 数据截点：2026-06-21 15:39-16:05（Asia/Shanghai）。概率为去水、贝叶斯融合和决策迭代后的模型估计。",
        "",
        "| 场次 | 胜/平/负 | 核心方向 | 让球胜/平/负 | 让球建议 | 总球 | 概率Top3比分 | 铁律Top3 | 冷门比分 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        probability_scores, iron_scores, cold_scores = SCORE_SETS[code]
        core = CORE[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])} | **{core[0]}** | "
            f"{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])} | {core[1]} | {core[2]} | "
            f"{fmt_scores(match, probability_scores)} | **{fmt_scores(match, iron_scores)}** | {fmt_scores(match, cold_scores)} |"
        )
    lines.extend([
        "",
        "说明：让球概率按主队所列让球结算；铁律Top3前两位保持保守，第三位承担上沿覆盖，不等同于纯概率排序。",
        "",
        "## 混合组合",
        "",
        "| 类型 | 组合 | 风险说明 |",
        "|---|---|---|",
        "| 2串1主线 | 比利时胜 × 埃及胜 | 两场模型胜率均在56%-58%，埃及与Opta一致性更高 |",
        "| 2串1替代 | 乌拉圭胜 × 埃及胜 | 乌拉圭存在过热、伤缺和天气折扣 |",
        "| 3串1 | 西班牙-2让胜 × 比利时胜 × 埃及胜 | 西班牙-2仅40.5%，必须控制权重 |",
        "| 4串1 | 西班牙-2让胜 × 比利时胜 × 乌拉圭-1让负 × 埃及胜 | 高波动，不作为核心方案 |",
        "",
        "## 比分组合",
        "",
        "- 2串1：西班牙 2-0/3-0 × 埃及 0-1/0-2。",
        "- 3串1：西班牙 2-0/3-0 × 比利时 1-0/2-1 × 埃及 0-1/0-2。",
        "- 4串1：再加入乌拉圭 1-0/2-0；只作小权重覆盖。",
        "",
        "> 风险提示：组合概率会随场次数增加快速下降；临场首发或市场跨档时必须重算。",
    ])
    return "\n".join(lines) + "\n"


def build_report(model: dict, source: dict, api_audit: dict, online: dict) -> str:
    matches = model["matches"]
    lines = [
        "# 2026-06-22 世界杯周日037-040 严格分析与GPT联网复核报告",
        "",
        "> 数据截点：500附件2026-06-21 15:39-15:41；API、天气与联网复核截至16:05（Asia/Shanghai）。",
        "",
        "## 一、步骤审计与数据完整度",
        "",
        f"- 500主表：胜平负、让球三向、比分、总进球、半全场全部读取。西班牙普通胜平负未开售，以百家即时均值作为降权证据。",
        f"- 深层附件：{len(source['pdfs'])}份PDF、{len(source['xls'])}份XLS全部解析，错误{len(source['errors'])}；XLS真实格式均为OLE2/BIFF。",
        "- 500深层页：排名、近况、首轮赛果、小组积分、未来赛程、预计阵容和市场热度均已读取。",
        "- Transfermarkt：四场比赛页均读取；缺席信息只按二级来源处理。",
        "- API-Football：四场fixture、prediction、odds均有结果；injuries、lineups、statistics均为0行。prediction负数goals字段判为异常并排除。",
        "- 天气：Open-Meteo四地开球小时数据已保存；迈阿密雷暴/高温触发节奏压制。",
        "- 数学层：Poisson/Dixon-Coles、市场去水、贝叶斯融合、proxy xG、LEG、校准规则、决策迭代、一致性检查全部运行。",
        "- 奇门：仅作低权重风险提示，不覆盖模型。",
        "- GPT联网复核：由Codex当前会话直接核验FIFA、Al Jazeera、Opta和Open-Meteo公开页面；通用搜索接口受挑战页阻断，已改用直达网页和Google News RSS发现。",
        "- 未完成项：没有官方最终首发；真实赛前xG/xGA不可用。两项均已降权披露，不以预计阵容冒充确认阵容。",
        "",
        "## 二、小组出线形势",
        "",
        "2026世界杯为12个四队小组；每组前二与8个成绩最好的第三名进入32强。两组首轮全部打平，所以第二轮胜者会升至4分并显著掌握主动，但4分在数学上尚不能一概写成提前出线。",
        "",
        "| 小组 | 当前积分结构 | 第二轮含义 |",
        "|---|---|---|",
        f"| H组 | {GROUP_CONTEXT['周日037']['standings']} | 西班牙、乌拉圭都需要胜利来避免末轮直接对话变成高压生死战；沙特、佛得角的平局策略仍有现实价值。 |",
        f"| G组 | {GROUP_CONTEXT['周日038']['standings']} | 四队同分；比利时、埃及市场更强，但伊朗、新西兰首轮都证明有进球和追平能力。 |",
        "",
        "## 三、总览结论",
        "",
        "| 场次 | 胜/平/负 | 让球胜/平/负 | 总球均值 | LEG修正进球 | 强弱差 | 一致性 | 核心 |",
        "|---|---|---|---:|---|---:|---|---|",
    ]
    for match in matches:
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        code = match["identity"]["code"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{match['means']['decision_final']:.3f} | {leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f} | "
            f"{leg['depth_gap_10']:.1f} | {match['consistency']['status']} | {CORE[code][0]}；{CORE[code][1]} |"
        )

    lines.extend(["", "## 四、逐场严格分析"])
    for match in matches:
        identity = match["identity"]
        code = identity["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        proxy = match["xg"]["proxy"]
        probability_scores, iron_scores, cold_scores = SCORE_SETS[code]
        lines.extend([
            "",
            f"### {code} {identity['home']} vs {identity['away']}",
            "",
            f"**基本面与出线形势**",
            "",
            f"- 场地：{identity['venue']}；首轮：{identity['first_round']}。",
            f"- {GROUP_CONTEXT[code]['shape']}",
            f"- FIFA排名：{match['source_facts']['fifa_rank']['home']} vs {match['source_facts']['fifa_rank']['away']}；近10场进失球：{match['source_facts']['recent_10']['home']['goals_for']}-{match['source_facts']['recent_10']['home']['goals_against']} vs {match['source_facts']['recent_10']['away']['goals_for']}-{match['source_facts']['recent_10']['away']['goals_against']}。",
            f"- 情报：{match['source_facts']['absence_note']}。",
            f"- 环境：{match['source_facts']['weather']}。",
            "",
            f"**市场数字与热度**",
            "",
            f"- 胜平负：{MARKET[code]['one_x_two']}。",
            f"- 让球：{MARKET[code]['handicap']}；{MARKET[code]['asian']}。",
            f"- 总球：{MARKET[code]['total']}。",
            f"- 热度：{MARKET[code]['heat']}。",
            "",
            f"**xG、融合与LEG**",
            "",
            f"- 真实赛前xG/xGA缺失；proxy xG为{proxy['home_xg']:.3f}-{proxy['away_xg']:.3f}，样本可靠度主{proxy['components']['team_rates']['home_sample_reliability']:.2f}/客{proxy['components']['team_rates']['away_sample_reliability']:.2f}，已向国家队基准收缩。",
            f"- 独立均值{match['means']['poisson_contextual']:.3f}；500精确总球均值{match['means']['market_exact']:.3f}；融合后{match['means']['final_fused']:.3f}；决策最终{match['means']['decision_final']:.3f}。",
            f"- 去水市场与模型最大偏差{match['fusion']['result']['max_deviation'] * 100:.1f}pp，可靠度{match['fusion']['result']['reliability']}；警告：{'、'.join(match['fusion']['result']['warnings']) or '无'}。",
            f"- 总进球市场去水警告：{'、'.join(match['market']['total_exact']['warnings']) or '无'}；该层只作为贝叶斯证据，不直接当作最终概率。",
            f"- LEG修正预期进球{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f}；L/E/G评分{leg['line_score'] * 10:.1f}/{leg['expected_goals_score'] * 10:.1f}/{leg['game_context_score'] * 10:.1f}；综合{leg['total_score'] * 10:.1f}/10，强弱差{leg['depth_gap_10']:.1f}；结论：{leg['depth_direction']}。",
            "",
            f"**最终概率与比分**",
            "",
            f"- 胜/平/负：**{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])}**。",
            f"- 让球胜/平/负：**{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])}**；建议：{CORE[code][1]}。",
            f"- 总球：{CORE[code][2]}。",
            f"- 概率Top3：{fmt_scores(match, probability_scores)}。",
            f"- 铁律Top3：**{fmt_scores(match, iron_scores)}**；冷门：{fmt_scores(match, cold_scores)}。",
            "",
            f"**决策迭代与一致性**",
            "",
            f"- 调整前胜/平/负：{pct(match['decision_iteration']['before_result']['home'])}/{pct(match['decision_iteration']['before_result']['draw'])}/{pct(match['decision_iteration']['before_result']['away'])}；调整后：{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}。",
            f"- 触发规则：{'、'.join(match['decision_iteration']['applied_rules'])}。",
            f"- 一致性：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings']) or '无冲突警告'}。",
            f"- 奇门辅助：{match['qimen']['qimen_result_prediction']}，置信{match['qimen']['confidence']}；仅作风险备注。",
            "",
            f"**GPT联网复核**",
            "",
            f"- {ONLINE[code]}",
            f"- 复核结论：数据主方向维持“{CORE[code][0]}”，但联网概率不直接覆盖项目模型；差异用于调整信心与保护表达。",
        ])

    lines.extend([
        "",
        "## 五、组合建议",
        "",
        "- 2串1主线：比利时胜 × 埃及胜。",
        "- 2串1替代：乌拉圭胜 × 埃及胜；乌拉圭需接受过热与天气折扣。",
        "- 3串1：西班牙-2让胜 × 比利时胜 × 埃及胜；西班牙深盘不是低风险项。",
        "- 4串1：西班牙-2让胜 × 比利时胜 × 乌拉圭-1让负 × 埃及胜；仅作高波动覆盖。",
        "- 比分2串1：西班牙2-0/3-0 × 埃及0-1/0-2。",
        "- 比分3串1：再加入比利时1-0/2-1。",
        "- 比分4串1：再加入乌拉圭1-0/2-0。",
        "",
        "## 六、GPT联网复核来源",
        "",
        "- [FIFA 2026赛制说明](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/world-cup-2026-format-teams-groups-qualification)",
        "- [Al Jazeera：西班牙vs沙特与亚马尔状态](https://www.aljazeera.com/sports/2026/6/20/spain-vs-saudi-arabia-world-cup-2026-yamal-prediction-watch-kickoff)",
        "- [Opta：西班牙vs沙特](https://theanalyst.com/articles/spain-vs-saudi-arabia-prediction-world-cup-2026)",
        "- [Al Jazeera：伊朗旅行限制背景](https://www.aljazeera.com/sports/2026/6/20/us-refuses-to-ease-iran-world-cup-travel-restrictions-for-belgium-match)",
        "- [Opta：比利时vs伊朗](https://theanalyst.com/articles/belgium-vs-iran-prediction-world-cup-2026)",
        "- [Opta：乌拉圭vs佛得角](https://theanalyst.com/articles/uruguay-vs-cape-verde-prediction-world-cup-2026)",
        "- [Al Jazeera：埃及主帅否认萨拉赫不和](https://www.aljazeera.com/sports/2026/6/21/egypt-coach-denies-salah-rift-before-world-cup-match-against-new-zealand)",
        "- [Opta：新西兰vs埃及](https://theanalyst.com/articles/new-zealand-vs-egypt-prediction-world-cup-2026)",
        "- [Open-Meteo天气API说明](https://open-meteo.com/en/docs)",
        "",
        "## 七、最终结论",
        "",
        "1. 西班牙是四场最强赛果方向，但亚马尔受限、首轮终结效率和-2深盘卡线要求保留让负。",
        "2. 比利时胜面存在，但主胜交易过热、伤缺不确定和14.7pp模型-市场偏差使其只能列中等信心。",
        "3. 乌拉圭是最需要降温的一场：竞彩主胜很低、交易极热，但总球下修、核心伤缺、佛得角低位韧性与迈阿密天气共同压低赢深。",
        "4. 埃及胜是联网与项目模型一致性最高的一场；仍需保留新西兰+1让胜，因为双方首轮均有追平能力且客胜热度偏高。",
        "5. 核心组合优先比利时胜+埃及胜；西班牙-2和乌拉圭-1都不应被当成稳胆。",
        "",
        "> 风险提示：所有概率均为当前数据截点下的估计，不是赛果保证。临场首发、伤停确认或市场跨档会改变结论。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    api_audit = json.loads(API_AUDIT_PATH.read_text(encoding="utf-8"))
    online = json.loads(ONLINE_PATH.read_text(encoding="utf-8"))
    OUT.write_text(build_report(model, source, api_audit, online), encoding="utf-8")
    TABLE_OUT.write_text(build_table(model["matches"]), encoding="utf-8")
    print(json.dumps({"report": str(OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
