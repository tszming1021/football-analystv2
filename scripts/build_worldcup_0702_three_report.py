from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_worldcup_0629_nine_report import (
    cold_scores,
    decision_text,
    exact_total_text,
    leg_text,
    market_fusion_text,
    pct,
    qimen_text,
    top_scores,
    xg_text,
)


BASE = Path("data/worldcup_20260702_three")
MODEL_PATH = BASE / "model_analysis.json"
MARKET_PATH = BASE / "market/latest_market.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
REPORT_OUT = BASE / "2026-07-02世界杯淘汰赛083-085_三场90分钟专项报告.md"
TABLE_OUT = BASE / "2026-07-02世界杯淘汰赛083-085_核心推荐总表.md"


CORE = {
    "周四083": {
        "pick": "西班牙胜",
        "kind": "result",
        "key": "home",
        "conservative": "西班牙胜，防西班牙-1让平",
        "total": "2球，防3球",
        "cold": ("1-1", "0-0", "1-2", "2-2"),
        "tactical": "500主胜继续降到1.19，胜面足够；但西班牙边路伤停、淘汰赛卡线和奥地利反击使-1只作次级。",
    },
    "周四084": {
        "pick": "克罗地亚+1让胜",
        "kind": "handicap",
        "key": "fail",
        "conservative": "克罗地亚+1让胜，防让平",
        "total": "2球，防3球",
        "cold": ("0-1", "1-2", "2-2", "0-0"),
        "tactical": "葡萄牙90分钟胜面仍在，但让球端让负最低、平局权重31.3%，克罗地亚淘汰赛韧性更适合作+1。",
    },
    "周四085": {
        "pick": "阿尔及利亚+1让胜",
        "kind": "handicap",
        "key": "fail",
        "conservative": "阿尔及利亚+1让胜，防让平",
        "total": "2球，防1球",
        "cold": ("0-1", "1-2", "2-2", "0-0"),
        "tactical": "Amoura疑伤削弱阿尔及利亚反击上限，但500让球端仍强保护+1；瑞士胜面不足以支持追-1。",
    },
}

AGE_FACTORS = {
    "周四083": {
        "impact": "加分",
        "note": "西班牙年轻冲击点和控球续航更好，Yamal/Pedri这类高频触球与边路冲刺资源提高后程压制；但Pino/Nico Williams伤停削弱边路轮换，-1仍防卡线。",
        "confidence": "主胜信心小升，深盘信心不升。",
    },
    "周四084": {
        "impact": "受让小降",
        "note": "葡萄牙与克罗地亚都是老核心战，Ronaldo/Modric年龄都会压低连续高强度能力；葡萄牙替补冲击和阵容年龄层更均衡，克罗地亚+1保留但后程被2-1打穿的风险上升。",
        "confidence": "克罗地亚+1从价值主线降为价值防线，重点防葡萄牙2-1。",
    },
    "周四085": {
        "impact": "受让下调",
        "note": "瑞士Xhaka/Freuler经验中轴利于控节奏；阿尔及利亚Mahrez年龄偏大，Amoura疑伤削弱反击速度，+1仍有盘口保护但不宜作为最强腿。",
        "confidence": "阿尔及利亚+1保留，信心低于084。",
    },
}


def core_prob(match: dict, code: str) -> float:
    spec = CORE[code]
    if spec["kind"] == "result":
        return match["final"]["result"][spec["key"]]
    return match["final"]["handicap_home_settlement"][spec["key"]]


def conservative_prob(match: dict, code: str) -> float:
    h = match["final"]["handicap_home_settlement"]
    r = match["final"]["result"]
    if CORE[code]["kind"] == "result":
        return r["home"] + h["push"] * 0.35
    return h["fail"] + h["push"]


def handicap_text(match: dict) -> str:
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    h = match["final"]["handicap_home_settlement"]
    return (
        f"{home}-1：让胜{pct(h['cover'])} / 让平{pct(h['push'])} / 让负{pct(h['fail'])}；"
        f"{away}+1：让胜{pct(h['fail'])} / 让平{pct(h['push'])} / 让负{pct(h['cover'])}"
    )


