"""Export the LightRAG graph as a Gephi-ready GEXF (pre-styled) for a thesis figure.

Gephi opens GEXF with the viz namespace already applied — so this writes node
colors (by entity_type), sizes, and labels baked in. Download Gephi (free,
gephi.org), File -> Open -> rag_storage/graph_gephi.gexf, then run a layout
(ForceAtlas 2) and File -> Export -> PNG/SVG for the paper.

Run: conda run -n xai python scripts/export_gephi.py
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
GRAPHML = ROOT / "rag_storage" / "graph_chunk_entity_relation.graphml"
OUT = ROOT / "rag_storage" / "graph_gephi.gexf"

# same palette as the HTML viewer; canonical grid entities pop, concepts are grey
RGB = {"DEVICE": (230, 85, 13), "IP_ADDRESS": (253, 141, 60), "BUS": (49, 130, 189),
       "BREAKER": (49, 163, 84), "ZONE": (117, 107, 177), "VENDOR": (227, 119, 194)}
DEFAULT = (150, 150, 150)


def main() -> None:
    if not GRAPHML.exists():
        raise SystemExit(f"{GRAPHML} not found — ingest the KB first")
    g = nx.read_graphml(GRAPHML)

    for node, d in g.nodes(data=True):
        etype = d.get("entity_type", "?")
        r, gr, b = RGB.get(etype, DEFAULT)
        d["label"] = node                        # Gephi node label
        d["viz"] = {"color": {"r": r, "g": gr, "b": b, "a": 1.0},
                    "size": 30.0 if etype in RGB else 12.0}
    for _, _, d in g.edges(data=True):
        d["label"] = d.get("keywords", "")       # relationship type as edge label

    nx.write_gexf(g, OUT)
    print(f"wrote {OUT}  ({g.number_of_nodes()} nodes, {g.number_of_edges()} edges)")
    print("Gephi: File -> Open this .gexf (already colored by entity_type), run "
          "ForceAtlas 2, then File -> Export -> PNG/SVG.")


if __name__ == "__main__":
    main()
