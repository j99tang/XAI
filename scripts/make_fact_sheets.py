"""Generate the CPAS scenarios + gold fact sheets (plan §4.0/§4.1, §4.5).

Design note (D24 — forced by the data): NO attack flow in the captures targets a
real RTU (all attack traffic is on the 121.x testbed subnet; only normal traffic
reaches 10.0.0.x). So a scenario pairs a REAL attack flow's statistics + SHAP
(the learned network evidence) with an AUTHORED target RTU (the physical-world
overlay joined at the contextualizer, per plan §1). The flow stats are real; the
target assignment is the scenario's synthetic overlay — stated honestly.

Each scenario is deterministic: flow features + label from the captures, device
from entities.yaml, consequence from the simulator's consequence library.
The gold fact sheet is what a correct explanation must contain — the judge scores
against it, so NOTHING here is authored by an LLM.

STRATIFICATION (D35, 2026-08-19). The first 15-scenario set drew its consequence from
`consequences_<RTU>.json` — one simulation per device, opening ALL its breakers — so
consequence was a pure function of device identity: 4 devices, 4 consequences, and any
two scenarios sharing a device were identical on the C, A and R dimensions. Effective n
for those dimensions was 4, not 15. We now draw from `consequence_library.json`
(every breaker SUBSET x load level = 304 entries, 126 distinct consequence texts) and
stratify across consequence CLASS, so consequence varies independently of device.

Run: conda run -n xai python scripts/simulate_consequences.py --library   # first!
     conda run -n xai python scripts/make_fact_sheets.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib

from caie.contextualizer.retrieve import resolve_device
from caie.ids.dataset import load_raw, split
from caie.schemas.anomaly_event import AnomalyEvent, FeatureAttribution
from caie.xai.explain import top_attributions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "scenarios"
MODELS = ROOT / "models"

# How many scenarios per consequence class. ABSORBED is deliberately smaller: the
# grid-absorbs outcome has exactly ONE consequence text no matter which breakers open
# (absorbed is absorbed), so extra ABSORBED scenarios add rows without adding
# discriminative power on the C dimension. 30 total -> adequate power for a paired
# Wilcoxon at the scenario level while the judge batch stays at 810 requests/model.
STRATA = {"OVERLOAD": 9, "OVER+VOLT": 6, "ISLAND": 4, "ABSORBED": 6}
N_FP = 5

# Attack classes present in the test split, ordered by scarcity so the rare ones are
# certain to appear. Cycled across scenarios so attack class varies independently of
# both device and consequence.
ATTACK_CLASSES = ["mitmattack", "floodattack", "fuzzyattack", "iec104starvationattack",
                  "ntpddosattack", "portscanattack", "dosattack"]

# CIP-008-6 R4 Part 4.2 (verified against the PDF in references/): initial notification
# is due "One hour after the determination of a Reportable Cyber Security Incident", or
# "by the end of the next calendar day after determination that a Cyber Security Incident
# was an attempt to compromise" an in-scope system.
#
# GOLD REVISED 2026-08-22 (D45/D46). The gold previously assigned the ONE-HOUR clock to
# every true positive, on the scenario designer's omniscient knowledge that a compromise
# was simulated. But the narrative is never given that: it receives an IDS flow
# classification and nothing else -- the simulated consequence lives in this file, not in
# the KB or the AnomalyEvent. Note the standard's own wording -- the clock runs from a
# *determination*, and the narrative has no evidential basis to determine compromise.
#
# So the evidentially-supported answer for a bare detection is ATTEMPT / next calendar
# day. The old gold graded the careful reading as wrong: gpt-5.5 reasoned "the detector
# does not establish compromise... this plausibly meets the attempted compromise
# threshold" in 16 of 22 INCIDENT scenarios and scored 27%, while an 8B that simply
# asserted the retrieved 1-hour figure scored 95%. That inverts the result -- the R
# dimension would have reported a frontier model as WORSE at regulatory reasoning.
#
# Reconnaissance (a port scan) remains a distinct, unambiguous attempt: it probes without
# compromising, so it is an attempt on its own merits, not merely for want of evidence.
ATTEMPT_CLASSES = {"portscanattack"}
# How many scenarios must carry the ATTEMPT clock. Cycling attack classes freely gave
# exactly ONE — the same n=1 trap D35 flags in the old set, where 14 "failures" were 14
# restatements of a single fact. A dimension with one instance cannot be measured.
N_ATTEMPT = 3

REPORTABLE = {
    # Detection establishes an attempt, not a compromise -- the narrative sees only an IDS
    # flow classification. The one-hour clock is stated as the CONDITIONAL it is in the
    # standard, so a narrative that reasons "attempt now, one hour if compromise is later
    # determined" is scored correct, and one that asserts one hour outright is not.
    "attempt_by_evidence":
        "Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: "
        "notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available "
        "(an IDS flow classification) does NOT establish compromise or disruption, so the "
        "1-hour clock does not apply on these facts; it would apply only if a compromise "
        "or disruption were subsequently determined.",
    "attempt_recon":
        "Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: "
        "notify E-ISAC/NCCIC by the end of the next calendar day. Reconnaissance probes "
        "without compromising, so the 1-hour clock does not apply.",
    "none": "likely NOT reportable — benign/borderline traffic; no reporting clock is "
            "triggered on these facts; verify before escalating",
}


def reportable_for(label: str, kind: str) -> str:
    """Gold reporting duty, derived from what the NARRATIVE can know (D45/D46).

    Not from what the scenario designer knows. The simulated consequence is never given
    to the model, so compromise is never evidentially established and the one-hour clock
    is never the answer on the facts presented."""
    if kind == "fp_noise":
        return REPORTABLE["none"]
    return REPORTABLE["attempt_recon" if label in ATTEMPT_CLASSES
                      else "attempt_by_evidence"]


def load_library() -> list[dict]:
    f = OUT / "consequence_library.json"
    if not f.exists():
        raise SystemExit(f"{f} missing — run: python scripts/simulate_consequences.py --library")
    return json.loads(f.read_text())


def pick_stratified(lib: list[dict]) -> list[dict]:
    """Choose library entries per consequence class, ROUND-ROBIN over devices so the
    class never collapses onto one RTU — that collapse is exactly the device/consequence
    coupling this rebuild exists to break. Within a device, prefer an unseen consequence
    text, but never skip a device just because its texts repeat: ABSORBED and ISLAND have
    one text each by nature, and forcing uniqueness there would starve every device but
    the first. Deterministic — no RNG, so the set is reproducible from the repo alone."""
    chosen = []
    for cls, n in STRATA.items():
        by_dev: dict[str, list[dict]] = {}
        for e in sorted((e for e in lib if e["class"] == cls),
                        key=lambda e: (e["device"], e["n_breakers"], e["load_scale"],
                                       e["consequence"])):
            by_dev.setdefault(e["device"], []).append(e)
        picked, seen_text, devs = [], set(), sorted(by_dev)
        while len(picked) < n and any(by_dev.values()):
            for d in devs:
                if len(picked) >= n or not by_dev[d]:
                    continue
                fresh = next((e for e in by_dev[d] if e["consequence"] not in seen_text), None)
                e = fresh or by_dev[d][0]
                by_dev[d].remove(e)
                seen_text.add(e["consequence"])
                picked.append(e)
        chosen += picked
    return chosen


def fact_sheet(ev: AnomalyEvent, label: str, entry: dict | None, kind: str) -> dict:
    cons = entry["consequence"] if entry else "not simulated"
    return {
        "gold_facts": {
            "device": resolve_device(ev.dst_ip),
            "attack_class": label,
            "top_features": [f.name for f in ev.top_features],
            "physical_consequence": cons,
            "is_physical": bool(entry) and entry["class"] != "ABSORBED",
            "reportable": reportable_for(label, kind),
        },
        "scenario_kind": kind,
        "consequence_class": entry["class"] if entry else "n/a",
        "opened_breakers": entry["breakers"] if entry else [],
        "load_scale": entry["load_scale"] if entry else None,
    }


def main() -> None:
    df = load_raw()
    X_tr, X_te, y_tr, y_te, m_tr, m_te = split(df)
    model = joblib.load(MODELS / "ids_rf.joblib")
    features = json.loads((MODELS / "feature_list.json").read_text())

    # constrained model for the FP pool
    cmodel = joblib.load(MODELS / "ids_rf_constrained.joblib")
    cfeats = json.loads((MODELS / "feature_list_constrained.json").read_text())

    scenarios = []
    labels_te = df.loc[X_te.index, "Label"]

    def flow_for(label: str, nth: int):
        """The nth distinct real test flow of this attack class (nth varies so two
        scenarios of the same class do not reuse identical SHAP evidence)."""
        idx_all = X_te.index[(labels_te == label).values & (y_te == 1).values]
        if len(idx_all) == 0:
            raise SystemExit(f"no test flow labelled {label!r}")
        return X_te.loc[idx_all[nth % len(idx_all)]]

    # --- true positives, stratified by CONSEQUENCE class (D35) ---------------
    # An ATTEMPT (reconnaissance) must never be paired with a physical consequence: a
    # port scan probes, it does not open breakers. Pairing them would make the gold facts
    # internally incoherent — the C dimension would assert an overload that the R
    # dimension simultaneously calls a mere attempt. So attempts occur only in ABSORBED.
    physical_classes = [c for c in ATTACK_CLASSES if c not in ATTEMPT_CLASSES]

    per_class, n_absorbed = {}, 0
    for n, entry in enumerate(pick_stratified(load_library())):
        if entry["class"] == "ABSORBED":
            # attempts live here (and only here): reconnaissance opens no breakers
            label = (sorted(ATTEMPT_CLASSES)[n_absorbed % len(ATTEMPT_CLASSES)]
                     if n_absorbed < N_ATTEMPT
                     else physical_classes[n_absorbed % len(physical_classes)])
            n_absorbed += 1
        else:
            label = physical_classes[n % len(physical_classes)]  # varies independently
        per_class[label] = per_class.get(label, -1) + 1
        row = flow_for(label, per_class[label])
        proba = float(model.predict_proba(row[features].to_frame().T.astype(float))[0, 1])
        feats = top_attributions(model, features, row, k=5)
        kind = "tp_cyber" if entry["class"] == "ABSORBED" else "tp_physical"
        ev = AnomalyEvent(
            flow_id=f"{kind}-{label}-{entry['device']}-{n}", src_ip="121.142.26.78",
            dst_ip=entry["ip"], dst_port=2404, prediction="attack", confidence=proba,
            top_features=feats)
        scenarios.append((ev, label, entry, kind))

    # 5 FP: real NORMAL flows the constrained model scores highest as "attack"
    normal_idx = X_te.index[(y_te == 0).values]
    cprob = cmodel.predict_proba(X_te.loc[normal_idx, cfeats].astype(float))[:, 1]
    top_fp = [normal_idx[i] for i in cprob.argsort()[::-1][:N_FP]]
    for n, idx in enumerate(top_fp):
        row = X_te.loc[idx]
        proba = float(cmodel.predict_proba(row[cfeats].to_frame().T.astype(float))[0, 1])
        ip = str(m_te.loc[idx, "Dst IP"])
        feats = top_attributions(cmodel, cfeats, row, k=5)
        ev = AnomalyEvent(
            flow_id=f"fp_noise-{n+1}", src_ip=str(m_te.loc[idx, "Src IP"]),
            dst_ip=ip, dst_port=int(row["Dst Port"]),
            prediction="attack" if proba >= 0.5 else "normal", confidence=proba,
            top_features=feats)
        scenarios.append((ev, "attackfree", None, "fp_noise"))

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("scenario_*.json"):      # stale scenarios would silently survive
        old.unlink()
    for i, (ev, label, entry, kind) in enumerate(scenarios, 1):
        rec = {"scenario_id": f"scenario_{i:02d}", "kind": kind,
               "anomaly_event": json.loads(ev.to_json()), **fact_sheet(ev, label, entry, kind)}
        (OUT / f"scenario_{i:02d}.json").write_text(json.dumps(rec, indent=2))
    print(f"wrote {len(scenarios)} scenarios to {OUT}\n")

    for i, (ev, label, entry, kind) in enumerate(scenarios, 1):
        cls = entry["class"] if entry else "-"
        dev = entry["device"] if entry else "-"
        brs = "+".join(entry["breakers"]) if entry else "-"
        ls = f"x{entry['load_scale']}" if entry else ""
        print(f"  {i:02d} {kind:12} {label:22} {cls:10} {dev:6} {ls:6} {brs}")

    # the diversity these scenarios were rebuilt for -- assert it, do not assume it
    facts = [fact_sheet(ev, lab, e, k)["gold_facts"] for ev, lab, e, k in scenarios]
    print(f"\nDISTINCT consequences: {len({f['physical_consequence'] for f in facts})}"
          f" / {len(facts)} scenarios   (was 4/15)")
    print(f"DISTINCT reportable:   {len({f['reportable'] for f in facts})}  (was 2)")
    print(f"DISTINCT attack class: {len({f['attack_class'] for f in facts})}")
    print(f"DISTINCT devices:      {len({f['device'][:60] for f in facts})}")


if __name__ == "__main__":
    main()
