# run: conda run -n xai python tests/test_scenarios.py  (reads generated scenarios only)
import collections, glob, json

rows = [json.loads(open(f).read()) for f in sorted(glob.glob("experiments/scenarios/scenario_*.json"))]
assert rows, "no scenarios -- run scripts/make_fact_sheets.py"
gold = [r["gold_facts"] for r in rows]

# D35: consequence must NOT be a function of device. In the old set it was (one sim per
# RTU), so effective n on C/A/R was 4. Each device must now carry several consequences.
# key on dst_ip, NOT the device sentence: every device string starts with the same
# 40-char "DEVICE (authoritative, from IP map): 10." prefix, which silently collapses
# them all into one bucket and makes these assertions pass vacuously.
by_dev = collections.defaultdict(set)
for r in rows:
    if r["consequence_class"] != "n/a":
        by_dev[r["anomaly_event"]["dst_ip"]].add(r["gold_facts"]["physical_consequence"])
assert by_dev, "no simulated scenarios"
assert min(len(v) for v in by_dev.values()) > 1, \
    f"a device has only one consequence -- coupling is back: { {k: len(v) for k, v in by_dev.items()} }"

# every consequence class must span multiple devices (else the class IS a device)
by_cls = collections.defaultdict(set)
for r in rows:
    if r["consequence_class"] != "n/a":
        by_cls[r["consequence_class"]].add(r["anomaly_event"]["dst_ip"])
assert min(len(v) for v in by_cls.values()) > 1, \
    f"a class collapsed onto one device: { {k: len(v) for k, v in by_cls.items()} }"

# D36: the overload path must actually be exercised -- it was dead code before
assert any("overload" in g["physical_consequence"] for g in gold), \
    "no scenario has an overload; ratings have regressed to unlimited"
assert any("islanding" in g["physical_consequence"] for g in gold)

# R needs >= 3 reportable classes with a real stratum each, not a single instance
# full string, not a prefix: both ATTEMPT variants share their first 30 chars, so a
# prefix key silently collapsed them into one class
rep = collections.Counter(g["reportable"] for g in gold)
assert len(rep) >= 3, f"R has only {len(rep)} classes: {list(rep)}"
assert min(rep.values()) >= 3, f"a reportable class has too few instances: {dict(rep)}"

# Coherence under the D46 gold. `reportable` is now EVIDENCE-relative (what the narrative
# can determine from an IDS classification), while `physical_consequence` is SIMULATION
# ground truth (what actually happened). Those can legitimately disagree -- a real overload
# occurred, yet the narrative cannot establish it -- but only if the gold says so
# explicitly, otherwise the answer key reads as self-contradictory to the judge.
for r in rows:
    g = r["gold_facts"]
    if "ATTEMPT" in g["reportable"] and g["is_physical"]:
        assert "does NOT establish compromise or disruption" in g["reportable"], (
            f"{r['scenario_id']}: gold pairs a physical consequence with an ATTEMPT duty "
            f"but does not explain that the duty is evidence-relative")
# reconnaissance is an attempt on its own merits and must carry no physical consequence
for r in rows:
    if "Reconnaissance probes" in r["gold_facts"]["reportable"]:
        assert not r["gold_facts"]["is_physical"], \
            f"{r['scenario_id']}: recon attempt paired with a physical consequence"

# gold facts stay LLM-free and internally consistent
for r in rows:
    g = r["gold_facts"]
    phys = g["physical_consequence"]
    assert g["is_physical"] == (phys.startswith("physical") or phys.startswith("islanding")), \
        f"{r['scenario_id']}: is_physical disagrees with the consequence text"

print(f"ok -- {len(rows)} scenarios, {len({g['physical_consequence'] for g in gold})} consequences, "
      f"{len(rep)} reportable classes, {len({g['attack_class'] for g in gold})} attack classes")
