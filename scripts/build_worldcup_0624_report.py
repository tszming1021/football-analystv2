from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260624")
OUT = BASE / "2026-06-24世界杯周二045-048_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-24世界杯周二045-048_推荐总表.md"

GROUP = {
    "周二045": "K组：哥伦比亚3分(+2)、葡萄牙1分(0)、刚果(金)1分(0)、乌兹别克斯坦0分(-2)。葡萄牙必须争胜，且需争净胜球以修复首轮失分；乌兹别克若再负将极度被动。",
    "周二046": "L组：英格兰3分(+2)、加纳3分(+1)、巴拿马0分(-1)、克罗地亚0分(-2)。双方拿到4分都可接受，英格兰没有必须持续压深的积分压力。",
    "周二047": "L组同上。巴拿马与克罗地亚均0分，克罗地亚必须拿分，落后方后段会主动增加人数，比赛尾段的开放和反击风险高。",
    "周二048": "K组同上。哥伦比亚取胜将到6分并锁定前二；刚果(金)首轮逼平葡萄牙，平局即可带着2分进入末轮，低位防守动机充分。",
}

CORE = {
    "周二045": ("葡萄牙胜", "葡萄牙-2让负，防让平", "2-4球；3/4球核心，保留5球"),
    "周二046": ("英格兰胜", "英格兰-2让负，防让平", "2-4球；2/3球核心"),
    "周二047": ("克罗地亚胜，降低串关权重", "巴拿马+1让胜/让负双防，回避单挑", "2-4球；3球核心"),
    "周二048": ("哥伦比亚胜，防平", "哥伦比亚-1让负", "1-3球；1/2球核心"),
}

SCORES = {
    "周二045": (["2-0", "1-0", "3-0"], ["2-0", "3-0", "3-1"], ["1-1", "2-2"]),
    "周二046": (["2-0", "1-0", "3-0"], ["2-0", "3-0", "3-1"], ["1-1", "2-2"]),
    "周二047": (["1-2", "0-1", "0-2"], ["0-1", "0-2", "0-3"], ["1-0", "2-2"]),
    "周二048": (["1-0", "2-0", "0-0"], ["1-0", "2-0", "3-0"], ["0-1", "2-2"]),
}

