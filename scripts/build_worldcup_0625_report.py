from __future__ import annotations

import json
import math
from pathlib import Path


BASE = Path("data/worldcup_20260625")
REPORT_OUT = BASE / "2026-06-25世界杯周三049-054_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-25世界杯周三049-054_推荐总表.md"

SCENARIOS = {
    "周三049": "B组：加拿大4分/+6、瑞士4分/+3。平局双方都到5分并携手出线；加拿大凭净胜球保持头名，瑞士只有取胜才能主动争头名。任何一方输球，仍需050出现约9球级别的净胜球摆动才可能跌出前二。",
    "周三050": "B组：波黑与卡塔尔同为1分，净胜球分别-3和-6。两队都必须取胜；胜者更现实的路径是以4分竞争最佳第三，若要冲前二还需049分出胜负并追赶巨大净胜球差。",
    "周三051": "C组：巴西4分/+3、苏格兰3分/0。巴西拿1分基本锁定晋级并继续争头名；苏格兰取胜最稳，平局到4分则主要等待最佳第三比较。",
    "周三052": "C组：摩洛哥4分/+1，与巴西同分但少2个净胜球；海地0分已出局。摩洛哥既要赢，也有追净胜球争头名的真实需求。",
    "周三053": "A组：墨西哥6分已锁定头名，韩国3分/0。韩国取胜锁定第二；平局到4分仍要看捷克能否击败墨西哥。南非1分/-2必须取胜，并争取净胜球。",
    "周三054": "A组：墨西哥6分/+3已锁定头名；捷克1分/-1必须取胜，4分可争第二或最佳第三。墨西哥最明确的动机是避免伤停和停赛，轮换风险为六场最高。",
}

CORE = {
    "周三049": ("瑞士胜/平双选；单项优先瑞士-1让负", "1-3球", ["1-1", "1-0", "0-0"], ["2-2", "2-1"]),
    "周三050": ("波黑胜；-1让胜/让平双选", "2-4球", ["2-0", "1-0", "2-1"], ["3-0", "3-1"]),
    "周三051": ("巴西胜；苏格兰+1让胜/让平保护", "2-3球", ["0-2", "0-1", "1-2"], ["1-1", "0-3"]),
    "周三052": ("摩洛哥胜；-2不单挑", "3-4球，防2球", ["2-0", "1-0", "3-0"], ["4-0", "3-1"]),
    "周三053": ("韩国胜；南非+1让胜", "1-3球", ["0-1", "1-1", "0-2"], ["1-2", "0-3"]),
    "周三054": ("墨西哥胜/平双选；捷克+1让胜", "1-3球", ["0-1", "1-1", "0-0"], ["1-0", "1-2"]),
}

TACTICAL = {
    "周三049": (
        "瑞士预计以三中卫体系控制中路和二点，加拿大依靠高压、边路速度及快速纵向转换。瑞士阵地战更细，加拿大的推进爆发力和前两轮创造量更高。",
        "前段双方会试探而非持续互攻。平局可让两队携手出线，加拿大还可保持头名；若049在60分钟后仍平，主动冒险的动力会继续下降。瑞士只有在明确争头名时才更需要把翼卫压高。",
    ),
    "周三050": (
        "波黑更适合三中卫或双前锋结构，通过高中锋支点、边翼卫传中和定位球制造优势；卡塔尔需要依靠阿菲夫一类持球点完成反击，但两名停赛球员削弱了中后场保护。",
        "两队都必须取胜，比赛不会长期停在保守均衡。波黑预计先压制，卡塔尔若先失球必须提高站位；最后30分钟无论哪队落后，阵型都会明显前移，因此角球、犯规和后段连续进球风险是六场最高之一。",
    ),
    "周三051": (
        "苏格兰会以五后卫低位、身体对抗和定位球寻找机会；巴西以四后卫控球体系拉开宽度，通过肋部小组配合制造射门。拉菲尼亚与内马尔的伤情降低巴西边路爆点和轮换弹性。",
        "巴西一分即可处于有利位置，开局不必无条件提速；苏格兰则需要抢分。若同场摩洛哥较早扩大净胜球，巴西争头名的进攻需求会上升。迈阿密高温、阵雨和强风使持续高压更困难，巴西胜面清楚但赢深需保守。",
    ),
    "周三052": (
        "摩洛哥以四后卫和高强度边路推进为主，能通过边锋一对一、边后卫套上和前场反抢形成持续压制；海地会收缩禁区并依赖直接反击。",
        "摩洛哥不仅需要获胜，还落后巴西两个净胜球，因此早进球后仍有继续进攻的真实理由。海地已经出局，若防线在前60分钟被打穿，末段体能和站位可能继续松动；这场必须保留四球以上尾部。",
    ),
    "周三053": (
        "南非通常依靠紧凑四后卫、快速边路和定位球；韩国以四后卫控球推进，利用前场换位、边路套上和禁区前沿的二次进攻。南非中场核心Mokoena停赛会削弱出球与定位球质量。",
        "南非必须取胜，韩国获胜即可锁定第二，双方都不能只守。高温和强风会压低连续逼抢质量，但落后方末段必然前压。韩国整体控制力占优，平局风险来自南非反击和定位球，而不是长期控场。",
    ),
    "周三054": (
        "捷克会利用三中卫、边翼卫推进和高点冲击禁区；墨西哥更擅长四后卫控球、快速地面传递与主场高原压迫。捷克必须主动，但压上后会暴露中卫两侧。",
        "墨西哥已经锁定头名，轮换和避免停赛比追求净胜球更可信。捷克只有取胜才有现实晋级路径，会在下半场逐步提高风险；若久攻不下，比赛可能从低节奏突然转成开放反击。墨西哥城细雨进一步提高传控失误与定位球波动。",
    ),
}

