# Figures

Regenerate all five: `conda run -n xai python scripts/make_figures.py`
(reads `experiments/results/*/cpas_scores.json`; no API cost).

| file | claim it carries | pairs with |
|---|---|---|
| `fig1_capability_gradient.png` | Context helps at every capability level; a gradient, not a threshold. Tiers A and B are flat at ~1.5 across all six models — and since those narratives are byte-identical between rows, that flatness doubles as an independent judge-consistency check. | T1 |
| `fig2_reliability_separates.png` | Raw substance is similar across models (3.02–4.04); the hallucination rate is not (38%→4%). Reliability, not eloquence, is the deployment constraint. | T1, T2 |
| `fig3_tier_ablation.png` | A<B<C by persona, floor vs ceiling. Shows the regulator flat at the 8B and transformed at the ceiling. | T3, T4 |
| `fig4_regulator_penalty.png` | Why the regulator is flat: raw 2.96 with H=73%, so λ·H erases the entire gain. The persona that gains most from context is the one most exposed to unreliability. | T3 |
| `fig5_lambda_sensitivity.png` | Model ordering is unchanged at λ = 0,1,2,3 — the conclusion does not depend on the pre-registered λ=2. | T6 |

## Architecture

| file | what it is |
|---|---|
| `fig0_architecture.png` | Five-stage pipeline in the style of LightRAG's Figure 1, but with **real content**: the RTU-3 trace from `docs/notes/worked_example.md`. Source passage → indexing → graph → persona-conditioned retrieval → role-specific narratives. |
| `trace_rtu3.png` | RTU-3's full one-hop neighbourhood (11 neighbours), edge labels are relation types. The detail view behind stage 3. |

Regenerate: `scripts/make_architecture_figure.py`, `scripts/trace_example.py [ENTITY]`

**House style** lives in `scripts/figstyle.py` — semantic `PALETTE` (blue = proposed
method, neutral = stock components, green = outcomes, gold = one callout per figure),
the rcParams preset (Arial/Helvetica stack, spines off, `svg.fonttype='none'` and
`pdf.fonttype=42` so vector text stays editable), and `finalize_figure()` which writes
PNG + PDF at dpi 300. `fig0` uses it; `fig1`–`fig5` and `graph.png` predate it and are
still styled ad hoc — worth unifying before the thesis.

Use the **PDF** in the written thesis (vector, live text, no resampling at print size)
and the PNG for slides.

**The figure argues two departures from stock LightRAG**, stated in its own footer:
a deterministic path running alongside LLM extraction (because the 8B under-extracted
IPs/buses/breakers and the synthesizer then invented device names), and
persona-conditioned retrieval rather than one shared query (because one ranking put the
CIP rule in 0/30 context blocks).

**The red callout is the slide's point.** "Loss of communication with an RTU means loss
of visibility and control of its breakers" is carried on the RTU-3→SCADA-1 *edge*, not
on any node — and it surfaces in the operator narrative as "main risk is loss of
view/control at Bus 6". That phrase is in no source table row and no node description.

## Knowledge graph

| file | what it is |
|---|---|
| `graph.html` | interactive: 153 entities, 134 relations; zoom/drag/hover for entity and relation descriptions. **Fully self-contained** — zero external requests, opens offline in any browser. |
| `graph.png` | static render for slides and print, where nobody can hover. Coloured = seeded from `entities.yaml`; grey = LLM-extracted. |

Regenerate: `conda run -n xai python scripts/view_graph.py`
Inspect one node's edges: `… scripts/view_graph.py RTU-3`

**Read the PNG as evidence, not decoration.** It shows two weakly-joined worlds: a
dense cluster of 46 seeded grid entities (56 internal edges) and 107 LLM-extracted
concepts (68 internal edges), joined by only **10 bridging edges** — and 9 of those
touch just SCADA-1 or RTU-3. The graph has **34 connected components and 18 isolated
nodes**. That is the 8B extractor's relation-building weakness made visible, and it is
why `seed_graph.py` exists (D-series remediation): without the injected entities there
would be no reliable device→bus→breaker chain at all.

It also bounds the "graph beats flat vector RAG" claim: multi-hop traversal from a
device into KB prose has very few paths available. Retrieval works (the §11.1 check
found the CIP rule in 30/30 regulator blocks) largely because entity *descriptions*
carry the facts, not because long relation chains are traversed.

## Suggested slide order

1. **fig1** — the headline. Two flat lines and one rising one.
2. **fig3** — break it out by role.
3. **fig4** — the surprise: the regulator *does* benefit; unreliability takes it back.
4. **fig2** — generalise it: reliability is what separates models.
5. **fig5** — pre-empt "why λ=2?" before it is asked.
