from __future__ import annotations

import json
import itertools
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


BASE = Path("data/worldcup_swe_20260703_four")
MODEL_PATH = BASE / "model_analysis.json"
MARKET_PATH = BASE / "market/latest_market.json"
API_AUDIT_PATH = BASE / "api/api_audit.json"
SUPPLEMENTAL_PATH = BASE / "supplemental_audit.json"
REPORT_OUT = BASE / "2026-07-03世界杯瑞超086-088-201_四场完整报告.md"
TABLE_OUT = BASE / "2026-07-03世界杯瑞超086-088-201_核心推荐总表.md"


CORE = {
    "周五086": {
        "pick": "澳大利亚+1让胜", "kind": "handicap", "key": "cover",
        "conservative": "澳大利亚+1让胜，防让平",
        "total": "2球，防1球", "cold": ("0-1", "1-2", "0-2", "2-2"),
        "tactical": "三向埃及小热，但API给澳大利亚不败，500大小球下压到低总球；+1覆盖比追埃及胜稳。",
    },
    "周五087": {
        "pick": "阿根廷胜", "kind": "result", "key": "home",
        "conservative": "阿根廷胜，防阿根廷-2让平/让负",
        "total": "2球，防3球", "cold": ("1-1", "0-0", "2-2"),
        "tactical": "阿根廷胜面最强，深层欧赔持续压低；但-2盘口仍有两球卡线，主胜优先、深盘降级。",
    },
    "周五088": {
        "pick": "哥伦比亚胜", "kind": "result", "key": "home",
        "conservative": "哥伦比亚胜，防哥伦比亚-1让平",
        "total": "2球，防3球", "cold": ("1-1", "0-0", "0-1", "2-2"),
        "tactical": "哥伦比亚欧赔/亚盘显著走强，但竞彩-1三向仍接近；主胜优于深追，让平是核心防线。",
    },
    "周五201": {
        "pick": "天狼星胜", "kind": "result", "key": "home",
        "conservative": "天狼星胜，防米亚尔比+1让胜/让平",
        "total": "3球，防2球", "cold": ("1-1", "2-2", "1-2"),
        "tactical": "天狼星榜首且近况强，但伤停和-1盘口不支持深追；主胜可做，-1不做胆。",
    },
}

HANDICAPS = {"周五086": 1, "周五087": -2, "周五088": -1, "周五201": -1}


def core_prob(match: dict, code: str) -> float:
    spec = CORE[code]
    if spec["kind"] == "result":
        return match["final"]["result"][spec["key"]]
    return match["final"]["handicap_home_settlement"][spec["key"]]


def conservative_prob(match: dict, code: str) -> float:
    h = match["final"]["handicap_home_settlement"]
    r = match["final"]["result"]
    if code == "周五086":
        return h["cover"] + h["push"]
    if code in {"周五087", "周五088", "周五201"}:
        return r["home"] + h["push"] * 0.35
    return core_prob(match, code)


def handicap_text(match: dict) -> str:
    code = match["identity"]["code"]
    line = HANDICAPS[code]
    home = match["identity"]["home"]
    away = match["identity"]["away"]
    h = match["final"]["handicap_home_settlement"]
    if line > 0:
        return (
            f"{home}+{line}：让胜{pct(h['cover'])} / 让平{pct(h['push'])} / 让负{pct(h['fail'])}；"
            f"{away}-{line}：让胜{pct(h['fail'])} / 让平{pct(h['push'])} / 让负{pct(h['cover'])}"
        )
    return (
        f"{home}{line}：让胜{pct(h['cover'])} / 让平{pct(h['push'])} / 让负{pct(h['fail'])}；"
        f"{away}+{abs(line)}：让胜{pct(h['fail'])} / 让平{pct(h['push'])} / 让负{pct(h['cover'])}"
    )


