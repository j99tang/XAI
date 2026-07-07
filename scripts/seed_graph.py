"""Pre-seed the LightRAG graph with canonical entities from entities.yaml.

Phase 3 remediation (Option 1, plan §2.9): the 8B LLM under-extracts the
systematic fine-grained entities (IPs, buses, breakers), so retrieval can't
supply real names and the synthesizer invents them ("RTU-123"). We HAVE the
ground-truth entities — inject them deterministically via custom-KG insertion
instead of hoping the model re-extracts them.

Run AFTER ingest.py, against the same rag_storage:
  conda run -n xai python scripts/seed_graph.py
Then re-check retrieval / §3.1b.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from ccir.contextualizer.rag import KB_DIR, build_rag

ENTITIES = KB_DIR / "entities.yaml"


def build_custom_kg() -> dict:
    ents = yaml.safe_load(ENTITIES.read_text())
    entities: list[dict] = []
    relationships: list[dict] = []
    chunks: list[dict] = []
    seen_ent: set[str] = set()

    def add_entity(name: str, etype: str, desc: str, source: str) -> None:
        if name in seen_ent:
            return
        seen_ent.add(name)
        entities.append({"entity_name": name, "entity_type": etype,
                         "description": desc, "source_id": source})

    def rel(a: str, b: str, desc: str, kw: str, source: str) -> None:
        relationships.append({"src_id": a, "tgt_id": b, "description": desc,
                              "keywords": kw, "weight": 1.0, "source_id": source})

    # zones + vendor (shared topology chunk)
    topo_src = "seed:topology"
    chunks.append({"content": "Canonical device, IP, bus, breaker, and zone registry "
                              "for the IEEE 14-bus overlay (from entities.yaml).",
                   "source_id": topo_src, "file_path": "entities.yaml"})
    vendor = ents["vendor"]
    add_entity(vendor["name"], "VENDOR", f"RTU manufacturer; model {vendor['rtu_model']}", topo_src)
    for z in ents["zones"]:
        add_entity(z["id"], "ZONE", f"{z['name']} (buses {z['buses']})", topo_src)
        for bus in z["buses"]:
            add_entity(f"Bus {bus}", "BUS", f"Bus {bus} of the IEEE 14-bus grid, in zone {z['id']} ({z['name']})", topo_src)
            rel(f"Bus {bus}", z["id"], f"Bus {bus} is in {z['name']}", "topology zone", topo_src)

    # devices — one chunk each carrying its IP-map facts
    for d in ents["devices"]:
        did, ip = d["id"], d["ip"]
        src = f"seed:{did}"
        fact = (f"{did} has IP {ip}, role: {d['role']}, in zone {d['zone']}"
                + (f", located at Bus {d['bus']}" if d["bus"] else "")
                + (f", controls breakers {', '.join(d['controls_breakers'])}"
                   if d["controls_breakers"] else "") + ".")
        chunks.append({"content": fact, "source_id": src, "file_path": "topology/ip_device_map.md"})
        add_entity(did, "DEVICE", fact, src)
        add_entity(ip, "IP_ADDRESS", f"IP address of {did} ({d['role']})", src)
        rel(ip, did, f"{ip} is the IP address of {did}", "ip device mapping", src)
        add_entity(d["zone"], "ZONE", f"Zone containing {did}", src)
        rel(did, d["zone"], f"{did} is in zone {d['zone']}", "device zone", src)
        if d["bus"]:
            add_entity(f"Bus {d['bus']}", "BUS", f"Bus {d['bus']} of the IEEE 14-bus grid", src)
            rel(did, f"Bus {d['bus']}", f"{did} is located at Bus {d['bus']}", "device location", src)
        for br in d["controls_breakers"]:
            add_entity(br, "BREAKER", f"Circuit breaker {br} on the IEEE 14-bus grid", src)
            rel(did, br, f"{did} supervises breaker {br}", "device controls breaker", src)

    return {"chunks": chunks, "entities": entities, "relationships": relationships}


async def main() -> None:
    kg = build_custom_kg()
    print(f"seeding: {len(kg['entities'])} entities, {len(kg['relationships'])} relationships, "
          f"{len(kg['chunks'])} chunks")
    rag = await build_rag()
    await rag.ainsert_custom_kg(kg)
    print("done — re-check retrieval (dst_ip should now resolve to device + bus + breakers)")


if __name__ == "__main__":
    asyncio.run(main())
