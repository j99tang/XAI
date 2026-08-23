"""Render the LightRAG knowledge graph to an interactive HTML you open in a browser.

Reads rag_storage/graph_chunk_entity_relation.graphml, colors nodes by entity_type,
and writes rag_storage/graph.html — zoom/drag/hover, no desktop app needed.
This is the quick view; for a publication figure open the .graphml in Gephi.

Run: conda run -n xai python scripts/view_graph.py            # build/open the HTML
     conda run -n xai python scripts/view_graph.py RTU-3      # inspect one node's edges
"""
from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
from pyvis.network import Network

ROOT = Path(__file__).resolve().parents[1]
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"
OUT = ROOT / "rag_storage" / "graph.html"

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
    net.write_html(str(OUT), notebook=False)
    print(f"wrote {OUT}  ({g.number_of_nodes()} nodes, {g.number_of_edges()} edges)")
    print("open it: file://" + str(OUT))
    print("legend: orange=DEVICE, light-orange=IP, blue=BUS, green=BREAKER, "
          "purple=ZONE, grey=LLM-extracted concept")


if __name__ == "__main__":
    main()
