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

JUDGE_MODEL = os.environ.get("CCIR_JUDGE", "claude-opus-4-8")
REPEATS = 3
WEIGHTS = {"D": 0.30, "C": 0.25, "A": 0.25, "R": 0.20}  # pre-registered

# Anchored rubric (condensed from cpas_protocol.md). The judge scores against these.
RUBRIC = """You are grading a single security-incident explanation against a gold
fact sheet. Score each dimension 1-5 using the anchors; be strict and use the
full range.

D (Diagnostic accuracy): 5 = names the specific affected device AND bus AND the
correct attack class; 3 = names device OR attack but not both/correctly; 1 = no
physical referent or wrong attack.
C (Consequence): 5 = matches the gold physical consequence (overload/island/
absorbed); 3 = vague or partial; 1 = contradicts the simulated consequence.
A (Actionability): 5 = specific, correct next step naming the right breakers/
response; 3 = generic step; 1 = no actionable step.
R (Role/regulatory fit): 5 = correct persona voice + correct reporting duty where
relevant; 3 = partial; 1 = wrong framing.

H (hallucination, 0 or 1): list every factual claim in the narrative; mark each
supported / contradicted / absent vs the gold facts. H penalizes only contradicted
**grounded facts** — device identity, bus, breaker, physical consequence, or
reporting obligation. Set H = 0 only if a GROUNDED fact is contradicted (e.g.
invents a device like "RTU-123", names a wrong breaker, states a wrong CIP
timeline, or asserts a consequence that contradicts the simulated one). The
attack-type / attack-class characterization is an **inference from the flow
fingerprint, NOT a grounded fact**: the detector is binary and never told the
narrative the specific class. If the stated attack type disagrees with the gold
attack_class, reflect that in D (diagnostic accuracy) — do NOT set H = 0 for it.
Otherwise H = 1."""

SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "claim": {"type": "string"},
            "status": {"type": "string", "enum": ["supported", "contradicted", "absent"]},
        }, "required": ["claim", "status"], "additionalProperties": False}},
        "D": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "C": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "A": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "R": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "H": {"type": "integer", "enum": [0, 1]},
    },
    "required": ["claims", "D", "C", "A", "R", "H"],
    "additionalProperties": False,
}


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY or an ant profile


def judge_once(client, narrative: str, gold_facts: dict, persona: str) -> dict:
    """One blinded, isolated judge call. No tier label is ever passed."""
    user = (
        f"{RUBRIC}\n\nPERSONA the narrative was written for: {persona}\n\n"
        f"GOLD FACTS (ground truth):\n{json.dumps(gold_facts, indent=2)}\n\n"
        f"NARRATIVE TO GRADE:\n{narrative}\n\n"
        f"Return the JSON scores."
    )
    resp = client.messages.create(
        model=JUDGE_MODEL, max_tokens=2000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def cpas(scores: dict) -> float:
    raw = sum(WEIGHTS[d] * scores[d] for d in WEIGHTS)
    return round(scores["H"] * raw, 3)


def judge_narrative(client, narrative: str, gold_facts: dict, persona: str) -> dict:
    """REPEATS calls; median per dimension (non-determinism control)."""
    runs = [judge_once(client, narrative, gold_facts, persona) for _ in range(REPEATS)]
    med = {d: int(statistics.median(r[d] for r in runs)) for d in ["D", "C", "A", "R", "H"]}
    return {**med, "cpas": cpas(med), "n_runs": REPEATS,
            "spread": {d: [r[d] for r in runs] for d in ["D", "C", "A", "R", "H"]}}


if __name__ == "__main__":
    # smoke-test: judge tier-C operator narrative for scenario_02
    sid = "scenario_02"
    gold = json.loads((SCEN_DIR / f"{sid}.json").read_text())["gold_facts"]
    narrative = (ROOT / "experiments" / "results" / f"{sid}_C_operator.txt").read_text()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first:  ! export ANTHROPIC_API_KEY=sk-ant-...")
    print(json.dumps(judge_narrative(_client(), narrative, gold, "operator"), indent=2))
