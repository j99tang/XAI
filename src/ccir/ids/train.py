"""Train the binary IDS (Layer 1) and persist model + feature list + metrics.

class_weight="balanced" instead of SMOTE: reweights real rows rather than
fabricating synthetic ones, so downstream SHAP explains only real data.
Run: conda run -n xai python -m ccir.ids.train
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

from ccir.ids.dataset import RANDOM_STATE, load_raw, split

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
MODEL_PATH = MODELS_DIR / "ids_rf.joblib"
FEATURES_PATH = MODELS_DIR / "feature_list.json"
METRICS_PATH = MODELS_DIR / "metrics.json"


def main() -> None:
    X_tr, X_te, y_tr, y_te, _, _ = split(load_raw())

    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
    )
    rf.fit(X_tr, y_tr)
    y_pred = rf.predict(X_te)

    report = classification_report(
        y_te, y_pred, target_names=["normal", "attack"], output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_te, y_pred).tolist()
    # top importances printed for the Phase 1.3 leakage audit
    importances = sorted(zip(X_tr.columns, rf.feature_importances_), key=lambda t: -t[1])

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(rf, MODEL_PATH)
    FEATURES_PATH.write_text(json.dumps(list(X_tr.columns), indent=2))
    METRICS_PATH.write_text(json.dumps(
        {"classification_report": report, "confusion_matrix": cm,
         "top_importances": [(n, round(v, 4)) for n, v in importances[:15]]}, indent=2))

    print(json.dumps(report, indent=2))
    print("confusion matrix [[TN FP][FN TP]]:", cm)
    print("\ntop-10 importances (leakage audit — investigate any single dominant feature):")
    for name, val in importances[:10]:
        print(f"  {val:.4f}  {name}")
    print(f"\nsaved: {MODEL_PATH.name}, {FEATURES_PATH.name}, {METRICS_PATH.name} -> {MODELS_DIR}")


if __name__ == "__main__":
    main()