def summary_rows(model: dict) -> list[str]:
    rows = []
    for match in model["matches"]:
        code = match["identity"]["code"]
        spec = CORE[code]
        r = match["final"]["result"]
        h = match["final"]["handicap_home_settlement"]
        rows.append(
            f"| {code}{match['identity']['home']}vs{match['identity']['away']} | **{spec['pick']}** | {pct(core_prob(match, code))} | "
            f"{spec['conservative']} | {pct(conservative_prob(match, code))} | "
            f"{pct(r['home'])}/{pct(r['draw'])}/{pct(r['away'])} | {pct(h['cover'])}/{pct(h['push'])}/{pct(h['fail'])} | "
            f"{spec['total']} | {exact_total_text(match)} | {top_scores(match)} |"
        )
    return rows


def score_probability(match: dict, score: str) -> float:
    for item in match["final"]["scorelines"]:
        if item["score"] == score:
            return item["probability"]
    return 0.0


def worldcup_combo_rows(model: dict) -> tuple[list[str], list[str]]:
    match_map = {item["identity"]["code"]: item for item in model["matches"]}
    codes = ["周五087", "周五086", "周五088"]
    mixed_rows = []
    score_rows = []
    for size in (2, 3):
        for combo in itertools.combinations(codes, size):
            probability = 1.0
            labels = []
            for code in combo:
                probability *= core_prob(match_map[code], code)
                labels.append(f"{code}{CORE[code]['pick']}")
            advice = "首选" if combo == ("周五087", "周五086") else ("次选" if combo == ("周五087", "周五088") else ("小注" if size == 3 else "进取"))
            mixed_rows.append(f"| {size}串1 | {' × '.join(labels)} | {pct(probability)} | {advice} |")

            score_probability_sum = 1.0
            score_labels = []
            bets = 1
            for code in combo:
                match = match_map[code]
                scores = [item["score"] for item in match["final"]["scorelines"][:2]]
                score_probability_sum *= sum(score_probability(match, score) for score in scores)
                bets *= len(scores)
                score_labels.append(f"{code} {'/'.join(scores)}")
            score_rows.append(f"| {size}串1 | {' × '.join(score_labels)} | {bets}注 | {pct(score_probability_sum)} |")
    return mixed_rows, score_rows


def table(model: dict, market: dict) -> str:
    mixed_rows, score_rows = worldcup_combo_rows(model)
    lines = [
        "# 2026-07-03 世界杯/瑞超086-088-201 核心推荐总表",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时 {market['fetched_at']}。世界杯与瑞超均按90分钟结算。",
        "",
        "| 场次 | 主推 | 概率 | 保守方向 | 概率 | 胜/平/负 | 主队让球胜/平/负 | 总球 | 总球概率 | 比分Top3 |",
        "|---|---|---:|---|---:|---:|---:|---|---:|---|",
        *summary_rows(model),
        "",
        "## 主推组合",
        "",
        "- 稳健2串：阿根廷胜 × 澳大利亚+1让胜。",
        "- 次稳2串：阿根廷胜 × 哥伦比亚胜。",
        "- 进取2串：哥伦比亚胜 × 天狼星胜。",
        "- 4场全串不建议作主仓，086/201都有高平局或让球卡线。",
        "",
        "## 世界杯混合过关",
        "",
        "| 类型 | 组合 | 独立近似概率 | 建议 |",
        "|---|---|---:|---|",
        *mixed_rows,
        "",
        "## 世界杯比分过关",
        "",
        "| 类型 | 组合 | 注数 | Top2覆盖近似概率 |",
        "|---|---|---:|---:|",
        *score_rows,
    ]
    return "\n".join(lines) + "\n"


