# Presentation tables — CAIE Phase 4

All numbers measured. Regenerate with `scripts/make_presentation_tables.py`.
Judge: `claude-opus-5`, 3 repeats, median. Significance: paired Wilcoxon signed-rank,
**paired by scenario** with personas averaged within (n=30 — the three personas share a
scenario and a context block, so 90 rows are not 90 independent observations).

---

## T0 — Experimental design: what varies, what is held constant

| slot | value | varies? |
|---|---|---|
| scenarios | 30, stratified | frozen |
| knowledge graph | 8B-built `rag_storage/` | frozen |
| embedder | `nomic-embed-text` (768-d, local) | frozen |
| retrieval | per-persona, `top_k=8`, `max_chars=9000` | frozen |
| judge | `claude-opus-5` × 3 repeats | frozen |
| formula | w = D .30 / C .25 / A .25 / R .20, λ = 2.0 | frozen |
| **synthesizer** | **8 models** | **the only variable** |

---

## T1 — Capability sweep: CPAS by tier

| synthesizer | A | B | C | raw C | H rate | pass | C−A Δ | p |
|---|---|---|---|---|---|---|---|---|
| llama-3.1-8b (API) | 1.51 | 1.61 | **2.27** | 3.02 | 38% | 49% | +0.75 | <.0001 |
| llama3.1:8b (LOCAL) | 1.51 | 1.59 | **2.48** | 3.14 | 33% | 54% | +0.96 | <.0001 |
| qwen3-32b | 1.50 | 1.60 | **2.86** | 3.40 | 27% | 71% | +1.37 | <.0001 |
| llama-3.3-70b | 1.50 | 1.60 | **3.15** | 3.46 | 16% | 77% | +1.65 | <.0001 |
| qwen3-235b | 1.48 | 1.62 | **3.29** | 3.62 | 17% | 86% | +1.81 | <.0001 |
| deepseek-v4.1-flash | 1.49 | 1.60 | **3.72** | 3.94 | 11% | 99% | +2.23 | <.0001 |
| qwen3.8-27b | 1.54 | 1.64 | **3.76** | 3.98 | 11% | 97% | +2.22 | <.0001 |
| gpt-5.5 (ceiling) | 1.52 | 1.58 | **3.95** | 4.04 | 4% | 100% | +2.43 | <.0001 |

## T1b — Capability progression: weight-release date vs CPAS

| synthesizer | weights | released | run date | tier C | raw C | H rate | pass |
|---|---|---|---|---|---|---|---|
| llama-3.1-8b (API) | open | 2024-07-23 | 2026-08-23 | **2.27** | 3.02 | 38% | 49% |
| llama3.1:8b (LOCAL) | open | 2024-07-23 | 2026-08-23 | **2.48** | 3.14 | 33% | 54% |
| llama-3.3-70b | open | 2024-12-06 | 2026-08-23 | **3.15** | 3.46 | 16% | 77% |
| qwen3-32b | open | 2025-04-28 | 2026-08-23 | **2.86** | 3.40 | 27% | 71% |
| qwen3-235b | open | 2025-07-21 | 2026-08-23 | **3.29** | 3.62 | 17% | 86% |
| gpt-5.5 (ceiling) | closed | 2026-04-24 | 2026-08-23 | **3.95** | 4.04 | 4% | 100% |
| qwen3.8-27b | open · Apache-2.0 | 2026-08-14 | 2026-11-09 | **3.76** | 3.98 | 11% | 97% |
| deepseek-v4.1-flash | open · MIT | 2026-10-17 | 2026-11-09 | **3.72** | 3.94 | 11% | 99% |

Spearman release date vs tier-C CPAS: **ρ = 0.821, p = 0.0234** (n = 7 releases); open-weight releases only **ρ = 0.886, p = 0.0188** (n = 6). Counting the two llama-3.1-8b serving paths as separate points instead gives ρ = 0.874, p = 0.0045 (n = 8) — the same conclusion, but one release would be voting twice, so the de-duplicated value is the one quoted. Plotted as `docs/figures/fig6_release_vs_cpas.png`.

The relation is strong but **not monotone**: `llama-3.3-70b` (Dec 2024) outscores
`qwen3-32b` (Apr 2025) at roughly twice the parameter count, and the closed
`gpt-5.5` (Apr 2026) still leads both later-released open models. Release date
predicts capability on this task; it does not determine it.

