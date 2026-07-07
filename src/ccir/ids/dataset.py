"""Load + consolidate the 8 raw IEC-104 CSVs and split columns by role.

The raw files are immutable evidence (never edited). Each row wears two hats:
- METADATA (Flow ID, IPs, ports, Timestamp): identity — carried through to the
  AnomalyEvent for the contextualizer's IP->device join. NEVER model input
  (Src IP alone separates real from simulated traffic: a label leak).
- FEATURES (flow statistics): behavior — the only thing the model may see.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "iec104"

METADATA_COLS = ["Flow ID", "Src IP", "Src Port", "Dst IP", "Timestamp"]
LABEL_COL = "Label"
NORMAL_LABEL = "attackfree"
RANDOM_STATE = 42


def load_raw() -> pd.DataFrame:
    """All 8 captures, concatenated; inf -> NaN -> dropped (CICFlowMeter emits
    inf in rate columns for zero-duration flows)."""
    files = sorted(RAW_DIR.glob("capture104-*.csv"))
    if len(files) != 8:
        raise FileNotFoundError(f"expected 8 capture CSVs in {RAW_DIR}, found {len(files)}")
    df = pd.concat((pd.read_csv(f, skipinitialspace=True) for f in files), ignore_index=True)
    df[LABEL_COL] = df[LABEL_COL].str.strip()
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    return df


def split(df: pd.DataFrame, test_size: float = 0.3):
    """-> (X_train, X_test, y_train, y_test, meta_train, meta_test).

    y: 1 = attack, 0 = normal. Stratified so the rare normal class is in both halves.
    """
    y = (df[LABEL_COL] != NORMAL_LABEL).astype(int)
    meta = df[METADATA_COLS]
    X = df.drop(columns=METADATA_COLS + [LABEL_COL])
    assert not set(METADATA_COLS) & set(X.columns), "metadata leaked into feature matrix"
    return train_test_split(X, y, meta, test_size=test_size, stratify=y, random_state=RANDOM_STATE)


if __name__ == "__main__":
    df = load_raw()
    X_tr, X_te, y_tr, y_te, m_tr, m_te = split(df)
    print(f"rows after cleaning: {len(df)}  features: {X_tr.shape[1]}")
    print(f"train: {len(y_tr)} (normal={int((y_tr == 0).sum())})  "
          f"test: {len(y_te)} (normal={int((y_te == 0).sum())})")
    assert (y_tr == 0).sum() > 0 and (y_te == 0).sum() > 0, "normal class missing from a split"
    print("self-check OK")