OPTA_FACT = {
    "周二045": "Opta同时指出乌兹别克首轮1.16 xG，是2010年以来世界杯首秀球队的最高值，葡萄牙深盘不能只看名气。",
    "周二046": "Opta给英格兰明显优势；但双方均3分，积分层不支持把英格兰胜面机械等同于净胜三球。",
    "周二047": "Opta给克罗地亚63.0%胜率，同时巴拿马世界杯四战全负；方向一致，但克罗地亚首轮已失4球。",
    "周二048": "Opta记录刚果(金)对葡萄牙仅24.6%控球，却只让对手完成7次射门，低位防守质量是真实证据。",
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def score_map(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def fmt_scores(match: dict, labels: list[str]) -> str:
    values = score_map(match)
    return " / ".join(f"{label}({pct(values.get(label, 0.0))})" for label in labels)


def total_top(match: dict) -> str:
    values = sorted(match["final"]["total_distribution"].items(), key=lambda item: item[1], reverse=True)[:3]
    return " / ".join(f"{key.replace('_plus', '+')}球 {pct(value)}" for key, value in values)


def market_line(item: dict) -> str:
    current = item["current"]
    deep = item["deep_market"]
    ox = current["one_x_two"]
    one = "竞彩未开售；百家" + "/".join(f"{v:.2f}" for v in deep["ouzhi"]["current"]) if not ox else f"竞彩{ox['3']:.2f}/{ox['1']:.2f}/{ox['0']:.2f}"
    h = current["handicap_three_way"]
    return (
        f"{one}；主队{current['handicap']:+.0f}为{h['3']:.2f}/{h['1']:.2f}/{h['0']:.2f}；"
        f"亚洲均线{deep['yazhi']['opening'][1]:+.3f}→{deep['yazhi']['current'][1]:+.3f}；"
        f"大小均线{deep['daxiao']['opening'][1]:.2f}→{deep['daxiao']['current'][1]:.2f}"
    )


def build_table(matches: list[dict]) -> str:
    lines = [
        "# 2026-06-24 世界杯周二045-048 推荐总表", "",
        "> 数据截点：500、API、天气与Opta截至2026-06-23 23:11，Polymarket截至23:14（Asia/Hong_Kong）。概率已完成三类市场去水、一次性多源融合、proxy xG、LEG和决策迭代。", "",
        "| 场次 | 胜/平/负 | 核心推荐 | 让球胜/平/负 | 让球推荐 | 总球Top3 | 概率Top3 | 铁律Top3 | 冷门低位/高位 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result, handicap = match["final"]["result"], match["final"]["handicap_home_settlement"]
        probability, iron, cold = SCORES[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | {pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])} | "
            f"**{CORE[code][0]}** | {pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])} | **{CORE[code][1]}** | "
            f"{total_top(match)} | {fmt_scores(match, probability)} | **{fmt_scores(match, iron)}** | {fmt_scores(match, cold)} |"
        )
    lines += [
        "", "让球概率按主队所列竞彩让球结算。铁律Top3的第三位承担赢深上沿，不是纯概率排序。", "",
        "## 混合过关", "",
        "| 类型 | 组合 | 定位 |", "|---|---|---|",
        "| 2串1主线 | 葡萄牙胜 × 英格兰胜 | 两个最强赛果方向，不碰-2深度 |",
        "| 2串1替代 | 克罗地亚胜 × 哥伦比亚-1让负 | 克罗地亚有波动，哥伦比亚用让球保护 |",
        "| 3串1 | 葡萄牙胜 × 英格兰胜 × 哥伦比亚-1让负 | 相对均衡的三场组合 |",
        "| 4串1 | 葡萄牙胜 × 英格兰-2让负 × 克罗地亚胜 × 哥伦比亚-1让负 | 高波动，仅小权重 |",
        "", "## 比分过关", "",
        "- 2串1：葡萄牙 2-0/3-0 × 英格兰 2-0/3-0。",
        "- 3串1：再加入哥伦比亚 1-0/2-0。",
        "- 4串1：再加入克罗地亚 0-1/0-2；该场分布最散。",
        "", "> 风险提示：过关腿数增加会快速压低命中概率；正式首发或盘口跨档时必须重算。",
    ]
    return "\n".join(lines) + "\n"


def build_report(model: dict, source: dict, api: dict, market: dict, weather: dict, online: dict) -> str:
    matches = model["matches"]
    lines = [
        "# 2026-06-24 世界杯周二045-048 严格分析与GPT联网复核报告", "",
        "> 数据截点：用户PDF 2026-06-23 17:19；500、API、天气与Opta于23:11重新获取，Polymarket于23:14刷新（Asia/Hong_Kong）。", "",
        "## 一、步骤审计", "",
        f"- 用户附件：{len(source['pdfs'])}份PDF已实际抽取并逐页渲染核验；本次没有XLS附件。",
        "- 500主表：让球三向、比分、总进球、半全场全部读取；045、046普通竞彩三向未开售，以百家即时均值降权替代。",
        f"- 500深盘：四场欧赔、亚洲盘、大小盘共12页重新抓取，错误{len(market['errors'])}；四场数据分析页同步读取。",
        "- Polymarket：四场活跃胜平负合约均已通过Gamma API刷新；事件流动性约297万至653万美元，三项买卖价差均约1美分。",
        "- 多源权重：Poisson、500、Opta和Polymarket一次性融合；Polymarket按流动性、成交量和价差评分并施加0.75相关性折扣，实际归一化权重约7.2%-8.9%。",
        "- 基本面：FIFA排名、K/L组积分、首轮赛果、近10场、未来赛程和预计阵容已读取。",
        "- API-Football：四场fixture、prediction、odds有结果；injuries、lineups、statistics均0行。异常或空白prediction不输入模型。",
        "- 天气：Open-Meteo按场馆当地开球小时抓取；休斯敦高温、福克斯堡小雨、瓜达拉哈拉高湿小雨进入G层。",
        "- 模型：Poisson/Dixon-Coles、三类市场去水、一次性多源融合、proxy xG、LEG、历史校准、决策迭代、一致性检查均完成。",
        "- Opta/GPT：Opta 25,000次模拟以约15.4%-19.3%实际权重进入赛果层；GPT联网复核保持0%直接概率权重，只回写可验证事实并触发重算。",
        "- 奇门：已运行，仅作低权重冲突提示，不覆盖数学模型。",
        "- 未完成项：真实赛前xG/xGA、官方最终首发与完整官方伤停尚不可得，已降权，未用预计阵容冒充确认。",
        "", "### 23:11临场变化", "",
        "- 葡萄牙-2让胜由1.94降至1.88，亚洲均线维持-2.25，总球均线维持3.29；赢深信号增强但仍未超过让负概率。",
        "- 英格兰-2让胜由2.20降至2.14，亚洲均线约-1.97升至-2.03，总球约2.93升至2.99；2-0和3-0权重同步提高。",
        "- 巴拿马亚洲受让由约+1.00走到+1.17，竞彩+1让负由2.11降至2.05；克罗地亚赢两球以上的市场支持增强，但模型让球三向仍有冲突。",
        "- 哥伦比亚亚洲均线维持约-1.03、总球维持2.29；让平价格从3.25降至3.10，一球小胜卡线风险提高。",
        "- API-Football在23:11复查四场injuries、lineups、statistics仍均为0行，正式首发尚未确认。",
        "", "## 二、小组积分形势", "",
        "世界杯每组前二及8个最佳第三名进入32强。第二轮的核心不是只看当前名次，而是区分‘必须赢并争净胜球’、‘平局可接受’和‘落后后段必须压上’三种节奏。", "",
    ]
    lines += [f"- **{m['identity']['code']}**：{GROUP[m['identity']['code']]}" for m in matches]
    lines += [
        "", "## 三、推荐总览", "",
        "| 场次 | 胜/平/负 | 让球胜/平/负 | 最终总球均值 | LEG修正进球 | L/E/G | 深度差 | 核心 |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for match in matches:
        code, result, handicap, leg = match["identity"]["code"], match["final"]["result"], match["final"]["handicap_home_settlement"], match["leg"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | {pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | {match['means']['decision_final']:.3f} | "
            f"{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f} | {leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f} | "
            f"{leg['depth_gap_10']:.1f} | **{CORE[code][0]}；{CORE[code][1]}** |"
        )
    lines += ["", "## 四、逐场分析"]
    for match in matches:
        code, identity = match["identity"]["code"], match["identity"]
        result, handicap, leg, proxy = match["final"]["result"], match["final"]["handicap_home_settlement"], match["leg"], match["xg"]["proxy"]
        probability, iron, cold = SCORES[code]
        opta = online["matches"][code]["opta"]
        multi = match["fusion"]["multi_source_result"]
        source_weights = multi["sources"]
        lines += [
            "", f"### {code} {identity['home']} vs {identity['away']}", "",
            f"- **积分动机**：{GROUP[code]}",
            f"- **实力近况**：FIFA {match['source_facts']['fifa_rank']['home']} vs {match['source_facts']['fifa_rank']['away']}；近10场进失球 {match['source_facts']['recent_10']['home']['goals_for']}-{match['source_facts']['recent_10']['home']['goals_against']} vs {match['source_facts']['recent_10']['away']['goals_for']}-{match['source_facts']['recent_10']['away']['goals_against']}；首轮{identity['first_round']}。",
            f"- **情报环境**：{match['source_facts']['absence_note']}。{match['source_facts']['weather']}。",
            f"- **市场变化**：{market_line(market['matches'][code])}。",
            f"- **一次性多源融合**：实际权重Poisson {pct(source_weights['poisson']['normalized_weight'])}、500 {pct(source_weights['500']['normalized_weight'])}、Opta {pct(source_weights['opta']['normalized_weight'])}、Polymarket {pct(source_weights['polymarket']['normalized_weight'])}；多源后验{pct(multi['posterior_probabilities']['home'])}/{pct(multi['posterior_probabilities']['draw'])}/{pct(multi['posterior_probabilities']['away'])}，可靠度{multi['reliability']}。",
            f"- **市场质量控制**：500去水{pct(match['market']['one_x_two']['probabilities']['home'])}/{pct(match['market']['one_x_two']['probabilities']['draw'])}/{pct(match['market']['one_x_two']['probabilities']['away'])}；Polymarket归一化{pct(source_weights['polymarket']['probabilities']['home'])}/{pct(source_weights['polymarket']['probabilities']['draw'])}/{pct(source_weights['polymarket']['probabilities']['away'])}，质量{source_weights['polymarket']['quality']:.2f}、相关性折扣{source_weights['polymarket']['correlation_discount']:.2f}。",
            f"- **xG与总球去偏**：真实xG缺失；proxy xG {proxy['home_xg']:.3f}-{proxy['away_xg']:.3f}，双方样本可靠度均{proxy['components']['team_rates']['home_sample_reliability']:.2f}。独立均值{match['means']['poisson_contextual']:.3f}，500精确总球均值{match['means']['market_exact']:.3f}，融合{match['means']['final_fused']:.3f}，决策最终{match['means']['decision_final']:.3f}。",
            f"- **LEG**：修正进球{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f}；L/E/G为{leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f}，综合{leg['total_score']*10:.1f}/10，强弱差{leg['depth_gap_10']:.1f}；{leg['depth_direction']}。",
            f"- **最终赛果**：**{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])}**；{CORE[code][0]}。",
            f"- **让球**：**{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])}**；{CORE[code][1]}。",
            f"- **总进球**：{CORE[code][2]}；Top3为{total_top(match)}。",
            f"- **比分**：概率Top3 {fmt_scores(match, probability)}；铁律Top3 **{fmt_scores(match, iron)}**；冷门低位/高位 {fmt_scores(match, cold)}。",
            f"- **决策迭代**：调整前{pct(match['decision_iteration']['before_result']['home'])}/{pct(match['decision_iteration']['before_result']['draw'])}/{pct(match['decision_iteration']['before_result']['away'])}，调整后{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}；触发{'、'.join(match['decision_iteration']['applied_rules'])}。",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings']) or '无冲突警告'}。",
            f"- **奇门**：{match['qimen']['qimen_result_prediction']}，置信{match['qimen']['confidence']}；不覆盖模型。",
            f"- **Opta/GPT复核**：Opta 25,000次模拟为{pct(opta['home'])}/{pct(opta['draw'])}/{pct(opta['away'])}，已按{pct(source_weights['opta']['normalized_weight'])}进入赛果融合；GPT直接概率权重为0%。{OPTA_FACT[code]}",
        ]
    lines += [
        "", "## 五、组合建议", "",
        "- 2串1主线：葡萄牙胜 × 英格兰胜。",
        "- 2串1替代：克罗地亚胜 × 哥伦比亚-1让负。",
        "- 3串1：葡萄牙胜 × 英格兰胜 × 哥伦比亚-1让负。",
        "- 4串1：葡萄牙胜 × 英格兰-2让负 × 克罗地亚胜 × 哥伦比亚-1让负；只作高波动覆盖。",
        "- 比分2串1：葡萄牙2-0/3-0 × 英格兰2-0/3-0。",
        "- 比分3串1：再加入哥伦比亚1-0/2-0。",
        "- 比分4串1：再加入克罗地亚0-1/0-2；该场分布最散。",
        "", "## 六、联网复核来源", "",
        "- [500竞彩足球实时主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [Opta：葡萄牙vs乌兹别克斯坦](https://theanalyst.com/articles/portugal-vs-uzbekistan-prediction-world-cup-2026)",
        "- [Opta：英格兰vs加纳](https://theanalyst.com/articles/england-vs-ghana-prediction-world-cup-2026)",
        "- [Opta：巴拿马vs克罗地亚](https://theanalyst.com/articles/panama-vs-croatia-prediction-world-cup-2026)",
        "- [Opta：哥伦比亚vs刚果(金)](https://theanalyst.com/articles/colombia-vs-dr-congo-prediction-world-cup-2026)",
        "- [Open-Meteo天气API](https://open-meteo.com/en/docs)",
        "- [Polymarket：葡萄牙vs乌兹别克斯坦](https://polymarket.com/event/fifwc-prt-uzb-2026-06-23)",
        "- [Polymarket：英格兰vs加纳](https://polymarket.com/event/fifwc-eng-gha-2026-06-23)",
        "- [Polymarket：巴拿马vs克罗地亚](https://polymarket.com/event/fifwc-pan-hrv-2026-06-23)",
        "- [Polymarket：哥伦比亚vs刚果(金)](https://polymarket.com/event/fifwc-col-cdr-2026-06-23)",
        "", "## 七、最终判断", "",
        "1. 葡萄牙和英格兰是最强赛果方向，但两场-2让胜都只有约32%，优先普通胜，不追净胜三球。",
        "2. 葡萄牙必须修复积分和净胜球，盘面也升至约-2.25；因此比分保留3-0/3-1上沿，但1-0/2-0仍是概率核心。",
        "3. 英格兰与加纳同为3分，平局对双方可接受；英格兰胜面高，深度却比葡萄牙更应克制。",
        "4. 克罗地亚胜是方向，不是稳胆；双方均0分会放大后段波动，受让三向出现模型与市场冲突，串关降权。",
        "5. 哥伦比亚面对十场不败、仅失2球的刚果(金)，且主胜欧赔均值由1.47漂至1.53；主胜可用，-1让负更稳，防1-1。",
        "", "> 风险提示：以上是当前截点的概率估计，不是赛果保证。正式首发、屋顶状态、临场伤停或盘口跨档均可能改变结论。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    source = json.loads((BASE / "source_extract_summary.json").read_text(encoding="utf-8"))
    api = json.loads((BASE / "api/api_audit.json").read_text(encoding="utf-8"))
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    weather = json.loads((BASE / "weather/weather_audit.json").read_text(encoding="utf-8"))
    online = json.loads((BASE / "online_review_sources.json").read_text(encoding="utf-8"))
    OUT.write_text(build_report(model, source, api, market, weather, online), encoding="utf-8")
    TABLE_OUT.write_text(build_table(model["matches"]), encoding="utf-8")
    print(json.dumps({"report": str(OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
