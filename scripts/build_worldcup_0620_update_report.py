from __future__ import annotations

import json
from pathlib import Path


BASE = Path("data/worldcup_20260621")
OLD_MODEL = BASE / "model_analysis.json"
NEW_MODEL = BASE / "model_analysis_1847.json"
DIFF_JSON = BASE / "update_diff_1847.json"
OUT = BASE / "2026-06-21世界杯周六033-036_1847更新对比报告.md"

MARKET_OLD = {
    "周六033": ("1.59 / 3.58 / 4.52", "-1: 2.86 / 3.45 / 2.04", "2.72", "-0.719"),
    "周六034": ("1.40 / 4.15 / 5.75", "-1: 2.23 / 3.65 / 2.46", "2.90", "-0.984"),
    "周六035": ("未开售；百家1.11 / 9.51 / 22.94", "-2: 1.90 / 3.95 / 2.86", "3.09", "-2.344"),
    "周六036": ("6.55 / 3.96 / 1.38", "+1: 2.50 / 3.40 / 2.30", "2.31", "+0.969"),
}

MARKET_NEW = {
    "周六033": ("1.53 / 3.83 / 4.65", "-1: 2.72 / 3.28 / 2.19", "2.76", "-0.719"),
    "周六034": ("1.34 / 4.70 / 5.90", "-1: 2.04 / 3.82 / 2.65", "2.90", "-0.984"),
    "周六035": ("未开售；百家1.12 / 8.93 / 22.01", "-2: 1.85 / 4.00 / 2.95", "3.04", "-2.281"),
    "周六036": ("6.36 / 3.95 / 1.39", "+1: 2.54 / 3.54 / 2.21", "2.31", "+0.969"),
}

MATCH_NOTES = {
    "周六033": [
        "荷兰胜由56.6%升至57.9%，市场对荷兰三向支持增强。",
        "荷兰-1让胜由27.9%升至29.4%，但让负仍以43.5%居首；结论仍是荷兰胜面高、赢深不足。",
        "总球均值由3.020升至3.138，4球及以上合计39.1%；总球范围从偏2-3球扩为2-4球。",
        "500新增预计阵容页与澳门推荐，澳门方向为和局；预计阵容无官方确认，不覆盖模型。",
    ],
    "周六034": [
        "德国胜由58.9%升至60.4%，是四场中主胜增幅最大的一场。",
        "德国-1让胜由33.2%升至35.8%，让负由39.6%降至37.6%，两端只差1.8个百分点；不再把让负列为高置信单选。",
        "总球均值由3.057升至3.137，3-1、4-0被提升为上沿覆盖；主线仍优先德国胜。",
        "500新增预计阵容页与澳门推荐，澳门方向为德国胜；伤停栏为空仍不等于官方确认全员可用。",
    ],
    "周六035": [
        "厄瓜多尔胜由72.5%微降至72.2%，赛果层基本不变。",
        "官方-2让胜数字走强，但亚洲平均线由-2.344退至-2.281、大小均线由3.09降至3.04，形成深度分歧。",
        "-2让负仍为42.9%的最高项，让胜33.0%；继续采用厄瓜多尔胜、-2让负保护，不追深盘。",
        "一致性检查提示卡线风险；比分保留3-0、3-1、4-0、4-1等上沿，不能只压2-0。",
    ],
    "周六036": [
        "日本胜由60.2%微降至60.0%，赛果主方向不变。",
        "突尼斯+1让负由33.6%升至34.3%，让胜由36.9%降至36.8%，日本赢两球以上信号增强，但三项仍非常接近。",
        "总球均值由2.512降至2.491，主区间仍为1-3球；0-2概率上升并进入概率前三。",
        "500新增预计阵容页与澳门推荐，澳门方向为日本胜；让球层继续保留突尼斯+1保护。",
    ],
}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def delta(old: float, new: float) -> str:
    return f"{(new - old) * 100:+.1f}pp"


def score_map(match: dict) -> dict[str, float]:
    return {item["score"]: item["probability"] for item in match["final"]["score_candidate_pool"]}


