# CPAS human-scoring worksheet

Score each narrative against the **gold facts shown with it** — not against
power-systems knowledge. The simulator already made the physics judgement.
Record scores in `human_scores.csv`, then run:

```
conda run -n xai python scripts/human_score.py --report
```

Run and tier are deliberately hidden so you cannot infer which model wrote it.
Some narratives are four-line alerts that score ~1 on everything — that is expected.

---

**D — Diagnostic accuracy — is it GROUNDED?**

```
5 names the right device AND its bus, and characterises the anomaly consistently
  with the evidence (either the right class OR an honest 'the detector cannot tell')
4 device+bus right, characterisation vague
3 device OR characterisation, not both
2 weak grounding; device absent or wrong
1 no physical referent, or a wrong class asserted as established fact
```

**C — Consequence — does it match the gold?**

```
5 matches the gold physical consequence incl. direction and affected element
3 vague or partial
1 contradicts it
IF gold says 'not simulated' (a false positive): 5 = correctly says no physical
  impact is established; 1 = invents one
```

**A — Actionability — a next step FOR THIS ROLE?**

```
5 specific, correct, role-appropriate next step
3 generic step
1 none
A step belonging to a different role earns no credit
```

**R — Role fit — does it deliver what this persona was asked for?**

```
5 matches the persona's deliverable and voice; states the right reporting duty
  where that is part of the role
3 partial
1 wrong framing, or another role's content
```

**H — Hallucination — 0 or 1**

```
1 if it CONTRADICTS a grounded fact: device identity, bus, breaker, physical
  consequence, or reporting obligation
0 otherwise.
NOT a hallucination: naming the wrong attack class (the detector is binary and
  never told it the class) — reflect that in D instead.
```

---

## Item 01 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.6 = RTU-4, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-S, at Bus 9, controls breakers BR-4-9, BR-7-9, BR-9-10, BR-9-14, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: attackfree
- **physical_consequence**: not simulated
- **reportable**: likely NOT reportable — benign/borderline traffic; no reporting clock is triggered on these facts; verify before escalating

**Narrative**

```
Based on the provided context, I will analyze the flow features that drove the prediction and what they mean.

The model predicted a normal flow with a confidence of 0.14. The top SHAP features contributing to this prediction are:

* Flow Bytes/s: -0.083 (low value)
* Fwd Packet Length Max: -0.076 (low value)
* Fwd IAT Max: -0.068 (low value)
* Subflow Fwd Packets: -0.052 (zero value)
* FWD Init Win Bytes: -0.049 (low value)

These features indicate a low-volume flow with small packet sizes and short inter-arrival times. The presence of zero subflow forward packets suggests that the flow is not carrying any significant data.

Considering the context, this flow appears to be control traffic from RTU-4 (10.0.0.6) on port 2404, which is a typical IEC-104 endpoint for SCADA communication. The low volume and small packet sizes are consistent with control traffic, which often carries minimal data.

The model's confidence of 0.14 suggests that the features do not strongly indicate an attack, but rather a normal flow. However, it is essential to note that this prediction is based on statistical patterns in the flow features and may not necessarily prove or disprove specific protocol actions.
```

`item 01` → D __  C __  A __  R __  H __

---

## Item 02 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.6 = RTU-4, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-S, at Bus 9, controls breakers BR-4-9, BR-7-9, BR-9-10, BR-9-14, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: attackfree
- **physical_consequence**: not simulated
- **reportable**: likely NOT reportable — benign/borderline traffic; no reporting clock is triggered on these facts; verify before escalating

**Narrative**

```
INTRUSION ALERT
prediction: normal
confidence: 0.14
destination: 10.0.0.6:2404
top SHAP features (toward 'attack'):
  Flow Bytes/s: value=24321.1, SHAP=-0.083
  Fwd Packet Length Max: value=16, SHAP=-0.076
  Fwd IAT Max: value=8303, SHAP=-0.068
  Subflow Fwd Packets: value=0, SHAP=-0.052
  FWD Init Win Bytes: value=259, SHAP=-0.049
```

`item 02` → D __  C __  A __  R __  H __

---

## Item 03 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: iec104starvationattack
- **physical_consequence**: physical: overloads: line 1 @ 122.5%, line 6 @ 116.6%; voltage: bus 5 @ 0.94pu
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
top SHAP features (toward 'attack'):
  Flow IAT Min: value=5, SHAP=+0.116
  Bwd Packet Length Min: value=0, SHAP=+0.091
  Packet Length Min: value=0, SHAP=+0.084
  Packet Length Max: value=90, SHAP=+0.058
  Fwd PSH Flags: value=0, SHAP=+0.054
