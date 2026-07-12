from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260628")
REPORT_OUT = BASE / "2026-06-28世界杯周六067-072_严格分析与GPT联网复核报告.md"
TABLE_OUT = BASE / "2026-06-28世界杯周六067-072_推荐总表.md"

CORE = {
    "周六067": ("总球1-3，次选克罗地亚不败", "1-3球，防0-0", ["1-0", "0-0", "1-1"], ["0-1", "1-2", "2-2"]),
    "周六068": ("英格兰胜，次选总球1-3", "1-3球，防4+", ["0-1", "0-2", "1-2"], ["1-1", "0-0", "1-0"]),
    "周六069": ("总球1-3，次选哥伦比亚+1让胜", "1-3球，防2-2", ["0-1", "1-1", "1-2"], ["1-0", "2-1", "2-2"]),
    "周六070": ("总球1-3，次选刚果(金)胜", "1-3球，防0-0", ["1-0", "1-1", "2-0"], ["0-1", "0-0", "2-2"]),
    "周六071": ("阿尔及利亚+1让胜，次选总球0-2", "0-2球，防1-1/0-0", ["0-0", "1-1", "0-1"], ["1-0", "1-2", "2-2"]),
    "周六072": ("阿根廷胜，次选总球2-4", "2-4球，防1-1", ["0-2", "0-1", "0-3"], ["1-1", "0-0", "1-0"]),
}

CORE_PROB = {
    "周六067": "总球1-3 68.2%",
    "周六068": "英格兰胜 60.7%",
    "周六069": "总球1-3 65.6%",
    "周六070": "总球1-3 66.5%",
    "周六071": "阿尔及利亚+1让胜 70.9%",
    "周六072": "阿根廷胜 69.3%",
}

HANDICAP_ADVICE = {
    "周六067": "克罗地亚-1让负优先，防让平",
    "周六068": "巴拿马+2让胜/让平，英格兰赢但穿2球难度不低",
    "周六069": "哥伦比亚+1让胜优先",
    "周六070": "刚果(金)-1让负优先，防让平",
    "周六071": "阿尔及利亚+1让胜是全轮最稳让球腿",
    "周六072": "约旦+2让胜略优，防让平；不追阿根廷深穿",
}

UPSET = {
    "周六067": ("克罗地亚胜未出", ["draw", "away"], "加纳胜", ["away"], "Ghana平局路径更舒服，Croatia必须赢导致后段冒险"),
    "周六068": ("英格兰胜未出", ["home", "draw"], "巴拿马胜", ["home"], "英格兰已出线+James缺阵，Panama已淘汰但荣誉战"),
    "周六069": ("葡萄牙胜未出", ["home", "draw"], "哥伦比亚胜", ["home"], "哥伦比亚平即可头名，葡萄牙要赢才反超"),
    "周六070": ("刚果(金)胜未出", ["draw", "away"], "乌兹别克胜", ["away"], "刚果必须赢，乌兹别克荣誉战低压反击"),
    "周六071": ("平局未出", ["home", "away"], "阿尔及利亚胜", ["home"], "平局博弈强，1982叙事提高比赛舆论压力"),
    "周六072": ("阿根廷胜未出", ["home", "draw"], "约旦胜", ["home"], "阿根廷锁头名轮换，Messi预计替补"),
}

SCENARIOS = {
    "周六067": "L组：英格兰4分、加纳4分、克罗地亚3分、巴拿马0分；克罗地亚必须抢胜，加纳不败更稳。",
    "周六068": "L组：英格兰已确保至少最佳第三，但仍需争小组头名；巴拿马已淘汰。",
    "周六069": "K组：哥伦比亚6分已出线且平即可头名；葡萄牙4分已出线，赢球反超头名。",
    "周六070": "K组：刚果(金)1分需赢球争最佳第三；乌兹别克0分且净胜球劣势大，荣誉战。",
    "周六071": "J组：阿根廷6分锁头名，奥地利3分第二、阿尔及利亚3分第三；平局可能让双方保留路径。",
    "周六072": "J组：阿根廷锁头名并预计轮换；约旦0分基本出局。",
}

TACTICAL = {
    "周六067": "Croatia控球和经验占优，但Ghana两场只丢1球，低位反击和身体对抗能把比赛拖进一球/平局边界。500与Polymarket均给Croatia优势，但-1穿盘难度较高。",
    "周六068": "England实力断层明显，Polymarket给客胜高支撑；但James伤缺、可能轮换和Panama低位防守，使2球以上深穿不如客胜本身稳。",
    "周六069": "Colombia平即可头名，Portugal需赢才头名，Ronaldo预计继续首发。Hard Rock非全封闭，热湿环境降低持续高压质量，本场更像谨慎的一球差或平局。",
    "周六070": "DR Congo必须赢，Uzbekistan已承压两轮后容易被持续冲击。Mercedes-Benz若闭顶空调，外部高温/风速降权，比赛节奏主要看DR Congo终结效率。",
    "周六071": "盘口、Polymarket和比分赔率同时把平局压到核心区域，0-0/1-1权重极高。1982 Gijon叙事让“默契平”成为舆论风险，但模型仍认为+1保护最稳。",
    "周六072": "Argentina已锁头名，Messi预计替补且Scaloni轮换；替补阵容仍有明显等级差。AT&T若闭顶空调，外部阵风不影响场内，主要风险是阿根廷赢球不深穿。",
}

