"""Deliberately weakened IDS variant for false-positive scenarios (plan §4.1).

The full model classifies the test set perfectly, so it cannot produce a false
positive to explain. We drop the top-N most-separating features until the model
makes mistakes — the uncertain regime where explanation actually matters. Save as
models/ids_rf_constrained.joblib. Honest by construction: FP scenarios are labeled
as coming from this variant.

Run: conda run -n xai python -m ccir.ids.train_constrained
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

from ccir.ids.dataset import RANDOM_STATE, load_raw, split

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
# The real/sim separation is extremely redundant (D10): dropping a few features
# leaves it perfect. To reach the *uncertain* regime we drop the strongest 50 AND
# shallow-limit the trees, so the model errs and produces borderline predictions
# on normal flows — the false-positive pool for §4.1 scenarios.
DROP_TOP_N = 50
MAX_DEPTH = 4


def main() -> None:
    X_tr, X_te, y_tr, y_te, _, _ = split(load_raw())

    # rank features on the full model, drop the strongest N
    full = RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                  random_state=RANDOM_STATE, n_jobs=-1).fit(X_tr, y_tr)
    ranked = sorted(zip(X_tr.columns, full.feature_importances_), key=lambda t: -t[1])
    dropped = [n for n, _ in ranked[:DROP_TOP_N]]
    keep = [c for c in X_tr.columns if c not in dropped]

    rf = RandomForestClassifier(n_estimators=50, max_depth=MAX_DEPTH, class_weight="balanced",
                                random_state=RANDOM_STATE, n_jobs=-1).fit(X_tr[keep], y_tr)
    y_pred = rf.predict(X_te[keep])
    proba = rf.predict_proba(X_te[keep])[:, 1]
    # borderline-normal pool: normal flows the weakened model is least sure about
    normal_conf = sorted(proba[(y_te == 0).values], reverse=True)[:10]

    cm = confusion_matrix(y_te, y_pred)
    fp = int(cm[0, 1])  # normal predicted attack
    report = classification_report(y_te, y_pred, target_names=["normal", "attack"],
                                   output_dict=True, zero_division=0)

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(rf, MODELS_DIR / "ids_rf_constrained.joblib")
    (MODELS_DIR / "feature_list_constrained.json").write_text(json.dumps(keep, indent=2))
    (MODELS_DIR / "metrics_constrained.json").write_text(json.dumps(
        {"dropped_features": dropped, "classification_report": report,
         "confusion_matrix": cm.tolist(), "false_positives": fp,
         "conf_range": [round(float(proba.min()), 3), round(float(proba.max()), 3)]}, indent=2))

    print(f"dropped top {DROP_TOP_N} features + max_depth={MAX_DEPTH}; kept {len(keep)}")
    print("confusion matrix [[TN FP][FN TP]]:", cm.tolist())
    print(f"hard false positives: {fp}")
    print(f"borderline-normal attack-probs (top 10): {[round(c,3) for c in normal_conf]}")
    if normal_conf[0] < 0.4:
        print("WARNING: no borderline-normal flows (all confidently normal) — loosen constraint")


if __name__ == "__main__":
    main()
