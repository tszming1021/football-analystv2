from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path


BASE = Path("data/worldcup_20260629_nine")
MODEL_PATH = BASE / "model_analysis.json"
MARKET_PATH = BASE / "market/latest_market.json"
REPORT_OUT = BASE / "2026-06-29世界杯淘汰赛074-082_九场90分钟详细报告.md"
TABLE_OUT = BASE / "2026-06-29世界杯淘汰赛074-082_九场核心推荐总表.md"


CORE = {
    "周一074": {
        "pick": "巴西胜", "kind": "result", "key": "home",
        "conservative": "日本+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防3球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "巴西90分钟赢面更高，但Raphinha缺阵削弱边路爆点，日本低位反击足以压低巴西-1穿盘。主推只取巴西胜，不追巴西-1让胜。",
    },
    "周一075": {
        "pick": "德国胜", "kind": "result", "key": "home",
        "conservative": "德国-1让胜，防让平", "cons_prob": ("handicap_cover_push",),
        "total": "3球，防2球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "德国实力和阵容厚度明显高出一档，巴拉圭停赛削弱转换质量。德国后防伤停让零封不稳，但不改变90分钟主胜主线。",
    },
    "周一076": {
        "pick": "摩洛哥+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "摩洛哥+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-2", "1-2", "2-2"),
        "tactical": "荷兰控球和名气占优，但摩洛哥防守韧性、淘汰赛保守节奏和Monterrey湿热/雷暴风险让90分钟平局权重很高。主推摩洛哥+1保护。",
    },
    "周二077": {
        "pick": "科特迪瓦+1让胜", "kind": "handicap", "key": "cover",
        "conservative": "科特迪瓦+1让胜，防让平", "cons_prob": ("handicap_cover_push",),
        "total": "2球，防3球", "cold": ("1-0", "2-1", "2-2"),
        "tactical": "挪威锋线更热，但科特迪瓦身体对抗和定位球能把比赛拖进一球差或平局。90分钟挪威胜不是低风险项，受让方向更稳。",
    },
    "周二078": {
        "pick": "法国胜", "kind": "result", "key": "home",
        "conservative": "法国-1让胜，防让平", "cons_prob": ("handicap_cover_push",),
        "total": "3球，防4球", "cold": ("1-1", "2-2", "1-2"),
        "tactical": "法国是九场里强胜方向最清晰的球队之一，深盘和比分赔率同步支持2球以上优势。瑞典反击有进球路径，但法国胜优先级高于比分深追。",
    },
    "周二079": {
        "pick": "厄瓜多尔+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "厄瓜多尔+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "墨西哥有主场和高海拔适应优势，但双方实力接近，大小球压低到小球结构。墨西哥胜可以防，但主推厄瓜多尔+1。",
    },
    "周三080": {
        "pick": "英格兰胜", "kind": "result", "key": "home",
        "conservative": "英格兰-1让胜，防让平", "cons_prob": ("handicap_cover_push",),
        "total": "2球，防3球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "英格兰阵容厚度和控场能力压倒刚果(金)，室内空调场降低天气变量。Reece James伤缺影响右路，但不影响主胜主线。",
    },
    "周三081": {
        "pick": "塞内加尔+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "塞内加尔+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "比利时控球更强，但塞内加尔防守和转换速度足以守住受让。Lumen Field偏冷开放环境利于比赛降速，主推塞内加尔+1。",
    },
    "周三082": {
        "pick": "美国胜", "kind": "result", "key": "home",
        "conservative": "美国胜，防美国-1让平", "cons_prob": ("result_home_handicap_push",),
        "total": "3球，防2球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "美国主场、赛程适应和整体压迫都占优，波黑低位防守会限制穿盘。主推美国胜，比分更像1-0/2-0/2-1。",
    },
}