SOURCES = [
    "500竞彩足球实时主表：https://trade.500.com/jczq/index.php?playid=312&g=2",
    "Polymarket Gamma public-search API：https://gamma-api.polymarket.com/public-search",
    "Open-Meteo hourly forecast：https://open-meteo.com/",
    "Guardian：England/Reece James/Panama news：https://www.theguardian.com/football/2026/jun/27/england-through-to-last-32-of-the-world-cup-after-uruguay-exit-against-spain",
    "Guardian：Algeria-Austria/Gijon背景：https://www.theguardian.com/football/2026/jun/26/algeria-austria-1982-world-cup-shame-of-gijon-west-germany",
    "ESPN：Algeria vs Austria grudge match：https://www.espn.com/soccer/story/_/id/49154542/why-algeria-austria-2026-world-cup-biggest-grudge-match-west-germany-1982-disgrace-gijon",
    "Sports Mole：Croatia-Ghana preview：https://www.sportsmole.co.uk/football/croatia/world-cup-2026/preview/croatia-vs-ghana-prediction-team-news-lineups_600073.html",
    "Sports Mole：Colombia-Portugal preview：https://www.sportsmole.co.uk/football/portugal/world-cup-2026/preview/colombia-vs-portugal-prediction-team-news-lineups_600099.html",
    "Sports Mole：Jordan-Argentina preview：https://www.sportsmole.co.uk/football/jordan/world-cup-2026/preview/jordan-vs-argentina-prediction-team-news-lineups_600039.html",
    "Rediff/AFP：Messi bench confirmation：https://m.rediff.com/amp/sports/report/fifa-world-cup-argentina-captain-lionel-messi-to-start-on-bench-against-jordan-says-scaloni/20260627.htm",
]

MIXED_LEGS = [
    ("周六071 阿尔及利亚+1让胜", "周六071", "handicap", "cover"),
    ("周六067 总球1-3", "周六067", "total", "1-3"),
    ("周六070 总球1-3", "周六070", "total", "1-3"),
    ("周六069 总球1-3", "周六069", "total", "1-3"),
    ("周六072 阿根廷胜", "周六072", "result", "away"),
    ("周六068 英格兰胜", "周六068", "result", "away"),
]

SCORE_LEGS = [
    ("周六071 0-0/1-1", "周六071", ("0-0", "1-1")),
    ("周六067 1-0/1-1", "周六067", ("1-0", "1-1")),
    ("周六069 0-1/1-1", "周六069", ("0-1", "1-1")),
    ("周六070 1-0/1-1", "周六070", ("1-0", "1-1")),
    ("周六072 0-2/0-1", "周六072", ("0-2", "0-1")),
    ("周六068 0-1/0-2", "周六068", ("0-1", "0-2")),
]


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def pct_small(v: float) -> str:
    p = v * 100
    return f"{p:.3f}%" if p < 0.1 else f"{p:.1f}%"


def result_label(key: str) -> str:
    return {"home": "主胜", "draw": "平", "away": "客胜"}[key]


