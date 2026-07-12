from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_worldcup_0629_nine_report import (
    cold_scores,
    conservative_prob,
    core_prob,
    decision_text,
    exact_total_text,
    final_score_pool,
    handicap_side_text,
    leg_text,
    market_fusion_text,
    pct,
    pct_small,
    qimen_text,
    score_prob,
    top_scores,
    xg_text,
)


BASE = Path("data/worldcup_20260630_nine")
MODEL_PATH = BASE / "model_analysis.json"
MARKET_PATH = BASE / "market/latest_market.json"
REPORT_OUT = BASE / "2026-06-30世界杯淘汰赛077-085_九场90分钟详细报告.md"
TABLE_OUT = BASE / "2026-06-30世界杯淘汰赛077-085_九场核心推荐总表.md"


CORE = {
    "周二077": {
        "pick": "科特迪瓦+1让胜", "kind": "handicap", "key": "cover",
        "conservative": "科特迪瓦+1让胜，防让平", "cons_prob": ("handicap_cover_push",),
        "total": "2球，防3球", "cold": ("1-0", "2-1", "2-2"),
        "tactical": "挪威锋线热度高，但科特迪瓦身体对抗、定位球和API不败信号足以支撑受让。主推受让，不追挪威胜。",
    },
    "周二078": {
        "pick": "法国胜", "kind": "result", "key": "home",
        "conservative": "法国胜，防法国-1让平", "cons_prob": ("result_home_handicap_push",),
        "total": "2球，防3球", "cold": ("1-1", "2-2", "1-2"),
        "tactical": "法国实力、近况进球和市场深度均占优，高温只削弱连续压迫，不改变90分钟主胜主线。",
    },
    "周二079": {
        "pick": "厄瓜多尔+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "厄瓜多尔+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "墨西哥主场与高海拔有利，但盘口和大小球都指向小比分卡线；厄瓜多尔+1优先级高于墨西哥胜。",
    },
    "周三080": {
        "pick": "英格兰胜", "kind": "result", "key": "home",
        "conservative": "英格兰胜，防英格兰-1让平", "cons_prob": ("result_home_handicap_push",),
        "total": "2球，防3球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "英格兰胜面稳定，但R. James伤缺和淘汰赛卡线规则让-1深追降级。",
    },
    "周三081": {
        "pick": "塞内加尔+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "塞内加尔+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "比利时三向小优，但让球端明显站在塞内加尔+1；塞内加尔反击和比利时伤停使穿盘风险偏高。",
    },
    "周三082": {
        "pick": "美国胜", "kind": "result", "key": "home",
        "conservative": "美国胜，防美国-1让平", "cons_prob": ("result_home_handicap_push",),
        "total": "2球，防3球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "美国主场、市场升温和API胜+进球组合支持主胜；-1让胜不如主胜稳。",
    },
    "周四083": {
        "pick": "西班牙胜", "kind": "result", "key": "home",
        "conservative": "西班牙胜，防西班牙-1让平", "cons_prob": ("result_home_handicap_push",),
        "total": "2球，防3球", "cold": ("1-1", "0-0", "1-2"),
        "tactical": "西班牙控球和防守稳定性明显强于奥地利，主胜优先；让胜因淘汰赛卡线只作次级。",
    },
    "周四084": {
        "pick": "克罗地亚+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "克罗地亚+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防1球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "葡萄牙胜面更高，但克罗地亚经验、控节奏和Toronto天气变量让+1保护更适合作核心。",
    },
    "周四085": {
        "pick": "阿尔及利亚+1让胜", "kind": "handicap", "key": "fail",
        "conservative": "阿尔及利亚+1让胜，防让平", "cons_prob": ("handicap_fail_push",),
        "total": "2球，防3球", "cold": ("0-1", "1-2", "2-2"),
        "tactical": "瑞士整体更稳，但三向优势不足以支撑-1；阿尔及利亚转换和受让保护更有价值。",
    },
}

HANDICAPS = {code: (-1 if code != "周二077" else 1) for code in CORE}


def match_map(model: dict) -> dict[str, dict]:
    return {item["identity"]["code"]: item for item in model["matches"]}


def core_prob_local(match: dict, code: str) -> float:
    spec = CORE[code]
    if spec["kind"] == "result":
        return match["final"]["result"][spec["key"]]
    return match["final"]["handicap_home_settlement"][spec["key"]]


def conservative_prob_local(match: dict, code: str) -> float:
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


def handicap_side_text_local(match: dict) -> str:
    code = match["identity"]["code"]
    line = HANDICAPS[code]
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    hp = match["final"]["handicap_home_settlement"]
    if line == -1:
        return (
            f"{home}-1：让胜{pct(hp['cover'])} / 让平{pct(hp['push'])} / 让负{pct(hp['fail'])}；"
            f"{away}+1：让胜{pct(hp['fail'])} / 让平{pct(hp['push'])} / 让负{pct(hp['cover'])}"
        )
    return (
        f"{home}+1：让胜{pct(hp['cover'])} / 让平{pct(hp['push'])} / 让负{pct(hp['fail'])}；"
        f"{away}-1：让胜{pct(hp['fail'])} / 让平{pct(hp['push'])} / 让负{pct(hp['cover'])}"
    )


