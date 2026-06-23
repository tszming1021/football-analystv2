from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/finland_20260623")
MODEL = BASE / "model_analysis.json"
SOURCE = BASE / "source_extract_summary.json"
MARKET = BASE / "market/latest_market.json"
API = BASE / "api/api_audit.json"
WEATHER = BASE / "weather/weather_audit.json"
ONLINE = BASE / "online_review_sources.json"
REPORT = BASE / "2026-06-23芬超周二201-206_严格分析与联网复核报告.md"
TABLE = BASE / "2026-06-23芬超周二201-206_推荐总表.md"

CORE = {
    "周二201": ("拉赫蒂胜，防平", "拉赫蒂-1让负", "2球核心，1/3球保护"),
    "周二202": ("库奥皮奥胜，防平", "库奥皮奥-1让负", "2-3球，4球上沿"),
    "周二203": ("瓦萨不败，重点防平", "瓦萨-1让负", "1-2球核心，0/3球保护"),
    "周二204": ("格尼斯坦不败，客胜优先", "雅罗+1让胜", "3球核心，2/4球保护"),
    "周二205": ("国际图尔库胜", "国际图尔库-1让胜/让负双防", "2-3球，4球上沿"),
    "周二206": ("赫尔辛基胜", "玛丽港+1让负", "3-4球，2/5球保护"),
}

SCORES = {
    "周二201": (["1-1", "1-0", "2-1"], ["1-1", "1-0", "3-0"], ["0-1", "2-2"]),
    "周二202": (["1-1", "1-0", "2-1"], ["1-1", "1-0", "3-1"], ["0-1", "2-3"]),
    "周二203": (["1-1", "1-0", "0-0"], ["1-1", "1-0", "3-0"], ["0-1", "2-2"]),
    "周二204": (["1-1", "1-2", "0-1"], ["1-1", "0-1", "1-3"], ["1-0", "3-2"]),
    "周二205": (["2-1", "2-0", "1-1"], ["2-0", "2-1", "3-0"], ["0-1", "2-2"]),
    "周二206": (["0-2", "1-2", "0-1"], ["0-2", "1-2", "0-3"], ["1-0", "2-2"]),
}

