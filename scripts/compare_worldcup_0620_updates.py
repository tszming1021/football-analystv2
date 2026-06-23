from __future__ import annotations

import difflib
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


SOURCE_DIR = Path("/Users/jamesm/Downloads/未命名文件夹")
BASE_DIR = Path("data/worldcup_20260621")
BASE_SUMMARY = BASE_DIR / "source_extract_summary.json"
OUT_DIR = BASE_DIR / "update_1847"
OUT_TEXT_DIR = OUT_DIR / "pdf_text"
OUT_JSON = BASE_DIR / "update_diff_1847.json"


def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        value = value.replace("\xa0", " ").strip()
        return value or None
    return value


def stable(value):
    if isinstance(value, float):
        return round(value, 10)
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def extract_pdf(path: Path) -> tuple[int, str]:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return len(pages), "\n\n".join(pages)


def read_xls(path: Path) -> dict:
    workbook = pd.ExcelFile(path, engine="xlrd")
    sheets = {}
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
        rows = []
        for _, row in frame.iterrows():
            cleaned = [stable(clean(value)) for value in row.tolist()]
            if any(value is not None for value in cleaned):
                rows.append(cleaned)
        sheets[sheet_name] = {"shape": list(frame.shape), "rows": rows}
    return sheets


def row_label(row: list) -> str:
    return " | ".join(str(value) for value in row[:4] if value is not None)[:160]


def compare_rows(old_rows: list, new_rows: list) -> dict:
    changes = []
    max_rows = max(len(old_rows), len(new_rows))
    for row_index in range(max_rows):
        old = old_rows[row_index] if row_index < len(old_rows) else []
        new = new_rows[row_index] if row_index < len(new_rows) else []
        max_cols = max(len(old), len(new))
        cells = []
        for col_index in range(max_cols):
            before = stable(old[col_index]) if col_index < len(old) else None
            after = stable(new[col_index]) if col_index < len(new) else None
            if before != after:
                cells.append({"column": col_index + 1, "before": before, "after": after})
        if cells:
            changes.append({
                "row": row_index + 1,
                "label_before": row_label(old),
                "label_after": row_label(new),
                "cells": cells,
            })
    return {
        "old_nonempty_rows": len(old_rows),
        "new_nonempty_rows": len(new_rows),
        "changed_rows": len(changes),
        "changes": changes,
    }


def main() -> None:
    baseline = json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))
    OUT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_dir": str(SOURCE_DIR),
        "baseline": str(BASE_SUMMARY),
        "pdfs": {},
        "xls": {},
        "errors": {},
    }

    for name, old_meta in baseline["pdfs"].items():
        path = SOURCE_DIR / name
        if not path.exists():
            result["pdfs"][name] = {"status": "missing_in_latest_folder"}
            continue
        try:
            page_count, current_text = extract_pdf(path)
            current_text_path = OUT_TEXT_DIR / f"{name}.txt"
            current_text_path.write_text(current_text, encoding="utf-8")
            old_text_path = Path(old_meta["text_path"])
            old_text = old_text_path.read_text(encoding="utf-8") if old_text_path.exists() else ""
            old_lines = normalized_lines(old_text)
            new_lines = normalized_lines(current_text)
            diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=1))
            additions = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
            removals = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
            result["pdfs"][name] = {
                "status": "changed" if old_lines != new_lines else "unchanged",
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
                "sha256": sha256(path),
                "old_pages": old_meta.get("page_count"),
                "new_pages": page_count,
                "old_chars": len(old_text),
                "new_chars": len(current_text),
                "added_line_count": len(additions),
                "removed_line_count": len(removals),
                "added_lines": additions[:300],
                "removed_lines": removals[:300],
                "diff_truncated": len(additions) > 300 or len(removals) > 300,
                "current_text_path": str(current_text_path),
            }
        except Exception as exc:
            result["errors"][name] = repr(exc)

    for name, old_meta in baseline["xls"].items():
        path = SOURCE_DIR / name
        if not path.exists():
            result["xls"][name] = {"status": "missing_in_latest_folder"}
            continue
        try:
            current = read_xls(path)
            sheet_results = {}
            sheet_names = sorted(set(old_meta["sheets"]) | set(current))
            for sheet_name in sheet_names:
                old_sheet = old_meta["sheets"].get(sheet_name, {"shape": [], "rows": []})
                new_sheet = current.get(sheet_name, {"shape": [], "rows": []})
                comparison = compare_rows(old_sheet["rows"], new_sheet["rows"])
                comparison["old_shape"] = old_sheet.get("shape")
                comparison["new_shape"] = new_sheet.get("shape")
                sheet_results[sheet_name] = comparison
            changed_rows = sum(sheet["changed_rows"] for sheet in sheet_results.values())
            result["xls"][name] = {
                "status": "changed" if changed_rows else "unchanged",
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
                "sha256": sha256(path),
                "changed_rows": changed_rows,
                "sheets": sheet_results,
            }
        except Exception as exc:
            result["errors"][name] = repr(exc)

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_JSON),
        "pdf_changed": sum(item.get("status") == "changed" for item in result["pdfs"].values()),
        "pdf_missing": sum(item.get("status") == "missing_in_latest_folder" for item in result["pdfs"].values()),
        "xls_changed": sum(item.get("status") == "changed" for item in result["xls"].values()),
        "errors": result["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
