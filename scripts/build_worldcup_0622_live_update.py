from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


BASE = Path("data/worldcup_20260623")
UPDATE = BASE / "update_0018"
OLD_MODEL = UPDATE / "model_analysis_previous.json"
NEW_MODEL = BASE / "model_analysis.json"
OLD_MARKET = UPDATE / "market_previous.json"
NEW_MARKET = BASE / "market/latest_market.json"
API = BASE / "api/api_audit.json"
WEATHER = BASE / "weather/weather_audit.json"
REPORT = BASE / "2026-06-23世界杯周一041-044_0018临场更新对比.md"
TABLE = BASE / "2026-06-23世界杯周一041-044_0018临场推荐总表.md"

CORE = {
    "周一041": ("阿根廷胜", "阿根廷-1让胜，防让负", "3球核心，2/4球保护"),
    "周一042": ("法国胜", "法国-3让负，防让胜", "4球核心，3/5球保护"),
    "周一043": ("挪威不败，胜平双选", "挪威-1让负", "2-3球，1/4球保护"),
    "周一044": ("阿尔及利亚胜", "约旦+1让胜/让负双防，不单挑", "2-3球，4球保护"),
}

SCORES = {
    "周一041": (["1-0", "2-0", "2-1"], ["1-0", "2-0", "3-0"], ["0-1", "2-2"]),
    "周一042": (["2-0", "3-0", "1-0"], ["2-0", "3-0", "4-0"], ["1-1", "3-2"]),
    "周一043": (["1-1", "2-1", "1-0"], ["1-1", "1-0", "2-2"], ["0-1", "2-3"]),
    "周一044": (["0-1", "0-2", "1-1"], ["0-1", "0-2", "0-3"], ["1-0", "2-2"]),
}

CHANGE = {
    "周一041": "主胜与亚洲盘同步升深；官方首发确认梅西、劳塔罗、德保罗、麦卡利斯特、恩佐同场，且Posch实际首发，撤销旧缺席假设。核心从“阿根廷-1让负略优”改为“让胜略优、让负保护”。",
    "周一042": "赛果几乎不变；法国-3让胜赔率下压、让负赔率抬升，总球均线3.46升至3.59，赢深和4球以上路径增强，但-3让负仍是最大项。",
    "周一043": "三向、亚洲盘和让球三向变化很小；市场继续只给亚洲-0.28，竞彩-1让负维持最清楚方向。纽约风力预报下修，但湿度升至91%。",
    "周一044": "阿尔及利亚客胜从1.44压至1.34，客胜概率上升；约旦+1让胜优势被压缩到不足1个百分点，改为让胜/让负双防，不再作为单一保护胆。",
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def signed_pp(new: float, old: float) -> str:
    value = (new - old) * 100
    return f"{value:+.1f}pp"


def score_probability(match: dict, score: str) -> float:
    for item in match["final"]["score_candidate_pool"]:
        if item["score"] == score:
            return item["probability"]
    return 0.0


def fmt_scores(match: dict, scores: list[str]) -> str:
    return " / ".join(f"{score}({pct(score_probability(match, score))})" for score in scores)


def total_top(match: dict) -> str:
    distribution = match["final"]["total_distribution"]
    top = sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:3]
    return " / ".join(f"{key.replace('_plus', '+')}球 {pct(value)}" for key, value in top)


def market_line(item: dict) -> str:
    current = item["current"]
    deep = item["deep_market"]
    one_x_two = current["one_x_two"]
    result = (
        f"{one_x_two.get('3', '-')}/{one_x_two.get('1', '-')}/{one_x_two.get('0', '-')}"
        if one_x_two else
        f"未开售，百家{deep['ouzhi']['current'][0]:.2f}/{deep['ouzhi']['current'][1]:.2f}/{deep['ouzhi']['current'][2]:.2f}"
    )
    handicap = current["handicap_three_way"]
    return (
        f"三向{result}；让球{current['handicap']:+g} "
        f"{handicap['3']:.2f}/{handicap['1']:.2f}/{handicap['0']:.2f}；"
        f"亚洲{deep['yazhi']['current'][1]:+.3f}；大小{deep['daxiao']['current'][1]:.2f}"
    )