FACTS = {
    "周二201": "拉赫蒂11场11分，主场2胜2平2负；TPS客场0胜2平3负。双方近10场同为3胜2平5负，但TPS仅进10球。",
    "周二202": "库普斯13场仅1负且主场4胜3平；埃尔维斯客场0胜3平3负。库普斯近10场只失5球，埃尔维斯近10场进22球，攻守信号相冲。",
    "周二203": "瓦萨主场不败，近10场5胜4平1负、失6球；奥卢排名第2，近10场6胜1平3负、失8球。属于低失球强强对话。",
    "周二204": "雅罗12场失27球，近10场失29球；格尼斯坦近10场6胜2平2负、进18失9。雅罗防线崩塌风险明显。",
    "周二205": "国际图尔库榜首、主场4胜3平0负，近10场7胜3平不败；塞伊奈排名第10，近10场失14球。",
    "周二206": "玛丽港11场0胜、仅进6球；赫尔辛基近10场进35球，双方进攻终结点差距最大。",
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def score_map(match: dict) -> dict[str, float]:
    return {x["score"]: x["probability"] for x in match["final"]["score_candidate_pool"]}


def fmt_scores(match: dict, scores: list[str]) -> str:
    mapping = score_map(match)
    return " / ".join(f"{s}({pct(mapping.get(s, 0.0))})" for s in scores)


def total_top(match: dict) -> str:
    items = sorted(match["final"]["total_distribution"].items(), key=lambda x: x[1], reverse=True)[:3]
    return " / ".join(f"{k.replace('_plus', '+')}球 {pct(v)}" for k, v in items)


def market_text(item: dict) -> str:
    current, deep = item["current"], item["deep_market"]
    one, hcp = current["one_x_two"], current["handicap_three_way"]
    return (f"竞彩{one['3']:.2f}/{one['1']:.2f}/{one['0']:.2f}；主队{current['handicap']:+g} "
            f"{hcp['3']:.2f}/{hcp['1']:.2f}/{hcp['0']:.2f}；亚洲{deep['yazhi']['current'][1]:+.3f}；"
            f"大小{deep['daxiao']['current'][1]:.2f}")


def build_table(matches: list[dict]) -> str:
    lines = [
        "# 2026-06-23 芬超周二201-206 推荐总表", "",
        "> 数据截点：2026-06-23 16:22（Asia/Hong_Kong）。让球概率按主队竞彩让球结算。", "",
        "| 场次 | 胜/平/负 | 核心 | 让球胜/平/负 | 让球推荐 | 总球Top3 | 概率Top3 | 铁律Top3 | 冷门低/高 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in matches:
        c = m["identity"]["code"]
        r, h = m["final"]["result"], m["final"]["handicap_home_settlement"]
        prob, iron, cold = SCORES[c]
        lines.append(
            f"| {c} {m['identity']['home']}vs{m['identity']['away']} | {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | "
            f"**{CORE[c][0]}** | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | **{CORE[c][1]}** | "
            f"{total_top(m)} | {fmt_scores(m, prob)} | **{fmt_scores(m, iron)}** | {fmt_scores(m, cold)} |"
        )
    lines.extend([
        "", "说明：铁律Top3第三位承担深盘上沿覆盖，不等于纯概率排序；周二203的3-0仅为竞彩-1卡线下的尾部风险位，主线仍是1-1/1-0/0-0。",
        "", "## 混合过关", "",
        "- 2串1主线：国际图尔库胜 × 赫尔辛基胜。",
        "- 2串1保护：拉赫蒂-1让负 × 瓦萨-1让负。",
        "- 3串1：国际图尔库胜 × 赫尔辛基胜 × 库奥皮奥-1让负。",
        "- 4串1：拉赫蒂胜 × 库奥皮奥-1让负 × 国际图尔库胜 × 赫尔辛基胜；高波动。",
        "", "## 比分过关", "",
        "- 2串1：国际图尔库2-0/2-1 × 赫尔辛基0-2/1-2。",
        "- 3串1：再加入拉赫蒂1-0/1-1。",
        "- 4串1：再加入格尼斯坦0-1/1-2；只作小权重覆盖。",
        "", "> 风险提示：瓦萨vs奥卢和库普斯vs埃尔维斯分布较散，不适合作单一赛果胆。",
    ])
    return "\n".join(lines) + "\n"


def build_report(model: dict, source: dict, market: dict, api: dict, weather: dict, online: dict) -> str:
    matches = model["matches"]
    lines = [
        "# 2026-06-23 芬超周二201-206 严格分析与联网复核报告", "",
        "> 数据截点：附件16:08-16:14；500/API/天气/联网复核截至16:22（Asia/Hong_Kong）。", "",
        "## 一、步骤审计", "",
        f"- 附件：{len(source['pdfs'])}份PDF、{len(source['xls'])}份XLS全部解析，错误{len(source['errors'])}；XLS真实格式均为OLE2/BIFF。",
        "- 500主表：六场胜平负、让球三向、比分、总进球、半全场全部读取；18个深盘页面实时复核，错误0。",
        "- 基本面：积分、主客拆分、近10场、交锋、未来赛程和预计阵容均读取。",
        "- API-Football：六场fixture、prediction、odds和联赛积分榜有结果；injuries、lineups、statistics均0行。",
        "- 联网消息：Google News RSS可用，但芬超中文/英文即时报道稀疏，未发现足以替代官方名单的新增伤停确认。",
        "- 缺失层：用户未提供投注分析PDF和Transfermarkt比赛页；交易热度与球员市场价值层不完整，已降权披露。",
        "- xG：真实赛前xG/xGA不可得；proxy xG使用主客拆分、近况、排名和总球市场，未冒充真实xG。",
        "- 模型：Poisson/Dixon-Coles、三类市场去水、贝叶斯融合、LEG、校准、决策迭代、一致性检查及低权重奇门均完成。",
        "", "## 二、总览", "",
        "| 场次 | 胜/平/负 | 让球胜/平/负 | 总球均值 | LEG进球 | L/E/G | 深度差 | 核心 |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for m in matches:
        c, r, h, leg = m["identity"]["code"], m["final"]["result"], m["final"]["handicap_home_settlement"], m["leg"]
        lines.append(
            f"| {c} {m['identity']['home']}vs{m['identity']['away']} | {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | "
            f"{pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | {m['means']['decision_final']:.3f} | "
            f"{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f} | "
            f"{leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f} | "
            f"{leg['depth_gap_10']:.1f} | **{CORE[c][0]}；{CORE[c][1]}** |"
        )
    lines.extend(["", "## 三、逐场分析"])
    for m in matches:
        c, r, h, leg = m["identity"]["code"], m["final"]["result"], m["final"]["handicap_home_settlement"], m["leg"]
        proxy = m["xg"]["proxy"]
        prob, iron, cold = SCORES[c]
        api_payload = json.loads((BASE / "api" / f"{m['identity']['fixture_id']}_predictions.json").read_text())
        api_advice = api_payload["response"][0]["predictions"]["advice"]
        lines.extend([
            "", f"### {c} {m['identity']['home']} vs {m['identity']['away']}", "",
            f"- **基本面**：{FACTS[c]}",
            f"- **市场**：{market_text(market['matches'][c])}。",
            f"- **天气/名单**：{m['source_facts']['weather']}；{m['source_facts']['absence_note']}。",
            f"- **去水融合**：市场去水{pct(m['market']['one_x_two']['probabilities']['home'])}/{pct(m['market']['one_x_two']['probabilities']['draw'])}/{pct(m['market']['one_x_two']['probabilities']['away'])}；模型-市场最大偏差{m['fusion']['result']['max_deviation']*100:.1f}pp，可靠度{m['fusion']['result']['reliability']}。",
            f"- **xG/均值**：proxy xG {proxy['home_xg']:.3f}-{proxy['away_xg']:.3f}，可靠度{proxy['confidence']}；独立均值{m['means']['poisson_contextual']:.3f}，500均值{m['means']['market_exact']:.3f}，融合{m['means']['final_fused']:.3f}，决策最终{m['means']['decision_final']:.3f}。",
            f"- **LEG**：修正进球{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f}；L/E/G {leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f}，综合{leg['total_score']*10:.1f}/10，深度差{leg['depth_gap_10']:.1f}；{leg['depth_direction']}。",
            f"- **最终赛果**：**{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])}**；{CORE[c][0]}。",
            f"- **让球**：**{pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])}**；{CORE[c][1]}。",
            f"- **总球**：{CORE[c][2]}；Top3为{total_top(m)}。",
            f"- **比分**：概率Top3 {fmt_scores(m, prob)}；铁律Top3 **{fmt_scores(m, iron)}**；冷门低/高 {fmt_scores(m, cold)}。",
            f"- **决策迭代**：调整前{pct(m['decision_iteration']['before_result']['home'])}/{pct(m['decision_iteration']['before_result']['draw'])}/{pct(m['decision_iteration']['before_result']['away'])}，调整后{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])}；触发{'、'.join(m['decision_iteration']['applied_rules']) or '无'}。",
            f"- **一致性**：{m['consistency']['status']}；{'；'.join(m['consistency']['warnings']) or '无冲突警告'}。奇门：{m['qimen']['qimen_result_prediction']}（{m['qimen']['confidence']}），仅作风险备注。",
            f"- **API/联网复核**：API建议“{api_advice}”；该固定结构仅作方向旁证，不覆盖项目模型。",
        ])
    lines.extend([
        "", "## 四、组合建议", "",
        "- 2串1主线：国际图尔库胜 × 赫尔辛基胜。",
        "- 2串1保护：拉赫蒂-1让负 × 瓦萨-1让负。",
        "- 3串1：国际图尔库胜 × 赫尔辛基胜 × 库奥皮奥-1让负。",
        "- 4串1：拉赫蒂胜 × 库奥皮奥-1让负 × 国际图尔库胜 × 赫尔辛基胜；高波动。",
        "- 比分2串1：国际图尔库2-0/2-1 × 赫尔辛基0-2/1-2。",
        "- 比分3串1：再加入拉赫蒂1-0/1-1。",
        "- 比分4串1：再加入格尼斯坦0-1/1-2。",
        "", "## 五、联网来源", "",
        "- [500竞彩足球实时主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [芬兰超级联赛官网](https://www.veikkausliiga.com/)",
        "- [Open-Meteo天气API](https://open-meteo.com/en/docs)",
        "", "## 六、最终判断", "",
        "1. 国际图尔库与赫尔辛基是最清楚的赛果方向；前者-1结算接近，后者赢两球以上路径更强。",
        "2. 拉赫蒂和库奥皮奥都有胜面，但让一球深度不足，优先让负保护。",
        "3. 瓦萨vs奥卢是最典型的防平场：低总球、两队防守好、榜上位置接近，1-1与0-0必须保留。",
        "4. 雅罗防线问题严重，格尼斯坦不败合理；但竞彩+1让胜偏低，说明市场仍高度防范雅罗守平或爆冷。",
        "5. 赫尔辛基场必须保留0-3和0-4上沿，不应把强弱差只压缩成0-1。",
        "", "> 风险提示：六场尚无官方首发与API伤停记录；临场名单或盘口跨档需重新计算。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    market = json.loads(MARKET.read_text(encoding="utf-8"))
    api = json.loads(API.read_text(encoding="utf-8"))
    weather = json.loads(WEATHER.read_text(encoding="utf-8"))
    online = json.loads(ONLINE.read_text(encoding="utf-8"))
    REPORT.write_text(build_report(model, source, market, api, weather, online), encoding="utf-8")
    TABLE.write_text(build_table(model["matches"]), encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "table": str(TABLE)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
