from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


SOURCE_DIR = Path("/Users/jamesm/Downloads/未命名文件夹")
OUT_DIR = Path("data/worldcup_20260621")
TEXT_DIR = OUT_DIR / "pdf_text"

MATCH_ALIASES = {
    "荷兰VS瑞典": ["荷兰VS瑞典", "Netherlands - Sweden"],
    "德国VS科特迪瓦": ["德国VS科特迪瓦", "Germany - Ivory Coast"],
    "厄瓜多尔VS库拉索": ["厄瓜多尔VS库拉索", "Ecuador - Cura", "Ecuador - Curac"],
    "突尼斯VS日本": ["突尼斯VS日本", "Tunisia - Japan"],
}


def detect_match(path: Path) -> str:
    for match, aliases in MATCH_ALIASES.items():
        if any(alias in path.name for alias in aliases):
            return match
    return "主表/其他"


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        value = value.replace("\xa0", " ").strip()
        return value or None
    return value


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    return {"page_count": len(pages), "text": text, "chars": len(text)}


def read_xls(path: Path) -> dict:
    xls = pd.ExcelFile(path, engine="xlrd")
    sheets = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
        rows = []
        key_rows = []
        for index, row in df.iterrows():
            cleaned = [clean_value(value) for value in row.tolist()]
            if not any(value is not None for value in cleaned):
                continue
            rows.append(cleaned)
            joined = " ".join(str(value) for value in cleaned if value is not None)
            if any(key in joined for key in ["平均", "最高", "最低", "初盘", "即时", "主流", "凯利"]):
                key_rows.append({"source_row": int(index), "text": joined[:2400]})
        sheets[sheet_name] = {
            "shape": list(df.shape),
            "rows": rows,
            "key_rows": key_rows,
        }
    return sheets


def classify_xls(name: str) -> str:
    if "欧洲数据" in name:
        return "europe_1x2"
    if "让球指数" in name:
        return "handicap_result"
    if "大小" in name:
        return "total_goals"
    if "亚盘" in name:
        return "asian_handicap"
    return "unknown"


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "source_dir": str(SOURCE_DIR),
        "pdfs": {},
        "xls": {},
        "errors": {},
        "matches": {},
    }

    for pdf in sorted(SOURCE_DIR.glob("*.pdf")):
        try:
            result = extract_pdf(pdf)
            text_path = TEXT_DIR / f"{pdf.name}.txt"
            text_path.write_text(result.pop("text"), encoding="utf-8")
            match = detect_match(pdf)
            summary["pdfs"][pdf.name] = {
                "match": match,
                "text_path": str(text_path),
                **result,
                "sample": normalize(text_path.read_text(encoding="utf-8"))[:1800],
            }
            summary["matches"].setdefault(match, {"pdfs": [], "xls": []})["pdfs"].append(pdf.name)
        except Exception as exc:
            summary["errors"][pdf.name] = repr(exc)

    for xls in sorted(SOURCE_DIR.glob("*.xls")):
        try:
            match = detect_match(xls)
            summary["xls"][xls.name] = {
                "match": match,
                "kind": classify_xls(xls.name),
                "real_format": "OLE2 Compound Document / BIFF .xls",
                "sheets": read_xls(xls),
            }
            summary["matches"].setdefault(match, {"pdfs": [], "xls": []})["xls"].append(xls.name)
        except Exception as exc:
            summary["errors"][xls.name] = repr(exc)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "source_extract_summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "pdfs": len(summary["pdfs"]),
        "xls": len(summary["xls"]),
        "errors": summary["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
