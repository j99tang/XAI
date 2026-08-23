# Findings — Phase 4 complete (2026-08-23)

Thesis-ready distillation of `decision_log.md` (D24–D47), reorganised by theme rather
than chronology. Every number here is measured, with the producing script named.

---

## 1. Headline result

Six synthesizer models, identical in every other respect (same 30 scenarios, same
8B-built graph, same `nomic-embed-text` embedder, same per-persona retrieval at
`top_k=8`/`max_chars=9000`, same `claude-opus-5` judge at 3 repeats, same weights and
λ=2). **Only the synthesizer varies.**

| synthesizer | tier A | tier B | tier C | raw C | H rate | pass | C−A Δ | p |
|---|---|---|---|---|---|---|---|---|
| llama3.1:8b (local Ollama) | 1.51 | 1.59 | **2.48** | 3.14 | 33% | 54% | +0.96 | <.0001 |
| llama-3.1-8b (OpenRouter) | 1.51 | 1.61 | **2.27** | 3.02 | 38% | 49% | +0.75 | <.0001 |
| qwen3-32b | 1.50 | 1.60 | **2.86** | 3.40 | 27% | 71% | +1.37 | <.0001 |
| llama-3.3-70b | 1.50 | 1.60 | **3.15** | 3.46 | 16% | 77% | +1.65 | <.0001 |
| qwen3-235b-a22b | 1.48 | 1.62 | **3.29** | 3.62 | 17% | 86% | +1.81 | <.0001 |
| gpt-5.5 (ceiling) | 1.52 | 1.58 | **3.95** | 4.04 | 4% | 100% | +2.43 | <.0001 |

`raw C` = weighted D/C/A/R before the λ·H penalty. `pass` = raw ≥ 3.0.
p from paired Wilcoxon signed-rank, **paired by scenario** with personas averaged
within (n=30, not 90 — the three personas share a scenario and a context block, so
treating rows as independent would be pseudoreplication).

**A < B < C holds in all six rows, every comparison significant.** The framework works
at every capability level tested; the effect size scales (+0.75 → +2.43) but never
disappears.

### 1.1 Reliability, not capability, separates the models
Raw scores span 3.02 → 4.04 (a third). H spans 38% → 4% (nearly tenfold). Every model
can *say* approximately the right things; they differ in how often they assert something
false. For a control-room deployment that is the binding constraint — a briefer
explanation is tolerable, a wrong breaker or reporting clock is not.

The clearest instance: `qwen3-32b` raw 3.40 vs `llama-3.3-70b` raw 3.46 — nearly
identical substance — yet CPAS 2.86 vs 3.15, entirely from H (27% vs 16%).

### 1.2 A gradient, not a threshold
2.27 → 2.86 → 3.15 → 3.29 → 3.95, smooth, with diminishing returns above ~70B. More
useful than a cliff: every capability increment buys reliability, so a deployer can pick
a point on the curve against their risk tolerance rather than meet a hard bar.

### 1.3 The A→B step is real but tiny
+0.05 to +0.11 across rows. Raw SHAP helps only the data-scientist persona; operator and
regulator are flat (D39 gives no credit for reciting feature names to personas whose
briefs call them clutter). This is the "XAI alone is not enough — context is" argument,
measured rather than asserted.

### 1.4 Hosting control: API ≈ local, mildly pessimistic
Rows 0 and 5 run the **same weights** (`llama-3.1-8b`) locally vs through OpenRouter:
CPAS 2.48 vs 2.27, H 33% vs 38%, pass 54% vs 49%. Close, but the API run is consistently
slightly worse — most plausibly provider-side quantisation (the same routing variance
that truncated row 3 mid-run). **Statement for the thesis:** API-hosted open weights are
a reasonable proxy for self-hosted, and a *pessimistic* one — the safe direction for a
deployment claim.

### 1.5 Figures
`scripts/make_figures.py` -> `docs/figures/` (regenerable from `cpas_scores.json`):
- **fig1 capability gradient** — tier C rises smoothly 2.27 -> 3.95 while tiers A and B
  stay flat at ~1.5 across every model. The flat A/B lines are the strongest visual in
  the set: those narratives are byte-identical between rows, so their flatness is also
  an independent judge-consistency check.
- **fig2 reliability separates** — raw vs penalised bars beside the hallucination curve
  (38% -> 4%). Substance is similar across models; reliability is not.
- **fig3 tier ablation by persona** — floor vs ceiling side by side.

---

## 2. Methodology contribution — the strongest transferable result

Seven times the evaluation graded something the narrative was never given. Each was
caught by a **free** check before a paid one; each would have produced a plausible but
wrong finding.

| # | graded expectation | what the model actually had |
|---|---|---|
| D39 | correct attack class for D=5 | binary detector, never conveys class |
| D39 | C on false positives | anchor undefined for that case |
| D39 | R/A against a generic anchor | three incompatible persona deliverables |
| D40 | which SHAP features drove it | features never passed to the synthesizer |
| D41 | the one-hour CIP clock | rule truncated away (0/30 context blocks) |
| D45/46 | compromise-based reporting duty | evidence establishes attempt only |
| D47 | reportability | asset CIP scope absent from context |

