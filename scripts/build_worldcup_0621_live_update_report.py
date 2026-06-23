from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260622")
OLD_MODEL_PATH = BASE / "model_analysis.json"
NEW_MODEL_PATH = BASE / "model_analysis_live.json"
MARKET_PATH = BASE / "update_live/latest_market.json"
NEWS_PATH = BASE / "update_live/latest_news.json"
OUT = BASE / "2026-06-22世界杯周日037-040_1949最新赔率消息更新对比.md"

ODDS_TEXT = {
    "周日037": {
        "result": "百家即时1.10/10.27/24.89 -> 1.09/10.82/24.21（竞彩普通三向仍未开售）",
        "handicap": "西班牙-2：1.63/4.50/3.40 -> 1.57/4.55/3.66",
        "deep": "亚洲均线-2.578 -> -2.719；大小均线3.43 -> 3.50",
        "meaning": "市场继续支持西班牙赢深和高总球，但新增双边锋缺席形成反向约束。",
    },
    "周日038": {
        "result": "1.28/4.61/7.60 -> 1.26/4.76/7.95",
        "handicap": "比利时-1：1.92/3.72/2.94 -> 1.89/3.72/3.02",
        "deep": "亚洲均线-1.281 -> -1.250；大小均线2.63 -> 2.68",
        "meaning": "竞彩强队端继续压低，但亚洲均线未同步升深；多库缺席抵消部分利好。",
    },
    "周日039": {
        "result": "1.30/4.05/8.80 -> 1.29/4.15/8.80",
        "handicap": "乌拉圭-1：2.14/3.23/2.84 -> 2.08/3.30/2.89",
        "deep": "亚洲均线-1.047 -> -1.172；大小均线维持2.29",
        "meaning": "乌拉圭方向获得增量支持，但总球未上调，仍是胜面增强、深度谨慎。",
    },
    "周日040": {
        "result": "5.85/3.80/1.44 -> 6.00/3.87/1.42",
        "handicap": "新西兰+1：2.40/3.34/2.42 -> 2.46/3.30/2.38",
        "deep": "亚洲均线+0.953 -> +0.969；大小均线2.31 -> 2.34",
        "meaning": "埃及胜与至少赢两球方向同步增强，但客胜热度风险仍存在。",
    },
}

NEWS_TEXT = {
    "周日037": ("亚马尔腿后肌恢复中、未准备踢满90分钟", "Reuters最新报道亚马尔与尼科·威廉斯均缺席", "实质负面更新；西班牙边路爆点和一对一终结需要下修。"),
    "周日038": ("Transfermarkt列多库患病、德巴斯特腿后肌伤，未获二次确认", "ESPN报道多库确定缺席；德巴斯特状态仍未获官方确认", "多库缺席由不确定变成权威媒体确认，抵消市场增强。"),
    "周日039": ("德阿拉斯凯塔、阿劳霍肌肉伤不确定；迈阿密30.3C且有雷暴代码95", "未出现更可靠伤停反转；天气更新为26.8C、湿度85%、风19.4km/h，雷暴信号下降", "伤停判断不变；天气仍压节奏，但极端雷暴风险减弱。"),
    "周日040": ("无新增缺席，埃及主帅否认萨拉赫不和", "未发现实质新增缺席；最新预览继续围绕萨拉赫正常出战", "消息面基本不变，赔率成为主要更新来源。"),
}

CORE = {
    "周日037": ("西班牙胜", "西班牙-2让胜，防让负", "3-4球"),
    "周日038": ("比利时胜，防平", "比利时-1让负", "2-4球"),
    "周日039": ("乌拉圭胜，重点防平", "乌拉圭-1让负；让胜同步保护", "1-3球"),
    "周日040": ("埃及胜", "新西兰+1让胜，防让负", "2-3球"),
}

