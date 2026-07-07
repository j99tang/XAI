"""Layer 2: SHAP attribution for one flow -> top-k FeatureAttributions.

Feature columns must be ordered exactly per models/feature_list.json — a
wrong order gives silently wrong SHAP values, not an error.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from ccir.schemas.anomaly_event import FeatureAttribution

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


def load_model():
    """-> (fitted RF, ordered feature list). Fails loudly if train.py hasn't run."""
    model_path = MODELS_DIR / "ids_rf.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"{model_path} missing — run `python -m ccir.ids.train` first")
    features = json.loads((MODELS_DIR / "feature_list.json").read_text())
    return joblib.load(model_path), features


def top_attributions(model, features: list[str], row: pd.Series, k: int = 5) -> list[FeatureAttribution]:
    """Top-k features pushing this flow toward "attack", by |SHAP|."""
    x = row[features].to_frame().T.astype(float)  # enforce training column order
    sv = shap.TreeExplainer(model).shap_values(x)
    # this shap version returns (rows, features, classes); slice class 1 = attack
    vals = sv[0][:, 1] if sv.ndim == 3 else sv[0]
    top = np.argsort(-np.abs(vals))[:k]
    return [FeatureAttribution(features[i], float(x.iloc[0, i]), float(vals[i])) for i in top]