def summary_rows(model: dict) -> list[str]:
    rows = []
    for match in model["matches"]:
        code = match["identity"]["code"]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        spec = CORE[code]
        rows.append(
            f"| {code}{match['identity']['home']}vs{match['identity']['away']} | **{spec['pick']}** | {pct(core_prob(match, code))} | "
            f"{spec['conservative']} | {pct(conservative_prob(match, code))} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | "
            f"{spec['total']} | {exact_total_text(match)} | {top_scores(match)} |"
        )
    return rows


def table(model: dict, market: dict) -> str:
    lines = [
        "# 2026-07-02 世界杯淘汰赛083-085 核心推荐总表",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500 PDF主表 {market['fetched_at']}。全部按90分钟结算。",
        "",
        "| 场次 | 主推 | 概率 | 保守方向 | 概率 | 胜/平/负 | 主队-1让胜/平/负 | 总球 | 总球概率 | 比分Top3 |",
        "|---|---|---:|---|---:|---:|---:|---|---:|---|",
        *summary_rows(model),
        "",
        "## 年龄叠加后排序",
        "",
        "| 场次 | 年龄影响 | 结论 |",
        "|---|---|---|",
        *[
            f"| {code} | {AGE_FACTORS[code]['impact']} | {AGE_FACTORS[code]['confidence']} |"
            for code in ["周四083", "周四084", "周四085"]
        ],
        "",
        "## 主推组合",
        "",
        "- 稳健主线：西班牙胜。",
        "- 价值主线：克罗地亚+1让胜；阿尔及利亚+1让胜降为防守型选择。",
        "- 年龄叠加后最优2串：西班牙胜 × 克罗地亚+1让胜。",
        "- 不追方向：葡萄牙-1让胜、瑞士-1让胜；西班牙-1只作让平防线。",
    ]
    return "\n".join(lines) + "\n"


