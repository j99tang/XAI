"""Extract every string and number the pipeline demo shows -> docs/demo/demo_data.js. No API cost.

The animation (docs/demo/pipeline_demo.html) contains no hand-typed data: it renders this
file. Each claim the video makes is asserted here, so a re-ingested graph or a re-run row
makes the build fail loudly instead of leaving a video that no longer matches the repo.

Sizes and chunk counts come from rag_storage (what the graph was actually BUILT from),
not from the files on disk, which can be edited after ingestion.

Run: conda run -n xai python scripts/make_demo_data.py
     (Ollama is needed only when docs/demo/contexts/ is empty: retrieval is cached there.)
"""
from __future__ import annotations

import asyncio, json, re, sys
from pathlib import Path

import joblib
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from caie.contextualizer.rag import LLM_MODEL  # noqa: E402
from caie.contextualizer.retrieve import (evidence_block, event_to_query,  # noqa: E402
                                          resolve_device, retrieve_context)
from caie.schemas.anomaly_event import AnomalyEvent  # noqa: E402

SCEN, RUN = "scenario_25", "openai-qwen-qwen3.8-27b"
PERSONAS = ["operator", "data_scientist", "regulator"]
RAG, OUT = ROOT / "rag_storage", ROOT / "docs" / "demo"
CTX = OUT / "contexts"
FOCUS, REG = "RTU-2", "NERC CIP-008-6"

# (file, category, how it was made, [(origin badge, substring that must appear in the file)])
DOCS = [
    ("attacks.md", "attack taxonomy", "paraphrased",
     [("SANDI-2024 dataset", "SANDI-2024 dataset paper"), ("MITRE ATT&CK for ICS", "MITRE ATT&CK for ICS")]),
    ("flow_features.md", "feature dictionary", "paraphrased", [("CICFlowMeter", "CICFlowMeter")]),
    ("ieee14_grid.md", "topology", "generated", [("IEEE 14-bus (pandapower)", "pandapower `case14`")]),
    ("ip_device_map.md", "topology", "authored",
     [("SANDI-2024 dataset", "read off the captures")]),
    ("power_flow_basics.md", "physics", "paraphrased",
     [("IEEE 14-bus (pandapower)", "pandapower docs"), ("von Meier textbook", "von Meier")]),
    ("operator_response.md", "playbook", "paraphrased",
     [("NIST SP 800 / CSF", "NIST SP 800-61r3")]),
    ("compliance.md", "compliance", "paraphrased",
     [("NERC CIP-008-6", "NERC CIP-008-6"), ("NIST SP 800 / CSF", "NIST CSF 2.0")]),
]

# (persona, phrase shown highlighted, lane it traces to, probes that must be in that lane)
TRACES = [
    ("operator", "RTU-2 (GridCom GC-4000), ZONE-C, Bus 4", "join", ["RTU-2", "GridCom GC-4000", "ZONE-C", "Bus 4"]),
    ("operator", "BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9", "join", ["BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9"]),
    ("operator", "Bwd IAT Min 0, Flow IAT Min 295", "evidence", ["Bwd IAT Min", "295"]),
    ("data_scientist", "Bwd IAT Min=0 (+0.063)", "evidence", ["Bwd IAT Min", "+0.063"]),
    ("data_scientist", "flood/scan or pure signalling behavior", "retrieved", ["flood/scan"]),
    ("data_scientist", "only a mild signal, not a leak", "retrieved", ["mild signal"]),
    ("regulator", "an IEC-104 controlled station and BES Cyber Asset under NERC CIP", "join",
     ["IEC-104 controlled station", "BES Cyber Asset under NERC CIP"]),
    ("regulator", "by the end of the next calendar day", "retrieved", ["next calendar day"]),
    ("regulator", "Notify E-ISAC", "retrieved", ["E-ISAC"]),
    ("regulator", "functional impact, attack vector, and level of intrusion", "retrieved", ["functional impact"]),
]


