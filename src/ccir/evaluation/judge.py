"""CPAS LLM-as-judge (plan §4.3, §7.6).

Judge = Claude Opus 4.8 via the Anthropic API — a different, stronger model than
the local 8B synthesizer (the independence rule). Bias controls, all from §7.6:
- BLINDED: the judge never sees the tier (A/B/C) or the hypothesis.
- ISOLATED: one narrative + rubric + gold facts per call.
- REPEATS: 3 calls per narrative, report the median (non-determinism control).
- Structured output: strict JSON schema so scores are machine-parseable.
- Anchored rubric + weights come from experiments/scenarios/cpas_protocol.md
  (pre-registered — do not tune after the first run).

Requires ANTHROPIC_API_KEY (or an `ant auth login` profile). Set it with the `!`
prefix in this session, e.g.:  ! export ANTHROPIC_API_KEY=sk-ant-...

Run:  conda run -n xai python -m ccir.evaluation.judge          # smoke-test one
      conda run -n xai python -m ccir.evaluation.report         # full run + table
"""
from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
SCEN_DIR = ROOT / "experiments" / "scenarios"

# Load ANTHROPIC_API_KEY from a gitignored .env at the repo root, if present.
# (The SDK reads the env var, not .env directly, so we bridge it here.)
load_dotenv(ROOT / ".env")

# Frozen across every run in the sweep: the judge is the ruler, not a variable
# (D34). Opus 5 is the current top-tier model at the same $5/$25 per 1M as 4.8.
JUDGE_MODEL = os.environ.get("CCIR_JUDGE", "claude-opus-5")
REPEATS = 3
WEIGHTS = {"D": 0.30, "C": 0.25, "A": 0.25, "R": 0.20}  # pre-registered; raw max = 5
LAMBDA = 2.0  # subtractive hallucination penalty (proposal: CPAS = wD+wC+wA+wR - λH)
# Pass mark on the raw 1-5 scale (the Foundry convention, D31). Reported ALONGSIDE the
# mean, never instead of it: a pass rate is far less sensitive to λ than a mean is, and
# λ=2 is large next to the ~1.0-1.5 raw gap between tiers.
THRESHOLD = 3.0

# What each persona was actually ASKED to produce (condensed from configs/personas/*.md
# and the ROLE_LINE in synthesize.py). The judge previously received only the persona's
# NAME and had to infer what "operator-appropriate" meant — so the grader held a weaker
# definition of the target than the generator did. R and A are role-dependent
# dimensions; scoring them against a generic anchor measures a different construct per
# persona while pooling the results on one 1-5 scale.
PERSONA_EXPECT = {
    "operator": (
        "Deliverable: an action briefing. R rewards operational voice — the affected "
        "device/substation, plain operational language, physical risk, continuity of "
        "the process. A rewards concrete switching actions (which breakers/RTUs to "
        "check, whether to go to manual). Model internals and SHAP values are NOT "
        "expected here and clutter is a fault; a reporting determination is optional."),
    "data_scientist": (
        "Deliverable: a model analysis. R rewards analytic voice — which flow features "
        "drove the prediction, what they mean, model confidence, and an explicit caveat "
        "about what the features can and cannot prove. A rewards a concrete analytic "
        "next step (a feature to check, a validation, a caveat to act on). Regulatory "
        "reporting duties are NOT expected here and asserting them is a fault; naming "
        "breakers is not this persona's job."),
    "regulator": (
        "Deliverable: a compliance assessment. R rewards compliance voice — what "
        "occurred, which asset, whether it meets the reportable threshold, WHICH CLOCK "
        "applies and to whom. A rewards the correct notification action. Switching "
        "instructions are NOT expected here and issuing them is a fault."),
}