```

`item 03` → D __  C __  A __  R __  H __

---

## Item 04 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: iec104starvationattack
- **physical_consequence**: physical: overloads: line 1 @ 122.5%, line 6 @ 116.6%; voltage: bus 5 @ 0.94pu
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
**Regulatory Assessment**

This incident involves a potential cyber security threat to a BES Cyber Asset, specifically RTU-1 at Bus 2, which controls critical breakers BR-1-2, BR-2-3, BR-2-4, and BR-2-5. The detector has predicted an attack with high confidence (1.00) on the IEC-104 endpoint at port 2404 of RTU-1.

Based on NERC CIP-008-6, this incident plausibly meets the threshold for a Reportable Cyber Security Incident as it involves an attempted compromise of a BES Cyber System. The reporting timeline applies: within one hour of determining the incident, notification is due to both the E-ISAC and NCCIC/CISA (under US jurisdiction).

The required attributes for initial notification include functional impact, attack vector, and level of intrusion. Although some of these may be unknown at first notification, they will need to be provided as updates follow.

This response sits under the **Detect** capability of the CSF functions, which is mapped to NIST SP 800-61r3's incident handling lifecycle.
```

`item 04` → D __  C __  A __  R __  H __

---

## Item 05 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.6 = RTU-4, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-S, at Bus 9, controls breakers BR-4-9, BR-7-9, BR-9-10, BR-9-14, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: mitmattack
- **physical_consequence**: physical: overloads: line 7 @ 168.6%, line 9 @ 131.3%, line 12 @ 138.6%, line 14 @ 163.1%; voltage: bus 9 @ 0.918pu, bus 10 @ 0.931pu, bus 14 @ 0.936pu
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
Affected: RTU-4, GridCom GC-4000 RTU at Bus 9, ZONE-S; substation name not in context. It controls BR-4-9, BR-7-9, BR-9-10, BR-9-14.

This incident evidence: attack alert to 10.0.0.6:2404 with flow statistics showing very tight packet timing and zero/minimal packet lengths. Detector did not see IEC-104 contents or breaker commands.

Immediate physical risk: RTU-4 telemetry/control for Bus 9 breakers may be delayed, dropped, or unreliable. No breaker trip/open/close is in context.

Next actions:
1. Treat RTU-4 remote operation as suspect; do not issue non-essential remote switching through RTU-4.
2. Verify current status/indications for BR-4-9, BR-7-9, BR-9-10, BR-9-14 by available trusted means; trusted alternate indication is not in context.
3. Check RTU-4 communications/health and Bus 9 breaker status before any switching.
4. Do not open/close breakers based on this alert alone; no electrical fault or overload is in context.
5. Manual control capability/procedure is not in context; switch to manual only if approved local procedure confirms safe manual operation.
```

`item 05` → D __  C __  A __  R __  H __

---

## Item 06 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.3 = RTU-2, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-C, at Bus 4, controls breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: ntpddosattack
- **physical_consequence**: islanding / loss of supply — network does not solve with these branches open (a bus or group is de-energized)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.3:2404
```

`item 06` → D __  C __  A __  R __  H __

---

## Item 07 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: iec104starvationattack
- **physical_consequence**: physical: overloads: line 1 @ 122.5%, line 6 @ 116.6%; voltage: bus 5 @ 0.94pu
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
Based on the model's output, the top SHAP features driving the prediction of an attack are:

* Flow IAT Min: value=5, SHAP=+0.116
* Bwd Packet Length Min: value=0, SHAP=+0.091
* Packet Length Min: value=0, SHAP=+0.084
* Packet Length Max: value=90, SHAP=+0.058
* Fwd PSH Flags: value=0, SHAP=+0.054

These features indicate a flow with short inter-arrival times (IAT) and small packet lengths, which is characteristic of a flood/scan attack family. The presence of zero Bwd Packet Length Min suggests that the destination is not responding to incoming packets.

The model's confidence in this prediction is 1.00, indicating high certainty. However, it's essential to note that these features can only provide statistical evidence and do not prove specific protocol actions or attack classes. Further analysis is required to determine the actual nature of the attack.

In particular, the feature "Flow IAT Min" suggests a potential flood/scan attack, but without more context, it's difficult to say whether this is a legitimate concern or simply normal traffic.
```

`item 07` → D __  C __  A __  R __  H __

---

## Item 08 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.3 = RTU-2, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-C, at Bus 4, controls breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: dosattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.3:2404
top SHAP features (toward 'attack'):
  Bwd IAT Min: value=0, SHAP=+0.063
  Flow IAT Min: value=295, SHAP=+0.053
  Packet Length Min: value=0, SHAP=+0.043
  Packet Length Max: value=0, SHAP=+0.036
  Bwd Packet Length Min: value=0, SHAP=+0.035
```