def layout(g: nx.Graph, comps: list[set]) -> dict:
    """Spring layout per component, packed: the two big islands side by side, the rest in a
    grid underneath. One global spring layout smears 34 components into soup."""
    pos = {}

    def place(nodes, x0, y0, w, h):
        sub = g.subgraph(nodes)
        p = nx.spring_layout(sub, seed=42, k=1.6 / max(len(sub), 1) ** 0.5, iterations=200)
        xs, ys = [v[0] for v in p.values()], [v[1] for v in p.values()]
        sx, sy = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        for n, (x, y) in p.items():
            pos[n] = (round(x0 + w * (x - min(xs)) / sx, 4) if len(sub) > 1 else x0 + w / 2,
                      round(y0 + h * (y - min(ys)) / sy, 4) if len(sub) > 1 else y0 + h / 2)

    place(comps[0], .03, .08, .44, .58)
    place(comps[1], .56, .08, .40, .50)
    cols = 16
    for i, c in enumerate(comps[2:]):
        place(c, .03 + (i % cols) * .06, .76 + (i // cols) * .12, .04, .08)
    return pos


async def contexts(ev) -> dict:
    """Retrieval is cached because the scored runs did not persist their context blocks:
    what is shown is a RE-retrieval for the same scenario, saved so it can be inspected."""
    CTX.mkdir(parents=True, exist_ok=True)
    paths = {p: CTX / f"{SCEN}_{p}.txt" for p in PERSONAS}
    if not all(f.exists() for f in paths.values()):
        from caie.contextualizer.rag import build_rag
        rag = await build_rag()
        for p, f in paths.items():
            f.write_text(await retrieve_context(rag, ev, p))
    return {p: f.read_text() for p, f in paths.items()}


def main() -> None:
    ev = AnomalyEvent.from_dict(json.loads(
        (ROOT / "experiments/scenarios" / f"{SCEN}.json").read_text())["anomaly_event"])
    res = ROOT / "experiments" / "results" / RUN

    # ---- knowledge base, as ingested
    status = {v["file_path"]: v for v in json.loads((RAG / "kv_store_doc_status.json").read_text()).values()}
    full = {v["file_path"]: v["content"] for v in json.loads((RAG / "kv_store_full_docs.json").read_text()).values()}
    chunks = json.loads((RAG / "kv_store_text_chunks.json").read_text())
    assert set(status) == {d[0] for d in DOCS}, f"ingested docs changed: {sorted(status)}"
    docs = []
    for name, cat, made, origins in DOCS:
        for badge, needle in origins:
            assert needle in full[name], f"{name} no longer cites {needle!r}"
        docs.append({"name": name, "category": cat, "made": made, "origins": [o[0] for o in origins],
                     "chars": int(status[name]["content_length"]), "chunks": int(status[name]["chunks_count"])})
    doc_chunks = sum(d["chunks"] for d in docs)
    # Document chunks are keyed "doc-<id>-chunk-NNN"; the rest are the one-line facts that
    # scripts/seed_graph.py inserted, which are NOT pieces of the seven documents.
    seeds = [c for key, c in chunks.items() if "-chunk-" not in key]
    assert doc_chunks + len(seeds) == len(chunks), (doc_chunks, len(seeds), len(chunks))
    seed_fact = next(c["content"] for c in seeds if c["content"].startswith(f"{FOCUS} has IP"))
    table = [l for l in full["ip_device_map.md"].splitlines() if l.startswith("| IP | Device | Zone") or f"| {FOCUS} |" in l]
    assert len(table) == 2, table

    # ---- graph
    g = nx.read_graphml(RAG / "graph_chunk_entity_relation.graphml")
    comps = sorted(nx.connected_components(g), key=len, reverse=True)
    assert FOCUS in comps[0] and REG in comps[1], "island membership changed"
    assert not nx.has_path(g, FOCUS, REG), "device and regulation are now CONNECTED: the 'joined in context' beat is false"
    seeded = lambda d: d.get("file_path") == "custom_kg"
    pos, ids = layout(g, comps), {n: i for i, n in enumerate(g)}
    comp_of = {n: i for i, c in enumerate(comps) for n in c}
    ego = [{"id": m, "kw": g[FOCUS][m].get("keywords", ""), "seeded": seeded(g[FOCUS][m]),
            "src": g[FOCUS][m].get("file_path", "")} for m in g[FOCUS]]
    assert any(not e["seeded"] for e in ego) and any(e["seeded"] for e in ego)

    # ---- contexts and what was retrieved
    ctx = asyncio.run(contexts(ev))
    join, evidence = resolve_device(ev.dst_ip), evidence_block(ev)
    head = f"{join}\n\n{evidence}\n\n"
    retrieval = {}
    for p, t in ctx.items():
        assert t.startswith(head), f"{p}: cached context does not match the current join/evidence"
        ents = re.findall(r'^\{"entity": "([^"]+)"', t, re.M)
        retrieval[p] = {"entities": ents, "ids": [ids[e] for e in ents if e in ids],
                        "relations": len(re.findall(r'^\{"entity1": ', t, re.M)),
                        "chunks": t.count('"reference_id"'), "chars": len(t),
                        "capped": len(t) - len(head) >= 9000}

    # ---- narratives, traces, scores
    rows = [r for r in json.loads((res / "cpas_scores.json").read_text())["rows"] if r["scenario"] == SCEN]
    narr = {}
    for p in PERSONAS:
        text = (res / f"{SCEN}_C_{p}.txt").read_text().strip()
        hl = []
        for q, phrase, lane, probes in TRACES:
            if q != p:
                continue
            assert phrase in text, f"{p}: narrative no longer says {phrase!r}"
            lane_text = {"join": join, "evidence": evidence, "retrieved": ctx[p][len(head):]}[lane]
            for pr in probes:
                assert pr.lower() in lane_text.lower(), f"{p}: {pr!r} not found in the {lane} lane"
            src = {"join": "table lookup (entities.yaml)", "evidence": "alert + SHAP"}.get(lane) or next(
                (n for n, c in full.items() if probes[0].lower() in c.lower()), "graph description")
            hl.append({"phrase": phrase, "lane": lane, "source": src})
        sc = {r["tier"]: round(r["cpas"], 2) for r in rows if r["persona"] == p}
        assert all(r["H"] == 0 for r in rows if r["persona"] == p and r["tier"] == "C")
        narr[p] = {"text": text, "highlights": hl, "scores": sc}

    rf = joblib.load(ROOT / "models" / "ids_rf.joblib")
    data = {
        "scenario": SCEN, "model": json.loads((res / "manifest.json").read_text())["synth_model"],
        "alert": (res / f"{SCEN}_A_operator.txt").read_text().strip(),
        "kb": {"docs": docs, "origins": list(dict.fromkeys(o for d in docs for o in d["origins"])),
               "chars": sum(d["chars"] for d in docs), "chunks": doc_chunks, "seed_chunks": len(seeds),
               "table": table, "seed_fact": seed_fact, "extract_model": LLM_MODEL},
        "graph": {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "components": len(comps),
                  "pos": [[*pos[n], comp_of[n]] for n in g],
                  "links": [[ids[a], ids[b], int(seeded(d))] for a, b, d in g.edges(data=True)],
                  "islands": [len(comps[0]), len(comps[1])], "focus": ids[FOCUS], "reg": ids[REG],
                  "focus_name": FOCUS, "reg_name": REG, "ego": ego},
        "event": {"src_ip": ev.src_ip, "dst_ip": ev.dst_ip, "dst_port": ev.dst_port,
                  "prediction": ev.prediction, "confidence": ev.confidence,
                  "features": [{"name": f.name, "value": f.value, "shap": f.shap} for f in ev.top_features]},
        "detector": {"trees": rf.n_estimators, "features": rf.n_features_in_, "classes": len(rf.classes_)},
        "join": join, "evidence": evidence, "query": event_to_query(ev, "regulator"),
        "retrieval": retrieval, "narratives": narr,
    }
    assert data["detector"]["classes"] == 2, "detector is no longer binary: revisit the 'attack or normal only' label"
    assert data["alert"] in evidence, "tier A alert is no longer a prefix of the evidence block"
    (OUT / "demo_data.js").write_text("window.DEMO = " + json.dumps(data, ensure_ascii=False) + ";\n")
    k = data["kb"]
    print(f"kb: {len(docs)} docs, {k['chars']} chars, {k['chunks']} chunks + {k['seed_chunks']} seeded facts")
    print(f"graph: {data['graph']['nodes']} nodes, {data['graph']['edges']} edges, {len(comps)} components; "
          f"islands {data['graph']['islands']}; no path {FOCUS} -> {REG}")
    for p in PERSONAS:
        r = retrieval[p]
        print(f"{p:15} retrieved {len(r['entities'])} entities, {r['relations']} relations, {r['chunks']} chunks "
              f"({r['chars']} chars, capped={r['capped']}); {len(narr[p]['highlights'])} traces; CPAS {narr[p]['scores']}")
    print(f"wrote {(OUT / 'demo_data.js').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
