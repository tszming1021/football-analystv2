from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/jamesm/Desktop/未命名文件夹 2")
OUT_DIR = Path("data/worldcup_four_20260617")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        value = value.replace("\xa0", " ").strip()
        return value or None
    return value


def read_workbook(path: Path):
    sheets = {}
    xls = pd.ExcelFile(path, engine="xlrd")
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
        rows = []
        for row in df.values.tolist():
            cleaned = [clean_value(v) for v in row]
            if any(v is not None for v in cleaned):
                rows.append(cleaned)
        sheets[sheet_name] = rows
    return sheets


def flatten(rows):
    return [str(v) for row in rows for v in row if v is not None]


def first_numbers(text, limit=12):
    nums = re.findall(r"(?<!\d)(?:\d+\.\d+|\d+)(?!\d)", text)
    return [float(n) for n in nums[:limit]]


def summarize_sheet(filename: str, sheets: dict):
    flat_text = " ".join(flatten([row for rows in sheets.values() for row in rows]))
    lower = filename.lower()
    summary = {
        "file": filename,
        "sheet_names": list(sheets),
        "shape_preview": {
            name: {
                "rows": len(rows),
                "max_cols": max((len(r) for r in rows), default=0),
                "first_rows": rows[:8],
            }
            for name, rows in sheets.items()
        },
        "numbers_preview": first_numbers(flat_text, 30),
    }
    if "欧洲数据" in filename:
        summary["kind"] = "europe_market"
    elif "让球指数" in filename:
        summary["kind"] = "handicap_result_index"
    elif "大小" in filename:
        summary["kind"] = "total_goals_index"
    elif "亚盘" in filename:
        summary["kind"] = "asian_handicap_index"
    else:
        summary["kind"] = "unknown"
    return summary


def main():
    result = {"source_dir": str(ROOT), "files": {}, "errors": {}}
    for path in sorted(ROOT.glob("*.xls")):
        try:
            sheets = read_workbook(path)
            result["files"][path.name] = summarize_sheet(path.name, sheets)
        except Exception as exc:
            result["errors"][path.name] = repr(exc)
    out = OUT_DIR / "xls_extraction_summary.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(result["files"]), "errors": result["errors"], "out": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