# Anchored rubric (condensed from cpas_protocol.md). The judge scores against these.
RUBRIC = """You are grading a single security-incident explanation against a gold
fact sheet. Score each dimension 1-5 using the anchors; be strict and use the
full range.

LENGTH IS NOT QUALITY. A short, correct, role-appropriate answer must outscore a long
one that pads, repeats the knowledge base, or adds unrequested material. Judge only
whether the required content is present, correct and appropriate for the role.

D (Diagnostic accuracy — is the explanation GROUNDED in a real physical referent?):
5 = names the specific affected device AND its bus, AND characterizes the anomaly
consistently with the flow evidence — EITHER matching the gold attack_class OR
explicitly flagging that the class is inferred and the detector cannot identify it;
4 = device and bus correct, characterization vague; 3 = device OR characterization
but not both; 2 = weak grounding, device absent or wrong; 1 = no physical referent,
OR a specific attack class asserted as established fact when it contradicts the gold.
NOTE: the detector is BINARY and never told the narrative the specific attack class,
so a confident correct guess is not better grounded than an honest hedge — do NOT
reward lucky guessing over stated uncertainty. Grounding is what D measures.

C (Consequence): 5 = matches the gold physical consequence (overload / voltage
violation / islanding / absorbed) including its direction and the affected element;
3 = vague or partial; 1 = contradicts the simulated consequence.
IF the gold physical_consequence is "not simulated" (a false positive — no physical
consequence was established): 5 = correctly states that no physical impact is
established, or refrains from asserting one; 3 = hedges unclearly; 1 = invents a
physical consequence. Inventing an impact on a false positive is the failure mode
this scenario class exists to detect.

A (Actionability): 5 = a specific, correct next step APPROPRIATE TO THIS PERSONA (see
below); 3 = generic step; 1 = no actionable step. A step that belongs to a different
role does not earn credit.

R (Role fit): 5 = matches the persona's deliverable and voice as specified below, and
where a reporting duty is part of that role, states the correct one; 3 = partial;
1 = wrong framing, or content belonging to a different role.

H (hallucination, 0 or 1): list every factual claim in the narrative; mark each
supported / contradicted / absent vs the gold facts. H flags hallucination of a
**grounded fact** — device identity, bus, breaker, physical consequence, or
reporting obligation. Set H = 1 (hallucination present) if a GROUNDED fact is
contradicted (e.g. invents a device like "RTU-123", names a wrong breaker, states
a wrong CIP timeline, or asserts a consequence that contradicts the simulated one);
otherwise H = 0. The attack-type / attack-class characterization is an **inference
from the flow fingerprint, NOT a grounded fact**: the detector is binary and never
told the narrative the specific class. If the stated attack type disagrees with the
gold attack_class, reflect that in D (diagnostic accuracy) — do NOT set H = 1 for it.

ON `top_features` IN THE GOLD FACTS: these are the SHAP drivers the detector actually
used. They are the MODEL'S INTERNALS, not a fact about the incident, and they are the
one gold entry a narrative is not generally expected to contain. Score them as follows:
- Naming DIFFERENT features as the drivers is a false claim about the model — mark it
  contradicted in `claims` and reflect it in D. (H stays 0: a feature name is not one
  of the grounded facts H covers — device, bus, breaker, consequence, reporting duty.)
- For the DATA SCIENTIST persona, correctly identifying these drivers is core to R and D.
- For the OPERATOR and REGULATOR personas, reciting feature names earns NO credit — it
  is clutter their briefs were told to avoid. Omitting them is not a fault.

Also report `attack_class_correct`: true only if the narrative names the gold
attack_class. DIAGNOSTIC ONLY — it does not enter any score. It measures how often a
binary detector's output can be resolved to the specific class at all.

For every dimension, write a one-sentence reason BEFORE its score, citing the
specific text that drove it. Where a dimension scores 1, say whether the narrative
got it WRONG or never mentioned it — the anchors collapse both onto 1."""

DIMS = ["D", "C", "A", "R", "H"]

SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "claim": {"type": "string"},
            "status": {"type": "string", "enum": ["supported", "contradicted", "absent"]},
        }, "required": ["claim", "status"], "additionalProperties": False}},
        # reason precedes each score so the judge commits to a justification first
        "D_reason": {"type": "string"}, "D": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "C_reason": {"type": "string"}, "C": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "A_reason": {"type": "string"}, "A": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "R_reason": {"type": "string"}, "R": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "H_reason": {"type": "string"}, "H": {"type": "integer", "enum": [0, 1]},
        # diagnostic only -- never enters cpas(); measures how often a BINARY detector's
        # output can be resolved to the specific attack class (the D27 structural claim)
        "attack_class_correct": {"type": "boolean"},
    },
    "required": (["claims"] + [f"{d}{sfx}" for d in DIMS for sfx in ("_reason", "")]
                 + ["attack_class_correct"]),
    "additionalProperties": False,
}


