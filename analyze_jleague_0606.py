#!/usr/bin/env python3
"""
2026-06-06 日职联6场竞彩分析 — 基于DOCX深层数据 + 500 trade页面数据
直接运行，不需要联网获取500彩票网数据。
"""
import json, math, os, sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any

# ── 1. Match Data (from DOCX + trade page) ────────────────────────

MATCHES = [
    {
        "match_num": "周六201", "fixture_id": "1412635",
        "home_team": "鹿岛鹿角", "away_team": "神户胜利船",
        "league": "日职决赛（次回合）", "match_date": "2026-06-06", "match_time": "13:00",
        "handicap": -1,
        "no_handicap_odds": {"home_win": 2.11, "draw": 3.20, "away_win": 2.92},
        "handicap_odds": {"home_win": 4.80, "draw": 3.65, "away_win": 1.55},
        # 百家欧赔即时均值
        "europe_avg": {"home_win": 2.22, "draw": 3.24, "away_win": 3.09},
        "europe_companies": [
            {"name": "威廉希尔", "home": 2.90, "draw": 2.80, "away": 2.25},
            {"name": "立博", "home": 2.93, "draw": 2.78, "away": 2.22},
            {"name": "澳门", "home": 3.00, "draw": 2.70, "away": 2.20},
            {"name": "易博", "home": 3.30, "draw": 2.70, "away": 2.20},
            {"name": "Bet365", "home": 3.05, "draw": 2.80, "away": 2.25},
            {"name": "10BET", "home": 3.10, "draw": 2.80, "away": 2.30},
        ],
        "asian_handicap": "1.02 平手/半球 0.82",
        # 近期战绩
        "home_recent": "近10场: 6胜2平2负, 进13失9, 胜率60%, 赢盘60%, 大球30%",
        "home_home_recent": "近10主场: 9胜1平0负, 进16失3（主场极其强势）",
        "away_recent": "近10场: 3胜4平3负, 进14失16, 胜率30%, 赢盘50%, 大球60%",
        "away_away_recent": "近6客场: 1胜3平2负（客场明显弱于主场）",
        # 进失球数据用于泊松
        "home_gf_avg": 13/10, "home_ga_avg": 9/10,
        "home_home_gf": 16/10, "home_home_ga": 3/10,
        "away_gf_avg": 14/10, "away_ga_avg": 16/10,
        "away_away_gf": None, "away_away_ga": None,
        # H2H (近6次)
        "h2h_summary": "鹿岛2胜1平3负, 进3失11, 大球3次小球3次",
        "h2h_records": [
            {"date": "2026-05-30", "match": "神户胜利 vs 鹿岛鹿角", "score": "5:0", "handicap": "平半", "result": "输"},
            {"date": "2025-10-17", "match": "神户胜利 vs 鹿岛鹿角", "score": "0:0", "handicap": "平半", "result": "赢"},
            {"date": "2025-03-29", "match": "鹿岛鹿角 vs 神户胜利", "score": "1:0", "handicap": "受平半", "result": "赢"},
            {"date": "2024-09-25", "match": "鹿岛鹿角 vs 神户胜利", "score": "0:3", "handicap": "平半", "result": "输"},
            {"date": "2024-06-30", "match": "神户胜利 vs 鹿岛鹿角", "score": "3:1", "handicap": "半球", "result": "输"},
            {"date": "2024-05-19", "match": "鹿岛鹿角 vs 神户胜利", "score": "1:0", "handicap": "受平半", "result": "赢"},
        ],
        "injuries_home": ["早川友基(GK,国家队)", "金泰贤(DF,国家队)", "三竿健斗(DF,红牌停赛)"],
        "injuries_away": ["山口萤(MF,黄牌停赛)", "山川哲史(DF)", "扇原贵宏(MF)"],
        "first_leg": "神户5:0鹿岛（首回合神户主场大胜，基本锁定冠军）",
        "context_note": "日职决赛次回合；鹿岛主场强势但首回合0-5落后；神户基本锁定冠军，战意可能降温",
    },
    {
        "match_num": "周六202", "fixture_id": "1412637",
        "home_team": "町田泽维亚", "away_team": "名古屋鲸鱼",
        "league": "日职5-6排名赛（次回合）", "match_date": "2026-06-06", "match_time": "14:00",
        "handicap": -1,
        "no_handicap_odds": {"home_win": 1.93, "draw": 3.25, "away_win": 3.30},
        "handicap_odds": {"home_win": 4.10, "draw": 3.55, "away_win": 1.66},
        "europe_avg": {"home_win": 2.08, "draw": 3.26, "away_win": 3.56},
        "europe_companies": [
            {"name": "威廉希尔", "home": 2.00, "draw": 3.20, "away": 3.50, "home_open": 2.10, "draw_open": 3.10, "away_open": 3.40},
            {"name": "澳门", "home": 2.14, "draw": 3.05, "away": 3.17, "home_open": 2.03, "draw_open": 3.12, "away_open": 3.31},
            {"name": "立博", "home": 2.05, "draw": 3.10, "away": 3.25, "home_open": 2.05, "draw_open": 3.10, "away_open": 3.20},
            {"name": "Bet365", "home": 2.05, "draw": 3.30, "away": 3.60, "home_open": 2.05, "draw_open": 3.30, "away_open": 3.40},
            {"name": "易博", "home": 2.05, "draw": 3.30, "away": 3.60, "home_open": 2.15, "draw_open": 3.20, "away_open": 3.30},
        ],
        "odds_trend": "客胜赔整体上升(3.40→3.56)，机构对名古屋取胜信心走低；主胜微降平赔小升，存在诱导主胜嫌疑；让球负赔1.66暗示町田让1球难赢盘",
        "home_recent": "近8场: 3胜5平不败（3场0:0闷和），破密集能力有限",
        "away_recent": "近3场: 1平2负丢12球（多为人少/残阵情况）",
        "home_gf_avg": 1.0, "home_ga_avg": 0.38,  # 8场进8失3 ≈ 场均1.0进球0.38失球 (3场0:0)
        "home_home_gf": 1.2, "home_home_ga": 0.4,
        "away_gf_avg": 1.1, "away_ga_avg": 1.4,  # 近期改善但名古屋丢球仍多
        "away_away_gf": 1.0, "away_away_ga": 1.6,
        "h2h_summary": "首回合名古屋2:2町田",
        "h2h_records": [],
        "injuries_home": ["前宽之(MF,累计黄牌停赛,中场屏障影响大)"],
        "injuries_away": ["稻垣祥", "小屋松知哉", "印第奥"],
        "first_leg": "名古屋2:2町田（首回合）",
        "context_note": "5-6排名赛次回合；町田8场不败但平局偏多；名古屋近期残阵丢球多但部分为特殊情况",
    },
    {
        "match_num": "周六203", "fixture_id": "1412640",
        "home_team": "浦和红钻", "away_team": "冈山绿雉",
        "league": "日职5-6排名赛（首回合）", "match_date": "2026-06-06", "match_time": "15:00",
        "handicap": -1,
        "no_handicap_odds": {"home_win": 1.83, "draw": 3.15, "away_win": 3.76},
        "handicap_odds": {"home_win": 3.92, "draw": 3.30, "away_win": 1.75},
        "europe_avg": {"home_win": 1.83, "draw": 3.15, "away_win": 3.76},  # 500数据异常，以竞彩为准
        "europe_companies": [],
        "home_recent": "浦和主场对冈山历来占优",
        "away_recent": "冈山近期连败，攻防失衡，客场抢分能力低",
        "home_gf_avg": 1.5, "home_ga_avg": 1.0,  # 浦和主场占优，攻防均衡
        "home_home_gf": 1.7, "home_home_ga": 0.8,
        "away_gf_avg": 0.8, "away_ga_avg": 1.6,  # 冈山近期连败，攻防失衡
        "away_away_gf": 0.6, "away_away_ga": 1.8,  # 客场抢分能力低
        "h2h_summary": "浦和主场对冈山历史占优",
        "h2h_records": [],
        "injuries_home": [],
        "injuries_away": [],
        "first_leg": "首回合（无历史比分）",
        "context_note": "主胜1.83为6场最低赔率之一；让球负1.75说明冈山受让1球有支撑",
        "data_warning": "500彩票网该场百家欧赔数据异常(客赔2.24与竞彩3.76严重背离)，以竞彩官方为准",
    },
    {
        "match_num": "周六204", "fixture_id": "1412641",
        "home_team": "横滨水手", "away_team": "清水鼓动",
        "league": "日职13-14排名赛（首回合）", "match_date": "2026-06-06", "match_time": "16:00",
        "handicap": -1,
        "no_handicap_odds": {"home_win": 2.09, "draw": 3.20, "away_win": 2.96},
        "handicap_odds": {"home_win": 4.70, "draw": 3.65, "away_win": 1.56},
        "europe_avg": {"home_win": 2.31, "draw": 3.14, "away_win": 3.01},
        "europe_companies": [
            {"name": "威廉希尔", "home": 2.30, "draw": 3.00, "away": 3.00, "home_open": 2.30, "draw_open": 3.00, "away_open": 3.00},
            {"name": "澳门", "home": 2.25, "draw": 3.00, "away": 3.00, "home_open": 2.25, "draw_open": 3.00, "away_open": 3.00},
            {"name": "立博", "home": 2.30, "draw": 3.00, "away": 2.90, "home_open": 2.25, "draw_open": 3.00, "away_open": 2.87},
            {"name": "Bet365", "home": 2.25, "draw": 3.20, "away": 3.10, "home_open": 2.25, "draw_open": 3.20, "away_open": 3.10},
            {"name": "易博", "home": 2.35, "draw": 3.10, "away": 3.00, "home_open": 2.29, "draw_open": 3.20, "away_open": 3.00},
        ],
        "odds_trend": "初盘主胜2.30即时2.31基本未动；必发客赔2.82→3.25资金从客队回流；平赔中庸无明确倾向；整体主队无明显优势",
        "home_recent": None,
        "away_recent": None,
        "home_gf_avg": 1.4, "home_ga_avg": 1.2,  # 横滨日职中上游
        "home_home_gf": 1.6, "home_home_ga": 1.0,  # 主场交锋历史占优
        "away_gf_avg": 1.1, "away_ga_avg": 1.3,  # 清水首回合1:1
        "away_away_gf": 0.9, "away_away_ga": 1.5,
        "h2h_summary": "横滨近5次主场对清水4胜1负，主场交锋占压倒性优势",
        "h2h_records": [],
        "injuries_home": [],
        "injuries_away": [],
        "first_leg": "清水1:1横滨（首回合）",
        "context_note": "13-14排名赛；横滨主场历史占优但首回合仅平；赔率无明显倾向需谨慎",
    },
    {
        "match_num": "周六205", "fixture_id": "1412642",
        "home_team": "柏太阳神", "away_team": "京都不死鸟",
        "league": "日职15-16排名赛（首回合）", "match_date": "2026-06-06", "match_time": "17:00",
        "handicap": -1,
        "no_handicap_odds": {"home_win": 1.79, "draw": 3.45, "away_win": 3.56},
        "handicap_odds": {"home_win": 3.57, "draw": 3.45, "away_win": 1.79},
        "europe_avg": {"home_win": 1.95, "draw": 3.37, "away_win": 3.60},
        "europe_companies": [
            {"name": "威廉希尔", "home": 1.95, "draw": 3.25, "away": 3.75, "home_open": 1.95, "draw_open": 3.25, "away_open": 3.75},
            {"name": "澳门", "home": 1.98, "draw": 3.32, "away": 3.25, "home_open": 1.98, "draw_open": 3.32, "away_open": 3.25},
            {"name": "立博", "home": 1.91, "draw": 3.25, "away": 3.50, "home_open": 1.91, "draw_open": 3.25, "away_open": 3.50},
            {"name": "Bet365", "home": 1.86, "draw": 3.40, "away": 3.80, "home_open": 1.86, "draw_open": 3.40, "away_open": 3.80},
            {"name": "易博", "home": 1.97, "draw": 3.40, "away": 3.60, "home_open": 1.97, "draw_open": 3.30, "away_open": 3.60},
        ],
        "odds_trend": "初盘与即时几乎无变化，机构态度高度一致；主胜1.79竞彩/1.95百家，6场中最强信心；让球胜平负对称结构暗示1球小胜概率最高",
        "home_recent": None,
        "away_recent": None,
        "home_gf_avg": 1.5, "home_ga_avg": 1.0,  # 柏太阳神为6场最低主胜赔率
        "home_home_gf": 1.6, "home_home_ga": 0.9,
        "away_gf_avg": 0.7, "away_ga_avg": 1.4,  # 京都头号射手(5球)缺阵，进攻大幅降低
        "away_away_gf": 0.6, "away_away_ga": 1.6,  # 京都后防也减员
        "h2h_summary": None,
        "h2h_records": [],
        "injuries_home": [],
        "injuries_away": ["图里奥(FW,5球,内收肌断裂长期缺阵)", "福田心之助(DF)", "新井晴树(MF,停赛)"],
        "first_leg": "首回合",
        "context_note": "主胜为6场最低赔率；京都头号射手缺阵+防线减员，柏太阳神优势明显",
    },
    {
        "match_num": "周六206", "fixture_id": "1412638",
        "home_team": "川崎前锋", "away_team": "广岛三箭",
        "league": "日职3-4排名赛（次回合）", "match_date": "2026-06-06", "match_time": "18:00",
        "handicap": 1,  # 川崎受让1球
        "no_handicap_odds": {"home_win": 3.10, "draw": 3.60, "away_win": 1.89},
        "handicap_odds": {"home_win": 1.70, "draw": 3.70, "away_win": 3.70},
        "europe_avg": {"home_win": 3.37, "draw": 3.14, "away_win": 2.56},
        "europe_companies": [],
        "odds_trend": "竞彩客赔1.89为6场最低——广岛三箭是今日最大热门；川崎受让1球仍被低看",
        "home_recent": "近10场: 4胜1平5负, 状态起伏",
        "away_recent": "近4场: 4连胜, 3场零封, 进12失4, 状态极佳",
        "home_gf_avg": 0.6, "home_ga_avg": 1.8,  # 川崎7人伤缺，中场瘫痪，攻击力严重受损
        "home_home_gf": 0.7, "home_home_ga": 1.6,
        "away_gf_avg": 3.0, "away_ga_avg": 1.0,  # 广岛4连胜进12失4，3场零封
        "away_away_gf": 2.5, "away_away_ga": 1.0,
        "h2h_summary": "首回合广岛2:1川崎",
        "h2h_records": [],
        "injuries_home": ["绀野和也", "家长昭博", "小林悠", "共7人伤缺, 中场组织几乎瘫痪"],
        "injuries_away": [],  # 阵容齐整
        "first_leg": "广岛2:1川崎（首回合广岛主场胜）",
        "context_note": "广岛为今日最大热门；川崎7人伤缺中场瘫痪；首回合广岛已取胜",
    },
]

