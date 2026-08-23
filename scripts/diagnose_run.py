"""Free pre-flight diagnostics on a generated run — no API cost.

Purpose: catch PIPELINE defects before spending a judge batch. It has done so seven
times (D39-D47). It is NOT a quality metric and must not be read as one.

Hard limit, learned the hard way: these are regex proxies. They score flat assertions
("notify within one hour") reliably and conditional reasoning ("if determined to be an
attempt, by the end of the next calendar day") unreliably — producing three false
readings on gpt-5.5 output in one session. Where a column is marked (proxy), a low
number means "look at the narratives", never "the model is worse".

Run: conda run -n xai python scripts/diagnose_run.py <run_tag> [<run_tag> ...]
"""
from __future__ import annotations
import glob, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECS = {json.loads(Path(f).read_text())["scenario_id"]: json.loads(Path(f).read_text())
        for f in glob.glob(str(ROOT / "experiments/scenarios/scenario_*.json"))}
PERSONAS = ["operator", "data_scientist", "regulator"]
TIERS = ["A", "B", "C"]
ALL_DEV = re.compile(r"\b(RTU-\d|ENG-WS-\d|SCADA-\d)\b")


def diagnose(tag: str) -> None:
    run = ROOT / "experiments" / "results" / tag
    man = json.loads((run / "manifest.json").read_text())
    print(f"\n{'='*74}\n{tag}   synthesizer={man['synth_model']}   {man['generated_utc']}\n{'='*74}")

    # --- integrity -------------------------------------------------------
    files = list(run.glob("scenario_*.txt"))
    empty = [f.name for f in files if not f.stat().st_size]
    print(f"integrity: {len(files)}/270 files, {len(empty)} empty, manifest {len(man['scenarios'])}/30")

    # --- length by tier (the §7.6 #1 verbosity control) ------------------
    print(f"\nlength by tier (chars) — verbosity control, §7.6 #1")
    for t in TIERS:
        w = [len((run / f"{s}_{t}_{p}.txt").read_text()) for s in RECS for p in PERSONAS]
        print(f"  tier {t}: mean {st.mean(w):>6.0f}  min {min(w):>5}  max {max(w):>5}")

    # --- tier-C grounding: is the right device named, and no other? -------
    dev_ok = dev_other = dev_absent = 0
    for sid, rec in RECS.items():
        want = ALL_DEV.search(rec["gold_facts"]["device"])
        want = want.group(1) if want else None
        for p in PERSONAS:
            t = (run / f"{sid}_C_{p}.txt").read_text()
            named = set(ALL_DEV.findall(t))
            if want in named and not (named - {want}): dev_ok += 1
            elif named - {want}: dev_other += 1
            else: dev_absent += 1
    n = len(RECS) * 3
    print(f"\ntier-C device grounding ({n} narratives)")
    print(f"  correct device, no other named : {dev_ok:>3} ({dev_ok/n:.0%})")
    print(f"  names a DIFFERENT device       : {dev_other:>3} ({dev_other/n:.0%})   <- hallucination risk")
    print(f"  names no device at all         : {dev_absent:>3} ({dev_absent/n:.0%})")

    # --- data-scientist feature fidelity (the D40 regression guard) -------
    good = sum(sum(f["name"] in (run / f"{sid}_C_data_scientist.txt").read_text()
                   for f in rec["anomaly_event"]["top_features"]) >= 3
               for sid, rec in RECS.items())
    print(f"\ndata-scientist cites >=3 real SHAP features: {good}/{len(RECS)}  (D40 guard)")

    # --- attack class named (D27 diagnostic, never part of CPAS) ---------
    named = sum(rec["gold_facts"]["attack_class"].lower().replace("attack", "") in
                (run / f"{sid}_C_data_scientist.txt").read_text().lower()
                for sid, rec in RECS.items() if rec["gold_facts"]["attack_class"] != "attackfree")
    tot = sum(1 for r in RECS.values() if r["gold_facts"]["attack_class"] != "attackfree")
    print(f"attack class named correctly (DIAGNOSTIC, D27): {named}/{tot}")

    # --- cross-persona bleed: did tier C collapse into one voice? ---------
    same = sum(len({(run / f"{sid}_C_{p}.txt").read_text() for p in PERSONAS}) < 3
               for sid in RECS)
    print(f"scenarios where 2+ personas produced IDENTICAL text: {same}/{len(RECS)}"
          f"{'   <- persona collapse' if same else ''}")


for tag in (sys.argv[1:] or ["ollama-llama3.1-8b"]):
    diagnose(tag)
print("\n(proxy caveat: regex checks read flat assertions well and conditional reasoning"
      "\n poorly — treat low numbers as 'go read the narratives', not as quality.)")
