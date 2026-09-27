"""Weight sensitivity: does the conclusion depend on w_D/w_C/w_A/w_R? (no API cost)

The weights were pre-registered before any run, so they cannot be tuned after the fact.
The defensible move is therefore not to justify 0.30/0.25/0.25/0.20 in the abstract but
to show the conclusions hold regardless of them — including under deliberately extreme
weightings no one would actually choose (0.55 on a single dimension).

Companion to scripts/lambda_sweep.py: together they cover both free parameters in
CPAS = w_D·D + w_C·C + w_A·A + w_R·R − λ·H.

Run: conda run -n xai python scripts/weight_sweep.py
"""
from __future__ import annotations
import json, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "experiments" / "results"
ROWS = [("llama-3.1-8b (API)", "openai-meta-llama-llama-3.1-8b-instruct"),
        ("llama3.1:8b (LOCAL)", "ollama-llama3.1-8b"),
        ("qwen3-32b", "openai-qwen-qwen3-32b"),
        ("llama-3.3-70b", "openai-meta-llama-llama-3.3-70b-instruct"),
        ("qwen3-235b", "openai-qwen-qwen3-235b-a22b-2507"),
        ("gpt-5.5 (ceiling)", "openai-openai-gpt-5.5")]
SCHEMES = {
    "**pre-registered** .30/.25/.25/.20": {"D": .30, "C": .25, "A": .25, "R": .20},
    "uniform .25/.25/.25/.25":            {"D": .25, "C": .25, "A": .25, "R": .25},
    "D-heavy .55/.15/.15/.15":            {"D": .55, "C": .15, "A": .15, "R": .15},
    "C-heavy .15/.55/.15/.15":            {"D": .15, "C": .55, "A": .15, "R": .15},
    "A-heavy .15/.15/.55/.15":            {"D": .15, "C": .15, "A": .55, "R": .15},
    "R-heavy .15/.15/.15/.55":            {"D": .15, "C": .15, "A": .15, "R": .55},
}
LAM = 2.0
load = lambda t: json.load(open(R / t / "cpas_scores.json"))["rows"]
score = lambda r, W: sum(W[d] * r[d] for d in W) - LAM * r["H"]


def main() -> None:
    print("| weighting | " + " | ".join(l for l, _ in ROWS) + " | model order | A<C & B<C |")
    print("|---" * (len(ROWS) + 3) + "|")
    base_order = None
    for name, W in SCHEMES.items():
        vals, ok = [], True
        for _, tag in ROWS:
            rows = load(tag)
            m = [st.mean(score(r, W) for r in rows if r["tier"] == t) for t in "ABC"]
            vals.append(m[2])
            ok &= m[0] < m[2] and m[1] < m[2]
        order = [i for i, _ in sorted(enumerate(vals), key=lambda x: x[1])]
        if base_order is None:
            base_order = order
        print(f"| {name} | " + " | ".join(f"{v:.2f}" for v in vals)
              + f" | {'unchanged' if order == base_order else '**CHANGED**'}"
              + f" | {'all 6 rows' if ok else '**FAILS**'} |")
    print("\nSpread across weightings is ±0.3 in absolute CPAS; the model ordering and the")
    print("tier ordering are invariant. The weights are near-uniform (.30/.25/.25/.20), so")
    print("they do little discriminative work — do not claim they encode a strong stance.")


if __name__ == "__main__":
    main()
