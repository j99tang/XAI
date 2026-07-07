# Data Reality Note (Phase 0.3)

Two facts about the SANDI-2024 IEC-104 CSVs that constrain the whole project.
This note becomes the *Limitations* paragraph of the final report.

## 1. The model can only ever see flow statistics

The CSVs are **CICFlowMeter output**: 84 columns = 5 identity/metadata columns
(`Flow ID`, `Src IP`, `Src Port`, `Dst IP`, `Timestamp`) + 78 flow statistics
(`Flow IAT Std`, `Bwd Packet Length Max`, `SYN Flag Count`, …) + `Label`.

There is **no IEC-104 protocol semantics in the data** — no ASDU TypeID, no IOA,
no cause-of-transmission. SHAP can therefore only attribute to *network behavior*
(timing, sizes, flags), never to *telecontrol meaning*. The proposal's original
story ("SHAP flags ASDU TypeID 46 → map to a breaker") cannot be told with this
data. Instead, the semantic hop happens downstream: the contextualizer joins the
flow's IP/port metadata to an authored IP→device map, and the feature dictionary
translates flow-statistic patterns into attack behaviors.

Consequence for the architecture: topology is a knowledge-graph overlay,
**never a training feature**.

## 2. Real and simulated traffic live on different subnets

Attack-free (real testbed) traffic is on `10.0.0.x`; every attack capture was
generated on other subnets (e.g. `121.142.26.x`). Source IP alone nearly
perfectly separates the classes.

Consequences:
- **IPs must never enter the feature matrix** — they are a label leak, not a signal.
- Any single feature that encodes the same artifact indirectly (candidate:
  `Dst Port`) must be audited before keeping it (Phase 1.3).
- Reported detection metrics measure separation of *this testbed's* normal vs
  attack traffic; there is a real/simulated **domain shift**, so field
  generalization is not claimed.

## 3. Class imbalance (context for metric choice)

~320k rows total; the attack-free class is a small minority (the original
authors' log shows a majority-class dummy classifier already at 0.86 accuracy).
Accuracy is therefore meaningless here; the project reports
precision/recall/F1 and confusion matrices, and trains with
`class_weight="balanced"` instead of synthetic oversampling (SMOTE), so SHAP
attributions describe real rows only.

## What this note is NOT

Not a criticism of the dataset — it is a statement of what claims the data can
and cannot support, written before modeling so the limitations section is
pre-committed rather than post-hoc.