**The rule:** *every graded expectation must be traceable to an input the narrative
actually receives.* Four of the seven were the rubric rewarding what the persona prompts
forbid — the grader contradicting the generator.

**Why it mattered financially and scientifically.** D45 would have reported a frontier
model as *worse* at regulatory reasoning than an 8B, because the careful model reasoned
"the detector does not establish compromise" while the careless one asserted the
retrieved figure. D40 would have reported "context makes the data scientist worse". Both
are directionally plausible enough to survive into a thesis unchallenged.

**Detection was cheap.** The D47 defect surfaced in a $0.07 smoke test whose stated
purpose was validating the JSON schema.

---

## 3. Robustness

**λ sensitivity** (`scripts/lambda_sweep.py`, no API cost). A<B<C holds at λ = 0, 1, 2, 3
in every row. λ=2 is pre-registered but admittedly "tunable", so the conclusion is stated
as robust to it rather than dependent on it. λ-sensitivity is itself a reliability
measure: the ceiling moves 4.18→4.08 across λ (H≈0) while the 8B moves 2.96→0.76.

**Judge sensitivity** (`scripts/judge_sensitivity.py`, n=20 blind sample, ~$0.50).
`gemini-3.1-pro-preview` vs `claude-opus-5`: Spearman ρ = D .888, C .796, A .891, R .987;
**H agreement 100%**; tier ordering survives (A 1.50 < B 1.59 < C 2.84). D shows 20%
exact but 100% within-1 with mean Δ +0.60 — a systematic offset, not disagreement, and
it cancels because CPAS compares tiers within one judge. The second judge was chosen to
be neither run's synthesizer; the script refuses a judge that authored narratives.

**Judge consistency, free.** Tiers A and B are byte-identical across all six rows and
scored 1.48–1.62 with H=0% everywhere — an independent check that the judge is stable
across batches.

---

## 4. Limitations — measured, not speculated

1. **The C dimension is structurally capped.** The simulated consequence is not in the KB
   or the `AnomalyEvent`, so no model can state it. Tier-C C-scores peak at 3.1 even at
   the ceiling, and ABSORBED scenarios outscore OVERLOAD (4.51 vs 3.27) because "no
   violation" is stateable from the evidence while "line 3 @ 102%" is not.
2. **Attack class is capped by a binary detector (D27).** `attack_class_correct` peaks at
   30% and barely improves with capability (8B 4/25, gpt-5.5 5/25). The lever is a
   multiclass detector, not a bigger model. Reported as a diagnostic, never in CPAS.
3. **H is not comparable across personas.** It fires only on five grounded fact types, so
   exposure varies by deliverable: data-scientist H=0% in *every* row (its brief asserts
   almost nothing H covers), regulator up to 73%. Comparable *within* a persona across
   models; not across personas. Pooling inherits the bias, which favours vagueness.
4. **The FP stratum is 1 false positive + 4 true negatives.** The constrained model never
   produces a confident false positive on this testbed (D24), so those 5 scenarios test
   *over-escalation on a low-confidence normal*, not false-positive recognition. Useful,
   but must be described accurately.
5. **CIP asset classifications are authored, not cited** (D47). Declared as synthetic
   overlay in `ip_device_map.md`; a real entity performs its own CIP-002 categorisation.
6. **Open-weights rows are not bit-reproducible.** OpenRouter routes across providers with
   differing quantisation, so temperature=0 is not deterministic there; one route ran away
   past `max_tokens` mid-row. Only row 0 (local Ollama) is reproducible.
7. **The ceiling is a lower bound.** All rows share the 8B-built graph, so headroom lost
   to weak entity/relation extraction is invisible. The ceiling understates the
   architecture — the safe direction.
8. **No human-agreement check yet.** Cross-judge agreement is not human validation: if
   models share a bias they agree with each other and human agreement stays unmeasured.
   `scripts/human_score.py` and the worksheet are ready; this is the outstanding gap.

---

## 5. Cost

| | |
|---|---|
| Judging — 4,860 calls, 6 rows, Batch API (50% off) | **$113.06** |
| Generation — 6 rows via OpenRouter | **$7.41** |
| **Total** | **$120.47** |

Per row: $18.28–$19.49. At list price the judging alone would be ~$226.

---

## 6. Outstanding

1. **Human-agreement check** — the one gap a committee will press on. Worksheet ready;
   even 5 items would catch a gross systematic divergence.
2. **Give the narrative the consequence** — would lift the C dimension's structural cap
   and remove the asymmetry between evidence-relative `reportable` and omniscient
   `physical_consequence` (D46 residual tension).
3. **Multiclass detector** — the only route to the attack-class dimension (D27).
4. **Graph-quality control** — row 0 vs a frontier-built graph, to separate the
   extractor's contribution from the synthesizer's. Deliberately outside the sweep.
