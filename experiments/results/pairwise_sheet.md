# Pairwise preference — which explanation is more useful?

For each item you see **the same incident** explained two ways. Pick the one that
would be **more useful to the named role**. You are comparing, not grading — no
score, no rubric, no power-systems judgement required.

Record `1`, `2`, or `=` (about the same) in `pairwise_choices.csv`, then run:

```
conda run -n xai python scripts/pairwise_eval.py --report
```

Which model or tier produced each option is hidden, and the left/right order is
randomised per item. Some pairs are deliberately easy; that is the sanity check.

---

## Item 01 — role: **regulator**

**Option 1**

```
**Regulatory Assessment**  This incident involves an intrusion alert on RTU-2, a BES Cyber
Asset under NERC CIP, at Bus 4, controlling breakers BR-2-4, BR-3-4, BR-4-5, BR-4-7, and
BR-4-9. The alert indicates a prediction of an attack with high confidence (1.00).  Based on
the knowledge graph data, this incident plausibly meets the threshold for a reportable cyber
security incident under NERC CIP-008-6. A Reportable Cyber Security Incident involves a
compromise or disruption of a BES Cyber System or its associated EACMS/PACS.  The reporting
timeline applies as follows:  * Within one hour of determining a Reportable Cyber Security
Incident. * By the end of the next calendar day for a determination that an incident was an
attempt to compromise an in-scope system.  Notification is due to both the E-ISAC and, under
US jurisdiction, the NCCIC/CISA. The required attributes for notification include functional
impact, attack vector, and level of intrusion.  This response sits under the **Detect**
capability of the CSF functions, as outlined in NIST SP 800-61r3.
```

**Option 2**

```
Illustrative assessment only: the context states this is a synthetic grid, not a
jurisdictional determination.  An IDS classified network flow statistics as an “attack” with
confidence 1.00 against destination 10.0.0.3:2404, mapped authoritatively to RTU-2, an IEC-104
controlled station at Bus 4 and a BES Cyber Asset under NERC CIP. The detector does not
identify a specific attack class, and functional impact, attack vector, and level of intrusion
are not in context.  Under NERC CIP-008-6, this plausibly meets the threshold for a Reportable
Cyber Security Incident as an attempted compromise of an in-scope BES Cyber Asset/BES Cyber
System. Actual compromise or disruption is not in context.  Applicable timeline: if determined
to be an attempted compromise, initial notification is due by the end of the next calendar
day. If later determined to have compromised or disrupted the in-scope system, the one-hour
notification timeline applies.  Notification is to the E-ISAC and, under US jurisdiction,
NCCIC/CISA. This response sits under the NIST CSF 2.0 Detect function, with reporting handled
under NERC CIP-008-6.
```

`item 01` → more useful:  1  /  2  /  =

---

## Item 02 — role: **operator**

**Option 1**

```
**Affected device/station:** RTU-2, GridCom GC-4000, IP 10.0.0.3, IEC-104 port 2404, ZONE-C,
Bus 4. Substation name: **not in context**.  **What is happening:** Attack alert with
confidence 1.00 on traffic to RTU-2. Detector saw network flow timing/size pattern: very short
inter-arrival times and small/zero-length packets. No protocol contents are in context.
**Immediate physical risk:** RTU-2 controls Bus 4 breakers **BR-2-4, BR-3-4, BR-4-5, BR-4-7,
BR-4-9**. Risk is loss or unreliability of remote visibility/control for these breakers; no
actual breaker operation or power-flow impact is in context.  **Next actions:**   1. Hold
normal grid configuration; do not issue remote switching to RTU-2 unless required for safety.
2. Immediately verify indication and control availability for RTU-2 and breakers BR-2-4,
BR-3-4, BR-4-5, BR-4-7, BR-4-9.   3. If indications are stale, inconsistent, or commands fail,
switch Bus 4 controlled bays to local/manual control and dispatch field/local operator.   4.
Before any required switching, confirm breaker position locally/manual path first.
```

**Option 2**

```
Affected: RTU-4, IP 10.0.0.6, IEC-104 port 2404, ZONE-S at Bus 9. Substation name: not in
context. RTU-4 controls BR-4-9, BR-7-9, BR-9-10, BR-9-14.  What is happening: detector reports
“normal” with low confidence 0.14. Evidence is only network flow statistics to RTU-4: small
forward packet size, timing/byte-rate features, and no protocol contents. No confirmed command
or breaker operation is in context.  Immediate physical risk: no confirmed immediate switching
risk in context. If RTU-4 stops responding, remote visibility/control of Bus 9 breakers could
be affected.  Next actions: 1. Check RTU-4 communications/response from SCADA for Bus 9. 2.
Verify current indications for BR-4-9, BR-7-9, BR-9-10, BR-9-14. 3. Do not open or close any
Bus 9 breakers based on this alert alone. 4. Keep remote control in service if RTU-4
indications and controls are healthy. 5. If RTU-4 becomes unresponsive or indications are
unreliable, switch RTU-4/Bus 9 control to manual/local control and hold existing breaker
positions unless grid safety requires action.
```

`item 02` → more useful:  1  /  2  /  =

---

## Item 03 — role: **operator**

**Option 1**

