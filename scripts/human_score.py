"""Blind human scoring worksheet for the CPAS human-agreement check.

WHY THIS EXISTS. Every CPAS number so far comes from an LLM grading an LLM. That is
circular until someone shows the judge agrees with a person. It is the item a committee
is most likely to ask about, and no amount of cross-LLM agreement substitutes for it: if
models share a bias, they agree with each other and still disagree with reality.

YOU DO NOT NEED POWER-SYSTEMS EXPERTISE. Every dimension is scored against the GOLD FACT
SHEET shown beside the narrative — the simulator already made the physics judgement
(plan §4.4). You are reading and matching, not assessing grid behaviour.

BLIND BY CONSTRUCTION: the judge's scores are never shown or loaded here. Sampling is
seeded, so the same 20 narratives come back if you resume.

  conda run -n xai python scripts/human_score.py            # score (resumable)
  conda run -n xai python scripts/human_score.py --report   # agreement vs the judge
"""
from __future__ import annotations
import json, random, sys, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "results" / "human_scores.json"
RUNS = ["ollama-llama3.1-8b", "openai-openai-gpt-5.5"]
N = 20
SEED = 20260823

ANCHORS = {
 "D": ("Diagnostic accuracy — is it GROUNDED?",
       "5 names the right device AND its bus, and characterises the anomaly consistently\n"
       "  with the evidence (either the right class OR an honest 'the detector cannot tell')\n"
       "4 device+bus right, characterisation vague\n"
       "3 device OR characterisation, not both\n"
       "2 weak grounding; device absent or wrong\n"
       "1 no physical referent, or a wrong class asserted as established fact"),
 "C": ("Consequence — does it match the gold?",
       "5 matches the gold physical consequence incl. direction and affected element\n"
       "3 vague or partial\n"
       "1 contradicts it\n"
       "IF gold says 'not simulated' (a false positive): 5 = correctly says no physical\n"
       "  impact is established; 1 = invents one"),
 "A": ("Actionability — a next step FOR THIS ROLE?",
       "5 specific, correct, role-appropriate next step\n3 generic step\n1 none\n"
       "A step belonging to a different role earns no credit"),
 "R": ("Role fit — does it deliver what this persona was asked for?",
       "5 matches the persona's deliverable and voice; states the right reporting duty\n"
       "  where that is part of the role\n3 partial\n1 wrong framing, or another role's content"),
 "H": ("Hallucination — 0 or 1",
       "1 if it CONTRADICTS a grounded fact: device identity, bus, breaker, physical\n"
       "  consequence, or reporting obligation\n"
       "0 otherwise.\n"
       "NOT a hallucination: naming the wrong attack class (the detector is binary and\n"
       "  never told it the class) — reflect that in D instead."),
}
EXPECT = {
 "operator": "action briefing: device, plain operational risk, which breakers/RTUs to check,\n"
             "manual control. Model internals are clutter here.",
 "data_scientist": "model analysis: which flow features drove it, what they mean, confidence,\n"
                   "and what the features can/cannot prove. Reporting duties are NOT its job.",
 "regulator": "compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK,\n"
              "to whom. Switching instructions are NOT its job.",
}


def sample():
    """One narrative from every (run x tier x persona) cell, then top up at random.

    2 runs x 3 tiers x 3 personas = 18 cells; N=20 covers every cell with 2 spare. Full
    coverage matters because agreement is not uniform: the regulator persona and tier C
    are where the judge does its hardest work (conditional reasoning, the H penalty), and
    a draw weighted toward tier-A data-scientist narratives would measure agreement on
    the easy cases and say nothing about the hard ones.
    """
    rng = random.Random(SEED)
    cells, picked = {}, []
    for run in RUNS:
        rows = json.load(open(ROOT / f"experiments/results/{run}/cpas_scores.json"))["rows"]
        for r in rows:
            cells.setdefault((run, r["tier"], r["persona"]), []).append(
                (run, r["scenario"], r["tier"], r["persona"]))
    for key in sorted(cells):
        picked.append(rng.choice(cells[key]))
    spare = [x for c in cells.values() for x in c if x not in picked]
    rng.shuffle(spare)
    picked += spare[: max(0, N - len(picked))]
    rng.shuffle(picked)
    return picked[:N]


