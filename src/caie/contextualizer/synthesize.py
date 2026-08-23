"""Phase 3.3-3.4: shared context block -> three persona narratives.

Retrieve the context ONCE (retrieve.py), then run the same block through three
system prompts at temperature 0 (reproducible). The persona prompts carry the
anti-hallucination and evidence-boundary guardrails (configs/personas/).

Run a demo on one attack flow:
  conda run -n xai python -m caie.contextualizer.synthesize

Synthesizer backend is pluggable (for the §7.5 "does a stronger model help?" test)
via env vars — local Ollama is the default so the baseline run is unchanged:
  CAIE_SYNTH_BACKEND=ollama   (default) — uses CAIE_LLM / OLLAMA_HOST from rag.py
  CAIE_SYNTH_BACKEND=openai   — any OpenAI-compatible endpoint (OpenRouter, Gemini
    compat, a hosted 70B, …). Set CAIE_SYNTH_MODEL, CAIE_SYNTH_BASE_URL
    (default OpenRouter), and CAIE_SYNTH_KEY (or in .env). Needs `pip install openai`.
Swapping the backend is the model-agnostic upgrade path — the AnomalyEvent contract
and everything downstream (judge, rubric) are unchanged.
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import ollama
from dotenv import load_dotenv

from caie.contextualizer.rag import LLM_MODEL, OLLAMA_HOST, ROOT, build_rag
from caie.contextualizer.retrieve import retrieve_all
from caie.schemas.anomaly_event import AnomalyEvent

load_dotenv(ROOT / ".env")

PERSONA_DIR = ROOT / "configs" / "personas"
PERSONAS = ["operator", "data_scientist", "regulator"]

SYNTH_BACKEND = os.environ.get("CAIE_SYNTH_BACKEND", "ollama")


def synth_model() -> str:
    """The synthesizer model id for the active backend."""
    if SYNTH_BACKEND == "ollama":
        return LLM_MODEL
    return os.environ.get("CAIE_SYNTH_MODEL", "unset")


def run_tag() -> str:
    """Filesystem-safe id for THIS synthesizer configuration.

    Every artifact (narratives, scores) is namespaced by it. Without this, the §7.7
    capability sweep would have each model silently overwrite the previous one's
    narratives and `cpas_scores.json` — a flat results/ directory has no model
    dimension, so N models produce 1 set of files.
    """
    return re.sub(r"[^a-z0-9.]+", "-", f"{SYNTH_BACKEND}-{synth_model()}".lower()).strip("-")


class TruncatedNarrative(RuntimeError):
    """The model hit its output ceiling mid-answer.

    Raised rather than returned because a truncated narrative is still a valid-looking
    .txt file: it would be written to disk, pass every completeness check, and be graded
    by the judge as a BAD EXPLANATION rather than a BROKEN RUN. Silent bad data is worse
    than a loud failure (the D38 lesson) — and on a reasoning model the failure is easy
    to hit, since internal reasoning tokens count against the same budget as the answer.
    """


# Generous enough for a reasoning model's internal reasoning PLUS a <=200-word answer.
# Not tight: on OpenRouter, `max_tokens` also sets the credit RESERVATION (worst-case
# cost), so leaving it unset reserved 65,536 tokens x $30/1M ~ $1.97 against a call that
# actually costs ~$0.023 — an 85x over-reservation that 402s on a low balance. Pinning it
# LOW would be worse: it would truncate reasoning models mid-answer. 4,000 cuts the
# reservation to ~$0.12 while leaving ample room.
MAX_OUTPUT_TOKENS = int(os.environ.get("CAIE_SYNTH_MAX_TOKENS", "4000"))


def _complete(system: str, user: str) -> str:
    """One chat completion at temperature 0. Dispatches on CAIE_SYNTH_BACKEND so
    the synthesizer model is a swappable variable while everything else is fixed."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if SYNTH_BACKEND == "ollama":
        resp = ollama.Client(host=OLLAMA_HOST).chat(
            model=LLM_MODEL, messages=messages,
            options={"temperature": 0, "num_predict": MAX_OUTPUT_TOKENS})
        if resp.get("done_reason") == "length":
            raise TruncatedNarrative(
                f"{LLM_MODEL} hit num_predict={MAX_OUTPUT_TOKENS}; narrative is cut off")
        return resp["message"]["content"].strip()
    if SYNTH_BACKEND == "openai":  # OpenRouter / any OpenAI-compatible endpoint
        from openai import OpenAI
        client = OpenAI(
            base_url=os.environ.get("CAIE_SYNTH_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=os.environ.get("CAIE_SYNTH_KEY") or os.environ.get("OPENROUTER_API_KEY", ""))
        model = os.environ["CAIE_SYNTH_MODEL"]
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS)
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            raise TruncatedNarrative(
                f"{model} hit max_tokens={MAX_OUTPUT_TOKENS}; narrative is cut off. "
                f"Raise CAIE_SYNTH_MAX_TOKENS — do NOT keep the partial text.")
        text = (choice.message.content or "").strip()
        if not text:
            raise TruncatedNarrative(
                f"{model} returned empty content (finish_reason={choice.finish_reason!r}); "
                f"an empty narrative must not reach the judge")
        return text
    raise ValueError(f"unknown CAIE_SYNTH_BACKEND={SYNTH_BACKEND!r} (use 'ollama' or 'openai')")


ROLE_LINE = {  # repeated in the USER turn: 8B under-weights the system role alone
    "operator": "You are the OT CONTROL-ROOM OPERATOR. Write ONLY the operator's "
                "action briefing — affected device, physical risk, next switching steps.",
    "data_scientist": "You are the DATA SCIENTIST. Write ONLY the model analysis — "
                      "which flow features drove the prediction and what they prove/can't prove.",
    "regulator": "You are the COMPLIANCE OFFICER. Write ONLY the regulatory assessment — "
                 "is it reportable, which timeline, to whom.",
}


# OpenRouter load-balances open-weights models across providers whose quantisation and
# sampling defaults differ, so temperature=0 is NOT fully deterministic there: the same
# request can return a normal 130-word brief on one route and run away past max_tokens on
# another. One bad route killed 17 scenarios into row 3. Retry rather than abort — but
# NEVER relax the guard: a truncated narrative must still never be written (D40).
SYNTH_RETRIES = 3


def synthesize_one(context: str, persona: str) -> str:
    system = (PERSONA_DIR / f"{persona}.md").read_text()
    user = (f"{ROLE_LINE[persona]}\n\nCONTEXT (use only these facts):\n{context}\n\n"
            f"Now write your role-specific briefing (<=200 words). "
            f"Do not summarize the knowledge base; analyze THIS incident.")
    last = None
    for attempt in range(SYNTH_RETRIES):
        try:
            return _complete(system, user)
        except TruncatedNarrative as e:
            last = e
            print(f"    retry {attempt+1}/{SYNTH_RETRIES} ({persona}): {e}", flush=True)
    raise last


async def synthesize_all(ev: AnomalyEvent, rag=None) -> dict[str, str]:
    """Persona-conditioned retrieval + synthesis (§11.1, D42).

    Each persona retrieves its own block, so the compliance rule ranks high for the
    regulator and the playbook ranks high for the operator. Previously one shared block
    was reused three times, which put the CIP timeline beyond every workable `max_chars`
    and left the regulator inventing a "24 hours" figure absent from the KB."""
    rag = rag or await build_rag()
    contexts = await retrieve_all(rag, ev, PERSONAS)
    return {p: synthesize_one(contexts[p], p) for p in PERSONAS}


async def _demo() -> None:
    ev = AnomalyEvent(
        flow_id="121.142.26.78-10.0.0.5-7774-2404-6",
        src_ip="121.142.26.78", dst_ip="10.0.0.5", dst_port=2404,
        prediction="attack", confidence=0.99,
        top_features=[],
    )
    from caie.schemas.anomaly_event import FeatureAttribution
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
