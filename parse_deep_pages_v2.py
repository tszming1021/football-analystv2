#!/usr/bin/env python3
"""Parse all 500.com deep analysis pages - v2 with proper structure."""
import re, json
from pathlib import Path
from html import unescape

DESKTOP = Path("/Users/jamesm/Desktop")

def strip(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_mbox_sections(text):
    """Extract M_box sections by h4 title."""
    sections = {}
    pattern = re.compile(
        r'<h4>(.*?)</h4>.*?<div class="M_box[^"]*">(.*?)(?=<div class="M_box[^"]*">|<div class="M_title">|$)',
        re.S
    )
    for match in pattern.finditer(text):
        title = strip(match.group(1))
        content = match.group(2)
        sections[title] = content
    return sections

def parse_records_table(html):
    """Parse match records from table HTML."""
    records = []
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for row_html in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)
        if len(cells) < 7:
            continue
        # Extract score which should contain "X:Y"
        score_cell = strip(cells[3]) if len(cells) > 3 else ""
        if re.search(r'\d+:\d+', score_cell):
            records.append({
                "date": strip(cells[0]), "competition": strip(cells[1]),
                "home_team": strip(cells[2]), "score": score_cell,
                "away_team": strip(cells[4]),
                "handicap": strip(cells[5]) if len(cells) > 5 else "",
                "result": strip(cells[6]) if len(cells) > 6 else "",
                "goals_result": strip(cells[7]) if len(cells) > 7 else "",
            })
    return records

def parse_lineup_from_text(text):
    """Parse lineup, injuries, suspensions from team sections."""
    home = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}
    away = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}

    # Find team_a and team_b sections
    team_a = re.search(r'<div class="team_a">(.*?)(?:<div class="team_b">|$)', text, re.S)
    team_b = re.search(r'<div class="team_b">(.*?)(?:<div class="M_box|</div>\s*</div>\s*</div>|$)', text, re.S)

    for team_html, target in [(team_a.group(1) if team_a else "", home),
                                (team_b.group(1) if team_b else "", away)]:
        if not team_html:
            continue
        # Parse pub_table rows
        all_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', team_html, re.S)

        current_section = "starting"
        for cell in all_cells:
            cell_text = strip(cell)
            if "首发" in cell_text: current_section = "starting"; continue
            if "替补" in cell_text: current_section = "substitutes"; continue
            if "伤病" in cell_text: current_section = "injuries"; continue
            if "停赛" in cell_text: current_section = "suspensions"; continue

            # Extract player name from format like "9莱奥·塞阿拉(前锋)"
            player_match = re.match(r'^\d+\s*(.+?)(?:\([^)]*\))?$', cell_text)
            if player_match and len(cell_text) > 2:
                name = player_match.group(1).strip()
                if name and not re.match(r'^[-–—]+$', name):
                    target[current_section].append(name)

    return home, away

def parse_standing_table(html):
    """Parse league standing table."""
    rows_data = []
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for row_html in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)
        cell_texts = [strip(c) for c in cells]
        if len(cell_texts) >= 7 and cell_texts[0].isdigit():
            rows_data.append({
                "rank": cell_texts[0], "team": cell_texts[1],
                "played": cell_texts[2], "win": cell_texts[3],
                "draw": cell_texts[4], "loss": cell_texts[5],
                "goals": cell_texts[6] if len(cell_texts) > 6 else "",
                "points": cell_texts[7] if len(cell_texts) > 7 else "",
            })
    return rows_data

