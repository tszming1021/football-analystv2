#!/usr/bin/env python3
"""Complete parser: all lineups + injuries + betting data from all 12 HTML files."""
import re, json
from pathlib import Path
from html import unescape

DESKTOP = Path("/Users/jamesm/Desktop")
PROJ = Path("/Users/jamesm/Desktop/football-analyst-skill")

MATCH_MAP = {
    "1412635": {"home": "鹿岛鹿角", "away": "神户胜利船", "mn": "周六201"},
    "1412637": {"home": "町田泽维亚", "away": "名古屋鲸八", "mn": "周六202"},
    "1412640": {"home": "浦和红钻", "away": "冈山绿雉", "mn": "周六203"},
    "1412641": {"home": "横滨水手", "away": "清水鼓动", "mn": "周六204"},
    "1412642": {"home": "柏太阳神", "away": "京都不死鸟", "mn": "周六205"},
    "1412638": {"home": "川崎前锋", "away": "广岛三箭", "mn": "周六206"},
}

def strip(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = unescape(s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def extract_name(cell_text):
    """Extract clean player name from cell like '9 莱奥·塞阿拉(前锋)'"""
    name = re.sub(r'^\d+\s*', '', cell_text)
    name = re.sub(r'\([^)]*\)', '', name).strip()
    return name

def parse_lineups_from_file(filepath):
    """Parse both teams' lineups from a 数据分析 HTML file."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")

    result = {"home": {"starting": [], "substitutes": [], "injuries": [], "suspensions": []},
              "away": {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}}

    # Find lineup area: search for the first "阵型" marker (near position 139000 area)
    formation_positions = [m.start() for m in re.finditer(r'阵型', text)]
    if not formation_positions:
        formation_positions = [m.start() for m in re.finditer(r'pub_table', text)]

    lineup_area_start = formation_positions[-2] - 500 if len(formation_positions) >= 2 else 139000
    lineup_area = text[lineup_area_start:lineup_area_start + 10000]

    # Find pub_table tables in lineup area
    tables = re.findall(r'<table[^>]*class="pub_table"[^>]*>(.*?)</table>', lineup_area, re.S)

    if len(tables) >= 2:
        for team_idx, side in enumerate(["home", "away"]):
            if team_idx >= len(tables):
                break
            t = tables[team_idx]
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
            # Column-based parsing: left col = starting/injuries, right col = subs/suspensions
            left_names = []; right_names = []
            left_section = "starting"; right_section = "substitutes"

            for row_html in rows:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)
                cell_texts = [strip(c) for c in cells]

                # Check for section header keywords in each cell
                for ci, ct in enumerate(cell_texts):
                    ct_clean = ct.replace('-', '').replace(' ', '')
                    if '首发' in ct_clean:
                        if ci == 0: left_section = "starting"
                        else: right_section = "starting"
                        continue
                    if '替补' in ct_clean:
                        if ci == 0: left_section = "substitutes"
                        else: right_section = "substitutes"
                        continue
                    if '伤病' in ct_clean:
                        if ci == 0: left_section = "injuries"
                        else: right_section = "injuries"
                        continue
                    if '停赛' in ct_clean:
                        if ci == 0: left_section = "suspensions"
                        else: right_section = "suspensions"
                        continue

                    name = extract_name(ct)
                    if not name or len(name) < 2: continue
                    if name in ['首发', '替补', '伤病', '停赛']: continue
                    if re.match(r'^[-–—•·\s]+$', name): continue

                    if ci == 0 and name not in result[side][left_section]:
                        result[side][left_section].append(name)
                    elif ci == 1 and name not in result[side][right_section]:
                        result[side][right_section].append(name)

    return result


def parse_betting_tables(filepath):
    """Parse euro/asian/OU/score data from 投注分析 HTML."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")
    result = {}

    # Find the main data tables - they contain "百家欧赔" or company names
    # Look for tab_content sections
    tab_sections = re.findall(r'<div[^>]*id="[^"]*tab[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S)

    all_tables = []
    for section in tab_sections:
        tables = re.findall(r'<table[^>]*>(.*?)</table>', section, re.S)
        for t in tables:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
            parsed = []
            for r in rows:
                cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
                if cells:
                    parsed.append(cells)
            if len(parsed) > 2:
                all_tables.append(parsed)

    # Also look for tables directly in the page
    if not all_tables:
        all_tables_raw = re.findall(r'<table[^>]*>(.*?)</table>', text, re.S)
        for t_html in all_tables_raw:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t_html, re.S)
            parsed = []
            for r in rows:
                cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
                if cells:
                    parsed.append(cells)
            # Filter: must have company-like data
            has_companies = any(
                any('威廉' in c or 'Bet' in c or '澳门' in c or '立博' in c for c in row)
                for row in parsed
            )
            if has_companies and len(parsed) > 3:
                all_tables.append(parsed)

    if all_tables:
        result["tables"] = all_tables

    return result


def parse_macau(text):
    """Extract Macau recommendation."""
    # Find after the "澳门心水推荐" h4
    pos = text.find("澳门心水推荐")
    if pos < 0:
        return ""
    section = text[pos:pos + 5000]
    # Get the recommendation text
    # Usually in a div after the h4
    rec_match = re.search(r'推介[^：]*[：:]\s*(.*?)(?:<|$|<br)', section, re.S)
    if rec_match:
        return strip(rec_match.group(1))[:300]
    # Try broader
    text_match = re.search(r'<td[^>]*>(.{50,300}?)</td>', section, re.S)
    if text_match:
        return strip(text_match.group(1))[:300]
    return strip(section)[:300]


def parse_future_fixtures(text):
    """Extract future fixtures table."""
    pos = text.find("未来赛事")
    if pos < 0:
        return []
    section = text[pos:pos + 5000]
    tables = re.findall(r'<table[^>]*>(.*?)</table>', section, re.S)
    futures = []
    for t in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
        for r in rows:
            cells = [strip(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
            if len(cells) >= 3 and re.search(r'\d{4}-\d{2}-\d{2}', cells[0]):
                futures.append({"date": cells[0], "competition": cells[1], "match": cells[2]})
    return futures


# ═══════════ MAIN ═══════════

all_results = {}

for fid, info in MATCH_MAP.items():
    home, away = info["home"], info["away"]
    print(f"\n{'='*60}")
    print(f"{info['mn']} {home} vs {away}")

    result = {"fixture_id": fid, "match_num": info["mn"], "home_team": home, "away_team": away}

    # Analysis page
    analysis_files = list(DESKTOP.glob(f"*{home}*{away}*数据分析*.html"))
    if analysis_files:
        apath = analysis_files[0]
        raw = apath.read_bytes()
        text = raw.decode("gb18030", "replace")

        # Lineups
        lineups = parse_lineups_from_file(apath)
        result["lineups"] = lineups
        for side in ["home", "away"]:
            lu = lineups[side]
            print(f"  {side}: start={len(lu['starting'])}, sub={len(lu['substitutes'])}, inj={len(lu['injuries'])}, susp={len(lu['suspensions'])}")
            if lu['starting']:
                print(f"    首发: {', '.join(lu['starting'][:5])}...")
            if lu['injuries']:
                print(f"    伤病: {', '.join(lu['injuries'])}")
            if lu['suspensions']:
                print(f"    停赛: {', '.join(lu['suspensions'])}")

        # Macau
        result["macau"] = parse_macau(text)
        if result["macau"]:
            print(f"  澳门: {result['macau'][:100]}...")

        # Future fixtures
        result["future"] = parse_future_fixtures(text)
        if result["future"]:
            print(f"  未来赛程: {len(result['future'])}条")
            for ff in result["future"][:3]:
                print(f"    {ff['date']} {ff['match']}")

    # Betting page
    betting_files = list(DESKTOP.glob(f"*{home}*{away}*投注分析*.html"))
    if betting_files:
        betting = parse_betting_tables(betting_files[0])
        result["betting"] = betting
        if betting.get("tables"):
            for ti, t in enumerate(betting["tables"]):
                print(f"  投注表{ti}: {len(t)}行, header={t[0][:6] if t else 'N/A'}")

    all_results[fid] = result

# Save
outpath = PROJ / "complete_parsed_data.json"
json.dump(all_results, open(outpath, "w"), ensure_ascii=False, indent=2)
print(f"\n{'='*60}")
print(f"✅ All data saved to {outpath}")
print(f"   {len(all_results)} matches parsed")

# Quick summary
print(f"\n{'='*60}")
print("数据完整性检查")
print(f"{'='*60}")
for fid, info in MATCH_MAP.items():
    r = all_results.get(fid, {})
    lu = r.get("lineups", {})
    h_s = len(lu.get("home", {}).get("starting", []))
    a_s = len(lu.get("away", {}).get("starting", []))
    h_inj = len(lu.get("home", {}).get("injuries", []))
    a_inj = len(lu.get("away", {}).get("injuries", []))
    has_macau = bool(r.get("macau"))
    has_future = bool(r.get("future"))
    has_betting = bool(r.get("betting", {}).get("tables"))

    parts = []
    parts.append(f"首发✅({h_s}+{a_s})" if h_s+a_s > 0 else "首发❌")
    parts.append(f"伤停✅({h_inj}+{a_inj})" if h_inj+a_inj > 0 else "伤停❌")
    parts.append("澳门✅" if has_macau else "澳门❌")
    parts.append("赛程✅" if has_future else "赛程❌")
    parts.append("赔率表✅" if has_betting else "赔率表❌")
    print(f"  {info['mn']} {info['home']} vs {info['away']}: {', '.join(parts)}")
