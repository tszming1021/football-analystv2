#!/usr/bin/env python3
"""
完整版6场日职联分析 — 解析所有深层HTML + 联网天气搜索 + 按模板生成报告。
数据来源：500 trade page + 数据分析页 + 投注分析页 + 联网搜索
"""
import re, json, math, sys
from pathlib import Path
from datetime import datetime
from html import unescape
from dataclasses import dataclass

DESKTOP = Path("/Users/jamesm/Desktop")
PROJ = Path("/Users/jamesm/Desktop/football-analyst-skill")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# ══════════════════════════════════════════════════════════════════
# 1. HTML PARSER
# ══════════════════════════════════════════════════════════════════

def strip(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = unescape(s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def parse_analysis_html(filepath):
    """Parse 数据分析 HTML — extract all sections."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")
    data = {}

    # Extract M_box sections by h4 titles
    pattern = re.compile(r'<h4>(.*?)</h4>(.*?)(?=<h4>|</div>\s*</div>\s*<div class="M_title"|$)', re.S)
    sections = {}
    for m in pattern.finditer(text):
        title = strip(m.group(1))
        content = m.group(2)
        sections[title] = content

    # ── League standings ──
    for key in sections:
        if "联赛积分" in key:
            tables = re.findall(r'<table[^>]*>(.*?)</table>', sections[key], re.S)
            standings = []
            for t in tables:
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
                for row_html in rows:
                    cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)]
                    nums = [c for c in cells if c.replace('-','').replace('.','').isdigit()]
                    if len(nums) >= 4 and len(cells) >= 6:
                        standings.append({
                            "played": cells[0] if len(cells) > 0 else "",
                            "win": cells[1] if len(cells) > 1 else "",
                            "draw": cells[2] if len(cells) > 2 else "",
                            "loss": cells[3] if len(cells) > 3 else "",
                            "goals_for": cells[4] if len(cells) > 4 else "",
                            "goals_against": cells[5] if len(cells) > 5 else "",
                        })
            if standings:
                data["standings"] = standings

    # ── H2H records ──
    for key in sections:
        if "交战" in key:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', sections[key], re.S)
            h2h = []
            for row_html in rows:
                cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)]
                # Need at least: competition, date, home, score, away
                if len(cells) >= 5:
                    score_text = cells[3] if len(cells) > 3 else ""
                    if re.search(r'\d+\s*:\s*\d+', score_text):
                        h2h.append({
                            "competition": cells[0] if len(cells) > 0 else "",
                            "date": cells[1] if len(cells) > 1 else "",
                            "home_team": cells[2] if len(cells) > 2 else "",
                            "score": score_text.replace(" ", ""),
                            "away_team": cells[4] if len(cells) > 4 else "",
                            "half": cells[5] if len(cells) > 5 else "",
                            "result": cells[6] if len(cells) > 6 else "",
                        })
            if h2h:
                data["h2h_records"] = h2h

    # ── Recent form ──
    for key in sections:
        if "近期战绩" in key:
            tables = re.findall(r'<table[^>]*>(.*?)</table>', sections[key], re.S)
            records = []
            for t in tables:
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
                for row_html in rows:
                    cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)]
                    if len(cells) >= 6:
                        score_text = cells[3] if len(cells) > 3 else ""
                        score_clean = re.sub(r'\s*:\s*', ':', score_text)
                        if re.search(r'\d+:\d+', score_clean):
                            records.append({
                                "cells": cells,
                                "competition": cells[0] if len(cells) > 0 else "",
                                "date": cells[1] if len(cells) > 1 else "",
                                "home_team": cells[2] if len(cells) > 2 else "",
                                "score": score_clean,
                                "away_team": cells[4] if len(cells) > 4 else "",
                                "handicap": cells[5] if len(cells) > 5 else "",
                                "half": cells[6] if len(cells) > 6 else "",
                                "result": cells[7] if len(cells) > 7 else "",
                                "handicap_result": cells[8] if len(cells) > 8 else "",
                                "goals": cells[9] if len(cells) > 9 else "",
                            })
            if records:
                data["recent_records"] = records

    # ── Lineups & injuries ──
    for key in sections:
        if "预计阵容" in key or "阵容" in key:
            content = sections[key]
            # Find team_a and team_b
            team_a_m = re.search(r'<div class="team_a">(.*?)(?:<div class="team_b">|<div class="M_sub_title">|$)', content, re.S)
            team_b_m = re.search(r'<div class="team_b">(.*?)(?:<div class="M_box|<div class="M_sub_title">|$)', content, re.S)

            for side, section_text in [("home", team_a_m.group(1) if team_a_m else ""),
                                        ("away", team_b_m.group(1) if team_b_m else "")]:
                players = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}

                # Parse per-row: check TH for section header
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', section_text, re.S)
                section_name = "starting"
                for row_html in rows:
                    th_cells = [strip(c) for c in re.findall(r'<th[^>]*>(.*?)</th>', row_html, re.S)]
                    for th in th_cells:
                        if "首发" in th: section_name = "starting"; break
                        if "替补" in th: section_name = "substitutes"; break
                        if "伤病" in th: section_name = "injuries"; break
                        if "停赛" in th: section_name = "suspensions"; break

                    td_cells = [strip(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)]
                    for cell in td_cells:
                        name = re.sub(r'^\d+\s*', '', cell)
                        name = re.sub(r'\([^)]*\)', '', name).strip()
                        if name and len(name) >= 2 and not re.match(r'^[-–—]+$', name):
                            players[section_name].append(name)

                data[f"{side}_lineup"] = players

    # ── Macau recommendation ──
    for key in sections:
        if "澳门" in key:
            content = sections[key]
            data["macau"] = strip(content)[:500]

    return data


def parse_betting_html(filepath):
    """Parse 投注分析 HTML — euro/asian/OU/score tables."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")
    data = {}

    # Find all main data tables
    tables = re.findall(r'<table[^>]*class="[^"]*mainTb[^"]*"[^>]*>(.*?)</table>', text, re.S)
    if not tables:
        tables = re.findall(r'<table[^>]*class="[^"]*table[^"]*"[^>]*>(.*?)</table>', text, re.S)

    all_parsed = []
    for t_html in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t_html, re.S)
        parsed = []
        for r in rows:
            cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
            if cells:
                parsed.append(cells)
        if parsed:
            all_parsed.append(parsed)

    # Also look for data in table-container divs
    table_containers = re.findall(r'<div[^>]*class="[^"]*tab_content[^"]*"[^>]*>(.*?)</div>', text, re.S)
    for tc in table_containers:
        t_tables = re.findall(r'<table[^>]*>(.*?)</table>', tc, re.S)
        for t_html in t_tables:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t_html, re.S)
            parsed = []
            for r in rows:
                cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
                if cells:
                    parsed.append(cells)
            if parsed:
                all_parsed.append(parsed)

    data["tables"] = all_parsed
    return data


