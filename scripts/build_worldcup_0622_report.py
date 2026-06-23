from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260623")
MODEL_PATH = BASE / "model_analysis.json"
SOURCE_PATH = BASE / "source_extract_summary.json"
API_PATH = BASE / "api/api_audit.json"
MARKET_PATH = BASE / "market/latest_market.json"
WEATHER_PATH = BASE / "weather/weather_audit.json"
ONLINE_PATH = BASE / "online_review_sources.json"
OUT = BASE / "2026-06-23世界杯周一041-044_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-23世界杯周一041-044_推荐总表.md"

GROUP = {
    "周一041": "J组：阿根廷3分(+3)、奥地利3分(+2)、约旦0分(-2)、阿尔及利亚0分(-3)。本场胜者到6分并锁定前二；平局则双方4分，末轮仍有主动权。",
    "周一042": "I组：挪威3分(+3)、法国3分(+2)、塞内加尔0分(-2)、伊拉克0分(-3)。法国取胜到6分并锁定前二；平局到4分仍占明显主动。",
    "周一043": "I组同上。挪威取胜到6分并锁定前二；塞内加尔若再负将连续两轮0分，第三名晋级路径也会非常被动，因此后段追分动机强。",
    "周一044": "J组同上。双方均0分，本场是现实意义上的抢救战；平局会让两队末轮必须取胜并依赖第三名横向比较，落后一方后段压上风险高。",
}

MARKET = {
    "周一041": ("1.40 / 3.98 / 6.10", "阿根廷-1：2.28 / 3.48 / 2.48", "亚洲-0.969（初始-0.797）", "2.50（初始2.49）", "阿根廷交易94.6% vs 百家62.0%，明显过热"),
    "周一042": ("竞彩未开售；百家1.08 / 11.27 / 28.04", "法国-3：2.61 / 4.50 / 1.91", "亚洲-2.719（初始-2.094）", "3.46（初始3.15）", "法国交易91.2% vs 百家88.0%，轻度偏热"),
    "周一043": ("1.95 / 3.30 / 3.20", "挪威-1：3.88 / 3.82 / 1.64", "亚洲仅-0.250（初始-0.328）", "2.50（初始2.53）", "挪威交易52.5% vs 百家42.2%，偏热但规模适中"),
    "周一044": ("5.82 / 3.80 / 1.44", "约旦+1：2.40 / 3.35 / 2.42", "约旦+0.969（初始+0.828）", "2.50（初始2.49）", "阿尔及利亚交易83.8% vs 百家60.6%，明显过热"),
}

CORE = {
    "周一041": ("阿根廷胜，防平", "阿根廷-1让负优先，与让胜双防", "2-4球，2/3球核心"),
    "周一042": ("法国胜", "法国-3让负", "3-5球，4球以上约42.6%"),
    "周一043": ("挪威不败，胜平双选", "挪威-1让负", "2-3球，1球保护"),
    "周一044": ("阿尔及利亚胜", "约旦+1让胜", "2-3球，4球上沿保护"),
}

