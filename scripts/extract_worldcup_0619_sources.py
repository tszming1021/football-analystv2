from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

SOURCE_DIR = Path("/Users/jamesm/Downloads/未命名文件夹 3")
OUT_DIR = Path("data/worldcup_20260619")
TEXT_DIR = OUT_DIR / "pdf_text"

MATCH_ALIASES = {
    "捷克VS南非": ["捷克VS南非", "捷克vs南非"],
    "瑞士VS波黑": ["瑞士VS波黑", "瑞士vs波黑"],
    "加拿大VS卡塔尔": ["加拿大VS卡塔尔", "加拿大vs卡塔尔"],
    "墨西哥VS韩国": ["墨西哥VS韩国", "墨西哥vs韩国"],
}


def detect_match(path: Path) -> str:
    name = path.name
    for match, aliases in MATCH_ALIASES.items():
        if any(alias in name for alias in aliases):
            return match
    return "主表/其他"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_xls(path: Path) -> dict:
    xls = pd.ExcelFile(path, engine="xlrd")
    result = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None, engine="xlrd")
        preview = []
        average_lines = []
        for i, row in df.iterrows():
            vals = ["" if pd.isna(v) else str(v) for v in row.tolist()]
            joined = " ".join(vals)
            if i < 25 and any(v.strip() for v in vals):
                preview.append(vals[:24])
            if any(key in joined for key in ["平均值", "最高值", "最低值"]):
                average_lines.append({"row": int(i), "text": joined[:1600]})
        result[sheet] = {
            "shape": list(df.shape),
            "preview": preview,
            "average_lines": average_lines,
        }
    return result


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"pdfs": {}, "xls": {}, "matches": {}}
    for pdf in sorted(SOURCE_DIR.glob("*.pdf")):
        text = extract_pdf(pdf)
        out = TEXT_DIR / f"{pdf.name}.txt"
        out.write_text(text, encoding="utf-8")
        match = detect_match(pdf)
        summary["pdfs"][pdf.name] = {
            "match": match,
            "chars": len(text),
            "text_path": str(out),
            "sample": normalize(text)[:1400],
        }
        summary["matches"].setdefault(match, {"pdfs": [], "xls": []})["pdfs"].append(pdf.name)

    for xls in sorted(SOURCE_DIR.glob("*.xls")):
        match = detect_match(xls)
        data = read_xls(xls)
        summary["xls"][xls.name] = {"match": match, "sheets": data}
        summary["matches"].setdefault(match, {"pdfs": [], "xls": []})["xls"].append(xls.name)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "source_extract_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "pdfs": len(summary["pdfs"]), "xls": len(summary["xls"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
