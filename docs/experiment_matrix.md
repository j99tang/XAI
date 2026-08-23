# Experiment design matrix (§7.7 / D34)

Which model fills which slot, across the ceiling run and the capability sweep.
Companion to `docs/model_map.md` (what each slot does) and D34/D38/D39.

---

## Matrix 0 — the principle that decides which slots may use a frontier model

The pivot argument (§7.7) is about **runtime** connectivity, not about models in general:
a unidirectional gateway permits egress only, and an API call needs a returned response.
That constraint binds only what runs when an alert fires. Anything built once, offline,
and shipped to site is unaffected — the same reasoning that lets the KB be authored with
Claude's help (D32).

| Slot | Runs at | Needs to be locally deployable? | Why |
|---|---|---|---|
| KB authoring | build | **no** | one-off, offline, no operational telemetry leaves site |
| Graph extractor | build | **no** | one-off; the graph is a shipped artifact |
| **Embedder** | build **AND runtime** | **YES** | `retrieve_context` embeds the *query* per alert — a hosted embedder is a runtime API call |
| **Synthesizer** | runtime | **YES** | the system under test |
| Judge | never deployed | n/a | measurement instrument, not part of the product |

The embedder is the slot most likely to be got wrong: it looks like build-time
infrastructure, but query embedding happens on every alert.

---

## Matrix 1 — the run plan

**Controlled-experiment rule (corrected 2026-08-22).** The ceiling run and every sweep run
differ in **exactly one thing: the synthesizer model.** Graph, embedder, retrieval settings,
`max_chars`, scenario set, rubric, judge, and all scripts are identical across every row.

An earlier version of this matrix had row 0 on the 8B-built graph and rows 1-4 on a
frontier-built graph — two variables between the anchor and the ceiling, which makes the
primary comparison uninterpretable. Graph quality is now an OPTIONAL side-experiment run
afterwards, explicitly not part of the sweep.

**Graph decision (2026-08-22): all rows share the EXISTING 8B-built `rag_storage/`.**
Free and available now. **Limitation to state in the thesis:** the ceiling is therefore
"best synthesizer on an 8B-extracted graph" — headroom lost to weak entity/relation
extraction is invisible, so the ceiling *understates* what the architecture can do. It is a
lower bound on the ceiling, which is the safe direction for the argument.

| # | Run | Graph | `max_chars` | **Synthesizer** (the ONLY variable) | Judge |
|---|---|---|---|---|---|
| 0 | Anchor (local) | existing 8B-built | 9,000 | `llama3.1:8b` via **local Ollama** | claude-opus-5 |
| 1 | **Ceiling** | " | " | `openai/gpt-5.5` | " |
| 2 | Sweep — large open (MoE) | " | " | `qwen/qwen3-235b-a22b-2507` | " |
| 3 | Sweep — ~70B open | " | " | `meta-llama/llama-3.3-70b-instruct` | " |
| 4 | Sweep — ~30B open | " | " | `qwen/qwen3-32b` | " |
| 5 | **Hosting control — 8B open** | " | " | `meta-llama/llama-3.1-8b-instruct` | " |

Embedder is `nomic-embed-text` (768-d, local) on every row — it is the one slot that runs at
BOTH build and runtime (query embedding per alert), so it must stay local for the deployment
claim to hold. See Matrix 0.

**Model ids and prices confirmed against OpenRouter's live catalogue 2026-08-22** (421 models),
not quoted from memory. All are non-Anthropic, so `assert_independent_of()` passes against the
`claude-opus-5` judge.

| row | $/1M in | $/1M out | est. synthesizer cost/run (90 generations) |
|---|---|---|---|
| 1 `openai/gpt-5.5` | 5.00 | 30.00 | ~$2.10 |
| 2 `qwen/qwen3-235b-a22b-2507` | 0.09 | 0.55 | ~$0.04 |
| 3 `meta-llama/llama-3.3-70b-instruct` | 0.10 | 0.32 | ~$0.03 |
| 4 `qwen/qwen3-32b` | 0.08 | 0.28 | ~$0.03 |
| 5 `meta-llama/llama-3.1-8b-instruct` | 0.05 | 0.08 | ~$0.01 |

**Total synthesizer spend for the whole programme: under $3.** The judge dominates
(~$15-23/run x 6). ~$10 of OpenRouter credit is sufficient.