IRON_SCORES = {
    "周日037": ["1-0", "2-0", "3-0"],
    "周日038": ["2-1", "1-0", "3-1"],
    "周日039": ["1-0", "2-0", "3-0"],
    "周日040": ["1-1", "0-1", "0-3"],
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pp(old: float, new: float) -> str:
    return f"{(new - old) * 100:+.1f}pp"


def score_map(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def scores(match: dict, labels: list[str]) -> str:
    mapping = score_map(match)
    return " / ".join(f"{label}({pct(mapping.get(label, 0.0))})" for label in labels)


def main() -> None:
    old_model = json.loads(OLD_MODEL_PATH.read_text(encoding="utf-8"))
    new_model = json.loads(NEW_MODEL_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    news = json.loads(NEWS_PATH.read_text(encoding="utf-8"))
    old_by_code = {item["identity"]["code"]: item for item in old_model["matches"]}
    new_by_code = {item["identity"]["code"]: item for item in new_model["matches"]}

    lines = [
        "# 2026-06-22 世界杯周日037-040 最新赔率与消息更新对比",
        "",
        f"> 最新市场抓取：{market['fetched_at']}；最新新闻抓取：{news['fetched_at']}。基准为15:39-16:05严格报告。",
        "",
        "## 一、更新审计",
        "",
        "- 500实时主表已直接抓取：普通三向、让球三向、比分、总进球、半全场全部更新。",
        "- 500深层页已抓取：百家平均、亚洲均线、大小均线；抓取错误0。",
        "- API-Football实时复查：四场injuries与lineups仍全部返回0行。",
        "- 新闻复核：Google News RSS发现最新报道，再按Reuters、ESPN、Al Jazeera等来源等级处理。",
        "- 真实赛前xG/xGA仍不可用；模型继续使用收缩后的proxy xG。",
        "- 最终官方首发尚未发布，因此媒体确认缺席进入模型，但不写成官方首发确认。",
        "",
        "## 二、最新赔率变化",
        "",
        "| 场次 | 胜平负变化 | 让球三向变化 | 深层均线变化 | 市场解释 |",
        "|---|---|---|---|---|",
    ]
    for code in new_by_code:
        item = ODDS_TEXT[code]
        lines.append(f"| {code} | {item['result']} | {item['handicap']} | {item['deep']} | {item['meaning']} |")

    lines.extend([
        "",
        "## 三、最新消息变化",
        "",
        "| 场次 | 之前报告 | 最新消息 | 模型处理 |",
        "|---|---|---|---|",
    ])
    for code, values in NEWS_TEXT.items():
        lines.append(f"| {code} | {values[0]} | {values[1]} | {values[2]} |")

    lines.extend([
        "",
        "## 四、概率重算对比",
        "",
        "| 场次 | 最新胜/平/负 | 相对之前 | 最新让球胜/平/负 | 让球变化 | 总球均值 | 核心结论 |",
        "|---|---|---|---|---|---:|---|",
    ])
    for code, current in new_by_code.items():
        previous = old_by_code[code]
        result = current["final"]["result"]
        old_result = previous["final"]["result"]
        handicap = current["final"]["handicap_home_settlement"]
        old_handicap = previous["final"]["handicap_home_settlement"]
        core = CORE[code]
        lines.append(
            f"| {code} {current['identity']['home']}vs{current['identity']['away']} | "
            f"{pct(result['home'])}/{pct(result['draw'])}/{pct(result['away'])} | "
            f"{pp(old_result['home'], result['home'])}/{pp(old_result['draw'], result['draw'])}/{pp(old_result['away'], result['away'])} | "
            f"{pct(handicap['cover'])}/{pct(handicap['push'])}/{pct(handicap['fail'])} | "
            f"{pp(old_handicap['cover'], handicap['cover'])}/{pp(old_handicap['push'], handicap['push'])}/{pp(old_handicap['fail'], handicap['fail'])} | "
            f"{previous['means']['decision_final']:.3f}->{current['means']['decision_final']:.3f} | {core[0]}；{core[1]} |"
        )

    lines.extend([
        "",
        "说明：让球胜/平/负按主队所列让球结算。变化顺序与概率顺序一致。",
        "",
        "## 五、逐场改变",
        "",
        "### 周日037 西班牙 vs 沙特阿拉伯",
        "",
        "- **改变**：西班牙胜79.9%降至79.2%；双边锋缺席的负面影响略大于三向市场增强。",
        "- **深盘**：-2让胜40.5%升至41.1%，仍只领先让负35.9%，不能升级为低风险单选。",
        "- **总球**：3.279升至3.302；3-4球不变，4-0/4-1上沿仍保留。",
        "- **结论**：西班牙胜不变；-2让胜主、防让负；比分1-0/2-0/3-0。",
        "",
        "### 周日038 比利时 vs 伊朗",
        "",
        "- **改变**：比利时胜56.2%微升至56.2%（四舍五入后相同）；市场利好被多库确定缺席抵消。",
        "- **深盘**：-1让负38.9%降至38.5%，让胜33.5%升至33.8%，但首选没有翻转。",
        "- **总球**：2.936降至2.918；2-4球不变。",
        "- **结论**：比利时胜、防平不变；-1继续让负；比分2-1/1-0/3-1。",
        "",
        "### 周日039 乌拉圭 vs 佛得角",
        "",
        "- **改变**：乌拉圭胜55.5%升至56.0%，平局28.6%降至28.1%。",
        "- **深盘**：-1让胜33.5%升至34.3%，让负36.3%降至35.8%，两端差距缩至1.5个百分点。",
        "- **天气**：雷暴风险减弱，但湿度和风速上升；低节奏保护不取消。",
        "- **结论**：乌拉圭胜仍防平；-1不建议单挑，让负主、让胜同步保护；比分1-0/2-0/3-0。",
        "",
        "### 周日040 新西兰 vs 埃及",
        "",
        "- **改变**：埃及胜58.2%升至58.6%；新西兰胜和平局各小幅下降。",
        "- **深盘**：新西兰+1让负32.0%升至32.7%，说明埃及赢两球路径增强；让胜仍以37.8%居首。",
        "- **总球**：2.499升至2.512；2-3球不变。",
        "- **结论**：埃及胜不变；新西兰+1让胜保护仍保留，防让负；比分1-1/0-1/0-3。",
        "",
        "## 六、最新推荐总表",
        "",
        "| 场次 | 核心 | 让球 | 总球 | 铁律Top3 | 一致性 |",
        "|---|---|---|---|---|---|",
    ])
    for code, match in new_by_code.items():
        core = CORE[code]
        lines.append(
            f"| {code} | **{core[0]}** | {core[1]} | {core[2]} | "
            f"{scores(match, IRON_SCORES[code])} | {match['consistency']['status']} |"
        )

    lines.extend([
        "",
        "## 七、组合变化",
        "",
        "- 2串1主线仍为：比利时胜 × 埃及胜。埃及权重略上调，比利时不变。",
        "- 2串1替代仍为：乌拉圭胜 × 埃及胜；乌拉圭权重可小幅上调，但平局保护不能删除。",
        "- 3串1仍为：西班牙-2让胜 × 比利时胜 × 埃及胜；西班牙双边锋缺席后不提高组合权重。",
        "- 4串1结构不变：西班牙-2让胜 × 比利时胜 × 乌拉圭-1让负 × 埃及胜；乌拉圭-1建议加入让胜分支，组合数会增加。",
        "- 比分组合不变：西班牙2-0/3-0，比利时1-0/2-1，乌拉圭1-0/2-0，埃及0-1/0-2。",
        "",
        "## 八、联网来源与限制",
        "",
        "- [500实时竞彩主表](https://trade.500.com/jczq/index.php?playid=312&g=2)",
        "- [Reuters新闻发现页：西班牙伤停查询](https://news.google.com/rss/search?q=Spain+Saudi+Arabia+World+Cup+2026+Yamal+lineup+injury&hl=en-US&gl=US&ceid=US:en)",
        "- [ESPN新闻发现页：比利时伤停查询](https://news.google.com/rss/search?q=Belgium+Iran+World+Cup+2026+Doku+injury+lineup&hl=en-US&gl=US&ceid=US:en)",
        "- [Al Jazeera：埃及主帅否认萨拉赫不和](https://www.aljazeera.com/sports/2026/6/21/egypt-coach-denies-salah-rift-before-world-cup-match-against-new-zealand)",
        "- [Open-Meteo天气API](https://open-meteo.com/en/docs)",
        "",
        "> 限制：官方最终首发仍未公布；API-Football伤停与首发端点仍为0行。Reuters和ESPN消息按权威媒体层处理，不冒充球队官方公告。",
        "",
        "## 九、最终变化结论",
        "",
        "1. 四场赛果与让球首选均未翻转。",
        "2. 西班牙市场更强但人员更弱，最终胜率小幅下降，不能因盘口升深而追高。",
        "3. 比利时市场增强被多库缺席抵消，仍是胜、防平结构。",
        "4. 乌拉圭是让球层变化最大的一场：让胜明显逼近让负，-1应改成双向保护。",
        "5. 埃及是本轮最清晰的增量增强项，胜率和赢两球概率同步上升，但新西兰+1让胜仍是最高项。",
        "",
        "> 风险提示：概率是当前截点估计，不是赛果保证。正式首发发布后应再做一次最终校准。",
    ])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
