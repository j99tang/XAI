# Worked example — KB passage → graph → retrieval → persona narrative

The LightRAG paper's Figure 1 shows the framework abstractly (the beekeeper example).
This is the same four stages instantiated with CAIE's own data, so the graph's
contribution is **auditable rather than asserted**: every claim in the final narrative
is traced back to the specific edge that produced it.

Anchor entity: **RTU-3**. Figure: `docs/figures/trace_rtu3.png`.
Regenerate: `conda run -n xai python scripts/trace_example.py RTU-3`

---

## Stage 1 — Source passage (`knowledge_base/topology/ip_device_map.md`)

```
| IP       | Device | Zone   | Bus | Controls breakers                  |
| 10.0.0.5 | RTU-3  | ZONE-S | 6   | BR-5-6, BR-6-11, BR-6-12, BR-6-13  |
```

One table row. Flat vector RAG would retrieve this row as a chunk; the graph decomposes
it into an entity plus six typed relations.

## Stage 2 — Graph: entity + 11 one-hop relations

```
RTU-3  (entity_type: DEVICE)
  "RTU-3 has IP 10.0.0.5, role: RTU (IEC-104 controlled station, GridCom GC-4000),
   in zone ZONE-S, located at Bus 6, controls breakers BR-5-6, BR-6-11, BR-6-12, BR-6-13"
```

| relation | target | description carried on the edge |
|---|---|---|
| `ip device mapping` | 10.0.0.5 | 10.0.0.5 is the IP address of RTU-3 |
| `device zone` | ZONE-S | RTU-3 is in zone ZONE-S |
| `device location` | Bus 6 | RTU-3 is located at Bus 6 |
| `device controls breaker` ×4 | BR-5-6, BR-6-11, BR-6-12, BR-6-13 | RTU-3 supervises breaker … |
| `controls, supervises` | SCADA-1 | **"Loss of communication with an RTU means loss of visibility and control of its breakers — the grid keeps operating, but blind"** |
| `configures, maintains` | ENG-WS-1 | Used for RTU configuration; does not speak IEC-104 normally |
| `Devices, Systems` | MITRE ATT&CK T0840 | Network connection enumeration is used to enumerate connections on RTU-3 |
| `Mapping, Targets` | `topology/ip_device_map.md` | provenance back to the source chunk |

**Note the mix.** The coloured grid entities and their relations are injected
deterministically by `seed_graph.py` (the 8B under-extracted them — D-series). The
MITRE and SCADA-1 edges are genuinely LLM-extracted. The SCADA-1 edge is the
interesting one: it carries *consequence reasoning*, not a lookup fact.

## Stage 3 — Retrieval (scenario_03: fuzzyattack on 10.0.0.5)

The operator persona issues its own query (§11.1 / D43):

> *"An IDS flagged a network flow to 10.0.0.5 on port 2404 as 'attack' with confidence
> 1.00. The most influential flow features were … What device is 10.0.0.5? What is the
> operator response playbook for this device: which breakers and RTUs to check, whether
> to switch to manual control, isolation and switching steps, and the physical risk?"*

Two things reach the synthesizer:
1. **Deterministic join first** — `resolve_device("10.0.0.5")` is prepended to every
   context block and can never be truncated away. This is why the device is never invented.
2. **Graph retrieval** — the RTU-3 ego-graph above, plus playbook chunks, capped at 9,000 chars.

## Stage 4 — Persona narrative (gpt-5.5, tier C, operator)

> Affected: **RTU-3**, GridCom GC-4000 IEC-104 controlled station, IP **10.0.0.5**:2404,
> **ZONE-S** at **Bus 6**. Substation name: not in context. Controls **BR-5-6, BR-6-11,
> BR-6-12, BR-6-13**.
>
> What is happening: Alert shows abnormal network flow pattern to RTU-3: very short
> inter-arrival times and small/zero-length packets. Detector saw timing, sizes, and TCP
> flags only; **no protocol contents observed.**
>
> Immediate physical risk: possible delayed or lost telemetry/control for Bus 6 breakers.
> **Main risk is loss of view/control at Bus 6**, not confirmed breaker operation.
>
> Next actions: 1. Do not issue elective remote switching through RTU-3 … 2. Immediately
> verify actual status/telemetry for BR-5-6, BR-6-11, BR-6-12, BR-6-13 …

### Claim-to-edge trace

| narrative claim | produced by |
|---|---|
| "RTU-3 … IP 10.0.0.5 … ZONE-S … Bus 6" | `resolve_device` join + `ip device mapping` / `device zone` / `device location` edges |
| "Controls BR-5-6, BR-6-11, BR-6-12, BR-6-13" | four `device controls breaker` edges |
| "verify status/telemetry for [those four breakers]" | same edges, turned into an action |
| **"Main risk is loss of view/control at Bus 6"** | **the SCADA-1 `controls, supervises` edge description** — a *relation*, not a node fact |
| "no protocol contents observed" | the persona prompt's evidence-trap rule + SHAP features in the context block |
| "Substation name: not in context" | the "never guess" rule, correctly applied |

**The fourth row is the one to present.** "Loss of view and control" appears nowhere in
the source table row, nowhere in the alert, and in no node description. It comes from a
*relation description* the extractor attached to the RTU→SCADA edge, and the model used
it to reason about physical risk. That is the graph doing work a flat chunk retrieval
would not do.

The last two rows are equally worth noting: the model declines twice — refusing to name
the substation, and refusing to assert protocol-level behaviour the binary detector
cannot see. Restraint is part of the deliverable.

---

## Honest bounds on this example

- **This is one good case, not a measured average.** The overall graph is weakly
  connected — 10 bridging edges between the 46 seeded entities and the 107 LLM-extracted
  concepts, 34 components, 18 isolated nodes (see `docs/figures/README.md`). RTU-3 is one
  of only two nodes carrying most of those bridges.
- **Most retrieval value comes from entity *descriptions*, not long traversals.** The
  §11.1 check found the CIP rule in 30/30 regulator blocks largely because it rides in
  entity/relation descriptions, not because multi-hop chains were walked.
- **The device chain is seeded, not learned.** `seed_graph.py` injects it because the 8B
  under-extracted IPs, buses and breakers. The claim is "a graph makes the physical join
  usable", not "the LLM discovered the grid topology".
