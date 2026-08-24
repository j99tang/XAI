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
ROWS = [("llama-3.1-8b (API)", "openai-meta-llama-llama-3.1-8b-instruct"),
        ("llama3.1:8b (LOCAL)", "ollama-llama3.1-8b"),
        ("qwen3-32b", "openai-qwen-qwen3-32b"),
        ("llama-3.3-70b", "openai-meta-llama-llama-3.3-70b-instruct"),
        ("qwen3-235b", "openai-qwen-qwen3-235b-a22b-2507"),
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


def main() -> None:
    print("regenerating presentation tables from cpas_scores.json …")
    for lbl, tag in ROWS:
        rs = load(tag)
        C = [r for r in rs if r["tier"] == "C"]
        a, c = by_scenario(rs, "A"), by_scenario(rs, "C")
        k = sorted(set(a) & set(c))
        _, p = wilcoxon([a[x] for x in k], [c[x] for x in k])
        print(f"  {lbl:22} tierC={st.mean(r['cpas'] for r in C):.2f} "
              f"raw={raw(C):.2f} H={sum(r['H'] for r in C)/len(C):.0%} "
              f"Δ={st.mean(c[x]-a[x] for x in k):+.2f} p={p:.5f}")
    print(f"\n  full tables live in docs/notes/presentation_tables.md")
    print("  (T0, T8-T11 are hand-written prose sections; T1-T7 are the computed ones)")


if __name__ == "__main__":
    main()