**Row 5 is a hosting control, not just another size tier.** It runs the SAME WEIGHTS as row 0
(`llama-3.1-8b`) but through OpenRouter instead of local Ollama. It answers the honesty gap in
D34 — that open weights are being tested *over a cloud API* in order to argue for on-prem
deployment. If rows 0 and 5 score alike, the objection is settled empirically for about one
cent. If they diverge, that is itself worth knowing before any deployment claim is made.

**Ceiling is `gpt-5.5`, not `gpt-5.5-pro`** ($30/$180, ~$12/run — affordable, but the `-pro`
variants behave differently enough that the ceiling is better as a clean frontier datapoint
than a maximally expensive one).

### Blockers that must clear BEFORE row 0 is regenerated or row 1 is run
1. **`max_chars` must be settled (D41).** At 9,000 the CIP rule reaches the model in 0/30
   scenarios. Running the ceiling under that constant would score a frontier model badly on
   the regulator persona for reasons unrelated to its capability — corrupting the very
   reference every other row is compared against. Cap is swept on the FINAL graph, since
   a different graph retrieves different content.
2. **Credentials + a non-Claude model id.** The judge is `claude-opus-5`, so the synthesizer
   must never be `anthropic/claude-*`; `assert_independent_of()` hard-fails the run.
3. **Row 0 regenerated under the settled cap**, so the anchor and the ceiling share it.

### Constraints that must hold on every row
- **Synthesizer vendor != judge vendor**, enforced in code.
- **Embedder frozen** at `nomic-embed-text` (768-d); changing it forces a full re-index.
- **Judge frozen.** It is the ruler; judge variation is a separate appendix (Matrix 3).
- **Scenario set frozen** at the 30 stratified scenarios (D37); `report.py` refuses to run
  on a fingerprint mismatch (D38).
- **`max_chars` frozen** once chosen — it is a silent, powerful confound (D41).

### Open-weights selection: verify before committing
Pick 3-4 spanning roughly 8B -> 30B -> 70B so the sweep locates a **threshold** rather than
comparing two points. Confirm ids against OpenRouter's current catalogue at run time; do not
hard-code ids from memory. Criteria: genuinely open weights (self-hostable), spread across
capability tiers, and at least one runnable on the target hardware (row 0 is that anchor).

Honesty note: rows 1-4 run through OpenRouter, a cloud API, to argue for on-prem deployment.
The API is experimental convenience; the weights are self-hostable, which is the actual
claim. Row 0 is the proof that the local path executes.

## Matrix 2 — cost and scale per run

30 scenarios x 3 tiers x 3 personas = 270 narratives; x3 judge repeats = **810 judge calls**.
Only tier C costs synthesizer calls (A and B are deterministic string formatting).

| Quantity | Per run | Full programme (7 rows) |
|---|---|---|
| Synthesizer calls (tier C only) | 90 | 630 |
| Graph retrievals | 30 | 210 |
| Judge calls (Batch API, 50% off) | 810 | 5,670 |
| Judge prompt size | ~1,375 tok in | — |
| Narrative files written | 270 | 1,890 |

Judge cost dominates and is the same for every row, so adding a sweep model costs one
batch. Batch API is a textbook fit here: independent calls, not latency-sensitive.

---

## Matrix 3 — judge sensitivity (separate appendix, NOT part of the sweep)

Freeze ONE narrative set (the ceiling run's), score it with several judges, report whether
the tier ordering survives. This validates the instrument; it is not a result about the
system.

| Judge | Role | Independence check |
|---|---|---|
| `claude-opus-5` | primary | ok if synthesizer is not Claude |
| GPT-5-class | secondary | **invalid if the ceiling synthesizer was GPT** — pick a different pair |
| Gemini-class | secondary | ok |
| Human (you, ~20 narratives) | **the one a committee will ask for** | n/a |

The human-agreement check is the highest-value item here: hand-score ~20 narratives on
the same 1-5 anchors and report Spearman / Krippendorff's alpha against the primary judge.
Twenty narratives is an afternoon and it converts "an LLM said so" into a validated
instrument. Nothing else in this programme substitutes for it.

---

## Reading the outcome

Per D34 the goal is to **locate a capability threshold**, not to prove generalization:

| Result | Reading |
|---|---|
| Small open model already shows A<B<C | strong deployment story; framework generalizes |
| Only ~70B+ clears it | concrete minimum on-prem spec — actionable for the OT audience |
| No open model clears it, ceiling does | genuine negative finding: context grounding needs capability current air-gappable models lack |
| Even the ceiling fails | the framework, scenario set, or rubric is at fault — not the models |

Every outcome is publishable under this framing. Significance is a paired Wilcoxon,
**paired by scenario with personas averaged within** (n=30, not 90 — D38).