def report(model: dict, market: dict, audit: dict) -> str:
    lines = [
        "# 2026-07-02 世界杯淘汰赛083-085 三场90分钟专项报告",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500 PDF主表 {market['fetched_at']}；API-Football {audit['fetched_at']}。胜平负、让球、比分、总球均按90分钟结算。",
        "",
        "## 主推建议",
        "",
        "- **083 西班牙vs奥地利**：西班牙胜；防西班牙-1让平。",
        "- **084 葡萄牙vs克罗地亚**：克罗地亚+1让胜；防让平。",
        "- **085 瑞士vs阿尔及利亚**：阿尔及利亚+1让胜；防让平，信心低于084。",
        "",
        "## 步骤审计",
        "",
        "- 已解析用户提供的500 PDF；文件创建时间2026-07-02 14:40 CST，共2页，含083-085三场主表、让球、比分、总球。",
        "- 500网页实时抓取因DNS解析失败未完成；本报告用PDF主表覆盖，深层欧赔/亚盘/大小球沿用2026-07-01缓存并降权披露。",
        "- API-Football已请求fixture/predictions/injuries/lineups/statistics/odds；085 statistics端点代理断开一次，正式首发均未发布。",
        "- 已执行去水/贝叶斯融合、proxy xG/xGA、LEG、复盘校准、决策迭代、一致性检查和奇门低权重辅助。",
        "- 已叠加年龄/体能层：年龄因素只修正信心、后程风险和组合排序，不直接覆盖数学模型概率。",
        "- 联网复核只进入事实层，直接概率权重0%。",
        "",
        "## 年龄/体能叠加层",
        "",
        "| 场次 | 年龄影响 | 体能与后程风险 | 调整后执行 |",
        "|---|---|---|---|",
        *[
            f"| {code} | {AGE_FACTORS[code]['impact']} | {AGE_FACTORS[code]['note']} | {AGE_FACTORS[code]['confidence']} |"
            for code in ["周四083", "周四084", "周四085"]
        ],
        "",
        "## 总推荐表",
        "",
        "| 场次 | 主推 | 概率 | 保守方向 | 概率 | 胜/平/负 | 主队-1让胜/平/负 | 总球 | 总球概率 | 比分Top3 |",
        "|---|---|---:|---|---:|---:|---:|---|---:|---|",
        *summary_rows(model),
        "",
        "## 单场分析",
        "",
    ]
    for match in model["matches"]:
        code = match["identity"]["code"]
        spec = CORE[code]
        r = match["final"]["result"]
        consistency = match["consistency"]
        lines += [
            f"### {code} {match['identity']['home']} vs {match['identity']['away']}",
            "",
            f"- **主推方向**：{spec['pick']}，概率{pct(core_prob(match, code))}；保守方向：{spec['conservative']}，覆盖{pct(conservative_prob(match, code))}。",
            f"- **胜平负**：{match['identity']['home']}胜{pct(r['home'])}，平{pct(r['draw'])}，{match['identity']['away']}胜{pct(r['away'])}。",
            f"- **让球胜平负**：{handicap_text(match)}。",
            f"- **总球/比分**：{spec['total']}；{exact_total_text(match)}；比分Top3：{top_scores(match)}；冷门保护：{cold_scores(match, spec['cold'])}。",
            f"- **去水与贝叶斯融合**：{market_fusion_text(match)}。",
            f"- **xG/xGA层**：{xg_text(match)}。",
            f"- **LEG层**：{leg_text(match)}。",
            f"- **决策迭代**：{decision_text(match)}。",
            f"- **奇门辅助**：{qimen_text(match)}",
            f"- **场馆天气/事实**：{match['source_facts']['weather']}",
            f"- **首发伤停**：{match['source_facts']['absence_note']}",
            f"- **API状态**：{json.dumps(match['source_facts']['api_endpoint_status'], ensure_ascii=False)}。",
            f"- **年龄/体能叠加**：{AGE_FACTORS[code]['note']} {AGE_FACTORS[code]['confidence']}",
            f"- **判断**：{spec['tactical']}",
            f"- **一致性审计**：{consistency['status']}；{'；'.join(consistency['warnings'] or consistency['notes'])}",
            "",
        ]
    lines += [
        "## 来源",
        "",
        "- 本地PDF：/Users/jamesm/Desktop/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.pdf",
        "- 500竞彩足球：https://trade.500.com/jczq/index.php?playid=312&g=2",
        "- API-Football：https://www.api-football.com/",
        "- FIFA 2026赛程：https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums",
        "- ESPN西班牙伤停复核：https://www.espn.com/soccer/story/_/id/49227164/are-european-champions-spain-world-cup-favorites",
        "- Goal西班牙vs奥地利赛前：https://www.goal.com/en-us/news/spain-austria-world-cup-preview/bltd6228bcab13b7c80",
        "- SportsMole葡萄牙vs克罗地亚赛前：https://www.sportsmole.co.uk/football/portugal/world-cup-2026/preview/portugal-vs-croatia-prediction-team-news-lineups_600433.html",
        "- Goal葡萄牙vs克罗地亚赛前：https://www.goal.com/en/news/portugal-croatia-world-cup-preview/blt9fb0907531786204",
        "- WhoScored瑞士vs阿尔及利亚统计预览：https://www.whoscored.com/matches/1992066/preview/international-fifa-world-cup-2026-switzerland-algeria",
        "- SportsMole瑞士vs阿尔及利亚伤停/预计首发：https://www.sportsmole.co.uk/football/switzerland/world-cup-2026/team-news/switzerland-vs-algeria-injury-suspension-list-predicted-xis_600443.html",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    audit = json.loads(API_AUDIT_PATH.read_text(encoding="utf-8"))
    TABLE_OUT.write_text(table(model, market), encoding="utf-8")
    REPORT_OUT.write_text(report(model, market, audit), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