def rows() -> str:
    old = json.loads(OLD_MODEL.read_text(encoding="utf-8"))
    new = json.loads(NEW_MODEL.read_text(encoding="utf-8"))
    diff_data = json.loads(DIFF_JSON.read_text(encoding="utf-8"))
    old_by_code = {item["identity"]["code"]: item for item in old["matches"]}
    new_by_code = {item["identity"]["code"]: item for item in new["matches"]}

    lines = [
        "# 2026-06-21 世界杯周六033-036 最新数据更新对比报告",
        "",
        "> 更新截点：2026-06-20 18:47-18:48（Asia/Shanghai）。本报告是早晨严格报告的增量重算版；未变化的基本面、天气、API和联网证据沿用基准报告，不重复制造新结论。",
        "",
        "## 一、更新审计",
        "",
        f"- 已重新解析：5份更新PDF、16份OLE2/BIFF `.xls`，解析错误0。",
        f"- 未变化：4份Transfermarkt比赛页。",
        f"- 新目录缺失：4份早晨存在的500补充分析PDF；缺失不视为内容撤回，只记录为本轮未提供。",
        f"- 500四场数据分析页由3页增至4页，新增预计阵容和澳门推荐；预计阵容仍未官宣。",
        f"- 模型：继续执行去水、贝叶斯融合、proxy xG、Poisson/Dixon-Coles、LEG、校准规则、决策迭代、一致性检查和低权重奇门辅助。",
        "- API-Football既有快照：四场fixture/prediction有结果；injuries/lineups/statistics均为0行。本轮附件未提供新的API回包。",
        "- 真实赛前xG/xGA仍不可用，继续使用收缩后的proxy xG与世界杯离线模型，不把普通进失球均值冒充xG。",
        "",
        "## 二、市场数字更新",
        "",
        "| 场次 | 胜平负：早晨 -> 最新 | 让球三向：早晨 -> 最新 | 大小均线 | 亚洲均线 |",
        "|---|---|---|---:|---:|",
    ]
    for code in new_by_code:
        o = MARKET_OLD[code]
        n = MARKET_NEW[code]
        lines.append(f"| {code} | {o[0]} -> **{n[0]}** | {o[1]} -> **{n[1]}** | {o[2]} -> {n[2]} | {o[3]} -> {n[3]} |")

    lines.extend([
        "",
        "## 三、概率重算总表",
        "",
        "| 场次 | 最新胜/平/负 | 相对早晨变化 | 最新让球胜/平/负 | 最新总球均值 | 核心结论 |",
        "|---|---|---|---|---:|---|",
    ])
    conclusions = {
        "周六033": "荷兰胜；荷兰-1让负",
        "周六034": "德国胜；-1不单挑",
        "周六035": "厄瓜多尔胜；厄瓜多尔-2让负",
        "周六036": "日本胜；突尼斯+1让胜保护",
    }
    for code, current in new_by_code.items():
        previous = old_by_code[code]
        result = current["final"]["result"]
        old_result = previous["final"]["result"]
        handicap = current["final"]["handicap_home_settlement"]
        lines.append(
            f"| {code} {current['identity']['home']}vs{current['identity']['away']} | "
            f"{pct(result['home'])} / {pct(result['draw'])} / {pct(result['away'])} | "
            f"{delta(old_result['home'], result['home'])} / {delta(old_result['draw'], result['draw'])} / {delta(old_result['away'], result['away'])} | "
            f"{pct(handicap['cover'])} / {pct(handicap['push'])} / {pct(handicap['fail'])} | "
            f"{current['means']['decision_final']:.3f} | {conclusions[code]} |"
        )

    lines.extend([
        "",
        "说明：让球胜/平/负均按主队所列让球结算。周六036为突尼斯+1，因此让负代表日本至少赢2球。",
        "",
        "## 四、最新推荐总表",
        "",
        "| 场次 | 胜平负核心 | 让球建议 | 总球分析 | 概率前三比分 | 铁律推荐Top3 | 冷门比分 |",
        "|---|---|---|---|---|---|---|",
    ])
    score_sets = {
        "周六033": (["1-1", "2-1", "2-0"], ["2-0", "1-1", "3-0"], ["2-2", "2-3"]),
        "周六034": (["2-1", "2-0", "1-1"], ["1-1", "2-1", "3-1"], ["1-1", "2-2"]),
        "周六035": (["2-0", "1-0", "3-0"], ["1-0", "2-0", "3-0"], ["1-1", "2-2"]),
        "周六036": (["0-1", "0-2", "1-1"], ["1-1", "0-1", "0-3"], ["1-0", "2-2"]),
    }
    recommendations = {
        "周六033": ("荷兰胜", "荷兰-1让负", "2-4球；3球核心，4+为39.1%"),
        "周六034": ("德国胜", "德国-1让负/让胜双向", "2-4球；3球核心"),
        "周六035": ("厄瓜多尔胜", "厄瓜多尔-2让负", "3-4球；保留4+上沿"),
        "周六036": ("日本胜", "突尼斯+1让胜，防让负", "1-3球；2球核心"),
    }
    for code, current in new_by_code.items():
        probabilities, recommended, cold = score_sets[code]
        mapping = score_map(current)
        fmt = lambda scores: " / ".join(f"{score}({pct(mapping.get(score, 0.0))})" for score in scores)
        rec = recommendations[code]
        lines.append(f"| {code} | **{rec[0]}** | {rec[1]} | {rec[2]} | {fmt(probabilities)} | **{fmt(recommended)}** | {fmt(cold)} |")

    lines.extend([
        "",
        "铁律推荐Top3不是概率排序：前两位保守，第三位主动覆盖赢深上沿；概率前三单独列示，避免概念混淆。",
        "",
        "## 五、逐场更新",
    ])
    for code, current in new_by_code.items():
        lines.extend(["", f"### {code} {current['identity']['home']} vs {current['identity']['away']}"])
        lines.extend(f"- {note}" for note in MATCH_NOTES[code])
        if current["consistency"]["warnings"]:
            lines.append("- 一致性提示：" + "；".join(current["consistency"]["warnings"]) + "。")

    lines.extend([
        "",
        "## 六、组合方案更新",
        "",
        "| 类型 | 最新组合 | 与早晨相比 |",
        "|---|---|---|",
        "| 稳健2串1 | 德国胜 × 日本胜 | 不变 |",
        "| 保护2串1 | 荷兰-1让负 × 厄瓜多尔-2让负 | 不变，但荷兰让负概率下降2.1pp |",
        "| 进取3串1 | 荷兰-1让负 × 德国胜 × 日本胜 | 结构不变；德国胜增强 |",
        "| 4串1 | 荷兰-1让负 × 德国胜 × 厄瓜多尔-2让负 × 日本胜 | 结构不变；仍属高波动组合 |",
        "| 比分2串1 | 德国 2-1/3-1 × 日本 0-1/0-2 | 德国新增3-1上沿，日本0-2增强 |",
        "| 比分3串1 | 荷兰 2-0/3-0 × 德国 2-1/3-1 × 日本 0-1/0-2 | 荷兰加入3-0上沿 |",
        "| 比分4串1 | 荷兰 2-0/3-0 × 德国 2-1/3-1 × 厄瓜多尔 2-0/3-0 × 日本 0-1/0-2 | 仅作小权重覆盖 |",
        "",
        "## 七、最终变化结论",
        "",
        "1. 四场胜平负主方向均未翻转：荷兰胜、德国胜、厄瓜多尔胜、日本胜。",
        "2. 德国是本次最明确的增强项；德国胜升级，但德国-1仍不适合单选。",
        "3. 荷兰胜增强、赢深略改善，但-1让负仍是最高项，原保护逻辑不变。",
        "4. 厄瓜多尔出现官方与亚洲深盘分歧，继续只认胜面、不追-2穿盘。",
        "5. 日本胜面基本不变，0-2与赢两球以上路径增强；突尼斯+1三项仍接近。",
        "6. 组合框架不换，只调整权重：德国胜上调，荷兰-1让负略降，厄瓜多尔深盘保持谨慎。",
        "",
        "## 八、审计文件",
        "",
        f"- 旧模型：`{OLD_MODEL}`",
        f"- 新模型：`{NEW_MODEL}`",
        f"- 文件级差异：`{DIFF_JSON}`",
        f"- 更新文件统计：PDF变化{sum(x.get('status') == 'changed' for x in diff_data['pdfs'].values())}份，XLS变化{sum(x.get('status') == 'changed' for x in diff_data['xls'].values())}份，解析错误{len(diff_data['errors'])}。",
        "",
        "> 风险提示：概率是模型在当前数据截点下的估计，不是赛果保证。临场首发若出现核心缺阵、门将更换或盘口跨档，需要再次重算。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.write_text(rows(), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