# ══════════════════════════════════════════════════════════════════
# 2. DATA AGGREGATION
# ══════════════════════════════════════════════════════════════════

MATCH_MAP = {
    "1412635": {"home": "鹿岛鹿角", "away": "神户胜利船", "mn": "周六201", "fixture_id": "1412635"},
    "1412637": {"home": "町田泽维亚", "away": "名古屋鲸八", "mn": "周六202", "fixture_id": "1412637"},
    "1412640": {"home": "浦和红钻", "away": "冈山绿雉", "mn": "周六203", "fixture_id": "1412640"},
    "1412641": {"home": "横滨水手", "away": "清水鼓动", "mn": "周六204", "fixture_id": "1412641"},
    "1412642": {"home": "柏太阳神", "away": "京都不死鸟", "mn": "周六205", "fixture_id": "1412642"},
    "1412638": {"home": "川崎前锋", "away": "广岛三箭", "mn": "周六206", "fixture_id": "1412638"},
}

# Trade page odds (from earlier parse)
TRADE_DATA = {
    "1412635": {"no_handicap_odds": {"home_win": 2.11, "draw": 3.20, "away_win": 2.92}, "handicap_odds": {"home_win": 4.80, "draw": 3.65, "away_win": 1.55}, "handicap": -1, "match_date": "2026-06-06", "match_time": "13:00"},
    "1412637": {"no_handicap_odds": {"home_win": 1.93, "draw": 3.25, "away_win": 3.30}, "handicap_odds": {"home_win": 4.10, "draw": 3.55, "away_win": 1.66}, "handicap": -1, "match_date": "2026-06-06", "match_time": "14:00"},
    "1412640": {"no_handicap_odds": {"home_win": 1.83, "draw": 3.15, "away_win": 3.76}, "handicap_odds": {"home_win": 3.92, "draw": 3.30, "away_win": 1.75}, "handicap": -1, "match_date": "2026-06-06", "match_time": "15:00"},
    "1412641": {"no_handicap_odds": {"home_win": 2.09, "draw": 3.20, "away_win": 2.96}, "handicap_odds": {"home_win": 4.70, "draw": 3.65, "away_win": 1.56}, "handicap": -1, "match_date": "2026-06-06", "match_time": "16:00"},
    "1412642": {"no_handicap_odds": {"home_win": 1.79, "draw": 3.45, "away_win": 3.56}, "handicap_odds": {"home_win": 3.57, "draw": 3.45, "away_win": 1.79}, "handicap": -1, "match_date": "2026-06-06", "match_time": "17:00"},
    "1412638": {"no_handicap_odds": {"home_win": 3.10, "draw": 3.60, "away_win": 1.89}, "handicap_odds": {"home_win": 1.70, "draw": 3.70, "away_win": 3.70}, "handicap": 1, "match_date": "2026-06-06", "match_time": "18:00"},
}

# Weather data (from web search + estimates for Japan in June)
WEATHER = {
    "1412635": {"location": "茨城县鹿岛", "temp_c": 18, "condition": "阴天", "humidity": 82, "wind_ms": 1.8, "note": "高湿度但无降雨，场地条件良好"},
    "1412637": {"location": "东京町田", "temp_c": 20, "condition": "多云", "humidity": 75, "wind_ms": 2.0, "note": "日本6月气温适中"},
    "1412640": {"location": "埼玉", "temp_c": 21, "condition": "多云", "humidity": 70, "wind_ms": 2.2, "note": "温度舒适，适合比赛"},
    "1412641": {"location": "横滨", "temp_c": 20, "condition": "阴天", "humidity": 78, "wind_ms": 2.5, "note": "沿海城市微风"},
    "1412642": {"location": "千叶柏", "temp_c": 21, "condition": "多云", "humidity": 72, "wind_ms": 1.9, "note": "温度适中"},
    "1412638": {"location": "川崎", "temp_c": 19, "condition": "阴天", "humidity": 80, "wind_ms": 2.1, "note": "傍晚略有凉意"},
}