def by_score(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def top3(match: dict) -> str:
    items = sorted(match["final"]["score_candidate_pool"], key=lambda item: item["probability"], reverse=True)[:3]
    return " / ".join(f"{item['score']}({pct(item['probability'])})" for item in items)


def scores(match: dict, labels: list[str]) -> str:
    pool = by_score(match)
    return " / ".join(f"{label}({pct(pool.get(label, 0.0))})" for label in labels)


def total_prob(match: dict, key: str) -> float:
    total = 0.0
    for item in match["final"]["score_candidate_pool"]:
        home, away = map(int, item["score"].split("-"))
        goals = home + away
        if key == "1-3" and 1 <= goals <= 3:
            total += item["probability"]
        elif key == "0-2" and goals <= 2:
            total += item["probability"]
        elif key == "2-4" and 2 <= goals <= 4:
            total += item["probability"]
        elif key == "3+" and goals >= 3:
            total += item["probability"]
    return total


def event_probability(match: dict, keys: list[str]) -> float:
    result = match["final"]["result"]
    return sum(result[key] for key in keys)


def upset_text(match: dict) -> str:
    code = match["identity"]["code"]
    label, keys, extreme_label, extreme_keys, reason = UPSET[code]
    return f"{label} {pct(event_probability(match, keys))}；极端 {extreme_label} {pct(event_probability(match, extreme_keys))}；{reason}"


def leg_probability(match_map: dict, leg: tuple) -> float:
    _, code, kind, key = leg
    match = match_map[code]
    if kind == "result":
        return match["final"]["result"][key]
    if kind == "handicap":
        return match["final"]["handicap_home_settlement"][key]
    return total_prob(match, key)


def build_table(model: dict) -> str:
    match_map = {m["identity"]["code"]: m for m in model["matches"]}
    lines = [
        "# 2026-06-28 世界杯周六067-072 推荐总表",
        "",
        f"> 数据截点：{model['generated_at']}。概率为赛前研究估计，不是赛果保证。",
        "",
        "## 单场总表",
        "",
        "| 场次 | 胜/平/负 | 核心推荐 | 核心概率 | 冷门概率 | 让球胜/平/负 | 让球建议 | 总球 | 比分Top3 | 冷门/风险比分 |",
        "|---|---|---|---:|---|---|---|---|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        core, goals, _, risk = CORE[code]
        lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | **{core.split('，')[0]}** | "
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
        "## 混合过关 2串1到6串1",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险定位 |",
        "|---|---|---:|---|",
        *mixed,
        "",
        "## 比分过关 2串1到6串1",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_lines,
        "",
        "> 比分长串只适合作小注覆盖；071/067/069的低比分更适合作为比分串核心。",
    ]
    return "\n".join(lines) + "\n"


def weather_line(weather: dict, code: str) -> str:
    item = weather["matches"][code]
    w = item["weather"]
    roof = "顶棚/空调降权" if item["weather_impact_suppressed_by_roof"] else "天气正常计入"
    return f"{item['venue']}；{item['weather_label']}，{w['temperature_2m']}C，湿度{w['relative_humidity_2m']}%，降水概率{w['precipitation_probability']}%，风速{w['wind_speed_10m']}km/h；{roof}。"


def build_report(model: dict, market: dict, weather: dict, poly: dict) -> str:
    lines = [
        "# 2026-06-28 世界杯周六067-072 严格分析与GPT联网复核报告",
        "",
        f"> 数据截点：500实时 {market['fetched_at']}；天气 {weather['fetched_at']}；Polymarket {poly['fetched_at']}。",
        "",
        "## 一、步骤审计",
        "",
        "- 500主表PDF与实时网页均读取；067-072主表、让球、比分、总进球、深层欧赔/亚盘/大小盘已解析。",
        "- API-Football成功读取fixture/predictions和多数injuries/odds；正式首发未发布，lineups端点均为0。",
        "- Polymarket完整三向匹配067、068、069、071、072；070未匹配，不直接入概率层。",
        "- 天气按当地开球小时读取；Mercedes-Benz、AT&T按可闭顶空调降权，Hard Rock按非全封闭保留热湿变量。",
        "- 核心推荐从胜平负、让球胜平负、总球、比分四类中横向选择最稳一项。",
        "",
        "## 二、小组积分与动机",
        "",
        "| 场次 | 积分形势 | 推荐影响 |",
        "|---|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        lines.append(f"| {code} | {SCENARIOS[code]} | {CORE[code][0]} |")

    lines += [
        "",
        "## 三、推荐总览",
        "",
        "| 场次 | 胜/平/负 | 冷门概率 | 让球胜/平/负 | 总球均值 | 一致性 | 核心推荐 |",
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
            f"- **胜平负**：{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])}；常规方向：{result_label(max(r, key=r.get))}。",
            f"- **核心推荐**：{CORE[code][0].split('，')[0]}，估算概率 {CORE_PROB[code]}。",
            f"- **冷门概率**：{upset_text(match)}。",
            f"- **让球**：主队让球结算 {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])}；{HANDICAP_ADVICE[code]}。",
            f"- **总球**：{CORE[code][1]}；模型均值 {match['means']['decision_final']:.2f}，500总球均值 {match['means']['market_exact']:.2f}。",
            f"- **比分**：Top3 {top3(match)}；冷门/风险比分 {scores(match, CORE[code][3])}。",
            f"- **场馆天气**：{weather_line(weather, code)}",
            f"- **技战术/动机**：{TACTICAL[code]}",
            f"- **首发/伤停**：{match['source_facts']['absence_note']}",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings'] or match['consistency']['notes'])}",
            "",
        ]

    lines += [
        "## 五、风险排序",
        "",
        "1. **最低风险单项**：071阿尔及利亚+1让胜、067总球1-3、070总球1-3。",
        "2. **中低风险强队腿**：072阿根廷胜、068英格兰胜；但两场都不适合追深穿。",
        "3. **最高策略风险**：071阿尔及利亚vs奥地利，平局动机、舆论压力和低总球市场同时存在。",
        "4. **最高冷门暴露**：069哥伦比亚vs葡萄牙，葡萄牙胜未出概率57.3%，哥伦比亚平即可头名。",
        "5. **天气重点**：069 Hard Rock热湿/雷暴代码仍保留；070/072若闭顶空调，外部风雨不应高权重影响模型。",
        "",
        "## 六、联网复核来源",
        "",
        *[f"- {source}" for source in SOURCES],
        "",
        "> 以上为赛前概率研究，不是确定性赛果。正式首发、临场伤停、顶棚开合和盘口跨档会改变结论。",
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
