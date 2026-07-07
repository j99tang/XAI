# Flow Feature Dictionary (CICFlowMeter → attack semantics)

The semantic bridge: it translates a SHAP feature name into what that feature
*means* and which attack behavior a high/low value suggests. Covers exactly the
**78 features the IDS trains on** (`models/feature_list.json`); if that list
changes, regenerate the model card and revisit this file.

**Definitions are paraphrased from CICFlowMeter** (ahlashkari) and the Engelen et
al. corrected-behaviour analysis. Where the two disagree on a rate/timing feature,
this file follows the corrected analysis and says so. A "flow" here is one TCP
connection (5-tuple); "Fwd" = client→server, "Bwd" = server→client.

**Reading the attack column:** these are *statistical fingerprints*, not proof.
The model sees only these numbers — never IEC-104 protocol content (no ASDU, no
IOA). So an entry may say "consistent with flooding," never "malformed ASDU sent."
That distinction is the evidence boundary the contextualizer must respect.

## Timing features (inter-arrival (IAT) and duration)

| Feature | Meaning | HIGH suggests | LOW suggests |
|---|---|---|---|
| Flow Duration | µs from first to last packet of the flow | long-lived session (normal IEC-104 polling; starvation holding a socket open) | very short exchange (scan probe, single SYN) |
| Flow IAT Mean / Std / Max / Min | gaps between consecutive packets, either direction | Std low + Mean low ⇒ machine-regular bursts (flood/DoS); high Max ⇒ stalled connection | uniformly tiny ⇒ packet flood saturating the link |
| Fwd IAT Total/Mean/Std/Max/Min | gaps between client→server packets | bursty command injection (fuzzing, flood) | steady automated polling |
| Bwd IAT Total/Mean/Std/Max/Min | gaps between server→RTU replies | server slowing/stalling ⇒ starvation, DoS pressure | healthy prompt replies |
| Idle Mean/Std/Max/Min | time the flow sat idle (no packets) | long idle then burst (scan sweeps, keep-alive abuse) | continuous traffic (flood) |
| Active Mean/Std/Max/Min | time the flow was continuously active | sustained blast (flood/DoS) | short active bursts (probing) |

## Volume & rate features

| Feature | Meaning | HIGH suggests | LOW suggests |
|---|---|---|---|
| Flow Bytes/s, Flow Packets/s | throughput of the flow | flooding / DoS saturation | reconnaissance (tiny probes) or a stalled victim |
| Fwd Packets/s, Bwd Packets/s | per-direction packet rate | high Fwd + low Bwd ⇒ one-sided flood/SYN storm (victim not replying) | balanced ⇒ normal request/response |
| Total Fwd Packet, Total Bwd packets | packet counts per direction | large asymmetric counts ⇒ flood/starvation | 1–2 packets ⇒ scan |
| Total Length of Fwd/Bwd Packet | total bytes per direction | bulk injection (fuzzing payloads) | control-only traffic |
| Down/Up Ratio | Bwd bytes ÷ Fwd bytes | server dumping data | attacker sending, server silent (flood, SYN DoS) |

## Packet-size features

| Feature | Meaning | HIGH suggests | LOW suggests |
|---|---|---|---|
| Fwd/Bwd Packet Length Max/Min/Mean/Std | per-direction packet-size distribution | high Std ⇒ irregular payloads (fuzzing); large Max ⇒ bulk transfer | uniform tiny packets ⇒ flood of identical frames |
| Packet Length Min/Max/Mean/Std/Variance | size distribution over the whole flow | high variance ⇒ malformed/random content (fuzzing) | zero variance ⇒ repeated identical packets (flood, replay-like) |
| Average Packet Size, Fwd/Bwd Segment Size Avg | mean segment sizes | large ⇒ data transfer | minimal ⇒ signalling/probing |

## TCP flag features

| Feature | Meaning | HIGH suggests | LOW suggests |
|---|---|---|---|
| SYN Flag Count | connection-open requests | many SYNs without completion ⇒ SYN-flood DoS or port scan | normal (1 per connection) |
| ACK Flag Count | acknowledgements | normal established traffic | absent ⇒ half-open connections (SYN DoS) |
| FIN / RST Flag Count | connection close / reset | many RSTs ⇒ scan hitting closed ports, or victim rejecting flood | orderly FIN ⇒ normal teardown |
| PSH Flag Count, Fwd/Bwd PSH Flags | push-data flags | frequent PSH ⇒ interactive command injection (fuzzing) | batch/polling |
| URG / CWR / ECE Flag Count, Fwd/Bwd URG Flags | urgent + congestion flags | unusual URG/CWR set ⇒ crafted/malformed packets (fuzzing, scan fingerprinting) | normally zero |

## Header, window & bulk features

| Feature | Meaning | HIGH suggests | LOW suggests |
|---|---|---|---|
| Fwd/Bwd Header Length | total TCP/IP header bytes per direction | many small packets (headers dominate) ⇒ flood/scan | few large packets |
| FWD/Bwd Init Win Bytes | initial TCP receive-window advertised | fingerprintable stack (scan tooling) | — |
| Fwd Act Data Pkts | client packets actually carrying payload | bulk command injection | pure signalling (SYN scan carries none) |
| Fwd Seg Size Min | smallest client segment | tiny ⇒ probe/keep-alive | — |
| Fwd/Bwd Bytes/Packet/Bulk Avg, Bulk Rate Avg | bulk-transfer estimators | sustained bulk (flood payloads) | control traffic (usually ~0) |
| Subflow Fwd/Bwd Packets/Bytes | per-subflow volume | large ⇒ sustained attack flow | small ⇒ short probe |

## Identity / low-signal features

| Feature | Meaning | Note |
|---|---|---|
| Dst Port | destination TCP port | 2404 = IEC-104 endpoint (RTU). NOT a leak here — the Phase 1 audit found it outside the top-10 importances; scans/DoS hit varied ports, so it carries mild signal only. |
| Protocol | IP protocol number (6 = TCP) | near-constant in this dataset; low signal. |

**Cross-references:** attack fingerprints above are expanded per attack class in
`attack_taxonomy/attacks.md`; physical consequences in `physics/power_flow_basics.md`.
