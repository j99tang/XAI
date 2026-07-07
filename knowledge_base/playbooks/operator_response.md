# Operator Response Playbooks

Role-specific response steps per attack class. **Structure paraphrased from
NIST SP 800-61r3** (incident-response lifecycle) and **NIST SP 800-82r3** (OT
security); reporting steps from `regulatory_compliance/compliance.md`. Device,
breaker, and zone names are ours (`entities.yaml`); the *procedure* is generic
best practice, the *targets* are grid-specific.

**OT-specific caveat (from NIST 800-82):** in OT you do **not** default to
"isolate and power off" — availability and safety of the physical process come
first. Containment must preserve grid operation; pulling an RTU offline can be
worse than the attack.

## The response lifecycle (all attacks share this spine)
NIST 800-61r3 maps to CSF 2.0 functions:
1. **Detect & Analyze** — confirm the anomaly is real (the IDS + this KB), identify affected device/bus.
2. **Contain** — limit spread *without* dropping the physical process.
3. **Eradicate & Recover** — remove the foothold, restore normal comms/control.
4. **Report** — per NERC CIP-008 timeline (see compliance doc) if it qualifies as a Reportable Cyber Security Incident.

## Per-attack playbooks

### dos / flood / starvation (availability attacks on an RTU)
- **Immediate:** confirm which RTU (map src/dst IP → device). Check whether SCADA-1 has lost telemetry from that substation.
- **Verify physical state:** the grid may be fine while blind — cross-check the affected bus via a **neighbouring** RTU still reporting, or field/local indication, before assuming an outage.
- **Contain:** rate-limit or filter the attacker subnet (121.142.26.0/24) at the router; do **not** power-cycle the RTU unless local control is confirmed available.
- **Recover:** restart the RTU's IEC-104 stack once the flood is filtered; confirm breaker status is observable again.
- **Escalate if:** telemetry loss coincides with an actual breaker change, or spans multiple RTUs.

### fuzzy (malformed commands to an RTU)
- **Immediate:** treat as potential unintended switching — check every breaker the RTU controls for unexpected state.
- **Verify:** compare RTU-reported breaker positions against expected schedule; a fuzzed command may have tripped or blocked one.
- **Contain:** block the source; if the RTU is unstable, fail over to local/manual control of its breakers.
- **Escalate if:** any breaker moved, or the RTU crashed/rebooted.

### mitm (ARP poisoning between RTU and SCADA)
- **Immediate:** distrust the affected RTU's telemetry — you may be seeing spoofed/stale data.
- **Verify:** corroborate that RTU's readings against an independent source before acting; do not issue control based on its data alone.
- **Contain:** clear ARP tables / enforce static ARP on the RTU–SCADA path; segment the LAN.
- **Escalate if:** evidence of spoofed measurements or dropped operator commands.

### ntpddos (time-sync disruption)
- **Immediate:** flag that **protection coordination may be degraded** — relay grading assumes synchronized clocks.
- **Verify:** check NTP/PTP server health and clock offset across devices.
- **Contain:** fail over to a backup time source / local clock; filter the attacker.
- **Escalate if:** a real fault occurs while time-sync is degraded (protection may mis-operate).

### portscan (reconnaissance)
- **Immediate:** low urgency, high signal — no physical effect, but a likely **precursor**.
- **Verify:** identify which assets were scanned (RTU, NTP, router); raise monitoring on them.
- **Contain:** block the scanning source; review firewall exposure of port 2404.
- **Escalate if:** the scan is followed by targeted traffic to a scanned RTU.

**Cross-references:** attack details `attack_taxonomy/attacks.md`; device targets
`topology/ip_device_map.md`; reporting duties `regulatory_compliance/compliance.md`.
