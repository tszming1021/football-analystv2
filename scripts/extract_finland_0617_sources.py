from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


SOURCE_DIR = Path("/Users/jamesm/Downloads/芬超")
OUT_DIR = Path("data/finland_20260617")
TEXT_DIR = OUT_DIR / "pdf_text"


MATCH_ALIASES = {
    "赫尔辛基VS国际图尔库": ["赫尔辛基VS国际图尔库", "赫尔辛基vs国际图尔库"],
    "埃尔维斯VS查路": ["埃尔维斯VS查路", "埃尔维斯vs查路", "坦佩雷山猫", "雅罗"],
    "TPS土尔库VS库普斯": ["TPS土尔库VS库普斯", "TPS土尔库vs库普斯"],
    "格尼斯坦VS拉赫蒂": ["格尼斯坦VS拉赫蒂", "格尼斯坦vs拉赫蒂", "赫尔辛基火花"],
    "塞那乔恩VS瓦萨": ["塞那乔恩VS瓦萨", "塞伊奈", "瓦萨"],
}


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_match(path: Path) -> str | None:
    name = path.name
    for match, aliases in MATCH_ALIASES.items():
        if any(alias in name for alias in aliases):
            return match
    return None


def read_xls_preview(path: Path) -> dict:
    xls = pd.ExcelFile(path, engine="xlrd")
    sheets = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None, engine="xlrd")
        rows = []
        for _, row in df.head(20).iterrows():
            vals = [None if pd.isna(v) else str(v) for v in row.tolist()[:18]]
            if any(v not in (None, "") for v in vals):
                rows.append(vals)
        sheets[sheet] = {
            "shape": list(df.shape),
            "preview": rows,
        }
    return sheets


def find_average_lines(sheets: dict) -> list[str]:
    lines: list[str] = []
    for sheet, info in sheets.items():
        for row in info["preview"]:
            joined = " ".join(v for v in row if v)
            if "平均值" in joined or "平均" in joined:
                lines.append(f"{sheet}: {joined}")
    return lines


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict = {"pdfs": {}, "xls": {}, "matches": {}}

    for pdf in sorted(SOURCE_DIR.glob("*.pdf")):
        text = extract_pdf_text(pdf)
        out = TEXT_DIR / f"{pdf.name}.txt"
        out.write_text(text, encoding="utf-8")
        match = detect_match(pdf) or "主表/其他"
        summary["pdfs"][pdf.name] = {
            "match": match,
            "chars": len(text),
            "text_path": str(out),
            "sample": normalize_text(text)[:1200],
        }
        summary["matches"].setdefault(match, {"pdfs": [], "xls": []})
        summary["matches"][match]["pdfs"].append(pdf.name)

    for xls_path in sorted(SOURCE_DIR.glob("*.xls")):
        match = detect_match(xls_path) or "其他"
        sheets = read_xls_preview(xls_path)
        summary["xls"][xls_path.name] = {
            "match": match,
            "sheets": sheets,
            "average_lines": find_average_lines(sheets),
        }
        summary["matches"].setdefault(match, {"pdfs": [], "xls": []})
        summary["matches"][match]["xls"].append(xls_path.name)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "source_extract_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"out": str(OUT_DIR / "source_extract_summary.json"), "pdfs": len(summary["pdfs"]), "xls": len(summary["xls"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