def build() -> tuple[str, str]:
    old_model = {m["identity"]["code"]: m for m in json.loads(OLD_MODEL.read_text())["matches"]}
    new_model = {m["identity"]["code"]: m for m in json.loads(NEW_MODEL.read_text())["matches"]}
    old_market = json.loads(OLD_MARKET.read_text())["matches"]
    new_market_data = json.loads(NEW_MARKET.read_text())
    new_market = new_market_data["matches"]
    api = json.loads(API.read_text())
    weather = json.loads(WEATHER.read_text())
    fetched = new_market_data["fetched_at"]

    table_lines = [
        "# 2026-06-23 世界杯周一041-044 00:18临场推荐总表",
        "",
        f"> 数据截点：{fetched}。周一041官方首发已确认，其余三场尚无官方首发。",
        "",
        "| 场次 | 最新胜/平/负 | 较旧版 | 核心 | 让球胜/平/负 | 让球推荐 | 总球Top3 | 概率Top3 | 铁律Top3 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for code, match in new_model.items():
        old = old_model[code]
        result = match["final"]["result"]
        old_result = old["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        probability, iron, _ = SCORES[code]
        table_lines.append(
            f"| {code} {match['identity']['home']}vs{match['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{signed_pp(result['home'], old_result['home'])}/{signed_pp(result['draw'], old_result['draw'])}/{signed_pp(result['away'], old_result['away'])} | "
            f"**{CORE[code][0]}** | {pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"**{CORE[code][1]}** | {total_top(match)} | {fmt_scores(match, probability)} | **{fmt_scores(match, iron)}** |"
        )
    table_lines.extend([
        "",
        "## 临场组合",
        "",
        "- 2串1主线：法国胜 × 挪威-1让负。",
        "- 2串1进取：阿根廷胜 × 阿尔及利亚胜。",
        "- 3串1：阿根廷胜 × 法国胜 × 挪威-1让负。",
        "- 4串1：阿根廷胜 × 法国胜 × 挪威-1让负 × 阿尔及利亚胜；高波动。",
        "- 比分2串1：阿根廷1-0/2-0 × 法国2-0/3-0。",
        "- 比分3串1：再加入阿尔及利亚0-1/0-2。",
        "",
        "> 阿根廷-1让胜已反超让负，但差距只有2.5个百分点，不作为单项重仓方向。",
    ])

    report_lines = [
        "# 2026-06-23 世界杯周一041-044 00:18临场更新对比",
        "",
        f"> 当前四场状态均为Not Started；数据截点{fetched}（Asia/Hong_Kong同为UTC+8）。",
        "",
        "## 一、临场数据审计",
        "",
        "- 500实时主表及12个深盘页面重新抓取，错误0。",
        "- API-Football四场fixture、prediction和odds重新查询。",
        "- 周一041阿根廷vs奥地利已返回双方官方首发；其余三场lineups仍为0行。",
        "- 四场injuries仍为0行，不能据此推导全员健康。",
        "- 天气预报已刷新：达拉斯31.8C；费城33.6C；纽约21.8C且湿度91%；圣克拉拉16.6C。",
        "- 联网消息刷新至00:18；阿根廷首发新闻与API阵容相互印证，其余场次媒体内容仍以预计阵容为主。",
        "",
        "## 二、关键结论",
        "",
        "1. **阿根廷方向增强**：官方强阵与盘口升深同时出现，主胜升至64.2%；-1让胜首次反超让负，但仍需双防。",
        "2. **法国赢深增强但未翻转**：-3让负由60.8%降至54.3%，仍是第一项；总球中枢上移到4球。",
        "3. **挪威场基本不变**：胜平负分布仍散，-1让负约59.3%继续是最清楚方向。",
        "4. **阿尔及利亚赛果增强、让球保护减弱**：客胜升至60.9%，约旦+1三项趋于均衡。",
        "",
        "## 三、逐场变化",
    ]
    for code, match in new_model.items():
        old = old_model[code]
        result = match["final"]["result"]
        old_result = old["final"]["result"]
        handicap = match["final"]["handicap_home_settlement"]
        old_handicap = old["final"]["handicap_home_settlement"]
        probability, iron, cold = SCORES[code]
        report_lines.extend([
            "",
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **最新市场**：{market_line(new_market[code])}。",
            f"- **旧版市场**：{market_line(old_market[code])}。",
            f"- **赛果**：{pct(old_result['home'])}/{pct(old_result['draw'])}/{pct(old_result['away'])} -> "
            f"**{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])}**，变化"
            f"{signed_pp(result['home'], old_result['home'])}/{signed_pp(result['draw'], old_result['draw'])}/{signed_pp(result['away'], old_result['away'])}。",
            f"- **让球**：{pct(old_handicap['cover'])}/{pct(old_handicap['push'])}/{pct(old_handicap['fail'])} -> "
            f"**{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])}**。",
            f"- **总球均值**：{old['means']['decision_final']:.3f} -> {match['means']['decision_final']:.3f}；最新Top3为{total_top(match)}。",
            f"- **比分**：概率Top3 {fmt_scores(match, probability)}；铁律Top3 **{fmt_scores(match, iron)}**；冷门 {fmt_scores(match, cold)}。",
            f"- **改变原因**：{CHANGE[code]}",
            f"- **最新结论**：{CORE[code][0]}；{CORE[code][1]}；{CORE[code][2]}。",
            f"- **一致性**：{match['consistency']['status']}；{'；'.join(match['consistency']['warnings']) or '无冲突警告'}。",
        ])

    report_lines.extend([
        "",
        "## 四、阿根廷官方首发",
        "",
        "- 阿根廷：E. Martinez；Molina、Romero、Lisandro Martinez、Medina；De Paul、Mac Allister、Enzo Fernandez、Almada；Messi、Lautaro Martinez。",
        "- 奥地利：Schlager；Posch、Danso、Alaba、Laimer；Seiwald、Xaver Schlager；Schmid、Wanner、Sabitzer；Gregoritsch。",
        "- Julian Alvarez与Arnautovic均在替补席。Posch实际首发，因此旧版Transfermarkt缺席条目不再采用。",
        "",
        "## 五、临场推荐",
        "",
        "- 主线2串1：法国胜 × 挪威-1让负。",
        "- 进取2串1：阿根廷胜 × 阿尔及利亚胜。",
        "- 3串1：阿根廷胜 × 法国胜 × 挪威-1让负。",
        "- 4串1：再加入阿尔及利亚胜；组合概率下降明显。",
        "- 比分2串1：阿根廷1-0/2-0 × 法国2-0/3-0。",
        "- 比分3串1：再加入阿尔及利亚0-1/0-2。",
        "",
        "## 六、联网来源",
        "",
        "- [500竞彩足球实时主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [Opta：阿根廷vs奥地利](https://theanalyst.com/articles/argentina-vs-austria-prediction-world-cup-2026)",
        "- [Opta：法国vs伊拉克](https://theanalyst.com/articles/france-vs-iraq-prediction-world-cup-2026)",
        "- [Opta：挪威vs塞内加尔](https://theanalyst.com/articles/norway-vs-senegal-prediction-world-cup-2026)",
        "- [Opta：约旦vs阿尔及利亚](https://theanalyst.com/articles/jordan-vs-algeria-prediction-world-cup-2026)",
        "- [Open-Meteo](https://open-meteo.com/en/docs)",
        "",
        "> 风险提示：周一041临近开赛，后续盘口可能因首发进一步波动；其余三场仍无官方首发，不能把媒体预计阵容当作确认信息。",
    ])
    return "\n".join(report_lines) + "\n", "\n".join(table_lines) + "\n"


def main() -> None:
    report, table = build()
    REPORT.write_text(report, encoding="utf-8")
    TABLE.write_text(table, encoding="utf-8")
    UPDATE.mkdir(parents=True, exist_ok=True)
    (UPDATE / "latest_market.json").write_text(NEW_MARKET.read_text(), encoding="utf-8")
    (UPDATE / "api_audit.json").write_text(API.read_text(), encoding="utf-8")
    (UPDATE / "weather_audit.json").write_text(WEATHER.read_text(), encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "table": str(TABLE)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