```
Action briefing:  Affected device: 10.0.0.4, ENG-WS-1 engineering workstation in ZONE-CC.
Substation affected: not in context. ENG-WS-1 is a control-center engineering workstation with
no primary equipment noted.  This incident’s evidence: detector prediction is “normal” with
confidence 0.14. Observed network-flow statistics to 10.0.0.4:123 show 26 forward packets and
timing/size features only. No protocol contents are in context.  Immediate physical risk: no
direct breaker or substation trip risk is shown in this incident. No evidence in context of
RTU loss, breaker command, or loss of visibility/control.  Next actions: - Do not operate
breakers based on this alert alone. - Verify SCADA visibility remains normal. - Because ENG-
WS-1 is used for RTU-3 configuration/maintenance, check RTU-3 at 10.0.0.5 remains
reachable/visible. - Confirm status indications for RTU-3 supervised breakers: BR-5-6,
BR-6-11, BR-6-12, BR-6-13. - Do not switch to manual control unless RTU-3 visibility/control
is actually lost; that loss is not in context for this alert.
```

**Option 2**

```
**Incident Briefing**  Device affected: ENG-WS-1, engineering workstation in zone ZONE-CC
Physical risk: Potential loss of visibility and control of RTU-3's breakers due to packet
starvation or denial-of-service attack.  Next actions:  1. Immediately switch ENG-WS-1 to
manual control mode. 2. Check the breaker status on RTU-3 (BR-5-6, BR-6-11, BR-6-12, BR-6-13)
and ensure they are not affected by any potential attack. 3. Verify that SCADA-1 is still
communicating with RTU-3 and has not lost visibility or control of the breakers.  We need to
act quickly to prevent a potential loss of control over the substation's breakers. Switching
ENG-WS-1 to manual control will allow us to maintain control over the system, even if the
attack continues.
```

`item 03` → more useful:  1  /  2  /  =

---

## Item 04 — role: **operator**

**Option 1**

```
Affected: RTU-4, GridCom GC-4000 RTU at Bus 9, ZONE-S; substation name not in context. It
controls BR-4-9, BR-7-9, BR-9-10, BR-9-14.  This incident evidence: attack alert to
10.0.0.6:2404 with flow statistics showing very tight packet timing and zero/minimal packet
lengths. Detector did not see IEC-104 contents or breaker commands.  Immediate physical risk:
RTU-4 telemetry/control for Bus 9 breakers may be delayed, dropped, or unreliable. No breaker
trip/open/close is in context.  Next actions: 1. Treat RTU-4 remote operation as suspect; do
not issue non-essential remote switching through RTU-4. 2. Verify current status/indications
for BR-4-9, BR-7-9, BR-9-10, BR-9-14 by available trusted means; trusted alternate indication
is not in context. 3. Check RTU-4 communications/health and Bus 9 breaker status before any
switching. 4. Do not open/close breakers based on this alert alone; no electrical fault or
overload is in context. 5. Manual control capability/procedure is not in context; switch to
manual only if approved local procedure confirms safe manual operation.
```

**Option 2**

```
Action briefing:  Affected device: 10.0.0.4, ENG-WS-1 engineering workstation in ZONE-CC.
Substation affected: not in context. ENG-WS-1 is a control-center engineering workstation with
no primary equipment noted.  This incident’s evidence: detector prediction is “normal” with
confidence 0.14. Observed network-flow statistics to 10.0.0.4:123 show 26 forward packets and
timing/size features only. No protocol contents are in context.  Immediate physical risk: no
direct breaker or substation trip risk is shown in this incident. No evidence in context of
RTU loss, breaker command, or loss of visibility/control.  Next actions: - Do not operate
breakers based on this alert alone. - Verify SCADA visibility remains normal. - Because ENG-
WS-1 is used for RTU-3 configuration/maintenance, check RTU-3 at 10.0.0.5 remains
reachable/visible. - Confirm status indications for RTU-3 supervised breakers: BR-5-6,
BR-6-11, BR-6-12, BR-6-13. - Do not switch to manual control unless RTU-3 visibility/control
is actually lost; that loss is not in context for this alert.
```

`item 04` → more useful:  1  /  2  /  =

---

## Item 05 — role: **data scientist**

**Option 1**

```
Based on the provided context, the model flagged this flow as an attack with a confidence of
1.00.  The top SHAP features driving the prediction are:  * Bwd IAT Min: value=0, SHAP=+0.054
* Flow IAT Min: value=315, SHAP=+0.048 * Packet Length Min: value=0, SHAP=+0.038 * Bwd Packet
Length Min: value=0, SHAP=+0.034 * Packet Length Max: value=0, SHAP=+0.033  These features
indicate that the flow has a minimum inter-arrival time (IAT) of 315 packets in both forward
and backward directions, with no packet length variation. This statistical fingerprint is
indicative of a flood/scan behavior family.  The model's confidence is high, but it's
essential to note that these features can only prove the presence of a flood/scan attack
pattern, not the specific type or class of attack. The evidence boundary is limited to
CICFlowMeter flow statistics and does not provide insight into IEC-104 protocol semantics.
```

**Option 2**

