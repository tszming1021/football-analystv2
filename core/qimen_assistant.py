#!/usr/bin/env python3
"""奇门遁甲辅助分析层。

该模块用于给足球赛前报告增加一个低权重、可回测的玄学辅助视角。
它不直接修改泊松概率、凯利值或投注金额，只输出风险提示和辅助倾向。

说明：
- 当前版本是轻量化结构化辅助，不是完整传统排盘引擎。
- 规则参考奇门中“主客”“八门”“八神”“九星”“伏吟/反吟”等基本象意。
- 后续若接入完整排盘库，可以保持 QimenAssistantResult 输出结构不变。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

DOORS = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]
STARS = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心"]
GODS = ["值符", "腾蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]

DOOR_WEIGHTS = {
    "开门": 2,
    "休门": 1,
    "生门": 2,
    "景门": 0,
    "杜门": 0,
    "伤门": -2,
    "惊门": -2,
    "死门": -3,
}

GOD_WEIGHTS = {
    "值符": 2,
    "太阴": 1,
    "六合": 2,
    "九地": 1,
    "九天": 1,
    "腾蛇": -2,
    "白虎": -2,
    "玄武": -2,
}

STAR_WEIGHTS = {
    "天任": 1,
    "天冲": 1,
    "天辅": 1,
    "天心": 1,
    "天英": 0,
    "天蓬": -1,
    "天芮": -2,
    "天柱": -1,
}


@dataclass
class QimenAssistantResult:
    match_datetime: str
    hour_branch: str
    day_stem: str
    hour_stem: str
    dun_type: str
    ju_number: int
    home_symbol: Dict[str, Any]
    away_symbol: Dict[str, Any]
    draw_symbol: Dict[str, Any]
    qimen_bias: str
    qimen_result_prediction: str
    predicted_score: str
    image_summary: str
    volatility: str
    confidence: str
    qimen_score: Dict[str, float]
    notes: List[str]
    risk_flags: List[str]
    disclaimer: str = "奇门结果仅作低权重辅助和赛前风险提示，不直接改变数据模型概率或投注金额。"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QimenAssistant:
    """轻量奇门辅助分析器。"""

    def analyze(
        self,
        match_datetime: datetime,
        home_team: str,
        away_team: str,
        poisson: Optional[Any] = None,
        odds: Optional[Dict[str, float]] = None,
    ) -> QimenAssistantResult:
        hour_branch = self._hour_branch(match_datetime.hour)
        day_index = self._day_index(match_datetime)
        day_stem = STEMS[day_index % 10]
        hour_stem = STEMS[(day_index * 2 + self._branch_index(hour_branch)) % 10]
        dun_type = "阳遁" if self._is_yang_dun(match_datetime) else "阴遁"
        ju_number = (day_index + self._branch_index(hour_branch)) % 9 + 1

        home_symbol = self._symbol_for_side(day_index, match_datetime.hour, side_offset=0, team_name=home_team)
        away_symbol = self._symbol_for_side(day_index, match_datetime.hour, side_offset=3, team_name=away_team)
        draw_symbol = self._draw_symbol(day_index, match_datetime.hour)

        scores = {
            "home": self._symbol_score(home_symbol),
            "away": self._symbol_score(away_symbol),
            "draw": self._symbol_score(draw_symbol),
        }
        self._apply_contextual_adjustments(scores, poisson, odds, home_symbol, away_symbol, draw_symbol)

        qimen_bias = self._bias(scores)
        volatility = self._volatility(home_symbol, away_symbol, draw_symbol, scores)
        predicted_score = self._predicted_score(qimen_bias, scores, home_symbol, away_symbol, draw_symbol, poisson)
        result_prediction = {
            "home": "主胜",
            "draw": "平局",
            "away": "客胜",
            "no_clear_bias": "胜平负不明，偏谨慎观望",
        }[qimen_bias]
        image_summary = self._image_summary(home_symbol, away_symbol, draw_symbol, qimen_bias, volatility)
        confidence = self._confidence(scores, volatility)
        notes = self._notes(home_symbol, away_symbol, draw_symbol, scores, qimen_bias)
        risk_flags = self._risk_flags(home_symbol, away_symbol, draw_symbol, volatility, qimen_bias, poisson)

        return QimenAssistantResult(
            match_datetime=match_datetime.isoformat(timespec="minutes"),
            hour_branch=hour_branch,
            day_stem=day_stem,
            hour_stem=hour_stem,
            dun_type=dun_type,
            ju_number=ju_number,
            home_symbol=home_symbol,
            away_symbol=away_symbol,
            draw_symbol=draw_symbol,
            qimen_bias=qimen_bias,
            qimen_result_prediction=result_prediction,
            predicted_score=predicted_score,
            image_summary=image_summary,
            volatility=volatility,
            confidence=confidence,
            qimen_score=scores,
            notes=notes,
            risk_flags=risk_flags,
        )

    @staticmethod
    def _day_index(value: datetime) -> int:
        # 用稳定参考日生成干支序，足够用于辅助层的一致性回测。
        ref = datetime(1984, 2, 2)
        return (value.date() - ref.date()).days % 60

    @staticmethod
    def _hour_branch(hour: int) -> str:
        return BRANCHES[((hour + 1) // 2) % 12]

    @staticmethod
    def _branch_index(branch: str) -> int:
        return BRANCHES.index(branch)

    @staticmethod
    def _is_yang_dun(value: datetime) -> bool:
        # 简化为冬至到夏至附近用阳遁，夏至到冬至附近用阴遁。
        month_day = (value.month, value.day)
        return month_day >= (12, 22) or month_day < (6, 21)

    def _symbol_for_side(self, day_index: int, hour: int, side_offset: int, team_name: str) -> Dict[str, Any]:
        base = day_index + hour + side_offset
        door = DOORS[base % len(DOORS)]
        star = STARS[(base + day_index) % len(STARS)]
        god = GODS[(base + hour) % len(GODS)]
        role = "主" if side_offset == 0 else "客"
        return {
            "team": team_name,
            "role": role,
            "door": door,
            "star": star,
            "god": god,
            "meaning": self._meaning(door, star, god),
        }

    def _draw_symbol(self, day_index: int, hour: int) -> Dict[str, Any]:
        base = day_index + hour + 5
        door = DOORS[base % len(DOORS)]
        star = STARS[(base + 2) % len(STARS)]
        god = GODS[(base + 4) % len(GODS)]
        return {
            "team": "平局",
            "role": "和",
            "door": door,
            "star": star,
            "god": god,
            "meaning": self._meaning(door, star, god),
        }

    @staticmethod
    def _meaning(door: str, star: str, god: str) -> str:
        pieces = []
        if door in {"开门", "生门", "休门"}:
            pieces.append("门象偏顺")
        elif door in {"伤门", "惊门", "死门"}:
            pieces.append("门象偏凶")
        else:
            pieces.append("门象中性")
        if god in {"六合", "太阴", "九地"}:
            pieces.append("利配合/稳守")
        elif god in {"白虎", "腾蛇", "玄武"}:
            pieces.append("有冲突/虚实/混乱象")
        if star in {"天冲", "天辅", "天心", "天任"}:
            pieces.append("星象有助")
        elif star in {"天芮", "天蓬", "天柱"}:
            pieces.append("星象有阻")
        return "，".join(pieces)

    @staticmethod
    def _symbol_score(symbol: Dict[str, Any]) -> float:
        return (
            DOOR_WEIGHTS.get(symbol.get("door"), 0)
            + GOD_WEIGHTS.get(symbol.get("god"), 0)
            + STAR_WEIGHTS.get(symbol.get("star"), 0)
        )

    @staticmethod
    def _apply_contextual_adjustments(
        scores: Dict[str, float],
        poisson: Optional[Any],
        odds: Optional[Dict[str, float]],
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
    ):
        if poisson:
            if abs(poisson.home_win_prob - poisson.away_win_prob) <= 0.04:
                scores["draw"] += 0.5
            if poisson.draw_prob >= 0.27:
                scores["draw"] += 0.5
        if odds:
            if odds.get("home") and odds.get("away") and abs(odds["home"] - odds["away"]) <= 0.18:
                scores["draw"] += 0.3
        if draw_symbol.get("god") == "六合":
            scores["draw"] += 0.8
        if home_symbol.get("door") == away_symbol.get("door"):
            scores["draw"] += 0.4

    @staticmethod
    def _bias(scores: Dict[str, float]) -> str:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if ordered[0][1] - ordered[1][1] < 1.0:
            return "no_clear_bias"
        return {
            "home": "home",
            "draw": "draw",
            "away": "away",
        }[ordered[0][0]]

    @staticmethod
    def _volatility(
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
        scores: Dict[str, float],
    ) -> str:
        bad_gods = {"白虎", "腾蛇", "玄武"}
        bad_doors = {"伤门", "惊门", "死门"}
        risk = 0
        for symbol in [home_symbol, away_symbol, draw_symbol]:
            if symbol.get("god") in bad_gods:
                risk += 1
            if symbol.get("door") in bad_doors:
                risk += 1
        if max(scores.values()) - min(scores.values()) <= 1.2:
            risk += 1
        if risk >= 4:
            return "high"
        if risk >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _confidence(scores: Dict[str, float], volatility: str) -> str:
        ordered = sorted(scores.values(), reverse=True)
        edge = ordered[0] - ordered[1]
        if volatility == "high" or edge < 1.0:
            return "low"
        if edge >= 2.5 and volatility == "low":
            return "medium"
        return "low"

    @staticmethod
    def _predicted_score(
        qimen_bias: str,
        scores: Dict[str, float],
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
        poisson: Optional[Any],
    ) -> str:
        if poisson:
            base_home, base_away = poisson.most_likely_score
        else:
            base_home, base_away = 1, 1

        home_attack = home_symbol.get("door") in {"开门", "生门", "景门"} or home_symbol.get("god") == "九天"
        away_attack = away_symbol.get("door") in {"开门", "生门", "景门"} or away_symbol.get("god") == "九天"
        draw_sticky = draw_symbol.get("god") in {"六合", "九地", "太阴"} or draw_symbol.get("door") in {"休门", "杜门"}
        chaos = any(
            symbol.get("god") in {"白虎", "腾蛇", "玄武"} or symbol.get("door") in {"伤门", "惊门"}
            for symbol in [home_symbol, away_symbol, draw_symbol]
        )

        if qimen_bias == "draw":
            if chaos and (home_attack or away_attack):
                return "2-2"
            return "1-1" if max(base_home, base_away) <= 2 else f"{min(base_home, base_away)}-{min(base_home, base_away)}"

        if qimen_bias == "home":
            margin = 2 if scores["home"] - max(scores["draw"], scores["away"]) >= 3 and home_attack else 1
            away_goal = 1 if away_attack or chaos else 0
            home_goal = max(1 + margin, away_goal + margin)
            if draw_sticky:
                home_goal = max(home_goal, 2)
                away_goal = max(away_goal, 1)
            return f"{home_goal}-{away_goal}"

        if qimen_bias == "away":
            margin = 2 if scores["away"] - max(scores["draw"], scores["home"]) >= 3 and away_attack else 1
            home_goal = 1 if home_attack or chaos else 0
            away_goal = max(1 + margin, home_goal + margin)
            if draw_sticky:
                away_goal = max(away_goal, 2)
                home_goal = max(home_goal, 1)
            return f"{home_goal}-{away_goal}"

        if abs(base_home - base_away) <= 1:
            return f"{base_home}-{base_away}"
        return "1-1"

    @staticmethod
    def _image_summary(
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
        qimen_bias: str,
        volatility: str,
    ) -> str:
        subject = {
            "home": "主队得势",
            "away": "客队得势",
            "draw": "和局象较重",
            "no_clear_bias": "三方拉扯，局像不清",
        }[qimen_bias]
        volatility_text = {
            "low": "局面较稳",
            "medium": "局中有扰动",
            "high": "变数偏大",
        }[volatility]
        return (
            f"{subject}，{volatility_text}。"
            f"主宫见{home_symbol['door']}{home_symbol['god']}，"
            f"客宫见{away_symbol['door']}{away_symbol['god']}，"
            f"平局象见{draw_symbol['door']}{draw_symbol['god']}。"
        )

    @staticmethod
    def _notes(
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
        scores: Dict[str, float],
        qimen_bias: str,
    ) -> List[str]:
        label = {
            "home": "主队",
            "away": "客队",
            "draw": "平局",
            "no_clear_bias": "无明显偏向",
        }[qimen_bias]
        return [
            f"主队宫: {home_symbol['door']} / {home_symbol['star']} / {home_symbol['god']}，{home_symbol['meaning']}",
            f"客队宫: {away_symbol['door']} / {away_symbol['star']} / {away_symbol['god']}，{away_symbol['meaning']}",
            f"平局象: {draw_symbol['door']} / {draw_symbol['star']} / {draw_symbol['god']}，{draw_symbol['meaning']}",
            f"奇门辅助偏向: {label}；评分 主{scores['home']:.1f} / 平{scores['draw']:.1f} / 客{scores['away']:.1f}",
        ]

    @staticmethod
    def _risk_flags(
        home_symbol: Dict[str, Any],
        away_symbol: Dict[str, Any],
        draw_symbol: Dict[str, Any],
        volatility: str,
        qimen_bias: str,
        poisson: Optional[Any],
    ) -> List[str]:
        flags = []
        if volatility == "high":
            flags.append("奇门波动偏高，提示爆冷/红牌/临场变化风险，串关需谨慎")
        if any(symbol.get("god") == "白虎" for symbol in [home_symbol, away_symbol, draw_symbol]):
            flags.append("见白虎象，留意伤停、身体对抗、牌面风险")
        if any(symbol.get("god") == "腾蛇" for symbol in [home_symbol, away_symbol, draw_symbol]):
            flags.append("见腾蛇象，留意盘口诱导、信息不透明或临场反复")
        if qimen_bias == "draw":
            flags.append("奇门有和局象，可额外关注让球平/平局保护")
        if poisson and qimen_bias in {"home", "away"}:
            model_side = "home" if poisson.home_win_prob > poisson.away_win_prob else "away"
            if model_side != qimen_bias:
                flags.append("奇门偏向与数据模型第一倾向不一致，建议降低主观加仓")
        if not flags:
            flags.append("奇门未提示额外高风险，仅作辅助确认")
        return flags


__all__ = ["QimenAssistant", "QimenAssistantResult"]
