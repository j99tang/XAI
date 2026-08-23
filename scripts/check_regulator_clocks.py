"""Did the regulator state the RIGHT CIP clock, broken down by reportable class?

Before §11.1 the rule reached the model in 0/30 context blocks (D41) and 27/30
narratives asserted "24 hours" -- a figure absent from the KB. §11.1 puts the rule in
30/30 blocks (D43). This measures whether the OUTPUT followed.

Broken out by class because the three are not equally hard:
  INCIDENT (n=22) -> "within one hour"           -- the common case
  ATTEMPT  (n=3)  -> "end of next calendar day"  -- the discriminating case: requires
                     reading the retrieved rule, not pattern-matching "attack -> report fast"
  NOT reportable (n=5) -> no obligation asserted -- the false-positive case

Run: conda run -n xai python scripts/check_regulator_clocks.py
"""
from __future__ import annotations
import collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys
RUN = ROOT / "experiments" / "results" / (
    _sys.argv[1] if len(_sys.argv) > 1 else "ollama-llama3.1-8b")

ONE_HOUR = re.compile(r"\b(within (an|one|1) hour|one hour|1 hour|60 minutes)\b", re.I)
NEXT_DAY = re.compile(r"next calendar day", re.I)
WRONG = re.compile(r"\b(24|48|72)[- ]hours?\b", re.I)
# Deliberately broad: models phrase a declination many ways ("does not plausibly meet",
# "no reporting clock is triggered", "no ... timeline applies"). A narrow pattern scores
# a correct declination as a miss -- which is how this checker first reported 0/5 for a
# model that had declined all five explicitly.
NOT_REP = re.compile(
    r"(not reportable"
    r"|does not (plausibly |currently |appear to )?meet"
    r"|no reporting (obligation|clock|timeline|requirement)"
    r"|no .{0,25}(clock|timeline) (is |are )?(triggered|applies|apply)"
    r"|not .{0,20}reportable"
    r"|no notification is due"
    r"|does not trigger)", re.I)


# Strip HYPOTHETICAL clauses before looking for an asserted clock. A sophisticated
# answer states its determination and then adds "if later determined to be X, the Y
# timeline would apply" -- correct compliance reasoning. Matching a bare timeline phrase
# anywhere scores that as if it had asserted Y, which penalises exactly the careful
# conditional a frontier model produces. (This is a cheap pre-flight proxy; the LLM
# judge, given the rubric, handles conditionals properly. See D46.)
COND = re.compile(r"(?:^|(?<=[.\n]))\s*(?:if\b|should\b|were\b|in the event)[^.]*\.",
                  re.I | re.M)
COND2 = re.compile(r"[^.]*\bwould (?:be due|apply)\b[^.]*\.", re.I)


def operative(text: str) -> str:
    """The text minus conditional/hypothetical sentences."""
    return COND2.sub(" ", COND.sub(" ", text))


def gold_class(rep: str) -> str:
    """Gold classes after the D46 revision: detection establishes an ATTEMPT, never a
    compromise, so the one-hour clock is no longer a gold answer on any scenario."""
    if "NOT report" in rep: return "NOT reportable"
    if "Reconnaissance probes" in rep: return "ATTEMPT - recon"
    return "ATTEMPT - by evidence"


def main() -> None:
    rows, by = [], collections.defaultdict(lambda: collections.Counter())
    for f in sorted(glob.glob(str(ROOT / "experiments/scenarios/scenario_*.json"))):
        rec = json.loads(Path(f).read_text())
        sid, cls = rec["scenario_id"], gold_class(rec["gold_facts"]["reportable"])
        nar = RUN / f"{sid}_C_regulator.txt"
        if not nar.exists():
            continue
        full = nar.read_text()
        t = operative(full)          # judge the DETERMINATION, not the hypotheticals
        one, nxt, bad, no = (bool(ONE_HOUR.search(t)), bool(NEXT_DAY.search(t)),
                             bool(WRONG.search(full)), bool(NOT_REP.search(t)))
        if cls.startswith("ATTEMPT"):    correct = nxt and not one and not bad
        else:                            correct = no and not (one or nxt)
        by[cls]["n"] += 1
        by[cls]["correct"] += correct
        by[cls]["wrong_clock"] += bad
        by[cls]["silent"] += not (one or nxt or no)
        rows.append((sid, cls, correct, bad, t))

    print(f"=== regulator clock accuracy: {RUN.name}, {len(rows)} scenarios ===")
    print(f"{'gold class':30} {'n':>3} {'correct':>9} {'said 24/72h':>12} {'no clock':>9}")
    for cls in ("ATTEMPT - by evidence", "ATTEMPT - recon", "NOT reportable"):
        c = by[cls]
        if not c["n"]:
            continue
        print(f"{cls:30} {c['n']:>3} {c['correct']:>4} ({c['correct']/c['n']:>3.0%}) "
              f"{c['wrong_clock']:>12} {c['silent']:>9}")
    tot = sum(c["correct"] for c in by.values()); n = sum(c["n"] for c in by.values())
    bad = sum(c["wrong_clock"] for c in by.values())
    print(f"{'TOTAL':30} {n:>3} {tot:>4} ({tot/n:>3.0%}) {bad:>12}")
    print("\n  'correct' = states the next-calendar-day attempt clock and does NOT assert")
    print("  the 1-hour clock as applying on these facts (D46 gold). Conditional mentions")
    print("  of the 1-hour clock are excluded from the check.")

    miss = [(s, c) for s, c, ok, _, _ in rows if not ok for c in [c]]
    if miss:
        print(f"\n  still wrong ({len(miss)}):")
        for s, c in miss[:10]:
            print(f"    {s}  gold={c}")


if __name__ == "__main__":
    main()
