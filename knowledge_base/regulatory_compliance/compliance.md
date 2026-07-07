# Regulatory & Compliance Reference (Regulator persona corpus)

Paraphrased and cited from public standards: **NERC CIP-008-6** (Incident
Reporting & Response Planning), **NIST CSF 2.0** (CSWP 29), **NIST SP 800-61r3**.
No policy IDs are invented; every obligation traces to a cited clause. Verify
clause text against the PDFs in `references/source_library/standards/` before
thesis citation.

## NERC CIP-008-6 — incident reporting (the load-bearing obligation)

**What triggers reporting.** A **Reportable Cyber Security Incident** — one that
compromised or disrupted (or, per CIP-008-6, *attempted* to compromise) a BES
Cyber System or its associated EACMS/PACS. An *attempt* is reportable even if it
did not succeed (this is the key CIP-008-6 expansion).

**Who to notify (Requirement R4).** The **E-ISAC** (Electricity Information
Sharing and Analysis Center) and, under US jurisdiction, the **NCCIC/CISA**.

**Reporting timeline (R4, initial notification):**
- **Within one hour** of determining a *Reportable Cyber Security Incident*.
- **By the end of the next calendar day** for a determination that an incident was
  an *attempt* to compromise an in-scope system.

**Required attributes (R4):** functional impact, attack vector, and level of
intrusion — even if some are "unknown" at first notification (updates follow).

**What this means for our personas.** When the pipeline classifies a flow as an
attack on an RTU (a BES Cyber Asset), the Regulator-facing narrative should state:
whether it plausibly meets the Reportable threshold, which clock applies
(1 hour vs next-day for an attempt), and who must be notified. The Operator
playbook's "Report" step defers to this document.

## NIST CSF 2.0 (CSWP 29) — the framework vocabulary
Six functions, used to frame where a response sits: **Govern, Identify, Protect,
Detect, Respond, Recover.** The IDS + contextualizer is a **Detect** capability;
the playbooks cover **Respond** and **Recover**. Using these exact terms is what
makes the Regulator narrative sound correctly grounded.

## NIST SP 800-61r3 — incident handling
Supplies the lifecycle the playbooks follow (Detect & Analyze → Contain, Eradicate
& Recover), mapped to the CSF functions above. Cited here so the Regulator persona
can reference the procedural standard, not just the reporting rule.

## Scope honesty
NERC CIP applies to the North American Bulk Electric System. Our grid is a
synthetic IEEE 14-bus overlay and the traffic originates from a European testbed
(SANDI-2024); CIP obligations are applied here **illustratively**, to demonstrate
regulator-aware explanation, not as a jurisdictional determination. State this in
any regulator narrative.

**Cross-references:** reporting is invoked from `playbooks/operator_response.md`;
incident facts come from the attack + topology docs.
