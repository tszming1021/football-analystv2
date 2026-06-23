#!/usr/bin/env python3
"""Parse all 500.com deep analysis HTML pages for the 6 J-League matches."""
import re, json, sys
from pathlib import Path
from html import unescape

DESKTOP = Path("/Users/jamesm/Desktop")

MATCH_FILES = {
    "1412635": {"home": "鹿岛鹿角", "away": "神户胜利船", "match_num": "周六201"},
    "1412637": {"home": "町田泽维亚", "away": "名古屋鲸八", "match_num": "周六202"},
    "1412640": {"home": "浦和红钻", "away": "冈山绿雉", "match_num": "周六203"},
    "1412641": {"home": "横滨水手", "away": "清水鼓动", "match_num": "周六204"},
    "1412642": {"home": "柏太阳神", "away": "京都不死鸟", "match_num": "周六205"},
    "1412638": {"home": "川崎前锋", "away": "广岛三箭", "match_num": "周六206"},
}

def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_analysis_html(filepath):
    """Parse a 数据分析 (data analysis) HTML page."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")
    data = {}

    # --- Recent form tables ---
    # Home recent: 近期战绩 主队, Away recent: 近期战绩 客队
    # These are in tables with class "s_table"
    form_tables = re.findall(r'<table[^>]*class="s_table"[^>]*>(.*?)</table>', text, re.S)
    records = []
    for table_html in form_tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S)
        for row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if not cells or len(cells) < 7:
                continue
            record = {
                "date": strip_html(cells[0]),
                "competition": strip_html(cells[1]),
                "home_team": strip_html(cells[2]),
                "score": strip_html(cells[3]),
                "away_team": strip_html(cells[4]),
                "handicap": strip_html(cells[5]) if len(cells) > 5 else "",
                "handicap_result": strip_html(cells[6]) if len(cells) > 6 else "",
            }
            # Check if contains score
            if re.search(r'\d+:\d+', record["score"]):
                records.append(record)
    if records:
        # Split: first half is home recent, second half is away recent
        # But they may be mixed. Look for subtitle markers in text.
        data["match_records"] = records

    # --- H2H table ---
    h2h_section = re.search(r'交战历史.*?</table>', text, re.S)
    if h2h_section:
        h2h_html = h2h_section.group(0)
        h2h_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', h2h_html, re.S)
        h2h_records = []
        for row_html in h2h_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 5:
                h2h_records.append({
                    "date": strip_html(cells[0]),
                    "competition": strip_html(cells[1]) if len(cells) > 1 else "",
                    "home_team": strip_html(cells[2]) if len(cells) > 2 else "",
                    "score": strip_html(cells[3]) if len(cells) > 3 else "",
                    "away_team": strip_html(cells[4]) if len(cells) > 4 else "",
                })
        data["h2h_records"] = h2h_records

    # --- League standings ---
    # Home team rank: [日职2] or similar
    home_rank = re.search(r'(?:鹿岛鹿角|町田泽维亚|浦和红钻|横滨水手|柏太阳神|川崎前锋).*?\[([^\]]+)\]', text)
    if home_rank:
        data["home_rank"] = home_rank.group(1)
    away_rank = re.search(r'(?:神户胜利船|名古屋鲸八|冈山绿雉|清水鼓动|京都不死鸟|广岛三箭).*?\[([^\]]+)\]', text)
    if away_rank:
        data["away_rank"] = away_rank.group(1)

    # League standing table
    standing_section = re.search(r'赛前联赛积分排名.*?</table>', text, re.S)
    if not standing_section:
        standing_section = re.search(r'联赛积分排名.*?</table>', text, re.S)
    if standing_section:
        standing_text = standing_section.group(0)
        standing_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', standing_text, re.S)
        standings_data = []
        for row_html in standing_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 8:
                standings_data.append({
                    "rank": strip_html(cells[0]),
                    "team": strip_html(cells[1]),
                    "played": strip_html(cells[2]),
                    "win": strip_html(cells[3]),
                    "draw": strip_html(cells[4]),
                    "loss": strip_html(cells[5]),
                    "goals": strip_html(cells[6]),
                    "points": strip_html(cells[7]),
                })
        data["league_standings"] = standings_data

    # --- Future fixtures ---
    future_section = re.search(r'未来赛事.*?</table>', text, re.S)
    if future_section:
        future_text = future_section.group(0)
        future_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', future_text, re.S)
        future_data = []
        for row_html in future_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 3:
                future_data.append({
                    "date": strip_html(cells[0]),
                    "competition": strip_html(cells[1]),
                    "match": strip_html(cells[2]),
                })
        data["future_fixtures"] = future_data

    # --- Predicted lineups and injuries ---
    # Find the formation/lineup section
    injury_section = re.search(r'伤病.*?</table>', text, re.S | re.I)
    if not injury_section:
        injury_section = re.search(r'停赛.*?</table>', text, re.S | re.I)

    # Look for player names with numbers in the lineup area
    lineup_area_start = text.find("预计阵容")
    if lineup_area_start < 0:
        lineup_area_start = text.find("阵容")
    if lineup_area_start >= 0:
        lineup_area = text[lineup_area_start:lineup_area_start+10000]
    else:
        lineup_area = text[1000:15000]  # fallback to beginning area

    # Extract home and away lineup info
    home_players = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}
    away_players = {"starting": [], "substitutes": [], "injuries": [], "suspensions": []}

    # The page structure has team_a (home) and team_b (away) sections
    # Each with: 首发, 替补, 伤病, 停赛
    team_sections = re.findall(r'<div class="team_[ab]">(.*?)(?=<div class="team_[ab]">|$)', lineup_area, re.S)
    if len(team_sections) >= 2:
        for idx, section in enumerate(team_sections):
            target = home_players if idx == 0 else away_players
            # Starting
            start_rows = re.findall(r'首发.*?</tr>', section, re.S)
            for row_html in start_rows:
                players = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for p in players:
                    name = strip_html(p)
                    if name and not re.match(r'^[-–—\s]*$', name) and '首发' not in name:
                        target["starting"].append(name)

            # Substitutes
            sub_rows = re.findall(r'替补.*?</tr>', section, re.S)
            for row_html in sub_rows:
                players = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for p in players:
                    name = strip_html(p)
                    if name and not re.match(r'^[-–—\s]*$', name) and '替补' not in name:
                        target["substitutes"].append(name)

            # Injuries
            inj_rows = re.findall(r'伤病.*?</tr>', section, re.S)
            for row_html in inj_rows:
                players = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for p in players:
                    name = strip_html(p)
                    if name and not re.match(r'^[-–—\s]*$', name) and '伤病' not in name:
                        target["injuries"].append(name)

            # Suspensions
            susp_rows = re.findall(r'停赛.*?</tr>', section, re.S)
            for row_html in susp_rows:
                players = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for p in players:
                    name = strip_html(p)
                    if name and not re.match(r'^[-–—\s]*$', name) and '停赛' not in name:
                        target["suspensions"].append(name)

            # Also search broader
            all_player_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', section, re.S)
            for row_html in all_player_rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
                for cell in cells:
                    cleaned = strip_html(cell)
                    # Match player patterns: "10大迫勇也(前锋)" or just player names
                    if re.match(r'^\d+', cleaned) and len(cleaned) > 3:
                        name_only = re.sub(r'^\d+\s*', '', cleaned)
                        name_only = re.sub(r'\([^)]*\)', '', name_only)
                        if name_only.strip() and name_only.strip() not in target["starting"]:
                            if "替补" in row_html or "sub" in row_html.lower():
                                if name_only.strip() not in target["substitutes"]:
                                    target["substitutes"].append(name_only.strip())
                            else:
                                if name_only.strip() not in target["starting"]:
                                    target["starting"].append(name_only.strip())

    data["home_lineup"] = home_players
    data["away_lineup"] = away_players

    # --- Recent form summary (stats) ---
    # Look for 近10场 / 近6场 summary text
    form_texts = re.findall(r'(?:近\d+场[^。，\.]*(?:[。，\.]|$))', text)
    data["form_summaries"] = form_texts[:10]

    # --- FIFA rankings ---
    fifa_section = re.search(r'FIFA排名.*?</table>', text, re.S)
    if fifa_section:
        fifa_text = fifa_section.group(0)
        fifa_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', fifa_text, re.S)
        fifa_data = []
        for row_html in fifa_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 4:
                fifa_data.append({
                    "month": strip_html(cells[0]),
                    "rank": strip_html(cells[1]),
                    "points": strip_html(cells[2]),
                    "change": strip_html(cells[3]),
                })
        data["fifa_rankings"] = fifa_data

    # --- Macau recommendation ---
    macau_section = re.search(r'澳门心水.*?</div>', text, re.S)
    if macau_section:
        data["macau_recommendation"] = strip_html(macau_section.group(0))

    return data


def parse_betting_html(filepath):
    """Parse a 投注分析 (betting analysis) HTML page."""
    raw = filepath.read_bytes()
    text = raw.decode("gb18030", "replace")
    data = {}

    # Euro odds table
    euro_section = re.search(r'百家欧赔.*?</table>', text, re.S)
    if euro_section:
        euro_text = euro_section.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', euro_text, re.S)
        companies = []
        for row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 4:
                companies.append({
                    "company": strip_html(cells[0]),
                    "home_open": strip_html(cells[1]) if len(cells) > 1 else "",
                    "draw_open": strip_html(cells[2]) if len(cells) > 2 else "",
                    "away_open": strip_html(cells[3]) if len(cells) > 3 else "",
                })
        data["europe_companies"] = companies

    # Asian handicap table
    asian_section = re.search(r'亚盘对比.*?</table>', text, re.S)
    if asian_section:
        asian_text = asian_section.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', asian_text, re.S)
        asian_companies = []
        for row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 6:
                asian_companies.append({
                    "company": strip_html(cells[0]),
                    "open_handicap": strip_html(cells[1]),
                    "open_home_water": strip_html(cells[2]),
                    "open_away_water": strip_html(cells[3]),
                    "current_handicap": strip_html(cells[4]),
                    "current_home_water": strip_html(cells[5]),
                    "current_away_water": strip_html(cells[6]) if len(cells) > 6 else "",
                })
        data["asian_companies"] = asian_companies

    # Over/under table
    ou_section = re.search(r'大小球指数.*?</table>', text, re.S)
    if ou_section:
        ou_text = ou_section.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', ou_text, re.S)
        ou_companies = []
        for row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 6:
                ou_companies.append({
                    "company": strip_html(cells[0]),
                    "open_line": strip_html(cells[1]),
                    "open_over_water": strip_html(cells[2]),
                    "open_under_water": strip_html(cells[3]),
                    "current_line": strip_html(cells[4]),
                    "current_over_water": strip_html(cells[5]),
                    "current_under_water": strip_html(cells[6]) if len(cells) > 6 else "",
                })
        data["over_under_companies"] = ou_companies

    # Score index
    score_section = re.search(r'比分指数.*?</table>', text, re.S)
    if score_section:
        score_text = score_section.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', score_text, re.S)
        score_data = []
        for row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S)
            if len(cells) >= 4:
                score_data.append({
                    "score": strip_html(cells[0]),
                    "home_water": strip_html(cells[1]) if len(cells) > 1 else "",
                    "draw_water": strip_html(cells[2]) if len(cells) > 2 else "",
                    "away_water": strip_html(cells[3]) if len(cells) > 3 else "",
                })
        data["score_index"] = score_data

    return data


def parse_all():
    results = {}
    for fid, info in MATCH_FILES.items():
        home = info["home"]
        away = info["away"]
        mn = info["match_num"]
        print(f"\nParsing {mn} {home} vs {away}...")

        # Find analysis file
        analysis_files = list(DESKTOP.glob(f"*{home}*{away}*数据分析*"))
        betting_files = list(DESKTOP.glob(f"*{home}*{away}*投注分析*"))

        result = {
            "fixture_id": fid, "match_num": mn,
            "home_team": home, "away_team": away,
        }

        if analysis_files:
            try:
                deep = parse_analysis_html(analysis_files[0])
                result["deep_data"] = deep
                print(f"  数据分析: OK - records={len(deep.get('match_records',[]))}, h2h={len(deep.get('h2h_records',[]))}, standings={len(deep.get('league_standings',[]))}, home_starters={len(deep.get('home_lineup',{}).get('starting',[]))}, away_starters={len(deep.get('away_lineup',{}).get('starting',[]))}")
            except Exception as e:
                print(f"  数据分析: ERROR - {e}")
        else:
            print(f"  No analysis file found for {home} vs {away}")

        if betting_files:
            try:
                betting = parse_betting_html(betting_files[0])
                result["betting_data"] = betting
                print(f"  投注分析: OK - euro={len(betting.get('europe_companies',[]))}, asian={len(betting.get('asian_companies',[]))}, ou={len(betting.get('over_under_companies',[]))}")
            except Exception as e:
                print(f"  投注分析: ERROR - {e}")
        else:
            print(f"  No betting file found for {home} vs {away}")

        results[fid] = result

    out = Path("/Users/jamesm/Desktop/football-analyst-skill/deep_data_parsed.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved to {out}")
    return results

if __name__ == "__main__":
    parse_all()
