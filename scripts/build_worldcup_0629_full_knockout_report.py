from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260629_full")
REPORT_OUT = BASE / "2026-06-29世界杯淘汰赛073-078_90分钟口径详细报告.md"
TABLE_OUT = BASE / "2026-06-29世界杯淘汰赛073-078_总推荐表.md"

CORE = {
    "周日073": ("总球1-3", "加拿大90分钟胜次选；南非+1让胜保护", "1-3"),
    "周一074": ("总球1-3", "巴西90分钟胜次选；巴西-1让负保护", "1-3"),
    "周一075": ("德国90分钟胜", "总球2-4；德国-1让胜可小注", "result_home"),
    "周一076": ("总球1-3", "荷兰-1让负保护；防加时", "1-3"),
    "周二077": ("总球1-3", "科特迪瓦+1让胜保护；防平", "1-3"),
    "周二078": ("法国90分钟胜", "总球2-4；法国-1让胜可小注", "result_home"),
}

HANDICAP_TEXT = {
    "周日073": "南非+1：让胜优先，防让平",
    "周一074": "巴西-1：让负优先，防让平",
    "周一075": "德国-1：让胜略优，但不如德国胜稳",
    "周一076": "荷兰-1：让负优先，摩洛哥+1保护最强",
    "周二077": "科特迪瓦+1：让胜优先",
    "周二078": "法国-1：让胜略优，防让平/让负",
}

TACTICAL = {
    "周日073": "加拿大实力和市场热度更强，但Kone缺阵削弱中场覆盖；淘汰赛首要目标是不输，南非拖慢节奏和定位球防线会抬高1-1/0-0。",
    "周一074": "巴西牌面优势明显，但Raphinha缺阵降低右路爆点；日本适合低位到反击，90分钟不败路径不低，巴西晋级优势大于穿盘优势。",
    "周一075": "德国是本轮最稳胜负方向之一，盘口和比分赔率同时支持2-0/3-0；但Schlotterbeck等防线伤停让2-1/3-1不能丢。",
    "周一076": "荷兰小优但摩洛哥防守韧性强，Monterrey开放球场强风会打断连续进攻。90分钟平局和加时路径最高。",
    "周二077": "挪威锋线名气更热，但科特迪瓦身体对抗、定位球和+1保护很强；API prediction与500方向分歧，胜负不如总球稳。",
    "周二078": "法国是本轮另一支强胜方向，盘口升到深盘且总球被抬高；瑞典反击有进球路径，因此法国胜强于法国深穿。",
}

SOURCES = [
    "500竞彩足球实时主表与赔率页：https://trade.500.com/jczq/index.php?playid=312&g=2",
    "SoFi Stadium赛程页：https://www.sofistadium.com/events/detail/fifa-world-cup-roundof32-june28",
    "FOX 26 Houston巴西vs日本场馆确认：https://www.fox26houston.com/news/fifa-world-cup-2026-round-32-matchup-set-monday-houston-stadium",
    "FIFA荷兰vs摩洛哥预览页：https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/netherlands-morocco-live-stream-team-news-tickets",
    "Open-Meteo天气：https://open-meteo.com/",
    "API-Football fixture/predictions/injuries/odds endpoints.",
]

MIXED_LEGS = [
    ("周一076 总球1-3", "周一076", "total", "1-3"),
    ("周日073 总球1-3", "周日073", "total", "1-3"),
    ("周一075 德国胜", "周一075", "result", "home"),
    ("周二078 法国胜", "周二078", "result", "home"),
    ("周一074 总球1-3", "周一074", "total", "1-3"),
    ("周二077 总球1-3", "周二077", "total", "1-3"),
]

SCORE_LEGS = [
    ("周一076 1-1/1-0", "周一076", ("1-1", "1-0")),
    ("周日073 0-1/1-1", "周日073", ("0-1", "1-1")),
    ("周一075 2-0/1-0", "周一075", ("2-0", "1-0")),
    ("周二078 2-0/2-1", "周二078", ("2-0", "2-1")),
    ("周一074 1-0/1-1", "周一074", ("1-0", "1-1")),
    ("周二077 1-1/0-1", "周二077", ("1-1", "0-1")),
]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pct_small(value: float) -> str:
    p = value * 100
    return f"{p:.3f}%" if p < 0.1 else f"{p:.1f}%"


