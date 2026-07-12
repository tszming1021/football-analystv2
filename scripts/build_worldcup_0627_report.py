from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260627")
REPORT_OUT = BASE / "2026-06-27世界杯周五061-066_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-27世界杯周五061-066_推荐总表.md"

CORE = {
    "周五061": ("总球3+，次选法国不败", "3+球，防2-4", ["1-1", "1-2", "0-2"], ["2-2", "1-3", "2-3"]),
    "周五062": ("塞内加尔胜，次选总球3+", "2-4球，防3+", ["2-0", "1-0", "2-1"], ["3-0", "3-1", "1-1"]),
    "周五063": ("总球1-3，次选佛得角-1让负", "1-3球，防0-0", ["1-1", "0-0", "0-1"], ["1-0", "1-2", "2-2"]),
    "周五064": ("总球1-3，次选西班牙不败", "1-3球", ["0-1", "1-1", "0-2"], ["0-0", "1-2", "2-2"]),
    "周五065": ("总球0-2，次选埃及-1让负", "0-2球", ["1-1", "0-0", "1-0"], ["0-1", "1-2", "2-2"]),
    "周五066": ("总球3+，次选比利时胜", "3+球，防2-4", ["1-2", "0-2", "0-1"], ["1-3", "0-3", "2-2"]),
}

CORE_PROB = {
    "周五061": "总球3+ 64.6%",
    "周五062": "塞内加尔胜 64.9%",
    "周五063": "总球1-3 70.9%",
    "周五064": "总球1-3 70.4%",
    "周五065": "总球0-2 74.7%",
    "周五066": "总球3+ 68.4%",
}

HANDICAP_ADVICE = {
    "周五061": "挪威+1让胜优先",
    "周五062": "-2不追，伊拉克+2让负/让平保护",
    "周五063": "佛得角-1让负",
    "周五064": "乌拉圭+1让胜/让平",
    "周五065": "埃及-1让负",
    "周五066": "新西兰+2让胜优先",
}

UPSET = {
    "周五061": ("法国胜未出", ["home", "draw"], "挪威胜", ["home"], "法国平即可头名+挪威争头名"),
    "周五062": ("塞内加尔胜未出", ["draw", "away"], "伊拉克胜", ["away"], "Mendy伤缺+两队荣誉战"),
    "周五063": ("佛得角胜", ["home"], "佛得角胜", ["home"], "沙特必须赢；NRG闭顶后天气影响降权"),
    "周五064": ("西班牙胜未出", ["home", "draw"], "乌拉圭胜", ["home"], "雷暴雨战+乌拉圭必须抢分"),
    "周五065": ("伊朗胜", ["away"], "伊朗胜", ["away"], "伊朗必须赢+埃及平即可"),
    "周五066": ("比利时胜未出", ["home", "draw"], "新西兰胜", ["home"], "比利时伤停集中+深盘压力"),
}

SCENARIOS = {
    "周五061": "法国6分/+5，挪威6分/+4，双方锁前二；法国平局头名，挪威需要赢。",
    "周五062": "塞内加尔0分/-3，伊拉克0分/-6；前二无望，塞内加尔仍有大胜争第三的理论动机。",
    "周五063": "佛得角2分/0，沙特1分/-4；佛得角赢球最稳，沙特必须赢并等待另一场。",
    "周五064": "西班牙4分/+4，乌拉圭2分/0；西班牙不败基本头名，乌拉圭需要抢分。",
    "周五065": "埃及4分/+2，伊朗2分/0；埃及不败晋级，伊朗取胜可反超。",
    "周五066": "比利时2分/0，新西兰1分/-2；比利时必须赢才稳，新西兰也需胜利求生。",
}

TACTICAL = {
    "周五061": "Haaland和Mbappe两条主线都能制造高质量机会，500总球和市场比分都偏开放。法国实力与阵容厚度更强，但平局即可头名，挪威+1保护比法国深度更稳。",
    "周五062": "塞内加尔身体、速度和前场压迫优势明显，但Mendy缺席削弱门线稳定性。伊拉克防线承压大，塞内加尔胜面高；-2深度被1-0/2-0/2-1压住。",
    "周五063": "NRG Stadium可闭合顶棚且具备现代HVAC，若顶棚关闭，雷暴和降水对场内节奏影响应大幅降权。佛得角停赛削弱中后场，沙特必须赢但进攻效率不稳；市场与模型仍把平局/一球边界推到前面。",
    "周五064": "Zapopan雷暴和高降水概率是本场核心变量。西班牙控球优势仍在，但乌拉圭缺Araujo/De Arrascaeta且必须抢分，比赛会有身体对抗和定位球波动。",
    "周五065": "埃及不败即可，伊朗必须赢；双方防线纪律和低总球市场使1-1/0-0权重很高。埃及后场停赛和伊朗追分动机会抬高客胜冷门。",
    "周五066": "比利时必须赢，Polymarket和500均强支撑客胜，但Doku/Debast/Ngoy缺席降低边路爆点与防线稳定。新西兰+2保护很强，比分更像1-2/0-2而不是大屠杀。",
}

