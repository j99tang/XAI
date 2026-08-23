# Phase 4 — Baseline CPAS result (8B synthesizer)

> **WITHDRAWN as of 2026-08-21 (D41): the central claim is false — the CIP timeline
> never reached the model (`max_chars` truncation), so "the 8B ignores context for its
> training prior" is not supported. Also STALE as of 2026-08-19 — quote only as the 15-scenario, pre-D36 baseline.** These
> numbers were produced against the old 15-scenario set, whose consequence was a pure
> function of device (4 distinct consequences; effective n=4 on C/A/R — see D35), and
> before the simulator's thermal ratings were fixed (D36), under which some consequences
> were simply WRONG: RTU-2's outage was graded "no physical violation" while in fact
> overloading three lines. Do NOT pool these with results from the 30-scenario set (D37).

Date 2026-07-10. Judge = Claude Opus 4.8 (batch API, 405 calls, 3 repeats/median).
Synthesizer = local llama3.1:8b, temp 0. Full scores:
`experiments/results/cpas_scores.json` (git-ignored — this note preserves the table).

## Formula note
The 2026-07-10 batch was scored with the FIRST (multiplicative) formula
`CPAS = H·raw`. That was later corrected to the original proposal's SUBTRACTIVE form
`CPAS = w_D·D+w_C·C+w_A·A+w_R·R − λ·H` (λ=2, H=1 = hallucination present) — see
`cpas_protocol.md` amendment. The corrected table below is **recomputed from the
same stored raw D/C/A/R/H** (no re-judging; `cpas_scores_corrected.json`).

## Corrected table — subtractive λ=2 (mean CPAS)
| persona | A | B | C |
|---|---|---|---|
| operator | 1.46 | 1.57 | **1.62** |
| data_scientist | 1.53 | **1.84** | 1.78 |
| regulator | 1.45 | 1.53 | **0.55** |

## Original table — multiplicative H·raw (superseded; kept for the record)
| persona | A | B | C |
|---|---|---|---|
| operator | 1.46 (77c) | 1.57 (322c) | 1.12 (956c) |
| data_scientist | 1.53 (77c) | 1.84 (322c) | 1.80 (1120c) |
| regulator | 1.45 (77c) | 1.53 (322c) | 0.21 (1084c) |

**The correction helps but does not overturn the finding.** Subtractive penalty lifts
operator C above A/B and regulator C from 0.21→0.55 (hallucinations now *degrade*,
don't *erase*). But tier C still doesn't clearly beat B, because **25/45 tier-C
narratives genuinely hallucinate a grounded fact** (regulator 14/15, the CIP timeline)
— even a flat −2 across two-thirds of the regulator set drags the mean down. The
multiplicative formula *masked* part of this; the real bottleneck is the 8B's
hallucination rate. Hypothesis C > B > A holds on the RAW dimensions (below), not yet
on the composite.

## Why — the finding (this is a reliability bottleneck, not a system failure)
Break CPAS into its parts (raw D/C/A/R, and the H 0/1 multiplier):

| tier | D | C | A | R | H=0 count | mean CPAS |
|---|---|---|---|---|---|---|
| A | 2.2 | 1.33 | 1.0 | 1.18 | 0/45 | 1.48 |
| B | 2.33 | 1.56 | 1.0 | 1.53 | 0/45 | 1.65 |
| C | **2.87** | **1.73** | **2.49** | **2.56** | **25/45** | 1.04 |

- **On substance, tier C wins on every dimension** — the contextualizer produces
  more diagnostic, actionable, role-fit narratives (D/C/A/R all highest for C). The
  semantic-gap value of context is real.
- **But H (hallucination) zeroes 25/45 tier-C narratives**, collapsing the multiplied
  score below the sparse A/B floor. A/B are terse ("prediction: attack, conf 0.99") —
  almost no grounded facts to contradict, so H=1 always and they never get zeroed.
  Tier C is rich and grounded, so one hallucinated grounded fact → H=0 → whole
  narrative scores 0.

## The failure is concentrated and RETRIEVABLE (→ fixable by a better model)
Tier-C H=0 by persona: **regulator 14/15, operator 10/15, data_scientist 1/15.**
- **Regulator:** 14/15 state a wrong CIP-008 reporting timeline ("within 24 hours",
  once "72 hours") — the KB clearly says **1 hour**. This is a contradicted grounded
  fact (reporting obligation) → H=0. The correct fact is *in the KB* (scenario_02's
  regulator got "60 minutes" right), so the 8B is ignoring provided context in favor
  of its training prior. **A retrieval/reasoning failure, not a structural one.**
- **Data scientist:** rarely hallucinates (talks features/model, few grounded facts
  to contradict) → H=1 mostly, but low D (doesn't name device/consequence).

## Interpretation (the thesis result)
Two-part story, richer than a plain "C > B > A":
1. **Context improves narrative quality** — raw D/C/A/R: C > B > A, clearly.
2. **But that value is bottlenecked by synthesizer reliability** — an 8B model
   hallucinates grounded facts (esp. the CIP timeline) often enough that the
   hallucination penalty dominates. A confidently-wrong grounded fact is worse than
   sparse-but-correct output. **Context without a reliable synthesizer is risky.**

Present BOTH the raw-dimension table (context helps) and the H-penalized CPAS
(reliability gates it). That contrast IS the contribution.

## This is the §7.5 upgrade signal (D28 gate now answered)
The dominant failure is a **retrievable-fact hallucination** (1-hour timeline is in
the KB), which is exactly the category a stronger synthesizer fixes — NOT the
structural class-naming limit (that needs multiclass, D27/§11.9). So the upgrade
test is now justified. **Predicted:** a stronger synthesizer that uses the KB's
1-hour timeline flips ~14 regulator + ~10 operator narratives H=0→H=1, and tier-C
CPAS jumps above A/B.

## Next step
Run the §7.5 upgrade test (backend already pluggable, D28): set
`CAIE_SYNTH_BACKEND=openai` + a stronger model (e.g. via OpenRouter), regenerate
tier C, re-run the batch (~$11), compare. Keep the judge (Opus 4.8) fixed.
