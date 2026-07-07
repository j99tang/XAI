"""Phase 3.2: AnomalyEvent -> one query -> the Multi-Domain Context Block.

Retrieve ONCE (graph dual-level retrieval), reuse the block for all three personas
— the efficiency claim in the proposal. Uses only_need_context so no generation
happens here; synthesis is a separate step.
"""
from __future__ import annotations

import ipaddress

import yaml
from lightrag import QueryParam

from ccir.contextualizer.rag import KB_DIR
from ccir.schemas.anomaly_event import AnomalyEvent

_ENTITIES = None


def resolve_device(ip: str) -> str:
    """Deterministic IP→device lookup from entities.yaml (the authoritative join
    key — a table join, NOT a semantic search). Returns an authoritative fact
    block, so the synthesizer never has to invent device/bus/breaker names."""
    global _ENTITIES
    if _ENTITIES is None:
        _ENTITIES = yaml.safe_load((KB_DIR / "entities.yaml").read_text())
    for d in _ENTITIES["devices"]:
        if d["ip"] == ip:
            loc = f", at Bus {d['bus']}" if d["bus"] else ""
            brk = (", controls breakers " + ", ".join(d["controls_breakers"])) if d["controls_breakers"] else ""
            return (f"DEVICE (authoritative, from IP map): {ip} = {d['id']}, {d['role']}, "
                    f"zone {d['zone']}{loc}{brk}.")
    for r in _ENTITIES["external_ranges"]:
        if "cidr" in r and ipaddress.ip_address(ip) in ipaddress.ip_network(r["cidr"]):
            return f"DEVICE (authoritative): {ip} is not a grid asset — {r['label']}."
        if ip in r.get("ips", []):
            return f"DEVICE (authoritative): {ip} is not a grid asset — {r['label']}."
    return f"DEVICE (authoritative): {ip} is not in the IP→device map."


def event_to_query(ev: AnomalyEvent) -> str:
    """Turn the event into a natural-language retrieval query: the SHAP features
    (network evidence) + the destination IP (join key to device/grid)."""
    feats = ", ".join(f"{f.name} (SHAP {f.shap:+.2f}, value {f.value:g})"
                      for f in ev.top_features)
    return (
        f"An IDS flagged a network flow to {ev.dst_ip} on port {ev.dst_port} as "
        f"'{ev.prediction}' with confidence {ev.confidence:.2f}. The most influential "
        f"flow features were: {feats}. "
        f"What device is {ev.dst_ip}, what attack does this feature pattern indicate, "
        f"and what is the physical consequence and required response?"
    )


async def retrieve_context(rag, ev: AnomalyEvent, mode: str = "hybrid",
                           top_k: int = 12, max_chars: int = 9000) -> str:
    """The shared context block. mode='hybrid' uses both local (entity) and global
    (theme) graph retrieval — the reason a graph beats flat vector RAG here.

    Keep it moderate: a 44k block drowns an 8B model's instruction-following
    (persona-collapse), but the token-budget knob (max_total_tokens) re-selects
    content and drops the seeded device/IP/bus facts — so we cap by CHARACTERS
    after retrieval, not by token budget during it. The IP→device→bus chain sits
    near the top of the block, so a 9k char cap keeps it while trimming the tail."""
    param = QueryParam(mode=mode, only_need_context=True, top_k=top_k, chunk_top_k=top_k)
    rag_block = await rag.aquery(event_to_query(ev), param=param) or ""
    # Prepend the authoritative device resolution (deterministic join) so the
    # network→physical link is never left to semantic retrieval / LLM invention.
    device = resolve_device(ev.dst_ip)
    return f"{device}\n\n{rag_block[:max_chars]}"