**The run date is provenance, not progression.** It takes two values — six rows
judged 23 Aug 2026, two on 9 Nov 2026 (D50) — and records when the job ran, not
when capability moved. The D49 token-ceiling change falls between the two batches;
it was verified non-binding for the first six (peak 9% of the old ceiling), so the
split does not confound the comparison. Any progression claim rests on the
release-date column.

## T2 — Per-dimension, tier C only

| synthesizer | D | C | A | R | H% |
|---|---|---|---|---|---|
| llama-3.1-8b (API) | 3.1 | 2.1 | 3.2 | 3.8 | 38% |
| llama3.1:8b (LOCAL) | 3.3 | 2.3 | 3.2 | 4.0 | 33% |
| qwen3-32b | 3.2 | 2.4 | 3.9 | 4.2 | 27% |
| llama-3.3-70b | 3.6 | 2.5 | 3.6 | 4.2 | 16% |
| qwen3-235b | 3.6 | 2.8 | 3.9 | 4.3 | 17% |
| deepseek-v4.1-flash | 4.4 | 2.8 | 4.1 | 4.5 | 11% |
| qwen3.8-27b | 4.3 | 3.0 | 4.1 | 4.6 | 11% |
| gpt-5.5 (ceiling) | 4.4 | 2.9 | 4.1 | 4.8 | 4% |

## T3 — Per persona: floor vs ceiling (tier C)

| persona |  | D | C | A | R | H% | raw | CPAS |
|---|---|---|---|---|---|---|---|---|
| operator | 8B | 3.5 | 2.6 | 4.3 | 4.2 | 27% | 3.62 | **3.08** |
|  | gpt-5.5 | 4.8 | 3.1 | 4.8 | 4.6 | 10% | 4.33 | **4.13** |
| data_scientist | 8B | 2.7 | 2.2 | 2.4 | 4.5 | 0% | 2.85 | **2.85** |
|  | gpt-5.5 | 4.0 | 3.0 | 2.6 | 5.0 | 0% | 3.61 | **3.61** |
| regulator | 8B | 3.5 | 2.0 | 3.0 | 3.2 | 73% | 2.96 | **1.49** |
|  | gpt-5.5 | 4.5 | 2.7 | 4.8 | 4.8 | 3% | 4.18 | **4.11** |

## T4 — Tier A→B→C by persona (is XAI alone enough?)

| persona | model | A | B | C | A→B | B→C |
|---|---|---|---|---|---|---|
| operator | 8B | 1.52 | 1.52 | 3.08 | +0.00 | +1.56 |
|  | gpt-5.5 | 1.55 | 1.48 | 4.13 | -0.07 | +2.65 |
| data_scientist | 8B | 1.52 | 1.75 | 2.85 | +0.23 | +1.10 |
|  | gpt-5.5 | 1.53 | 1.77 | 3.61 | +0.24 | +1.83 |
| regulator | 8B | 1.49 | 1.49 | 1.49 | +0.00 | +0.00 |
|  | gpt-5.5 | 1.49 | 1.48 | 4.11 | -0.02 | +2.64 |

## T5 — CPAS by consequence class (tier C)

| consequence class | llama-3.1-8b (API) | llama3.1:8b (LOCAL) | qwen3-32b | llama-3.3-70b | qwen3-235b | deepseek-v4.1-flash | qwen3.8-27b | gpt-5.5 (ceiling) |
|---|---|---|---|---|---|---|---|---|
| ABSORBED | 2.94 | 3.16 | 3.68 | 3.48 | 3.84 | 4.34 | 4.44 | 4.51 |
| ISLAND | 2.06 | 2.52 | 2.89 | 3.38 | 3.37 | 3.42 | 3.62 | 3.88 |
| OVER+VOLT | 2.21 | 2.59 | 2.77 | 3.17 | 3.31 | 3.32 | 3.38 | 3.27 |
| OVERLOAD | 2.25 | 2.35 | 3.07 | 3.18 | 3.23 | 3.36 | 3.16 | 3.68 |

## T6 — λ sensitivity (tier C mean CPAS)

