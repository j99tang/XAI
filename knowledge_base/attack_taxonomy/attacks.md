# Attack Taxonomy (IEC-104 captures)

One section per attack class present in `data/raw/iec104/`. **Mechanisms are
paraphrased from the SANDI-2024 dataset paper** (Gutiérrez Mlot et al., *Data in
Brief* 57, 2024) — the authoritative description of how *these* traces were
generated — and cross-mapped to **MITRE ATT&CK for ICS** technique IDs.

**Testbed note (bounds every consequence claim):** the attacks were run in a lab
against a simulated RTU/PLC, not against the real substation. The *network
fingerprint* is real data; the *physical consequence* is what such an attack
**would** cause on our synthetic IEEE 14-bus grid, reasoned via
`physics/power_flow_basics.md`, not something observed. State it that way.

**MITRE IDs need verification:** confirm each against https://attack.mitre.org/matrices/ics/
before citing in the thesis (authored from memory; format is validated by
`check_kb.py`, the mapping is not).

---

## attackfree (baseline, label 0)
Normal IEC-104 polling: SCADA-1 (10.0.0.2) opens connections on port 2404 to the
RTUs and exchanges balanced request/response traffic. Fingerprint: regular
`Flow IAT Std`, balanced `Fwd/Bwd Packets/s`, orderly SYN→ACK→FIN. This is the
reference every attack deviates from.

## dos — SYN Denial of Service
- **Mechanism (paper):** many TCP SYN packets sent to the PLC while skipping the SYN+ACK completion — classic half-open flood.
- **Network fingerprint:** high `SYN Flag Count` with low `ACK Flag Count`; high `Fwd Packets/s`, near-zero `Bwd Packets/s`; low `Down/Up Ratio`; many short flows.
- **MITRE ATT&CK for ICS:** T0814 (Denial of Service).
- **Physical consequence (synthetic):** if directed at an RTU, SCADA-1 loses supervisory reach to that substation → **loss of view and control** of its breakers; the grid runs but is unobservable at that node.

## flood — Packet Flooding
- **Mechanism (paper):** the RTU is flooded with messages from the PLC, saturating it.
- **Network fingerprint:** very high `Flow Packets/s` and `Flow Bytes/s`; low `Flow IAT Std` and `Flow IAT Mean` (machine-regular blast); high `Total Fwd Packet`; low packet-length variance (repeated identical frames).
- **MITRE ATT&CK for ICS:** T0814 (Denial of Service); consequence aligns with T0815 (Denial of View).
- **Physical consequence (synthetic):** RTU CPU/link exhaustion → delayed or dropped telemetry → operator flying blind on that zone; sustained flooding can force the RTU offline (as in starvation).

## fuzzy — Fuzzing
- **Mechanism (paper):** random/malformed commands sent to the RTU to induce failures.
- **Network fingerprint:** high `Packet Length Std`/`Variance` (irregular payloads); elevated `PSH Flag Count`/`Fwd PSH Flags` (interactive injection); occasional unusual `URG`/`CWR` flags; irregular `Fwd IAT Std`.
- **MITRE ATT&CK for ICS:** T0855 (Unauthorized Command Message); may cause T0836 (Modify Parameter) or a device fault.
- **Physical consequence (synthetic):** a malformed command the RTU mis-handles could trip or block a breaker unexpectedly, or crash the RTU → unplanned switching or loss of control at its bus.

## mitm — Person-in-the-Middle
- **Mechanism (paper):** ARP poisoning isolates and drops traffic between the RTU and the PLC.
- **Network fingerprint:** subtler — asymmetric/interrupted flows, rising `Bwd IAT Max` (stalled replies), incomplete request/response pairs; volume looks near-normal (why raw stats alone are weak here and context matters most).
- **MITRE ATT&CK for ICS:** T0830 (Adversary-in-the-Middle); enables T0815 (Denial of View), T0856 (Spoof Reporting Message).
- **Physical consequence (synthetic):** SCADA-1 sees stale or spoofed RTU data → operator acts on a false picture; dropped commands mean intended switching never reaches the breaker.

## ntpddos — NTP Denial of Service
- **Mechanism (paper):** the NTP server is attacked to disrupt time synchronization.
- **Network fingerprint:** high-rate traffic toward the NTP service (not port 2404); flood-like `Flow Packets/s` on the time-sync path.
- **MITRE ATT&CK for ICS:** T0814 (Denial of Service) against time service; downstream T0837 (Loss of Protection) risk.
- **Physical consequence (synthetic):** loss of accurate time → mis-ordered event logs and, critically, degraded time-based protection coordination (relay grading assumes synchronized clocks) → protection may mis-operate during a real fault.

## portscan — Port Scanning
- **Mechanism (paper):** reconnaissance against the PLC, RTU, NTP server, and router.
- **Network fingerprint:** many very short flows; high `SYN`/`RST Flag Count`; tiny `Flow Duration`, 1–2 packets each; `Fwd Act Data Pkts` ≈ 0; sweeps across many `Dst Port` values.
- **MITRE ATT&CK for ICS:** T0846 (Remote System Discovery); T0840 (Network Connection Enumeration).
- **Physical consequence (synthetic):** none directly — it is pre-attack reconnaissance. Its value is as an **early warning**: a scan against RTU-3 today predicts a targeted attack tomorrow. (A frequent true-negative-looking-suspicious case for the false-positive scenarios.)

## starvation — Packet Starvation
- **Mechanism (paper):** the RTU is overwhelmed with connections until it stops responding.
- **Network fingerprint:** many concurrent long-lived flows to port 2404; rising `Bwd IAT Max`/`Flow IAT Max` (RTU slowing then silent); high `Total Bwd packets` early then a stall; connection counts far above the RTU's limit.
- **MITRE ATT&CK for ICS:** T0814 (Denial of Service — resource exhaustion); consequence T0813 (Denial of Control).
- **Physical consequence (synthetic):** RTU connection table exhausted → it stops answering SCADA-1 → **full loss of visibility and control** of that substation's breakers until the RTU is restarted; the most direct "lose the substation" attack in this set.

---
**Cross-references:** fingerprints defined in `feature_dictionary/flow_features.md`;
device/bus targets in `topology/ip_device_map.md`; consequence physics in
`physics/power_flow_basics.md`.