```
The binary detector flagged this flow to RTU-3 at 10.0.0.5:2404 as attack with confidence
1.00.  The strongest attack-side SHAP drivers were timing and zero-length packet statistics:
Bwd IAT Min=0, SHAP +0.054; Flow IAT Min=315, SHAP +0.048; Packet Length Min=0, SHAP +0.038;
Bwd Packet Length Min=0, SHAP +0.034; Packet Length Max=0, SHAP +0.033. In context, IAT
features are inter-arrival-time flow statistics, while small/zero packet lengths indicate
traffic where headers dominate or no payload/control-style signalling is present.  This
signature is a statistical fingerprint consistent with a flood/scan or pure-signalling family
pattern: many small/no-payload packets are described as indicative of flood/scanning, and SYN
scans carrying no payload are associated with control traffic. However, the top evidence here
does not include SYN/ACK counts or packet-rate features, so a specific SYN DoS class is not
proven.  Caveat: the model sees only CICFlowMeter flow statistics, not IEC-104 protocol
semantics. It can support “attack-like flow behavior” toward an IEC-104 RTU endpoint, but it
cannot prove specific IEC-104 commands, breaker actions, RTU compromise, or physical grid
consequences.
```

`item 05` → more useful:  1  /  2  /  =

---

## Item 06 — role: **operator**

**Option 1**

```
Action briefing:  Affected device is RTU-1, GridCom GC-4000 at Bus 2, ZONE-N. Substation name:
not in context. RTU-1 controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5.  This incident’s
evidence: network-flow detector flags attack, confidence 1.00, targeting 10.0.0.1:2404.
Observed pattern is rapid small/zero-length packet flow statistics toward the IEC-104
endpoint. No protocol contents or specific commands are visible.  Immediate physical risk:
loss or degradation of supervisory view/control of Bus 2 breakers through RTU-1. No evidence
in context of an actual breaker operation, trip, or load impact.  Next actions: 1. Treat RTU-1
remote control/telemetry as unreliable until checked. 2. Immediately verify current states of
BR-1-2, BR-2-3, BR-2-4, and BR-2-5. 3. Check RTU-1 communications and telemetry quality for
Bus 2. 4. Do not issue switching commands through RTU-1 unless breaker status and command path
are confirmed reliable. 5. Manual/local control availability and procedure: not in context. If
authorized by local procedure, shift Bus 2 breaker control away from unreliable RTU remote
operation to maintain safe continuity.
```

**Option 2**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.1:2404 top SHAP
features (toward 'attack'):   Flow IAT Min: value=5, SHAP=+0.116   Bwd Packet Length Min:
value=0, SHAP=+0.091   Packet Length Min: value=0, SHAP=+0.084   Packet Length Max: value=90,
SHAP=+0.058   Fwd PSH Flags: value=0, SHAP=+0.054
```

`item 06` → more useful:  1  /  2  /  =

---

## Item 07 — role: **data scientist**

**Option 1**

```
The model flagged this flow to destination 10.0.0.3:2404, RTU-2, with confidence 1.00. The
strongest attack-side drivers were timing and very small/empty packet-size statistics: `Flow
IAT Min=57` (SHAP `+0.075`), `Bwd IAT Min=209` (`+0.071`), `Packet Length Max=24` (`+0.063`),
`Packet Length Min=0` (`+0.058`), and `Bwd Packet Length Min=0` (`+0.053`). Statistically,
this is a compact-flow fingerprint: very small maximum packet length, zero-length minimum
packets, and short inter-arrival minima.  In the provided knowledge base, “many small packets”
/ header-dominated traffic is associated with flood/scan behavior, and zero-payload signaling
is noted for SYN-scan-style traffic. Therefore, the feature signature is consistent with a
flooding/scanning/probing family rather than normal balanced IEC-104 polling.  Caveat: this
detector is binary, so the specific attack class is not in context. These SHAP values show why
the model classified the flow as attack-like, but they do not prove IEC-104 command semantics,
malformed commands, SYN state behavior, RTU compromise, or physical grid impact. The model
sees CICFlowMeter flow statistics only, not IEC-104 protocol actions.
```

**Option 2**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.3:2404 top SHAP
features (toward 'attack'):   Flow IAT Min: value=57, SHAP=+0.075   Bwd IAT Min: value=209,
SHAP=+0.071   Packet Length Max: value=24, SHAP=+0.063   Packet Length Min: value=0,
SHAP=+0.058   Bwd Packet Length Min: value=0, SHAP=+0.053
```

`item 07` → more useful:  1  /  2  /  =

---

## Item 08 — role: **data scientist**

**Option 1**

```
The binary detector flagged the flow to RTU-4 at 10.0.0.6:2404 as attack with confidence 1.00.
Main positive SHAP drivers were `Flow IAT Min` value 4, SHAP +0.114; `Packet Length Max` value
42, SHAP +0.082; `Bwd Packet Length Min` value 0, SHAP +0.082; `Packet Length Min` value 0,
SHAP +0.080; and `Fwd PSH Flags` value 0, SHAP +0.054. The strongest evidence is therefore
timing plus packet-size statistics: very small/zero-length packet observations and a small
maximum packet length. In the provided feature guidance, “many small packets” with headers
dominating are associated with flood/scan behavior; zero-byte/control-like traffic is also
noted, but the exact meaning of `Fwd PSH Flags` is not in context.  This signature is best
characterized as a small-packet flood/scan-family statistical fingerprint, potentially
consistent with DoS/flood/probe behavior. The model does not identify the attack class.
Caveat: this is CICFlowMeter flow-statistical evidence only. It does not inspect IEC-104
semantics, payload content, command types, or breaker actions, and cannot prove RTU
saturation, SYN behavior, remote discovery, or any specific protocol operation.
```

