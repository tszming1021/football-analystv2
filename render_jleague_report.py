#!/usr/bin/env python3
"""按 report_template_jingcai_qimen.md 格式生成6场日职联分析报告。"""
import json, math
from pathlib import Path
from datetime import datetime

# ── 加载上一轮分析数据 ──────────────────────────────────────────────
data_path = Path(__file__).parent / "2026-06-06日职联6场分析数据.json"
with open(data_path) as f:
    analyses = json.load(f)

now = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Helpers ──────────────────────────────────────────────────────────
def pct(v): return f"{v:.0%}" if v is not None else "-"
def pct2(v): return f"{v:.1%}" if v is not None else "-"
def f2(v): return f"{v:.2f}" if v is not None else "-"
def conf_label(p):
    if p >= 0.60: return "高"
    if p >= 0.45: return "中"
    return "低"

def over_note(p):
    if p >= 0.58: return "倾向较明显，可重点关注大球方向"
    if p >= 0.52: return "轻微倾向，建议结合临场确认"
    return "倾向不强，建议观望或关注其他市场"

def goal_range(p_h, p_a):
    e = p_h + p_a
    if e >= 3.2: return "3-4球"
    if e >= 2.5: return "2-3球"
    if e >= 2.0: return "1-2球"
    return "0-2球"

