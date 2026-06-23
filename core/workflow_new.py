#!/usr/bin/env python3
"""
足球大数据精算分析智能体 - 新工作流程架构 (V5.0)
重构版本：分离数据获取、数学建模、大模型分析三大模块
"""

import os
import sys
import json
import re
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# 1. 输入层 + 实体识别层 (保持不变)
# ============================================================================

@dataclass
class ParsedMatch:
    """解析后的比赛信息"""
    home_team_raw: str          # 原始输入的主队名
    away_team_raw: str          # 原始输入的客队名
    home_team_en: str           # 转换后的英文主队名
    away_team_en: str           # 转换后的英文客队名
    league_hint: Optional[str]  # 联赛提示（如果有）
    input_str: str              # 原始输入字符串


class TeamNameTranslator:
    """球队名称翻译器 - 支持多语言转换"""

    # 球队名映射表
    NAME_MAP = {
        # 西班牙球队
        '巴萨': 'Barcelona', '巴薩': 'Barcelona', '巴塞罗那': 'Barcelona', '巴塞隆拿': 'Barcelona',
        '皇馬': 'Real Madrid', '皇马': 'Real Madrid', '皇家馬德里': 'Real Madrid',
        '皇家马德里': 'Real Madrid',
        '馬競': 'Atletico Madrid', '马竞': 'Atletico Madrid', '馬德里競技': 'Atletico Madrid',
        '马德里竞技': 'Atletico Madrid',
        '塞維利亞': 'Sevilla', '塞维利亚': 'Sevilla',
        '瓦倫西亞': 'Valencia', '瓦伦西亚': 'Valencia',
        '比利亞雷亞爾': 'Villarreal', '比利亚雷亚尔': 'Villarreal', '黃潛': 'Villarreal', '黄潜': 'Villarreal',
        '皇蘇': 'Real Sociedad', '皇社': 'Real Sociedad', '皇家社會': 'Real Sociedad', '皇家社会': 'Real Sociedad',
        '畢爾包': 'Athletic Club', '毕尔巴鄂': 'Athletic Club', '畢爾巴鄂競技': 'Athletic Club', '毕尔巴鄂竞技': 'Athletic Club',

        # 英格兰球队
        '曼城': 'Manchester City', '曼市': 'Manchester City',
        '曼聯': 'Manchester United', '曼联': 'Manchester United',
        '利物浦': 'Liverpool',
        '切爾西': 'Chelsea', '切尔西': 'Chelsea', '車路士': 'Chelsea',
        '阿仙奴': 'Arsenal', '阿森納': 'Arsenal', '阿森纳': 'Arsenal',
        '熱刺': 'Tottenham', '热刺': 'Tottenham',
        '紐卡素': 'Newcastle', '纽卡斯尔': 'Newcastle',
        '阿士東維拉': 'Aston Villa', '阿斯顿维拉': 'Aston Villa',

        # 德国球队
        '拜仁': 'Bayern Munich', '拜仁慕尼黑': 'Bayern Munich',
        '多蒙特': 'Borussia Dortmund', '多特蒙德': 'Borussia Dortmund',
        '利華古遜': 'Bayer Leverkusen', '勒沃库森': 'Bayer Leverkusen',
        'RB萊比錫': 'RB Leipzig', '莱比锡': 'RB Leipzig',

        # 意大利球队
        '祖雲達斯': 'Juventus', '尤文图斯': 'Juventus',
        '國米': 'Inter', '国米': 'Inter', '國際米蘭': 'Inter', '国际米兰': 'Inter',
        'A米': 'AC Milan', 'AC米蘭': 'AC Milan', 'AC米兰': 'AC Milan',
        '拿坡里': 'Napoli', '那不勒斯': 'Napoli',
        '羅馬': 'Roma', '罗马': 'Roma',
        '拉素': 'Lazio', '拉齐奥': 'Lazio',
        '亞特蘭大': 'Atalanta', '亚特兰大': 'Atalanta',

        # 法国球队
        '巴黎': 'Paris Saint Germain', 'PSG': 'Paris Saint Germain',
        '巴黎聖日耳門': 'Paris Saint Germain', '巴黎圣日耳曼': 'Paris Saint Germain',
        '摩納哥': 'Monaco', '摩纳哥': 'Monaco',
        '馬賽': 'Marseille', '马赛': 'Marseille',

        # 国家队
        '斯洛文尼亚': 'Slovenia', '斯洛文尼亞': 'Slovenia',
        '塞浦路斯': 'Cyprus',
        '瑞典': 'Sweden', '希腊': 'Greece', '希臘': 'Greece',
        '西班牙': 'Spain', '伊拉克': 'Iraq',
        '法国': 'France', '法國': 'France',
        '科特迪瓦': 'Ivory Coast', '象牙海岸': 'Ivory Coast',
        '墨西哥': 'Mexico', '塞尔维亚': 'Serbia', '塞爾維亞': 'Serbia',
    }

    @classmethod
    def translate(cls, name: str) -> str:
        """将球队名翻译为标准英文名"""
        # 直接匹配
        if name in cls.NAME_MAP:
            return cls.NAME_MAP[name]

        # 不区分大小写匹配
        for key, value in cls.NAME_MAP.items():
            if key.lower() == name.lower():
                return value

        # 无法匹配则返回原名
        return name

    @classmethod
    def get_all_names(cls, english_name: str) -> List[str]:
        """获取一个英文名的所有变体"""
        variants = [english_name]
        for zh_name, en_name in cls.NAME_MAP.items():
            if en_name.lower() == english_name.lower():
                variants.append(zh_name)
        return list(set(variants))


class InputParser:
    """输入解析器 - 处理用户输入并转换为结构化数据"""

    @staticmethod
    def parse_match_input(match_str: str) -> ParsedMatch:
        """
        解析用户输入的比赛字符串
        支持格式: "巴薩 vs 馬競", "Barcelona vs Atletico Madrid", "曼城 - 利物浦"
        """
        separators = [' vs ', ' VS ', ' - ', ' – ', ' 对 ', ' 對 ', ' vs. ', ' VS. ']

        # 尝试各种分隔符
        for sep in separators:
            if sep in match_str:
                parts = match_str.split(sep)
                if len(parts) == 2:
                    home_raw = parts[0].strip()
                    away_raw = parts[1].strip()

                    # 转换为英文名
                    home_en = TeamNameTranslator.translate(home_raw)
                    away_en = TeamNameTranslator.translate(away_raw)

                    return ParsedMatch(
                        home_team_raw=home_raw,
                        away_team_raw=away_raw,
                        home_team_en=home_en,
                        away_team_en=away_en,
                        league_hint=None,
                        input_str=match_str
                    )

        # 如果无法解析，尝试空格分割
        parts = match_str.split()
        if len(parts) >= 4:
            mid = len(parts) // 2
            home_raw = ' '.join(parts[:mid]).strip()
            away_raw = ' '.join(parts[mid:]).strip()

            home_en = TeamNameTranslator.translate(home_raw)
            away_en = TeamNameTranslator.translate(away_raw)

            return ParsedMatch(
                home_team_raw=home_raw,
                away_team_raw=away_raw,
                home_team_en=home_en,
                away_team_en=away_en,
                league_hint=None,
                input_str=match_str
            )

        raise ValueError(f"无法解析比赛输入: {match_str}")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'ParsedMatch',
    'TeamNameTranslator',
    'InputParser',
]
