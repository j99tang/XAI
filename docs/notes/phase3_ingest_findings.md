# Phase 3 — Ingestion & §3.1b graph-verification findings

Date 2026-07-07. Local stack: Ollama `llama3.1:8b` (LLM, temp 0) +
`nomic-embed-text` (768-dim). Graph in `rag_storage/`.

## What was built (Layer 3 code, `src/ccir/contextualizer/`)
- `rag.py` — shared LightRAG config (one place for models + storage).
- `ingest.py` — builds the graph from `knowledge_base/*.md` (§3.1). Run once.
- `retrieve.py` — `AnomalyEvent` → query → Multi-Domain Context Block (retrieve once).
- `synthesize.py` — context block → 3 persona narratives (temp 0).
- `configs/personas/{operator,data_scientist,regulator}.md` — system prompts with
  the anti-hallucination + evidence-boundary guardrails (§3.4).

## Bug fixed: embedding dimension mismatch (768 vs 1024)
LightRAG's `lightrag.llm.ollama.ollama_embed` is pre-decorated with
`embedding_dim=1024` (sized for bge-m3), which fights nomic's true 768 and halts
the pipeline mid-ingest. Fix: bypass that helper — call Ollama directly and wrap
in a single `EmbeddingFunc(embedding_dim=768)` (see `rag.py:_embed`). Symptom to
recognize: "total elements (768) cannot be evenly divided by expected dimension
(1024)". Also: a partially-built `rag_storage/` must be wiped before a clean
re-ingest (`find rag_storage -type f -delete`).

## §3.1b verification — the graph quality finding
Ingest succeeded: 8 chunks, **98 entities, 79 relationships**.

**Good:** naming is *consistent* — `RTU-3`, `SCADA-1` appear once, no
"RTU-3" vs "RTU 3" duplicates. The `entities.yaml` discipline held where entities
were extracted.

**Weak (the real finding):** the 8B model **under-extracted** the systematic
fine-grained entities. It created generic `RTU`/`RTUs` nodes, individuated only
`RTU-3` (not RTU-1/2/4), and extracted **zero breakers** and **no individual
buses**. This is a known small-model limitation: LLM graph extraction captures
salient concepts, not exhaustive tables.

**Retrieval impact (measured):** for a starvation-pattern flow to 10.0.0.5, the
context block correctly surfaces `RTU-3`, `starvation`, `visibility` — enough for
a correct narrative (the A3 acceptance "block contains the correct device name"
passes). But it **misses the exact `10.0.0.5` and `Bus 6`** rows — a precision gap
from the sparse graph.

## Remediation options (decide before Phase 4, don't over-build now)
1. **Pre-seed the graph from `entities.yaml`** via LightRAG custom-KG insertion —
   the principled fix: we *have* canonical entities, inject them deterministically
   instead of hoping an 8B model re-extracts them. (Most aligned with §2.9.)
2. **Stronger extraction model** (plan §7.5 escalation) — bigger local or API
   model for ingest only; retrieval/synthesis can stay local.
3. **Accept + tune retrieval** (raise top_k / mode=mix) if narratives score fine on
   CPAS regardless — test in Phase 4 before investing in 1 or 2.

Recommendation: try (3) first (free), escalate to (1) if the missing IP/bus hurts
CPAS D/H. Re-run `ingest.py` + re-check this file after any change.