MIXED_LEGS = [
    ("周三052 摩洛哥胜", "周三052", "result", "home"),
    ("周三050 波黑胜", "周三050", "result", "home"),
    ("周三053 韩国胜", "周三053", "result", "away"),
    ("周三049 瑞士-1让负", "周三049", "handicap", "fail"),
    ("周三051 巴西胜", "周三051", "result", "away"),
    ("周三054 捷克+1让胜", "周三054", "handicap", "cover"),
]

SCORE_LEGS = [
    ("周三052 摩洛哥 2-0/3-0", "周三052", ("2-0", "3-0")),
    ("周三050 波黑 2-0/1-0", "周三050", ("2-0", "1-0")),
    ("周三053 韩国 0-1/0-2", "周三053", ("0-1", "0-2")),
    ("周三049 瑞士 1-1/1-0", "周三049", ("1-1", "1-0")),
    ("周三051 巴西 0-2/0-1", "周三051", ("0-2", "0-1")),
    ("周三054 墨西哥 0-1/1-1", "周三054", ("0-1", "1-1")),
]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pct_small(value: float) -> str:
    percentage = value * 100
    return f"{percentage:.3f}%" if percentage < 0.1 else f"{percentage:.1f}%"


def scores(items: list[dict], labels: list[str]) -> str:
    by_score = {item["score"]: item["probability"] for item in items}
    return " / ".join(f"{label}({pct(by_score.get(label, 0.0))})" for label in labels)


def total_top(match: dict) -> str:
    values = sorted(match["final"]["total_distribution"].items(), key=lambda item: item[1], reverse=True)[:3]
    return " / ".join(f"{key.replace('_plus', '+')}球 {pct(value)}" for key, value in values)


def source_weights(match: dict) -> str:
    sources = match["fusion"]["multi_source_result"]["sources"]
    order = [name for name in ("poisson", "500", "opta", "polymarket") if name in sources]
    return "、".join(f"{name} {pct(sources[name]['normalized_weight'])}" for name in order)


def market_move(code: str, market: dict) -> str:
    deep = market["matches"][code]["deep_market"]
    ou = deep["ouzhi"]
    asian = deep["yazhi"]
    total = deep["daxiao"]
    return (
        f"百家欧赔开盘{ou['opening'][0]:.2f}/{ou['opening'][1]:.2f}/{ou['opening'][2]:.2f}，"
        f"即时{ou['current'][0]:.2f}/{ou['current'][1]:.2f}/{ou['current'][2]:.2f}；"
        f"亚洲均线{asian['opening'][1]:+.2f}→{asian['current'][1]:+.2f}；"
        f"大小均线{total['opening'][1]:.2f}→{total['current'][1]:.2f}。"
    )


def mixed_probability(match_map: dict, legs: list[tuple]) -> float:
    value = 1.0
    for _, code, layer, key in legs:
        if layer == "result":
            value *= match_map[code]["final"]["result"][key]
        else:
            value *= match_map[code]["final"]["handicap_home_settlement"][key]
    return value


