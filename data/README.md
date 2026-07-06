# Data

**This folder's raw/processed contents are git-ignored** (large + regenerable). Only this
README is committed. A collaborator re-creates the data by following the provenance below.

## Provenance
Source: **SANDI-2024** (Substation Anomaly Network Data for Intrusion detection, 2024) —
IEC 60870-5-104 telecontrol traffic. Attack-free traffic is a **real** substation capture;
attack traffic is **lab-simulated**. Original dataset README: `references/SANDI-2024_dataset_README.md`.
Feature extraction: CICFlowMeter-style flow statistics (79 features + label).

## Layout
- `raw/iec104/` — the 8 original CSVs + `headers_iec104*.txt`. Never edit by hand.
- `processed/` — merged + train/test splits (written by `ccir.ids`). Regenerable.

## ⚠️ Two facts every consumer of this data must know
1. **Features are flow statistics only** (`Flow IAT Std`, `Bwd Packet Length Max`, …).
   There is **no ASDU TypeID / IOA / protocol-semantic field**. SHAP can only attribute to
   flow behavior — topology is joined later in the knowledge graph, not learned here.
2. **Real vs. simulated live on different subnets** (attack-free `10.0.0.x`; attacks
   `121.142.26.x` etc.). Therefore **IP / subnet must NEVER be a model feature** — it would
   be a near-perfect label leak. `Dst Port` should also be audited for the same reason.

## Size warning
`capture104-dosattack.csv` is ~123 MB — **over GitHub's 100 MB file limit**. Keep it local.