**Option 2**

```
Based on the model's output, the flow features that drove the prediction of an attack are:  *
Flow IAT Min: value=4, SHAP=+0.114 * Packet Length Max: value=42, SHAP=+0.082 * Bwd Packet
Length Min: value=0, SHAP=+0.082 * Packet Length Min: value=0, SHAP=+0.080 * Fwd PSH Flags:
value=0, SHAP=+0.054  These features indicate a flow with short inter-arrival times (IAT),
large packet lengths, and no packets in the backward direction. The presence of these features
corresponds to a flood/scan behavior family, which is indicative of a potential Denial of
Service (DoS) or flooding attack.  The model's confidence is 1.00, indicating that it is
highly certain about its prediction. However, it's essential to note that the evidence
provided by these features can only prove the presence of a flood/scan behavior family and not
specifically identify the type of attack. Further analysis would be required to determine the
exact nature of the attack.  It's also worth noting that the destination IP address (10.0.0.6)
is an IEC-104 endpoint, which may indicate that the attack is targeting the RTU or PLC.
However, without further context or information about the specific protocol semantics, we
cannot draw any conclusions about the nature of the attack beyond what can be inferred from
the flow features.
```

`item 08` → more useful:  1  /  2  /  =

---

## Item 09 — role: **data scientist**

**Option 1**

```
Based on the provided context, the model flagged this flow as an attack with a confidence of
1.00.  The top SHAP features driving the prediction are:  * Bwd IAT Min: value=0, SHAP=+0.054
* Flow IAT Min: value=89, SHAP=+0.048 * Packet Length Min: value=0, SHAP=+0.038 * Bwd Packet
Length Min: value=0, SHAP=+0.034 * Packet Length Max: value=0, SHAP=+0.033  These features
indicate that the flow has a minimum inter-arrival time (IAT) of 89 packets in both forward
and backward directions, with no packet length variation. This statistical fingerprint is
characteristic of a flood/scan attack family.  The model's confidence is high, but it's
essential to note that these features can only prove the presence of a flood/scan behavior
pattern, not the specific type of attack or its intent. The evidence boundary is limited to
CICFlowMeter flow statistics and does not provide insight into IEC-104 protocol semantics.
```

**Option 2**

```
The binary detector flagged the flow to 10.0.0.1:2404 (RTU-1 IEC-104 endpoint) as attack with
confidence 1.00. The strongest positive SHAP drivers were timing and packet-size statistics:
`Bwd IAT Min=0` (+0.054), `Flow IAT Min=89` (+0.048), `Packet Length Min=0` (+0.038), `Bwd
Packet Length Min=0` (+0.034), and `Packet Length Max=0` (+0.033). “Bwd” is destination-to-
source traffic; IAT features are inter-arrival timing statistics, though the exact `Min`
definition is not in context. The packet-length features show zero-length/minimal observed
packet sizing, including in the backward direction.  This is a statistical fingerprint of very
small or no-payload/control-like traffic. In the provided taxonomy, many small packets with
headers dominating are associated with flood/scan behavior, and SYN scans can carry no payload
as pure signalling. Therefore, the signature is consistent with a flooding/scanning/DoS-family
or probe-style pattern, not a confirmed specific attack class.  Caveat: the model sees only
CICFlowMeter flow statistics, not IEC-104 protocol semantics. These features cannot prove a
specific IEC-104 command, malformed payload, half-open SYN behavior, RTU state change, or
physical consequence. Also, key class-specific indicators such as `SYN Flag Count`, `ACK Flag
Count`, packet rates, or byte rates are not among the cited SHAP drivers.
```

`item 09` → more useful:  1  /  2  /  =

---

## Item 10 — role: **operator**