def assert_independent_of(synth_backend: str, synth_model: str) -> None:
    """The judge must never share a vendor with the synthesizer (§7.6 independence).

    OpenRouter puts `anthropic/claude-*` one string away from the synthesis slot, which
    would have Claude grading its own family — self-preference measured as quality, and
    the ceiling run invalidated. Cheap to violate by accident, so assert it rather than
    document it."""
    if "claude" in f"{synth_backend} {synth_model}".lower() and "claude" in JUDGE_MODEL.lower():
        raise SystemExit(
            f"judge ({JUDGE_MODEL}) and synthesizer ({synth_model}) share a vendor.\n"
            f"The judge must be a different vendor (§7.6). Use a GPT/Gemini-class "
            f"synthesizer, or set CCIR_JUDGE to a non-Anthropic judge.")


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY or an ant profile


def judge_params(narrative: str, gold_facts: dict, persona: str) -> dict:
    """The create() kwargs for one blinded, isolated judge call. Shared by the
    synchronous path (judge_once) and the batch path (report.py) so both send
    byte-identical requests. No tier label is ever passed."""
    user = (
        f"{RUBRIC}\n\nPERSONA the narrative was written for: {persona}\n"
        f"WHAT THIS PERSONA WAS ASKED TO PRODUCE (score R and A against this):\n"
        f"{PERSONA_EXPECT[persona]}\n\n"
        f"GOLD FACTS (ground truth):\n{json.dumps(gold_facts, indent=2)}\n\n"
        f"NARRATIVE TO GRADE:\n{narrative}\n\n"
        f"Return the JSON scores."
    )
    return dict(
        # headroom for adaptive thinking + the claims array + 5 reason strings;
        # billed on actual output tokens, so a high cap is free insurance against
        # a truncated response failing json.loads mid-batch
        model=JUDGE_MODEL, max_tokens=4000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )


def parse_scores(message) -> dict:
    """Extract the JSON scores from a judge response message."""
    text = next(b.text for b in message.content if b.type == "text")
    return json.loads(text)


def judge_once(client, narrative: str, gold_facts: dict, persona: str) -> dict:
    """One synchronous judge call (used by the smoke test)."""
    return parse_scores(client.messages.create(**judge_params(narrative, gold_facts, persona)))


def cpas(scores: dict) -> float:
    raw = sum(WEIGHTS[d] * scores[d] for d in WEIGHTS)
    return round(raw - LAMBDA * scores["H"], 3)  # subtractive penalty, not multiplier


def aggregate_runs(runs: list[dict]) -> dict:
    """Median per dimension across repeats + CPAS + the raw spread. Shared by the
    sync and batch paths so both aggregate identically (non-determinism control)."""
    med = {d: int(statistics.median(r[d] for r in runs)) for d in DIMS}
    return {**med, "cpas": cpas(med), "n_runs": len(runs),
            # diagnostic, not scored: majority vote over repeats
            "attack_class_correct": sum(r["attack_class_correct"] for r in runs) > len(runs) / 2,
            "spread": {d: [r[d] for r in runs] for d in DIMS},
            # all repeats' reasons: they explain the spread, not just the median
            "reasons": {d: [r[f"{d}_reason"] for r in runs] for d in DIMS}}


def judge_narrative(client, narrative: str, gold_facts: dict, persona: str) -> dict:
    """REPEATS synchronous calls; median per dimension (used by the smoke test)."""
    return aggregate_runs([judge_once(client, narrative, gold_facts, persona)
                           for _ in range(REPEATS)])


if __name__ == "__main__":
    # smoke-test: judge tier-C operator narrative for scenario_02
    sid = "scenario_02"
    gold = json.loads((SCEN_DIR / f"{sid}.json").read_text())["gold_facts"]
    narrative = (ROOT / "experiments" / "results" / f"{sid}_C_operator.txt").read_text()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first:  ! export ANTHROPIC_API_KEY=sk-ant-...")
    print(json.dumps(judge_narrative(_client(), narrative, gold, "operator"), indent=2))