def by_score(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def score_prob(match: dict, score: str) -> float:
    return by_score(match).get(score, 0.0)


def top_scores(match: dict, n: int = 3) -> str:
    items = sorted(match["final"]["score_candidate_pool"], key=lambda item: item["probability"], reverse=True)[:n]
    return " / ".join(f"{item['score']}({pct(item['probability'])})" for item in items)


def scores(match: dict, labels: tuple[str, ...]) -> str:
    return " / ".join(f"{label}({pct(score_prob(match, label))})" for label in labels)


def total_prob(match: dict, key: str) -> float:
    total = 0.0
    for item in match["final"]["score_candidate_pool"]:
        home, away = map(int, item["score"].split("-"))
        goals = home + away
        if key == "1-3" and 1 <= goals <= 3:
            total += item["probability"]
        elif key == "2-4" and 2 <= goals <= 4:
            total += item["probability"]
        elif key == "0-2" and goals <= 2:
            total += item["probability"]
        elif key == "3+" and goals >= 3:
            total += item["probability"]
    return total


def core_probability(match: dict, key: str) -> float:
    if key == "result_home":
        return match["final"]["result"]["home"]
    if key == "result_away":
        return match["final"]["result"]["away"]
    return total_prob(match, key)


def leg_probability(match_map: dict, leg: tuple) -> float:
    _, code, kind, key = leg
    match = match_map[code]
    if kind == "result":
        return match["final"]["result"][key]
    if kind == "handicap":
        return match["final"]["handicap_home_settlement"][key]
    return total_prob(match, key)


def weather_line(weather: dict, code: str) -> str:
    item = weather["matches"][code]
    w = item["weather"]
    roof = "顶棚/空调降权" if item["weather_impact_suppressed_by_roof"] else "天气正常计入"
    return f"{item['venue']}；{item['weather_label']}，{w['temperature_2m']}C，湿度{w['relative_humidity_2m']}%，降水{w['precipitation_probability']}%，风速{w['wind_speed_10m']}km/h，阵风{w['wind_gusts_10m']}km/h；{roof}。"


def build_table(model: dict) -> str:
    match_map = {m["identity"]["code"]: m for m in model["matches"]}
    lines = [
        "# 2026-06-29 世界杯淘汰赛073-078 总推荐表",
        "",
        f"> 数据截点：{model['generated_at']}。全部按90分钟常规时间结算，不含加时和点球。",
        "",
        "## 单场总表",
        "",
        "| 场次 | 90分钟胜/平/负 | 核心推荐 | 核心概率 | 让球胜/平/负 | 让球建议 | 总球 | 比分Top3 | 冷门/风险比分 |",
        "|---|---:|---|---:|---:|---|---|---|---|",
    ]
    risks = {
        "周日073": ("1-0", "2-1", "2-2"),
        "周一074": ("0-1", "1-2", "2-2"),
        "周一075": ("1-1", "0-0", "1-2"),
        "周一076": ("0-1", "1-2", "2-2"),
        "周二077": ("1-0", "2-1", "2-2"),
        "周二078": ("1-1", "2-2", "1-2"),
    }
    for match in model["matches"]:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        core, _, core_key = CORE[code]
        total_text = f"1-3({pct(total_prob(match, '1-3'))}) / 2-4({pct(total_prob(match, '2-4'))})"
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | **{core}** | "
            f"{pct(core_probability(match, core_key))} | {pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{HANDICAP_TEXT[code]} | {total_text} | {top_scores(match)} | {scores(match, risks[code])} |"
        )

    mixed, score_lines = [], []
    for count in range(2, 7):
        p = 1.0
        for leg in MIXED_LEGS[:count]:
            p *= leg_probability(match_map, leg)
        mixed.append(f"| {count}串1 | {' × '.join(leg[0] for leg in MIXED_LEGS[:count])} | {pct(p)} | {'中风险' if count <= 3 else '高风险'} |")
        sp = 1.0
        for _, code, labels in SCORE_LEGS[:count]:
            pool = by_score(match_map[code])
            sp *= sum(pool.get(label, 0.0) for label in labels)
        score_lines.append(f"| {count}串1 | {' × '.join(leg[0] for leg in SCORE_LEGS[:count])} | {2 ** count} | {pct_small(sp)} |")

    lines += [
        "",
        "让球概率按主队让球结算，顺序为让胜/让平/让负。",
        "",
        "## 混合过关 2串1到6串1",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险 |",
        "|---|---|---:|---|",
        *mixed,
        "",
        "## 比分过关 2串1到6串1",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_lines,
        "",
        "> 比分长串概率很低，只适合作小注覆盖；主推仍是2串1或3串1。",
    ]
    return "\n".join(lines) + "\n"


