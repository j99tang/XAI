# run: conda run -n xai python tests/test_cpas.py  (no API calls -- pure arithmetic)
from ccir.evaluation.judge import (DIMS, PERSONA_EXPECT, SCHEMA, aggregate_runs,
                                   cpas, judge_params)


def run(D, C, A, R, H, class_ok=False):
    r = {"claims": [], "D": D, "C": C, "A": A, "R": R, "H": H,
         "attack_class_correct": class_ok}
    r.update({f"{d}_reason": f"because {d}" for d in DIMS})
    return r


# schema wiring: every dimension's reason is generated BEFORE its score, so the
# judge commits to a justification instead of rationalising a number it already picked
props = list(SCHEMA["properties"])
for d in DIMS:
    assert props.index(f"{d}_reason") < props.index(d), f"{d}: reason must precede score"
assert set(SCHEMA["required"]) == ({"claims", "attack_class_correct"} | set(DIMS)
                                   | {f"{d}_reason" for d in DIMS})

# D39: attack_class_correct is a DIAGNOSTIC. It must never move the score -- it exists
# to quantify D27 (can a binary detector's output be resolved to a class at all?), and
# folding it in would silently redefine CPAS.
assert cpas(run(3, 3, 3, 3, 0, class_ok=True)) == cpas(run(3, 3, 3, 3, 0, class_ok=False))
assert aggregate_runs([run(3, 3, 3, 3, 0, True)] * 3)["attack_class_correct"] is True
assert aggregate_runs([run(3, 3, 3, 3, 0, True), run(3, 3, 3, 3, 0, False),
                       run(3, 3, 3, 3, 0, False)])["attack_class_correct"] is False  # majority

# D39: R and A are role-dependent, so the judge must be told what THIS persona owes.
# Previously it got only the persona's name -- a weaker spec than the generator had.
for persona, expect in PERSONA_EXPECT.items():
    prompt = judge_params("narrative", {"device": "x"}, persona)["messages"][0]["content"]
    assert expect in prompt, f"{persona}: R/A expectations not sent to the judge"
assert "LENGTH IS NOT QUALITY" in prompt, "anti-verbosity instruction missing (§7.6 #1)"
assert "not simulated" in prompt, "false-positive C anchor missing"
assert "do NOT\nreward lucky guessing" in prompt.replace("\r", ""), \
    "D must not reward a lucky class guess over an honest hedge"

# D39: top_features sits inside the GOLD FACTS blob but is the model's internals, not a
# fact about the incident. Unqualified, it invites the judge to reward feature recitation
# from the operator/regulator personas -- which their own prompts call clutter.
for persona in PERSONA_EXPECT:
    prompt = judge_params("n", {"device": "x"}, persona)["messages"][0]["content"]
    assert "ON `top_features` IN THE GOLD FACTS" in prompt, f"{persona}: scope missing"
    assert "earns NO credit" in prompt

# CPAS is exactly as pre-registered: w-sum minus 2H, spanning -1.0 .. 5.0
assert cpas(run(5, 5, 5, 5, 0)) == 5.0
assert cpas(run(1, 1, 1, 1, 0)) == 1.0
assert cpas(run(1, 1, 1, 1, 1)) == -1.0
assert cpas(run(5, 5, 5, 5, 1)) == 3.0

# aggregation: median per dimension, raw spread kept, all repeats' reasons kept
# (the reasons explain the spread, so keeping only the median run's would lose the why)
agg = aggregate_runs([run(4, 4, 4, 4, 0), run(2, 2, 2, 2, 1), run(4, 4, 4, 4, 0)])
assert agg["D"] == 4 and agg["H"] == 0 and agg["cpas"] == 4.0
assert agg["spread"]["D"] == [4, 2, 4]
assert agg["reasons"]["D"] == ["because D"] * 3 and len(agg["reasons"]) == len(DIMS)

# D30/D31: a top narrative survives one hallucination (5.0-2 = 3.0), but in the MID
# range -- where the 8B actually scores -- lambda=2 inverts the ranking, letting a
# sparse-but-clean narrative outrank a substantive one. This is the open lambda issue.
assert cpas(run(5, 5, 5, 5, 1)) > cpas(run(2, 1, 1, 2, 0))      # top survives
assert cpas(run(3, 3, 3, 3, 1)) < cpas(run(2, 1, 1, 2, 0))      # mid does not
print("ok -- cpas unchanged; reasons precede scores and survive aggregation")
