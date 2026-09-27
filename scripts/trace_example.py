"""Worked end-to-end example: KB passage -> graph -> retrieval -> persona narrative.

The LightRAG paper's Figure 1 (beekeeper) shows the framework abstractly. This renders
the same four stages with THIS project's data, so the graph's contribution is auditable
rather than asserted: you can see which edges the narrative actually used.

Writes docs/figures/trace_rtu3.png (ego-graph of the anchor entity) and prints the
four-stage trace for docs/notes/worked_example.md.

Run: conda run -n xai python scripts/trace_example.py [ENTITY]   (default RTU-3)
"""
from __future__ import annotations
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"
ANCHOR = sys.argv[1] if len(sys.argv) > 1 else "RTU-3"
OUT = ROOT / "docs" / "figures" / f"trace_{ANCHOR.lower().replace('-','')}.png"
COLORS = {"DEVICE": "#e6550d", "IP_ADDRESS": "#fd8d3c", "BUS": "#3182bd",
          "BREAKER": "#31a354", "ZONE": "#756bb1", "VENDOR": "#e377c2"}
DEFAULT = "#bdbdbd"


def main() -> None:
    g = nx.read_graphml(GRAPHML).to_undirected()
    if ANCHOR not in g:
        raise SystemExit(f"{ANCHOR} not in graph")
    ego = nx.ego_graph(g, ANCHOR, radius=1)

    fig, ax = plt.subplots(figsize=(11, 7.5))
    pos = nx.spring_layout(ego, k=1.1, iterations=300, seed=3)
    pos[ANCHOR] = [0, 0]                      # anchor dead centre
    types = [ego.nodes[n].get("entity_type", "?") for n in ego]
    nx.draw_networkx_edges(ego, pos, ax=ax, edge_color="#c6c6c6", width=1.4)
    nx.draw_networkx_nodes(ego, pos, ax=ax,
                           node_size=[1500 if n == ANCHOR else 900 for n in ego],
                           node_color=[COLORS.get(t, DEFAULT) for t in types],
                           edgecolors=["#000" if n == ANCHOR else "#666" for n in ego],
                           linewidths=[2 if n == ANCHOR else .5 for n in ego])
    nx.draw_networkx_labels(ego, pos, ax=ax, font_size=8,
                            labels={n: (n[:26] + "…" if len(n) > 27 else n) for n in ego})
    # edge labels are the relation TYPE — the thing a flat vector store cannot give you
    nx.draw_networkx_edge_labels(
        ego, pos, ax=ax, font_size=6.5, font_color="#444", bbox=dict(alpha=0),
        edge_labels={(a, b): (d.get("keywords", "") or "").split(",")[0][:22]
                     for a, b, d in ego.edges(data=True)})
    ax.set_title(f"{ANCHOR}: one-hop neighbourhood in the CAIE knowledge graph\n"
                 f"{ego.number_of_nodes()-1} neighbours · edge labels are relation types",
                 fontsize=11)
    ax.axis("off")
    fig.tight_layout(); fig.savefig(OUT, dpi=170); plt.close(fig)
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB, {ego.number_of_nodes()-1} neighbours)")

    print(f"\n{ANCHOR} — {g.nodes[ANCHOR].get('entity_type','?')}")
    print(f"  {g.nodes[ANCHOR].get('description','')[:150]}")
    for _, tgt, d in nx.read_graphml(GRAPHML).edges(ANCHOR, data=True):
        print(f"  —[{d.get('keywords','?')[:34]}]→ {tgt[:40]}")


if __name__ == "__main__":
    main()