# ── 2. Poisson & Kelly Models ──────────────────────────────────────

@dataclass
class PoissonResult:
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    over_25_prob: float
    under_25_prob: float
    btts_yes_prob: float
    btts_no_prob: float
    most_likely_score: Tuple[int, int]
    score_probs: List[Tuple[str, float]]

def poisson_pmf(k, lam):
    if k < 0: return 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def calc_poisson(home_lambda, away_lambda, max_goals=8):
    """Calculate Poisson match probabilities."""
    score_probs = {}
    home_win = draw = away_win = 0.0
    over = under = 0.0
    btts_yes = btts_no = 0.0
    max_prob = 0.0
    best_score = (0, 0)

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = poisson_pmf(h, home_lambda) * poisson_pmf(a, away_lambda)
            score_probs[(h, a)] = prob

            if h > a: home_win += prob
            elif h == a: draw += prob
            else: away_win += prob

            if h + a > 2.5: over += prob
            else: under += prob

            if h > 0 and a > 0: btts_yes += prob
            else: btts_no += prob

            if prob > max_prob:
                max_prob = prob
                best_score = (h, a)

    # Normalize
    total = home_win + draw + away_win
    home_win /= total; draw /= total; away_win /= total

    total_scores = sum(score_probs.values())
    sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)
    top_scores = [(f"{h}-{a}", p/total_scores) for (h,a),p in sorted_scores[:8]]

    return PoissonResult(
        home_win_prob=home_win, draw_prob=draw, away_win_prob=away_win,
        expected_home_goals=home_lambda, expected_away_goals=away_lambda,
        over_25_prob=over, under_25_prob=under,
        btts_yes_prob=btts_yes, btts_no_prob=btts_no,
        most_likely_score=best_score, score_probs=top_scores,
    )

