# Power Grids — A Crash Course for the Semantic-Gap Project

**Who this is for:** you, coming in with no power-systems background, needing *just enough* to (1) author the knowledge-base physics/topology/protection documents, (2) judge whether a generated CPAS narrative is physically sensible, and (3) speak the language your three personas use. It is deliberately practical, not a textbook. Every section ends by tying back to your project.

**How to read it:** Parts 1–2 are the physics you must not skip. Parts 3–6 are the grid and how it fails (this is what "Cascading Impact" means). Part 7 is the OT/SCADA world that connects to your IEC-104 data. Part 8 maps every concept to a KB file and a CPAS dimension. The Glossary at the end defines every acronym — keep it open in a second tab.

---

## Part 1 — Electricity physics, from zero

### The water analogy (your mental model)

Electricity is hard to picture, so use water in pipes:

- **Voltage (V, volts)** = water *pressure*. The "push" that drives electricity. Higher voltage = harder push.
- **Current (I, amperes / amps)** = *flow rate*. How much electricity actually moves per second.
- **Resistance (R, ohms Ω)** = how *narrow* the pipe is. Narrow pipe resists flow.
- **Power (P, watts)** = pressure × flow = the *rate of work done* (heating a room, spinning a motor).

The core relationships:

- **Ohm's law:** `V = I × R`. Push harder (more V) or widen the pipe (less R) and more current flows.
- **Power:** `P = V × I`. This is why it all matters — power is what does useful work, and what overheats equipment when there's too much of it.

### Why voltage and current trade off (the single most important idea)

To deliver a fixed amount of **power** (`P = V × I`), you can use *high voltage and low current*, or *low voltage and high current*. They're interchangeable for delivering power — **but heating losses depend only on current**: `P_loss = I² × R`. Doubling current quadruples the wasted heat.

