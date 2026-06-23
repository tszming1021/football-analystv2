#!/usr/bin/env python3
"""Parse saved 500.com trade page HTML into structured JSON."""
import re, json
from pathlib import Path
from datetime import datetime

path = Path("/Users/jamesm/Desktop/【竞彩足球混合】数据资讯_足彩_足球彩票_500彩票网.html")
raw = path.read_bytes()
text = raw.decode("gb18030", "replace")

more_tables = re.findall(r'<table class="bet-more-tb[^"]*">(.*?)</table>', text, re.S)

# Group by 3 tables per match
all_expanded = []
for chunk_start in range(0, len(more_tables), 3):
    chunk = more_tables[chunk_start:chunk_start+3]
    if len(chunk) < 3:
        break
    data = {"score_odds": {}, "total_goals_odds": {}, "half_full_odds": {}}
    for table_html in chunk:
        for val, sp in re.findall(r'data-type="bqc"[^>]*data-value="([^"]*)"[^>]*data-sp="([^"]*)"', table_html):
            data["half_full_odds"][val] = float(sp)
        for val, sp in re.findall(r'data-type="bf"[^>]*data-value="([^"]*)"[^>]*data-sp="([^"]*)"', table_html):
            data["score_odds"][val] = float(sp)
        for val, sp in re.findall(r'data-type="jqs"[^>]*data-value="([^"]*)"[^>]*data-sp="([^"]*)"', table_html):
            data["total_goals_odds"][val] = float(sp)
    all_expanded.append(data)

# Extract attributes
fixture_ids = re.findall(r'data-fixtureid="(\d+)"', text)
match_nums = re.findall(r'data-matchnum="([^"]*)"', text)
home_teams = re.findall(r'data-homesxname="([^"]*)"', text)
away_teams = re.findall(r'data-awaysxname="([^"]*)"', text)
match_dates = re.findall(r'data-matchdate="([^"]*)"', text)
match_times = re.findall(r'data-matchtime="([^"]*)"', text)
rangqius = re.findall(r'data-rangqiu="([^"]*)"', text)
leagues = re.findall(r'data-simpleleague="([^"]*)"', text)
isends = re.findall(r'data-isend="(\d+)"', text)

tr_tags = re.findall(r'<tr\s+class="bet-tb-tr".*?</tr>', text, re.S)

all_matches = []
for i, row_html in enumerate(tr_tags):
    m = {
        "fixture_id": fixture_ids[i] if i < len(fixture_ids) else "",
        "match_num": match_nums[i] if i < len(match_nums) else "",
        "league": leagues[i] if i < len(leagues) else "",
        "home_team": home_teams[i] if i < len(home_teams) else "",
        "away_team": away_teams[i] if i < len(away_teams) else "",
        "match_date": match_dates[i] if i < len(match_dates) else "",
        "match_time": match_times[i] if i < len(match_times) else "",
        "handicap": int(rangqius[i]) if i < len(rangqius) and rangqius[i].lstrip('-').isdigit() else 0,
        "sale_status": "closed" if (isends[i] if i < len(isends) else "0") == "1" else "available_or_displayed",
    }

    nspf_btns = re.findall(r'data-type="nspf"[^>]*data-value="([^"]*)"[^>]*data-sp="([^"]*)"', row_html)
    if nspf_btns:
        odds_map = {v: float(sp) for v, sp in nspf_btns}
        m["no_handicap_odds"] = {
            "home_win": odds_map.get("3", 0),
            "draw": odds_map.get("1", 0),
            "away_win": odds_map.get("0", 0),
            "source": "500彩票网竞彩胜平负"
        }

    spf_btns = re.findall(r'data-type="spf"[^>]*data-value="([^"]*)"[^>]*data-sp="([^"]*)"', row_html)
    if spf_btns:
        odds_map = {v: float(sp) for v, sp in spf_btns}
        m["handicap_odds"] = {
            "home_win": odds_map.get("3", 0),
            "draw": odds_map.get("1", 0),
            "away_win": odds_map.get("0", 0),
        }

    if i < len(all_expanded):
        m["score_odds"] = all_expanded[i]["score_odds"]
        m["total_goals_odds"] = all_expanded[i]["total_goals_odds"]
        m["half_full_odds"] = all_expanded[i]["half_full_odds"]

    all_matches.append(m)

# Print
print(f"\n{'='*80}")
print(f"2026-06-06 竞彩足球完整数据 (共 {len(all_matches)} 场)")
print(f"{'='*80}")

for m in all_matches:
    print(f"\n{'─'*80}")
    handicap_str = "{0:+d}".format(m['handicap']) if m['handicap'] else "0"
    status_str = "可投注" if m['sale_status'] != 'closed' else "已截止"
    print(f"【{m['match_num']}】{m['home_team']} vs {m['away_team']}  |  {m['league']}  |  {m['match_date']} {m['match_time']}")
    print(f"      让球: {handicap_str}  |  {status_str}  |  fixture_id: {m['fixture_id']}")

    nspf = m.get('no_handicap_odds', {})
    print(f"      胜平负:  主@{nspf.get('home_win','?')}  平@{nspf.get('draw','?')}  客@{nspf.get('away_win','?')}")

    spf = m.get('handicap_odds', {})
    print(f"      让球SP:  让胜@{spf.get('home_win','?')}  让平@{spf.get('draw','?')}  让负@{spf.get('away_win','?')}")

    scores = m.get('score_odds', {})
    if scores:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])[:6]
        print(f"      比分({len(scores)}项): {' | '.join(f'{s}@{o:.0f}' for s,o in sorted_scores)}")

    goals = m.get('total_goals_odds', {})
    if goals:
        print(f"      总进球({len(goals)}项): {' | '.join(f'{k}球@{v:.1f}' for k,v in sorted(goals.items(), key=lambda x: int(x[0])))}")

    hf = m.get('half_full_odds', {})
    if hf:
        sorted_hf = sorted(hf.items(), key=lambda x: x[1])[:5]
        print(f"      半全场({len(hf)}项): {' | '.join(f'{s}@{o:.0f}' for s,o in sorted_hf)}")

# Save
output = {
    "fetch_time": datetime.now().isoformat(),
    "source": "500.com trade page saved HTML",
    "total_matches": len(all_matches),
    "matches": all_matches
}

outpath = Path("/Users/jamesm/Desktop/football-analyst-skill/500_trade_supplement_local.json")
outpath.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n{'='*80}")
print(f"已保存: 500_trade_supplement_local.json")
print(f"比赛: {len(all_matches)}场 | 比分项: {sum(len(m.get('score_odds',{})) for m in all_matches)} | 总进球: {sum(len(m.get('total_goals_odds',{})) for m in all_matches)} | 半全场: {sum(len(m.get('half_full_odds',{})) for m in all_matches)}")