**Option 1**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.3:2404
```

**Option 2**

```
Action briefing:  Affected asset is RTU-2, GridCom GC-4000, IEC-104 controlled station at
10.0.0.3:2404, zone ZONE-C, Bus 4. Substation name: not in context.  This incident evidence is
network-flow only: detector flags attack with confidence 1.00 against RTU-2, showing very
small/empty packet behavior and zero back-direction timing values. No IEC-104 message contents
are in context.  Immediate physical risk: loss, delay, or unreliability of supervisory
view/control for Bus 4 breakers controlled by RTU-2. Breakers at risk for missed or unverified
remote operation: BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9.  Next actions: 1. Treat RTU-2 remote
control/telemetry as suspect. 2. Check current status/alarms for BR-2-4, BR-3-4, BR-4-5,
BR-4-7, BR-4-9. 3. Do not issue remote switching through RTU-2 unless status is independently
confirmed. 4. Switch Bus 4 breaker operations to manual/local control for continuity if
telemetry is stale, missing, or commands fail. 5. Maintain present breaker positions unless a
confirmed grid safety condition requires switching.
```

`item 10` → more useful:  1  /  2  /  =

---

## Item 11 — role: **operator**

**Option 1**

```
Action briefing:  Affected device: RTU-1, GridCom GC-4000 RTU at Bus 2, ZONE-N. Substation
name: not in context. RTU-1 controls breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5.  What is
happening: Alert shows attack prediction confidence 1.00 on traffic to 10.0.0.1:2404, the
IEC-104 endpoint. Evidence is network flow statistics only: timing, packet sizes, TCP flags.
No protocol contents are in context.  Immediate physical risk: possible loss or delay of
supervisory view/control for Bus 2 breakers. No evidence in context of an actual breaker trip,
close, or command.  Next actions: 1. Verify RTU-1 communications and health immediately. 2.
Check present status/telemetry for BR-1-2, BR-2-3, BR-2-4, BR-2-5. 3. Do not perform
nonessential remote switching through RTU-1 until communications are confirmed reliable. 4.
Manual/local control capability is not in context. If approved site procedure confirms manual
control is available, use manual/local control for any required Bus 2 switching until RTU-1 is
verified. 5. Maintain grid continuity; only switch if needed for safety or system stability.
```

**Option 2**

```
**Incident Briefing**  Device Affected: RTU-1, 10.0.0.1, Zone ZONE-N, Bus 2  Physical Risk:
Potential loss of control and view of breakers BR-1-2, BR-2-3, BR-2-4, BR-2-5 due to possible
attack on the RTU.  Next Actions:  1. Immediately switch to manual control for RTU-1 by
disconnecting it from the grid. 2. Check breaker status and ensure they are not affected by
any potential loss of control. 3. Verify that all other breakers in Zone ZONE-N are
functioning correctly. 4. Investigate further, but prioritize safety and continuity of the
physical process over investigation.  **Note:** This is a high-priority incident requiring
immediate attention to prevent potential damage to the grid.
```

`item 11` → more useful:  1  /  2  /  =

---

## Item 12 — role: **data scientist**

**Option 1**

```
The binary detector flagged this flow to 10.0.0.1:2404, RTU-1 / IEC-104 endpoint, as
**attack** with confidence **1.00**.  Primary positive SHAP drivers were all flow-statistical:
`Bwd IAT Min=0` (**+0.068**), `Packet Length Min=0` (**+0.046**), `Bwd Packet Length Min=0`
(**+0.039**), `Packet Length Max=0` (**+0.034**), and `Fwd PSH Flags=0` (**+0.030**). The
packet-length evidence indicates zero-length or extremely small observed packets; the context
associates small/header-dominated packets with **flood/scan** fingerprints, and zero-byte
control traffic / no-payload SYN-style signalling with pure signalling. `Bwd IAT Min` is an
inter-arrival timing feature by name, but its exact definition is **not in context**. The
meaning of `Fwd PSH Flags` is also **not in context**, beyond the observed value and SHAP
contribution.  This signature is therefore most consistent with a **flooding/scanning/short-
probe behavior family**, possibly no-payload signalling, rather than normal balanced IEC-104
polling. It does **not** prove a specific IEC-104 command, SYN scan, DoS, or physical effect:
the model sees CICFlowMeter flow statistics only, not IEC-104 protocol semantics. Also, the
detector is binary, so it identifies attack-vs-normal, not the attack class.
```

**Option 2**

```
The model predicted **normal** for traffic to **10.0.0.6:2404** (**RTU-4**, IEC-104 endpoint)
with reported **confidence 0.19**, so the normal decision is weak.  The only top feature
pushing toward **attack** was **`Total Fwd Packet` = 1, SHAP +0.115**: a one-packet forward
direction flow is statistically short/probe-like. That can resemble the short-flow side of
scan/flood fingerprints, but by itself it does not establish scanning.  The other top features
pushed away from attack: **`Flow Bytes/s` = 14733.6, SHAP -0.081**, **`FIN Flag Count` = 1,
SHAP -0.078**, **`Flow IAT Max` = 17505, SHAP -0.073**, and **`Down/Up Ratio` = 2, SHAP
-0.068**. In this model, those values made the flow less attack-like. This weakens a
starvation/flood-family interpretation; starvation context would require broader evidence such
as many concurrent long-lived flows, rising `Bwd IAT Max`/`Flow IAT Max`, and high early
`Total Bwd packets` followed by stall, which is **not in context**.  Evidence boundary: the
detector is binary and uses CICFlowMeter flow statistics only. It does **not** inspect IEC-104
semantics and cannot prove protocol actions, breaker control, or a specific attack class.
```

`item 12` → more useful:  1  /  2  /  =

---

## Item 13 — role: **regulator**

**Option 1**

```
Illustrative assessment only: the context notes this is a synthetic grid, not a jurisdictional
determination.  An IDS classified network flow to 10.0.0.5:2404 as “attack” with confidence
1.00. The authoritative IP map identifies 10.0.0.5 as RTU-3, an IEC-104 controlled station at
Bus 6 controlling breakers BR-5-6, BR-6-11, BR-6-12, and BR-6-13, and a BES Cyber Asset under
NERC CIP.  Under NERC CIP-008-6, a Reportable Cyber Security Incident includes a compromise,
disruption, or attempted compromise of a BES Cyber System or associated EACMS/PACS. The
context does not show confirmed compromise or disruption; it shows a binary IDS attack alert
against an in-scope BES Cyber Asset. Therefore, it plausibly meets the attempted-compromise
reporting threshold if determined to be a Reportable Cyber Security Incident.  Timeline: for
an attempted compromise, initial notification is due by the end of the next calendar day. If
later determined to be an actual compromise or disruption, the one-hour notification timeline
applies.  Notify: E-ISAC, and under US jurisdiction, NCCIC/CISA. Required attributes include
functional impact, attack vector, and level of intrusion, even if initially “unknown.”  CSF
function: Respond; the IDS alert itself is Detect.
```

**Option 2**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.5:2404 top SHAP
features (toward 'attack'):   Bwd IAT Min: value=0, SHAP=+0.054   Flow IAT Min: value=315,
SHAP=+0.048   Packet Length Min: value=0, SHAP=+0.038   Bwd Packet Length Min: value=0,
SHAP=+0.034   Packet Length Max: value=0, SHAP=+0.033
```

