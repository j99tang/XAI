"""Pairwise human preference — validating the CPAS *ordering* without absolute scoring.

WHY PAIRWISE. Absolute 1-5 scoring on D/C/A/R needs domain judgement: deciding whether
"lines around Bus 6 would be stressed" matches "overloads: line 7 @ 108.2%" is a
power-systems call. Choosing which of two explanations is more useful is not — comparison
needs no calibration and no scale to internalise. And it tests exactly the claim the
thesis makes, which is an ORDERING (A < B < C, and weaker model < stronger model), not
an absolute score level. Same design as Chatbot Arena and most preference collection.

WHAT IT GUARDS AGAINST. Tier A is 78 characters and tier C is ~1,100, so an A-vs-C pair
is won on length alone and validates little. The sample is therefore stratified:

  easy      (6)  tier A or B  vs  tier C, same model     -> sanity floor, expect ~100%
  model    (10)  tier C 8B    vs  tier C gpt-5.5         -> THE REAL TEST: similar length
                                                             (1027 vs 1177 chars),
                                                             CPAS 2.48 vs 3.95
  discrim   (4)  tier C, same model, CPAS-high vs -low   -> does CPAS separate within a tier?

The report also correlates preference with length difference, so a reviewer can see
whether the human was tracking quality or merely verbosity.

  conda run -n xai python scripts/pairwise_eval.py          # build the sheet + csv
  conda run -n xai python scripts/pairwise_eval.py --report # agreement vs CPAS
"""
from __future__ import annotations

import csv, json, random, sys, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "experiments" / "results"
SHEET = RES / "pairwise_sheet.md"
CSV = RES / "pairwise_choices.csv"
KEYMAP = RES / ".pairwise_keymap.json"
WEAK, STRONG = "ollama-llama3.1-8b", "openai-openai-gpt-5.5"
PERSONAS = ["operator", "data_scientist", "regulator"]
SEED = 20261108


def rows(tag):
    return json.load(open(RES / tag / "cpas_scores.json"))["rows"]


def by_key(tag):
    return {(r["scenario"], r["tier"], r["persona"]): r for r in rows(tag)}


def build_pairs():
    """Stratified pair list. Each entry: (kind, left, right) where each side is
    (run_tag, scenario, tier, persona). `left` is always the one CPAS scores HIGHER —
    presentation order is randomised separately so the sheet gives nothing away."""
    rng = random.Random(SEED)
    w, s = by_key(WEAK), by_key(STRONG)
    scen = sorted({k[0] for k in s})
    pairs = []

    # easy: tier A/B vs tier C, same model. Sanity floor.
    for i, sc in enumerate(rng.sample(scen, 6)):
        p = PERSONAS[i % 3]
        lo_tier = "A" if i % 2 == 0 else "B"
        pairs.append(("easy", (STRONG, sc, "C", p), (STRONG, sc, lo_tier, p)))

    # model: tier C, weak vs strong. The real test — comparable length.
    for i, sc in enumerate(rng.sample(scen, 10)):
        p = PERSONAS[i % 3]
        if s[(sc, "C", p)]["cpas"] >= w[(sc, "C", p)]["cpas"]:
            pairs.append(("model", (STRONG, sc, "C", p), (WEAK, sc, "C", p)))
        else:
            pairs.append(("model", (WEAK, sc, "C", p), (STRONG, sc, "C", p)))

    # discrim: same model+persona, tier C, widest CPAS gap between two scenarios.
    for p in PERSONAS[:2] + PERSONAS[:2]:
        cands = sorted((r for r in rows(STRONG) if r["tier"] == "C" and r["persona"] == p),
                       key=lambda r: r["cpas"])
        pick = [(cands[-1], cands[0]), (cands[-2], cands[1])][len([x for x in pairs
                                                                   if x[0] == "discrim"
                                                                   and x[1][3] == p])]
        hi, lo = pick
        pairs.append(("discrim", (STRONG, hi["scenario"], "C", p),
                      (STRONG, lo["scenario"], "C", p)))
    rng.shuffle(pairs)
    return pairs


def text_of(side):
    tag, sc, tier, p = side
    return (RES / tag / f"{sc}_{tier}_{p}.txt").read_text().strip()


def cpas_of(side):
    tag, sc, tier, p = side
    return by_key(tag)[(sc, tier, p)]["cpas"]


