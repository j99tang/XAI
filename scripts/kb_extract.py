"""Reference-text extractor for KB authoring (plan §2.9 supporting tool).

Pulls plain text (optionally only pages matching a keyword) from the PDFs in
references/source_library/ so KB documents are paraphrased from the ACTUAL source
text, never from model memory. This is the reproducible provenance trail: re-run
it to see exactly what a KB claim was grounded in.

Examples:
  conda run -n xai python scripts/kb_extract.py "references/source_library/standards/NERC-CIP-008-6.pdf" --grep "72 hours"
  conda run -n xai python scripts/kb_extract.py "references/data explanation paper.pdf" --pages 5-6
"""
from __future__ import annotations

import argparse
import re
import sys

import fitz  # pymupdf


def extract(path: str, grep: str | None, pages: str | None, context: int) -> str:
    doc = fitz.open(path)
    page_ids = range(len(doc))
    if pages:
        a, _, b = pages.partition("-")
        page_ids = range(int(a) - 1, int(b or a))
    out = []
    for i in page_ids:
        text = doc[i].get_text()
        if grep is None:
            out.append(f"--- page {i + 1} ---\n{text}")
            continue
        for m in re.finditer(re.escape(grep), text, re.IGNORECASE):
            s, e = max(0, m.start() - context), min(len(text), m.end() + context)
            out.append(f"--- page {i + 1} (match '{grep}') ---\n"
                       + re.sub(r"[ \t]+", " ", text[s:e]))
    return "\n\n".join(out) if out else f"(no match for '{grep}' in {path})"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--grep", help="only show windows around this phrase")
    ap.add_argument("--pages", help="page range, e.g. 5-6 (1-based)")
    ap.add_argument("--context", type=int, default=400)
    a = ap.parse_args()
    try:
        print(extract(a.pdf, a.grep, a.pages, a.context))
    except FileNotFoundError:
        sys.exit(f"not found: {a.pdf}")