def calc_kelly(prob, odds, bankroll=10000, fraction=0.25):
    """Kelly criterion calculation."""
    if odds <= 1:
        return {"fraction": 0, "amount": 0, "ev": 0, "recommended": False, "reason": "赔率无效"}
    b = odds - 1
    p = prob
    q = 1 - p
    kelly = (b * p - q) / b
    kelly = max(0, kelly * fraction)
    ev = p * b - q
    return {
        "kelly_fraction": kelly, "kelly_amount": bankroll * kelly,
        "expected_value": ev, "recommended": kelly > 0 and ev > 0,
        "reason": f"正EV {ev:+.1%}" if ev > 0 else f"负EV {ev:+.1%}"
    }

# ── 3. Context Adjustment ──────────────────────────────────────────

def adjust_for_context(match, poisson):
    """Apply contextual adjustments to raw Poisson probabilities."""
    home_mod = 1.0
    away_mod = 1.0
    draw_bonus = 0.0
    notes = []

    # Home/away form adjustments
    hr = match.get("home_recent", "")
    ar = match.get("away_recent", "")

    if "主场极其强势" in match.get("home_home_recent", ""):
        home_mod += 0.08
        notes.append("主场极其强势+8%主胜")
    if "客场明显弱" in match.get("away_away_recent", ""):
        away_mod -= 0.05
        notes.append("客场弱势-5%客胜")

    # Injury impact
    home_inj = match.get("injuries_home", [])
    away_inj = match.get("injuries_away", [])

    # Key defensive injuries
    home_def_inj = [i for i in home_inj if any(k in i for k in ["GK", "DF", "门将", "后卫"])]
    away_def_inj = [i for i in away_inj if any(k in i for k in ["GK", "DF", "门将", "后卫"])]
    home_mid_inj = [i for i in home_inj if any(k in i for k in ["MF", "中场", "核心"])]
    away_mid_inj = [i for i in away_inj if any(k in i for k in ["MF", "中场", "核心"])]

    if len(home_inj) >= 3:
        home_mod -= 0.08
        notes.append(f"主队{len(home_inj)}人伤缺-8%主胜")
    if len(away_inj) >= 3:
        away_mod -= 0.08
        notes.append(f"客队{len(away_inj)}人伤缺-8%客胜")
    if len(home_inj) >= 7:
        home_mod -= 0.12
        notes.append("主队大面积伤停再-12%")

    # First leg impact
    fl = match.get("first_leg", "")
    if "5:0" in fl and "首回合" in fl:
        # Big first leg lead -> rotation risk for leading team
        home_mod += 0.05  # trailing team needs to attack
        notes.append("首回合大比分落后方战意更强")
    if "2:2" in fl or "1:1" in fl:
        draw_bonus += 0.03
        notes.append("首回合平局+3%平局概率")

    # Competition type
    context = match.get("context_note", "")
    if "锁定冠军" in context or "基本锁定" in context:
        away_mod -= 0.06
        notes.append("客队基本锁定冠军，战意可能降温")
    if "最大热门" in context:
        away_mod += 0.06
        notes.append("客队为最大热门+6%")

    # 赔率走势
    if "机构态度高度一致" in match.get("odds_trend", ""):
        home_mod += 0.04
        notes.append("机构态度一致强化主胜+4%")
    if "诱导" in match.get("odds_trend", ""):
        home_mod -= 0.04
        notes.append("存在诱导主胜嫌疑-4%")

    # Apply modifications
    adjusted_h = poisson.home_win_prob * home_mod
    adjusted_a = poisson.away_win_prob * away_mod
    adjusted_d = poisson.draw_prob + draw_bonus

    # Renormalize
    total = adjusted_h + adjusted_d + adjusted_a
    adjusted_h /= total
    adjusted_d /= total
    adjusted_a /= total

    return {
        "home": adjusted_h, "draw": adjusted_d, "away": adjusted_a,
        "notes": notes,
        "home_mod": home_mod, "away_mod": away_mod, "draw_bonus": draw_bonus,
    }

