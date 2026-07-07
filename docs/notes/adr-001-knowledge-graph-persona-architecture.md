# ADR-001 — Knowledge-graph structure vs. persona differentiation

**Status:** Accepted (baseline) · persona-conditioned retrieval planned as an ablation
**Date:** 2026-07-06
**Decision owners:** Jiakai Tang (with advisor sign-off pending)

---

## Context

The contextualizer (Layer 3) must produce three role-specific narratives — OT Operator,
Data Scientist, Regulator — from a single anomaly event (IDS prediction + SHAP attribution).
The question raised: *should each persona have its own knowledge graph built from different
sources, or should there be one shared graph?*

The key realization is that "how is the graph built" and "how is the answer personalized" are
**three independent decisions**, not one:

1. **Graph construction** — one graph vs. three graphs.
2. **Retrieval** — one shared retrieval vs. persona-specific retrieval.
3. **Generation** — one shared prompt vs. three persona system prompts.

Conflating construction with retrieval is what made "one graph with per-persona bias" feel
unimplementable. Once separated, the design is clear.

## Options considered

- **Option A — one graph, one shared retrieval, three persona prompts.** The original proposal
  design: retrieve a single Multi-Domain Context Block once, reuse it for all three personas,
  differentiate only at the system prompt.
- **Option B — three dedicated graphs, one per persona, each from its own sources.** The IDS+SHAP
  output routes through a persona-specific contextualizer end to end.
- **Option C (chosen direction) — one graph as the single source of truth, personalized at
  retrieval *and* generation.** Shared "core incident" retrieval + persona-scoped supplementary
  retrieval, then persona-specific generation.

## Decision

**Adopt one knowledge graph. Reject three separate graphs (Option B). Ship Option A first as the
baseline, then add Option C's persona-conditioned retrieval as a measured ablation.**

## Why not three graphs (Option B)

The knowledge sources overlap heavily. Topology, the IEC-104 protocol reference, and the attack
taxonomy are needed by *all three* personas; only the leaf documents differ (playbooks→operator,
compliance→regulator, model card→data scientist). Building three graphs forces one of two bad
outcomes:

1. **Duplicate the shared topology** into every graph — creating three copies of the single
   source of truth that drift out of sync. This is a maintenance hazard and directly harms the
   **H (hallucination)** score, which is checked against that inventory.
2. **Sever the cross-domain edges** that were the entire justification for using a graph over
   vanilla vector RAG. The most valuable reasoning chains span personas
   ("this attack → this RTU → this feeder → this NERC CIP-008 reporting obligation"). Siloing the
   graph deletes those chains.

Worse, three graphs let the operator and regulator narratives ground on **different facts about
the same incident** — a credibility problem and a failure of cross-persona consistency.

Separate graphs are justified only when corpora are genuinely disjoint, very large, or separated
by access-control boundaries (e.g., the regulator legally must not see internal operator data).
None of these hold for a synthetic research prototype.

## Chosen design (Option C), concretely

- **One graph, single source of truth.** All KB docs ingest into one LightRAG graph.
- **Tag every document at ingest** with metadata: which persona(s) it serves and which CPAS
  dimension it supports (e.g., `personas: [regulator]`, `cpas: [R, A]`).
- **Two-part retrieval per anomaly event:**
  - *Shared core* — keyed on the incident itself (dst-IP → device, attack class, top SHAP
    features, topology neighborhood). Identical for all three personas → guarantees they agree on
    the facts. Protects **H** and **D**.
  - *Persona supplement* — filtered/up-weighted to the persona's tagged sources, with a
    persona-shaped query (operator → device/action vocabulary; regulator → reporting/compliance
    vocabulary). Also exploit LightRAG's retrieval mode: operator → *local* (specific device
    facts), regulator → *global* (community/policy summaries). Lifts **A** and **R** by giving
    each persona tight, relevant material without the other personas' noise.
- **Generation** — concatenate core + supplement → persona system prompt → synthesizer at
  temperature 0.

## Implementation caveat (LightRAG)

LightRAG's headline capability is dual-level (local/global) retrieval; its support for hard
*per-document metadata filtering* at query time is thinner than a dedicated vector store's. The
most LightRAG-native path to persona separation is therefore persona-shaped **queries** over the
one graph, plus post-filtering retrieved chunks by the source tags we store. Verify the exact
filtering API when building Phase 3 rather than assuming it.

## Rollout — do not over-build up front

1. **Baseline (Phase 3 as written):** Option A — one graph, one shared retrieval, three persona
   prompts. Get the pipeline working end to end first.
2. **Ablation (post-baseline):** add Option C's persona-conditioned retrieval and measure the CPAS
   delta versus the baseline.

This turns the architecture question into a **thesis result**: *"Does persona-specific retrieval
improve CPAS over a shared context block with persona prompts, and on which dimensions?"* Letting
the data answer is a stronger contribution than asserting a design.

## Consequences

- **Positive:** single source of truth; cross-domain reasoning preserved; factual consistency
  across personas; a clean, publishable ablation; no graph duplication.
- **Negative / to watch:** persona-conditioned retrieval adds retrieval calls and complexity;
  must ensure the shared core always contains the core incident facts so personas never diverge
  on ground truth; depends on LightRAG filtering behavior that needs verification.

## Related

- IMPLEMENTATION_PLAN.md — Phase 3 (§6, baseline) and Future Improvements (§11, this design).