So the grid moves power at **very high voltage and low current** over long distances (to minimize loss), then steps voltage *down* near you (so it's safe to use). This one fact explains the entire physical structure of the grid in Part 2.

### AC vs DC

- **DC (Direct Current):** electricity flows one direction, steady (a battery). Simple.
- **AC (Alternating Current):** the voltage/current *reverses direction* many times per second, tracing a sine wave. The grid is AC.
- **Frequency (f, hertz Hz):** how many times per second the AC cycles. **60 Hz in North America** (Canada included), 50 Hz in Europe.
- **Why AC won:** transformers (Part 3) can cheaply change AC voltage up and down. You can't do that easily with DC. That's the whole reason the grid is AC.

**RMS value:** because AC is constantly changing, we quote its *effective* value, the "root-mean-square" (RMS). When someone says "120 V outlet," that's the RMS voltage — the DC voltage that would deliver equivalent power.

### Three-phase power (why grids come in threes)

The grid doesn't use one AC wave — it uses **three**, offset by 120° (a third of a cycle) from each other. This is **three-phase** power. Reasons it's used everywhere:

- Delivers constant, smooth power (the three waves' dips fill each other in), so big motors and generators run smoothly.
- Needs less conductor material for the same power than single-phase.

You'll see two voltages quoted for three-phase: **line-to-neutral** (one wire to ground) and **line-to-line** (wire to wire). They relate by `V_line-to-line = √3 × V_line-to-neutral`. You rarely need the math — just know "three-phase" means three coordinated AC circuits, and a "three-phase fault" (all three shorting together) is the most severe kind.

### Real, reactive, and apparent power (the P, Q, S you'll see constantly)

This trips up newcomers, so slow down here. In AC systems there are **two kinds of power**:

- **Real / active power (P, measured in watts W, or MW):** the power that does actual work — light, heat, motion. This is what you pay for.
- **Reactive power (Q, measured in VAR / MVAR, "volt-amperes reactive"):** power that sloshes back and forth between the source and things like motors and transformers, which store energy in magnetic fields. It does *no net work*, but it's necessary to keep those devices energized and to hold **voltage** up.
- **Apparent power (S, measured in VA / MVA):** the total, the combination of both. They relate by a right triangle: `S² = P² + Q²`.
- **Power factor (PF):** `PF = P / S`. How much of the apparent power is doing real work. PF = 1.0 is ideal; low PF means lots of reactive current clogging the lines for no useful work.

**Why you care:** voltage stability (a big grid failure mode) is fundamentally about reactive power. When Q runs short, voltages *sag*; too much sag and the grid can voltage-collapse. In the IEEE 14-bus, several "generators" are actually **synchronous condensers** — machines that produce *only reactive power* to hold voltage up. That will look strange until you know this.

**→ Project tie-in:** your `physics/` KB doc must define P, Q, S, voltage limits, and thermal limits correctly, because the "Cascading Impact" (C) narratives reason about overloads (too much current/MVA on a line) and voltage violations (too little Q).

---

## Part 2 — The grid: from power plant to wall socket

Electricity flows through four stages. Voltage is highest in the middle and stepped down toward you.

1. **Generation.** Power plants (gas, hydro, nuclear, wind, solar) produce AC, typically at a medium voltage (e.g., ~10–25 kV).
2. **Transmission.** A step-up transformer raises it to **very high voltage** (115 kV up to 765 kV) for efficient long-distance travel on the big steel towers. This is a *meshed* network — many interconnected paths (important later).
3. **Sub-transmission / distribution substations.** Transformers step voltage *down* in stages (e.g., 138 kV → 69 kV → 13.8 kV).
4. **Distribution.** Local lines (the wooden poles) carry lower voltage (~4–35 kV) to neighborhoods, then a final transformer drops it to household voltage (120/240 V in North America).

Key structural distinction you must keep straight:

- **Transmission = meshed** (looped, many redundant paths). Losing one line reroutes power over others — which is exactly how a *cascade* happens (an overload moves to the next line). **The IEEE 14-bus is a transmission system**, which is why your plan chose it: cascades are meaningful here.
- **Distribution = radial** (tree-like, one path out from the substation). Losing a line just de-energizes everything downstream — little cascading. (This is why the plan rejected the 13-bus *distribution* feeder for your cascading narratives.)

**Units of scale:** homes draw kilowatts (kW). Substations and lines are rated in **megawatts (MW)** / **megavolt-amperes (MVA)** — millions of watts. A transmission line might be rated a few hundred MVA.

**→ Project tie-in:** your topology KB (`ieee14_grid.md`) is a transmission network. Devices sit at **buses** (Part 3); RTUs report their state over IEC-104; when SHAP flags an anomalous flow to a device's IP, the contextualizer looks up *which bus/line* it controls and reasons about the physical consequence there.

---

## Part 3 — The components (what sits in a substation)

- **Bus (busbar):** a common electrical connection point — think of it as an electrical "junction" or "node" in the network where several lines, transformers, and equipment connect. **In the IEEE 14-bus, the "14" is the number of buses.** Buses are the nodes of your graph.
- **Transmission/distribution line (branch):** the wire connecting two buses. Has a **thermal limit** (max MVA before it overheats and sags). In models, a "branch" is a line *or* a transformer.
- **Transformer:** changes AC voltage up or down (step-up / step-down) between two voltage levels. No moving parts; works only on AC.
- **Generator:** injects real power (P) and often reactive power (Q). One generator is the **slack bus** (see Part 4).
- **Synchronous condenser:** a generator-like machine that supplies **only reactive power (Q)** to support voltage. The 14-bus has several.
- **Load:** anything consuming power (a city, a factory) — modeled as drawing P and Q at a bus.
- **Circuit breaker (CB):** a heavy-duty switch that can **interrupt** current, including fault current. It *opens* (trips) to isolate a faulted or overloaded element. In your KB, breakers are named like `BR-4-5` (the breaker on the line between bus 4 and bus 5).
- **Protective relay:** the "brain" that *watches* measurements and *commands* the breaker to trip when it detects a fault. (Details in Part 6.)
- **RTU (Remote Terminal Unit) / IED (Intelligent Electronic Device):** the substation computers that collect measurements from sensors and relays, send them to the control center, and execute remote commands. **These are the devices talking IEC-104 in your dataset.** An RTU is the classic data-collector/command-executor; an IED is a smarter device (a relay or meter with a processor and comms).
- **Substation:** the fenced yard where lines meet, voltage is transformed, and breakers/relays/RTUs live. A **protection zone** is the region a given relay is responsible for.

**→ Project tie-in:** your `ip_device_map.md` assigns each IP in the data to one of these (RTU/SCADA server/gateway) *at a specific bus*, controlling specific breakers. That mapping is the network→physical bridge.

---

## Part 4 — Power flow: the physics that decides everything

**Power flow (a.k.a. load flow)** is *the* core calculation. Given: where generation is, where loads are, and the network layout, it computes **the voltage at every bus and the power flowing on every line.** pandapower does exactly this for you.

Why it's not trivial: the equations are **nonlinear** (power depends on voltage *squared* and on angle differences between buses), so they're solved iteratively by computer (the classic method is **Newton-Raphson**). You never solve it by hand; you let pandapower run it.

Three **bus types** you'll see in the model (this explains the input data of case14):

- **Slack bus (reference):** one bus that "balances the books" — it absorbs or supplies whatever is left over so generation exactly equals load + losses. Its voltage angle is the 0° reference.
- **PV bus (generator bus):** a bus where you fix real power **P** and voltage magnitude **V**; the solver finds its Q and angle.
- **PQ bus (load bus):** a bus where you fix P and **Q**; the solver finds its voltage and angle.

The two limits every power-flow result is checked against — memorize these, they *are* your consequence criteria:

- **Thermal limit (line loading):** each line can carry only so much current/MVA before overheating. Above ~100% loading = **overload** → the line must be tripped or it's damaged. Reported as "% loading."
- **Voltage limit:** each bus voltage must stay within a band, typically **0.95–1.05 per-unit** (±5% of nominal). Below → equipment misbehaves, voltage-collapse risk; above → insulation stress.

**Per-unit (p.u.):** power engineers normalize everything to a base value, so "1.0 p.u. voltage" = exactly nominal, "1.03 p.u." = 3% high. It makes different voltage levels comparable. case14 voltages are in p.u.

**→ Project tie-in:** this is the engine of your **C (Cascading Impact)** ground truth. `scripts/simulate_consequences.py` runs pandapower power flow *after* opening a breaker/removing a device, then reads off which lines are now overloaded and which bus voltages are now out of band. That simulated result — not a human expert, not the LLM — is the "correct answer" your judge scores narratives against.

---

## Part 5 — How grids fail (the whole point of "Cascading Impact")

- **Fault:** an abnormal condition, usually a **short circuit** — two conductors touch, or a line touches ground (tree, storm, equipment failure). Enormous current flows. Types, by severity: **line-to-ground (LG)** most common, **line-to-line (LL)**, **double-line-to-ground (LLG)**, and **three-phase (3φ)** the most severe.
- **Fault current:** the huge current during a fault. Breakers must interrupt it fast (tens of milliseconds) before equipment burns.
- **N-1 criterion:** the grid must be able to lose **any single** element (one line, one transformer, one generator) *without* violating thermal or voltage limits. Operators plan the grid to always be "N-1 secure." A well-run grid survives the *first* failure.
- **Contingency:** the analysis of "what if element X is lost?" — running power flow with that element removed and checking limits. (This is precisely what your simulator does per scenario.)
- **Cascading failure:** the nightmare. One line trips → its power **reroutes** onto neighboring lines (meshed network!) → one of them is now overloaded → *it* trips → more rerouting → more overloads → … → **blackout**. The 2003 Northeast blackout (55 million people) was a cascade. This only happens meaningfully on **meshed transmission** grids — which is why you're using the 14-bus.
- **Load shedding:** the deliberate, controlled disconnection of some customers to save the rest of the grid. When frequency drops (generation can't meet load), **under-frequency load shedding (UFLS)** automatically drops load in steps to rebalance. Ugly but prevents total collapse.
- **Frequency as a health signal:** grid frequency (60 Hz) rises if there's too much generation, falls if too much load. It's the real-time heartbeat of supply-demand balance. Big deviations trigger protective actions.

**→ Project tie-in:** these terms populate `physics/power_flow_basics.md` and `attack_taxonomy/` (the *physical consequence* of each attack). A convincing operator/regulator narrative about a DoS on an RTU should reason: "loss of visibility/control at Bus X → operator can't act on an overload → potential N-1 violation → cascade risk." That chain is your **C** dimension.

---

## Part 6 — Protection & control (relays, zones, coordination)

Protection is the grid's immune system: detect a fault, isolate the smallest possible area, fast.

- **Protective relay:** monitors current/voltage; if it sees a fault signature, it commands a breaker to trip. Modern ones are IEDs (digital, networked).
- **ANSI device numbers** (you'll see relays referred to by number):
  - **50** — instantaneous overcurrent (trip immediately on very high current).
  - **51** — time overcurrent (trip if high current persists).
  - **87** — differential (compares current in vs out of a zone; mismatch = fault inside).
  - **21** — distance/impedance (estimates how far away a fault is).
  - **27 / 59** — under/over-voltage. **81** — under/over-frequency.
- **Protection zone:** the region one relay is responsible for (e.g., a bus zone, a line zone). Zones deliberately **overlap** so nothing is unprotected.
- **Coordination (grading):** relays are timed so the one *closest* to the fault trips *first* (primary protection), and a backup relay trips only if the primary fails, after a short delay. This prevents tripping the whole grid for a local fault. Getting these delays right is "protection coordination."
- **Breaker operation:** the relay decides; the breaker acts. "The relay tripped the breaker" = protection isolated something.

**→ Project tie-in:** this feeds `protection_control/protection_basics.md` and the operator `playbooks/`. An operator-persona narrative gains **Actionability (A)** when it references the right protective action ("verify Zone-2 relay at Bus 4 didn't misoperate; reclose BR-4-5 only after confirming no fault"). Note pandapower models *steady-state* power flow, not the millisecond relay dynamics — so your simulated consequences are "after the dust settles" states, not the transient relay sequence. State that limitation.

---

## Part 7 — SCADA / OT: where the grid meets your network data

This is the bridge between power engineering and your IEC-104 cyber dataset.

- **OT (Operational Technology):** the computers and networks that *run physical processes* — as opposed to **IT** (email, databases). The grid's OT is its control system.
- **ICS (Industrial Control System):** the umbrella term for OT control systems (grids, water, factories).
- **SCADA (Supervisory Control And Data Acquisition):** the system operators use to *see* and *control* the grid remotely. Two directions of traffic:
  - **Telemetry / monitoring:** measurements (voltages, currents, breaker open/closed) flow *up* from substations to the control center.
  - **Control:** commands (open this breaker, change this setpoint) flow *down* from the control center to substations.
- **Control center / master station:** where operators sit, running an **EMS (Energy Management System)** for transmission or **DMS (Distribution Management System)** for distribution, with an **HMI (Human-Machine Interface)** — the screens.
- **Master / outstation (client / server):** in telecontrol, the **master** (control center) polls **outstations** (RTUs at substations). In your attack-free data, `10.0.0.2` is the master polling RTUs `10.0.0.5`, `.6`, etc.
- **IEC 60870-5-104 (IEC-104):** the telecontrol *protocol* your dataset captures — how master and RTU talk over TCP/IP, standard **port 2404**. Key terms inside it:
  - **ASDU (Application Service Data Unit):** the actual data payload (a measurement or a command).
  - **TypeID:** what *kind* of information the ASDU carries (e.g., a measured value vs. a command).
  - **IOA (Information Object Address):** points to *which specific data point* inside the device — e.g., a particular breaker's status. (Note: your flow-feature dataset does **not** contain IOAs — that's the core gap your KB overlay works around.)
  - **COT (Cause of Transmission):** *why* this message was sent (spontaneous change, response to interrogation, etc.).
  - **STARTDT / STOPDT / TESTFR:** control frames that start, stop, and test the connection. A "starvation" attack abuses these.
- **Related protocols you may see named:** **DNP3** and **Modbus** (other SCADA protocols); **IEC 61850** (the modern substation-automation standard — the SANDI dataset also has 61850 data you're not using).

**→ Project tie-in:** this whole part is your `protocol_reference/` KB doc and the vocabulary of the **OT Operator** and **Data Scientist** personas. When your narrative says "abnormal traffic on port 2404 to the RTU at Bus 4," Part 7 is what makes that sentence mean something.

---

## Part 8 — Concept → KB file → CPAS map (your cheat sheet)

| Concept (from this doc) | Goes in KB file | Primarily supports |
|---|---|---|
| Buses, lines, transformers, thermal/voltage limits, IEEE 14-bus layout | `topology/ieee14_grid.md` | D, C, H |
| Which IP = which device at which bus/breaker | `topology/ip_device_map.md` | D, H |
| P/Q/S, power flow, N-1, overload, voltage limits, cascading | `physics/power_flow_basics.md` | **C** |
| Relays (50/51/87/21), zones, coordination, breaker operation, load shedding | `protection_control/protection_basics.md` | C, A |
| SCADA, RTU/IED, master/outstation, IEC-104 (ASDU/TypeID/IOA/COT) | `protocol_reference/iec104_protocol.md` | D, H |
| Attack → network fingerprint → physical consequence | `attack_taxonomy/attacks.md` | D, C |
| Operator response steps referencing real breakers/zones | `playbooks/operator_response.md` | **A**, R |

If a generated narrative uses a term you don't recognize while spot-checking, it's in the Glossary below — and if it uses a term that's *not* in your KB, that's a hallucination (**H** penalty).

---

## Glossary (acronyms & terms)

**AC (Alternating Current)** — electricity whose direction reverses cyclically; the grid standard. Opposite of DC.

**ANSI device numbers** — standard numeric codes for protective relay functions (50 = instantaneous overcurrent, 51 = time overcurrent, 87 = differential, 21 = distance, 27 = undervoltage, 59 = overvoltage, 81 = under/over-frequency).

**Apparent power (S)** — total AC power, combining real and reactive; units VA/MVA. `S² = P² + Q²`.

**ASDU (Application Service Data Unit)** — the data payload unit in IEC-104 (carries a measurement or command).

**Ampacity / thermal rating** — max current/MVA a line can carry before overheating.

**Bus / busbar** — an electrical node where lines/equipment connect. The "14" in IEEE 14-bus.

**Branch** — a line or transformer connecting two buses (model term).

**Blackout** — large-scale loss of power, often the end state of a cascade.

**Cascading failure** — sequential tripping of elements as overloads reroute; the main transmission failure mode.

**CB (Circuit Breaker)** — switch that interrupts current, including fault current; trips to isolate faults/overloads.

**CIP (Critical Infrastructure Protection)** — NERC's mandatory cybersecurity standards for the North American grid (e.g., CIP-008 = incident reporting).

**Contingency** — a "what if this element is lost?" analysis; running power flow with an element removed.

**COT (Cause of Transmission)** — IEC-104 field stating *why* a message was sent.

**Current (I)** — rate of electric flow; amps (A). "Flow rate" in the water analogy.

**DC (Direct Current)** — steady one-directional electricity (a battery).

**DER / DG (Distributed Energy Resources / Distributed Generation)** — small generation (rooftop solar, etc.) on the distribution system.

**Distribution** — the low-voltage, *radial* final delivery network (~4–35 kV → 120/240 V).

**DMS (Distribution Management System)** — control-center software for distribution.

**DNP3** — a SCADA protocol common in North America (alternative to IEC-104).

**EMS (Energy Management System)** — control-center software for transmission operations.

**Fault** — abnormal condition, usually a short circuit; types LG, LL, LLG, 3φ (increasing severity).

**Feeder** — a distribution line carrying power from a substation out to loads.

**Frequency (f, Hz)** — AC cycles per second; 60 Hz in North America. Reflects generation-load balance.

**Generator** — machine injecting real (and often reactive) power.

**HMI (Human-Machine Interface)** — the operator's screens/controls.

**ICS (Industrial Control System)** — control systems for physical processes (grid, water, factory).

**ICS / OT vs IT** — OT/ICS run physical processes; IT handles data/business systems.

**IEC 60870-5-104 (IEC-104)** — telecontrol protocol over TCP/IP (port 2404); your dataset's protocol.

**IEC 61850** — modern substation-automation standard (also in SANDI, not used by you).

**IED (Intelligent Electronic Device)** — a networked digital substation device (relay/meter with a processor).

**IOA (Information Object Address)** — IEC-104 address of a specific data point inside a device.

**ISO / RTO (Independent System Operator / Regional Transmission Organization)** — entities that operate regional grids/markets.

**kV / MW / MVA / MVAR / kW** — kilovolts; megawatts (real power); megavolt-amperes (apparent); megavolt-amperes reactive; kilowatts.

**Load** — anything consuming power; modeled as drawing P and Q at a bus.

**Load shedding** — deliberate disconnection of load to save the grid; **UFLS** = under-frequency load shedding.

**Master / outstation** — telecontrol roles: master (control center) polls outstations (substation RTUs).

**Meshed vs radial** — meshed = looped, redundant paths (transmission, cascades possible); radial = tree, single path (distribution).

**Modbus** — a simple, widespread industrial protocol.

**N-1 criterion** — the grid must survive loss of any single element without violating limits.

**Newton-Raphson** — the iterative math method that solves the nonlinear power-flow equations.

**NERC (North American Electric Reliability Corporation)** — sets/enforces grid reliability & CIP standards.

**Ohm's law** — `V = I × R`.

**OT (Operational Technology)** — computing that runs physical processes (vs IT).

**Overload** — a line carrying more than its thermal rating (>100% loading).

**Per-unit (p.u.)** — values normalized to a base (1.0 p.u. voltage = nominal).

**PF (Power Factor)** — `P / S`; fraction of apparent power doing real work (1.0 ideal).

**PLC (Programmable Logic Controller)** — industrial controller running automation logic.

**Power (P, real/active)** — power doing actual work; watts (W) / MW.

**Power flow (load flow)** — computation of all bus voltages and line flows given generation and load.

**Protection zone** — the region a relay is responsible for; zones overlap for full coverage.

**Protective relay** — device that detects faults and commands breakers to trip.

**PQ bus / PV bus / slack bus** — power-flow bus types: PQ fixes P&Q (loads); PV fixes P&V (generators); slack balances the system and sets the angle reference.

**Reactive power (Q)** — non-working power that sustains magnetic fields and holds voltage up; VAR/MVAR.

**Relay coordination (grading)** — timing relays so the nearest one trips first, backups after a delay.

**RMS (Root-Mean-Square)** — the effective value of an AC quantity (what "120 V" refers to).

**RTU (Remote Terminal Unit)** — substation device that collects data and executes commands over SCADA.

**SCADA (Supervisory Control And Data Acquisition)** — the remote monitor-and-control system.

**Short circuit** — an unintended low-resistance path causing huge fault current.

**Slack bus** — see PQ/PV/slack.

**STARTDT / STOPDT / TESTFR** — IEC-104 control frames to start, stop, and test a connection.

**Substation** — facility where lines meet, voltage is transformed, and protection/RTUs reside.

**Synchronous condenser** — a machine supplying only reactive power to support voltage (several in the 14-bus).

**Thermal limit** — max MVA/current a line can carry before overheating; the overload threshold.

**Three-phase (3φ)** — three AC circuits 120° apart; the grid standard; a 3φ fault is the most severe.

**Transformer** — device that steps AC voltage up/down between two levels.

**Transmission** — the high-voltage (115–765 kV), *meshed* long-distance network.

**TypeID** — IEC-104 field for the kind of information in an ASDU.

**UFLS (Under-Frequency Load Shedding)** — automatic load disconnection when frequency drops.

**Voltage (V)** — electrical "pressure"; volts. Grid buses must stay ~0.95–1.05 p.u.

**Voltage stability / collapse** — the ability to hold voltages up; failure (often from reactive-power shortage) can collapse the grid.

---

*This is a working reference, not a citable source — for the thesis, cite the public references in IMPLEMENTATION_PLAN.md §2.8 (NIST, MITRE ATT&CK for ICS, MATPOWER, etc.). If any generated narrative uses a term absent from both this glossary and your KB, treat it as a hallucination.*