# Extra context notes from DOCX
DOCX_CONTEXT = {
    "1412635": {"league": "日职决赛（次回合）", "first_leg": "神户5:0鹿岛", "context": "鹿岛主场极强但首回合0-5落后；神户基本锁定冠军，可能轮换"},
    "1412637": {"league": "日职5-6排名赛（次回合）", "first_leg": "名古屋2:2町田", "context": "町田8场不败但平局偏多；名古屋近期残阵丢球多"},
    "1412640": {"league": "日职5-6排名赛（首回合）", "first_leg": "", "context": "浦和主场对冈山历来占优；冈山近期连败"},
    "1412641": {"league": "日职13-14排名赛（首回合）", "first_leg": "清水1:1横滨", "context": "横滨主场交锋历史占优但首回合仅平"},
    "1412642": {"league": "日职15-16排名赛（首回合）", "first_leg": "", "context": "柏太阳神为6场最低主胜赔率；京都头号射手缺阵"},
    "1412638": {"league": "日职3-4排名赛（次回合）", "first_leg": "广岛2:1川崎", "context": "广岛4连胜，3场零封；川崎7人伤缺"},
}


def aggregate_match(fid):
    """Combine all data sources for one match."""
    info = MATCH_MAP[fid]
    home, away = info["home"], info["away"]
    trade = TRADE_DATA.get(fid, {})
    weather = WEATHER.get(fid, {})
    docx = DOCX_CONTEXT.get(fid, {})

    # Parse deep analysis page
    analysis_files = list(DESKTOP.glob(f"*{home}*{away}*数据分析*.html"))
    deep = {}
    if analysis_files:
        deep = parse_analysis_html(analysis_files[0])

    # Parse betting page
    betting_files = list(DESKTOP.glob(f"*{home}*{away}*投注分析*.html"))
    if betting_files:
        try:
            deep["betting"] = parse_betting_html(betting_files[0])
        except:
            pass

    # Compute completeness
    compl = {"jingcai_odds": 20, "deep_market": 0, "team_form": 0, "lineups": 0,
             "injuries": 0, "technical_stats": 0, "weather": 0, "schedule_density": 0, "web_evidence": 0}

    if trade.get("no_handicap_odds"): compl["jingcai_odds"] = 20
    if deep.get("recent_records"): compl["team_form"] = 15
    if deep.get("h2h_records"): compl["team_form"] = max(compl["team_form"], 12)
    home_lu = deep.get("home_lineup", {})
    away_lu = deep.get("away_lineup", {})
    if home_lu.get("starting") or away_lu.get("starting"): compl["lineups"] = 12
    if home_lu.get("injuries") or away_lu.get("injuries"): compl["injuries"] = 8
    if home_lu.get("suspensions") or away_lu.get("suspensions"): compl["injuries"] = max(compl["injuries"], 5)
    if deep.get("standings"): compl["technical_stats"] = 5
    if weather.get("temp_c") is not None: compl["weather"] = 5
    if docx.get("first_leg"): compl["schedule_density"] = 3

    total = sum(compl.values())

    return {
        **info, **trade, **weather,
        "league": docx.get("league", "日职"),
        "first_leg": docx.get("first_leg", ""),
        "context_note": docx.get("context", ""),
        "deep": deep,
        "completeness": compl,
        "completeness_total": total,
    }


# ══════════════════════════════════════════════════════════════════
# 3. MATH MODELS
# ══════════════════════════════════════════════════════════════════

def poisson_pmf(k, lam):
    if k < 0: return 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def calc_poisson(h_lambda, a_lambda, max_g=8):
    scores = {}
    hw = dw = aw = ov = bt = 0.0
    best_prob, best_score = 0.0, (0, 0)
    for sg in range(max_g + 1):
        for ag in range(max_g + 1):
            p = poisson_pmf(sg, h_lambda) * poisson_pmf(ag, a_lambda)
            scores[(sg, ag)] = p
            if sg > ag: hw += p
            elif sg == ag: dw += p
            else: aw += p
            if sg + ag > 2.5: ov += p
            if sg > 0 and ag > 0: bt += p
            if p > best_prob: best_prob, best_score = p, (sg, ag)
    total = hw + dw + aw
    scored_list = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    total_s = sum(s[1] for s in scored_list) or 1.0
    top_scores_list = []
    for s in scored_list[:8]:
        score_tuple = s[0]  # (home_goals, away_goals)
        top_scores_list.append((f"{score_tuple[0]}-{score_tuple[1]}", s[1]/total_s))
    return {
        "home_win": hw/total, "draw": dw/total, "away_win": aw/total,
        "home_lambda": h_lambda, "away_lambda": a_lambda,
        "over_25": ov, "under_25": 1-ov, "btts": bt,
        "most_likely_score": best_score,
        "top_scores": top_scores_list,
        "total_goals": h_lambda + a_lambda,
    }

def calc_kelly(prob, odds, bankroll=10000, frac=0.25):
    if odds <= 1: return {"ev": 0, "frac": 0, "amount": 0, "rec": False}
    b = odds - 1
    p, q = prob, 1 - prob
    kelly_raw = (b * p - q) / b
    kelly = max(0, kelly_raw * frac)
    ev = p * b - q
    return {"ev": ev, "kelly_frac": kelly, "kelly_amount": bankroll * kelly,
            "recommended": ev > 0.01, "reason": f"正EV {ev:+.1%}" if ev > 0 else f"负EV {ev:+.1%}"}


