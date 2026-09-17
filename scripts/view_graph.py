"""Render the LightRAG knowledge graph to an interactive HTML you open in a browser.

Reads rag_storage/graph_chunk_entity_relation.graphml, colors nodes by entity_type,
and writes rag_storage/graph.html — zoom/drag/hover, no desktop app needed.
This is the quick view; for a publication figure open the .graphml in Gephi.

Run: conda run -n xai python scripts/view_graph.py            # build/open the HTML
     conda run -n xai python scripts/view_graph.py RTU-3      # inspect one node's edges
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import networkx as nx
from pyvis.network import Network

ROOT = Path(__file__).resolve().parents[1]
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"
OUT = ROOT / "docs" / "figures" / "graph.html"      # committed: a thesis artefact
PNG = ROOT / "docs" / "figures" / "graph.png"       # static, for slides/print

# canonical grid entities get bright colors; LLM-extracted concepts are muted grey
COLORS = {"DEVICE": "#e6550d", "IP_ADDRESS": "#fd8d3c", "BUS": "#3182bd",
          "BREAKER": "#31a354", "ZONE": "#756bb1", "VENDOR": "#e377c2"}
DEFAULT = "#bdbdbd"


def main() -> None:
    if not GRAPHML.exists():
        raise SystemExit(f"{GRAPHML} not found — run `python -m caie.contextualizer.ingest` first")
    g = nx.read_graphml(GRAPHML)

    # `view_graph.py <node>` — print that node's relationships in the terminal
    if len(sys.argv) > 1:
        node = sys.argv[1]
        if node not in g:
            raise SystemExit(f"'{node}' not in graph. Try one of: "
                             f"{', '.join(sorted(list(g.nodes))[:8])} ...")
        edges = list(g.edges(node, data=True))
        print(f"{node} — {g.nodes[node].get('entity_type','?')}: "
              f"{g.nodes[node].get('description','')[:120]}")
        print(f"{len(edges)} relationship(s):")
        for _, tgt, d in edges:
            print(f"  —[{d.get('keywords','?')}]→ {tgt}")
            print(f"       {d.get('description','')[:110]}  (weight {d.get('weight','?')})")
        return
    net = Network(height="800px", width="100%", bgcolor="#111", font_color="#eee",
                  notebook=False, cdn_resources="in_line")
    for node, d in g.nodes(data=True):
        etype = d.get("entity_type", "?")
        net.add_node(node, label=node, color=COLORS.get(etype, DEFAULT),
                     title=f"{etype}: {d.get('description', '')[:200]}",
                     size=18 if etype in COLORS else 10)
    for a, b, d in g.edges(data=True):
        # tooltip shows the relationship TYPE and its description (hover the line)
        kw, desc = d.get("keywords", ""), d.get("description", "")
        net.add_edge(a, b, title=f"[{kw}] {desc}"[:200], label=kw or None)
    net.force_atlas_2based()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(OUT), notebook=False)

    # pyvis's cdn_resources="in_line" inlines vis-network but still LINKS Bootstrap from
    # jsdelivr, so the file is not actually self-contained: it degrades without internet
    # (bad for an air-gapped demo) and rots when the CDN URL stops resolving (bad for a
    # thesis artefact meant to open in five years). Bootstrap is only used for cosmetic
    # chrome here, so strip the links rather than vendoring 200 KB of CSS.
    html = OUT.read_text()
    before = len(re.findall(r'(?:src|href)="https?://', html))
    html = re.sub(r'\s*<(?:link|script)[^>]*(?:href|src)="https?://[^"]*"[^>]*>'
                  r'(?:</script>)?', "", html)
    after = len(re.findall(r'(?:src|href)="https?://', html))
    OUT.write_text(html)

    print(f"wrote {OUT}  ({g.number_of_nodes()} nodes, {g.number_of_edges()} edges, "
          f"{len(html)//1024} KB)")
    print(f"  external refs stripped: {before} -> {after}  "
          f"({'fully self-contained' if after == 0 else 'STILL HAS EXTERNAL REFS'})")
    _write_png(g)
    print("open it: file://" + str(OUT))
    print("legend: orange=DEVICE, light-orange=IP, blue=BUS, green=BREAKER, "
          "purple=ZONE, grey=LLM-extracted concept")


def _write_png(g) -> None:
    """Static render for slides and print, where nobody can hover a tooltip."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(13, 9))
    pos = nx.spring_layout(g, k=.55, iterations=180, seed=7)
    types = [d.get("entity_type", "?") for _, d in g.nodes(data=True)]
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#d9d9d9", width=.7)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=[260 if t in COLORS else 60 for t in types],
                           node_color=[COLORS.get(t, DEFAULT) for t in types],
                           linewidths=.4, edgecolors="#555")
    # label only the canonical grid entities: labelling 153 nodes is unreadable, and the
    # grey LLM-extracted concepts are context, not the point of the figure
    nx.draw_networkx_labels(g, pos, ax=ax, font_size=7,
                            labels={n: n for n, d in g.nodes(data=True)
                                    if d.get("entity_type") in COLORS})
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=c, label=t)
                       for t, c in COLORS.items()]
                      + [Line2D([], [], marker="o", ls="", color=DEFAULT,
                                label="LLM-extracted concept")],
              loc="upper left", fontsize=8, frameon=False)
    ax.set_title(f"CAIE knowledge graph — {g.number_of_nodes()} entities, "
                 f"{g.number_of_edges()} relations\n"
                 f"coloured entities are seeded from entities.yaml; grey are LLM-extracted",
                 fontsize=11)
    ax.axis("off")
    fig.tight_layout(); fig.savefig(PNG, dpi=170); plt.close(fig)
    print(f"wrote {PNG}  ({PNG.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
