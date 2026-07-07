"""End of Layers 1+2: one flow -> AnomalyEvent JSON (the frozen contract).

Run as a demo on one attack flow from the held-out test split:
  conda run -n xai python -m ccir.xai.emit
"""
from __future__ import annotations

import pandas as pd

from ccir.ids.dataset import load_raw, split
from ccir.schemas.anomaly_event import AnomalyEvent
from ccir.xai.explain import load_model, top_attributions


def emit(model, features: list[str], row: pd.Series, meta: pd.Series, k: int = 5) -> AnomalyEvent:
    proba = float(model.predict_proba(row[features].to_frame().T.astype(float))[0, 1])
    return AnomalyEvent(
        flow_id=str(meta["Flow ID"]),
        src_ip=str(meta["Src IP"]),
        dst_ip=str(meta["Dst IP"]),
        dst_port=int(row["Dst Port"]),
        prediction="attack" if proba >= 0.5 else "normal",
        confidence=proba if proba >= 0.5 else 1 - proba,
        top_features=top_attributions(model, features, row, k),
    )


if __name__ == "__main__":
    model, features = load_model()
    _, X_te, _, y_te, _, m_te = split(load_raw())
    i = (y_te == 1).idxmax()  # first attack flow in the test split
    ev = emit(model, features, X_te.loc[i], m_te.loc[i])
    assert ev.prediction in ("attack", "normal") and len(ev.top_features) == 5
    print(ev.to_json())