def score():
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [i for i in sample() if f"{i[0]}|{i[1]}|{i[2]}|{i[3]}" not in done]
    print(f"{len(done)} scored, {len(todo)} to go. Ctrl-C anytime — progress is saved.\n")
    for run, sid, tier, persona in todo:
        key = f"{run}|{sid}|{tier}|{persona}"
        gold = json.load(open(ROOT / f"experiments/scenarios/{sid}.json"))["gold_facts"]
        nar = (ROOT / f"experiments/results/{run}/{sid}_{tier}_{persona}.txt").read_text()
        print("=" * 78)
        print(f"[{len(done)+1}/{N}]  persona = {persona.upper()}   (run/tier hidden on purpose)")
        print(f"\nWHAT THIS PERSONA WAS ASKED FOR:\n  " + EXPECT[persona].replace("\n", "\n  "))
        print("\nGOLD FACTS (the answer key — score against THIS, not domain knowledge):")
        for k in ("device", "attack_class", "physical_consequence", "reportable"):
            print(textwrap.fill(f"{k}: {gold[k]}", 76, initial_indent="  ", subsequent_indent="      "))
        print("\nNARRATIVE:\n" + textwrap.indent(nar.strip(), "  "))
        rec = {}
        for dim, (title, anchor) in ANCHORS.items():
            print(f"\n--- {dim}: {title} ---\n  " + anchor.replace("\n", "\n  "))
            while True:
                v = input(f"  {dim} = ").strip()
                ok = v in ("0", "1") if dim == "H" else v in list("12345")
                if ok: rec[dim] = int(v); break
                print("   (H is 0 or 1; others are 1-5)")
        done[key] = rec
        OUT.write_text(json.dumps(done, indent=1))
        print(f"\n  saved -> {OUT}\n")
    print("done.  now run:  python scripts/human_score.py --report")


def _load_human():
    """Accept either the CSV worksheet or the interactive script's JSON."""
    csv_path = ROOT / "experiments/results/human_scores.csv"
    if csv_path.exists():
        import csv as _csv
        keymap = json.loads((ROOT / "experiments/results/.human_score_keymap.json").read_text())
        out = {}
        with open(csv_path) as f:
            for row in _csv.DictReader(f):
                if all(row[d].strip() for d in ("D", "C", "A", "R", "H")):
                    out[keymap[row["item"]]] = {d: int(row[d]) for d in ("D", "C", "A", "R", "H")}
        if out:
            print(f"(read {len(out)} completed rows from human_scores.csv)\n")
            return out
    if OUT.exists():
        return json.loads(OUT.read_text())
    raise SystemExit("no scores yet — fill experiments/results/human_scores.csv")


def report():
    from scipy.stats import spearmanr
    human = _load_human()
    judge = {}
    for run in RUNS:
        for r in json.load(open(ROOT / f"experiments/results/{run}/cpas_scores.json"))["rows"]:
            judge[f"{run}|{r['scenario']}|{r['tier']}|{r['persona']}"] = r
    keys = [k for k in human if k in judge]
    print(f"human-vs-judge agreement, n={len(keys)} narratives\n")
    print(f"{'dim':>4} {'Spearman ρ':>12} {'exact':>8} {'within 1':>10} {'mean Δ':>8}")
    for d in "DCAR":
        h = [human[k][d] for k in keys]; j = [judge[k][d] for k in keys]
        rho = spearmanr(h, j).correlation if len(set(h)) > 1 else float("nan")
        ex = sum(a == b for a, b in zip(h, j)) / len(h)
        w1 = sum(abs(a - b) <= 1 for a, b in zip(h, j)) / len(h)
        print(f"{d:>4} {rho:>12.3f} {ex:>7.0%} {w1:>9.0%} {sum(j)/len(j)-sum(h)/len(h):>+8.2f}")
    h = [human[k]["H"] for k in keys]; j = [judge[k]["H"] for k in keys]
    agree = sum(a == b for a, b in zip(h, j)) / len(h)
    print(f"{'H':>4} {'(binary)':>12} {agree:>7.0%} {'':>9} {sum(j)/len(j)-sum(h)/len(h):>+8.2f}")
    print("\n  mean Δ > 0 means the JUDGE scores higher than you (judge is lenient).")
    print("  Report Spearman ρ per dimension and the H agreement rate in the thesis.")


if __name__ == "__main__":
    report() if "--report" in sys.argv else score()
