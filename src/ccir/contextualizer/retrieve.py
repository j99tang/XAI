"""Phase 3.2: AnomalyEvent -> one query -> the Multi-Domain Context Block.

Retrieve ONCE (graph dual-level retrieval), reuse the block for all three personas
— the efficiency claim in the proposal. Uses only_need_context so no generation
happens here; synthesis is a separate step.
"""
from __future__ import annotations

from lightrag import QueryParam

from ccir.schemas.anomaly_event import AnomalyEvent


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


async def retrieve_context(rag, ev: AnomalyEvent, mode: str = "hybrid") -> str:
    """The shared context block. mode='hybrid' uses both local (entity) and global
    (theme) graph retrieval — the reason a graph beats flat vector RAG here."""
    param = QueryParam(mode=mode, only_need_context=True)
    return await rag.aquery(event_to_query(ev), param=param)