`item 08` → D __  C __  A __  R __  H __

---

## Item 09 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.3 = RTU-2, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-C, at Bus 4, controls breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: dosattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.3:2404
top SHAP features (toward 'attack'):
  Bwd IAT Min: value=0, SHAP=+0.063
  Flow IAT Min: value=295, SHAP=+0.053
  Packet Length Min: value=0, SHAP=+0.043
  Packet Length Max: value=0, SHAP=+0.036
  Bwd Packet Length Min: value=0, SHAP=+0.035
```

`item 09` → D __  C __  A __  R __  H __

---

## Item 10 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.6 = RTU-4, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-S, at Bus 9, controls breakers BR-4-9, BR-7-9, BR-9-10, BR-9-14, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: attackfree
- **physical_consequence**: not simulated
- **reportable**: likely NOT reportable — benign/borderline traffic; no reporting clock is triggered on these facts; verify before escalating

**Narrative**

```
Illustrative assessment only: the context notes this is a synthetic grid, not a jurisdictional determination.

Observed event: an intrusion alert for traffic to 10.0.0.6:2404, mapped authoritatively to RTU-4, an IEC-104 controlled station in ZONE-S at Bus 9 controlling BR-4-9, BR-7-9, BR-9-10, and BR-9-14. RTU-4 is identified as a BES Cyber Asset under NERC CIP.

Reportability: based on the provided facts, this is not yet determined to be a NERC CIP-008-6 Reportable Cyber Security Incident. The detector prediction is “normal” with confidence 0.14, and it observes network flow statistics only. No compromise, disruption, or attempted compromise of a BES Cyber System or associated EACMS/PACS is established in context; attack vector, functional impact, and level of intrusion are not in context.

Timeline/to whom: no notification clock is triggered on these facts. If later determined to be a Reportable Cyber Security Incident, initial notification is within one hour; if determined to be an attempt to compromise an in-scope system, notification is by the end of the next calendar day. Notify E-ISAC and, under US jurisdiction, NCCIC/CISA.

Framework function: Detect.
```

`item 10` → D __  C __  A __  R __  H __

---

## Item 11 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.3 = RTU-2, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-C, at Bus 4, controls breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: floodattack
- **physical_consequence**: physical: overloads: line 2 @ 101.2%
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
**Incident Briefing**

**Affected Device:** RTU-2, 10.0.0.3, Zone C, Bus 4
**Physical Risk:** Potential loss of control and view of breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9

**Incident Analysis:**

The intrusion alert indicates a potential attack on RTU-2. The observed pattern shows high frequency of small packets with zero bytes, indicating a flood-like behavior. This is consistent with a flooding attack, which can cause the RTU to become overwhelmed and lose control of its breakers.

**Immediate Action:**

1. Switch to manual control for Zone C to prevent any potential loss of control.
2. Check breaker status for BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9 to ensure they are not affected by the attack.
3. Verify that RTU-2 is functioning correctly and not compromised.

**Next Steps:**

1. Investigate the source of the attack and take necessary measures to prevent future incidents.
2. Review and update security protocols for RTUs and other critical devices in the grid.

**Priority:** Safety and continuity of the physical process are paramount. Take immediate action to prevent any potential loss of control or view of breakers.
```

`item 11` → D __  C __  A __  R __  H __

---

## Item 12 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: ntpddosattack
- **physical_consequence**: physical: overloads: line 2 @ 103.3%
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
top SHAP features (toward 'attack'):
  Flow IAT Min: value=310, SHAP=+0.135
  Packet Length Max: value=48, SHAP=+0.096
  Bwd IAT Min: value=640, SHAP=+0.093
  Fwd PSH Flags: value=0, SHAP=+0.047
  Flow IAT Mean: value=1115.84, SHAP=+0.031
```

`item 12` → D __  C __  A __  R __  H __

---

## Item 13 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: portscanattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. Reconnaissance probes without compromising, so the 1-hour clock does not apply.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
```

`item 13` → D __  C __  A __  R __  H __

---

## Item 14 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.6 = RTU-4, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-S, at Bus 9, controls breakers BR-4-9, BR-7-9, BR-9-10, BR-9-14, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: attackfree
- **physical_consequence**: not simulated
- **reportable**: likely NOT reportable — benign/borderline traffic; no reporting clock is triggered on these facts; verify before escalating

**Narrative**