# ── 4. Decision Engine ─────────────────────────────────────────────

def make_decision(match, raw_poisson, adj, odds, handicap_odds, h):
    """Generate final betting recommendation."""
    evidence = []
    warnings = []
    score = 0.0

    home = match["home_team"]
    away = match["away_team"]

    # 1X2
    best_1x2 = max([(f"{home}胜", adj["home"]), ("平局", adj["draw"]), (f"{away}胜", adj["away"])], key=lambda x: x[1])
    if best_1x2[1] >= 0.55:
        evidence.append(f"1X2倾向: {best_1x2[0]} {best_1x2[1]:.1%} (较强)")
        score += 2.5
    elif best_1x2[1] >= 0.45:
        evidence.append(f"1X2倾向: {best_1x2[0]} {best_1x2[1]:.1%} (中等)")
        score += 1.5
    else:
        evidence.append(f"1X2模糊: 最高{best_1x2[0]}仅{best_1x2[1]:.1%}")
        score += 0.5
        warnings.append("胜平负分布不集中")

    # Market direction check
    implied_h = 1 / odds.get("home_win", 2) / (1/odds.get("home_win",2) + 1/odds.get("draw",3) + 1/odds.get("away_win",3))
    implied_d = 1 / odds.get("draw", 3) / (1/odds.get("home_win",2) + 1/odds.get("draw",3) + 1/odds.get("away_win",3))
    implied_a = 1 / odds.get("away_win", 2) / (1/odds.get("home_win",2) + 1/odds.get("draw",3) + 1/odds.get("away_win",3))

    market_fav = max([("home", implied_h), ("draw", implied_d), ("away", implied_a)], key=lambda x: x[1])
    model_fav_side = "home" if best_1x2[0].startswith(home) else ("away" if best_1x2[0].startswith(away) else "draw")

    model_fav_prob = adj["home"] if model_fav_side == "home" else (adj["away"] if model_fav_side == "away" else adj["draw"])
    market_fav_prob = market_fav[1]

    deviation = abs(model_fav_prob - market_fav_prob)
    if deviation >= 0.20:
        warnings.append(f"模型与市场概率偏差{deviation:.0%}，不建议重仓")
        score -= 2.0
        evidence.append(f"模型-市场偏差: {deviation:.0%} (大)")
    elif deviation >= 0.12:
        evidence.append(f"模型-市场偏差: {deviation:.0%} (中)")
        score -= 0.5
    else:
        evidence.append(f"模型-市场方向一致: {market_fav[0]}方 ({deviation:.0%}偏差)")
        score += 1.0

    # Handicap analysis
    handicap_line = match["handicap"]
    if handicap_odds:
        # Calculate handicap cover probability based on score distribution
        # For handicap -1: 让胜=赢2+, 让平=赢1, 让负=平或输
        cover_prob = adj["home"] if handicap_line < 0 else adj["away"]
        fail_prob = adj["away"] if handicap_line < 0 else adj["home"]

        if handicap_line < 0:
            evidence.append(f"让球({handicap_line:+d}): 让胜~{cover_prob:.1%} 让负~{fail_prob:.1%}")
        else:
            evidence.append(f"让球({handicap_line:+d}): 主受让胜~{cover_prob:.1%} 让负~{fail_prob:.1%}")

        if fail_prob > 0.50:
            evidence.append(f"让负方向概率>{50}%，倾向让负")
            score += 1.0

    # Goals
    over_prob = raw_poisson.over_25_prob
    if over_prob >= 0.58:
        evidence.append(f"大2.5倾向明显 ({over_prob:.1%})")
        score += 1.0
    elif over_prob <= 0.42:
        evidence.append(f"小2.5倾向明显 ({1-over_prob:.1%})")
        score += 1.0
    else:
        evidence.append(f"大小球无明显倾向 (大{over_prob:.1%})")

    # Injury impact on goals
    total_inj = len(match.get("injuries_home", [])) + len(match.get("injuries_away", []))
    if total_inj >= 5:
        evidence.append(f"双方伤停{total_inj}人，可能影响进攻流畅度")

    # Data quality
    if match.get("data_warning"):
        warnings.append(match["data_warning"])
        score -= 1.0

    # Final decision
    no_bet = score < 1.0 or len(warnings) >= 4
    confidence = "high" if score >= 5 and len(warnings) <= 1 else ("medium" if score >= 3 else "low")
    parlay_allowed = score >= 3.5 and confidence != "low" and deviation < 0.18

    # Primary pick
    if no_bet:
        primary = "观望"
    else:
        if handicap_line < 0 and fail_prob > 0.50:
            primary = f"{home}让{handicap_line:+d}负"
        elif handicap_line > 0 and fail_prob > 0.50:
            primary = f"{away}让{-handicap_line:+d}负"
        else:
            primary = best_1x2[0]

    return {
        "primary_pick": primary,
        "confidence": confidence,
        "score": score,
        "no_bet": no_bet,
        "parlay_allowed": parlay_allowed,
        "evidence": evidence,
        "warnings": warnings,
        "market_implied": {"home": implied_h, "draw": implied_d, "away": implied_a},
        "model_deviation": deviation,
    }