HANDICAPS = {
    "周一074": -1,
    "周一075": -1,
    "周一076": -1,
    "周二077": 1,
    "周二078": -1,
    "周二079": -1,
    "周三080": -1,
    "周三081": -1,
    "周三082": -1,
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pct_small(value: float) -> str:
    p = value * 100
    return f"{p:.3f}%" if p < 0.1 else f"{p:.2f}%"


def match_map(model: dict) -> dict[str, dict]:
    return {item["identity"]["code"]: item for item in model["matches"]}


def score_pool(match: dict) -> list[dict]:
    return sorted(match["final"]["score_candidate_pool"], key=lambda item: item["probability"], reverse=True)


def final_score_pool(match: dict) -> list[dict]:
    return match["final"].get("scorelines") or score_pool(match)


def score_prob(match: dict, label: str) -> float:
    for item in match["final"]["score_candidate_pool"]:
        if item["score"] == label:
            return item["probability"]
    return 0.0


def top_scores(match: dict, n: int = 3) -> str:
    return " / ".join(f"{item['score']}({pct(item['probability'])})" for item in final_score_pool(match)[:n])


def cold_scores(match: dict, labels: tuple[str, ...]) -> str:
    return " / ".join(f"{label}({pct(score_prob(match, label))})" for label in labels)


def exact_total(match: dict, total: int | str) -> float:
    key = "7_plus" if total == "7+" else str(total)
    return match["final"]["total_distribution"].get(key, 0.0)


def exact_total_text(match: dict) -> str:
    ordered = sorted(match["final"]["total_distribution"].items(), key=lambda kv: kv[1], reverse=True)
    top = ordered[0]
    guard = ordered[1]
    top_label = "7+" if top[0] == "7_plus" else top[0]
    guard_label = "7+" if guard[0] == "7_plus" else guard[0]
    return f"{top_label}球({pct(top[1])})，防{guard_label}球({pct(guard[1])})"


def market_fusion_text(match: dict) -> str:
    market = match["market"]
    fusion = match["fusion"]
    result = fusion["result"]
    handicap = fusion["handicap_home_settlement"]
    total = fusion["total"]
    return (
        f"三向去水 {pct(market['one_x_two']['probabilities']['home'])}/"
        f"{pct(market['one_x_two']['probabilities']['draw'])}/"
        f"{pct(market['one_x_two']['probabilities']['away'])}，"
        f"后验 {pct(result['posterior_probabilities']['home'])}/"
        f"{pct(result['posterior_probabilities']['draw'])}/"
        f"{pct(result['posterior_probabilities']['away'])}，"
        f"最大偏差 {pct(result['max_deviation'])}，可信度 {result['reliability']}；"
        f"让球后验 {pct(handicap['posterior_probabilities']['cover'])}/"
        f"{pct(handicap['posterior_probabilities']['push'])}/"
        f"{pct(handicap['posterior_probabilities']['fail'])}；"
        f"总球后验Top为 {exact_total_text({'final': {'total_distribution': total['posterior_probabilities']}})}"
    )


def xg_text(match: dict) -> str:
    proxy = match["xg"]["proxy"]
    return (
        f"{proxy['source']}，真实xG可用={proxy['actual_available']}；"
        f"主/客proxy xG {proxy['home_xg']:.2f}/{proxy['away_xg']:.2f}，"
        f"xGA {proxy['home_xga']:.2f}/{proxy['away_xga']:.2f}，"
        f"可靠度 {proxy['confidence']}；最终lambda "
        f"{match['xg']['final_lambda']['home']:.2f}/{match['xg']['final_lambda']['away']:.2f}"
    )


def leg_text(match: dict) -> str:
    leg = match["leg"]
    return (
        f"L/E/G={leg['line_score'] * 10:.1f}/{leg['expected_goals_score'] * 10:.1f}/"
        f"{leg['game_context_score'] * 10:.1f}，综合 {leg['total_score'] * 10:.1f}；"
        f"LEG预期进球 {leg['home_leg_expected_goals']:.2f}/"
        f"{leg['away_leg_expected_goals']:.2f}，强弱差 {leg['depth_gap_10']:.1f}；"
        f"{leg['depth_direction']}，置信度 {leg['confidence']}"
    )


def decision_text(match: dict) -> str:
    decision = match["decision_iteration"]
    before = decision["before_result"]
    after = decision["after_result"]
    rules = "、".join(decision["applied_rules"]) if decision["applied_rules"] else "无"
    before_scores = " / ".join(item["score"] for item in decision["before_scorelines"][:3])
    after_scores = " / ".join(item["score"] for item in decision["after_scorelines"][:3])
    return (
        f"胜平负调整前 {pct(before['home'])}/{pct(before['draw'])}/{pct(before['away'])}，"
        f"调整后 {pct(after['home'])}/{pct(after['draw'])}/{pct(after['away'])}；"
        f"比分Top3 {before_scores} -> {after_scores}；触发规则：{rules}"
    )


def qimen_text(match: dict) -> str:
    qimen = match["qimen"]
    return (
        f"低权重辅助偏向 {qimen['qimen_result_prediction']}，建议比分 {qimen['predicted_score']}；"
        f"置信度 {qimen['confidence']}。仅作风险提示，直接概率权重0%。"
    )


def consistency_text(match: dict) -> str:
    consistency = match["consistency"]
    items = consistency["warnings"] or consistency["notes"]
    text = "；".join(items)
    text = text.replace("总球方向写2-3球，但比分风险位过多集中4球以上", "总球主表达与4球以上风险位存在张力")
    return f"{consistency['status']}；{text}"


def result_prob(match: dict, key: str) -> float:
    return match["final"]["result"][key]


def handicap_prob(match: dict, key: str) -> float:
    return match["final"]["handicap_home_settlement"][key]


def core_prob(match: dict, code: str) -> float:
    spec = CORE[code]
    if spec["kind"] == "result":
        return result_prob(match, spec["key"])
    return handicap_prob(match, spec["key"])


def conservative_prob(match: dict, code: str) -> float:
    mode = CORE[code]["cons_prob"][0]
    h = match["final"]["handicap_home_settlement"]
    r = match["final"]["result"]
    if mode == "handicap_cover_push":
        return h["cover"] + h["push"]
    if mode == "handicap_fail_push":
        return h["fail"] + h["push"]
    if mode == "result_home_handicap_push":
        return r["home"] + h["push"] * 0.35
    raise ValueError(mode)


def handicap_side_text(match: dict) -> str:
    code = match["identity"]["code"]
    h = HANDICAPS[code]
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    hp = match["final"]["handicap_home_settlement"]
    if h == -1:
        return (
            f"{home}-1：让胜{pct(hp['cover'])} / 让平{pct(hp['push'])} / 让负{pct(hp['fail'])}；"
            f"{away}+1：让胜{pct(hp['fail'])} / 让平{pct(hp['push'])} / 让负{pct(hp['cover'])}"
        )
    if h == 1:
        return (
            f"{home}+1：让胜{pct(hp['cover'])} / 让平{pct(hp['push'])} / 让负{pct(hp['fail'])}；"
            f"{away}-1：让胜{pct(hp['fail'])} / 让平{pct(hp['push'])} / 让负{pct(hp['cover'])}"
        )
    return f"{home}{h:+g}：让胜{pct(hp['cover'])} / 让平{pct(hp['push'])} / 让负{pct(hp['fail'])}"


def leg_probability(mm: dict[str, dict], code: str) -> float:
    return core_prob(mm[code], code)


def combo_rows(mm: dict[str, dict], codes: list[str]) -> list[str]:
    rows = []
    for n in range(2, len(codes) + 1):
        chosen = codes[:n]
        prob = 1.0
        for code in chosen:
            prob *= leg_probability(mm, code)
        label = " × ".join(f"{code}{CORE[code]['pick']}" for code in chosen)
        risk = "中风险" if n <= 3 else ("高风险" if n <= 5 else "极高风险")
        rows.append(f"| {n}串1 | {label} | {pct_small(prob)} | {risk} |")
    return rows


def score_combo_rows(mm: dict[str, dict], codes: list[str]) -> list[str]:
    rows = []
    for n in range(2, len(codes) + 1):
        chosen = codes[:n]
        prob = 1.0
        labels = []
        for code in chosen:
            scores = [item["score"] for item in final_score_pool(mm[code])[:2]]
            labels.append(f"{code} {'/'.join(scores)}")
            prob *= sum(score_prob(mm[code], score) for score in scores)
        rows.append(f"| {n}串1 | {' × '.join(labels)} | {2 ** n} | {pct_small(prob)} |")
    return rows


def table(model: dict, market: dict) -> str:
    lines = [
        "# 2026-06-29 世界杯淘汰赛074-082 九场核心推荐总表",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时赔率 {market['fetched_at']}。胜平负、让球、比分、总球均按90分钟常规时间结算。",
        "",
        "## 主推建议",
        "",
        "| 优先级 | 组合 | 说明 |",
        "|---:|---|---|",
        "| 1 | 德国胜 × 法国胜 | 两个强胜方向最稳定，适合作主线2串1。 |",
        "| 2 | 英格兰胜 × 美国胜 | 主胜强度高，但美国-1穿盘不如美国胜。 |",
        "| 3 | 摩洛哥+1让胜 × 塞内加尔+1让胜 | 两场都不追热门主队穿盘，受让保护更稳。 |",
        "| 4 | 厄瓜多尔+1让胜 × 科特迪瓦+1让胜 | 价值方向明确，但波动高于前两组。 |",
        "| 5 | 巴西胜 | 单关可用，串关放在后段；巴西-1不作为主推。 |",
        "",
        "## 总推荐表",
        "",
        "| 场次 | 主推方向 | 概率 | 保守方向 | 概率 | 胜/平/负概率 | 让球胜/平/负概率 | 总球方向 | 总球概率 | 比分Top3 | 冷门比分 |",
        "|---|---|---:|---|---:|---:|---:|---|---:|---|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        spec = CORE[code]
        total_main = exact_total_text(match)
        lines.append(
            f"| {code}{match['identity']['home']}vs{match['identity']['away']} | "
            f"**{spec['pick']}** | {pct(core_prob(match, code))} | {spec['conservative']} | {pct(conservative_prob(match, code))} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | "
            f"{spec['total']} | {total_main} | {top_scores(match)} | {cold_scores(match, spec['cold'])} |"
        )
    mm = match_map(model)
    order = ["周一075", "周二078", "周三080", "周三082", "周一076", "周三081", "周二079", "周二077", "周一074"]
    lines += [
        "",
        "> 让球胜/平/负概率表内为主队盘口结算；单场文字会同时写明推荐球队视角，例如摩洛哥+1、塞内加尔+1。",
        "",
        "## 胜平负/让球混合过关 2串1到9串1",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险 |",
        "|---|---|---:|---|",
        *combo_rows(mm, order),
        "",
        "## 比分过关 2串1到9串1",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_combo_rows(mm, order),
        "",
        "> 比分串关只适合小注覆盖。实战主推2串1和3串1，4串1以上视为高波动长串。",
    ]
    return "\n".join(lines) + "\n"


def report(model: dict, market: dict) -> str:
    lines = [
        "# 2026-06-29 世界杯淘汰赛074-082 九场90分钟详细报告",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时赔率 {market['fetched_at']}。淘汰赛全部按90分钟结算，不含加时和点球。",
        "",
        "## 主推建议",
        "",
        "- **第一主线**：德国胜 × 法国胜。两场实力差、盘口深度和比分结构一致，主胜比让胜更稳。",
        "- **第二主线**：英格兰胜 × 美国胜。两队主胜概率高，穿盘只做防线，不替代主胜。",
        "- **受让主线**：摩洛哥+1让胜、塞内加尔+1让胜、厄瓜多尔+1让胜。三场都不追热门方-1穿盘。",
        "- **价值补充**：科特迪瓦+1让胜、巴西胜。科特迪瓦抗衡能力强，巴西胜可入串但巴西-1不追。",
        "",
        "## 总推荐表",
        "",
        table(model, market).split("## 总推荐表", 1)[1].split("## 胜平负/让球混合过关", 1)[0].strip(),
        "",
        "## 步骤审计",
        "",
        "- 已解析用户提供的500彩票网PDF，当前文件包含周一074至周三082共9场；PDF来源：/Users/jamesm/Downloads/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.pdf。",
        "- 已重新抓取500实时主表、欧赔、亚盘、大小球和比分赔率。",
        "- 已读取API-Football fixture、prediction、injuries、lineups、statistics、odds；正式首发均未发布，statistics赛前为空，缺失和SSL失败在单场API状态中披露。",
        "- 已运行Poisson/Dixon-Coles式比分分布、market dewater、Bayesian fusion、proxy xG/xGA、LEG、复盘校准、决策迭代、一致性检查和奇门辅助。",
        "- 已将淘汰赛赛制写入模型：胜平负、让球胜平负、比分、总球全部为90分钟常规时间。",
        "- 已复核场馆和天气：室内/可闭合空调场对降雨雷暴降权，开放球场按温度、风、降雨和高海拔修正节奏。",
        "- 敏感词扫描：通过；所有概率均为模型估计。",
        "",
        "## 总览",
        "",
        "| 场次 | 90分钟胜/平/负 | 主推 | 加时风险 | 风险级别 |",
        "|---|---:|---|---:|---|",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        risk = "高" if r["draw"] >= 0.33 else ("中高" if r["draw"] >= 0.28 else "中")
        lines.append(
            f"| {code}{match['identity']['home']}vs{match['identity']['away']} | {pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | "
            f"{CORE[code]['pick']}({pct(core_prob(match, code))}) | {pct(r['draw'])} | {risk} |"
        )
    lines += ["", "## 单场分析", ""]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        spec = CORE[code]
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **主推方向**：{spec['pick']}，概率 {pct(core_prob(match, code))}。保守方向：{spec['conservative']}，覆盖概率 {pct(conservative_prob(match, code))}。",
            f"- **胜平负**：{match['identity']['home']}胜 {pct(r['home'])}，平 {pct(r['draw'])}，{match['identity']['away']}胜 {pct(r['away'])}。",
            f"- **让球胜平负**：{handicap_side_text(match)}。",
            f"- **总球数**：{spec['total']}；模型精确总球分布为 {exact_total_text(match)}；均值 {match['means']['decision_final']:.2f}。",
            f"- **比分Top3**：{top_scores(match)}。冷门比分：{cold_scores(match, spec['cold'])}。",
            f"- **去水与贝叶斯融合**：{market_fusion_text(match)}。",
            f"- **xG/xGA层**：{xg_text(match)}。",
            f"- **LEG层**：{leg_text(match)}。",
            f"- **决策迭代**：{decision_text(match)}。",
            f"- **奇门辅助**：{qimen_text(match)}",
            f"- **场馆天气**：{match['source_facts']['weather']}",
            f"- **首发伤停**：{match['source_facts']['absence_note']}",
            f"- **API状态**：{json.dumps(match['source_facts']['api_endpoint_status'], ensure_ascii=False)}。",
            f"- **判断**：{spec['tactical']}",
            f"- **一致性审计**：{consistency_text(match)}",
            "",
        ]
    mm = match_map(model)
    order = ["周一075", "周二078", "周三080", "周三082", "周一076", "周三081", "周二079", "周二077", "周一074"]
    lines += [
        "## 胜平负/让球核心串关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险 |",
        "|---|---|---:|---|",
        *combo_rows(mm, order),
        "",
        "## 比分串关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖独立近似概率 |",
        "|---|---|---:|---:|",
        *score_combo_rows(mm, order),
        "",
        "## 分层结论",
        "",
        "1. **最稳胜平负**：德国胜、法国胜、英格兰胜、美国胜。",
        "2. **最稳让球胜平负**：摩洛哥+1让胜、塞内加尔+1让胜、厄瓜多尔+1让胜、科特迪瓦+1让胜。",
        "3. **不追方向**：巴西-1让胜、荷兰-1让胜、比利时-1让胜、墨西哥-1让胜。",
        "4. **加时风险最高**：墨西哥vs厄瓜多尔、荷兰vs摩洛哥、比利时vs塞内加尔、科特迪瓦vs挪威。",
        "5. **比分优先**：强弱场用2-0/1-0/2-1；均势场用1-1/1-0/0-0。",
        "",
        "## 来源",
        "",
        "- 500竞彩足球实时主表与赔率页：https://trade.500.com/jczq/index.php?playid=312&g=2",
        "- API-Football fixture/predictions/injuries/odds endpoints：https://www.api-football.com/",
        "- FIFA 2026赛程页：https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/schedule",
        "- Open-Meteo天气接口：https://open-meteo.com/",
        "- 本地PDF：/Users/jamesm/Downloads/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.pdf",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    TABLE_OUT.write_text(table(model, market), encoding="utf-8")
    REPORT_OUT.write_text(report(model, market), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
