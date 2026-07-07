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

## H — hallucination penalty (0/1 multiplier)
Applied per §7.6 #6 as structured fact-checking, not holistic judgment:
- List every factual claim in the narrative.
- Mark each: supported / contradicted / absent w.r.t. the scenario's gold fact
  sheet + retrieved context.
- **H = 0** (penalized to zero for that narrative) if any claim is *contradicted*
  (e.g., invents a device like "RTU-123", or states a wrong CIP timeline);
  otherwise **H = 1**.

## Scoring formula (weights pre-registered)
```
raw   = w_D*D + w_C*C + w_A*A + w_R*R
CPAS  = H * raw
weights: w_D = 0.30, w_C = 0.25, w_A = 0.25, w_R = 0.20   (sum = 1.0)
```
Rationale for weights: D and C are the semantic-gap core (grounding + consequence),
so weighted highest; A and R matter but ride on correct D/C. Max raw = 5.

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
