"""Generate the 15 CPAS scenarios + gold fact sheets (plan §4.1, §4.5).

Design note (D24 — forced by the data): NO attack flow in the captures targets a
real RTU (all attack traffic is on the 121.x testbed subnet; only normal traffic
reaches 10.0.0.x). So a scenario pairs a REAL attack flow's statistics + SHAP
(the learned network evidence) with an AUTHORED target RTU (the physical-world
overlay joined at the contextualizer, per plan §1). The flow stats are real; the
target assignment is the scenario's synthetic overlay — stated honestly.

Each scenario is deterministic: flow features + label from the captures, device
from entities.yaml, consequence from experiments/scenarios/consequences_<RTU>.json.
The gold fact sheet is what a correct explanation must contain — the judge scores
against it, so NOTHING here is authored by an LLM.

Run: conda run -n xai python scripts/make_fact_sheets.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib

from ccir.contextualizer.retrieve import resolve_device
from ccir.ids.dataset import load_raw, split
from ccir.schemas.anomaly_event import AnomalyEvent, FeatureAttribution
from ccir.xai.explain import top_attributions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "scenarios"
MODELS = ROOT / "models"

# attack label -> (assigned target RTU, its IP). Physical-consequence RTUs (1,3)
# for TP-physical; operational-only RTUs (2,4) for TP-cyber. From consequences_*.json.
TP_PHYSICAL = [  # 5: attacks assigned to RTUs whose loss causes a physical violation
    ("floodattack", "RTU-3", "10.0.0.5"),
    ("iec104starvationattack", "RTU-3", "10.0.0.5"),
    ("dosattack", "RTU-1", "10.0.0.1"),
    ("fuzzyattack", "RTU-1", "10.0.0.1"),
    ("ntpddosattack", "RTU-3", "10.0.0.5"),
]
TP_CYBER = [  # 5: attacks assigned to RTUs the grid absorbs (operational consequence)
    ("portscanattack", "RTU-2", "10.0.0.3"),
    ("mitmattack", "RTU-2", "10.0.0.3"),
    ("floodattack", "RTU-4", "10.0.0.6"),
    ("dosattack", "RTU-4", "10.0.0.6"),
    ("portscanattack", "RTU-4", "10.0.0.6"),
]


def consequence(rtu: str) -> dict:
    f = OUT / f"consequences_{rtu}.json"
    return json.loads(f.read_text()) if f.exists() else {"consequence": "not simulated"}


def fact_sheet(ev: AnomalyEvent, label: str, rtu: str, kind: str) -> dict:
    cons = consequence(rtu)
    return {
        "gold_facts": {
            "device": resolve_device(ev.dst_ip),
            "attack_class": label,
            "top_features": [f.name for f in ev.top_features],
            "physical_consequence": cons["consequence"],
            "is_physical": cons.get("consequence", "").startswith("physical")
                           or not cons.get("converged", True),
            "reportable": "Reportable Cyber Security Incident (BES Cyber Asset) — "
                          "CIP-008-6: notify E-ISAC/NCCIC within 1 hour"
                          if kind != "fp_noise" else
                          "likely NOT reportable — benign/borderline traffic; verify before escalating",
        },
        "scenario_kind": kind,
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

    def add_tp(specs, kind):
        for label, rtu, ip in specs:
            # a real test flow of this attack class
            mask = (df.loc[X_te.index, "Label"] == label).values & (y_te == 1).values
            idx = X_te.index[mask][0]
            row = X_te.loc[idx]
            proba = float(model.predict_proba(row[features].to_frame().T.astype(float))[0, 1])
            feats = top_attributions(model, features, row, k=5)
            ev = AnomalyEvent(
                flow_id=f"{kind}-{label}-{rtu}", src_ip="121.142.26.78",
                dst_ip=ip, dst_port=2404, prediction="attack", confidence=proba,
                top_features=feats)
            scenarios.append((ev, label, rtu, kind))

    add_tp(TP_PHYSICAL, "tp_physical")
    add_tp(TP_CYBER, "tp_cyber")

    # 5 FP: real NORMAL flows the constrained model scores highest as "attack"
    normal_idx = X_te.index[(y_te == 0).values]
    cprob = cmodel.predict_proba(X_te.loc[normal_idx, cfeats].astype(float))[:, 1]
    top_fp = [normal_idx[i] for i in cprob.argsort()[::-1][:5]]
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
        scenarios.append((ev, "attackfree", "n/a", "fp_noise"))

    OUT.mkdir(parents=True, exist_ok=True)
    for i, (ev, label, rtu, kind) in enumerate(scenarios, 1):
        rec = {"scenario_id": f"scenario_{i:02d}", "kind": kind,
               "anomaly_event": json.loads(ev.to_json()), **fact_sheet(ev, label, rtu, kind)}
        (OUT / f"scenario_{i:02d}.json").write_text(json.dumps(rec, indent=2))
    print(f"wrote {len(scenarios)} scenarios to {OUT}")
    for i, (ev, label, rtu, kind) in enumerate(scenarios, 1):
        print(f"  {i:02d} {kind:12} {label:22} -> {rtu:6} conf={ev.confidence:.2f}")


if __name__ == "__main__":
    main()