`item 13` → more useful:  1  /  2  /  =

---

## Item 14 — role: **data scientist**

**Option 1**

```
The detector classified this flow to ENG-WS-1 (10.0.0.4:123) as **normal** with **low
confidence = 0.14**.  The listed SHAP values are all **negative for the attack class**, so
they did **not** drive an attack decision; they pushed the score away from “attack”: `Total
Fwd Packet=26` (SHAP `-0.101`), `Active Std=1.46191e+07` (`-0.077`), `Fwd Packet Length
Max=120` (`-0.065`), `Active Mean=9.07436e+06` (`-0.064`), and `Active Min=1585` (`-0.052`).
Exact definitions for `Total Fwd Packet`, `Active Std`, `Active Mean`, `Active Min`, and `Fwd
Packet Length Max` are **not in context**; only related forward-packet concepts are described
generally as source-to-destination packet counts/payload activity.  This feature signature
does **not** support a documented flooding/scan/starvation fingerprint in the provided
context. Portscan would involve many very short flows, high SYN/RST counts, tiny duration, 1–2
packets, and `Fwd Act Data Pkts≈0`; starvation would involve many concurrent long-lived flows
to port 2404 with rising IAT/stall behavior. Those required features are **not in context for
this flow**.  Caveat: the model sees only CICFlowMeter flow statistics, not protocol semantics
or actions on ENG-WS-1. These SHAP values are statistical fingerprints only, not proof of
benign intent or absence of compromise.
```

**Option 2**

```
The model predicted **attack** with **confidence 1.00** for traffic to **10.0.0.3:2404**.  The
attack score was driven by CICFlowMeter flow-statistics: **Flow IAT Min=298, SHAP +0.156** and
**Flow IAT Mean=1381.82, SHAP +0.037**, indicating timing/inter-arrival behavior the model
associates with attack traffic; **Packet Length Max=48, SHAP +0.114**, a small maximum packet
size consistent with “many small packets / headers dominate”; **Fwd PSH Flags=0, SHAP
+0.056**; and **ACK Flag Count=0, SHAP +0.030**, which aligns with low/absent ACK behavior
noted in DoS-style fingerprints.  As a statistical signature, this looks most like a
**flooding / scanning / starvation-family fingerprint**: small packets plus attack-associated
inter-arrival timing and absent ACKs. It also partially overlaps the documented SYN DoS
fingerprint through low `ACK Flag Count`, but the provided top features do **not** include
`SYN Flag Count`, `Fwd Packets/s`, or `Bwd Packets/s`, so the specific attack class is **not
proven**.  Caveat: the detector is **binary attack vs normal** and sees only flow statistics,
not IEC-104 protocol semantics. These features do **not** prove a specific IEC-104 command,
breaker action, or physical impact.
```

`item 14` → more useful:  1  /  2  /  =

---

## Item 15 — role: **data scientist**

