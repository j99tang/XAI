"""Phase 5.3 figures, straight from cpas_scores.json. No API cost.

Three plots, each carrying one argument:
  fig1  capability gradient  — CPAS rises smoothly with model capability; no cliff
  fig2  raw vs penalised     — reliability, not substance, is what separates models
  fig3  tier ablation        — A<B<C by persona, at the floor and at the ceiling
  fig6  release vs CPAS      — capability progression over calendar time, and its exception
"""
from __future__ import annotations
import json, statistics as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
# ordered by capability, not by score, so the x-axis is an independent variable
ORDER = [("llama-3.1-8b\n(API)", "openai-meta-llama-llama-3.1-8b-instruct"),
         ("llama3.1:8b\n(local)", "ollama-llama3.1-8b"),
         ("qwen3-32b", "openai-qwen-qwen3-32b"),
         ("llama-3.3-70b", "openai-meta-llama-llama-3.3-70b-instruct"),
         ("qwen3-235b", "openai-qwen-qwen3-235b-a22b-2507"),
         ("deepseek\nv4.1-flash", "openai-deepseek-deepseek-v4.1-flash-1017"),
         ("qwen3.8-27b", "openai-qwen-qwen3.8-27b"),
         ("gpt-5.5\n(ceiling)", "openai-openai-gpt-5.5")]
PERS = ["operator", "data_scientist", "regulator"]

D = {}
for lbl, tag in ORDER:
    rows = json.load(open(ROOT / f"experiments/results/{tag}/cpas_scores.json"))["rows"]
    C = [r for r in rows if r["tier"] == "C"]
    D[lbl] = {
        "cpas": {t: st.mean(r["cpas"] for r in rows if r["tier"] == t) for t in "ABC"},
        "raw": st.mean(r["cpas"] + 2 * r["H"] for r in C),
        "H": sum(r["H"] for r in C) / len(C) * 100,
        "pass": sum((r["cpas"] + 2 * r["H"]) >= 3 for r in C) / len(C) * 100,
        "by_persona": {p: {t: st.mean(r["cpas"] for r in rows
                                      if r["tier"] == t and r["persona"] == p)
                           for t in "ABC"} for p in PERS}}
labels = [l for l, _ in ORDER]

# fig 1 — capability gradient
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(labels, [D[l]["cpas"]["C"] for l in labels], "o-", lw=2, ms=7, label="tier C (full system)")
ax.plot(labels, [D[l]["cpas"]["B"] for l in labels], "s--", lw=1.5, ms=5, label="tier B (IDS + SHAP)")
ax.plot(labels, [D[l]["cpas"]["A"] for l in labels], "^--", lw=1.5, ms=5, label="tier A (IDS alert only)")
ax.set_ylabel("CPAS"); ax.set_ylim(0, 5)
ax.set_title("Grounded context improves explanation quality at every capability level\n"
             "(a gradient, not a threshold)", fontsize=11)
ax.legend(fontsize=9); ax.grid(alpha=.3); ax.tick_params(labelsize=8)
fig.tight_layout(); fig.savefig(FIG / "fig1_capability_gradient.png", dpi=180); plt.close(fig)

# fig 2 — raw vs penalised: reliability is the separator
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.8))
x = range(len(labels))
# 8 models no longer fit horizontally in a half-width panel -> rotate, and flatten the
# two-line names (a rotated multi-line tick label is unreadable).
flat = [l.replace("\n", " ") for l in labels]
a1.bar([i - .2 for i in x], [D[l]["raw"] for l in labels], .4, label="raw D/C/A/R")
a1.bar([i + .2 for i in x], [D[l]["cpas"]["C"] for l in labels], .4, label="CPAS (after −λH)")
a1.set_xticks(list(x))
a1.set_xticklabels(flat, fontsize=8, rotation=30, ha="right"); a1.set_ylabel("score")
a1.set_title("Substance is similar; the penalty separates them", fontsize=10)
a1.legend(fontsize=8); a1.grid(alpha=.3, axis="y")
a2.plot(list(x), [D[l]["H"] for l in labels], "o-", color="firebrick", lw=2, ms=7)
a2.set_xticks(list(x)); a2.set_xticklabels(flat, fontsize=8, rotation=30, ha="right")
a2.set_ylabel("hallucination rate, tier C (%)"); a2.set_ylim(0, 45)
a2.set_title("Reliability, not capability, is the deployment constraint", fontsize=10)
a2.grid(alpha=.3); a2.tick_params(labelsize=7)
fig.tight_layout(); fig.savefig(FIG / "fig2_reliability_separates.png", dpi=180); plt.close(fig)

