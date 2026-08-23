# CPAS Evaluation Protocol (PRE-REGISTERED)

Committed to git **before** running the judge, so scores cannot be accused of
being tuned to the result (plan §4.3, §7.6). Do not edit after the first judge run;
amend only by a new dated section explaining why.

## CPAS dimensions (each scored 1–5 by an independent judge)

| Dim | Name | What it measures | Anchor 1 | Anchor 3 | Anchor 5 |
|---|---|---|---|---|---|
| **D** | Diagnostic accuracy | Correctly names the affected device/bus and attack class | no physical referent, wrong attack | names device OR attack, not both | names the specific device + bus + correct attack class |
| **C** | Cascading/consequence | Correctly states the physical consequence | consequence contradicts the simulator | vague/partial consequence | matches the simulated consequence (overload/island/absorbed) |
| **A** | Actionability | Gives correct, role-appropriate next steps | no actionable step | generic step | specific step naming the right breakers/response |
| **R** | Regulatory/role fit | Uses correct role framing and (for REG) reporting duty | wrong framing | partial | correct persona voice + correct CIP obligation where relevant |

## H — hallucination penalty (0/1, subtractive)
Applied per §7.6 #6 as structured fact-checking, not holistic judgment:
- List every factual claim in the narrative.
- Mark each: supported / contradicted / absent w.r.t. the scenario's gold fact
  sheet + retrieved context.
- **H = 1** (hallucination present) if a **grounded fact** is *contradicted* —
  device identity, bus, breaker, physical consequence, or reporting obligation
  (e.g., invents a device like "RTU-123", names a wrong breaker, states a wrong
  CIP timeline, or a consequence contradicting the simulator); otherwise **H = 0**.
- The **attack-type/class characterization is an inference, not a grounded fact**:
  the binary detector never conveys the specific class, so a wrong attack-type
  reading lowers **D** (diagnostic accuracy), it does **not** set H = 1.