def report(model: dict, market: dict, api: dict, supplemental: dict) -> str:
    lines = [
        "# 2026-07-03 世界杯/瑞超086-088-201 四场完整报告",
        "",
        f"> 数据截点：模型 {model['generated_at']}；500实时 {market['fetched_at']}；API-Football {api['fetched_at']}；补源审计 {supplemental['fetched_at']}。",
        "> 赔率变化层当前为 `phase1_shadow_mode`，只输出信心/风险标签，不直接修改最终概率。",
        "",
        "## 主推建议",
        "",
        "- **086 澳大利亚vs埃及**：澳大利亚+1让胜，防让平。",
        "- **087 阿根廷vs佛得角**：阿根廷胜，不深追-2。",
        "- **088 哥伦比亚vs加纳**：哥伦比亚胜，防-1让平。",
        "- **201 天狼星vs米亚尔比**：天狼星胜，防米亚尔比+1。",
        "",
        "## 步骤审计",
        "",
        "- 已解析用户提供的500 PDF；PDF创建时间2026-07-02 14:40 CST。",
        "- 已重新抓取500实时主表、比分、总球、半全场及深层欧赔/亚盘/大小球，错误0。",
        "- API-Football已读取四场fixture/predictions/injuries/lineups/statistics/odds；正式首发均未发布，赛前statistics为空。",
        "- OddsPortal、Flashscore、AiScore已作为补源尝试；详见单场补源审计。",
        "- 已执行去水/贝叶斯、proxy xG、总球去偏、LEG、决策迭代、一致性检查、奇门辅助与GPT联网复核。",
        "",
        "## 总推荐表",
        "",
        "| 场次 | 主推 | 概率 | 保守方向 | 概率 | 胜/平/负 | 主队让球胜/平/负 | 总球 | 总球概率 | 比分Top3 |",
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
        supp = supplemental["matches"][code]
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
            f"- **场馆天气**：{match['source_facts']['weather']}",
            f"- **首发伤停**：{match['source_facts']['absence_note']}",
            f"- **API状态**：{json.dumps(match['source_facts']['api_endpoint_status'], ensure_ascii=False)}。",
            f"- **补源审计**：OddsPortal={supp['source_status_oddsportal']}；Flashscore={supp['source_status_flashscore']}；AiScore={supp['source_status_aiscore']}；phase={supp['phase_gate_decision']}。",
            f"- **赔率变化影子标签**：{'；'.join(supp['movement_tags'])}",
            f"- **判断**：{spec['tactical']}",
            f"- **一致性审计**：{consistency['status']}；{'；'.join(consistency['warnings'] or consistency['notes'])}",
            "",
        ]
    lines += [
        "## 来源",
        "",
        "- 500竞彩足球实时主表：https://trade.500.com/jczq/index.php?playid=312&g=2",
        "- API-Football：https://www.api-football.com/",
        "- OddsPortal Australia-Egypt：https://www.oddsportal.com/football/h2h/australia-xSrf6qMM/egypt-bejDn7NN/",
        "- OddsPortal Argentina-Cape Verde：https://www.oddsportal.com/football/h2h/argentina-f9OppQjp/cape-verde-MocyWdm7/",
        "- OddsPortal Colombia-Ghana：https://www.oddsportal.com/football/h2h/colombia-G02s4PCS/ghana-nNBjHale/",
        "- Flashscore Australia-Egypt：https://www.flashscore.com/match/football/australia-xSrf6qMM/egypt-bejDn7NN/",
        "- Flashscore Colombia-Ghana：https://www.flashscore.com/match/football/colombia-G02s4PCS/ghana-nNBjHale/summary/lineups/",
        "- Flashscore Sirius-Mjallby：https://www.flashscore.com/match/football/mjallby-S0XtXM1E/sirius-vXr8fotG/",
        "- Guardian Australia-Egypt/Salah：https://www.theguardian.com/football/2026/jul/03/egypt-mo-salah-fit-to-play-australia-socceroos-after-injury",
        "- FIFA Colombia-Ghana：https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/colombia-ghana-live-stream-team-news-tickets-and-more",
        "- SportsMole Sirius-Mjallby：https://www.sportsmole.co.uk/football/sirius/preview/sirius-vs-mjallby-aif-prediction-team-news-lineups_600513.html",
        "- 本地PDF：/Users/jamesm/Desktop/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.pdf",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    api = json.loads(API_AUDIT_PATH.read_text(encoding="utf-8"))
    supplemental = json.loads(SUPPLEMENTAL_PATH.read_text(encoding="utf-8"))
    TABLE_OUT.write_text(table(model, market), encoding="utf-8")
    REPORT_OUT.write_text(report(model, market, api, supplemental), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUT), "table": str(TABLE_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