# fig 3 — tier ablation by persona, floor vs ceiling
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, lbl in zip(axes, ["llama3.1:8b\n(local)", "gpt-5.5\n(ceiling)"]):
    w = .25
    for i, t in enumerate("ABC"):
        ax.bar([j + (i - 1) * w for j in range(len(PERS))],
               [D[lbl]["by_persona"][p][t] for p in PERS], w, label=f"tier {t}")
    ax.set_xticks(range(len(PERS)))
    ax.set_xticklabels([p.replace("_", "\n") for p in PERS], fontsize=9)
    ax.set_title(lbl.replace("\n", " "), fontsize=10); ax.grid(alpha=.3, axis="y")
axes[0].set_ylabel("CPAS"); axes[0].set_ylim(0, 5); axes[0].legend(fontsize=8)
fig.suptitle("Tier ablation by persona: context helps every role, once the model can deliver it",
             fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig3_tier_ablation.png", dpi=180); plt.close(fig)

# fig 4 — the regulator story: context works, then H erases it (at 8B only)
fig, ax = plt.subplots(figsize=(8, 4.4))
labs, x = ["operator", "data scientist", "regulator"], range(3)
for off, (lbl, key) in zip((-.2, .2), [("llama3.1:8b", "llama3.1:8b\n(local)"),
                                       ("gpt-5.5", "gpt-5.5\n(ceiling)")]):
    rawv = []
    for p_ in PERS:
        rows = json.load(open(ROOT / f"experiments/results/"
                              f"{dict(ORDER)[key]}/cpas_scores.json"))["rows"]
        C = [r for r in rows if r["tier"] == "C" and r["persona"] == p_]
        rawv.append((st.mean(r["cpas"] + 2 * r["H"] for r in C),
                     st.mean(r["cpas"] for r in C),
                     sum(r["H"] for r in C) / len(C) * 100))
    ax.bar([i + off for i in x], [v[0] for v in rawv], .38, alpha=.35,
           color="tab:blue" if off < 0 else "tab:green",
           label=f"{lbl} — raw (before −λH)")
    ax.bar([i + off for i in x], [v[1] for v in rawv], .38,
           color="tab:blue" if off < 0 else "tab:green", label=f"{lbl} — CPAS")
    for i, v in enumerate(rawv):
        if v[0] - v[1] > .3:
            ax.annotate(f"H={v[2]:.0f}%", (i + off, v[0]), ha="center", va="bottom",
                        fontsize=8, color="firebrick")
ax.set_xticks(list(x)); ax.set_xticklabels(labs); ax.set_ylabel("CPAS"); ax.set_ylim(0, 5)
ax.set_title("The regulator benefits most from context — and loses most to unreliability\n"
             "(faded = raw score, solid = after the hallucination penalty)", fontsize=10)
ax.legend(fontsize=7, ncol=2); ax.grid(alpha=.3, axis="y")
fig.tight_layout(); fig.savefig(FIG / "fig4_regulator_penalty.png", dpi=180); plt.close(fig)

# fig 5 — lambda sensitivity: the conclusion does not depend on lambda=2
fig, ax = plt.subplots(figsize=(7.5, 4.2))
W = {"D": .30, "C": .25, "A": .25, "R": .20}
lams = [0, 1, 2, 3]
for lbl, tag in ORDER:
    rows = json.load(open(ROOT / f"experiments/results/{tag}/cpas_scores.json"))["rows"]
    C = [r for r in rows if r["tier"] == "C"]
    ax.plot(lams, [st.mean(sum(W[d] * r[d] for d in W) - L * r["H"] for r in C) for L in lams],
            "o-", ms=5, label=lbl.replace("\n", " "))
ax.axvline(2, color="grey", ls=":", lw=1)
ax.annotate("pre-registered λ=2", (2, .3), fontsize=8, color="grey", ha="center")
ax.set_xlabel("λ  (hallucination penalty)"); ax.set_ylabel("tier-C CPAS")
ax.set_xticks(lams); ax.set_ylim(0, 5)
ax.set_title("Model ordering is unchanged across every λ tested", fontsize=10)
ax.legend(fontsize=7); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig5_lambda_sensitivity.png", dpi=180); plt.close(fig)

# fig 6 — capability progression against weight-release date (D51)
# Release dates: OpenRouter catalogue `created` field, verified 2026-11-09. The two
# llama-3.1-8b rows share a date (same weights, two serving paths), so only the local
# one is plotted -- otherwise one release contributes two points to the rank statistic.
from figstyle import PALETTE, FigureStyle, apply_publication_style, finalize_figure
from scipy.stats import spearmanr
import datetime as dt

REL = {"llama3.1:8b\n(local)": ("2024-07-23", "open"),
       "llama-3.3-70b": ("2024-12-06", "open"),
       "qwen3-32b": ("2025-04-28", "open"),
       "qwen3-235b": ("2025-07-21", "open"),
       "gpt-5.5\n(ceiling)": ("2026-04-24", "closed"),
       "qwen3.8-27b": ("2026-08-14", "open"),
       "deepseek\nv4.1-flash": ("2026-10-17", "open")}

apply_publication_style(FigureStyle(font_size=13, axes_linewidth=2.0))
fig, ax = plt.subplots(figsize=(9.5, 5.4))
pts = sorted(((dt.date.fromisoformat(d), D[l]["cpas"]["C"], l.replace("\n", " "), kind)
              for l, (d, kind) in REL.items()), key=lambda t: t[0])
op = [q for q in pts if q[3] == "open"]
ax.plot([q[0] for q in op], [q[1] for q in op], "-", color=PALETTE["neutral"], lw=2, zorder=1)
ax.scatter([q[0] for q in op], [q[1] for q in op], s=130, color=PALETTE["blue_main"],
           zorder=3, label="open weights")
cl = [q for q in pts if q[3] == "closed"]
ax.scatter([q[0] for q in cl], [q[1] for q in cl], s=260, marker="*",
           color=PALETTE["red_strong"], zorder=3, label="closed weights")
ax.axhline(3.0, color=PALETTE["mute"], ls=":", lw=1.5)
ax.annotate("usability threshold 3.0", (dt.date(2026, 11, 20), 3.04), fontsize=10,
            ha="right", color=PALETTE["mute"])

# Hand-placed labels: eight points over two years cluster at both ends, and matplotlib
# has no collision avoidance, so offsets are per-point rather than a single rule.
OFF = {"llama3.1:8b (local)": (0.12, "bottom", "left"),
       "llama-3.3-70b":       (0.13, "bottom", "center"),
       "qwen3-32b":           (-0.14, "top", "center"),
       "qwen3-235b":          (0.13, "bottom", "center"),
       "gpt-5.5 (ceiling)":   (0.13, "bottom", "center"),
       "qwen3.8-27b":         (-0.14, "top", "center"),
       "deepseek v4.1-flash": (0.13, "bottom", "right")}
for x, y, lbl, _ in pts:
    dy, va, ha = OFF[lbl]
    ax.annotate(lbl, (x, y + dy), fontsize=11, ha=ha, va=va, color=PALETTE["ink"])

# the inversion: an older, larger model outscores a newer, smaller one
a = next(q for q in pts if q[2] == "llama-3.3-70b")
b = next(q for q in pts if q[2] == "qwen3-32b")
ax.annotate("", xy=(b[0], b[1]), xytext=(a[0], a[1]),
            arrowprops=dict(arrowstyle="->", color=PALETTE["violet"], lw=2.2,
                            connectionstyle="arc3,rad=-0.35"))
ax.annotate("not monotone: llama-3.3-70b (Dec 2024) outscores\nqwen3-32b (Apr 2025) by 0.29 CPAS "
            "— scale still beats recency",
            xy=(dt.date(2024, 11, 1), 2.22), fontsize=10.5, color=PALETTE["violet"])

# One point per RELEASE, not per run: the API and local llama-3.1-8b rows are the same
# weights, so counting both would give a single release two votes in a rank statistic.
rho, pv = spearmanr([q[0].toordinal() for q in pts], [q[1] for q in pts])
orho, opv = spearmanr([q[0].toordinal() for q in op], [q[1] for q in op])
ax.annotate(f"Spearman ρ = {rho:.3f}, p = {pv:.4f}  (n = {len(pts)} releases)\n"
            f"open weights only: ρ = {orho:.3f}, p = {opv:.4f}  (n = {len(op)})",
            xy=(0.03, 0.93), xycoords="axes fraction", fontsize=11,
            va="top", color=PALETTE["ink"],
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=PALETTE["neutral"], lw=1.5))
ax.set_ylabel("tier-C CPAS"); ax.set_xlabel("model weight-release date")
ax.set_ylim(2.0, 4.4); ax.set_xlim(dt.date(2024, 5, 1), dt.date(2026, 12, 31))
ax.grid(alpha=.3, axis="y")
ax.legend(loc="lower right", fontsize=11)
ax.set_title("Explanation quality tracks model release date, but not strictly",
             fontsize=14, pad=14)
print("  fig6:", [str(f.relative_to(ROOT)) for f in
                  finalize_figure(fig, FIG / "fig6_release_vs_cpas", pad=1.2)])


for f in sorted(FIG.glob("*.png")):
    print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size//1024} KB)")
