from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260626")
REPORT_OUT = BASE / "2026-06-26世界杯周四055-060_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-26世界杯周四055-060_推荐总表.md"

CORE = {
    "周四055": ("德国胜；德国-1让胜/让平双选", "2-4球", ["0-2", "0-1", "1-2"], ["0-3", "1-3", "2-2"]),
    "周四056": ("科特迪瓦胜；库拉索+2让胜优先", "2-4球", ["0-1", "0-2", "1-1"], ["0-3", "1-3", "2-2"]),
    "周四057": ("荷兰胜；-2不单挑，防让平", "3-5球", ["0-2", "0-3", "1-2"], ["1-3", "0-4", "1-4"]),
    "周四058": ("日本胜防平；日本-1让负", "2-4球", ["1-1", "2-1", "1-0"], ["2-2", "3-1", "1-2"]),
    "周四059": ("平局主线，澳大利亚不败；巴拉圭-1让负", "0-2球", ["1-1", "0-0", "0-1"], ["1-0", "1-2", "2-2"]),
    "周四060": ("美国胜；土耳其+1让胜/让平保护", "2-4球", ["0-1", "1-1", "0-2"], ["1-2", "0-3", "1-3"]),
}

UPSET = {
    "周四055": ("德国胜未出", ["home", "draw"], "厄瓜多尔胜", ["home"], "德国轮换+厄瓜多尔必须抢分"),
    "周四056": ("科特迪瓦胜未出", ["home", "draw"], "库拉索胜", ["home"], "科特迪瓦平即可+库拉索必须冒险"),
    "周四057": ("荷兰胜未出", ["home", "draw"], "突尼斯胜", ["home"], "雨战高湿+荷兰深让降温"),
    "周四058": ("瑞典胜", ["away"], "瑞典胜", ["away"], "瑞典定位球/高点+日本伤停与平局心态"),
    "周四059": ("非平局", ["home", "away"], "巴拉圭胜", ["home"], "巴拉圭必须赢导致节奏破局"),
    "周四060": ("美国胜未出", ["home", "draw"], "土耳其胜", ["home"], "美国轮换+土耳其荣誉战反扑"),
}

SCENARIOS = {
    "周四055": "德国6分/+7已锁E组头名，轮换概率高但替补深度强；厄瓜多尔1分/-1且尚未进球，必须抢分，落后后会主动打开。",
    "周四056": "科特迪瓦3分/0，平局大概率第二出线；库拉索1分/-6，必须大胜且等待德国帮助，理论战意强但风险暴露更大。",
    "周四057": "荷兰4分/+4，与日本同分争F组头名；突尼斯0分/-8已出局，雨战和高湿压节奏，但突尼斯防线崩盘样本很重。",
    "周四058": "日本4分/+4，不败大概率晋级并争头名；瑞典3分/0，赢球可反超，平局仍要看第三名比较。",
    "周四059": "澳大利亚3分/0，平局锁定D组第二；巴拉圭3分/-2，必须赢才能反超，且Almiron红牌停赛。",
    "周四060": "美国6分/+5已锁D组头名；土耳其0分/-3已出局。美国可能轮换黄牌风险球员，但主场 momentum 和替补深度仍强。",
}

TACTICAL = {
    "周四055": "厄瓜多尔防守完整但前两轮0进球，进攻要依靠边路推进、定位球和反抢后的二次进攻。德国大概率控球占优，若轮换Undav等替补仍有冲击力；厄瓜多尔必须抢分会给德国肋部和身后空间。",
    "周四056": "库拉索上一轮依赖门将高扑救守住0-0，但两轮被射门压力很大。科特迪瓦速度和身体优势明显，平局即可但若早进球仍有打穿空间；问题是-2深度并不稳。",
    "周四057": "突尼斯两轮丢9球，低位纪律和禁区保护都失衡。荷兰争头名，有持续进攻动机；Kansas City雨战会降低连续冲刺质量，但荷兰边路和替补火力仍能制造多段进球。",
    "周四058": "日本前两轮进6球，组织和转换效率都好；瑞典定位球、高点和反击质量足以制造扳平风险。日本胜面更高，但-1穿盘被平局和一球小胜压制。",
    "周四059": "这是六场里最像末轮默契/保护型节奏的一场。澳大利亚打平即可锁第二，巴拉圭缺Almiron后创造力下降；巴拉圭必须赢会后段冒险，但主线仍偏低比分平局。",
    "周四060": "美国已锁头名但公开口径是不放松，且主场和替补深度明显；土耳其荣誉战会提高进攻意愿。美国胜面清楚，但轮换和土耳其反扑使-1深度不宜单挑。",
}