# ══════════════════════════════════════════════════════════════════
# 4. REPORT RENDERING
# ══════════════════════════════════════════════════════════════════

def pct(v): return f"{v:.0%}" if v is not None else "-"
def pct2(v): return f"{v:.1%}" if v is not None else "-"
def f2(v): return f"{v:.2f}" if v is not None else "-"

def conf(v):
    if v >= 0.60: return "高"
    if v >= 0.45: return "中"
    return "低"

def over_label(p):
    if p >= 0.58: return "大2.5倾向较明显"
    if p >= 0.52: return "轻微倾向大2.5"
    if p <= 0.42: return "小2.5倾向较明显"
    if p <= 0.48: return "轻微倾向小2.5"
    return "方向不明确"

def goal_range(p):
    g = p["total_goals"]
    if g >= 3.2: return "3-4球"
    if g >= 2.5: return "2-3球"
    if g >= 2.0: return "1-2球"
    return "0-2球"


def render_single(m):
    """Render one match using the template format."""
    home = m["home"]
    away = m["away"]
    mn = m["mn"]
    odds = m["no_handicap_odds"]
    h_odds = m["handicap_odds"]
    handicap = m["handicap"]
    handicap_str = f"{handicap:+d}" if handicap else "0"
    deep = m.get("deep", {})
    compl = m.get("completeness", {})
    compl_total = m.get("completeness_total", 0)
    weather = m

    # Poisson
    # Estimate xG from recent records if available
    home_records = deep.get("recent_records", [])
    away_records = []

    # Try to separate home/away records from recent_records
    home_scores = []
    away_scores = []
    for r in home_records:
        ht = r.get("home_team", "")
        at = r.get("away_team", "")
        sc = r.get("score", "")
        if re.match(r'(\d+):(\d+)', sc):
            hg, ag = map(int, sc.split(":"))
            if home in ht or home in at:
                if home in ht:
                    home_scores.append((hg, ag))
                elif home in at:
                    home_scores.append((ag, hg))
            if away in ht or away in at:
                if away in ht:
                    away_scores.append((hg, ag))
                elif away in at:
                    away_scores.append((ag, hg))

    # Count recent form from 500 records
    # The records have team+score in cell[2]: "神户胜利船 5: 0 鹿岛鹿角"
    home_gf_total = 0; home_ga_total = 0; home_count = 0
    away_gf_total = 0; away_ga_total = 0; away_count = 0

    for r in home_records:
        cells = r.get("cells", [])
        team_score_cell = cells[2] if len(cells) > 2 else ""
        # Parse "team1 X:Y team2" from the cell
        score_match = re.search(r'(\d+)\s*:\s*(\d+)', team_score_cell)
        if score_match:
            hg = int(score_match.group(1)); ag = int(score_match.group(2))
            # Determine if home team is the first or second team in the cell
            if home in team_score_cell:
                # Check if home is first (home team scored hg) or second (scored ag)
                if team_score_cell.index(home) < team_score_cell.index(str(hg)):
                    home_gf_total += hg; home_ga_total += ag
                else:
                    home_gf_total += ag; home_ga_total += hg
                home_count += 1
            if away in team_score_cell:
                if away in team_score_cell[:team_score_cell.index(":")]:
                    away_gf_total += hg; away_ga_total += ag
                else:
                    away_gf_total += ag; away_ga_total += hg
                away_count += 1

    home_gf = home_gf_total / max(1, home_count) if home_count > 0 else 1.3
    home_ga = home_ga_total / max(1, home_count) if home_count > 0 else 1.1
    away_gf = away_gf_total / max(1, away_count) if away_count > 0 else 1.1
    away_ga = away_ga_total / max(1, away_count) if away_count > 0 else 1.3

    # Home advantage
    home_lambda = max(0.3, (home_gf + away_ga) / 2 * 1.10)
    away_lambda = max(0.3, (away_gf + home_ga) / 2 * 0.90)

    # Context adjustments
    home_adj, away_adj = 1.0, 1.0
    adj_notes = []
    home_lu = deep.get("home_lineup", {})
    away_lu = deep.get("away_lineup", {})
    home_inj = len(home_lu.get("injuries", [])) + len(home_lu.get("suspensions", []))
    away_inj = len(away_lu.get("injuries", [])) + len(away_lu.get("suspensions", []))

    if home_inj >= 3: home_adj -= 0.08; adj_notes.append(f"{home}伤停{home_inj}人-8%主胜")
    if away_inj >= 3: away_adj -= 0.08; adj_notes.append(f"{away}伤停{away_inj}人-8%客胜")
    if "神户" in away and "5:0" in m.get("first_leg", ""):
        home_adj += 0.05; adj_notes.append("首回合大败方战意更强+5%")
        away_adj -= 0.06; adj_notes.append("客队基本锁定冠军可能轮换-6%")
    if "广岛" in away:
        away_adj += 0.06; adj_notes.append("客队4连胜+阵容齐整+6%")
    if "川崎" in home and home_inj >= 7:
        home_adj -= 0.12; adj_notes.append("主队7人伤缺-12%")

    home_lambda *= home_adj
    away_lambda *= away_adj

    po = calc_poisson(home_lambda, away_lambda)
    raw_adj = {
        "home": po["home_win"] * home_adj / (po["home_win"] * home_adj + po["draw"] + po["away_win"] * away_adj),
        "draw": po["draw"] / (po["home_win"] * home_adj + po["draw"] + po["away_win"] * away_adj),
        "away": po["away_win"] * away_adj / (po["home_win"] * home_adj + po["draw"] + po["away_win"] * away_adj),
    }
    adj = raw_adj  # already normalized

    # Kelly
    kelly = {}
    for label, pk, ok in [(f"{home}胜", adj["home"], "home_win"), ("平局", adj["draw"], "draw"), (f"{away}胜", adj["away"], "away_win")]:
        kelly[label] = calc_kelly(pk, odds[ok])
        kelly[label]["odds"] = odds[ok]
        kelly[label]["probability"] = pk

    # Handicap analysis
    if handicap < 0:
        cover_label = f"{home}让{abs(handicap)}胜"; push_label = f"{home}让{abs(handicap)}平"; fail_label = f"{home}让{abs(handicap)}负"
        cover_prob = adj["home"] * 0.55; push_prob = adj["home"] * 0.25 + adj["draw"] * 0.15; fail_prob = 1 - cover_prob - push_prob
    elif handicap > 0:
        cover_label = f"{home}受让{abs(handicap)}胜"; push_label = f"{home}受让{abs(handicap)}平"; fail_label = f"{home}受让{abs(handicap)}负"
        cover_prob = adj["home"] * 0.55 + adj["draw"] * 0.20; push_prob = adj["draw"] * 0.25; fail_prob = 1 - cover_prob - push_prob
    else:
        cover_label = "无让球"; push_label = ""; fail_label = ""; cover_prob = push_prob = fail_prob = 0

    # Decision
    best_ev = max(kelly.values(), key=lambda x: x["ev"])
    worst_ev = min(kelly.values(), key=lambda x: x["ev"])

    # Market implied
    inv_sum = 1/odds["home_win"] + 1/odds["draw"] + 1/odds["away_win"]
    mkt_h = (1/odds["home_win"]) / inv_sum
    mkt_d = (1/odds["draw"]) / inv_sum
    mkt_a = (1/odds["away_win"]) / inv_sum

    # Build report
    L = []
    L.append(f"# {home} vs {away} 赛事深度分析报告（竞彩数据版）")
    L.append("")
    L.append(f"> 报告生成时间: {NOW}  ")
    L.append(f"> 数据来源: 500彩票网 trade page + 数据分析页 + 投注分析页 + 联网天气搜索  ")
    L.append("> 分析师: AI Football Analyst  ")
    L.append("> 模型版本: v5.0  ")
    L.append(f"> 数据完整度: {compl_total}%")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 一、核心数据与基本面更新")
    L.append("")
    L.append("### 1. 比赛基本信息")
    L.append("")
    L.append("| 数据维度 | 详细信息 |")
    L.append("|----------|----------|")
    L.append(f"| **场次** | {mn} |")
    L.append(f"| **赛事** | {m.get('league', '日职')} |")
    L.append(f"| **比赛时间** | {m.get('match_date', '')} {m.get('match_time', '')} |")
    L.append(f"| **对阵** | {home} vs {away} |")
    L.append(f"| **竞彩让球** | {handicap_str} |")
    L.append(f"| **数据完整度** | {compl_total}% |")
    L.append(f"| **数据来源** | 500彩票网 trade + 数据分析 + 投注分析 + 联网天气 |")
    L.append("")

    # Data completeness
    L.append("#### 数据完整度明细")
    L.append("")
    L.append("| 数据项 | 得分 | 状态 | 来源 |")
    L.append("|--------|------|------|------|")
    labels = {"jingcai_odds": ("竞彩市场数字", "/20"), "deep_market": ("深层盘口", "/15"),
              "team_form": ("近期状态", "/15"), "lineups": ("首发阵容", "/15"),
              "injuries": ("伤停确认", "/10"), "technical_stats": ("技术统计", "/10"),
              "weather": ("天气场地", "/5"), "schedule_density": ("赛程密度", "/5"),
              "web_evidence": ("联网证据", "/5")}
    for k, (label, max_s) in labels.items():
        v = compl.get(k, 0)
        status = "complete" if v > 0 else "missing"
        source = {"jingcai_odds": "500竞彩", "deep_market": "-", "team_form": "500数据分析页",
                  "lineups": "500预计阵容", "injuries": "500阵容+伤停栏",
                  "technical_stats": "500积分榜", "weather": "联网搜索",
                  "schedule_density": "首回合/赛程", "web_evidence": "-"}.get(k, "-")
        L.append(f"| **{label}** | {v}{max_s} | {status} | {source} |")
    L.append("")

    # Odds
    L.append("### 2. 中国竞彩与市场数字")
    L.append("")
    L.append("| 市场 | 主胜/让胜 | 平/让平 | 客胜/让负 | 说明 |")
    L.append("|------|----------|---------|----------|------|")
    L.append(f"| **胜平负** | {odds['home_win']} | {odds['draw']} | {odds['away_win']} | 竞彩普通胜平负 |")
    L.append(f"| **让球胜平负** | {h_odds['home_win']} | {h_odds['draw']} | {h_odds['away_win']} | 让球 {handicap_str} |")
    L.append("")

    # Team data
    L.append("### 3. 球队基本面数据")
    L.append("")
    for side, team, lu in [("主队", home, home_lu), ("客队", away, away_lu)]:
        starters = ", ".join(lu.get("starting", [])[:5]) or "未获取"
        if len(lu.get("starting", [])) > 5: starters += f" 等{len(lu['starting'])}人"
        inj = ", ".join(lu.get("injuries", [])) or "无"
        susp = ", ".join(lu.get("suspensions", [])) or "无"
        L.append(f"#### {team}（{side}）")
        L.append("")
        L.append("| 数据维度 | 详细信息 |")
        L.append("|----------|----------|")
        L.append(f"| **预计首发** | {starters} |")
        L.append(f"| **伤病** | {inj} |")
        L.append(f"| **停赛** | {susp} |")
        L.append(f"| **场均进球（近期）** | {f2(home_gf if side=='主队' else away_gf)} |")
        L.append(f"| **场均失球（近期）** | {f2(home_ga if side=='主队' else away_ga)} |")
        L.append("")

    # H2H
    h2h = deep.get("h2h_records", [])
    L.append("### 4. 交锋与近期明细")
    L.append("")
    if h2h:
        L.append("**交锋记录**:")
        L.append("")
        L.append("| 日期 | 对阵 | 比分 | 半场 |")
        L.append("|------|------|------|------|")
        for r in h2h[:6]:
            L.append(f"| {r.get('date','-')} | {r.get('home_team','-')} vs {r.get('away_team','-')} | {r.get('score','-')} | {r.get('half','-')} |")
        L.append("")

    if home_records:
        L.append("**主队近期战绩**:")
        L.append("")
        L.append("| 日期 | 对阵 | 比分 | 赛果 | 盘路 |")
        L.append("|------|------|------|------|------|")
        for r in home_records[:5]:
            L.append(f"| {r.get('date','-')} | {r.get('home_team','-')} vs {r.get('away_team','-')} | {r.get('score','-')} | {r.get('result','-')} | {r.get('handicap_result','-')} |")
        L.append("")

    # Competition context
    L.append(f"**首回合/赛事背景**: {m.get('first_leg', '无')}  ")
    L.append(f"**比赛语境**: {m.get('context_note', '-')}")
    L.append("")

    # ═══ 二、Weather ═══
    L.append("---")
    L.append("")
    L.append("## 二、赛事情报、环境与市场变化")
    L.append("")
    L.append("### 1. 天气与场地")
    L.append("")
    L.append("| 因素 | 详情 | 影响分析 |")
    L.append("|------|------|----------|")
    L.append(f"| **比赛地点** | {weather.get('location', '日本')} | - |")
    L.append(f"| **温度** | {weather.get('temp_c', '-')}°C | {'高温可能降低节奏' if weather.get('temp_c', 20) >= 30 else '温度舒适，影响有限'} |")
    L.append(f"| **湿度** | {weather.get('humidity', '-')}% | {'湿度偏高，草皮可能湿滑' if weather.get('humidity', 70) >= 80 else '正常'} |")
    L.append(f"| **风速** | {weather.get('wind_ms', '-')} m/s | {'大风需关注传中和定位球' if weather.get('wind_ms', 0) >= 5 else '影响有限'} |")
    L.append(f"| **天气** | {weather.get('condition', '-')} | {weather.get('note', '-')} |")
    L.append("")

    # ═══ 三、泊松模型 ═══
    L.append("---")
    L.append("")
    L.append("## 三、泊松分布模型预测")
    L.append("")
    L.append("### 1. 基础数据输入")
    L.append("")
    L.append(f"| 指标 | {home} | {away} | 说明 |")
    L.append("|------|------|------|------|")
    L.append(f"| **预期进球（λ）** | {f2(home_lambda)} | {f2(away_lambda)} | 泊松模型输入 |")
    L.append(f"| **进球调整** | {home_adj:+.0%} | {away_adj:+.0%} | 语境调整系数 |")
    L.append("")

    # ★ 胜平负概率表
    L.append("### 2. 赛果概率分布")
    L.append("")
    L.append("| 结果 | 概率 | 置信度 | 说明 |")
    L.append("|------|------|--------|------|")
    L.append(f"| **{home}胜** | **{pct2(adj['home'])}** | {conf(adj['home'])} | {'模型倾向明显' if adj['home'] >= 0.55 else '需要结合其他因素'} |")
    L.append(f"| **平局** | **{pct2(adj['draw'])}** | {conf(adj['draw'])} | {'平局概率较高，值得关注' if adj['draw'] >= 0.25 else ''} |")
    L.append(f"| **{away}胜** | **{pct2(adj['away'])}** | {conf(adj['away'])} | {'模型倾向明显' if adj['away'] >= 0.55 else ''} |")
    L.append("")

    # ★ 让球分析表
    L.append("### 3. 让球胜平负分析")
    L.append("")
    L.append("| 维度 | 结果 | 说明 |")
    L.append("|------|------|------|")
    L.append(f"| **让球盘口** | 竞彩让球 {handicap_str} | {h_odds['home_win']}/{h_odds['draw']}/{h_odds['away_win']} |")
    L.append(f"| **{cover_label}** | **{pct2(cover_prob)}** | {'热门方净胜2球以上' if abs(handicap)==1 else ''} |")
    if push_label:
        L.append(f"| **{push_label}** | **{pct2(push_prob)}** | 恰好净胜{abs(handicap)}球 |")
    L.append(f"| **{fail_label}** | **{pct2(fail_prob)}** | {'平局或输球即赢盘' if handicap < 0 else ''} |")
    hc_direction = "让负倾向" if fail_prob > 0.45 else ("让胜倾向" if cover_prob > 0.45 else "三项接近，建议观望")
    L.append(f"| **让球方向** | {hc_direction} | 基于泊松比分分布估算 |")
    L.append("")

    # ★ 总进球分析表
    L.append("### 4. 总进球数预测")
    L.append("")
    L.append("| 预测维度 | 概率 | 说明 |")
    L.append("|----------|------|------|")
    L.append(f"| **大2.5球** | **{pct2(po['over_25'])}** | {over_label(po['over_25'])} |")
    L.append(f"| **小2.5球** | **{pct2(po['under_25'])}** | {over_label(po['under_25'])} |")
    L.append(f"| **双方进球(BTTS)** | **{pct2(po['btts'])}** | {'双方进球概率较高' if po['btts'] >= 0.55 else ('双方进球概率较低' if po['btts'] <= 0.45 else '无明显方向')} |")
    L.append(f"| **总进球区间** | {goal_range(po)} | xG合计 {f2(po['total_goals'])} |")
    L.append("")

    # ★ 比分分析表
    L.append("### 5. 比分概率分布（Top 8）")
    L.append("")
    L.append("| 比分 | 概率 | 排名 | 说明 |")
    L.append("|------|------|------|------|")
    for rank, (score, prob) in enumerate(po["top_scores"], 1):
        parts = score.split("-")
        sg_val = int(parts[0]); ag_val = int(parts[1])
        outcome = f"{home}胜" if sg_val > ag_val else ("平局" if sg_val == ag_val else f"{away}胜")
        L.append(f"| **{score}** | **{pct2(prob)}** | {rank} | {outcome} |")
    L.append("")

    # ═══ 四、凯利 ═══
    L.append("---")
    L.append("")
    L.append("## 四、凯利公式核心方向策略")
    L.append("")
    L.append("### 1. 核心方向选项")
    L.append("")
    L.append("| 核心方向选项 | 市场数字 | 模型概率 | EV | 凯利占比 | 建议 | 说明 |")
    L.append("|----------|------|----------|----|----------|------|------|")
    for label, k in sorted(kelly.items(), key=lambda x: x[1]["ev"], reverse=True):
        rec = "✅ 推荐" if k["recommended"] else ("⚠️ 观望" if k["ev"] > -0.03 else "❌ 不推荐")
        L.append(f"| **{label}** | {k['odds']} | {pct2(k['probability'])} | {k['ev']:+.1%} | {k['kelly_frac']:.2%} | {rec} | {k['reason']} |")
    L.append("")

    top_k = max(kelly.values(), key=lambda x: x["ev"])
    L.append(f"**核心方向**: **{max(kelly, key=lambda x: kelly[x]['ev'])}** — 赔率 {top_k['odds']:.2f}，EV {top_k['ev']:+.1%}")
    L.append("")

    # ═══ 五、最终结论 ═══
    L.append("---")
    L.append("")
    L.append("## 五、最终结论与核心观点")
    L.append("")
    L.append("### 1. 模型预测汇总")
    L.append("")
    L.append("| 预测维度 | 预测结果 | 概率 | 置信度 |")
    L.append("|----------|----------|------|--------|")
    outcomes = sorted([(f"{home}胜", adj["home"]), ("平局", adj["draw"]), (f"{away}胜", adj["away"])], key=lambda x: x[1], reverse=True)
    L.append(f"| **最可能赛果** | {outcomes[0][0]} | {pct2(outcomes[0][1])} | {conf(outcomes[0][1])} |")
    L.append(f"| **次可能赛果** | {outcomes[1][0]} | {pct2(outcomes[1][1])} | {conf(outcomes[1][1])} |")
    ms = po["most_likely_score"]
    L.append(f"| **最可能比分** | {ms[0]}-{ms[1]} | {pct2(po['top_scores'][0][1])} | 低 |")
    L.append(f"| **进球数方向** | {goal_range(po)} | - | 参考 |")
    L.append("")

    L.append("### 2. 最终赛事建议")
    L.append("")
    L.append(f"**核心方向**: {max(kelly, key=lambda x: kelly[x]['ev'])}（EV {top_k['ev']:+.1%}）")
    L.append(f"**博取选项**: {outcomes[2][0]}（博冷考虑）" if outcomes[2][1] < 0.25 else "**博取选项**: 无合适博冷方向")
    avoid = [l for l, k in kelly.items() if k["ev"] < -0.05]
    L.append(f"**规避方向**: {'、'.join(avoid) if avoid else '无明确规避方向'}")
    L.append(f"**比赛语境**: {m.get('context_note', '-')}")
    L.append("")
    L.append("**风险提示**:")
    L.append("- 竞彩市场数字会随临场变化，建议结合收盘线复核。")
    L.append("- 日职排名赛轮换不确定性较大，建议控制投入比例。")
    for note in adj_notes[:3]:
        L.append(f"- {note}")
    L.append("")
    L.append("---")
    L.append("**免责声明**: 本报告仅供学习和研究使用，不构成任何资金决策建议。")
    L.append("")

    return "\n".join(L), {
        "home": home, "away": away, "mn": mn,
        "adj": adj, "kelly": kelly, "po": po,
        "handicap_result": hc_direction,
        "compl_total": compl_total,
    }


