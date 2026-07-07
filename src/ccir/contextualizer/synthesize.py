"""Phase 3.3-3.4: shared context block -> three persona narratives.

Retrieve the context ONCE (retrieve.py), then run the same block through three
system prompts at temperature 0 (reproducible). The persona prompts carry the
anti-hallucination and evidence-boundary guardrails (configs/personas/).

Run a demo on one attack flow:
  conda run -n xai python -m ccir.contextualizer.synthesize
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import ollama

from ccir.contextualizer.rag import LLM_MODEL, OLLAMA_HOST, ROOT, build_rag
from ccir.contextualizer.retrieve import retrieve_context
from ccir.schemas.anomaly_event import AnomalyEvent

PERSONA_DIR = ROOT / "configs" / "personas"
PERSONAS = ["operator", "data_scientist", "regulator"]


def synthesize_one(context: str, persona: str) -> str:
    system = (PERSONA_DIR / f"{persona}.md").read_text()
    client = ollama.Client(host=OLLAMA_HOST)
    resp = client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nWrite your briefing."},
        ],
        options={"temperature": 0},
    )
    return resp["message"]["content"].strip()


async def synthesize_all(ev: AnomalyEvent, rag=None) -> dict[str, str]:
    rag = rag or await build_rag()
    context = await retrieve_context(rag, ev)          # retrieve ONCE
    return {p: synthesize_one(context, p) for p in PERSONAS}  # reuse for all three


async def _demo() -> None:
    ev = AnomalyEvent(
        flow_id="121.142.26.78-10.0.0.5-7774-2404-6",
        src_ip="121.142.26.78", dst_ip="10.0.0.5", dst_port=2404,
        prediction="attack", confidence=0.99,
        top_features=[],
    )
    from ccir.schemas.anomaly_event import FeatureAttribution
    ev.top_features = [
        FeatureAttribution("Flow Packets/s", 4820.0, 0.19),
        FeatureAttribution("Flow IAT Std", 12.4, 0.15),
        FeatureAttribution("SYN Flag Count", 0.0, 0.08),
    ]
    out = await synthesize_all(ev)
    for p in PERSONAS:
        print(f"\n{'='*70}\n{p.upper()}\n{'='*70}\n{out[p]}")


if __name__ == "__main__":
    asyncio.run(_demo())