```
INTRUSION ALERT
prediction: normal
confidence: 0.14
destination: 10.0.0.6:2404
```

`item 14` → D __  C __  A __  R __  H __

---

## Item 15 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: ntpddosattack
- **physical_consequence**: physical: overloads: line 2 @ 103.3%
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
The binary detector labeled the flow to 10.0.0.1:2404, RTU-1’s IEC-104 endpoint, as attack with confidence 1.00.

Main positive drivers were timing and small-packet statistics: Flow IAT Min=310 (SHAP +0.135), Bwd IAT Min=640 (+0.093), and Flow IAT Mean=1115.84 (+0.031) indicate the model saw short/regular inter-arrival timing; low Flow IAT Mean is described in context as part of machine-regular flood fingerprints. Packet Length Max=48 (+0.096) means even the largest packet was small, matching the “many small packets / headers dominate” fingerprint associated with flood/scan behavior. Fwd PSH Flags=0 (+0.047) also pushed toward attack, but its detailed semantic meaning is not in context beyond the feature name/value.

This signature is best characterized as a flooding/scanning-family statistical fingerprint: small packets plus tight inter-arrival timing resemble the documented flood/scan indicators. Because the detector is binary, it does not identify whether this is DoS, flood, scan, or another class.

Caveat: the model sees CICFlowMeter flow statistics only, not IEC-104 protocol semantics. These features can support an anomalous traffic-pattern explanation toward an RTU endpoint, but they cannot prove specific IEC-104 commands, attacker intent, or physical grid consequences.
```

`item 15` → D __  C __  A __  R __  H __

---

## Item 16 — persona: **regulator**

*Asked for:* compliance assessment: what happened, which asset, is it reportable, WHICH CLOCK, to whom. Switching instructions are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: iec104starvationattack
- **physical_consequence**: islanding / loss of supply — network does not solve with these branches open (a bus or group is de-energized)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
```

`item 16` → D __  C __  A __  R __  H __

---

## Item 17 — persona: **operator**

*Asked for:* action briefing: device, plain operational risk, which breakers/RTUs to check, manual control. Model internals are clutter here.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: fuzzyattack
- **physical_consequence**: physical: overloads: line 2 @ 113.5%, line 4 @ 103.6%
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
top SHAP features (toward 'attack'):
  Flow IAT Min: value=58, SHAP=+0.075
  Bwd IAT Min: value=243, SHAP=+0.071
  Packet Length Max: value=24, SHAP=+0.064
  Packet Length Min: value=0, SHAP=+0.058
  Bwd Packet Length Min: value=0, SHAP=+0.053
```

`item 17` → D __  C __  A __  R __  H __

---

## Item 18 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.3 = RTU-2, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-C, at Bus 4, controls breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: portscanattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. Reconnaissance probes without compromising, so the 1-hour clock does not apply.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.3:2404
```

`item 18` → D __  C __  A __  R __  H __

---

## Item 19 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: ntpddosattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. The evidence available (an IDS flow classification) does NOT establish compromise or disruption, so the 1-hour clock does not apply on these facts; it would apply only if a compromise or disruption were subsequently determined.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
top SHAP features (toward 'attack'):
  Bwd IAT Min: value=0, SHAP=+0.081
  Packet Length Max: value=8, SHAP=+0.047
  Flow IAT Min: value=641, SHAP=+0.044
  Bwd Packet Length Min: value=0, SHAP=+0.037
  Fwd PSH Flags: value=0, SHAP=+0.032
```

`item 19` → D __  C __  A __  R __  H __

---

## Item 20 — persona: **data_scientist**

*Asked for:* model analysis: which flow features drove it, what they mean, confidence, and what the features can/cannot prove. Reporting duties are NOT its job.

**Gold facts**

- **device**: DEVICE (authoritative, from IP map): 10.0.0.1 = RTU-1, RTU (IEC-104 controlled station, GridCom GC-4000), zone ZONE-N, at Bus 2, controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5, BES Cyber Asset under NERC CIP (authored overlay).
- **attack_class**: portscanattack
- **physical_consequence**: no physical violation — consequence is loss of visibility/control only (the grid absorbs the outage; remaining branches stay within thermal rating and all bus voltages stay in band)
- **reportable**: Reportable as an ATTEMPT to compromise a BES Cyber System — CIP-008-6 R4: notify E-ISAC/NCCIC by the end of the next calendar day. Reconnaissance probes without compromising, so the 1-hour clock does not apply.

**Narrative**

```
INTRUSION ALERT
prediction: attack
confidence: 1.00
destination: 10.0.0.1:2404
```

`item 20` → D __  C __  A __  R __  H __

---
