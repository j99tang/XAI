# Power-Flow & Protection Reference (steady-state)

Consequence-reasoning principles for the IEEE 14-bus overlay. **Scope is
deliberately steady-state** (what pandapower's power flow can compute): line
loadings, bus voltages, post-contingency redistribution. Dynamics — transient
stability, oscillations — are out of scope (see plan §11.4).

**Grounding rule (plan §2.9):** principles here are paraphrased from open
references (MATPOWER/pandapower docs, von Meier's *Electric Power Systems*).
**Every *quantitative* claim about our grid must be reproduced by
`scripts/simulate_consequences.py`, not asserted here.** Numbers below marked
*(base case)* come from the solved `case14` and match `topology/ieee14_grid.md`.

## What the grid normally looks like
- Buses carry a voltage; limits are **0.94–1.10 p.u.** Generator-regulated buses
  (2, 3, 6, 8) sit near the top by design. *(base case: voltages 1.010–1.090 p.u.)*
- Lines/transformers carry power up to a thermal rating. Loading is expressed as
  a percentage of that rating; **>100 % = overload** (thermal violation),
  **>90 % = alarm.** *(base case: max branch loading ~1.5 %, so there is large
  headroom — a single outage rarely overloads anything, which shapes scenario design.)*

## Meshed vs radial (why the 14-bus matters)
A **meshed** transmission grid has multiple paths between buses. Removing one line
does **not** de-energize downstream buses; instead the power it carried
**redistributes** onto parallel paths. If a parallel path was already loaded, the
extra flow can push it over its rating → a **cascading overload**. This is the
mechanism the C (Cascading Impact) score reasons about, and it is why a radial
feeder (single path, no redistribution) was rejected.

## Contingency analysis (the N-1 idea)
Operators plan so the grid survives the loss of any **single** element (N-1).
A cyberattack that opens a breaker is, electrically, a forced N-1 event. The
question the simulator answers per scenario: *after this breaker opens, does any
remaining branch exceed 100 %, or any bus leave 0.94–1.10 p.u.?* If yes, the
attack has a real physical consequence; if no (headroom absorbed it), the
consequence is operational (loss of visibility) rather than physical.

## Protection & relays
- A **breaker** physically opens/closes a line; a **protective relay** decides
  when it should, based on measured current/voltage.
- **Relay grading (coordination):** relays are time-ordered so the one nearest a
  fault trips first, limiting the outage. Coordination assumes **synchronized
  time** — which is why the `ntpddos` attack (disrupting time sync) threatens
  protection: mis-timed relays can trip the wrong element or too slowly.
- **Load shedding:** deliberately dropping load to rebalance a stressed grid — the
  last-resort response to a cascade.

## How an attack becomes a physical consequence (the reasoning chain)
1. Attack disables a device / forces a breaker open (from `attack_taxonomy/attacks.md`).
2. Map device → bus/breakers (`topology/ip_device_map.md`).
3. Open that breaker in `case14`, re-run power flow (`simulate_consequences.py`).
4. Read off overloads / voltage violations → that is the consequence.
5. If none, the consequence is **loss of visibility/control**, not a physical trip.

**Cross-references:** grid data `topology/ieee14_grid.md`; attack targets
`attack_taxonomy/attacks.md`; operator actions `playbooks/operator_response.md`.