**Amendment 2026-07 (pilot-driven, pre-run — legitimate per §7.6 #2).** The
3-scenario pilot revealed H mis-firing: tier-C narratives correctly ground the
device/bus/breakers/consequence but infer a flooding-*family* class (flood/DoS/
starvation are near-indistinguishable from flow statistics), which the strict H
then zeroed. Grounded facts vs evidence-based inferences are different failures
(the plan's §2.8 evidence-trap distinction); H guards the former, D grades the
latter. This narrowing was made **before** the full run, on pilot evidence — not
tuned to results. Rationale and the flagged claim are in the decision log.

## Scoring formula (weights pre-registered)
```
CPAS = w_D*D + w_C*C + w_A*A + w_R*R  -  λ*H
weights: w_D = 0.30, w_C = 0.25, w_A = 0.25, w_R = 0.20   (sum = 1.0; raw max = 5)
λ = 2.0   (subtractive hallucination penalty)
```
Rationale for weights: D and C are the semantic-gap core (grounding + consequence),
so weighted highest; A and R matter but ride on correct D/C. Raw max = 5; a
hallucination costs a flat λ=2 (severe but not total), so one wrong grounded fact
degrades a strong narrative without erasing its other merits.

**Amendment 2026-07 (correction to match the original proposal).** The first
implementation used a *multiplicative* gate (`CPAS = H·raw`), which zeroed any
tier-C narrative with a single contradicted grounded fact and let sparse A/B tiers
(nothing to contradict) float on a floor — structurally rewarding saying less. The
**original proposal defines CPAS additively with a subtractive penalty**
(`… − λH`), so this restores the pre-registered form; H's polarity is flipped to
match (H=1 = hallucination present). This is a correction *to* pre-registration,
not a post-hoc tuning. λ=2.0 chosen as a severe-but-non-erasing deduction (40% of
raw max); tunable. The 2026-07 baseline run used the multiplicative form and must
be re-run under this formula before interpretation.

## Amendment 2026-08-21 — rubric corrected before re-establishing the baseline
The 15-scenario baseline is abandoned (D35/D37); this rubric is the pre-registration
for the new 30-scenario programme. Four corrections, all made BEFORE any run:

1. **R and A are now scored per persona.** They are role-dependent dimensions, and one
   generic anchor measured a different construct for each persona while pooling all
   three on one 1-5 scale. "Correct reporting duty where relevant" is the whole of R
   for the regulator and never relevant for the data scientist. The judge now receives
   each persona's deliverable spec (`PERSONA_EXPECT`), so it grades against the same
   target the narrative was written to — previously it received only the persona's NAME.
2. **D no longer rewards lucky guessing.** The old anchor required the "correct attack
   class" for a 5, but the detector is binary and never conveys the class, so D=5
   demanded a guess. A model confidently asserting "DoS" and happening to be right
   outscored one correctly saying "the features indicate flooding; the detector cannot
   identify the class" — penalising exactly the epistemic honesty the persona prompts
   require ("never guess"; "what the features can and cannot prove"). D now measures
   GROUNDING: a correct hedge scores as well as a correct name, and only false
   confidence is penalised.
3. **C is now defined for false positives.** 5 of 30 scenarios have
   `physical_consequence = "not simulated"`, and the old anchor gave the judge no way
   to score them — 17% of the set was scoring an undefined dimension. For an FP, 5 =
   correctly states no physical impact is established; 1 = invents one. Inventing an
   impact on a false positive is the failure this scenario class exists to detect.
4. **Explicit anti-verbosity instruction.** Tier A is ~77 characters and tier C ~1000;
   length bias is the best-documented LLM-judge failure (§7.6 #1). Logging lengths
   detects it but does not counter it, so the judge is now told directly that a short
   correct answer must outscore a padded one.

5. **`top_features` is scoped.** It sits inside the blob labelled GOLD FACTS
   (ground truth) but is the MODEL'S INTERNALS, not a fact about the incident — and it
   is the only gold entry with no correctness semantics (a device can be wrong; a
   feature list is just what the detector used). Unqualified, it implied every narrative
   should contain it, so the judge could reward feature recitation from the operator and
   regulator personas — clutter their own prompts forbid. Now: naming DIFFERENT features
   is a false claim about the model (contradicted claim, reflected in D, but H stays 0 —
   a feature name is not one of the grounded facts H covers); correct identification is
   core to R and D for the DATA SCIENTIST only; recitation earns no credit for the other
   two, and omission is not a fault. Retained rather than removed because it is the only
   way to catch a feature hallucination, which is a live failure mode for the
   data-scientist persona.

**Weights, λ, and the formula are UNCHANGED.** These amendments alter what the D, C, A
and R anchors mean, not how they combine.

**New diagnostic (not scored):** `attack_class_correct` — did the narrative name the
gold attack class? Reported per tier x persona, never in CPAS. It quantifies the D27
structural claim: if this stays low even for tier C under a frontier synthesizer, the
lever is a multiclass detector, not a bigger model.

## Per-dimension reasons (diagnostic output only)
The judge returns a one-sentence reason per dimension, written *before* the score.
No effect on the formula. Where a dimension scores 1, the reason must say whether the
narrative got the fact WRONG or never mentioned it — the anchors collapse both onto 1,
so the reason is the only place that distinction survives.

## Judge procedure (bias controls, §7.6)
- **Judge ≠ synthesizer family.** Synthesizer = local llama3.1:8b; judge = a
  different, stronger model (Claude or Gemini via API, or a distinct stronger
  model). Decided per `CCIR_JUDGE` at run time.
- **Blinded:** the judge never sees the tier label (A/B/C) or the hypothesis.
- **Isolated:** one narrative + rubric + gold facts per call; no cross-comparison.
- **Repeats:** 3 judge calls per narrative; report the **median** and the spread.
- **Pinned model version** recorded in the run output.

## Expected result (hypothesis, pre-registered)
CPAS(C) > CPAS(B) > CPAS(A), because context (C) supplies device/consequence
grounding that raw SHAP (B) and bare prediction (A) cannot. Per persona, C's
advantage should be largest for the Operator (needs device+action) and Regulator
(needs reporting duty), smaller for the Data Scientist (B already has the features).

## Human spot-check
Author scores 5 scenarios (one per kind + two random) with this rubric BEFORE
seeing judge scores; report within-1-point agreement per dimension. Validates the
judge tracks a human (§7.6 #7).

## Scenario set (frozen)
15 scenarios in `experiments/scenarios/scenario_*.json`:
- 01–05 tp_physical (attack flows assigned to RTU-1/RTU-3 → simulated physical violation)
- 06–10 tp_cyber (attack flows assigned to RTU-2/RTU-4 → grid absorbs, operational only)
- 11–15 fp_noise (real normal flows the constrained model scored most attack-like)

Note (D24): attack flow *statistics* are real captures; the *target RTU* is an
authored overlay (no capture attack targets a real RTU — the real/sim domain
shift). Fact sheets' consequences come from the pandapower simulator, not an LLM.