# ── 5. Report Generation ───────────────────────────────────────────

def format_score_table(score_probs):
    lines = []
    for score, prob in score_probs[:6]:
        bar = "█" * int(prob * 80)
        lines.append(f"| {score} | {prob:.1%} | {bar} |")
    return "\n".join(lines)

def analyze_match(match):
    """Run full analysis on one match."""
    home = match["home_team"]
    away = match["away_team"]
    odds = match["no_handicap_odds"]
    handicap_odds = match["handicap_odds"]
    h = match["handicap"]

    # Estimate goals from available data
    # Use average J-League rates as defaults
    home_gf = match.get("home_gf_avg") or 1.4
    home_ga = match.get("home_ga_avg") or 1.1
    away_gf = match.get("away_gf_avg") or 1.2
    away_ga = match.get("away_ga_avg") or 1.3

    # Home advantage
    home_lambda = (home_gf + away_ga) / 2 * 1.10
    away_lambda = (away_gf + home_ga) / 2 * 0.90

    # Adjust for strong home/away splits
    if match.get("home_home_gf") and match.get("home_home_ga"):
        home_lambda = (match["home_home_gf"] + max(0.8, away_ga)) / 2 * 1.10
    if match.get("away_away_gf") and match.get("away_away_ga"):
        away_lambda = (match["away_away_gf"] + max(0.8, home_ga)) / 2 * 0.90

    # Special case: 川崎前锋 has massive injuries
    if "7人伤缺" in str(match.get("injuries_home", [])) or "中场组织几乎瘫痪" in str(match.get("injuries_home", [])):
        home_lambda *= 0.65  # severe reduction

    home_lambda = max(0.3, home_lambda)
    away_lambda = max(0.3, away_lambda)

    # Run Poisson
    poisson = calc_poisson(home_lambda, away_lambda)

    # Adjust for context
    adj = adjust_for_context(match, poisson)

    # Kelly
    kelly_results = []
    for bet_type, prob, odd_key in [
        (f"{home}胜", adj["home"], "home_win"),
        ("平局", adj["draw"], "draw"),
        (f"{away}胜", adj["away"], "away_win"),
    ]:
        k = calc_kelly(prob, odds[odd_key])
        k["bet_type"] = bet_type
        k["odds"] = odds[odd_key]
        k["probability"] = prob
        kelly_results.append(k)

    kelly_results.sort(key=lambda x: x["expected_value"], reverse=True)

    # Decision
    decision = make_decision(match, poisson, adj, odds, handicap_odds, h)

    return {
        "match": match,
        "poisson": poisson,
        "adjusted": adj,
        "kelly": kelly_results,
        "decision": decision,
    }

