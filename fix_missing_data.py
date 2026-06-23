#!/usr/bin/env python3
"""Quick fix: re-parse lineups + injuries + betting data from existing HTML."""
import re, json
from pathlib import Path
from html import unescape

DESKTOP = Path("/Users/jamesm/Desktop")
PROJ = Path("/Users/jamesm/Desktop/football-analyst-skill")

def strip(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = unescape(s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

MATCH_MAP = {
    "1412635": {"home": "鹿岛鹿角", "away": "神户胜利船", "mn": "周六201"},
    "1412637": {"home": "町田泽维亚", "away": "名古屋鲸八", "mn": "周六202"},
    "1412640": {"home": "浦和红钻", "away": "冈山绿雉", "mn": "周六203"},
    "1412641": {"home": "横滨水手", "away": "清水鼓动", "mn": "周六204"},
    "1412642": {"home": "柏太阳神", "away": "京都不死鸟", "mn": "周六205"},
    "1412638": {"home": "川崎前锋", "away": "广岛三箭", "mn": "周六206"},
}

results = {}

for fid, info in MATCH_MAP.items():
    home, away = info["home"], info["away"]
    print(f"\n{fid} {home} vs {away}")

    result = {}

    # ── Parse Analysis Page ──
    analysis_files = list(DESKTOP.glob(f"*{home}*{away}*数据分析*.html"))
    if analysis_files:
        raw = analysis_files[0].read_bytes()
        text = raw.decode("gb18030", "replace")

        # Find lineup area: search full text for team_a/team_b divs
        # These are NOT inside M_box — they're in the page directly
        team_a_m = re.search(r'<div class="team_a">(.*?)<div class="team_b">', text, re.S)
        team_b_m = re.search(r'<div class="team_b">(.*?)(?:<div class="M_box|<div class="M_title"|</div>\s*</div>\s*<div class="M_title")', text, re.S)

        for side, section_match in [("home", team_a_m), ("away", team_b_m)]:
            if not section_match:
                result[f"{side}_lineup"] = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}
                continue

            section_text = section_match.group(1)
            players = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}

            # Parse row by row, detect section from TH
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', section_text, re.S)
            section_name = "starting"
            for row_html in rows:
                th_cells = [strip(c) for c in re.findall(r'<th[^>]*>(.*?)</th>', row_html, re.S)]
                for th in th_cells:
                    th_clean = th.lower().replace('-','').replace(' ','')
                    if '首发' in th_clean: section_name = "starting"; break
                    if '替补' in th_clean: section_name = "substitutes"; break
                    if '伤病' in th_clean: section_name = "injuries"; break
                    if '停赛' in th_clean: section_name = "suspensions"; break

                td_cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for cell_html in td_cells:
                    cell_text = strip(cell_html)
                    # Extract name: remove number prefix and position suffix
                    name = re.sub(r'^\d+\s*', '', cell_text)
                    name = re.sub(r'\([^)]*\)', '', name).strip()
                    if name and len(name) >= 2 and not re.match(r'^[-–—•·]+$', name) and '暂无' not in name:
                        if name not in players[section_name]:
                            players[section_name].append(name)

            result[f"{side}_lineup"] = players
            print(f"  {side}: start={len(players['starting'])}, sub={len(players['substitutes'])}, inj={len(players['injuries'])}, susp={len(players['suspensions'])}")

        # Macau recommendation
        macau_m = re.search(r'澳门心水推荐.*?<td[^>]*>(.*?)</td>', text, re.S)
        if macau_m:
            result["macau"] = strip(macau_m.group(1))[:300]
            print(f"  澳门心水: found")

        # Future fixtures
        future_start = text.find("未来赛事")
        if future_start > 0:
            future_section = text[future_start:future_start+2000]
            fut_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', future_section, re.S)
            futures = []
            for row_html in fut_rows:
                cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)]
                if len(cells) >= 3 and re.search(r'\d{4}-\d{2}-\d{2}', cells[0]):
                    futures.append({"date": cells[0], "competition": cells[1], "match": cells[2]})
            result["future_fixtures"] = futures
            print(f"  未来赛程: {len(futures)} fixtures")

    # ── Parse Betting Page ──
    betting_files = list(DESKTOP.glob(f"*{home}*{away}*投注分析*.html"))
    if betting_files:
        raw = betting_files[0].read_bytes()
        text = raw.decode("gb18030", "replace")

        # Find the euro odds + market data table
        # Table containing odds from multiple companies
        company_tables = []
        for t_match in re.finditer(r'<table[^>]*>(.*?)</table>', text, re.S):
            t_html = t_match.group(1)
            if '欧赔' in t_html or '公司' in t_html or '赔率' in t_html:
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t_html, re.S)
                parsed = []
                for r in rows:
                    cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
                    if cells:
                        parsed.append(cells)
                if len(parsed) > 3:
                    company_tables.append(parsed)

        if company_tables:
            result["betting_tables"] = company_tables
            print(f"  投注分析: {len(company_tables)} company tables, rows: {[len(t) for t in company_tables]}")

    results[fid] = result

# Save
out = PROJ / "deep_data_extra.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n✅ Saved: {out}")

# Summary
print(f"\n{'='*60}")
print("数据收集状态")
print(f"{'='*60}")
for fid, info in MATCH_MAP.items():
    r = results.get(fid, {})
    home_lu = r.get("home_lineup", {})
    away_lu = r.get("away_lineup", {})
    h_start = len(home_lu.get("starting", []))
    a_start = len(away_lu.get("starting", []))
    h_inj = len(home_lu.get("injuries", []))
    a_inj = len(away_lu.get("injuries", []))
    has_betting = bool(r.get("betting_tables"))
    has_macau = bool(r.get("macau"))
    has_future = bool(r.get("future_fixtures"))

    parts = []
    if h_start or a_start: parts.append(f"首发✅({h_start}+{a_start})")
    else: parts.append("首发❌")
    if h_inj or a_inj: parts.append(f"伤停✅({h_inj}+{a_inj})")
    else: parts.append("伤停❌")
    if has_betting: parts.append("赔率公司✅")
    if has_macau: parts.append("澳门✅")
    if has_future: parts.append("赛程✅")

    print(f"  {info['mn']} {info['home']} vs {info['away']}: {', '.join(parts)}")