**Option 1**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.6:2404
```

**Option 2**

```
The model flagged traffic to 10.0.0.6:2404, which maps to RTU-4, an IEC-104 RTU endpoint.
Confidence is 1.00.  The strongest attack evidence is a compact timing/zero-length
fingerprint: `Bwd IAT Min=0` with SHAP `+0.061`, `Flow IAT Min=250` with SHAP `+0.050`,
`Packet Length Min=0` with SHAP `+0.040`, `Bwd Packet Length Min=0` with SHAP `+0.036`, and
`Packet Length Max=0` with SHAP `+0.035`. The packet-length features indicate zero-
byte/minimal observed packet sizes; the context links small packets/header-dominated traffic
to flood/scan behavior and notes SYN scans can carry no payload. The IAT features indicate
very small minimum inter-arrival timing values, contributing to the same statistical
fingerprint.  Behaviorally, this looks like a small-packet / no-payload probing or flooding-
family signature, rather than normal balanced IEC-104 polling. Because the detector is binary,
it does not identify a specific attack class.  Caveat: these are CICFlowMeter flow statistics
only. They do not prove IEC-104 command semantics, breaker actions, or a specific protocol-
level operation. The evidence supports an attack-like network fingerprint against the RTU
endpoint, not proof of the attacker’s intent or physical consequence.
```

`item 15` → more useful:  1  /  2  /  =

---

## Item 16 — role: **regulator**

**Option 1**

```
Illustrative assessment only: the context states this is a synthetic grid, not a
jurisdictional determination.  A binary IDS alert classified network flow to 10.0.0.6:2404 as
“attack” with confidence 1.00. The affected asset is RTU-4, an IEC-104 controlled station at
Bus 9 controlling breakers BR-4-9, BR-7-9, BR-9-10, and BR-9-14, identified as a BES Cyber
Asset under the authored NERC CIP overlay.  Based on NERC CIP-008-6, this plausibly meets the
threshold for a Reportable Cyber Security Incident as an attempted compromise of an in-scope
BES Cyber Asset/BES Cyber System context. Actual compromise or disruption is not in context;
the detector observes network flow statistics only and does not identify protocol contents or
a specific attack class.  Timeline: because the available facts support, at most, an attempted
compromise determination, initial notification is due by the end of the next calendar day. If
later determined to be a compromise or disruption, the one-hour notification timeline would
apply.  Notification is to the E-ISAC and, under US jurisdiction, NCCIC/CISA, with required
attributes even if unknown initially.  CSF function: this regulatory reporting action sits
under Respond; the IDS alerting capability is Detect.
```

**Option 2**

```
INTRUSION ALERT prediction: attack confidence: 1.00 destination: 10.0.0.6:2404
```

`item 16` → more useful:  1  /  2  /  =

---

## Item 17 — role: **regulator**

**Option 1**

```
**Regulatory Assessment**  This incident involves a potential cyber security threat to a BES
Cyber Asset, specifically RTU-4 at Bus 9, which controls critical breakers in the grid. The
detector has predicted an attack with high confidence (1.00) on destination IP address
10.0.0.6:2404.  Based on NERC CIP-008-6, a Reportable Cyber Security Incident is triggered
when there is a compromise or disruption of a BES Cyber System or its associated EACMS/PACS.
Since RTU-4 is a BES Cyber Asset and the incident involves potential unauthorized access to
it, this plausibly meets the threshold for a reportable cyber security incident.  The
reporting timeline applies as follows: since the incident is an attempted compromise (not a
successful one), notification must be made by the end of the next calendar day. The required
attributes for initial notification include functional impact, attack vector, and level of
intrusion, which may not be fully known at this time.  Notification is due to both the E-ISAC
and NCCIC/CISA under US jurisdiction. This assessment is illustrative, as our grid is a
synthetic IEEE 14-bus overlay and CIP obligations are applied here for demonstration purposes
only.
```

**Option 2**

```
Illustrative assessment only: the context notes a synthetic grid, not a jurisdictional
determination.  An IDS classified network flow statistics as **attack** with confidence 1.00
to **10.0.0.6:2404**, which the authoritative IP map identifies as **RTU-4**, an IEC-104
controlled station at Bus 9 and a **BES Cyber Asset under NERC CIP**. No compromise or
disruption is in context.  Under **NERC CIP-008-6**, this plausibly meets the reporting
threshold as an **attempted** compromise of an in-scope BES cyber asset/system; the detector
does not identify a specific attack class. Because the facts support an attempt, not confirmed
compromise/disruption, the applicable initial notification timeline is **by the end of the
next calendar day**. If later determined to be a **Reportable Cyber Security Incident**
involving compromise or disruption, the **within one hour** timeline would apply.
Notification is due to the **E-ISAC** and, under US jurisdiction, **NCCIC/CISA**, with
required attributes even if initially unknown.  This regulatory reporting response sits under
the NIST CSF **Respond** function.
```

`item 17` → more useful:  1  /  2  /  =

---

## Item 18 — role: **operator**

**Option 1**

```
**Incident Briefing for OT Control-Room Operator**  **Affected Device:** ENG-WS-1, engineering
workstation in zone ZONE-CC.  **Physical Risk:** The device is experiencing a potential flood
attack, characterized by high packet flow rates and low inter-arrival times (IAT). This could
lead to RTU CPU/link exhaustion, delayed or dropped telemetry, and operator flying blind on
that zone. Sustained flooding can force the RTU offline.  **Immediate Action:**  1. Check
breaker status in zone ZONE-CC using ENG-WS-1's IEC-104 connections. 2. Verify if any breakers
have been tripped or blocked unexpectedly. 3. Switch to manual control for ENG-WS-1 and
isolate it from the grid, if necessary.  **Next Steps:**  1. Investigate further to determine
the cause of the flood attack. 2. Check network traffic patterns and flow statistics for other
devices in the zone. 3. Consult with security team to determine if this is a targeted or
random attack.  **Priority:** Safety and continuity of physical process over investigation.
```

**Option 2**

```
Action briefing:  Affected device: ENG-WS-1, 10.0.0.4, engineering workstation in ZONE-CC,
EACMS. Affected substation: not in context.  What is happening: detector flagged traffic to
ENG-WS-1 on port 123 as “attack” with 0.59 confidence. Evidence is network flow statistics
only: packet counts, packet size, timing gaps, and TCP-flow features. No protocol contents or
control commands were observed.  Immediate physical risk: no affected breaker, RTU, bus, or
substation is identified in context. Direct physical switching risk is not in context.  Next
actions: 1. Do not initiate breaker switching based on this alert alone. 2. Keep the grid in
normal control mode unless independent operational alarms appear. 3. Breakers to check: not in
context. 4. RTUs to check: not in context. 5. Manual control: do not switch to manual solely
from this alert; manual-control target is not in context. 6. Confirm ENG-WS-1 status and
maintain operator attention on normal SCADA indications for loss of view/control; any specific
downstream dependency is not in context.
```

`item 18` → more useful:  1  /  2  /  =

---

## Item 19 — role: **operator**

**Option 1**

```
Affected: RTU-3, 10.0.0.5, GridCom GC-4000 IEC-104 station in ZONE-S at Bus 6. Substation
name: not in context.  This incident: attack alert on traffic to RTU-3 port 2404. Evidence is
abnormal network flow timing and zero/minimum packet-size statistics only; no protocol
contents are confirmed.  Immediate physical risk: possible loss or delay of supervisory
view/control for Bus 6 breakers controlled by RTU-3: BR-5-6, BR-6-11, BR-6-12, BR-6-13. No
confirmed breaker operation is in context.  Next actions: 1. Check RTU-3 communications and
telemetry quality now. 2. Verify present indications for BR-5-6, BR-6-11, BR-6-12, BR-6-13
before any switching. 3. Do not rely on remote commands through RTU-3 until indications are
confirmed stable. 4. Switch to manual/local control: not in context; if RTU-3 view/control is
lost, follow approved local/manual operating procedure — procedure details not in context. 5.
Maintain grid continuity; no breaker opening/closing is indicated by this alert alone.
```

**Option 2**

```
**Incident Briefing**  **Affected Device:** RTU-3, 10.0.0.5, Zone-S, Bus 6 **Physical Risk:**
Potential loss of control and view of breakers BR-5-6, BR-6-11, BR-6-12, BR-6-13  The security
alert indicates a potential attack on RTU-3. The observed pattern shows high frequency of
small packets with zero bytes, indicating a flood-like behavior. This is consistent with a
Denial of Service (DoS) or flooding-type attack.  **Immediate Action:**  1. Switch to manual
control for RTU-3 to prevent further potential damage. 2. Check the breaker status and ensure
they are not being manipulated by the attacker. 3. Verify the communication link between RTU-3
and the SCADA system is secure. 4. Isolate RTU-3 from the network to prevent further attack.
**Next Steps:**  1. Investigate the cause of the attack and identify potential vulnerabilities
in RTU-3's configuration or software. 2. Review the security measures in place for RTU-3 and
ensure they are up-to-date and effective. 3. Coordinate with the SCADA team to verify the
integrity of the system and prevent any further disruptions.  **Priority:** Safety and
continuity of the physical process over investigation.
```

`item 19` → more useful:  1  /  2  /  =

---

## Item 20 — role: **regulator**

**Option 1**

```
**Regulatory Assessment**  This incident involves a potential cyber security threat to a BES
Cyber Asset, specifically RTU-3 at Bus 6, which controls critical breakers BR-5-6, BR-6-11,
BR-6-12, and BR-6-13. The detector has predicted an attack with high confidence (1.00) on the
IEC-104 endpoint at port 2404 of RTU-3.  Based on NERC CIP-008-6, this incident plausibly
meets the threshold for a Reportable Cyber Security Incident as it involves a potential
compromise or disruption of a BES Cyber System. The reporting timeline applies within one hour
of determining the incident, which is not explicitly stated in the context but can be
inferred.  Notification is due to both the E-ISAC and NCCIC/CISA under US jurisdiction. As
this assessment is illustrative (the grid is a synthetic IEEE 14-bus overlay), it is essential
to note that CIP obligations are applied here for demonstration purposes only, not as a
jurisdictional determination.  This incident response sits under the **Detect** capability of
the CSF functions, which involves identifying and analyzing potential security threats. The
required attributes for reporting include functional impact, attack vector, and level of
intrusion, even if some are unknown at first notification (updates will follow).
```

**Option 2**

```
Illustrative assessment only: jurisdiction is not determined because the context states this
is a synthetic grid/testbed.  An IDS classified network flow statistics as “attack” with
confidence 1.00 to 10.0.0.5:2404, which the authoritative IP map identifies as RTU-3, an
IEC-104 controlled station at Bus 6 and a BES Cyber Asset under NERC CIP. Actual compromise,
disruption, functional impact, attack vector, and level of intrusion are not in context.
Under NERC CIP-008-6, this plausibly meets the threshold for a Reportable Cyber Security
Incident as an attempted compromise of an in-scope BES Cyber Asset/System. Because compromise
or disruption is not in context, the applicable initial notification timeline is by the end of
the next calendar day for an attempted compromise determination, not the one-hour timeline for
a determined Reportable Cyber Security Incident involving compromise/disruption.  Notification
is due to the E-ISAC and, under US jurisdiction, NCCIC/CISA, with required attributes provided
even if initially “unknown.”  Framework function: NIST CSF 2.0 Respond; the originating IDS
alert is a Detect capability.
```

`item 20` → more useful:  1  /  2  /  =

---