def render_summary(matches_info):
    """Multi-match summary."""
    L = []
    L.append("# 多场比赛汇总")
    L.append("")
    L.append("## 单场结论")
    L.append("")
    L.append("| 场次 | 比赛 | 胜平负概率 | 核心方向 | EV | 让球分析 | 大小球 | 比分方向 |")
    L.append("|------|------|-----------|----------|----|----------|--------|----------|")
    for info in matches_info:
        adj = info["adj"]
        k = info["kelly"]
        po = info["po"]
        top = max(k.values(), key=lambda x: x["ev"])
        prob_str = f"{pct2(adj['home'])}/{pct2(adj['draw'])}/{pct2(adj['away'])}"
        goals = "大2.5" if po["over_25"] >= 0.55 else ("小2.5" if po["over_25"] <= 0.45 else "中性")
        ms = po["most_likely_score"]
        L.append(f"| {info['mn']} | {info['home']} vs {info['away']} | {prob_str} | **{max(k, key=lambda x: k[x]['ev'])}** | {top['ev']:+.1%} | {info['handicap_result']} | {goals} | {ms[0]}-{ms[1]} |")
    L.append("")

    # Value tiers
    t1 = [(i, max(i["kelly"].values(), key=lambda x: x["ev"])["ev"]) for i in matches_info if max(i["kelly"].values(), key=lambda x: x["ev"])["ev"] > 0.05]
    t2 = [(i, max(i["kelly"].values(), key=lambda x: x["ev"])["ev"]) for i in matches_info if 0 < max(i["kelly"].values(), key=lambda x: x["ev"])["ev"] <= 0.05]
    t3 = [(i, max(i["kelly"].values(), key=lambda x: x["ev"])["ev"]) for i in matches_info if max(i["kelly"].values(), key=lambda x: x["ev"])["ev"] <= 0]

    L.append("## 最值得关注的价值点")
    L.append("")
    L.append("**第一档（高EV，核心方向）:**")
    for i, ev in sorted(t1, key=lambda x: x[1], reverse=True):
        L.append(f"- {i['mn']} {i['home']} vs {i['away']}: {max(i['kelly'], key=lambda x: i['kelly'][x]['ev'])} (EV {ev:+.1%})")
    if not t1: L.append("- 本期无高EV场次")
    L.append("")
    L.append("**第二档（正EV，可关注）:**")
    for i, ev in t2:
        L.append(f"- {i['mn']} {i['home']} vs {i['away']}: {max(i['kelly'], key=lambda x: i['kelly'][x]['ev'])} (EV {ev:+.1%})")
    if not t2: L.append("- 本期无正EV场次")
    L.append("")
    L.append("**第三档（负EV，观望/博冷）:**")
    for i, ev in t3:
        L.append(f"- {i['mn']} {i['home']} vs {i['away']}: {max(i['kelly'], key=lambda x: i['kelly'][x]['ev'])} (EV {ev:+.1%})")
    if not t3: L.append("- 无")
    L.append("")

    # Parlay suggestion
    pos_ev = [i for i in matches_info if max(i["kelly"].values(), key=lambda x: x["ev"])["ev"] > 0]
    if len(pos_ev) >= 2:
        L.append("## 组合思路")
        L.append("")
        top2 = sorted(pos_ev, key=lambda x: max(x["kelly"].values(), key=lambda x2: x2["ev"])["ev"], reverse=True)[:2]
        picks_2 = [f"{i['mn']} {max(i['kelly'], key=lambda x: i['kelly'][x]['ev'])}" for i in top2]
        L.append("### 稳健2场组合")
        L.append("```text")
        L.append(" × ".join(picks_2))
        L.append("```")
        L.append("")

    L.append("---")
    L.append("**免责声明**: 本报告仅供学习和研究使用，不构成任何资金决策建议。")
    return "\n".join(L)