def build_report(model: dict, market: dict, weather: dict) -> str:
    lines = [
        "# 2026-06-29 世界杯淘汰赛073-078 90分钟口径详细报告",
        "",
        f"> 数据截点：500实时 {market['fetched_at']}；天气 {weather['fetched_at']}。全部按90分钟常规时间结算。",
        "",
        "## 一、步骤审计",
        "",
        "- 已解析用户提供的500主表PDF，新增识别075德国vs巴拉圭、077科特迪瓦vs挪威、078法国vs瑞典。",
        "- 已重新抓取073-078六场500实时主表、深层欧赔、亚盘、大小球和比分赔率。",
        "- 已读取API-Football fixture、prediction、injuries、odds；正式首发均未发布。",
        "- 已按场馆天气修正：SoFi、NRG、AT&T按顶棚/空调降权；Gillette、Estadio BBVA、MetLife按开放球场计入。",
        "- 淘汰赛赛制已进入模型：胜平负、让球、比分和总球全部按90分钟；平局代表进入加时/点球路径。",
        "",
        "## 二、总览",
        "",
        "| 场次 | 90分钟胜/平/负 | 核心推荐 | 加时风险 | 风险级别 |",
        "|---|---:|---|---:|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        core, note, core_key = CORE[code]
        risk = "高" if result["draw"] >= 0.32 else ("中高" if result["draw"] >= 0.28 else "中")
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | {core}（{pct(core_probability(match, core_key))}）；{note} | "
            f"{pct(result['draw'])} | {risk} |"
        )

    lines += ["", "## 三、单场分析", ""]
    for match in model["matches"]:
        code = match["identity"]["code"]
        result = match["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        core, note, core_key = CORE[code]
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **90分钟胜平负**：{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}。平局即加时路径，不等于晋级判断。",
            f"- **核心推荐**：{core}，估算概率 {pct(core_probability(match, core_key))}；{note}。",
            f"- **让球**：{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])}；{HANDICAP_TEXT[code]}。",
            f"- **总球**：1-3球 {pct(total_prob(match, '1-3'))}，2-4球 {pct(total_prob(match, '2-4'))}，模型均值 {match['means']['decision_final']:.2f}。",
            f"- **比分**：Top3 {top_scores(match)}。",
            f"- **场馆天气**：{weather_line(weather, code)}",
            f"- **伤停/首发**：{match['source_facts']['absence_note']}",
            f"- **技战术/赛制**：{TACTICAL[code]}",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings'] or match['consistency']['notes'])}",
            "",
        ]

    lines += [
        "## 四、分层结论",
        "",
        "1. **最稳单项**：076总球1-3、073总球1-3、075德国胜、078法国胜。",
        "2. **最稳胜负方向**：075德国90分钟胜、078法国90分钟胜；074巴西胜只能列中等信心。",
        "3. **最稳让球保护**：076荷兰-1让负、077科特迪瓦+1让胜、073南非+1让胜。",
        "4. **最强加时风险**：076荷兰vs摩洛哥、073南非vs加拿大、077科特迪瓦vs挪威。",
        "5. **不建议深追**：巴西-1让胜、荷兰-1让胜；法国和德国虽可穿盘，但仍不如胜平负方向稳。",
        "",
        "## 五、来源",
        "",
        *[f"- {source}" for source in SOURCES],
        "",
        "> 正式首发、临场伤停、顶棚开合和盘口跨档会改变结论。淘汰赛尤其要把90分钟赛果与最终晋级分开。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads((BASE / "model_analysis.json").read_text(encoding="utf-8"))
    market = json.loads((BASE / "market/latest_market.json").read_text(encoding="utf-8"))
    weather = json.loads((BASE / "weather/weather_audit.json").read_text(encoding="utf-8"))
    TABLE_OUT.write_text(build_table(model), encoding="utf-8")
    REPORT_OUT.write_text(build_report(model, market, weather), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