MIXED_LEGS = [
    ("周五066 比利时胜", "周五066", "result", "away"),
    ("周五062 塞内加尔胜", "周五062", "result", "home"),
    ("周五065 埃及不败", "周五065", "double", ("home", "draw")),
    ("周五064 西班牙不败", "周五064", "double", ("draw", "away")),
    ("周五063 沙特不败", "周五063", "double", ("draw", "away")),
    ("周五061 法国不败", "周五061", "double", ("draw", "away")),
]

SCORE_LEGS = [
    ("周五065 1-1/0-0", "周五065", ("1-1", "0-0")),
    ("周五064 0-1/1-1", "周五064", ("0-1", "1-1")),
    ("周五066 1-2/0-2", "周五066", ("1-2", "0-2")),
    ("周五062 2-0/1-0", "周五062", ("2-0", "1-0")),
    ("周五063 1-1/0-0", "周五063", ("1-1", "0-0")),
    ("周五061 1-1/1-2", "周五061", ("1-1", "1-2")),
]


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def pct_small(v: float) -> str:
    p = v * 100
    return f"{p:.3f}%" if p < 0.1 else f"{p:.1f}%"


def by_score(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def top3(match: dict) -> str:
    items = sorted(match["final"]["score_candidate_pool"], key=lambda item: item["probability"], reverse=True)[:3]
    return " / ".join(f"{item['score']}({pct(item['probability'])})" for item in items)


def scores(match: dict, labels: list[str]) -> str:
    pool = by_score(match)
    return " / ".join(f"{label}({pct(pool.get(label, 0.0))})" for label in labels)


def event_probability(match: dict, keys) -> float:
    result = match["final"]["result"]
    return sum(result[key] for key in keys)


def upset_text(match: dict) -> str:
    code = match["identity"]["code"]
    label, keys, extreme_label, extreme_keys, reason = UPSET[code]
    return f"{label} {pct(event_probability(match, keys))}；极端 {extreme_label} {pct(event_probability(match, extreme_keys))}；{reason}"


def leg_probability(match_map: dict, leg: tuple) -> float:
    _, code, kind, key = leg
    result = match_map[code]["final"]["result"]
    if kind == "result":
        return result[key]
    return sum(result[item] for item in key)


def build_table(model: dict) -> str:
    match_map = {m["identity"]["code"]: m for m in model["matches"]}
    lines = [
        "# 2026-06-27 世界杯周五061-066 推荐总表",
        "",
        f"> 数据截点：{model['generated_at']}。概率为研究估计，不是赛果保证。",
        "",
        "## 单场总表",
        "",
        "| 场次 | 胜/平/负 | 核心推荐 | 核心概率 | 冷门概率 | 让球胜/平/负 | 让球建议 | 总球 | 比分Top3 | 风险比分 |",
        "|---|---|---|---:|---|---|---|---|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        core, goals, _, risk = CORE[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | **{core.split('；')[0]}** | "
            f"{CORE_PROB[code]} | {upset_text(match)} | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | "
            f"{HANDICAP_ADVICE[code]} | {goals} | {top3(match)} | {scores(match, risk)} |"
        )

    mixed, score_lines = [], []
    for count in range(2, 7):
        prob = 1.0
        for leg in MIXED_LEGS[:count]:
            prob *= leg_probability(match_map, leg)
        mixed.append(f"| {count}串1 | {' × '.join(i[0] for i in MIXED_LEGS[:count])} | {pct(prob)} | {'中风险' if count <= 3 else '高风险'} |")
        sp = 1.0
        for _, code, labels in SCORE_LEGS[:count]:
            pool = by_score(match_map[code])
            sp *= sum(pool.get(label, 0.0) for label in labels)
        score_lines.append(f"| {count}串1 | {' × '.join(i[0] for i in SCORE_LEGS[:count])} | {2 ** count} | {pct_small(sp)} |")

    lines += [
        "",
        "让球概率按主队让球结算，顺序为让胜/让平/让负。",
        "",
        "## 混合过关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |",
        "|---|---|---:|---|",
        *mixed,
        "",
        "## 比分过关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_lines,
        "",
        "> 064/065/063这种末轮低比分场，不建议把比分长串当核心；最多作为小注覆盖。",
    ]
    return "\n".join(lines) + "\n"


def build_report(model: dict, market: dict, weather: dict, poly: dict) -> str:
    lines = [
        "# 2026-06-27 世界杯周五061-066 严格分析与GPT联网复核报告",
        "",
        f"> 数据截点：500实时 {market['fetched_at']}；天气 {weather['fetched_at']}；Polymarket {poly['fetched_at']}。",
        "",
        "## 一、步骤审计",
        "",
        "- 500主表PDF与实时网页均读取；061-066主表、让球、比分、总进球、半全场完整解析。",
        "- 500深层欧赔/亚盘/大小盘18个页面抓取成功，错误0。",
        "- API-Football读取fixture、prediction、odds、injuries、standings；061 injuries和066 fixture有SSL失败，已记录并用其他端点/联网复核补足。",
        "- 天气按场馆当地开球小时读取；NRG Stadium可闭合且有HVAC，因此063雷暴/降水大幅降权；Estadio Akron按露天处理，064雷暴和98%降水仍保留。",
        "- Polymarket完整三向仅061、062、066入模；063、064、065不完整，不直接入概率层。",
        "- 决策迭代包含小组末轮平即可、必须赢、强队深盘、天气压节奏和伤停校准。",
        "",
        "## 二、小组形势",
        "",
        "| 场次 | 积分形势 | 影响 |",
        "|---|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        lines.append(f"| {code} | {SCENARIOS[code]} | {CORE[code][0]} |")

    lines += [
        "",
        "## 三、推荐总览",
        "",
        "| 场次 | 胜/平/负 | 冷门概率 | 让球胜/平/负 | 总球均值 | 一致性 | 核心方向 |",
        "|---|---|---|---|---:|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {upset_text(match)} | "
            f"{pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | {match['means']['decision_final']:.2f} | "
            f"{match['consistency']['status']} | {CORE[code][0]} |"
        )

    lines += ["", "## 四、单场分析", ""]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **胜平负**：{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])}；**{CORE[code][0].split('；')[0]}**。",
            f"- **冷门概率**：{upset_text(match)}。",
            f"- **核心推荐**：{CORE[code][0].split('；')[0]}，估算概率 {CORE_PROB[code]}。",
            f"- **让球**：主队让球结算 {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])}；{HANDICAP_ADVICE[code]}。",
            f"- **总球**：{CORE[code][1]}；模型均值 {match['means']['decision_final']:.2f}，500总球均值 {match['means']['market_exact']:.2f}。",
            f"- **比分**：概率Top3 {top3(match)}；风险 {scores(match, CORE[code][3])}。",
            f"- **技战术/动机/天气**：{TACTICAL[code]}",
            f"- **伤停/首发**：{match['source_facts']['absence_note']}",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings'] or match['consistency']['notes'])}",
            "",
        ]

    lines += [
        "## 五、风险排序",
        "",
        "1. **最低风险方向**：065总球0-2、063总球1-3、066总球3+。",
        "2. **中等风险方向**：062塞内加尔胜、064总球1-3、061总球3+。",
        "3. **最高风险场**：佛得角vs沙特。场馆可闭合使天气影响降权，但积分和双方效率仍把比赛推向低比分摇摆。",
        "4. **最大天气变量**：乌拉圭vs西班牙。Estadio Akron按露天处理，Zapopan雷暴和98%降水概率会压低西班牙传控稳定性。",
        "5. **玩法选择原则**：核心推荐优先取四类玩法中概率最高且逻辑最顺的一项；胜平负只作为次选或串关腿。",
        "",
        "## 六、联网复核来源",
        "",
        "- 500竞彩足球实时主表：https://trade.500.com/jczq/index.php?playid=312&g=2",
        "- API-Football fixture / injuries / standings / predictions.",
        "- Open-Meteo天气API.",
        "- Polymarket Gamma public-search API：Norway vs France、Senegal vs Iraq、New Zealand vs Belgium.",
        "- Guardian / Al Jazeera / RacingPost / Climate Central 等赛前报道用于伤停、天气和战意复核。",
        "",
        "> 以上为赛前概率研究，不是确定性赛果。正式首发、临场伤停、顶棚状态和盘口跨档会改变结论。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    weather = json.loads((BASE / "weather/weather_audit.json").read_text(encoding="utf-8"))
    poly = json.loads((BASE / "polymarket_snapshot.json").read_text(encoding="utf-8"))
    TABLE_OUT.write_text(build_table(model), encoding="utf-8")
    REPORT_OUT.write_text(build_report(model, market, weather, poly), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