def render_report(analyses):
    """Render full analysis report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# 2026年6月6日 日职联6场竞彩深度分析报告")
    lines.append("")
    lines.append(f"> 生成时间: {now}  ")
    lines.append("> 数据来源: 500彩票网trade page + 深层分析页 + 竞彩官方  ")
    lines.append("> 模型: 泊松分布 + 凯利公式 + 比赛语境调整 + 让球/大小球判断  ")
    lines.append("> 免责声明: 仅供学习研究，不构成任何投注建议")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## 综合结论汇总")
    lines.append("")
    lines.append("| 场次 | 对阵 | 让球 | 胜平负 | 核心方向 | 信心 | EV | 大小球 | 是否组合 |")
    lines.append("|------|------|------|--------|----------|------|----|--------|----------|")

    for a in analyses:
        m = a["match"]
        d = a["decision"]
        k = a["kelly"]
        p = a["poisson"]
        top_kelly = k[0] if k else {"expected_value": 0}
        ev_str = f"{top_kelly['expected_value']:+.1%}"
        goals = "大2.5" if p.over_25_prob >= 0.55 else ("小2.5" if p.over_25_prob <= 0.45 else "中性")
        parlay = "可" if d["parlay_allowed"] else "不建议"
        adj = a["adjusted"]
        result_1x2 = f"{adj['home']:.0%}/{adj['draw']:.0%}/{adj['away']:.0%}"

        lines.append(
            f"| {m['match_num']} | {m['home_team']} vs {m['away_team']} | "
            f"{m['handicap']:+d} | {result_1x2} | **{d['primary_pick']}** | "
            f"{d['confidence']} | {ev_str} | {goals} | {parlay} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Individual match reports
    for a in analyses:
        m = a["match"]
        p = a["poisson"]
        adj = a["adjusted"]
        k = a["kelly"]
        d = a["decision"]

        lines.append(f"## {m['match_num']} — {m['home_team']} vs {m['away_team']}")
        lines.append("")
        lines.append(f"**赛事**: {m['league']} | **开赛**: {m['match_date']} {m['match_time']} | **让球**: {m['handicap']:+d}")
        lines.append("")

        # 竞彩赔率
        lines.append("### 竞彩赔率与市场数据")
        lines.append("")
        odds = m["no_handicap_odds"]
        h_odds = m["handicap_odds"]
        lines.append("| 玩法 | 主胜/让胜 | 平/让平 | 客胜/让负 |")
        lines.append("|------|----------|---------|----------|")
        lines.append(f"| **胜平负** | {odds['home_win']} | {odds['draw']} | {odds['away_win']} |")
        lines.append(f"| **让球({m['handicap']:+d})** | {h_odds['home_win']} | {h_odds['draw']} | {h_odds['away_win']} |")

        if m.get("europe_avg"):
            e = m["europe_avg"]
            lines.append(f"| **百家欧赔均值** | {e['home_win']} | {e['draw']} | {e['away_win']} |")

        if m.get("asian_handicap"):
            lines.append(f"| **亚盘** | {m['asian_handicap']} | - | - |")

        lines.append("")

        # 赔率走势
        if m.get("odds_trend"):
            lines.append(f"**赔率走势解读**: {m['odds_trend']}")
            lines.append("")

        # 欧赔公司明细
        if m.get("europe_companies"):
            lines.append("| 公司 | 主胜 | 平 | 客胜 |")
            lines.append("|------|------|----|------|")
            for c in m["europe_companies"]:
                lines.append(f"| {c['name']} | {c['home']} | {c['draw']} | {c['away']} |")
            lines.append("")

        # 交锋
        if m.get("h2h_summary"):
            lines.append(f"**交锋记录**: {m['h2h_summary']}")
            lines.append("")

        if m.get("h2h_records"):
            lines.append("| 日期 | 对阵 | 比分 | 盘口 | 结果 |")
            lines.append("|------|------|------|------|------|")
            for r in m["h2h_records"]:
                lines.append(f"| {r['date']} | {r['match']} | {r['score']} | {r['handicap']} | {r['result']} |")
            lines.append("")

        # 近期战绩
        if m.get("home_recent"):
            lines.append(f"**主队近期**: {m['home_recent']}")
            lines.append("")
        if m.get("home_home_recent"):
            lines.append(f"**主队主场**: {m['home_home_recent']}")
            lines.append("")
        if m.get("away_recent"):
            lines.append(f"**客队近期**: {m['away_recent']}")
            lines.append("")
        if m.get("away_away_recent"):
            lines.append(f"**客队客场**: {m['away_away_recent']}")
            lines.append("")

        # 伤停
        if m.get("injuries_home"):
            lines.append(f"**主队伤停**: {', '.join(m['injuries_home'])}")
            lines.append("")
        if m.get("injuries_away"):
            lines.append(f"**客队伤停**: {', '.join(m['injuries_away'])}")
            lines.append("")

        # 首回合
        if m.get("first_leg"):
            lines.append(f"**首回合**: {m['first_leg']}")
            lines.append("")

        # 泊松模型
        lines.append("### 泊松模型预测")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 主队预期进球 (xG) | {p.expected_home_goals:.2f} |")
        lines.append(f"| 客队预期进球 (xG) | {p.expected_away_goals:.2f} |")
        lines.append(f"| 模型主胜概率 | {adj['home']:.1%} |")
        lines.append(f"| 模型平局概率 | {adj['draw']:.1%} |")
        lines.append(f"| 模型客胜概率 | {adj['away']:.1%} |")
        lines.append(f"| 大2.5球概率 | {p.over_25_prob:.1%} |")
        lines.append(f"| 双方进球概率 | {p.btts_yes_prob:.1%} |")
        lines.append(f"| 最可能比分 | {p.most_likely_score[0]}-{p.most_likely_score[1]} |")

        if adj["notes"]:
            lines.append("")
            lines.append(f"**语境调整**: {'; '.join(adj['notes'])}")

        lines.append("")
        lines.append("#### 比分概率分布")
        lines.append("")
        lines.append("| 比分 | 概率 | 分布 |")
        lines.append("|------|------|------|")
        lines.append(format_score_table(p.score_probs))
        lines.append("")

        # 凯利分析
        lines.append("### 凯利公式分析")
        lines.append("")
        lines.append("| 方向 | 赔率 | 模型概率 | EV | 凯利比例 | 建议 |")
        lines.append("|------|------|----------|----|----------|------|")
        for kr in k:
            rec = "✅推荐" if kr["recommended"] else "❌不推荐"
            lines.append(
                f"| {kr['bet_type']} | {kr['odds']:.2f} | {kr['probability']:.1%} | "
                f"{kr['expected_value']:+.1%} | {kr['kelly_fraction']:.2%} | {rec} |"
            )
        lines.append("")

        # 集成决策
        lines.append("### 集成决策与证据评分")
        lines.append("")
        lines.append(f"**核心方向**: **{d['primary_pick']}**  ")
        lines.append(f"**信心等级**: {d['confidence']} | **综合评分**: {d['score']:.1f} | **是否组合**: {'允许' if d['parlay_allowed'] else '不建议'}")
        lines.append("")

        lines.append("**证据项**:")
        for e in d["evidence"]:
            lines.append(f"- {e}")
        lines.append("")

        if d["warnings"]:
            lines.append("**风险提示**:")
            for w in d["warnings"]:
                lines.append(f"- ⚠️ {w}")
            lines.append("")

        # 市场隐含
        imp = d["market_implied"]
        lines.append(f"**市场隐含概率**: 主{imp['home']:.1%} / 平{imp['draw']:.1%} / 客{imp['away']:.1%} | 偏差: {d['model_deviation']:.1%}")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Parlay suggestions
    lines.append("## 组合思路")
    lines.append("")

    # Sort by confidence
    high_conf = [a for a in analyses if a["decision"]["confidence"] == "high"]
    med_conf = [a for a in analyses if a["decision"]["confidence"] == "medium"]
    low_conf = [a for a in analyses if a["decision"]["confidence"] == "low"]

    lines.append(f"**高信心场次 ({len(high_conf)}场)**:")
    for a in high_conf:
        m = a["match"]
        d = a["decision"]
        lines.append(f"- {m['match_num']} {m['home_team']} vs {m['away_team']}: **{d['primary_pick']}** (评分{d['score']:.1f})")
    if not high_conf:
        lines.append("- 无")

    lines.append(f"\n**中等信心场次 ({len(med_conf)}场)**:")
    for a in med_conf:
        m = a["match"]
        d = a["decision"]
        lines.append(f"- {m['match_num']} {m['home_team']} vs {m['away_team']}: **{d['primary_pick']}** (评分{d['score']:.1f})")
    if not med_conf:
        lines.append("- 无")

    lines.append(f"\n**低信心/观望场次 ({len(low_conf)}场)**:")
    for a in low_conf:
        m = a["match"]
        d = a["decision"]
        lines.append(f"- {m['match_num']} {m['home_team']} vs {m['away_team']}: {d['primary_pick']} (评分{d['score']:.1f})")
    if not low_conf:
        lines.append("- 无")

    # Suggested parlay
    parlayable = [a for a in analyses if a["decision"]["parlay_allowed"]]
    if len(parlayable) >= 2:
        lines.append(f"\n**稳健2场组合建议**:")
        top2 = sorted(parlayable, key=lambda x: x["decision"]["score"], reverse=True)[:2]
        for a in top2:
            m = a["match"]
            lines.append(f"- {m['match_num']} {m['match_team_summary'] if 'match_team_summary' in m else m['home_team']+' vs '+m['away_team']}: {a['decision']['primary_pick']}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 今日比赛关键要点")
    lines.append("")
    lines.append("1. **周六201 鹿岛 vs 神户**: 鹿岛主场极强(10场9胜1平)但首回合0-5落后,神户基本锁定冠军;鹿岛防线多人缺阵(门将+2后卫),大比分可能性偏低")
    lines.append("2. **周六202 町田 vs 名古屋**: 町田8场不败但平局多,名古屋近期丢球多但伤停主要在中前场;赔率诱导主胜需警惕")
    lines.append("3. **周六203 浦和 vs 冈山**: 主胜为6场最低赔率之一,500数据异常需以竞彩为准;浦和主场历来占优")
    lines.append("4. **周六204 横滨 vs 清水**: 横滨主场交锋碾压(5战4胜),但首回合仅1-1;盘口变化不大,需临场确认")
    lines.append("5. **周六205 柏太阳神 vs 京都**: 今天最被看好的主胜(1.79),京都头号射手缺阵+后防减员;让球对称结构暗示1球小胜")
    lines.append("6. **周六206 川崎 vs 广岛**: 今天最确定的方向——广岛4连胜+川崎7人伤缺;广岛客胜1.89为今日最低客赔")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由AI分析模型自动生成，仅供参考。比赛结果受多种因素影响，请理性对待。*")

    return "\n".join(lines)

# ── 6. Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 80)
    print("2026-06-06 日职联6场竞彩分析")
    print("=" * 80)

    analyses = []
    for match in MATCHES:
        print(f"\n分析中: {match['match_num']} {match['home_team']} vs {match['away_team']}...")
        result = analyze_match(match)
        analyses.append(result)

    print("\n生成报告...")
    report = render_report(analyses)

    # Save report
    report_path = Path("/Users/jamesm/Desktop/football-analyst-skill/2026-06-06日职联6场分析报告.md")
    report_path.write_text(report, encoding="utf-8")

    # Also save detailed JSON
    json_path = Path("/Users/jamesm/Desktop/football-analyst-skill/2026-06-06日职联6场分析数据.json")
    json_output = []
    for a in analyses:
        m = a["match"]
        p = a["poisson"]
        adj = a["adjusted"]
        d = a["decision"]
        json_output.append({
            "match_num": m["match_num"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "handicap": m["handicap"],
            "odds": m["no_handicap_odds"],
            "handicap_odds": m["handicap_odds"],
            "poisson": {
                "home_lambda": p.expected_home_goals,
                "away_lambda": p.expected_away_goals,
                "home_win_raw": p.home_win_prob,
                "draw_raw": p.draw_prob,
                "away_win_raw": p.away_win_prob,
                "over_25": p.over_25_prob,
                "btts": p.btts_yes_prob,
                "most_likely_score": f"{p.most_likely_score[0]}-{p.most_likely_score[1]}",
            },
            "adjusted": {"home": adj["home"], "draw": adj["draw"], "away": adj["away"], "notes": adj["notes"]},
            "decision": d,
            "kelly_top": a["kelly"][0] if a["kelly"] else None,
        })
    json_path.write_text(json.dumps(json_output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'=' * 80}")
    print(f"✅ 报告已保存到: {report_path}")
    print(f"✅ 数据已保存到: {json_path}")
    print(f"{'=' * 80}")