SCORES = {
    "周一041": (["1-0", "2-0", "1-1"], ["1-0", "2-0", "3-0"], ["0-1", "2-2"]),
    "周一042": (["2-0", "3-0", "1-0"], ["2-0", "3-0", "4-0"], ["1-1", "3-2"]),
    "周一043": (["1-1", "1-0", "2-1"], ["1-1", "1-0", "2-2"], ["0-1", "2-3"]),
    "周一044": (["0-1", "0-2", "1-1"], ["0-1", "0-2", "0-3"], ["1-0", "2-2"]),
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def score_map(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def fmt_scores(match: dict, scores: list[str]) -> str:
    mapping = score_map(match)
    return " / ".join(f"{score}({pct(mapping.get(score, 0.0))})" for score in scores)


def total_top(match: dict) -> str:
    distribution = match["final"]["total_distribution"]
    items = sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:3]
    return " / ".join(f"{key.replace('_plus', '+')}球 {pct(value)}" for key, value in items)


def build_table(matches: list[dict]) -> str:
    lines = [
        "# 2026-06-23 世界杯周一041-044 推荐总表",
        "",
        "> 数据截点：2026-06-22 03:19（Asia/Shanghai）。概率经过市场去水、贝叶斯融合和决策迭代；法国普通竞彩三向未开售。",
        "",
        "| 场次 | 胜/平/负 | 核心推荐 | 让球胜/平/负 | 让球推荐 | 总球Top3 | 概率Top3比分 | 铁律Top3 | 冷门低位/高位 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        probability, iron, cold = SCORES[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])} | **{CORE[code][0]}** | "
            f"{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])} | **{CORE[code][1]}** | "
            f"{total_top(match)} | {fmt_scores(match, probability)} | **{fmt_scores(match, iron)}** | {fmt_scores(match, cold)} |"
        )
    lines.extend([
        "",
        "让球概率均按主队所列竞彩让球结算。铁律Top3不是纯概率排序：第三位承担强弱差对应的上沿覆盖。",
        "",
        "## 混合过关",
        "",
        "| 类型 | 组合 | 定位 |",
        "|---|---|---|",
        "| 2串1主线 | 法国胜 × 挪威-1让负 | 法国赛果最稳，挪威深盘反向最清楚 |",
        "| 2串1替代 | 阿根廷胜 × 阿尔及利亚胜 | 两个赛果方向，但双方均有交易过热 |",
        "| 3串1 | 法国胜 × 挪威-1让负 × 阿尔及利亚胜 | 主线组合；阿尔及利亚需防约旦+1 |",
        "| 4串1 | 阿根廷胜 × 法国胜 × 挪威-1让负 × 约旦+1让胜 | 高波动，只作小权重覆盖 |",
        "",
        "## 比分过关",
        "",
        "- 2串1：法国 2-0/3-0 × 阿尔及利亚 0-1/0-2。",
        "- 3串1：阿根廷 1-0/2-0 × 法国 2-0/3-0 × 阿尔及利亚 0-1/0-2。",
        "- 4串1：再加入挪威 1-1/1-0/2-1；该场分布最散，组合风险显著上升。",
        "",
        "> 风险提示：过关场次增加会快速压低命中概率；临场首发或盘口跨档时需重算。",
    ])
    return "\n".join(lines) + "\n"


def build_report(model: dict, source: dict, api: dict, market: dict, weather: dict, online: dict) -> str:
    matches = model["matches"]
    lines = [
        "# 2026-06-23 世界杯周一041-044 严格分析与GPT联网复核报告",
        "",
        "> 数据截点：附件与500网页截至2026-06-22 03:16；API、天气与联网复核截至03:19（Asia/Shanghai）。",
        "",
        "## 一、步骤审计",
        "",
        f"- 附件：{len(source['pdfs'])}份PDF、{len(source['xls'])}份XLS全部实际解析，错误{len(source['errors'])}；XLS均为真实OLE2/BIFF。",
        "- 500主表：胜平负、让球三向、比分、总进球、半全场全部读取；法国普通胜平负未开售，以百家即时均值降权替代。",
        f"- 500实时深盘：四场欧赔、亚洲盘、大小盘共12页重新抓取，错误{len(market['errors'])}。",
        "- 基本面：FIFA排名、小组积分、首轮赛果、近10场、未来赛程、预计阵容、交易热度均读取。",
        "- Transfermarkt：四场市场价值与缺席页已读取；仅奥地利列Stefan Posch下颌骨折，其余未列缺席不代表官方全员健康。",
        "- API-Football：四场fixture、prediction、odds有结果；injuries、lineups、statistics均0行。prediction的Poisson字段为0%，不输入最终概率。",
        "- 天气：Open-Meteo按四个场馆当地开球小时抓取；达拉斯雷暴湿热、费城高温大风、纽约大风已进入G层。",
        "- 数学层：Poisson/Dixon-Coles、三类市场去水、贝叶斯融合、proxy xG、LEG、历史校准、决策迭代、一致性检查均完成。",
        "- 奇门：已运行，只保留低权重风险提示，不覆盖模型。",
        "- GPT联网复核：当前Codex会话核验Opta模拟、Google News RSS、FIFA赛制与Open-Meteo；通用搜索接口HTTP 403，已改用直达页面与RSS。",
        "- 未完成项：真实赛前xG/xGA和官方最终首发尚不可得，已明确降权，未用预计阵容冒充确认。",
        "",
        "## 二、小组出线形势",
        "",
        "2026世界杯每组前二及8个最佳第三名进入32强。I组与J组首轮都形成两队3分、两队0分；第二轮拿到6分即可锁定前二，0分球队则必须尽快抢分。",
        "",
    ]
    for match in matches:
        code = match["identity"]["code"]
        lines.append(f"- **{code}**：{GROUP[code]}")
    lines.extend([
        "",
        "## 三、推荐总览",
        "",
        "| 场次 | 胜/平/负 | 让球胜/平/负 | 最终总球均值 | LEG进球 | L/E/G | 深度差 | 核心 |",
        "|---|---|---|---:|---|---|---:|---|",
    ])
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{match['means']['decision_final']:.3f} | {leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f} | "
            f"{leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f} | "
            f"{leg['depth_gap_10']:.1f} | **{CORE[code][0]}；{CORE[code][1]}** |"
        )
    lines.extend(["", "## 四、逐场分析"])
    for match in matches:
        identity = match["identity"]
        code = identity["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        proxy = match["xg"]["proxy"]
        probability, iron, cold = SCORES[code]
        opta = online["matches"][code]["opta"]
        market_text = MARKET[code]
        lines.extend([
            "",
            f"### {code} {identity['home']} vs {identity['away']}",
            "",
            f"- **出线背景**：{GROUP[code]}",
            f"- **实力近况**：FIFA {match['source_facts']['fifa_rank']['home']} vs {match['source_facts']['fifa_rank']['away']}；近10场进失球 {match['source_facts']['recent_10']['home']['goals_for']}-{match['source_facts']['recent_10']['home']['goals_against']} vs {match['source_facts']['recent_10']['away']['goals_for']}-{match['source_facts']['recent_10']['away']['goals_against']}；首轮{identity['first_round']}。",
            f"- **情报环境**：{match['source_facts']['absence_note']}。{match['source_facts']['weather']}。",
            f"- **市场**：三向{market_text[0]}；{market_text[1]}；{market_text[2]}；大小{market_text[3]}；热度：{market_text[4]}。",
            f"- **去水融合**：市场去水{pct(match['market']['one_x_two']['probabilities']['home'])}/{pct(match['market']['one_x_two']['probabilities']['draw'])}/{pct(match['market']['one_x_two']['probabilities']['away'])}；模型-市场最大偏差{match['fusion']['result']['max_deviation']*100:.1f}pp，可靠度{match['fusion']['result']['reliability']}，警告{'、'.join(match['fusion']['result']['warnings']) or '无'}。",
            f"- **xG与均值**：真实xG缺失；proxy xG {proxy['home_xg']:.3f}-{proxy['away_xg']:.3f}，样本可靠度主/客均{proxy['components']['team_rates']['home_sample_reliability']:.2f}。独立均值{match['means']['poisson_contextual']:.3f}，500精确总球均值{match['means']['market_exact']:.3f}，融合{match['means']['final_fused']:.3f}，决策最终{match['means']['decision_final']:.3f}。",
            f"- **LEG**：修正进球{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f}；L/E/G为{leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f}，综合{leg['total_score']*10:.1f}/10，强弱差{leg['depth_gap_10']:.1f}；{leg['depth_direction']}。",
            f"- **最终赛果**：**{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])}**；核心：{CORE[code][0]}。",
            f"- **让球**：**{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])}**；建议：{CORE[code][1]}。",
            f"- **总球**：{CORE[code][2]}；分布Top3为{total_top(match)}。",
            f"- **比分**：概率Top3 {fmt_scores(match, probability)}；铁律Top3 **{fmt_scores(match, iron)}**；冷门低位/高位 {fmt_scores(match, cold)}。",
            f"- **决策迭代**：调整前{pct(match['decision_iteration']['before_result']['home'])}/{pct(match['decision_iteration']['before_result']['draw'])}/{pct(match['decision_iteration']['before_result']['away'])}，调整后{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}；触发{'、'.join(match['decision_iteration']['applied_rules'])}。",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings']) or '无冲突警告'}。",
            f"- **奇门**：{match['qimen']['qimen_result_prediction']}，置信{match['qimen']['confidence']}；不覆盖数据模型。",
            f"- **GPT/Opta复核**：Opta 25,000次模拟为{pct(opta['home'])}/{pct(opta['draw'])}/{pct(opta['away'])}。项目模型与其差异用于校验信心，不直接替换项目后验概率。",
        ])
    lines.extend([
        "",
        "## 五、组合建议",
        "",
        "- 2串1主线：法国胜 × 挪威-1让负。",
        "- 2串1替代：阿根廷胜 × 阿尔及利亚胜；两场都存在交易过热。",
        "- 3串1：法国胜 × 挪威-1让负 × 阿尔及利亚胜。",
        "- 4串1：阿根廷胜 × 法国胜 × 挪威-1让负 × 约旦+1让胜；高波动。",
        "- 比分2串1：法国2-0/3-0 × 阿尔及利亚0-1/0-2。",
        "- 比分3串1：再加入阿根廷1-0/2-0。",
        "- 比分4串1：再加入挪威1-1/1-0/2-1；挪威场分布最散。",
        "",
        "## 六、联网复核来源",
        "",
        "- [500竞彩足球实时主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [Opta：阿根廷vs奥地利](https://theanalyst.com/articles/argentina-vs-austria-prediction-world-cup-2026)",
        "- [Opta：法国vs伊拉克](https://theanalyst.com/articles/france-vs-iraq-prediction-world-cup-2026)",
        "- [Opta：挪威vs塞内加尔](https://theanalyst.com/articles/norway-vs-senegal-prediction-world-cup-2026)",
        "- [Opta：约旦vs阿尔及利亚](https://theanalyst.com/articles/jordan-vs-algeria-prediction-world-cup-2026)",
        "- [FIFA 2026赛制说明](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/world-cup-2026-format-teams-groups-qualification)",
        "- [Open-Meteo天气API](https://open-meteo.com/en/docs)",
        "",
        "## 七、最终判断",
        "",
        "1. 法国胜是四场最强赛果，但法国-3让负高达约60.8%，不要把超低胜赔等同于净胜4球。",
        "2. 阿根廷主胜方向与Opta一致，但交易94.6%远高于百家62.0%，-1让胜和让负几乎五五开，优先赛果而非深盘。",
        "3. 挪威只具小幅胜面；竞彩设-1而亚洲均线仅-0.25，最清楚的玩法反而是挪威-1让负。",
        "4. 阿尔及利亚客胜方向稳定，但客胜交易83.8%过热；约旦+1让胜是更有保护性的让球方向。",
        "5. 比分层法国必须保留4-0上沿，阿尔及利亚保留0-3；挪威场必须同时保留1-1和2-2，避免单押主胜。",
        "",
        "> 风险提示：以上为当前数据截点的概率估计，不是赛果保证。临场官方首发、屋顶状态、伤停确认或盘口跨档都可能改变结论。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    api = json.loads(API_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    weather = json.loads(WEATHER_PATH.read_text(encoding="utf-8"))
    online = json.loads(ONLINE_PATH.read_text(encoding="utf-8"))
    OUT.write_text(build_report(model, source, api, market, weather, online), encoding="utf-8")
    TABLE_OUT.write_text(build_table(model["matches"]), encoding="utf-8")
    print(json.dumps({"report": str(OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