| synthesizer | λ=0 | λ=1 | λ=2 | λ=3 |
|---|---|---|---|---|
| llama-3.1-8b (API) | 3.02 | 2.65 | 2.27 | 1.89 |
| llama3.1:8b (LOCAL) | 3.14 | 2.81 | 2.48 | 2.14 |
| qwen3-32b | 3.40 | 3.13 | 2.86 | 2.60 |
| llama-3.3-70b | 3.46 | 3.31 | 3.15 | 2.99 |
| qwen3-235b | 3.62 | 3.45 | 3.29 | 3.12 |
| deepseek-v4.1-flash | 3.94 | 3.83 | 3.72 | 3.61 |
| qwen3.8-27b | 3.98 | 3.87 | 3.76 | 3.65 |
| gpt-5.5 (ceiling) | 4.04 | 4.00 | 3.95 | 3.91 |
## T6b — Weight sensitivity (tier-C CPAS, λ=2 throughout)

The weights were **pre-registered before any run**, so they cannot be tuned after the
fact. The defensible claim is therefore not that 0.30/0.25/0.25/0.20 is optimal, but
that the conclusions do not depend on it — tested including deliberately extreme
weightings nobody would choose.

| weighting | llama-3.1-8b (API) | llama3.1:8b (LOCAL) | qwen3-32b | llama-3.3-70b | qwen3-235b | gpt-5.5 (ceiling) | model order | A<C & B<C |
|---|---|---|---|---|---|---|---|---|
| **pre-registered** .30/.25/.25/.20 | 2.27 | 2.48 | 2.86 | 3.15 | 3.29 | 3.95 | unchanged | all 6 rows |
| uniform .25/.25/.25/.25 | 2.31 | 2.51 | 2.91 | 3.18 | 3.32 | 3.97 | unchanged | all 6 rows |
| D-heavy .55/.15/.15/.15 | 2.31 | 2.54 | 2.83 | 3.23 | 3.31 | 4.12 | unchanged | all 6 rows |
| C-heavy .15/.55/.15/.15 | 1.93 | 2.14 | 2.51 | 2.80 | 2.96 | 3.52 | unchanged | all 6 rows |
| A-heavy .15/.15/.55/.15 | 2.36 | 2.54 | 3.08 | 3.24 | 3.43 | 3.97 | unchanged | all 6 rows |
| R-heavy .15/.15/.15/.55 | 2.62 | 2.82 | 3.23 | 3.45 | 3.57 | 4.26 | unchanged | all 6 rows |

Spread is ±0.3 in absolute CPAS; **model ordering and tier ordering are invariant under
every weighting tested.** Note the weights are near-uniform, so they do little
discriminative work — a plain mean would rank the narratives almost identically. Do not
claim the weighting encodes a strong theoretical stance; claim the result is robust to it.

**λ, not w, is the consequential parameter.** λ=2 moves regulator CPAS from 2.96 raw to
1.49 — far more than any weight does. See T6 and `fig5_lambda_sensitivity.png`.

## T7 — Scenario set composition (n=30)

**attack class**

| value | n |
|---|---|
| attackfree | 5 |
| mitmattack | 4 |
| iec104starvationattack | 4 |
| ntpddosattack | 4 |
| dosattack | 4 |
| floodattack | 3 |
| fuzzyattack | 3 |
| portscanattack | 3 |

**consequence class**

| value | n |
|---|---|
| OVERLOAD | 9 |
| OVER+VOLT | 6 |
| ABSORBED | 6 |
| n/a | 5 |
| ISLAND | 4 |

**reportable class**

| value | n |
|---|---|
| ATTEMPT – by evidence | 22 |
| NOT reportable | 5 |
| ATTEMPT – recon | 3 |


---

## T8 — Robustness: judge agreement

Three grading configurations. "Clean panel" = every item scored by a second judge that
did **not** author it (`gpt-5.4` on llama-authored items, `gemini-3.1-pro` on gpt-5.5-authored).

| | D | C | A | R | H |
|---|---|---|---|---|---|
| Gemini vs Claude, Spearman ρ (n=20) | .888 | .796 | .891 | .987 | 100% agree |
| Clean panel vs Claude, Spearman ρ (n=20) | .664 | .402 | .848 | .896 | 95% agree |
| clean panel, within-1 agreement | 90% | 60% | 90% | 85% | — |