MIXED_LEGS = [
    ("周四057 荷兰胜", "周四057", "result", "away"),
    ("周四058 日本不败", "周四058", "double", ("home", "draw")),
    ("周四059 澳大利亚不败", "周四059", "double", ("draw", "away")),
    ("周四055 德国胜", "周四055", "result", "away"),
    ("周四056 科特迪瓦胜", "周四056", "result", "away"),
    ("周四060 美国胜", "周四060", "result", "away"),
]

SCORE_LEGS = [
    ("周四057 荷兰 0-2/0-3", "周四057", ("0-2", "0-3")),
    ("周四059 1-1/0-0", "周四059", ("1-1", "0-0")),
    ("周四058 日本 1-1/2-1", "周四058", ("1-1", "2-1")),
    ("周四055 德国 0-2/0-1", "周四055", ("0-2", "0-1")),
    ("周四056 科特迪瓦 0-1/0-2", "周四056", ("0-1", "0-2")),
    ("周四060 美国 0-1/1-1", "周四060", ("0-1", "1-1")),
]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pct_small(value: float) -> str:
    percentage = value * 100
    return f"{percentage:.3f}%" if percentage < 0.1 else f"{percentage:.1f}%"


def by_score(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def scores(match: dict, labels: list[str]) -> str:
    pool = by_score(match)
    return " / ".join(f"{label}({pct(pool.get(label, 0.0))})" for label in labels)


def top3(match: dict) -> str:
    items = sorted(match["final"]["score_candidate_pool"], key=lambda item: item["probability"], reverse=True)[:3]
    return " / ".join(f"{item['score']}({pct(item['probability'])})" for item in items)


def leg_probability(match_map: dict, leg: tuple) -> float:
    _, code, kind, key = leg
    result = match_map[code]["final"]["result"]
    if kind == "result":
        return result[key]
    return sum(result[item] for item in key)


def event_probability(match: dict, keys: list[str]) -> float:
    result = match["final"]["result"]
    return sum(result[key] for key in keys)


def upset_text(match: dict) -> str:
    code = match["identity"]["code"]
    label, keys, extreme_label, extreme_keys, reason = UPSET[code]
    return f"{label} {pct(event_probability(match, keys))}；极端 {extreme_label} {pct(event_probability(match, extreme_keys))}；{reason}"


def build_table(model: dict) -> str:
    matches = model["matches"]
    match_map = {item["identity"]["code"]: item for item in matches}
    lines = [
        "# 2026-06-26 世界杯周四055-060 推荐总表",
        "",
        f"> 数据截点：{model['generated_at']}。概率为研究估计，不是赛果保证。",
        "",
        "## 单场总表",
        "",
        "| 场次 | 胜/平/负 | 核心推荐 | 冷门概率 | 让球胜/平/负 | 让球建议 | 总球 | 比分Top3 | 风险比分 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        core, goals, _, risk = CORE[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | **{core.split('；')[0]}** | "
            f"{upset_text(match)} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | {core.split('；')[-1]} | "
            f"{goals} | {top3(match)} | {scores(match, risk)} |"
        )

    mixed_lines = []
    score_lines = []
    for count in range(2, len(MIXED_LEGS) + 1):
        probability = 1.0
        for leg in MIXED_LEGS[:count]:
            probability *= leg_probability(match_map, leg)
        mixed_lines.append(f"| {count}串1 | {' × '.join(item[0] for item in MIXED_LEGS[:count])} | {pct(probability)} | {'中风险' if count <= 3 else '高风险'} |")
        score_probability = 1.0
        for _, code, labels in SCORE_LEGS[:count]:
            pool = by_score(match_map[code])
            score_probability *= sum(pool.get(label, 0.0) for label in labels)
        score_lines.append(f"| {count}串1 | {' × '.join(item[0] for item in SCORE_LEGS[:count])} | {2 ** count} | {pct_small(score_probability)} |")

    lines += [
        "",
        "让球概率按主队让球结算，顺序为让胜/让平/让负。",
        "",
        "## 混合过关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |",
        "|---|---|---:|---|",
        *mixed_lines,
        "",
        "## 比分过关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_lines,
        "",
        "> 比分串关从3串1开始已经明显变陡；059这种低比分末轮局建议单场覆盖，不建议拖入长串。",
    ]
    return "\n".join(lines) + "\n"


def build_report(model: dict, market: dict, weather: dict, polymarket: dict) -> str:
    matches = model["matches"]
    lines = [
        "# 2026-06-26 世界杯周四055-060 严格分析与GPT联网复核报告",
        "",
        f"> 数据截点：500 PDF 2026-06-25 15:48；500实时 {market['fetched_at']}；天气 {weather['fetched_at']}；Polymarket {polymarket['fetched_at']}。",
        "",
        "## 一、步骤审计",
        "",
        "- 500主表PDF：3页已抽取文本，周四055-060普通三向、让球三向、比分、总进球、半全场完整读取；Poppler命令不可用，使用pdfplumber文本抽取。",
        "- 500实时市场：主表和18个深层欧赔/亚盘/大小页面均抓取成功，错误0。",
        "- API-Football：六场fixture、prediction、odds、standings已读取；injuries返回日本Machino illness、巴拉圭Almiron红牌停赛；lineups/statistics尚未发布。",
        "- 天气：Open-Meteo按当地开球小时读取；Kansas City雨战高湿，Dallas高温风大，其余条件可控。",
        "- 外部市场：Polymarket仅日本vs瑞典、巴拉圭vs澳大利亚完整匹配并进入一次性融合；其他场使用Kalshi/Squawka/媒体报道作联网复核，直接概率权重为0。",
        "- 模型：Poisson/Dixon-Coles、市场去水、贝叶斯融合、proxy xG、让球/总球/比分、LEG、决策迭代、一致性检查均执行。",
        "- 决策迭代：已启用小组末轮规则，包括热门平即可、弱队必须赢、已锁头名但替补深度、强队胜但不零封尾部。",
        "",
        "## 二、小组形势",
        "",
        "| 场次 | 小组形势 | 关键影响 |",
        "|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        lines.append(f"| {code} | {SCENARIOS[code]} | {CORE[code][0]} |")

    lines += [
        "",
        "## 三、推荐总览",
        "",
        "| 场次 | 胜/平/负 | 冷门概率 | 让球胜/平/负 | 总球均值 | 决策迭代 | 一致性 | 核心方向 |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        rules = ", ".join(match["decision_iteration"]["applied_rules"][:3])
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{upset_text(match)} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{match['means']['decision_final']:.2f} | {rules} | {match['consistency']['status']} | {CORE[code][0]} |"
        )

    lines += ["", "## 四、单场分析", ""]
    for match in matches:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **胜平负**：{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}；**{CORE[code][0].split('；')[0]}**。",
            f"- **冷门概率**：{upset_text(match)}。",
            f"- **让球**：主队让球结算 {pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])}；{CORE[code][0].split('；')[-1]}。",
            f"- **总球**：{CORE[code][1]}；模型均值 {match['means']['decision_final']:.2f}，500总球均值 {match['means']['market_exact']:.2f}。",
            f"- **比分**：概率Top3 {top3(match)}；风险 {scores(match, CORE[code][3])}。",
            f"- **技战术与动机**：{TACTICAL[code]}",
            f"- **伤停/首发**：{match['source_facts']['absence_note']}",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings'] or match['consistency']['notes'])}",
            "",
        ]

    lines += [
        "## 五、风险排序",
        "",
        "1. **最低风险方向**：荷兰胜、德国胜。",
        "2. **中等风险方向**：科特迪瓦胜、日本不败、美国胜。",
        "3. **最高风险场**：巴拉圭vs澳大利亚。市场、积分和Polymarket都把平局推高，普通胜负方向不适合单挑。",
        "4. **最大穿盘陷阱**：科特迪瓦、美国。胜面存在，但对手受让保护较强。",
        "5. **最大天气/节奏冲突**：突尼斯vs荷兰。荷兰强势与雨战降节奏并存，建议胜负方向优于深让单挑。",
        "",
        "## 六、联网复核来源",
        "",
        "- 500竞彩足球实时主表：https://trade.500.com/jczq/index.php?playid=312&g=2",
        "- Bavarian Football Works：Ecuador vs Germany preview.",
        "- TalkSport/RacingPost：Curacao vs Ivory Coast previews.",
        "- Yahoo/Squawka/WhoScored：Tunisia vs Netherlands、Japan vs Sweden previews and market references.",
        "- Guardian：Australia vs Paraguay permutations and Socceroos news.",
        "- Times Union/New York Post/FanDuel：USA vs Turkey team news and rotation context.",
        "- Open-Meteo weather API.",
        "- Polymarket Gamma public-search API：Japan vs Sweden、Paraguay vs Australia.",
        "",
        "> 以上为赛前概率研究，不是确定性赛果。正式首发、临场伤停和盘口跨档会改变结论。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    weather = json.loads((BASE / "weather/weather_audit.json").read_text(encoding="utf-8"))
    polymarket = json.loads((BASE / "polymarket_snapshot.json").read_text(encoding="utf-8"))
    TABLE_OUT.write_text(build_table(model), encoding="utf-8")
    REPORT_OUT.write_text(build_report(model, market, weather, polymarket), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
