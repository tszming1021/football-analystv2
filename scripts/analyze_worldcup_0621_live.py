from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

from core.worldcup_trained_model import WorldCupTrainedModel
from scripts.analyze_worldcup_0620_strict_1847 import analyze_match
from scripts.analyze_worldcup_0621_strict import MATCHES as BASE_MATCHES


MARKET_PATH = Path("data/worldcup_20260622/update_live/latest_market.json")
WEATHER_PATH = Path("data/worldcup_20260622/weather/weather_audit.json")
OUT_PATH = Path("data/worldcup_20260622/model_analysis_live.json")
TOTAL_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7")


def ordered_prices(mapping: dict[str, float]) -> tuple[float, float, float]:
    return mapping["3"], mapping["1"], mapping["0"]


def prepare_matches() -> list[dict]:
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))["matches"]
    weather = json.loads(WEATHER_PATH.read_text(encoding="utf-8"))
    matches = copy.deepcopy(BASE_MATCHES)
    weather_by_code = {
        "周日037": ("atlanta", "Atlanta", "Mercedes-Benz Stadium可闭合顶棚"),
        "周日038": ("los_angeles", "Los Angeles", "SoFi Stadium顶棚覆盖"),
        "周日039": ("miami", "Miami", "Hard Rock Stadium为开放式场地"),
        "周日040": ("vancouver", "Vancouver", "BC Place可闭合顶棚"),
    }
    for match in matches:
        code = match["code"]
        latest = market[code]
        current = latest["current"]
        deep = latest["deep_market"]
        one_x_two = current["one_x_two"]
        if one_x_two:
            match["market_1x2"] = ordered_prices(one_x_two)
            match["market_1x2_source"] = "500竞彩官方实时"
        else:
            match["market_1x2"] = tuple(deep["ouzhi"]["current"])
            match["market_1x2_source"] = "500百家实时均值（竞彩三向未开售）"
        match["handicap_3way"] = ordered_prices(current["handicap_three_way"])
        match["total_exact"] = tuple(current["total_exact"][key] for key in TOTAL_KEYS)
        match["score_prices"] = {
            label: price
            for label, price in current["scores"].items()
            if len(label.split("-")) == 2 and all(part.isdigit() for part in label.split("-"))
        }
        match["asian_line"] = float(deep["yazhi"]["current"][1])
        match["market_total_line"] = float(deep["daxiao"]["current"][1])

        weather_key, city, venue_note = weather_by_code[code]
        latest_weather = weather[weather_key]
        match["weather"] = (
            f"{city}开球时段，{latest_weather['temperature_c']}C、湿度{latest_weather['humidity_pct']}%、"
            f"降水{latest_weather['precipitation_probability_pct']}%、天气代码{latest_weather['weather_code']}、"
            f"风速{latest_weather['wind_kmh']}km/h；{venue_note}"
        )

    by_code = {match["code"]: match for match in matches}
    by_code["周日037"]["absence_note"] = (
        "API-Football实时伤停/首发仍为0行；Reuters报道亚马尔与尼科·威廉斯缺席，"
        "按权威媒体确认层处理，等待官方首发"
    )
    by_code["周日037"]["lambda_context"] = (0.02, -0.08)

    by_code["周日038"]["absence_note"] = (
        "API-Football实时伤停/首发仍为0行；ESPN报道多库确定缺席；"
        "德巴斯特腿后肌伤仍缺球队官方二次确认"
    )
    by_code["周日038"]["lambda_context"] = (-0.08, 0.06)

    by_code["周日039"]["absence_note"] = (
        "API-Football实时伤停/首发仍为0行；未发现更新来源推翻德阿拉斯凯塔、阿劳霍肌肉伤的不确定状态"
    )
    by_code["周日039"]["lambda_context"] = (-0.09, -0.04)

    by_code["周日040"]["absence_note"] = (
        "API-Football实时伤停/首发仍为0行；未发现新增实质缺席；最新预览仍围绕萨拉赫正常出战展开"
    )
    return matches


def main() -> None:
    trained = WorldCupTrainedModel()
    matches = prepare_matches()
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_version": "worldcup-strict-20260621-live-v2",
        "market_source": str(MARKET_PATH),
        "notes": [
            "相对15:39基准，仅更新实时市场、最新天气与新增权威媒体伤停消息。",
            "真实赛前xG/xGA仍不可用，继续使用收缩后的proxy xG与离线世界杯模型。",
            "API-Football实时injuries和lineups仍为0行；媒体伤停保留来源等级。",
        ],
        "matches": [analyze_match(match, trained) for match in matches],
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "summary": [
            {
                "code": item["identity"]["code"],
                "result": item["final"]["result"],
                "handicap": item["final"]["handicap_home_settlement"],
                "mean": item["means"]["decision_final"],
                "scores": [score["score"] for score in item["final"]["scorelines"][:5]],
                "consistency": item["consistency"]["status"],
                "warnings": item["consistency"]["warnings"],
            }
            for item in output["matches"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
