"""CAIE architecture figure, in the style of LightRAG's Figure 1.

Five stages left to right: source passage -> indexing -> graph -> persona-conditioned
retrieval -> three role-specific narratives. Content is REAL (the RTU-3 trace in
docs/notes/worked_example.md), not illustrative, so the figure can be audited.

Two things it encodes that the LightRAG figure does not, because they are this
project's departures from stock LightRAG:
  * a DETERMINISTIC path alongside LLM extraction (seed_graph + resolve_device), added
    because the 8B under-extracted IPs/buses/breakers and the synthesizer then invented
    device names;
  * THREE persona-conditioned queries instead of one shared retrieval (plan 11.1 / D43),
    because one ranking could not serve three information needs.

Run: conda run -n xai python scripts/make_architecture_figure.py
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures" / "fig0_architecture.png"
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"

INK, MUTE = "#1a1a1a", "#666666"
C_SRC, C_DET, C_LLM = "#fff4e6", "#e6550d", "#4a7ebb"
C_GRAPH, C_RET, C_OUT = "#eef4fb", "#f3eefb", "#eaf6ee"


def box(ax, x, y, w, h, fc, ec, lw=1.2, r=0.02, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, zorder=z))


def arrow(ax, x1, y1, x2, y2, color=MUTE, lw=1.8, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, lw=lw,
                                 color=color, mutation_scale=14,
                                 connectionstyle="arc3,rad=0", zorder=3))


def main() -> None:
    fig, ax = plt.subplots(figsize=(20, 7.1))
    ax.set_xlim(0, 20); ax.set_ylim(1.15, 8.0); ax.axis("off")

    head = dict(fontsize=11.5, weight="bold", ha="center", color=INK)
    sub = dict(fontsize=8, ha="center", color=MUTE, style="italic")

    # ---------------------------------------------------------------- 1. source
    ax.text(1.85, 7.8, "1 · Source", **head)
    ax.text(1.85, 7.45, "knowledge_base/ (7 docs, 4.2k words)", **sub)
    box(ax, .25, 4.15, 3.2, 3.1, C_SRC, "#d0a070")
    ax.text(.45, 7.0, "topology/ip_device_map.md", fontsize=8, weight="bold", color="#8a5a10")
    ax.text(.45, 6.62, "| IP | Device | Zone | Bus | Breakers |", fontsize=7.4, family="monospace")
    ax.text(.45, 6.34, "|----|--------|------|-----|----------|", fontsize=7.4, family="monospace",
            color="#bbb")
    for i, (txt, col) in enumerate([
            ("| 10.0.0.5 | RTU-3 | ZONE-S | 6 |", INK),
            ("|   BR-5-6, BR-6-11, BR-6-12, BR-6-13 |", INK)]):
        ax.text(.45, 6.04 - i * .28, txt, fontsize=7.4, family="monospace", color=col)
    ax.add_patch(plt.Rectangle((.92, 5.94), .52, .22, fc="none", ec="#e6550d", lw=1.4))
    ax.add_patch(plt.Rectangle((1.62, 5.94), .48, .22, fc="none", ec="#756bb1", lw=1.4))
    ax.add_patch(plt.Rectangle((2.52, 5.94), .16, .22, fc="none", ec="#3182bd", lw=1.4))
    ax.add_patch(plt.Rectangle((.70, 5.66), 2.3, .22, fc="none", ec="#31a354", lw=1.4))
    ax.text(.45, 5.28, "regulatory_compliance/compliance.md", fontsize=8, weight="bold",
            color="#8a5a10")
    ax.text(.45, 4.98, "CIP-008-6 R4: one hour after determination", fontsize=7.2,
            family="monospace")
    ax.text(.45, 4.74, "of a Reportable Incident; end of next", fontsize=7.2, family="monospace")
    ax.text(.45, 4.50, "calendar day for an attempt.", fontsize=7.2, family="monospace")

    # ---------------------------------------------------------------- 2. indexing
    ax.text(5.1, 7.8, "2 · Indexing", **head)
    ax.text(5.1, 7.45, "two paths, deliberately", **sub)
    box(ax, 3.95, 5.9, 2.3, 1.15, "#fdece1", C_DET, 1.6)
    ax.text(5.1, 6.72, "DETERMINISTIC", fontsize=8.5, weight="bold", ha="center", color=C_DET)
    ax.text(5.1, 6.44, "seed_graph.py", fontsize=7.6, ha="center", family="monospace")
    ax.text(5.1, 6.14, "entities.yaml → 46 canonical\nnodes injected verbatim",
            fontsize=6.8, ha="center", color=MUTE)
    box(ax, 3.95, 4.35, 2.3, 1.15, "#e8eff8", C_LLM, 1.6)
    ax.text(5.1, 5.17, "LLM EXTRACTION", fontsize=8.5, weight="bold", ha="center", color=C_LLM)
    ax.text(5.1, 4.89, "llama3.1:8b", fontsize=7.6, ha="center", family="monospace")
    ax.text(5.1, 4.59, "107 concepts + relation\ndescriptions", fontsize=6.8, ha="center",
            color=MUTE)
    arrow(ax, 3.5, 6.1, 3.9, 6.45, C_DET)
    arrow(ax, 3.5, 5.3, 3.9, 4.95, C_LLM)
    ax.text(3.72, 6.62, "seed", fontsize=6.8, color=C_DET, ha="center")
    ax.text(3.68, 5.08, "extract", fontsize=6.8, color=C_LLM, ha="center")
    ax.text(5.1, 3.98, "the 8B under-extracted IPs/buses/breakers,\n"
                       "so the physical join is injected, not learned",
            fontsize=6.6, ha="center", color=C_DET, style="italic")

    # ---------------------------------------------------------------- 3. graph
    ax.text(9.15, 7.8, "3 · Knowledge graph", **head)
    ax.text(9.15, 7.45, "153 entities · 134 relations", **sub)
    box(ax, 6.85, 4.35, 4.6, 2.95, C_GRAPH, "#9dbcd9")
    g = nx.read_graphml(GRAPHML).to_undirected()
    COL = {"RTU-3": "#e6550d", "10.0.0.5": "#fd8d3c", "Bus 6": "#3182bd", "ZONE-S": "#756bb1",
           "BR-5-6": "#31a354", "BR-6-11": "#31a354", "SCADA-1": "#e6550d"}
    pos = {"RTU-3": (9.15, 5.78), "10.0.0.5": (7.55, 6.66), "Bus 6": (9.15, 6.90),
           "ZONE-S": (10.75, 6.66), "BR-5-6": (7.55, 4.95), "BR-6-11": (9.15, 4.78),
           "SCADA-1": (10.75, 4.95)}
    for n in pos:
        if n != "RTU-3":
            ax.plot(*zip(pos["RTU-3"], pos[n]), color="#9dbcd9", lw=1.3, zorder=2)
    for n, (x, y) in pos.items():
        ax.scatter(x, y, s=470 if n == "RTU-3" else 310, c=COL[n], edgecolors="#333",
                   linewidths=1.5 if n == "RTU-3" else .6, zorder=4)
        # label BELOW the marker: node names are wider than any readable in-marker font
        ax.text(x, y - .27, n, fontsize=6.8, ha="center", va="top", zorder=5,
                weight="bold" if n == "RTU-3" else "normal", color=INK)
    for n, lbl in [("10.0.0.5", "ip mapping"), ("Bus 6", "located at"), ("ZONE-S", "in zone"),
                   ("BR-5-6", "controls"), ("BR-6-11", "controls")]:
        mx = (pos["RTU-3"][0] + pos[n][0]) / 2
        my = (pos["RTU-3"][1] + pos[n][1]) / 2
        ax.text(mx, my, lbl, fontsize=5.8, ha="center", va="center", color="#33628f", zorder=6,
                bbox=dict(fc=C_GRAPH, ec="none", pad=.9))
    mx = (pos["RTU-3"][0] + pos["SCADA-1"][0]) / 2
    my = (pos["RTU-3"][1] + pos["SCADA-1"][1]) / 2
    ax.text(mx, my, "supervises", fontsize=5.9, ha="center", va="center", color="#b3121e",
            weight="bold", zorder=6, bbox=dict(fc=C_GRAPH, ec="none", pad=.9))
    # callout sits OUTSIDE the panel so it cannot occlude a node
    box(ax, 6.85, 3.62, 4.6, .62, "#fff0f0", "#b3121e", 1.1, z=6)
    ax.text(9.15, 3.93, '"Loss of communication with an RTU means loss of visibility and\n'
                        'control of its breakers"  —  carried on the EDGE, not on a node',
            fontsize=6.4, ha="center", va="center", color="#b3121e", zorder=7)
    arrow(ax, 6.3, 6.45, 6.8, 6.1, C_DET)
    arrow(ax, 6.3, 4.95, 6.8, 5.3, C_LLM)

    # ---------------------------------------------------------------- 4. retrieval
    ax.text(13.6, 7.8, "4 · Retrieval", **head)
    ax.text(13.6, 7.45, "one query PER PERSONA (§11.1)", **sub)
    box(ax, 11.95, 4.35, 3.3, 2.95, C_RET, "#b9a7d6")
    box(ax, 12.15, 6.42, 2.9, .62, "#fdece1", C_DET, 1.4)
    ax.text(13.6, 6.86, "resolve_device(10.0.0.5)", fontsize=7, ha="center", weight="bold",
            family="monospace", color=C_DET)
    ax.text(13.6, 6.58, "table join · always first · never truncated", fontsize=6.2,
            ha="center", color=MUTE)
    for i, (p, q) in enumerate([("operator", "which breakers, manual control,\nphysical risk"),
                                ("data scientist", "what the features mean,\nwhat they can't prove"),
                                ("regulator", "reportable? which clock?\nnotify whom?")]):
        ytop = 6.10 - i * .58                       # boxes land 5.52-6.02 … 4.36-4.86
        box(ax, 12.15, ytop - .50, 2.9, .50, "white", "#b9a7d6", 1)
        ax.text(12.3, ytop - .14, p, fontsize=7.2, weight="bold", color="#5b4a8a")
        ax.text(12.3, ytop - .36, q, fontsize=6.0, color=MUTE, va="center")
    ax.text(13.6, 3.93, "one ranking could not serve three needs: the CIP rule\n"
                        "reached the model in 0/30 blocks before this",
            fontsize=6.4, ha="center", va="center", color="#5b4a8a", style="italic")
    arrow(ax, 11.5, 5.4, 11.9, 5.4)

    # ---------------------------------------------------------------- 5. output
    ax.text(17.6, 7.8, "5 · Role-specific narratives", **head)
    ax.text(17.6, 7.45, "tier C — the system under test", **sub)
    box(ax, 15.5, 4.35, 4.25, 2.95, C_OUT, "#8fc3a3")
    outs = [("OPERATOR",
             "Affected: RTU-3, IEC-104 station,\n10.0.0.5:2404, ZONE-S at Bus 6.\n"
             "Controls BR-5-6, BR-6-11, BR-6-12,\nBR-6-13.\n"
             "Main risk is loss of view/control\nat Bus 6, not confirmed breaker\noperation."),
            ("REGULATOR",
             "Reportable as an ATTEMPT under\nCIP-008-6 R4 — end of next\n"
             "calendar day to E-ISAC/NCCIC.\nThe detector does not establish\ncompromise.")]
    for i, (p, t) in enumerate(outs):
        ytop = 7.08 - i * 1.44                      # 5.90-7.08 and 4.46-5.64
        box(ax, 15.7, ytop - 1.18, 3.85, 1.18, "white", "#8fc3a3", 1)
        ax.text(15.85, ytop - .22, p, fontsize=7.2, weight="bold", color="#2f6b46")
        ax.text(15.85, ytop - .72, t, fontsize=6.1, va="center", color=INK)
    arrow(ax, 15.3, 5.4, 15.65, 5.4)
    ax.text(17.6, 3.93, "every claim traces back to a specific edge\n— see docs/notes/worked_example.md",
            fontsize=6.4, ha="center", va="center", color="#2f6b46", style="italic")

    # ---------------------------------------------------------------- footer
    ax.plot([.25, 19.75], [3.32, 3.32], color="#ddd", lw=1)
    ax.text(.25, 3.02, "The two departures from stock LightRAG", fontsize=9.5, weight="bold",
            color=INK)
    ax.text(.25, 2.62,
            "①  A deterministic path runs alongside LLM extraction.  The 8B under-extracted "
            "IPs, buses and breakers, and the synthesizer then invented device names "
            "(\"RTU-123\").  Canonical entities are now injected from entities.yaml, and the "
            "IP→device join is a table lookup\n     prepended to every context block — so the "
            "network→physical link is never left to semantic search.  Coloured nodes above are "
            "seeded; grey concepts elsewhere in the graph are LLM-extracted.",
            fontsize=7.4, color=INK, va="top")
    ax.text(.25, 1.78,
            "②  Retrieval is persona-conditioned, not shared.  One query per alert, reused for "
            "three personas, ranked the compliance chunk last: the CIP reporting rule reached "
            "the synthesizer in 0 of 30 context blocks, and the model filled the gap with a "
            "\"24 hours\" figure\n     found nowhere in the knowledge base.  Three targeted "
            "queries put it in 30 of 30.  The cost, stated plainly: three retrievals per alert "
            "instead of one.",
            fontsize=7.4, color=INK, va="top")
    ax.text(19.75, 1.22, "CAIE · Context-Aware Intrusion Explanation", fontsize=7,
            ha="right", color="#999")

    fig.tight_layout()
    fig.savefig(OUT, dpi=175, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