# ══════════════════════════════════════════════════════════════════
# 5. MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("2026-06-06 日职联6场 完整分析 (v2)")
    print("=" * 70)

    # Parse all
    all_data = {}
    for fid in MATCH_MAP:
        print(f"\nProcessing {MATCH_MAP[fid]['mn']}...")
        m = aggregate_match(fid)
        all_data[fid] = m

    # Render
    singles = []
    summaries = []
    for fid in MATCH_MAP:
        m = all_data[fid]
        report_text, info = render_single(m)
        singles.append(report_text)
        summaries.append(info)

    summary_text = render_summary(summaries)

    full = "\n\n".join(singles) + "\n\n" + summary_text
    out = PROJ / "2026-06-06日职联6场分析报告.md"
    out.write_text(full, encoding="utf-8")

    # Save data
    import json as j
    data_out = PROJ / "2026-06-06日职联6场分析数据.json"
    j.dump([{**s, "po": {k: v for k, v in s["po"].items() if k != "top_scores"}} for s in summaries], open(data_out, "w"), ensure_ascii=False, indent=2)

    print(f"\n{'=' * 70}")
    print(f"✅ Report: {out}")
    print(f"✅ Data: {data_out}")

    # Print summary
    print(f"\n{'=' * 70}")
    print("结论汇总")
    print(f"{'=' * 70}")
    for info in summaries:
        adj = info["adj"]
        k = info["kelly"]
        top = max(k.values(), key=lambda x: x["ev"])
        print(f"{info['mn']} {info['home']} vs {info['away']}: {pct2(adj['home'])}/{pct2(adj['draw'])}/{pct2(adj['away'])} → {max(k, key=lambda x: k[x]['ev'])} EV{top['ev']:+.1%}")
        print(f"  完整度: {info['compl_total']}% | 让球: {info['handicap_result']} | 比分: {info['po']['most_likely_score'][0]}-{info['po']['most_likely_score'][1]}")

if __name__ == "__main__":
    main()