**Tier ordering survives every configuration.** Same-family bias measured and not found:
`gpt-5.4` scored its sibling's narratives **+2.44** vs the primary judge and other
narratives **+2.55** — a difference of −0.10.

### T8b — The qualifier: effect SIZE is judge-dependent

Disagreement is *tier-dependent*, so it does not cancel:

| tier | D | C | A | R | CPAS Δ (2nd judge − primary) |
|---|---|---|---|---|---|
| A | −0.50 | **+1.00** | 0.00 | +0.17 | +0.13 |
| B | +0.29 | **+1.57** | 0.00 | +0.71 | +0.62 |
| C | 0.00 | +0.14 | +0.14 | 0.00 | −0.21 |

```
C−A gap, primary judge : +1.30
C−A gap, clean panel   : +0.95      (~27% smaller)
```

Direction and significance robust; **magnitude carries ~±25% grader uncertainty**. State
the effect as "roughly 1.0–1.3 CPAS depending on grader", not a point value. Cause: the C
anchor treats 1 as *"contradicts"*, but silence is not contradiction — a tier-A alert
saying nothing about consequence can defensibly score 1 or 3.

---

## T9 — Methodology contribution: seven evaluation defects

Each caught by a **free** check before a paid one. Each would have produced a plausible
but wrong finding.

| # | what was graded | what the narrative actually had |
|---|---|---|
| D39 | correct attack class for D=5 | binary detector; never conveys class |
| D39 | C on false positives | anchor undefined for that case |
| D39 | R/A on one generic anchor | three incompatible persona deliverables |
| D40 | which SHAP features drove it | features never passed to the synthesizer |
| D41 | the one-hour CIP clock | rule truncated away — 0/30 context blocks |
| D45/46 | compromise-based reporting duty | evidence establishes attempt only |
| D47 | reportability | asset CIP scope absent from context |

**Rule:** *every graded expectation must be traceable to an input the narrative receives.*
Four of seven were the rubric rewarding what the persona prompts forbid — grader
contradicting generator. Two would have **inverted** the headline: D45 would have reported
a frontier model as *worse* at regulatory reasoning than an 8B.

---

## T10 — Cost

| | calls | cost |
|---|---|---|
| Judging — rows 1-6, Batch API (50% off) | 4,860 | **$113.06** |
| Judging — rows 7-8 (D50), Batch API (50% off) | 1,620 | **$38.66** |
| Generation — rows 1-6 via OpenRouter | 540 | **$7.41** |
| Generation — rows 7-8 via OpenRouter | 540 | *not metered (small)* |
| **Total judging, 8 rows** | 6,480 | **$151.72** |

Per row, judging: $18.28–$19.50. At list price, judging alone ≈ $303.

Rows 7-8 judging is computed from measured batch usage (5,064,579 input +
2,079,530 output tokens) at the published `claude-opus-5` rate of $5/$25 per MTok
with the 50% Batch discount — not an estimate. Generation for rows 7-8 was not
captured per call; it is a few dollars at OpenRouter rates, dominated by
qwen3.8-27b's reasoning tokens.

---

## T11 — Limitations

| # | limitation | evidence |
|---|---|---|
| 1 | C dimension structurally capped | consequence not in KB or `AnomalyEvent`; C peaks at 3.1 even at ceiling |
| 2 | Attack class capped by binary detector | 4/25 (8B) → 5/25 (ceiling); barely moves with capability |
| 3 | H not comparable across personas | data-scientist H=0% in every row; regulator up to 73% |
| 4 | FP stratum is 1 FP + 4 true negatives | constrained model makes no confident FP on this testbed |
| 5 | CIP asset classes authored, not cited | declared as synthetic overlay in `ip_device_map.md` |
| 6 | Open-weights rows not bit-reproducible | OpenRouter routes across providers; only local row is deterministic. Measured: identical prompt to qwen3.8-27b used 4,000 vs 1,192 reasoning tokens on two calls |
| 7 | Ceiling is a lower bound | all rows share the 8B-built graph |
| 8 | Effect size judge-dependent | +1.30 vs +0.95 (T8b) |
| 9 | Output ceiling raised mid-sweep | `MAX_OUTPUT_TOKENS` 4,000→16,000 (D49); verified non-binding for rows 1-6 (peak 9% of old ceiling), so no row was re-judged |
| 10 | **No human-agreement check** | the one unmet exit criterion in the plan |
