"""Regenerate docs/notes/presentation_tables.md from the stored scores. No API cost.

Every table in the presentation deck comes from cpas_scores.json, so a re-judged run or
a corrected gold can be reflected by re-running this rather than editing numbers by hand
— which is how figures and prose drift apart.

Run: conda run -n xai python scripts/make_presentation_tables.py
"""
from __future__ import annotations
import json, statistics as st, collections, glob
from pathlib import Path
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "experiments" / "results"
MD = ROOT / "docs" / "notes" / "presentation_tables.md"
ROWS = [("llama-3.1-8b (API)", "openai-meta-llama-llama-3.1-8b-instruct"),
        ("llama3.1:8b (LOCAL)", "ollama-llama3.1-8b"),
        ("qwen3-32b", "openai-qwen-qwen3-32b"),
        ("llama-3.3-70b", "openai-meta-llama-llama-3.3-70b-instruct"),
        ("qwen3-235b", "openai-qwen-qwen3-235b-a22b-2507"),
        ("deepseek-v4.1-flash", "openai-deepseek-deepseek-v4.1-flash-1017"),
        ("qwen3.8-27b", "openai-qwen-qwen3.8-27b"),
        ("gpt-5.5 (ceiling)", "openai-openai-gpt-5.5")]
P = ["operator", "data_scientist", "regulator"]
W = {"D": .30, "C": .25, "A": .25, "R": .20}
load = lambda t: json.load(open(R / t / "cpas_scores.json"))["rows"]
raw = lambda rs: st.mean(r["cpas"] + 2 * r["H"] for r in rs)


def by_scenario(rows, tier):
    a = {}
    for r in rows:
        if r["tier"] == tier:
            a.setdefault(r["scenario"], []).append(r["cpas"])
    return {k: st.mean(v) for k, v in a.items()}


FLOOR, CEIL = "ollama-llama3.1-8b", "openai-openai-gpt-5.5"
DIMS = ["D", "C", "A", "R"]
rawrow = lambda r: sum(W[d] * r[d] for d in DIMS)
tierC = lambda rs: [r for r in rs if r["tier"] == "C"]
pers = lambda rs, p: [r for r in rs if r["persona"] == p]


def tbl(header, lines):
    return ["| " + " | ".join(header) + " |",
            "|" + "---|" * len(header)] + lines