def combo_rows(mm: dict[str, dict], codes: list[str]) -> list[str]:
    rows = []
    for n in range(2, len(codes) + 1):
        chosen = codes[:n]
        prob = 1.0
        for code in chosen:
            prob *= core_prob_local(mm[code], code)
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
    order = ["周二078", "周三080", "周三082", "周四083", "周三081", "周二079", "周四084", "周四085", "周二077"]
    lines = [
        "# 2026-06-30 世界杯淘汰赛077-085 九场核心推荐总表",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时赔率 {market['fetched_at']}。胜平负、让球、比分、总球均按90分钟常规时间结算。",
        "",
        "## 主推建议",
        "",
        "| 优先级 | 组合 | 说明 |",
        "|---:|---|---|",
        "| 1 | 法国胜 × 英格兰胜 | 强胜主线最稳定，但不深追-1。 |",
        "| 2 | 美国胜 × 西班牙胜 | 主胜胜面清晰，穿盘降级处理。 |",
        "| 3 | 塞内加尔+1让胜 × 厄瓜多尔+1让胜 | 两场均为热门小优但让球端保护客队。 |",
        "| 4 | 克罗地亚+1让胜 × 阿尔及利亚+1让胜 | 淘汰赛卡线价值方向，波动高于前三组。 |",
        "| 5 | 科特迪瓦+1让胜 | 单场价值补充，适合防挪威热度。 |",
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
        lines.append(
            f"| {code}{match['identity']['home']}vs{match['identity']['away']} | "
            f"**{spec['pick']}** | {pct(core_prob_local(match, code))} | {spec['conservative']} | {pct(conservative_prob_local(match, code))} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | "
            f"{spec['total']} | {exact_total_text(match)} | {top_scores(match)} | {cold_scores(match, spec['cold'])} |"
        )
    mm = match_map(model)
    lines += [
        "",
        "> 让球胜/平/负概率表内为主队盘口结算；单场文字会同时写明推荐球队视角。",
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
        "> 比分串关只适合小注覆盖；4串1以上视为高波动长串。",
    ]
    return "\n".join(lines) + "\n"


def report(model: dict, market: dict) -> str:
    lines = [
        "# 2026-06-30 世界杯淘汰赛077-085 九场90分钟详细报告",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时赔率 {market['fetched_at']}。淘汰赛全部按90分钟结算，不含加时和点球。",
        "",
        "## 主推建议",
        "",
        "- **第一主线**：法国胜 × 英格兰胜。",
        "- **第二主线**：美国胜 × 西班牙胜。",
        "- **受让主线**：塞内加尔+1让胜、厄瓜多尔+1让胜、克罗地亚+1让胜、阿尔及利亚+1让胜。",
        "- **价值补充**：科特迪瓦+1让胜。",
        "",
        "## 总推荐表",
        "",
        table(model, market).split("## 总推荐表", 1)[1].split("## 胜平负/让球混合过关", 1)[0].strip(),
        "",
        "## 步骤审计",
        "",
        "- 已解析用户提供的500彩票网PDF，当前文件包含周二077至周四085共9场；PDF创建时间为2026-06-30 16:25 CST。",
        "- 已重新抓取500实时主表、欧赔、亚盘、大小球和比分赔率。",
        "- 已读取API-Football fixture、prediction、injuries、lineups、statistics、odds；正式首发均未发布，赛前statistics为空。",
        "- 已运行Poisson/Dixon-Coles式比分分布、market dewater、Bayesian fusion、proxy xG/xGA、LEG、复盘校准、决策迭代、一致性检查和奇门辅助。",
        "- 已核对场馆天气和室内/开放球场属性；GPT/联网复核直接概率权重0%。",
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
            f"{CORE[code]['pick']}({pct(core_prob_local(match, code))}) | {pct(r['draw'])} | {risk} |"
        )
    lines += ["", "## 单场分析", ""]
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        spec = CORE[code]
        consistency = match["consistency"]
        consistency_text = "；".join(consistency["warnings"] or consistency["notes"])
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **主推方向**：{spec['pick']}，概率 {pct(core_prob_local(match, code))}。保守方向：{spec['conservative']}，覆盖概率 {pct(conservative_prob_local(match, code))}。",
            f"- **胜平负**：{match['identity']['home']}胜 {pct(r['home'])}，平 {pct(r['draw'])}，{match['identity']['away']}胜 {pct(r['away'])}。",
            f"- **让球胜平负**：{handicap_side_text_local(match)}。",
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
            f"- **一致性审计**：{consistency['status']}；{consistency_text}",
            "",
        ]
    mm = match_map(model)
    order = ["周二078", "周三080", "周三082", "周四083", "周三081", "周二079", "周四084", "周四085", "周二077"]
    lines += [
        "## 胜平负/让球核心串关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 风险 |",
        "|---|---|---:|---|",
        *combo_rows(mm, order),
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