def parse_betting_tables(text):
    """Parse betting analysis page - euro, asian, OU tables."""
    data = {}

    # Find all main tables
    tables = re.findall(r'<table[^>]*class="[^"]*odds[^"]*"[^>]*>(.*?)</table>', text, re.S)
    if not tables:
        tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.S)

    for table_html in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S)
        parsed_rows = []
        for row_html in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)
            parsed_rows.append([strip(c) for c in cells])

        # Identify table type
        first_row = parsed_rows[0] if parsed_rows else []
        first_str = " ".join(first_row)
        if "欧赔" in first_str or "初盘赔率" in first_str:
            data["europe_companies"] = parsed_rows
        elif "亚盘" in first_str or "让球" in first_str:
            data["asian_companies"] = parsed_rows
        elif "大" in first_str and ("小" in first_str or "球" in first_str):
            data["over_under_companies"] = parsed_rows
        elif "比分" in first_str:
            data["score_index"] = parsed_rows

    return data


def parse_all():
    results = {}

    MATCH_FILES = {
        "1412635": {"home": "鹿岛鹿角", "away": "神户胜利船", "mn": "周六201"},
        "1412637": {"home": "町田泽维亚", "away": "名古屋鲸八", "mn": "周六202"},
        "1412640": {"home": "浦和红钻", "away": "冈山绿雉", "mn": "周六203"},
        "1412641": {"home": "横滨水手", "away": "清水鼓动", "mn": "周六204"},
        "1412642": {"home": "柏太阳神", "away": "京都不死鸟", "mn": "周六205"},
        "1412638": {"home": "川崎前锋", "away": "广岛三箭", "mn": "周六206"},
    }

    for fid, info in MATCH_FILES.items():
        home, away, mn = info["home"], info["away"], info["mn"]
        print(f"\n{'='*60}")
        print(f"{mn} {home} vs {away}")

        result = {"fixture_id": fid, "match_num": mn, "home_team": home, "away_team": away}

        # Analysis file
        analysis_files = list(DESKTOP.glob(f"*{home}*{away}*数据分析*.html"))
        if analysis_files:
            raw = analysis_files[0].read_bytes()
            text = raw.decode("gb18030", "replace")
            sections = extract_mbox_sections(text)

            for title, html in sections.items():
                if "联赛积分" in title:
                    result["league_standings"] = parse_standing_table(html)
                    print(f"  联赛积分: {len(result['league_standings'])} teams")
                elif "交战" in title:
                    result["h2h_records"] = parse_records_table(html)
                    print(f"  交战历史: {len(result['h2h_records'])} records")
                elif "近期战绩" in title:
                    result["recent_records"] = parse_records_table(html)
                    print(f"  近期战绩: {len(result['recent_records'])} records")
                elif "未来赛事" in title:
                    result["future_fixtures"] = parse_records_table(html)
                    print(f"  未来赛事: {len(result['future_fixtures'])} rows")
                elif "预计阵容" in title:
                    home_lu, away_lu = parse_lineup_from_text(html)
                    result["home_lineup"] = home_lu
                    result["away_lineup"] = away_lu
                    print(f"  阵容: home_starters={len(home_lu['starting'])}, away_starters={len(away_lu['starting'])}, home_inj={len(home_lu['injuries'])}, away_inj={len(away_lu['injuries'])}")
                elif "澳门" in title:
                    result["macau_recommendation"] = strip(html)
                    print(f"  澳门心水: {len(result['macau_recommendation'])} chars")
                elif "平均数据" in title:
                    result["team_averages"] = strip(html)[:500]
                    print(f"  平均数据: OK")

            if not sections:
                print(f"  WARNING: No M_box sections found!")

        # Betting file
        betting_files = list(DESKTOP.glob(f"*{home}*{away}*投注分析*.html"))
        if betting_files:
            raw = betting_files[0].read_bytes()
            text = raw.decode("gb18030", "replace")
            betting = parse_betting_tables(text)
            result["betting_data"] = betting
            for k, v in betting.items():
                print(f"  投注-{k}: {len(v)} rows")

        results[fid] = result

    out = Path("/Users/jamesm/Desktop/football-analyst-skill/deep_data_parsed.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved to {out}")
    return results

if __name__ == "__main__":
    parse_all()