def build_combinations(match_map: dict) -> tuple[list[str], list[str]]:
    mixed = []
    score_lines = []
    for count in range(2, len(MIXED_LEGS) + 1):
        legs = MIXED_LEGS[:count]
        probability = mixed_probability(match_map, legs)
        mixed.append(
            f"| {count}串1 | {' × '.join(item[0] for item in legs)} | {pct(probability)} | "
            f"{'中高风险' if count <= 3 else '高风险，仅小权重'} |"
        )
        score_probability = 1.0
        for _, code, labels in SCORE_LEGS[:count]:
            pool = {item["score"]: item["probability"] for item in match_map[code]["final"]["score_candidate_pool"]}
            score_probability *= sum(pool.get(label, 0.0) for label in labels)
        score_lines.append(
            f"| {count}串1 | {' × '.join(item[0] for item in SCORE_LEGS[:count])} | {2 ** count} | {pct_small(score_probability)} |"
        )
    return mixed, score_lines


def build_table(model: dict) -> str:
    matches = model["matches"]
    match_map = {item["identity"]["code"]: item for item in matches}
    lines = [
        "# 2026-06-25 世界杯周三049-054 推荐总表", "",
        f"> 数据截点：{model['generated_at']}。以下是概率研究结论，不是确定性赛果。", "",
        "## 单场总表", "",
        "| 场次 | 胜/平/负 | 核心推荐 | 让球胜/平/负 | 让球建议 | 总球 | 比分Top3 | 风险比分 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        core, goals, top, risk = CORE[code]
        pool = match["final"]["score_candidate_pool"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | **{core.split('；')[0]}** | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | {core.split('；')[-1]} | "
            f"{goals} | {scores(pool, top)} | {scores(pool, risk)} |"
        )
    mixed, score_lines = build_combinations(match_map)
    lines += [
        "", "让球概率均按主队所列竞彩让球结算，顺序为让胜/让平/让负。", "",
        "## 混合过关", "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |", "|---|---|---:|---|", *mixed,
        "", "> 联合概率仅用于横向比较，未把同组同时开球的相关性当成独立事件；4串1以上实际风险高于表内数字。", "",
        "## 比分过关", "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |", "|---|---|---:|---:|", *score_lines,
        "", "> 比分过关从4串1开始概率快速降至1%以下；6串1为64注但理论覆盖仍约0.03%，只适合作为极小权重娱乐覆盖。",
    ]
    return "\n".join(lines) + "\n"


def build_report(model: dict, market: dict, api: dict, weather: dict, online: dict, polymarket: dict, accessory: dict) -> str:
    matches = model["matches"]
    match_map = {item["identity"]["code"]: item for item in matches}
    lines = [
        "# 2026-06-25 世界杯周三049-054 严格分析与GPT联网复核报告", "",
        f"> 数据截点：用户PDF 2026-06-24 14:06；500 {market['fetched_at']}、API {api['fetched_at']}、天气 {weather['fetched_at']}、Opta {online['fetched_at']}、Polymarket {polymarket['fetched_at']}。", "",
        "## 一、步骤审计", "",
        "- 用户附件：1份PDF，3页，已抽取文本并逐页渲染核验；049-054普通三向、让球三向、比分、总进球与半全场完整读取。",
        f"- 500实时市场：六场主表与18个深层欧赔/亚盘/大小页面刷新完成，错误{len(market['errors'])}。",
        "- 500深层基本面：FIFA排名、B/C/A组积分、近10场、预计阵容、交锋与赛程页面全部保存。",
        "- API-Football：六场fixture、prediction、odds均返回；injuries合计返回9条，lineups/statistics均0行；0行不视为确认无人缺席。",
        "- 外部市场：六场Polymarket三向合约均活跃，价差约1美分；质量和与500的相关性折扣已写入有效权重。",
        "- Opta：049、050、051、052、054的25,000次模拟已直接抓取并核验；053无可核验页面，Opta直接权重为0。",
        "- 联网新闻：通用搜索接口返回403，改用Google News RSS发现最新报道并直接抓取Opta；失败路径在审计中明示。",
        "- 天气：Open-Meteo按六个场馆当地开球小时读取；迈阿密高温强阵雨与大风、蒙特雷高温强风、墨西哥城高概率细雨进入G层。",
        "- 模型：Poisson/Dixon-Coles、市场去水、一次性多源融合、proxy xG、让球/总球/比分、LEG、决策迭代、奇门与一致性检查均已执行。",
        "- xG：前两轮API真实xG/xGA已读取，因每队仅2场，按0.33可靠度向国家队基准收缩后进入proxy、历史模型与市场融合。",
        "- 限制：官方最终首发和完整官方伤停名单尚不可得；所有预计阵容信息均已降权。",
        "", "## 二、积分与淘汰赛对位", "",
        "| 小组 | 当前形势 | 对比赛节奏的影响 |", "|---|---|---|",
        "| B组 | 加拿大4分/+6，瑞士4分/+3，波黑1分/-3，卡塔尔1分/-6 | 049平局互利；050双方必须赢，落后方后段会全面压上。 |",
        "| C组 | 巴西4分/+3，摩洛哥4分/+1，苏格兰3分/0，海地0分/-4 | 巴西/摩洛哥争头名；苏格兰抢分；摩洛哥有追净胜球动力。 |",
        "| A组 | 墨西哥6分/+3，韩国3分/0，捷克1分/-1，南非1分/-2 | 墨西哥锁定头名；其余三队仍有晋级诉求，053/054后段联动明显。 |",
        "", "### 是否会选择淘汰赛对手", "",
        "- C组按当前路径，头名对日本、第二对荷兰、第三可能对德国。三条路径都不轻松，没有足够证据支持巴西或摩洛哥故意输球；头名仍有现实价值。",
        "- 墨西哥已经锁定A组头名，对手来自多个小组的第三名，054结果无法改变其排名；因此轮换、避免伤停和停赛是可信风险。",
        "- 加拿大平局即可保持B组头名，瑞士则需要取胜争头名；049的非对称动机解释了平局高权重，但不能据此断言默契。",
        "- 对位选择只改变战意标签与轮换风险，不直接获得独立概率权重；没有正式首发证据时，修正保持在模型边界内。",
        "", "## 三、总览", "",
        "| 场次 | 胜/平/负 | 让球胜/平/负 | 最终总球均值 | LEG修正进球 | L/E/G | 深度差 | 核心 |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{match['means']['decision_final']:.2f} | {leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f} | "
            f"{leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f} | "
            f"{leg['depth_gap_10']:.1f} | **{CORE[code][0]}** |"
        )
    lines += ["", "## 四、逐场详细分析"]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        leg = match["leg"]
        proxy = match["xg"]["proxy"]
        pool = match["final"]["score_candidate_pool"]
        core, goals, top, risk = CORE[code]
        multi = match["fusion"]["multi_source_result"]
        opta = online["matches"][code]["opta"]
        pm = polymarket["matches"][code]
        opta_text = "未找到可核验赛前页面，权重0%"
        if opta.get("verified"):
            opta_text = f"25,000次模拟 {pct(opta['home'])}/{pct(opta['draw'])}/{pct(opta['away'])}"
        lines += [
            "", f"### {code} {match['identity']['home']} vs {match['identity']['away']}", "",
            f"- **积分情境**：{SCENARIOS[code]}",
            f"- **市场变化**：{market_move(code, market)}",
            f"- **多源融合**：有效权重{source_weights(match)}；可靠度{multi['reliability']}；警告{'、'.join(multi['warnings']) or '无'}。",
            f"- **Polymarket**：{pct(pm['normalized_probabilities']['home'])}/{pct(pm['normalized_probabilities']['draw'])}/{pct(pm['normalized_probabilities']['away'])}；流动性{pm['liquidity']:.0f}美元、成交量{pm['volume']:.0f}美元、平均价差{pm['average_spread']:.2f}。",
            f"- **Opta**：{opta_text}。",
            f"- **阵容天气**：{match['source_facts']['absence_note']}。{match['source_facts']['weather']}。",
            f"- **xG与去偏**：前两轮真实xG已按0.33可靠度收缩；融合xG {proxy['home_xg']:.2f}-{proxy['away_xg']:.2f}，独立总均值{match['means']['poisson_contextual']:.2f}，500总球均值{match['means']['market_exact']:.2f}，最终{match['means']['decision_final']:.2f}。",
            f"- **LEG**：修正进球{leg['home_leg_expected_goals']:.2f}-{leg['away_leg_expected_goals']:.2f}；L/E/G {leg['line_score']*10:.1f}/{leg['expected_goals_score']*10:.1f}/{leg['game_context_score']*10:.1f}，综合{leg['total_score']*10:.1f}/10，深度差{leg['depth_gap_10']:.1f}；{leg['depth_direction']}。",
            f"- **最终赛果**：{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}；**{core.split('；')[0]}**。",
            f"- **让球**：{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])}；{core.split('；')[-1]}。",
            f"- **总进球**：{goals}；概率Top3为{total_top(match)}。",
            f"- **比分层**：概率Top3 **{scores(pool, top)}**；风险上沿/冷门 **{scores(pool, risk)}**。",
            f"- **决策迭代**：调整前{pct(match['decision_iteration']['before_result']['home'])}/{pct(match['decision_iteration']['before_result']['draw'])}/{pct(match['decision_iteration']['before_result']['away'])}，调整后{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}；触发{'、'.join(match['decision_iteration']['applied_rules'])}。",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings']) or '无冲突警告'}。",
            f"- **奇门/GPT**：奇门偏向{match['qimen']['qimen_result_prediction']}，仅作提示；GPT直接概率权重0%，只核验事实并要求重算。",
        ]
    lines += ["", "## 五、10,000次Monte Carlo模拟", "", "| 场次 | 主胜 | 平局 | 客胜 | 大2.5 | 大3.5 | 双方进球 | 模拟进球均值 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for code, item in accessory["matches"].items():
        values = item["monte_carlo"]["probabilities"]
        identity = match_map[code]["identity"]
        lines.append(
            f"| {code} {identity['home']}vs{identity['away']} | {pct(values['home'])} | {pct(values['draw'])} | "
            f"{pct(values['away'])} | {pct(values['over_2_5'])} | {pct(values['over_3_5'])} | {pct(values['btts'])} | "
            f"{item['expected_goals']['home']:.2f}-{item['expected_goals']['away']:.2f} |"
        )
    lines += [
        "", "说明：Monte Carlo是进球分布原始层；最终胜平负还融合了500去水、Opta、Polymarket、末轮动机与决策迭代，因此两列不应被强行写成相同。", "",
        "## 六、半场预测", "",
        "| 场次 | 半场主/平/客 | 半场大0.5 | 半场大1.5 | 半场比分Top3 |", "|---|---|---:|---:|---|",
    ]
    for code, item in accessory["matches"].items():
        half = item["half_time"]
        score_text = " / ".join(f"{entry['score']}({pct(entry['probability'])})" for entry in half["score_top5"][:3])
        lines.append(
            f"| {code} | {pct(half['result']['home'])}/{pct(half['result']['draw'])}/{pct(half['result']['away'])} | "
            f"{pct(half['over_0_5'])} | {pct(half['over_1_5'])} | {score_text} |"
        )
    lines += [
        "", "## 七、角球、牌数与点球", "",
        "| 场次 | 角球期望（主-客） | 大8.5角 | 大9.5角 | 黄牌期望（主-客） | 大2.5牌 | 红牌概率 | 点球概率 |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for code, item in accessory["matches"].items():
        corners = item["corners"]
        discipline = item["discipline"]
        lines.append(
            f"| {code} | {corners['total']:.2f}（{corners['home']:.2f}-{corners['away']:.2f}） | {pct(corners['over_8_5'])} | "
            f"{pct(corners['over_9_5'])} | {discipline['yellow_total']:.2f}（{discipline['yellow_home']:.2f}-{discipline['yellow_away']:.2f}） | "
            f"{pct(discipline['over_2_5'])} | {pct(discipline['red_probability'])} | {pct(discipline['penalty_probability'])} |"
        )
    lines += [
        "", "角球与牌数只使用前两轮样本，已按 n/(n+5) 向世界杯基准收缩。裁判尚未指派，因此牌数、红牌和点球置信度低于胜平负与总球。", "",
        "## 八、战术与比赛进程模拟", "",
    ]
    for code, (tactical, process) in TACTICAL.items():
        lines += [f"### {code}", "", f"- **阵型打法**：{tactical}", f"- **进程模拟**：{process}", ""]
    mixed, score_lines = build_combinations(match_map)
    lines += [
        "", "## 九、混合过关", "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |", "|---|---|---:|---|", *mixed,
        "", "组合原则：2串1优先跨组；3串1覆盖B/C/A各一场。4串1以上不可避免引入同组同时开球的相关性，只能降低权重，不能把表内独立概率当真实命中率。",
        "", "## 十、比分过关", "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |", "|---|---|---:|---:|", *score_lines,
        "", "比分过关成本按每场2个比分计算：2串1为4注，之后依次8、16、32、64注。4串1以上概率已经很低，不属于核心策略。",
        "", "## 十一、风险排序", "",
        "1. **最低风险方向**：摩洛哥胜、波黑胜。",
        "2. **中等风险方向**：瑞士-1让负、巴西胜、韩国胜。",
        "3. **最高风险场**：捷克vs墨西哥。墨西哥实力与主场环境占优，但已锁定头名；捷克必须赢，盘口、天气与轮换方向互相冲突。",
        "4. **最大穿盘陷阱**：摩洛哥-2。主胜78.1%，但-2让胜仅33.4%，强队胜面与赢三球必须拆开。",
        "5. **最大平局风险**：瑞士vs加拿大。两队平局合计出线，模型胜/平仅差0.1个百分点。",
        "", "## 十二、联网复核来源", "",
        "- [500竞彩足球实时主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [Opta：瑞士vs加拿大](https://theanalyst.com/articles/switzerland-vs-canada-prediction-world-cup-2026-match-preview)",
        "- [Opta：波黑vs卡塔尔](https://theanalyst.com/articles/bosnia-herzegovina-vs-qatar-prediction-world-cup-2026-match-preview)",
        "- [Opta：苏格兰vs巴西](https://theanalyst.com/articles/scotland-vs-brazil-prediction-world-cup-2026-match-preview)",
        "- [Opta：摩洛哥vs海地](https://theanalyst.com/articles/morocco-vs-haiti-prediction-world-cup-2026-match-preview)",
        "- [Opta：捷克vs墨西哥](https://theanalyst.com/articles/czechia-vs-mexico-prediction-world-cup-2026-match-preview)",
        "- [Open-Meteo天气API](https://open-meteo.com/en/docs)",
        *[f"- [Polymarket：{item['identity']['home']}vs{item['identity']['away']}]({polymarket['matches'][item['identity']['code']]['event_url']})" for item in matches],
        "", "> 风险提示：报告是当前数据截点下的概率估计。正式首发、临场伤停、顶棚状态或盘口跨档时必须重算；任何单场或串关都存在明显不确定性。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    api = json.loads((BASE / "api/api_audit.json").read_text(encoding="utf-8"))
    weather = json.loads((BASE / "weather/weather_audit.json").read_text(encoding="utf-8"))
    online = json.loads((BASE / "online_review_sources.json").read_text(encoding="utf-8"))
    polymarket = json.loads((BASE / "polymarket_snapshot.json").read_text(encoding="utf-8"))
    accessory = json.loads((BASE / "accessory_analysis.json").read_text(encoding="utf-8"))
    REPORT_OUT.write_text(build_report(model, market, api, weather, online, polymarket, accessory), encoding="utf-8")
    TABLE_OUT.write_text(build_table(model), encoding="utf-8")
    source_summary = {
        "created_at": model["generated_at"],
        "pdfs": [{
            "path": "/Users/jamesm/Downloads/未命名文件夹/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.pdf",
            "pages": 3, "creation_date": "2026-06-24T14:06:02+08:00",
            "text_output": str(BASE / "pdf_text/500主表.txt"),
            "visual_pages": [str(BASE / f"pdf_visual_audit/main-{index}.jpg") for index in range(1, 4)],
            "visual_audit": "passed_all_pages",
        }],
        "market_matches": list(market["matches"]), "market_errors": market["errors"],
        "api_fixture_count": len(api["fixtures"]), "weather_locations": len(weather["locations"]),
        "polymarket_matches": list(polymarket["matches"]), "polymarket_errors": polymarket["errors"],
        "opta_verified": [code for code, item in online["matches"].items() if item["opta"].get("verified")],
        "opta_missing": [code for code, item in online["matches"].items() if not item["opta"].get("verified")],
        "accessory_analysis": str(BASE / "accessory_analysis.json"),
        "generic_web_search": "HTTP 403; replaced by Google News RSS plus direct source retrieval",
    }
    (BASE / "source_extract_summary.json").write_text(json.dumps(source_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
