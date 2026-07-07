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

## CRITICAL finding — first end-to-end synthesis run (synthesize_demo.log)
Ran the 3-persona demo on a flood/starvation-pattern flow to 10.0.0.5. The
pipeline executes cleanly but **output quality is poor** — two failures:

1. **Persona collapse:** all three narratives were byte-for-byte identical. The
   distinct system prompts had *no* effect — llama3.1:8b, given a ~44k-char
   context block, ignored the persona role and just summarized the context.
2. **Wrong + meta-polluted content:** instead of the starvation-on-RTU-3
   incident, it produced a generic "NERC CIP-008-6 and topology" summary and
   leaked KB scaffolding ("Phase 2", "CPAS dimensions", "LightRAG ingests").
   Root cause: `README.md` files were ingested as domain knowledge.

**Fixes / next steps (in priority order):**
- [x] Exclude README.md from ingestion (`ingest.py`) — removes meta-noise. **Requires re-ingest.**
- [ ] Shrink the context handed to the synthesizer (lower `top_k`/`chunk_top_k`,
      or cap chars) — a 44k block drowns an 8B model's instruction-following.
- [ ] Strengthen persona conditioning: repeat the role instruction in the *user*
      message (not just system), since 8B under-weights the system role.
- [ ] If persona collapse persists after the above → this is the plan §7.5
      trigger: escalate the synthesizer to a stronger model (API or larger local).
      The demo just gave the "human spot-check shows weakness" signal §7.5 asks for.

This is a genuine, expected checkpoint: the local-8B synthesizer is the weakest
link, and the plan pre-registered exactly this decision. Do NOT wire up Phase 4
scoring until the synthesizer produces distinct, incident-specific narratives.

## After the free fixes (re-ingest w/o README + top_k=12/8k cap + role in user turn)
**Persona collapse RESOLVED.** The three narratives are now distinct and
role-appropriate (synthesize_demo.log): operator gives switching actions, data
scientist analyzes features *and correctly states the evidence boundary*,
regulator assesses reportability. The free fixes worked for their target problem.

**New visible issue — entity hallucination (expected, diagnosed):** with the
context now small, the 8B model fills gaps by inventing plausible names:
- operator: "RTU-123 at Substation Alpha", breaker "B3-12" — NOT in entities.yaml
  (should be RTU-3 / BR-x-y). Direct cost of the §3.1b under-extraction: the graph
  has no IP→device→breaker nodes, so retrieval can't supply the real names.
- regulator: "within 24 hours" is WRONG (CIP-008 is 1 hour reportable / next-day
  attempt) and it leaked node-type meta ("...which is an organization/person").
- data scientist: evidence-boundary guardrail HELD (good), but MITRE ID mismatched.

**Conclusion:** free fixes did their job (distinct personas). Remaining accuracy
failures trace to the sparse graph, not the prompts. This is the decision point:
- **Option 1 (recommended): pre-seed the graph from `entities.yaml`** via LightRAG
  custom-KG insertion — deterministically inject RTU-1..4, buses, breakers, IPs so
  retrieval returns real names and the model stops inventing them. Not free (a
  build), but the principled §2.9-aligned fix and cheaper than model escalation.
- **Option 2: §7.5 model escalation** (API/larger model) — helps reasoning but does
  NOT fix missing facts; the graph would still lack the entities. Do after Option 1.
Recommend Option 1 next; keep 8B for now.

## After Option 1 (graph pre-seeding + deterministic device join) — RESOLVED
Two changes:
1. **`scripts/seed_graph.py`** — injects the canonical entities.yaml facts
   (devices, IPs, buses, breakers, zones: 46 entities / 47 relations) into the
   graph via `ainsert_custom_kg`. Run AFTER `ingest.py`. **New pipeline order:
   ingest → seed_graph.**
2. **Deterministic device join in `retrieve.py`** (`resolve_device`): the dst_ip
   is the network↔physical *join key* (plan §1) — a table lookup, not a semantic
   search. We resolve it directly from entities.yaml and prepend an authoritative
   DEVICE block, so the IP→device→bus→breaker chain is never left to LLM
   invention. (Also fixed: `max_total_tokens` re-budgeting was dropping seeded
   facts — replaced with a plain char cap.)

**Result (synthesize_demo.log):** all three personas now correctly name RTU-3,
10.0.0.5, Bus 6, and the real breakers BR-5-6/6-11/6-12/6-13. The "RTU-123"
hallucination is gone; the device grounding is 100% correct and deterministic.

**Residual (8B reasoning quality, NOT architecture — the §7.5 territory):**
- regulator still says "within 24 hours" (should be 1 hour reportable / next-day
  attempt) — facts are in the KB, the 8B model doesn't retrieve/use the precise
  timeline.
- data scientist loosely names features / attack type.
These are model-quality gaps; the device/topology grounding (Option 1's target)
is solved. Decide model escalation vs. accept-for-baseline separately, informed by
CPAS scores in Phase 4.
