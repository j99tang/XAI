"""How much of the result is λ? (D30 follow-up, no API cost.)

λ=2 is pre-registered but explicitly "severe-but-non-erasing, tunable" — and it does
enormous work: it turned row 0's regulator raw 2.96 into CPAS 1.49, erasing the entire
tier-C gain. "Why 2?" has no principled answer beyond "40% of raw max", so the defensible
move is to show how conclusions behave across plausible values rather than assert one.

Recomputes CPAS from the STORED raw D/C/A/R/H — no re-judging, nothing re-run.

Run: conda run -n xai python scripts/lambda_sweep.py [<run_tag> ...]
"""
from __future__ import annotations
import json, statistics as st, sys
from pathlib import Path
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
W = {"D": 0.30, "C": 0.25, "A": 0.25, "R": 0.20}
LAMBDAS = [0.0, 1.0, 2.0, 3.0]
PERSONAS = ["operator", "data_scientist", "regulator"]


def cpas(r, lam):
    return sum(W[d] * r[d] for d in W) - lam * r["H"]


def by_scenario(rows, tier, lam):
    acc = {}
    for r in rows:
        if r["tier"] == tier:
            acc.setdefault(r["scenario"], []).append(cpas(r, lam))
    return {k: st.mean(v) for k, v in acc.items()}


def sweep(tag):
    rows = json.load(open(ROOT / f"experiments/results/{tag}/cpas_scores.json"))["rows"]
    print(f"\n{'='*72}\n{tag}\n{'='*72}")
    print(f"{'λ':>5}  " + "".join(f"{p[:9]:>11}" for p in PERSONAS) +
          f"{'C-A Δ':>9}{'p':>10}{'C>B?':>7}")
    for lam in LAMBDAS:
        cells = []
        for p in PERSONAS:
            v = [cpas(r, lam) for r in rows if r["persona"] == p and r["tier"] == "C"]
            cells.append(f"{st.mean(v):>11.2f}")
        a, c, b = (by_scenario(rows, t, lam) for t in ("A", "C", "B"))
        k = sorted(set(a) & set(c))
        d = st.mean(c[x] - a[x] for x in k)
        _, pv = wilcoxon([a[x] for x in k], [c[x] for x in k])
        cb = st.mean(c[x] - b[x] for x in k)
        flag = "***" if pv < .001 else "**" if pv < .01 else "*" if pv < .05 else "n.s."
        star = "yes" if cb > 0 else "NO"
        print(f"{lam:>5.1f}  " + "".join(cells) + f"{d:>9.2f}{pv:>8.4f}{flag:>4}{star:>7}")
    print("  λ=0 is the raw weighted score (no hallucination penalty) — the ceiling on what")
    print("  context delivers. The gap between λ=0 and λ=2 IS the reliability cost.")


for tag in (sys.argv[1:] or ["ollama-llama3.1-8b", "openai-openai-gpt-5.5"]):
    sweep(tag)
