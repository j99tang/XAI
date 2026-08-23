# Model map — which model runs where, and why

Every place this project uses a model, build-time and runtime. Written because the
system is easy to mis-describe: it is **not** a multi-agent system, and it is **not**
purely local.

## What kind of system this is

A **staged pipeline with two independent LLM roles** — one in-the-loop generator
(synthesis) and one out-of-loop evaluator (judge). Not multi-agent: no component
chooses its own next action, selects tools, loops, or messages another component.
Execution order is fixed and every stage's output is the next stage's input.

That determinism is load-bearing, not a limitation. If a model could choose its own
retrieval strategy, tier C's advantage would be confounded with agent behaviour and
the A/B/C ablation would not attribute cleanly to context.

## Build time (runs once, by a human with assistance)

```
references/source_library/*.pdf
        |
   [0a] kb_extract.py ................... NO MODEL (pymupdf text extraction)
        |                                 so authoring paraphrases the ACTUAL
        v                                 source text, never model memory
   extracted source text
        |
   [0b] Claude, via the kb-author skill .. HUMAN-IN-THE-LOOP, frontier model
        |    drafts KB prose per plan 2.9's provenance split:
        |      - machine-checkable facts -> GENERATED, never drafted
        |        (topology from pandapower, model card from metrics.json)
        |      - judgment prose -> LLM-drafted, then gated
        v
   knowledge_base/*.md   (8 files, ~26.6k chars)  +  entities.yaml
        |
   [0c] check_kb.py ..................... NO MODEL (5 mechanical consistency rules)
        |                                 prose rules decay, asserts don't
        v
   [1] nomic-embed-text (768-d, Ollama) .. embed chunks for vector recall
   [2] llama3.1:8b (Ollama, temp 0) ...... extract entities + relations
        |                                  (LightRAG ingest, rag.py)
        v
   rag_storage/  LightRAG graph
        ^
        |
   seed_graph.py ........................ NO MODEL. Injects canonical IPs / buses /
                                          breakers from entities.yaml because the 8B
                                          under-extracts them (D-series remediation).
```

## Runtime (per alert)

```
   raw flow record
        |
   RandomForest IDS ..................... ML, not GenAI (train.py)
   SHAP TreeExplainer ................... ML, not GenAI (explain.py)
        v
   AnomalyEvent  (the stable contract -- the swap point for every model below)
        |
        +---> resolve_device(ip) ........ NO MODEL. entities.yaml table join,
        |                                 NOT semantic search. This is why the
        |                                 synthesizer never has to invent a device.
        |
        +---> retrieve_context(ev, persona)  PER-PERSONA graph query (§11.1, D43)
        |     hybrid local+global, top_k=8, capped at 9,000 chars
        v
   THREE Multi-Domain Context Blocks, one per persona
   (the "retrieve once, reuse 3x" efficiency claim is forfeited -- D42/D43:
    one ranking could not serve three information needs, and the regulator's
    CIP rule reached the model in 0/30 scenarios)
        |
   [3] llama3.1:8b, temp 0 .............. THE SYSTEM UNDER TEST
        |    3 isolated completions, identical context, differing only by
        |    system prompt (configs/personas/*.md) + ROLE_LINE.
        |    Swappable: CAIE_SYNTH_BACKEND=openai + CAIE_SYNTH_MODEL.
        v
   3 persona narratives  (operator / data_scientist / regulator)
```

## Evaluation (out of loop)

```
   tier A (alert only) .................. NO MODEL
   tier B (alert + SHAP) ................ NO MODEL
   tier C (the above)                     <- only C involves a model
        |
        |   gold_facts <- make_fact_sheets.py .... NO MODEL, deliberately.
        |                 (entities.yaml + power-flow sim) The ground truth must
        |                 not be model-authored or the judge grades a model
        v                 against another model's guess.
   [4] claude-opus-5 (Anthropic, Batch API)
        |    blinded to tier, isolated per narrative, 3 repeats -> median.
        |    Different vendor and scale from the synthesizer: the independence
        |    rule -- a model must never grade its own output.
        v
   D/C/A/R/H + per-dimension reasons
        |
   cpas() ............................... NO MODEL, pure arithmetic
```

## Summary

| # | Stage | Model | When | Under test? |
|---|---|---|---|---|
| 0a | Source extraction | none (pymupdf) | build | no |
| 0b | KB authoring | Claude (kb-author skill) | build | no |
| 0c | KB gate | none (check_kb.py) | build | no |
| 1 | Chunk embedding | nomic-embed-text, 768-d | build | no |
| 2 | Entity/relation extraction | llama3.1:8b | build | no |
| 3 | Persona synthesis | llama3.1:8b (swappable) | runtime | **YES** |
| 4 | Scoring | claude-opus-5 | eval | no |

## Two honesty notes for the write-up

**The KB was authored with frontier-model assistance.** The runtime pipeline is
local-only, but its knowledge substrate was not written unaided. The defensible
claim is: *"KB documents were authored with LLM assistance from deterministically
extracted source text, with provenance enforced by a mechanical gate (`check_kb.py`);
the runtime pipeline uses only local models."* Do not claim a hand-written KB.

**The same 8B does [2] and [3].** A weakness compounds across two stages: what the
extractor fails to put in the graph, the synthesizer cannot retrieve. `seed_graph.py`
patches the entity half deterministically; relation quality is still 8B-limited.
Upgrading [3] alone therefore tests only half of "does a stronger model help?".