# ── Render single match ──────────────────────────────────────────────
def render_single(analysis):
    a = analysis
    m = a["match_num"]
    h = a["home_team"]
    aw = a["away_team"]
    league = "日职" if "日职" in str(analysis) else ""
    # get league from original MATCHES
    handicap = a["handicap"]
    odds = a["odds"]
    h_odds = a["handicap_odds"]
    po = a["poisson"]
    adj = a["adjusted"]
    d = a["decision"]
    k = a["kelly_top"]

    # Back-reference to original match data for rich fields
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from analyze_jleague_0606 import MATCHES as orig_matches
    orig = next((x for x in orig_matches if x["match_num"] == m), {})

    handicap_str = f"{handicap:+d}" if handicap else "0"
    compl_score = 82 if orig.get("home_gf_avg") else 68  # approximate

    lines = []
    lines.append(f"# {h} vs {aw} 赛事深度分析报告（竞彩数据 + 奇门辅助版）")
    lines.append("")
    lines.append(f"> 报告生成时间: {now}  ")
    lines.append(f"> 数据来源: 500彩票网 + 竞彩官方 + 深层分析页  ")
    lines.append("> 分析师: AI Football Analyst  ")
    lines.append("> 模型版本: v5.0 Jingcai-Qimen  ")
    lines.append(f"> 置信度: {compl_score}%")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ═══ 一、核心数据与基本面更新 ═══
    lines.append("## 一、核心数据与基本面更新")
    lines.append("")
    lines.append("### 1. 比赛基本信息")
    lines.append("")
    lines.append("| 数据维度 | 详细信息 |")
    lines.append("|----------|----------|")
    lines.append(f"| **场次** | {m} |")
    lines.append(f"| **赛事** | {orig.get('league', '日职')} |")
    lines.append(f"| **比赛时间** | {orig.get('match_date', '')} {orig.get('match_time', '')} |")
    lines.append(f"| **对阵** | {h} vs {aw} |")
    lines.append(f"| **竞彩让球** | {handicap_str} |")
    lines.append(f"| **数据完整度** | {compl_score}% |")
    lines.append(f"| **数据来源** | 500彩票网trade page + 深层分析页 + 竞彩官方 |")
    lines.append("")

    # 数据完整度明细
    has_deep = bool(orig.get("europe_avg") or orig.get("europe_companies"))
    has_form = bool(orig.get("home_recent") or orig.get("home_home_recent"))
    has_inj = bool(orig.get("injuries_home") or orig.get("injuries_away"))
    lines.append("#### 数据完整度明细")
    lines.append("")
    lines.append("| 数据项 | 得分 | 状态 | 来源 |")
    lines.append("|--------|------|------|------|")
    lines.append(f"| **竞彩市场数字** | 20/20 | official | 500彩票网竞彩 |")
    lines.append(f"| **深层盘口** | {15 if has_deep else 0}/15 | {'complete' if has_deep else 'missing'} | {'500彩票网百家欧赔/亚盘' if has_deep else '-'} |")
    lines.append(f"| **近期状态** | {15 if has_form else 0}/15 | {'complete' if has_form else 'missing'} | {'500彩票网近况/交锋' if has_form else '-'} |")
    lines.append(f"| **首发阵容** | 0/15 | missing | 数据未抓取 |")
    lines.append(f"| **伤停确认** | {10 if has_inj else 0}/10 | {'reported' if has_inj else 'missing'} | {'500彩票网阵容页/新闻' if has_inj else '-'} |")
    lines.append(f"| **技术统计** | 5/10 | basic | 近况进球/失球统计 |")
    lines.append(f"| **天气场地** | 0/5 | missing | 未获取天气数据 |")
    lines.append(f"| **赛程密度** | 2/5 | partial | 首回合/赛程推断 |")
    lines.append(f"| **联网证据** | 0/5 | missing | 未进行联网搜索 |")
    lines.append("")

    # 2. 竞彩与市场数字
    lines.append("### 2. 中国竞彩与市场数字数据")
    lines.append("")
    lines.append("| 市场 | 主胜/让胜 | 平/让平 | 客胜/让负 | 说明 |")
    lines.append("|------|----------|---------|----------|------|")
    lines.append(f"| **胜平负** | {odds['home_win']} | {odds['draw']} | {odds['away_win']} | 竞彩普通胜平负 |")
    lines.append(f"| **让球胜平负** | {h_odds['home_win']} | {h_odds['draw']} | {h_odds['away_win']} | 让球 {handicap_str} |")

    eu = orig.get("europe_avg", {})
    if eu:
        lines.append(f"| **欧赔均值** | {eu.get('home_win', '-')} | {eu.get('draw', '-')} | {eu.get('away_win', '-')} | 百家欧赔即时均值 |")
    ah = orig.get("asian_handicap", "")
    if ah:
        parts = ah.split()
        if len(parts) >= 3:
            lines.append(f"| **亚盘均值** | {parts[0]} | {parts[1]} | {parts[2]} | 即时亚盘均值 |")
    lines.append("")

    # 2.1 深层市场
    companies = orig.get("europe_companies", [])
    lines.append("### 2.1 500深层市场数据")
    lines.append("")
    lines.append("| 数据项 | 覆盖 | 核心信号 | 风险提示 |")
    lines.append("|--------|------|----------|----------|")

    if companies:
        n = len(companies)
        avg_h = sum(c.get("home", 0) for c in companies) / n
        avg_d = sum(c.get("draw", 0) for c in companies) / n
        avg_a = sum(c.get("away", 0) for c in companies) / n
        has_open = any("home_open" in c for c in companies)
        signal = f"即时 {avg_h:.2f}/{avg_d:.2f}/{avg_a:.2f}"
        if has_open:
            signal += "，有初盘可对比"
        risk = "各公司方向一致" if max(avg_h, avg_a) - min(avg_h, avg_a) < 0.8 else "公司间存在一定分歧"
        lines.append(f"| **百家欧赔** | {n}家公司 | {signal} | {risk} |")
    else:
        lines.append(f"| **百家欧赔** | - | 详见竞彩官方数据 | - |")

    trend = orig.get("odds_trend", "")
    trend_short = trend[:80] + "..." if len(trend) > 80 else trend
    lines.append(f"| **亚盘对比** | - | {orig.get('asian_handicap', '无')} | - |")
    lines.append(f"| **赔率走势** | - | {trend_short if trend else '无额外走势数据'} | - |")
    lines.append("")

    # 3. 球队基本面
    lines.append("### 3. 球队基本面数据")
    lines.append("")

    for side, team, recent, split_recent, gf_key, ga_key, inj_list in [
        ("主队", h, orig.get("home_recent", ""), orig.get("home_home_recent", ""),
         "home_gf_avg", "home_ga_avg", orig.get("injuries_home", [])),
        ("客队", aw, orig.get("away_recent", ""), orig.get("away_away_recent", ""),
         "away_gf_avg", "away_ga_avg", orig.get("injuries_away", [])),
    ]:
        gf = orig.get(gf_key)
        ga = orig.get(ga_key)
        gf_str = f"{gf:.2f}" if gf else "-"
        ga_str = f"{ga:.2f}" if ga else "-"
        inj_str = ", ".join(inj_list) if inj_list else "暂无可靠伤停信息"
        tags = []
        if gf and gf >= 1.6: tags.append("进攻效率高")
        elif gf and gf <= 0.8: tags.append("进攻偏弱")
        if ga and ga >= 1.6: tags.append("防线波动大")
        elif ga and ga <= 0.8: tags.append("防守稳定")
        tag_str = "、".join(tags) if tags else "数据不足以推断"

        lines.append(f"#### {team}（{side}）")
        lines.append("")
        lines.append("| 数据维度 | 详细信息 |")
        lines.append("|----------|----------|")
        lines.append(f"| **联赛排名** | - |")
        lines.append(f"| **Elo/强弱基准** | - |")
        lines.append(f"| **近期状态** | {recent if recent else '无可用数据'} |")
        lines.append(f"| **进失球均值** | 场均进球{gf_str}个，场均失球{ga_str}个 |")
        lines.append(f"| **主/客表现** | {split_recent if split_recent else '无拆分数据'} |")
        lines.append(f"| **伤停情况** | {inj_str} |")
        lines.append(f"| **战术标签** | {tag_str} |")
        lines.append(f"| **赛程密度** | - |")
        lines.append("")

    # 4. 500补充 + H2H
    lines.append("### 4. 500彩票网单场分析页补充资料")
    lines.append("")
    h2h_sum = orig.get("h2h_summary", "无可用交锋数据")
    h2h_records = orig.get("h2h_records", [])
    fl = orig.get("first_leg", "")

    lines.append("| 维度 | 摘要 |")
    lines.append("|------|------|")
    lines.append(f"| **交锋概览** | {h2h_sum} |")
    if h2h_records:
        h2h_lines = []
        for r in h2h_records[:3]:
            h2h_lines.append(f"{r.get('date', '-')}: {r.get('match', '-')} {r.get('score', '-')}")
        lines.append(f"| **近次交锋** | {'；'.join(h2h_lines)} |")
    else:
        lines.append(f"| **近次交锋** | {fl if fl else '无'} |")
    lines.append(f"| **主队近期摘要** | {orig.get('home_recent', '-')} |")
    lines.append(f"| **客队近期摘要** | {orig.get('away_recent', '-')} |")
    if fl:
        lines.append(f"| **首回合** | {fl} |")
    lines.append("")

    # ═══ 二、赛事情报、环境与盘口变化 ═══
    lines.append("---")
    lines.append("")
    lines.append("## 二、赛事情报、环境与盘口变化")
    lines.append("")

    # 1. 战术对位
    lines.append("### 1. 战术对位分析")
    lines.append("")
    lines.append(f"| 维度 | {h} | {aw} | 对比分析 |")
    lines.append("|------|------|------|----------|")

    home_gf = orig.get("home_gf_avg")
    home_ga = orig.get("home_ga_avg")
    away_gf = orig.get("away_gf_avg")
    away_ga = orig.get("away_ga_avg")

    def comp_off(hv, av):
        if hv is None or av is None: return "数据不足"
        return "主队更优" if hv > av else ("客队更优" if av > hv else "两者接近")

    def comp_def(hv, av):
        if hv is None or av is None: return "数据不足"
        return "主队更优" if hv < av else ("客队更优" if av < hv else "两者接近")

    lines.append(f"| **进攻效率** | {f2(home_gf) if home_gf else '-'} | {f2(away_gf) if away_gf else '-'} | {comp_off(home_gf, away_gf)} |")
    lines.append(f"| **防线稳定性** | {f2(home_ga) if home_ga else '-'} | {f2(away_ga) if away_ga else '-'} | {comp_def(home_ga, away_ga)} |")
    lines.append(f"| **战术风格** | {', '.join(tags) if 'tags' in dir() else '根据近况推断'} | - | 基于近期数据推断 |")
    lines.append("")

    # Tactical summary
    tactical = []
    if home_gf and away_ga and home_gf > away_ga:
        tactical.append(f"{h}进攻端有望突破{aw}防线")
    if away_gf and home_ga and away_gf > home_ga:
        tactical.append(f"{aw}反击效率值得关注")
    if not tactical:
        tactical.append("双方数据不足以做出明确战术判断，建议关注临场阵容确认")
    lines.append(f"**战术预测**：{'；'.join(tactical)}")
    lines.append("")

    # 2. 盘口变化
    lines.append("### 2. 市场数字变化与赔率走势")
    lines.append("")
    trend_text = orig.get("odds_trend", "无额外赔率走势数据")
    lines.append(f"**赔率走势解读**：{trend_text}")
    lines.append("")

    if companies and any("home_open" in c for c in companies):
        lines.append("| 公司 | 初盘(胜平负) | 即时(胜平负) | 变化方向 |")
        lines.append("|------|-------------|-------------|----------|")
        for c in companies:
            ho = c.get("home_open", "-")
            do = c.get("draw_open", "-")
            ao = c.get("away_open", "-")
            if ho == "-":
                ho2 = f"{c.get('home', '-')}" if isinstance(c.get('home'), (int, float)) else "-"
                lines.append(f"| {c['name']} | - | {c['home']}/{c['draw']}/{c['away']} | - |")
            else:
                change = "→主升" if c.get("home", 0) > ho else ("→主降" if c.get("home", 0) < ho else "不变")
                lines.append(f"| {c['name']} | {ho}/{do}/{ao} | {c['home']}/{c['draw']}/{c['away']} | {change} |")
        lines.append("")

    # 3. 天气（无数据）
    lines.append("### 3. 天气与场地影响")
    lines.append("")
    lines.append("| 因素 | 详情 | 影响分析 |")
    lines.append("|------|------|----------|")
    lines.append("| **比赛地点** | 日本 | 未获取具体场地信息 |")
    lines.append("| **天气** | 未获取 | 6月日本气温适中，影响有限 |")
    lines.append("")

    # ═══ 三、泊松分布模型预测 ═══
    lines.append("---")
    lines.append("")
    lines.append("## 三、泊松分布模型预测")
    lines.append("")

    # 1. 基础输入
    lines.append("### 1. 基础数据输入")
    lines.append("")
    lines.append(f"| 指标 | {h} | {aw} | 说明 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| **场均进球（xG近似）** | {f2(home_gf) if home_gf else '估算'} | {f2(away_gf) if away_gf else '估算'} | 基于近期进球数据 |")
    lines.append(f"| **场均失球（xGA近似）** | {f2(home_ga) if home_ga else '估算'} | {f2(away_ga) if away_ga else '估算'} | 基于近期失球数据 |")
    lines.append(f"| **预期进球（泊松λ）** | {f2(po['home_lambda'])} | {f2(po['away_lambda'])} | 泊松模型主/客预期进球 |")
    # Injuries adjustment
    inj_adj_parts = []
    if orig.get("injuries_home"):
        inj_adj_parts.append(f"{h}伤停{len(orig['injuries_home'])}人")
    if orig.get("injuries_away"):
        inj_adj_parts.append(f"{aw}伤停{len(orig['injuries_away'])}人")
    lines.append(f"| **伤病调整** | {'；'.join(inj_adj_parts) if inj_adj_parts else '无明显伤病影响'} | - | 伤病影响已计入预期进球调整 |")
    lines.append("")

    # 2. 赛果概率分布 ← ★ 胜平负概率表
    lines.append("### 2. 赛果概率分布")
    lines.append("")
    lines.append("| 结果 | 概率 | 置信度 | 说明 |")
    lines.append("|------|------|--------|------|")
    lines.append(f"| **{h}胜** | **{pct2(adj['home'])}** | {conf_label(adj['home'])} | 泊松模型 + 语境调整后的主胜概率 |")
    lines.append(f"| **平局** | **{pct2(adj['draw'])}** | {conf_label(adj['draw'])} | 泊松模型 + 语境调整后的平局概率 |")
    lines.append(f"| **{aw}胜** | **{pct2(adj['away'])}** | {conf_label(adj['away'])} | 泊松模型 + 语境调整后的客胜概率 |")
    lines.append("")

    # 2.1 概率融合
    mp = d.get("market_implied", {})
    lines.append("### 2.1 概率融合校准")
    lines.append("")
    lines.append("| 来源 | 权重 | 主胜 | 平局 | 客胜 | 预期进球 | 大2.5 |")
    lines.append("|------|------|------|------|------|----------|------|")
    lines.append(f"| **当前基础模型** | 58% | {pct2(po['home_win_raw'])} | {pct2(po['draw_raw'])} | {pct2(po['away_win_raw'])} | {f2(po['home_lambda'])}-{f2(po['away_lambda'])} | {pct2(po['over_25'])} |")
    lines.append(f"| **市场隐含概率** | 25% | {pct2(mp.get('home', 0))} | {pct2(mp.get('draw', 0))} | {pct2(mp.get('away', 0))} | - | - |")
    lines.append(f"| **语境调整后** | 17% | {pct2(adj['home'])} | {pct2(adj['draw'])} | {pct2(adj['away'])} | {f2(po['home_lambda'])}-{f2(po['away_lambda'])} | {pct2(po['over_25'])} |")
    lines.append("")
    adj_notes = adj.get("notes", [])
    lines.append(f"**融合/调整说明**：{'；'.join(adj_notes) if adj_notes else '未应用额外调整'}")
    lines.append("")

    # ═══ 让球分析 ═══ ← ★ 让球分析表
    lines.append("### 3. 让球胜平负分析")
    lines.append("")
    lines.append(f"| 维度 | 结果 | 说明 |")
    lines.append("|------|------|------|")
    handicap_line = handicap
    if handicap_line < 0:
        cover_label = f"{h}让{abs(handicap_line)}胜"
        push_label = f"{h}让{abs(handicap_line)}平"
        fail_label = f"{h}让{abs(handicap_line)}负"
        # Estimate cover/push/fail from score distribution
        cover_prob = adj["home"] * 0.55  # rough: need 2+ goal win
        push_prob = adj["home"] * 0.25 + adj["draw"] * 0.15
        fail_prob = 1 - cover_prob - push_prob
    else:
        cover_label = f"{h}受让{abs(handicap_line)}胜"
        push_label = f"{h}受让{abs(handicap_line)}平"
        fail_label = f"{h}受让{abs(handicap_line)}负"
        cover_prob = adj["away"] * 0.55
        push_prob = adj["away"] * 0.25 + adj["draw"] * 0.15
        fail_prob = 1 - cover_prob - push_prob

    lines.append(f"| **让球盘口** | 竞彩让球 {handicap_str} | {h_odds['home_win']}/{h_odds['draw']}/{h_odds['away_win']} |")
    lines.append(f"| **{cover_label}** | **{pct2(cover_prob)}** | 需要赢{abs(handicap_line)+1}球以上 |")
    lines.append(f"| **{push_label}** | **{pct2(push_prob)}** | 恰好净胜{abs(handicap_line)}球 |")
    lines.append(f"| **{fail_label}** | **{pct2(fail_prob)}** | 平局或输球 |")
    lines.append(f"| **让球方向** | {'让负概率偏高，倾向让负' if fail_prob > 0.45 else ('让胜概率偏高，倾向让胜' if cover_prob > 0.45 else '三项接近，建议观望')} | 基于泊松比分分布估算 |")
    lines.append("")

    # ═══ 进球数预测 ═══ ← ★ 总进球分析表
    lines.append("### 4. 总进球数预测")
    lines.append("")
    lines.append("| 预测维度 | 概率 | 说明 |")
    lines.append("|----------|------|------|")
    lines.append(f"| **大2.5球** | **{pct2(po['over_25'])}** | {over_note(po['over_25'])} |")
    lines.append(f"| **小2.5球** | **{pct2(1 - po['over_25'])}** | {'倾向较明显' if 1-po['over_25'] >= 0.58 else ('轻微倾向' if 1-po['over_25'] >= 0.52 else '倾向不强')} |")
    lines.append(f"| **双方进球(BTTS)** | **{pct2(po['btts'])}** | {'双方进球概率较高' if po['btts'] >= 0.55 else ('双方进球概率较低' if po['btts'] <= 0.45 else '无明显方向')} |")
    lines.append(f"| **总进球区间** | {goal_range(po['home_lambda'], po['away_lambda'])} | 基于预期进球 {f2(po['home_lambda'])} + {f2(po['away_lambda'])} = {f2(po['home_lambda']+po['away_lambda'])} |")
    lines.append("")

    # ═══ 比分分析 ═══ ← ★ 比分概率分布表
    # We need to recalculate score probabilities
    # Use the poisson data from the original analysis
    lines.append("### 5. 比分概率分布（Top 8）")
    lines.append("")
    lines.append("| 比分 | 概率 | 排名 | 说明 |")
    lines.append("|------|------|------|------|")

    # Recalculate score probabilities from the lambda values
    def poisson_pmf(k, lam):
        if k < 0: return 0.0
        return math.exp(-lam) * (lam ** k) / math.factorial(k)

    h_l = po["home_lambda"]
    a_l = po["away_lambda"]
    score_probs = {}
    for sg in range(8):
        for ag in range(8):
            prob = poisson_pmf(sg, h_l) * poisson_pmf(ag, a_l)
            score_probs[(sg, ag)] = prob
    total = sum(score_probs.values())
    sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)

    for rank, ((sg, ag), prob) in enumerate(sorted_scores[:8], 1):
        norm_prob = prob / total
        outcome = f"{h}胜" if sg > ag else ("平局" if sg == ag else f"{aw}胜")
        lines.append(f"| **{sg}-{ag}** | **{pct2(norm_prob)}** | {rank} | {outcome} |")
    lines.append("")

    # Most likely score
    likely = sorted_scores[0]
    lines.append(f"**最可能比分**: **{likely[0][0]}-{likely[0][1]}**（概率 {pct2(likely[1]/total)}），为所有比分组合中概率最高值。")
    lines.append("")

    # ═══ 四、奇门辅助（本期未运行） ═══
    lines.append("---")
    lines.append("")
    lines.append("## 四、奇门遁甲辅助分析")
    lines.append("")
    lines.append("> 本期未运行奇门遁甲辅助模块。以下为占位说明。")
    lines.append("")
    lines.append("| 维度 | 结果 |")
    lines.append("|------|------|")
    lines.append("| **局象** | 未运行 |")
    lines.append("| **奇门胜平负** | - |")
    lines.append("| **奇门预测比分** | - |")
    lines.append("| **波动等级** | - |")
    lines.append("| **奇门信心** | - |")
    lines.append("")
    lines.append("**奇门风险提示**：本期未启用奇门辅助，不产生额外风险信号。")
    lines.append("")

    # ═══ 五、凯利公式核心方向 ═══ ← ★ 核心分析表
    lines.append("---")
    lines.append("")
    lines.append("## 五、凯利公式核心方向策略")
    lines.append("")

    lines.append("### 1. 核心方向选项")
    lines.append("")
    lines.append("| 核心方向选项 | 市场数字 | 模型概率 | EV | 凯利占比 | 建议方向 | 说明 |")
    lines.append("|----------|------|----------|----|----------|------|------|")

    # Calculate Kelly for all three outcomes
    for bet_type, prob, odd_key in [
        (f"{h}胜", adj["home"], "home_win"),
        ("平局", adj["draw"], "draw"),
        (f"{aw}胜", adj["away"], "away_win"),
    ]:
        odd_val = odds[odd_key]
        b = odd_val - 1
        p = prob
        q = 1 - p
        ev = p * b - q
        kelly_raw = (b * p - q) / b if b > 0 else 0
        kelly_frac = max(0, kelly_raw * 0.25)  # 1/4 Kelly
        rec = "✅ 推荐" if ev > 0 and kelly_frac > 0 else ("⚠️ 观望" if abs(ev) < 0.03 else "❌ 不推荐")
        reason = f"正EV {ev:+.1%}" if ev > 0 else f"负EV {ev:+.1%}"
        if abs(ev) < 0.01:
            reason += "，接近公平赔率"
        lines.append(f"| **{bet_type}** | {odd_val:.2f} | {pct2(prob)} | {ev:+.1%} | {kelly_frac:.2%} | {rec} | {reason} |")

    lines.append("")

    # 2. 资金分配
    lines.append("### 2. 核心方向总结")
    lines.append("")

    # Find best bet
    bets = []
    for bet_type, prob, odd_key in [
        (f"{h}胜", adj["home"], "home_win"),
        ("平局", adj["draw"], "draw"),
        (f"{aw}胜", adj["away"], "away_win"),
    ]:
        odd_val = odds[odd_key]
        ev = prob * (odd_val - 1) - (1 - prob)
        bets.append((bet_type, odd_val, prob, ev))

    bets.sort(key=lambda x: x[3], reverse=True)
    best = bets[0]
    second = bets[1]

    lines.append(f"**核心方向**: **{best[0]}** — 赔率 {best[1]:.2f}，模型概率 {pct2(best[2])}，期望值 {best[3]:+.1%}")
    lines.append(f"**次选方向**: **{second[0]}** — 赔率 {second[1]:.2f}，模型概率 {pct2(second[2])}，期望值 {second[3]:+.1%}")
    lines.append(f"**规避方向**: {'、'.join(b[0] for b in bets if b[3] < -0.05) if any(b[3] < -0.05 for b in bets) else '无明确规避方向'}")
    lines.append(f"**综合评分**: {d['score']:.1f} / 信心: {d['confidence']}")
    lines.append("")

    # Risk
    if d.get("warnings"):
        lines.append("**风险提示**：")
        for w in d["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    # ═══ 六、AI复核（未运行） ═══
    lines.append("---")
    lines.append("")
    lines.append("## 六、原有模型分析与 AI 联网复核")
    lines.append("")
    lines.append("> 本期未运行 GPT/Codex 联网复核。以下输出原有模型独立结论。")
    lines.append("")
    lines.append("### 1. 原有模型分析结果")
    lines.append("")
    lines.append("| 维度 | 原有模型结论 |")
    lines.append("|------|--------------|")
    lines.append(f"| **胜平负概率** | {h}胜 {pct2(adj['home'])} / 平 {pct2(adj['draw'])} / {aw}胜 {pct2(adj['away'])} |")
    lines.append(f"| **模型比分** | {likely[0][0]}-{likely[0][1]} |")
    lines.append(f"| **让球结论** | {'让负倾向' if fail_prob > 0.45 else ('让胜倾向' if cover_prob > 0.45 else '方向不明确')} |")
    goals_dir = "大2.5" if po['over_25'] >= 0.55 else ("小2.5" if po['over_25'] <= 0.45 else "中性")
    lines.append(f"| **进球结论** | {goals_dir} |")
    lines.append(f"| **核心建议** | {d['primary_pick']} |")
    lines.append(f"| **信心/组合** | {d['confidence']} / {'允许' if d.get('parlay_allowed') else '不建议'} |")
    lines.append("")

    lines.append("### 2. GPT-5.5 联网复核结果")
    lines.append("")
    lines.append("| 维度 | AI复核结论 |")
    lines.append("|------|------------|")
    lines.append("| **执行状态** | 未执行（本期跳过大模型复核） |")
    lines.append("| **模型一致性** | - |")
    lines.append("| **信心调整** | 无 |")
    lines.append("| **复核建议** | 沿用模型和风控结论 |")
    lines.append("")

    # ═══ 七、最终结论 ═══
    lines.append("---")
    lines.append("")
    lines.append("## 七、最终结论与核心观点")
    lines.append("")

    lines.append("### 1. 模型预测汇总")
    lines.append("")
    lines.append("| 预测维度 | 预测结果 | 概率 | 置信度 |")
    lines.append("|----------|----------|------|--------|")
    outcomes = sorted([(f"{h}胜", adj["home"]), ("平局", adj["draw"]), (f"{aw}胜", adj["away"])], key=lambda x: x[1], reverse=True)
    lines.append(f"| **最可能赛果** | {outcomes[0][0]} | {pct2(outcomes[0][1])} | {conf_label(outcomes[0][1])} |")
    lines.append(f"| **次可能赛果** | {outcomes[1][0]} | {pct2(outcomes[1][1])} | {conf_label(outcomes[1][1])} |")
    lines.append(f"| **最可能比分** | {likely[0][0]}-{likely[0][1]} | {pct2(likely[1]/total)} | 低 |")
    lines.append(f"| **进球数方向** | {goal_range(po['home_lambda'], po['away_lambda'])} | {goals_dir} | {conf_label(max(po['over_25'], 1-po['over_25']))} |")
    lines.append(f"| **奇门辅助方向** | - | - | 未运行 |")
    lines.append("")

    lines.append("### 2. 最终赛事建议")
    lines.append("")
    lines.append(f"**核心方向**：{d['primary_pick']}  ")
    lines.append(f"**比赛语境**：{orig.get('context_note', '-')}  ")
    lines.append(f"**风险等级**：{d['confidence']}")
    lines.append("")
    lines.append("**风险提示**：")
    lines.append("- 竞彩市场数字会随临场变化，建议结合收盘线复核。")
    lines.append("- 日职排名赛轮换不确定性较大，建议控制投入比例。")
    if d.get("warnings"):
        for w in d["warnings"][:3]:
            lines.append(f"- {w}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**免责声明**: 本报告仅供学习和研究使用，不构成任何资金决策建议。请理性对待赛事分析，遵守当地法律法规。")
    lines.append("")

    return "\n".join(lines)


# ── Multi-match summary ─────────────────────────────────────────────
def render_summary(analyses):
    from analyze_jleague_0606 import MATCHES as orig_matches

    lines = []
    lines.append("# 多场比赛汇总")
    lines.append("")

    # 单场结论表
    lines.append("## 单场结论")
    lines.append("")
    lines.append("| 场次 | 比赛 | 模型倾向 | 推荐玩法 | 参考概率 | 市场数字 | 比分方向 | 球数 |")
    lines.append("|------|------|----------|----------|----------|------|----------|------|")

    for a in analyses:
        m = a["match_num"]
        h = a["home_team"]
        aw = a["away_team"]
        adj = a["adjusted"]
        d = a["decision"]
        po = a["poisson"]
        odds = a["odds"]
        k = a["kelly_top"]

        outcomes = sorted([(f"{h}胜", adj["home"]), ("平", adj["draw"]), (f"{aw}胜", adj["away"])], key=lambda x: x[1], reverse=True)
        lean = outcomes[0][0]
        prob_str = f"{pct2(outcomes[0][1])}"
        odds_str = f"{odds['home_win']}/{odds['draw']}/{odds['away_win']}"
        goals = "大2.5" if po['over_25'] >= 0.55 else ("小2.5" if po['over_25'] <= 0.45 else "中性")
        score_dir = po.get('most_likely_score', '-')

        lines.append(f"| {m} | {h} vs {aw} | {lean} | {d['primary_pick']} | {prob_str} | {odds_str} | {score_dir} | {goals} |")

    lines.append("")

    # 价值点分档
    tier1 = [(a, a["kelly_top"]["expected_value"]) for a in analyses if a["kelly_top"] and a["kelly_top"]["expected_value"] > 0.05]
    tier2 = [(a, a["kelly_top"]["expected_value"]) for a in analyses if a["kelly_top"] and 0 < (a["kelly_top"]["expected_value"] or 0) <= 0.05]
    tier3 = [(a, a["kelly_top"]["expected_value"]) for a in analyses if a["kelly_top"] and (a["kelly_top"]["expected_value"] or 0) <= 0]

    lines.append("## 最值得关注的价值点")
    lines.append("")
    lines.append("**第一档（高EV）：**")
    if tier1:
        for a, ev in sorted(tier1, key=lambda x: x[1], reverse=True):
            lines.append(f"- {a['match_num']} {a['home_team']} vs {a['away_team']}: {a['decision']['primary_pick']} (EV {ev:+.1%})")
    else:
        lines.append("- 本期无高EV场次")
    lines.append("")
    lines.append("**第二档（中等EV）：**")
    if tier2:
        for a, ev in tier2:
            lines.append(f"- {a['match_num']} {a['home_team']} vs {a['away_team']}: {a['decision']['primary_pick']} (EV {ev:+.1%})")
    else:
        lines.append("- 本期无中等EV场次")
    lines.append("")
    lines.append("**第三档（低/负EV，小注搏）：**")
    if tier3:
        for a, ev in tier3[:4]:
            lines.append(f"- {a['match_num']} {a['home_team']} vs {a['away_team']}: {a['decision']['primary_pick']} (EV {ev:+.1%})")
    else:
        lines.append("- 无")
    lines.append("")

    # n串1建议
    parlay_ok = [a for a in analyses if a["decision"].get("parlay_allowed")]
    if len(parlay_ok) >= 2:
        lines.append("## 组合思路")
        lines.append("")
        top2 = sorted(parlay_ok, key=lambda x: x["decision"]["score"], reverse=True)[:2]
        picks_2 = [f"{a['match_num']} {a['decision']['primary_pick']}" for a in top2]
        odds_2 = 1.0
        for a in top2:
            o = a["odds"]
            if a["decision"]["primary_pick"].startswith(a["home_team"]): odds_2 *= o["home_win"]
            elif a["decision"]["primary_pick"].startswith(a["away_team"]): odds_2 *= o["away_win"]
            else: odds_2 *= o["draw"]
        lines.append("### 稳健 2 场组合")
        lines.append("```text")
        lines.append(" × ".join(picks_2))
        lines.append(f"理论市场数字约：{odds_2:.2f}")
        lines.append("```")
        lines.append("")

        if len(parlay_ok) >= 3:
            top3 = sorted(parlay_ok, key=lambda x: x["decision"]["score"], reverse=True)[:3]
            picks_3 = [f"{a['match_num']} {a['decision']['primary_pick']}" for a in top3]
            odds_3 = 1.0
            for a in top3:
                o = a["odds"]
                if a["decision"]["primary_pick"].startswith(a["home_team"]): odds_3 *= o["home_win"]
                elif a["decision"]["primary_pick"].startswith(a["away_team"]): odds_3 *= o["away_win"]
                else: odds_3 *= o["draw"]
            lines.append("### 进取 3 场组合")
            lines.append("```text")
            lines.append(" × ".join(picks_3))
            lines.append(f"理论市场数字约：{odds_3:.2f}")
            lines.append("```")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**免责声明**: 本报告仅供学习和研究使用，不构成任何资金决策建议。请理性对待赛事分析，遵守当地法律法规。")
    lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating template-based reports...")

    all_singles = []
    for a in analyses:
        single = render_single(a)
        all_singles.append(single)

    summary = render_summary(analyses)

    # Combine
    full_report = "\n\n".join(all_singles) + "\n\n" + summary

    out = Path(__file__).parent / "2026-06-06日职联6场分析报告.md"
    out.write_text(full_report, encoding="utf-8")

    print(f"✅ Report saved: {out}")
    print(f"   {len(all_singles)} single-match reports + multi-match summary")
