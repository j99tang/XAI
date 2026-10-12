"""CAIE architecture figure, in the style of LightRAG's Figure 1.

Five stages left to right: source passage -> indexing -> knowledge graph ->
persona-conditioned retrieval -> role-specific narratives. Content is REAL (the RTU-3
trace in docs/notes/worked_example.md), not illustrative, so the figure can be audited
against the data rather than taken on trust.

Styled to the house publication conventions in scripts/figstyle.py: semantic palette
(blue = the proposed contributions, neutral = stock components, green = outcomes,
highlight gold reserved for the single callout), Arial/Helvetica stack, and both a
raster and a vector export.

Two things it encodes that stock LightRAG does not, because they are this project's
departures:
  * a DETERMINISTIC path alongside LLM extraction (seed_graph + resolve_device), added
    because the 8B under-extracted IPs/buses/breakers and the synthesizer then invented
    device names;
  * THREE persona-conditioned queries instead of one shared retrieval (plan 11.1 / D43),
    because one ranking could not serve three information needs.

Run: conda run -n xai python scripts/make_architecture_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import networkx as nx
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from figstyle import PALETTE, FigureStyle, apply_publication_style, finalize_figure
import matplotlib.pyplot as plt

OUT = ROOT / "docs" / "figures" / "fig0_architecture"
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"

P = PALETTE
INK, MUTE = P["ink"], P["mute"]
# Semantic roles. Contributions are blue; stock components neutral; outputs green.
C_CONTRIB, C_STOCK = P["blue_main"], P["mute"]
TINT = {"source": "#F5F5F5", "graph": "#EAF1F3", "retrieve": "#F2ECF4",
        "output": P["green_1"], "contrib": "#E4EDF6", "callout": "#FFF9E0"}


def box(ax, x, y, w, h, fc, ec, lw=1.2, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, zorder=z))


def arrow(ax, x1, y1, x2, y2, color=MUTE, lw=1.8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", lw=lw,
                                 color=color, mutation_scale=14, zorder=3))


def main() -> None:
    # compact-plot preset: this is a dense schematic, not a large bar panel
    apply_publication_style(FigureStyle(font_size=15, axes_linewidth=2))
    fig, ax = plt.subplots(figsize=(20, 7.1))
    ax.set_xlim(0, 20); ax.set_ylim(1.15, 8.0); ax.axis("off")

    head = dict(fontsize=12, weight="bold", ha="center", color=INK)
    sub = dict(fontsize=8.5, ha="center", color=MUTE, style="italic")

    # ------------------------------------------------------------ 1 · source
    ax.text(1.85, 7.78, "1 · Source", **head)
    ax.text(1.85, 7.44, "knowledge_base/  ·  7 docs, 4.2k words", **sub)
    box(ax, .25, 4.15, 3.2, 3.1, TINT["source"], P["neutral"], 1.4)
    ax.text(.45, 7.00, "topology/ip_device_map.md", fontsize=8.5, weight="bold", color=INK)
    # The data row is drawn as COLOURED SEGMENTS rather than one string with rectangles
    # laid over it: monospace advance width is predictable, so each field can be placed
    # exactly, whereas eyeballed boxes drift by a few hundredths and look misaligned.
    MONO, CW = 7.4, 0.0612          # fontsize, and its character width in data units
    ax.text(.45, 6.62, "| IP | Device | Zone | Bus | Breakers |", fontsize=MONO,
            family="monospace", color=INK)
    ax.text(.45, 6.33, "|----|--------|------|-----|----------|", fontsize=MONO,
            family="monospace", color="#AAAAAA")
    row = "| 10.0.0.5 | RTU-3 | ZONE-S | 6 |"
    # (start index, text, colour) — colours match the node colours in panel 3
    fields = {2: P["blue_secondary"], 13: P["blue_main"], 21: P["violet"], 30: P["teal"]}
    for i, ch in enumerate(row):
        start = max((k for k in fields if k <= i), default=None)
        end = {2: 10, 13: 18, 21: 27, 30: 31}.get(start, -1)
        hot = start is not None and i < end
        ax.text(.45 + i * CW, 6.04, ch, fontsize=MONO, family="monospace",
                color=fields[start] if hot else INK, weight="bold" if hot else "normal")
    ax.text(.45, 5.75, "|   BR-5-6, BR-6-11, BR-6-12, BR-6-13 |", fontsize=MONO,
            family="monospace", color=INK)
    ax.add_patch(plt.Rectangle((.45 + 3.7 * CW, 5.70), 34.2 * CW, .20, fc="none",
                               ec=P["green_3"], lw=1.3))

    ax.text(.45, 5.26, "regulatory_compliance/compliance.md", fontsize=8.5,
            weight="bold", color=INK)
    for i, t in enumerate(["CIP-008-6 R4: one hour after determination",
                           "of a Reportable Incident; end of next",
                           "calendar day for an attempt."]):
        ax.text(.45, 4.96 - i * .24, t, fontsize=7.2, family="monospace", color=INK)

    # ------------------------------------------------------------ 2 · indexing
    ax.text(5.1, 7.78, "2 · Indexing", **head)
    ax.text(5.1, 7.44, "two paths, deliberately", **sub)
    box(ax, 3.95, 5.90, 2.3, 1.15, TINT["contrib"], C_CONTRIB, 2.0)
    ax.text(5.1, 6.72, "DETERMINISTIC", fontsize=9, weight="bold", ha="center", color=C_CONTRIB)
    ax.text(5.1, 6.44, "seed_graph.py", fontsize=7.8, ha="center", family="monospace", color=INK)
    ax.text(5.1, 6.13, "entities.yaml → 46 canonical\nnodes injected verbatim",
            fontsize=7, ha="center", color=MUTE)
    box(ax, 3.95, 4.35, 2.3, 1.15, "#F5F5F5", C_STOCK, 1.4)
    ax.text(5.1, 5.17, "LLM EXTRACTION", fontsize=9, weight="bold", ha="center", color=C_STOCK)
    ax.text(5.1, 4.89, "llama3.1:8b", fontsize=7.8, ha="center", family="monospace", color=INK)
    ax.text(5.1, 4.58, "107 concepts + relation\ndescriptions", fontsize=7, ha="center", color=MUTE)
    arrow(ax, 3.5, 6.10, 3.9, 6.45, C_CONTRIB)
    arrow(ax, 3.5, 5.30, 3.9, 4.95, C_STOCK)
    ax.text(3.70, 6.60, "seed", fontsize=7, color=C_CONTRIB, ha="center")
    ax.text(3.60, 4.86, "extract", fontsize=7, color=C_STOCK, ha="center")
    ax.text(5.1, 3.96, "the 8B under-extracted IPs / buses / breakers,\n"
                       "so the physical join is injected, not learned",
            fontsize=7, ha="center", va="center", color=C_CONTRIB, style="italic")

    # ------------------------------------------------------------ 3 · graph
    ax.text(9.15, 7.78, "3 · Knowledge graph", **head)
    ax.text(9.15, 7.44, "153 entities  ·  134 relations", **sub)
    box(ax, 6.85, 4.35, 4.6, 2.95, TINT["graph"], P["teal"], 1.4)
    g = nx.read_graphml(GRAPHML).to_undirected()
    COL = {"RTU-3": P["blue_main"], "10.0.0.5": P["blue_secondary"], "Bus 6": P["teal"],
           "ZONE-S": P["violet"], "BR-5-6": P["green_3"], "BR-6-11": P["green_3"],
           "SCADA-1": P["blue_main"]}
    pos = {"RTU-3": (9.15, 5.78), "10.0.0.5": (7.55, 6.66), "Bus 6": (9.15, 6.90),
           "ZONE-S": (10.75, 6.66), "BR-5-6": (7.55, 4.95), "BR-6-11": (9.15, 4.78),
           "SCADA-1": (10.75, 4.95)}
    assert all(n in g for n in pos), "ego nodes missing from graphml"
    for n in pos:
        if n != "RTU-3":
            ax.plot(*zip(pos["RTU-3"], pos[n]), color=P["teal"], lw=1.2, alpha=.55, zorder=2)
    for n, (x, y) in pos.items():
        ax.scatter(x, y, s=480 if n == "RTU-3" else 310, c=COL[n], edgecolors=INK,
                   linewidths=1.6 if n == "RTU-3" else .7, zorder=4)
        # labels sit BELOW the markers: entity names are wider than any legible
        # in-marker font at this panel size
        ax.text(x, y - .27, n, fontsize=7, ha="center", va="top", zorder=5,
                weight="bold" if n == "RTU-3" else "normal", color=INK)
    for n, lbl in [("10.0.0.5", "ip mapping"), ("Bus 6", "located at"), ("ZONE-S", "in zone"),
                   ("BR-5-6", "controls"), ("BR-6-11", "controls"), ("SCADA-1", "supervises")]:
        mx = (pos["RTU-3"][0] + pos[n][0]) / 2
        my = (pos["RTU-3"][1] + pos[n][1]) / 2
        key = n == "SCADA-1"
        ax.text(mx, my, lbl, fontsize=6.2, ha="center", va="center", zorder=6,
                color=P["red_strong"] if key else "#2E6670",
                weight="bold" if key else "normal",
                bbox=dict(fc=TINT["graph"], ec="none", pad=1.0))
    # the one highlight in the figure
    box(ax, 6.85, 3.60, 4.6, .64, TINT["callout"], P["highlight"], 1.8, z=6)
    ax.text(9.15, 3.92, '"Loss of communication with an RTU means loss of visibility and\n'
                        'control of its breakers"   —   carried on the EDGE, not on a node',
            fontsize=6.8, ha="center", va="center", color=INK, zorder=7)
    arrow(ax, 6.30, 6.45, 6.80, 6.10, C_CONTRIB)
    arrow(ax, 6.30, 4.95, 6.80, 5.30, C_STOCK)

    # ------------------------------------------------------------ 4 · retrieval
    ax.text(13.6, 7.78, "4 · Retrieval", **head)
    ax.text(13.6, 7.44, "one query PER PERSONA  (§11.1)", **sub)
    box(ax, 11.95, 4.35, 3.3, 2.95, TINT["retrieve"], P["violet"], 1.4)
    box(ax, 12.15, 6.42, 2.9, .62, TINT["contrib"], C_CONTRIB, 1.8)
    ax.text(13.6, 6.86, "resolve_device(10.0.0.5)", fontsize=7.4, ha="center",
            weight="bold", family="monospace", color=C_CONTRIB)
    ax.text(13.6, 6.58, "table join  ·  always first  ·  never truncated",
            fontsize=6.4, ha="center", color=MUTE)
    for i, (p_, q) in enumerate([("operator", "which breakers, manual control,\nphysical risk"),
                                 ("data scientist", "what the features mean,\nwhat they can't prove"),
                                 ("regulator", "reportable? which clock?\nnotify whom?")]):
        ytop = 6.10 - i * .58
        box(ax, 12.15, ytop - .50, 2.9, .50, "white", P["violet"], 1)
        ax.text(12.30, ytop - .14, p_, fontsize=7.4, weight="bold", color=P["violet"])
        ax.text(12.30, ytop - .36, q, fontsize=6.2, color=MUTE, va="center")
    ax.text(13.6, 3.92, "one ranking could not serve three needs: the CIP rule\n"
                        "reached the model in 0 / 30 blocks before this",
            fontsize=7, ha="center", va="center", color=P["violet"], style="italic")
    arrow(ax, 11.50, 5.40, 11.90, 5.40)

    # ------------------------------------------------------------ 5 · output
    ax.text(17.6, 7.78, "5 · Role-specific narratives", **head)
    ax.text(17.6, 7.44, "tier C  —  the system under test", **sub)
    box(ax, 15.5, 4.35, 4.25, 2.95, TINT["output"], P["green_3"], 1.4)
    outs = [("OPERATOR",
             "Affected: RTU-3, IEC-104 station,\n10.0.0.5:2404, ZONE-S at Bus 6.\n"
             "Controls BR-5-6, BR-6-11, BR-6-12,\nBR-6-13.\n"
             "Main risk is loss of view/control\nat Bus 6, not confirmed breaker\noperation."),
            ("REGULATOR",
             "Reportable as an ATTEMPT under\nCIP-008-6 R4 — end of next\n"
             "calendar day to E-ISAC/NCCIC.\nThe detector does not establish\ncompromise.")]
    for i, (p_, t) in enumerate(outs):
        ytop = 7.08 - i * 1.44
        box(ax, 15.7, ytop - 1.18, 3.85, 1.18, "white", P["green_3"], 1)
        ax.text(15.85, ytop - .22, p_, fontsize=7.4, weight="bold", color="#2F6B46")
        ax.text(15.85, ytop - .72, t, fontsize=6.3, va="center", color=INK)
    ax.text(17.6, 3.92, "every claim traces back to a specific edge\n"
                        "— see docs/notes/worked_example.md",
            fontsize=7, ha="center", va="center", color="#2F6B46", style="italic")
    arrow(ax, 15.30, 5.40, 15.65, 5.40)

    # ------------------------------------------------------------ footer
    ax.plot([.25, 19.75], [3.30, 3.30], color=P["neutral"], lw=1.2)
    ax.text(.25, 3.00, "The two departures from stock LightRAG", fontsize=10,
            weight="bold", color=INK)
    ax.text(.25, 2.60,
            "①  A deterministic path runs alongside LLM extraction.  The 8B under-extracted "
            "IPs, buses and breakers, and the synthesizer then invented device names "
            "(\"RTU-123\").  Canonical entities are now injected from entities.yaml, and the "
            "IP→device join is a table lookup\n     prepended to every context block — so the "
            "network→physical link is never left to semantic search.  Coloured nodes above are "
            "seeded; grey concepts elsewhere in the graph are LLM-extracted.",
            fontsize=7.8, color=INK, va="top")
    ax.text(.25, 1.76,
            "②  Retrieval is persona-conditioned, not shared.  One query per alert, reused for "
            "three personas, ranked the compliance chunk last: the CIP reporting rule reached "
            "the synthesizer in 0 of 30 context blocks, and the model filled the gap with a "
            "\"24 hours\" figure\n     found nowhere in the knowledge base.  Three targeted "
            "queries put it in 30 of 30.  The cost, stated plainly: three retrievals per alert "
            "instead of one.",
            fontsize=7.8, color=INK, va="top")
    ax.text(19.75, 1.20, "CAIE  ·  Context-Aware Intrusion Explanation", fontsize=7.2,
            ha="right", color=P["neutral"])

    for p_ in finalize_figure(fig, OUT, formats=("png", "pdf"), dpi=300, pad=0.4):
        print(f"wrote {p_}  ({p_.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