def main() -> None:
    print("regenerating presentation tables from cpas_scores.json ...")
    data = {lbl: load(tag) for lbl, tag in ROWS}
    out = []

    # ---- T1 capability sweep
    out += ["## T1 — Capability sweep: CPAS by tier", ""]
    rows = []
    for lbl, _ in ROWS:
        rs = data[lbl]; C = tierC(rs)
        a, c = by_scenario(rs, "A"), by_scenario(rs, "C")
        k = sorted(set(a) & set(c))
        _, pv = wilcoxon([a[x] for x in k], [c[x] for x in k])
        means = {t: st.mean(r["cpas"] for r in rs if r["tier"] == t) for t in "ABC"}
        rows.append("| " + " | ".join([
            lbl, f'{means["A"]:.2f}', f'{means["B"]:.2f}', f'**{means["C"]:.2f}**',
            f"{raw(C):.2f}", f'{sum(r["H"] for r in C)/len(C):.0%}',
            f"{sum(rawrow(r) >= 3.0 for r in C)/len(C):.0%}",
            f'{st.mean(c[x]-a[x] for x in k):+.2f}',
            "<.0001" if pv < 1e-4 else f"{pv:.4f}"]) + " |")
        print(f'  {lbl:22} tierC={means["C"]:.2f} raw={raw(C):.2f} '
              f'H={sum(r["H"] for r in C)/len(C):.0%}')
    out += tbl(["synthesizer", "A", "B", "C", "raw C", "H rate", "pass", "C−A Δ", "p"], rows) + [""]

    # ---- T2 per-dimension
    out += ["## T2 — Per-dimension, tier C only", ""]
    rows = ["| " + " | ".join([lbl] + [f'{st.mean(r[d] for r in tierC(data[lbl])):.1f}' for d in DIMS]
            + [f'{sum(r["H"] for r in tierC(data[lbl]))/len(tierC(data[lbl])):.0%}']) + " |"
            for lbl, _ in ROWS]
    out += tbl(["synthesizer", "D", "C", "A", "R", "H%"], rows) + [""]

    # ---- T3 per persona, floor vs ceiling
    out += ["## T3 — Per persona: floor vs ceiling (tier C)", ""]
    name = {FLOOR: "8B", CEIL: "gpt-5.5"}
    rows = []
    for pn in P:
        for i, tag in enumerate((FLOOR, CEIL)):
            rs = pers(tierC(load(tag)), pn)
            rows.append("| " + " | ".join([
                pn if i == 0 else "", name[tag]]
                + [f"{st.mean(r[d] for r in rs):.1f}" for d in DIMS]
                + [f'{sum(r["H"] for r in rs)/len(rs):.0%}', f"{st.mean(rawrow(r) for r in rs):.2f}",
                   f'**{st.mean(r["cpas"] for r in rs):.2f}**']) + " |")
    out += tbl(["persona", "", "D", "C", "A", "R", "H%", "raw", "CPAS"], rows) + [""]

    # ---- T4 tier progression by persona
    out += ["## T4 — Tier A→B→C by persona (is XAI alone enough?)", ""]
    rows = []
    for pn in P:
        for i, tag in enumerate((FLOOR, CEIL)):
            rs = load(tag)
            m = {t: st.mean(r["cpas"] for r in rs if r["tier"] == t and r["persona"] == pn)
                 for t in "ABC"}
            rows.append("| " + " | ".join([
                pn if i == 0 else "", name[tag], f'{m["A"]:.2f}', f'{m["B"]:.2f}', f'{m["C"]:.2f}',
                f'{m["B"]-m["A"]:+.2f}', f'{m["C"]-m["B"]:+.2f}']) + " |")
    out += tbl(["persona", "model", "A", "B", "C", "A→B", "B→C"], rows) + [""]

    # ---- T5 consequence class
    out += ["## T5 — CPAS by consequence class (tier C)", ""]
    classes = sorted({r["consequence_class"] for r in data[ROWS[0][0]]} - {"n/a"})
    rows = []
    for cls in classes:
        cells = []
        for lbl, _ in ROWS:
            v = [r["cpas"] for r in tierC(data[lbl]) if r["consequence_class"] == cls]
            cells.append(f"{st.mean(v):.2f}" if v else "-")
        rows.append("| " + " | ".join([cls] + cells) + " |")
    out += tbl(["consequence class"] + [l for l, _ in ROWS], rows) + [""]

    # ---- T6 lambda sensitivity
    out += ["## T6 — λ sensitivity (tier C mean CPAS)", ""]
    rows = []
    for lbl, _ in ROWS:
        C = tierC(data[lbl])
        rows.append("| " + " | ".join([lbl] + [
            f'{st.mean(rawrow(r) - lam * r["H"] for r in C):.2f}' for lam in (0, 1, 2, 3)]) + " |")
    out += tbl(["synthesizer", "λ=0", "λ=1", "λ=2", "λ=3"], rows) + [""]

    # ---- splice T1..T6 into the doc, preserving the hand-written sections
    md = MD.read_text()
    start, end = md.index("## T1 "), md.index("## T6b ")
    MD.write_text(md[:start] + "\n".join(out) + md[end:])
    print(f"\n  wrote T1-T6 ({len(ROWS)} models) -> {MD.relative_to(ROOT)}")
    print("  (T0, T6b, T7-T11 are hand-written and were left untouched)")


if __name__ == "__main__":
    main()