def build_sheet():
    rng = random.Random(SEED + 1)
    pairs = build_pairs()
    md = ["# Pairwise preference — which explanation is more useful?", "",
          "For each item you see **the same incident** explained two ways. Pick the one that",
          "would be **more useful to the named role**. You are comparing, not grading — no",
          "score, no rubric, no power-systems judgement required.", "",
          "Record `1`, `2`, or `=` (about the same) in `pairwise_choices.csv`, then run:", "",
          "```", "conda run -n xai python scripts/pairwise_eval.py --report", "```", "",
          "Which model or tier produced each option is hidden, and the left/right order is",
          "randomised per item. Some pairs are deliberately easy; that is the sanity check.",
          "", "---", ""]
    keymap, csv_rows = {}, []
    for n, (kind, hi, lo) in enumerate(pairs, 1):
        flip = rng.random() < .5                       # randomise which side is shown first
        o1, o2 = (lo, hi) if flip else (hi, lo)
        persona = hi[3]
        md += [f"## Item {n:02d} — role: **{persona.replace('_',' ')}**", "",
               "**Option 1**", "", "```", textwrap.fill(text_of(o1), 94), "```", "",
               "**Option 2**", "", "```", textwrap.fill(text_of(o2), 94), "```", "",
               f"`item {n:02d}` → more useful:  1  /  2  /  =", "", "---", ""]
        keymap[f"{n:02d}"] = {"kind": kind,
                              "opt1": list(o1), "opt2": list(o2),
                              "cpas1": cpas_of(o1), "cpas2": cpas_of(o2),
                              "len1": len(text_of(o1)), "len2": len(text_of(o2))}
        csv_rows.append({"item": f"{n:02d}", "role": persona, "choice": ""})
    SHEET.write_text("\n".join(md))
    with open(CSV, "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=["item", "role", "choice"])
        wtr.writeheader(); wtr.writerows(csv_rows)
    KEYMAP.write_text(json.dumps(keymap, indent=1))
    import collections
    print(f"sheet : {SHEET}")
    print(f"csv   : {CSV}   <- put 1 / 2 / = in the 'choice' column")
    print(f"{len(pairs)} pairs: {dict(collections.Counter(k for k, _, _ in pairs))}")


def report():
    km = json.loads(KEYMAP.read_text())
    got = {}
    with open(CSV) as f:
        for row in csv.DictReader(f):
            c = row["choice"].strip()
            if c in ("1", "2", "="):
                got[row["item"]] = c
    if not got:
        raise SystemExit(f"no choices recorded yet — fill the 'choice' column in {CSV}")

    import collections, statistics as st
    agree = collections.Counter(); total = collections.Counter(); ties = 0
    longer_picked = decided = 0
    for item, c in got.items():
        k = km[item]
        total[k["kind"]] += 1
        if c == "=":
            ties += 1
            continue
        chosen, other = (1, 2) if c == "1" else (2, 1)
        if k[f"cpas{chosen}"] > k[f"cpas{other}"]:
            agree[k["kind"]] += 1
        decided += 1
        longer_picked += k[f"len{chosen}"] > k[f"len{other}"]

    print(f"human vs CPAS, n={len(got)} pairs ({ties} called a tie)\n")
    print(f"{'pair type':12} {'n':>3} {'agree with CPAS':>18}")
    for kind in ("easy", "model", "discrim"):
        if total[kind]:
            print(f"{kind:12} {total[kind]:>3} {agree[kind]}/{total[kind]} "
                  f"({agree[kind]/total[kind]:.0%})".rjust(18))
    n_all = sum(total.values()); a_all = sum(agree.values())
    print(f"{'TOTAL':12} {n_all:>3} {a_all}/{n_all} ({a_all/n_all:.0%})".rjust(18))

    if decided:
        print(f"\nverbosity check: the LONGER option was chosen in "
              f"{longer_picked}/{decided} ({longer_picked/decided:.0%}) decided pairs.")
        print("  ~50% on the 'model' pairs means preference tracked quality, not length.")
        print("  near 100% overall is expected — the 'easy' pairs are long-vs-short by design.")
    print("\nReport the 'model' row as the headline: it is the one where both options are")
    print("full tier-C narratives of comparable length, so only quality separates them.")


if __name__ == "__main__":
    report() if "--report" in sys.argv else build_sheet()
