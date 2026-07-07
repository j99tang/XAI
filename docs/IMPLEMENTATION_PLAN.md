# Implementation Plan — Context-Aware Intrusion Response for IEC-104 Smart Grids

**Project:** Multi-Persona Contextualizer for XAI in Cyber-Physical Systems
**Student:** Jiakai Tang · Prof. Kundur's group · ECE2500Y
**Timeline assumed:** ~1 term (3–4 months / ~14 weeks)
**Author of this plan:** working notes, written for someone new to coding — every tool is explained, and every choice states *why*.

---

## 0. How to read this document

This is a teaching plan, not just a checklist. Each phase says **what** to do, **why** it matters, and **which AI model** to lean on for that kind of work. Because you are running this "AI-native" (delegating chunks to different agents), I have tagged tasks with a suggested model tier so you know when to use a heavyweight reasoning model versus a cheap fast one.

Read Section 1 (the corrected architecture) first — it changes one core assumption from your proposal. Then follow the phases in order. Do not skip Phase 0; a clean environment saves you days later.

---

## 1. The one architectural correction (read this first)

Your proposal's story is: *SHAP flags a feature like "ASDU TypeID 46" → we map that to a physical RTU/breaker.* After reading your data, that story cannot be told as written, because:

- Your model is trained on **CICFlowMeter flow statistics** (`Flow IAT Std`, `Bwd Packet Length Max`, `SYN Flag Count`, `Dst Port`, … 79 columns). There is **no ASDU TypeID, no IOA, no protocol-semantic field** in the model's inputs. SHAP can only ever attribute to flow statistics.
- Real (attack-free) traffic is on subnet `10.0.0.x`; every simulated attack is on a **different subnet** (`121.142.26.x`, etc.). So the source IP alone almost perfectly separates normal from attack — which is why **IP must never be a model feature** (it would be a label leak).

**The fix — separate the two worlds and join them at the contextualizer, not the model:**

```
  NETWORK WORLD (learned)                 PHYSICAL WORLD (authored, synthetic)
  ┌───────────────────────┐               ┌────────────────────────────────┐
  │ Flow-stat IDS model   │               │ IEEE 14-bus grid topology      │
  │  → prediction+conf    │   join key    │  device table, breakers, zones │
  │ SHAP on flow features │  = flow's     │  physics rules, playbooks      │
  │  → top-k attributions │  Src/Dst IP   │  attack taxonomy, feature dict │
  └──────────┬────────────┘   +Port       └───────────────┬────────────────┘
             │                                             │
             └──────────────►  LightRAG Contextualizer  ◄──┘
                                (retrieves + routes to 3 personas)
```

**Why this is the right call and not just easier:** it keeps the machine-learning honest. The model never sees topology, so SHAP genuinely explains *network behavior*. The physical mapping is a **synthetic overlay** you author (mapping `10.0.0.5` → "RTU-3 at Bus 4 (69 kV), controls line breaker BR-4-5"), stored in the knowledge graph. Your contribution is then defensible as *a method for grounding model-agnostic XAI in domain context* — you are not claiming the grid mapping was learned, and no reviewer can accuse you of circular feature injection.

**About your idea of "adding topology features to the data":** do it as *metadata columns attached after prediction* (for the contextualizer to read), **never as training inputs**. If you retrain with a `bus_number` column, SHAP will rank it high only because you planted it — that is begging the question. Keep training features = flow stats only.

**IEEE 14-bus (chosen) vs 13-bus:** use the **IEEE 14-bus** transmission case. Three reasons, in order of importance:
1. **Your differentiator is the C — Cascading Impact score, and cascading is a transmission/meshed-network phenomenon.** On a meshed grid a line trip redistributes flow → overloads the next line → trips again → blackout: a rich consequence narrative. A radial distribution feeder (like the 13-node) is a tree — a fault just de-energizes everything downstream, with little genuine cascade to reason about. Your proposal already talks about "thermal overload" and "cascading failures," which are transmission concepts.
2. **Tooling.** The 14-bus is balanced positive-sequence and ships as `case14` in MATPOWER, and is native to ETAP/PowerWorld/pandapower. The IEEE 13-node feeder is *unbalanced three-phase* and needs OpenDSS/GridLAB-D — MATPOWER cannot solve it. So the standard simulators are only open to you with the 14-bus.
3. **Familiarity.** It's the de-facto teaching/benchmark case; reviewers recognize it.
The only reason to switch back to a distribution feeder is if Prof. Kundur specifically wants a *distribution-operator* persona with feeder-level consequences — worth one line of confirmation. IEC-104 itself spans both transmission and distribution substations, so it does not force the choice.

---

## 2. Scope decision for a 3–4 month term

You cannot do everything in the proposal in one term. Here is the honest cut:

**In scope (must finish):**
- Consolidated flow-based IDS (binary attack/normal) + SHAP attribution, emitting a clean JSON "anomaly event."
- Synthetic IEEE 14-bus knowledge base + IP→device mapping.
- LightRAG contextualizer + 3-persona synthesizer at temperature 0.
- CPAS evaluation on 15 curated scenarios, with the A/B/C tiers.
- **pandapower simulation of the IEEE 14-bus case** (promoted from stretch — see "The no-expert constraint" below). It is the mechanical source of physical ground truth: topology facts are *exported* from `case14`, and per-scenario consequences are *computed* by the solver. Tiny, CPU-only, no HPC.

**Stretch (only if ahead):**
- Multiclass attack typing (which attack), beyond binary.
- Re-extracting real IEC-104 protocol fields from the original PCAPs (you only have CSVs now).

### The no-expert constraint (design principle for everything below)

You have no power-systems expertise and no access to domain experts, so **no piece of ground truth may depend on human domain judgment.** Every "correct answer" must be *derivable* from one of four expert-free sources:
1. **Published benchmark data** — MATPOWER/pandapower `case14` (topology, limits, voltages).
2. **The simulator** — pandapower computes consequences (disable device → open breaker → re-run power flow → read off overloads/voltage violations). The solver plays the expert.
3. **Your own construction** — the IP→device map is fictional, so it is true by definition; it only has to be *consistent*, which `check_kb.py` verifies.
4. **Public authoritative prose** — NERC Lessons Learned, CISA ICS advisories, the SANS/E-ISAC Ukraine 2015 report — for playbooks and incident language. These are written for operators, not researchers, and are safe to paraphrase.

Your human spot-check remains valid under this constraint: verifying "every claim in this narrative traces to the KB / fact sheet" is a reading task, not an engineering one. What you must *not* do: hand-author physics claims, or accept LLM-drafted physics that the simulator can't confirm. State in the report: the system is evaluated for *groundedness in a consistent synthetic world with simulator-derived physics*, not field validity — and note that expert validation is the natural follow-on work.

**Explicitly out of scope:** Neo4j is *optional* — LightRAG ships with its own lightweight graph store. Skip Neo4j unless you have a reason.

**On the Trillium HPC cluster — a real decision, see Section 7.5.** Short version: none of Phases 0–2 need it (the RF model, SHAP, and KB authoring are trivial on your Mac). It becomes genuinely worth the onboarding cost in exactly one situation — hosting a *large open-weight* model (70B-class) for the synthesizer in Phase 3, if the small local model proves too weak *and* you want a self-hosted/reproducible model rather than a cloud API. Defer the HPC learning curve until Phase 3 tells you whether you need it.

---

## 3. Phase 0 — Environment & foundations (Week 1–2)

**Goal:** a working, reproducible dev setup, and you can re-run the existing IDS benchmark yourself.

### Tools to install (each explained)

- **Miniconda** — a manager that keeps each project's Python packages isolated so they don't conflict. Install from the Miniconda site (Apple Silicon / arm64 build). *Why:* isolated, pinned package versions make your results reproducible on your Mac or any ordinary VM. **Scope note:** conda is for your Mac only. Trillium HPC discourages conda (conda envs create huge numbers of small files that strain the shared parallel filesystem); the cluster's supported pattern is `module load python` + virtualenv + pip. This doesn't affect the plan, because the only HPC use case (Section 7.5 branch 4) is *serving a model over HTTP* — the cluster never runs your pipeline code, so the two machines' environments never need to match.
- **VS Code** — the code editor. Install the *Python* and *Jupyter* extensions. *Why:* it runs notebooks, shows errors inline, and integrates with git and with AI coding assistants.
- **Git + a GitHub account** — version control. *Why:* you will change code daily; git lets you undo mistakes and lets an AI agent and you both track exactly what changed. Your folder is already a git repo (`.git` exists) — good.
- **Ollama** — runs Large Language Models *locally* on your Mac (from the Ollama site). *Why:* your in-pipeline synthesizer must run at `temperature=0` reproducibly and ideally offline/free. On 16 GB RAM you can run a 7–8B model. We'll use this in Phase 3.

### Tasks

- **0.1 Create the conda environment.** In VS Code's terminal:
  ```bash
  conda env create -f environment.yml   # creates the `xai` env from the repo's pinned spec
  conda activate xai
  python -m pip install -e .            # editable install: `import ccir` works everywhere
  ```
  *Why from the yml, not ad-hoc `conda create`:* `environment.yml` is the single source of truth for the env — reproducible and re-creatable anywhere. *Why `python -m pip`, never bare `pip`:* see Appendix B — bare `pip` can resolve to a different Python on this machine. **Status 2026-07: done** — env exists and verifies. `[model: none — just follow the commands]`
- **0.2 Reproduce the benchmark.** Open `notebooks/legacy/iec104_benchmark.ipynb`, point it at the CSVs in `data/raw/iec104/`, and run it. Compare your numbers against the two references that exist: (a) the dataset authors' original run in `experiments/results/test1-iec104.log` (final table — e.g., Random Forest ≈ 0.82 accuracy / 0.81 F1 multiclass), and (b) the saved cell outputs inside the legacy notebooks. Expect *similar*, not identical — different library versions and random seeds shift scores a point or two. Note: the dataset's bundled `model-test1-iec104.pkl` (in your iCloud dataset folder, outside this repo) contains **only the 8 class-label names, not a trained model** — the legacy notebook already established this; there is no saved model to compare against. *Why this task matters:* if you can't reproduce the published result, you don't yet control the pipeline. **Status 2026-07: descoped by decision** — the full 14-model PyCaret sweep takes ~7 h on the laptop and nothing downstream consumes it. Close-out: reproduce only the RandomForest row (same SMOTE + MCC methodology, ~10 min) and report "RF row reproduced within X points; full sweep exceeded practical laptop runtime; authors' full table cited from the log." Pipeline control — this task's real purpose — was independently demonstrated by Phase 1 (own consolidation, training, artifacts). `[model: Sonnet-class to help debug path/library errors]`
- **0.3 Write a one-page "data reality" note** capturing the two facts from Section 1 (flow-only features; real vs sim on different subnets). This becomes a *Limitations* paragraph in your report later. **Status 2026-07: done — see `docs/data_reality.md`.** `[model: Opus-class — this is analysis/writing]`

**Exit check:** benchmark re-runs on your Mac; you can explain what one row of the CSV represents.

---

## 4. Phase 1 — IDS + SHAP layer, producing a clean "anomaly event" (Week 2–4)

**Goal:** a script that takes a flow, predicts attack/normal, runs SHAP, and outputs one JSON object. This JSON is the *contract* between the ML side and the contextualizer — the "model-agnostic" boundary your proposal sells.

### Why re-do Layer 1 if models already exist
The saved models were trained multiclass with SMOTE on a 256-vs-304k imbalance. For your thesis you want (a) a **binary** attack/normal head that is simple and robust, (b) a **train/test split that never mixes** so metrics are honest, and (c) **no leaky features** (drop or audit `Dst Port`; never add IP). Clean this up now so SHAP explains signal, not artifacts.

### Tasks

- **1.1 Consolidate + label + split columns.** Merge the 8 CSVs (they have **84 columns**: 5 identity/metadata columns — `Flow ID`, `Src IP`, `Src Port`, `Dst IP`, `Timestamp` — plus the 79 in `headers_iec104.txt`). **Never edit the raw CSVs** — raw data is immutable evidence; all cleaning happens in code on a loaded copy. Split the columns by role: **metadata** (`Flow ID`, IPs, ports, `Timestamp`) is carried alongside every row for the `AnomalyEvent` and the contextualizer's IP→device join — it must *never* enter the model's feature matrix; **features** (the flow statistics) are what the model trains on. Create a binary label (`Label == "attackfree"` → 0, everything else → 1). Do a stratified 70/30 train/test split with `random_state=42`. *Why stratified:* keeps the rare normal class present in both halves. *Why the split-not-delete design:* `Dst IP` would leak the answer if trained on, but it is also the join key that maps a flow to a physical device in Phase 3 — you need it out of the model and in the event. `[model: Sonnet — routine data wrangling]`
- **1.2 Train and persist the model.** Use `class_weight="balanced"` in a `RandomForestClassifier` rather than SMOTE-ing 300k synthetic rows. *Why:* class weighting doesn't fabricate data, so SHAP stays interpretable; report precision/recall/F1 and a confusion matrix, **not** accuracy (accuracy is meaningless at this imbalance — the original authors' log shows a dummy classifier already scoring 0.86). **Save three artifacts to `models/`** (git-ignored, regenerable): `ids_rf.joblib` (the model, via `joblib.dump` — scikit-learn's standard persistence format, a pickle variant optimized for numpy), `feature_list.json` (the exact ordered training columns — SHAP and inference must feed columns in this same order, and mismatched order is a *silent* wrong-answer bug, not a crash), and `metrics.json` (test-set precision/recall/F1 + confusion matrix, so results are inspectable without retraining). There is no pre-existing saved model anywhere — the dataset's bundled pkl is label names only; this is the first real one. `[model: Sonnet]`
- **1.3 Leakage audit.** Train once, look at feature importances. If `Dst Port` or any single feature gives near-perfect separation, investigate — it likely encodes the real-vs-sim subnet artifact. Document what you keep and why. `[model: Opus — judgment call]`
- **1.4 Wire SHAP.** Load `models/ids_rf.joblib` and `feature_list.json`; use `shap.TreeExplainer` (fast and exact for tree models). For a given flagged flow, output the top-k features (start with k=5) with their SHAP values and the feature's actual value, feature columns ordered exactly per `feature_list.json`. `[model: Sonnet, with Opus if the SHAP API confuses]`
- **1.5 Emit the anomaly-event JSON.** The schema is **already designed and frozen** in `src/ccir/schemas/anomaly_event.py` (`AnomalyEvent` / `FeatureAttribution` dataclasses) — do not redesign it; import it. The metadata columns carried through from 1.1 fill `flow_id`/`src_ip`/`dst_ip`/`dst_port`; the SHAP output from 1.4 fills `top_features`. Example output:
  ```json
  {
    "flow_id": "10.0.0.2-10.0.0.5-62883-2404-6",
    "src_ip": "10.0.0.5", "dst_ip": "10.0.0.2",
    "dst_port": 2404,
    "prediction": "attack", "confidence": 0.97,
    "top_features": [
      {"name": "Flow IAT Std", "value": 3677.2, "shap": 0.21},
      {"name": "Bwd Packet Length Max", "value": 543.0, "shap": 0.14}
    ]
  }
  ```
  *Why freeze it now:* every downstream piece (LightRAG, personas, judge) consumes this. A stable contract is what makes the system "model- and XAI-agnostic" — swap the model, keep the JSON. `[model: Opus — schema design is architectural]`

**Exit check:** you can feed any test-set flow and get a valid anomaly-event JSON.

---

## 5. Phase 2 — Knowledge base + synthetic IEEE 14-bus overlay (Week 4–6)

**Goal:** the authored "physical world" — the documents LightRAG will turn into a graph, plus the IP→device mapping that joins network to physics.

Your slides already scoped these documents well. Author them as plain Markdown files; keep everything **synthetic and paraphrased from open standards** (you already stated this — good for IP/licensing).

### The documents (each is a graph "source")

- **2.1 Grid topology (the single source of truth).** Two parts with different provenance: (a) the grid tables (buses, lines, generators/synchronous condensers, transformer taps, thermal/voltage limits, breakers) are **generated by `scripts/export_topology.py` from pandapower's `case14`** — never hand-typed, so the doc cannot contradict the simulator (pandapower is core scope now, not a stretch goal); (b) the **IP→device mapping table** joining `10.0.0.5` → "RTU-3 @ Bus 4 …" is the part you *author* — fictional, so it only needs consistency. *Why first:* every other document and every CPAS dimension except R depends on it. `[model: script for (a); Opus for (b) — needs internal consistency]`
- **2.2 Feature dictionary (the crucial bridge).** For each of the **78 features the model actually trains on** (the exact list: `models/feature_list.json`, written by Phase 1): plain-English meaning, and which attack behaviors a high/low value implies (e.g., "very low `Flow IAT Std` + high `Flow Packets/s` ⇒ flooding/DoS"). *Why this is the linchpin:* this is what lets the system translate "SHAP said `Flow IAT Std`" into "this looks like a flooding pattern," which is the actual semantic hop. Without it, the LLM guesses. `[model: Opus — this is the intellectual core]`
- **2.3 Attack taxonomy.** For each attack class in your data (DoS, flood, fuzzy, MITM, NTP-DDoS, port-scan, starvation): signature, network fingerprint, and *physical* consequence on the grid. `[model: Sonnet, reviewed by Opus]`
- **2.4 Physics reference.** Paraphrased power-flow/protection principles needed for consequence reasoning (relay grading, load-shed thresholds, fault types). `[model: Opus for accuracy]`
- **2.5 Operator playbooks.** Role-specific response steps per attack class. `[model: Sonnet]`

### 2.6 Concrete file manifest (what an agent should actually create)

Every KB file is Markdown, lives under `knowledge_base/`, and follows one rule: **facts appear in exactly one file; every other file references, never restates.** Duplicated facts drift out of sync and make the hallucination penalty un-scorable (was it a hallucination or a stale copy?).

**Build order follows the §2.8 tiers:** ★ rows are Phase 2 deliverables; ○ rows are *deferred* — do **not** create them in Phase 2; build one only when the Phase-4 pilot shows a CPAS gap it addresses.

| File | Required content | Consistency rule |
|---|---|---|
| ★ `topology/ieee14_grid.md` | Bus table (14 buses: number, name, voltage kV, type gen/load), line table (20 lines: from-bus, to-bus, thermal limit MVA), transformer table, breaker table (one breaker per line end, named `BR-<from>-<to>`) | **Generated by script** (`scripts/export_topology.py`) from pandapower's built-in `case14` — never hand-typed, so it cannot contradict the simulator |
| ★ `topology/ip_device_map.md` | One row per IP seen in the CSVs: IP → device (RTU/gateway/SCADA server) → bus → breakers it controls → substation zone | Every `src_ip`/`dst_ip` in `data/raw/iec104/` appears here; port 2404 devices are IEC-104 endpoints |
| ★ `feature_dictionary/flow_features.md` | One entry per model feature: plain-English meaning, unit, what a HIGH value suggests, what a LOW value suggests, which attack classes it fingerprints | Every feature name matches `models/feature_list.json` byte-for-byte — the 78 columns the model actually trains on (SHAP output joins on this string) |
| ★ `attack_taxonomy/attacks.md` | One section per attack class in the data (DoS, flood, fuzzy, MITM, NTP-DDoS, port-scan, starvation): mechanism, network fingerprint (in feature-dictionary terms), physical consequence, MITRE ATT&CK for ICS technique ID | Attack names match the CSV filenames' classes |
| ★ `physics/power_flow_basics.md` | Paraphrased: what a line trip does on a meshed grid, thermal overload, voltage limits, N-1 criterion, relay protection zones, load shedding | References buses/lines only from `ieee14_grid.md`; every *quantitative* claim (e.g., "tripping line 2-4 overloads line 2-5") must be reproduced by a pandapower run in `scripts/simulate_consequences.py` — no LLM-drafted physics enters the KB unverified |
| ★ `playbooks/operator_response.md` | Per attack class: immediate actions, verification steps, escalation criteria — written per persona where they differ | Actions reference only breakers/devices that exist in the topology |
| ★ `incident_reports/` (2–3 files; more only per §2.8 deferral) | Short synthetic past incidents on this same grid ("2024-03: flood attack on RTU-7 caused loss of visibility at Bus 9…") | Same devices, same naming |
| ○ `vendor_manuals/` (2–3 files, **new — see below**) | Synthetic manufacturer documentation | Same device names |
| ○ `protocol_reference/iec104_protocol.md` (**new**; mind the §2.8 evidence trap) | IEC 60870-5-104 essentials: ASDU TypeIDs, IOA, Cause-of-Transmission, t1/t2/t3 timers, port 2404 | Paraphrased from public protocol refs; terms reused consistently by attack taxonomy + manuals |
| ○ `protection_control/protection_basics.md` (**new**) | Relay grading, protection zones, breaker operation, load-shed thresholds | References only buses/devices in `ieee14_grid.md`; principles from open SEL application guides |
| ★ `regulatory_compliance/compliance.md` (**new**) | NERC CIP obligations (esp. CIP-008 reporting: timeline + recipients E-ISAC/CISA); NIST CSF functions | Paraphrased + cited from public standards; no invented policy IDs |
| ○ `model_documentation/model_card.md` (**new**) | Your IDS model card: metrics, confusion matrix, known caveats **as actually found by the Phase 1 audit**: perfect test separation caused by a *diffuse* real-vs-sim subnet artifact spread across many features — the audit found **no** single leaky feature (`Dst Port` is not even top-10); plus SHAP interpretation notes | **Generated by script** from `models/metrics.json` + `feature_list.json` (§2.8 rule — never hand-author), re-run on every retrain |

### 2.7 The synthetic "manufacturer manual" question — recommendations

You asked whether to search for real manuals or create synthetic ones. **Create synthetic ones, styled after real public documents.** Reasons:

1. **Licensing/IP.** Real vendor manuals (Siemens SICAM, ABB RTU560, SEL relays, Hitachi MicroSCADA) are copyrighted; you cannot commit them to a public repo or a thesis appendix. Paraphrased synthetic documents you own outright.
2. **Consistency.** A real ABB manual describes ABB device behavior — which won't match your synthetic grid's device names, IPs, and breaker IDs. A KB where documents contradict each other poisons retrieval: LightRAG will surface the contradiction and the synthesizer will hallucinate a reconciliation.
3. **Evaluation control.** For CPAS you need to know *exactly* what facts are in the KB, so you can score hallucination as "stated a fact not in the KB." Real manuals are too large to enumerate.

**How to make synthetic manuals credible (so a reviewer doesn't dismiss them):**
- Study the *structure* of real public documents first, then imitate the genre: SEL publishes application guides openly (selinc.com), the IEC 60870-5-104 companion standard's structure is well described in open literature, and CISA ICS advisories (public) show real vulnerability language. Cite these as "style references" in your report.
- Create a fictional vendor ("GridCom GC-4000 RTU") and write 2–3 short docs: a **device datasheet** (comm ports, supported ASDU types, watchdog/timeout behavior — IEC-104 t1/t2/t3 timers are public protocol facts and safe to state), a **configuration guide excerpt** (default port 2404, connection limits — this is what makes starvation/flood consequences explainable), and a **troubleshooting section** ("if the RTU stops responding to TESTFR frames…" — gives the operator persona concrete language).
- Keep each under ~2 pages. LightRAG quality degrades with padding; density beats volume.
- **Ground the physics in real open sources you can cite:** MATPOWER `case14` data (open), the public analyses of the 2015/2016 Ukraine grid attacks (SANS/E-ISAC report is public and describes real IEC-104-adjacent attack consequences), and NERC's public Lessons Learned pages. Paraphrase, cite in the thesis, never copy.

`[model: Opus drafts, YOU fact-check the physics against your coursework — this is the part a reviewer will probe]`

### 2.8 Knowledge-source catalogue — CPAS/persona mapping + public references

This is the authoritative list of *what knowledge goes in the graph and where to get it*. The §2.6 manifest says which files to create; this says which CPAS bands and persona each serves and which **public reference** to build it from, so you don't synthesize what already exists publicly.

**The direct-vs-synthesize rule (read first).** Split every source into two buckets:
- *General domain knowledge* (protocol, attack taxonomy, physics, compliance, feature definitions) → take **directly** from public references: paraphrase and cite, never invent.
- *Grid-specific content* (your topology facts, IP→device map, incident reports, playbooks and manuals that name *your* fictional breakers/RTUs) → **must be synthetic**, because no public document describes your invented 14-bus grid, and inserting a real vendor manual would contradict your device names and poison retrieval. Ground the synthetic ones in public sources for *style and physics*; the specifics stay yours.

**Tiering (build order — the catalogue's own "more is not better" warning, enforced).** Twelve document types is roughly double the original Phase-2 load, in the same 2-week window, for a non-expert author. Each extra doc is also a new retrieval-noise surface and more cross-references for `check_kb.py` to police. So the catalogue is split:
- **Core (build in Phase 2):** `topology/`, `feature_dictionary/`, `attack_taxonomy/`, `playbooks/`, and `regulatory_compliance/` — the last is the only *new* folder that is load-bearing, because without it the Regulator persona and the **R** dimension have no corpus at all.
- **Deferred (build only when the Phase-4 pilot shows a specific CPAS gap):** `protocol_reference/`, `protection_control/`, `vendor_manuals/`, `model_documentation/`, and incident reports beyond the first 2–3. *Why deferred rather than cut:* adding a source in response to a measured gap is better methodology than front-loading everything — you can then report *which* knowledge moved *which* CPAS dimension.

Personas: **OP** = OT Operator · **DS** = Data Scientist · **REG** = Regulator. Tier: ★ = core, ○ = deferred.

| KB source (folder) | Tier | CPAS | Persona | Public reference to build from | Direct / Synthesize |
|---|---|---|---|---|---|
| `topology/` (grid + IP→device map) | ★ | D, C, **H** | All (esp. OP) | MATPOWER `case14` / pandapower `networks.case14()` — exported by `scripts/export_topology.py` | Topology facts **direct**; IP map **synthesize** |
| `feature_dictionary/` | ★ | **D** | DS; shared | CICFlowMeter ReadMe + CICIDS2017 feature docs (ahlashkari GitHub); GintsEngelen fixed-version analysis — **not optional**: CICFlowMeter has documented feature-calculation bugs; where the two disagree, prefer the corrected analysis and note the discrepancy in the dictionary entry (a DS persona that knows the tool's quirks is more credible) | Definitions **direct**; attack-signature mapping synthesize |
| `attack_taxonomy/` | ★ | D, C, H, R | All | **Primary: the SANDI-2024 dataset's own paper** (`references/data explanation paper.pdf` — the authors describe exactly how each of the 7 attacks was generated, the most authoritative description of *these* attacks); cross-map each to a **MITRE ATT&CK for ICS** technique ID | **Direct** (dataset paper for specifics, MITRE for standard IDs) |
| `protocol_reference/` (*new*) | ○ | D, H | OP, DS | **Prefer `lib60870` docs** (open-source IEC-104 implementation — effectively a free, code-verified protocol reference) + Wireshark IEC-104 dissector; scadaprotocols.com is an informal practitioner site — fine for orientation, don't cite it in the thesis | **Direct** |
| `physics/` | ★ | **C**, some D | OP, DS | MATPOWER manual; pandapower docs; open power-systems lecture notes (e.g., MIT OCW). Textbooks: cite **P. Kundur, *Power System Stability and Control*** for fundamentals with authority (note: Prabha Kundur — a different person from supervisor Prof. Deepa Kundur; don't conflate in citations), but sparingly — it is a *dynamics* reference and this project's physics is deliberately steady-state; most of the book covers phenomena pandapower doesn't model, and teaching the synthesizer unverifiable dynamics vocabulary invites the §2.8 evidence trap. It becomes *the* citation only for §11.4. For your own learning, read **von Meier, *Electric Power Systems: A Conceptual Introduction*** (written for non-power-engineers). All textbooks: paraphrase + cite, never ingest passages into KB files (copyright) | Principles **direct**; every *quantitative* claim reproduced by pandapower, not copied |
| `protection_control/` (*new*) | ○ | C, A | OP | Open **SEL application guides** (selinc.com); NERC protection refs (IEEE C37 is paid — use free app-guides) | **Direct** (principles) |
| `playbooks/` | ★ | **A**, R | OP | NIST SP 800-82 Rev 3; NIST SP 800-61; CISA ICS advisories; SANS/E-ISAC Ukraine DUC | Structure **direct**; steps naming your breakers **synthesize** |
| `incident_reports/` | ★ | D, C | All | SANS E-ISAC Ukraine 2016 DUC; NERC Lessons Learned; **ESET's Industroyer2 analysis (2022) — the single most on-point source: real malware whose payload spoke IEC-104 natively to breakers**; Dragos CRASHOVERRIDE report for the 2016 original | **Synthesize** onto your grid, styled on the reports |
| `regulatory_compliance/` (*new*) | ★ | **R**, A, D | REG | NERC CIP (esp. **CIP-008-6** — record the version; standards revise, free PDFs at nerc.com); **NERC Glossary of Terms** (free PDF — fixes the regulator persona's vocabulary to officially defined terms); NIST CSF; IEC 62443 (paid → free overviews) | **Direct** (paraphrase + cite) |
| `model_documentation/` (*new*) | ○ | D, R | DS | "Model Cards" (Mitchell et al.) + "Datasheets for Datasets" (Gebru et al.); SHAP docs | **Generate, never hand-author**: render from `models/metrics.json` + `feature_list.json` by script, re-run + re-ingest on every retrain. *Why:* the model retrains several times in Phase 1; a hand-written card describing last month's model is a hallucination generator with a citation |
| `vendor_manuals/` | ○ | A, H | OP | Style from public SEL app-guides + generic RTU datasheets; IEC-104 timers from `protocol_reference/` | **Synthesize** (fictional vendor, e.g. "GridCom GC-4000") |

**Coverage check:** OP ← topology, protocol, physics, protection, playbooks, manuals. DS ← feature dictionary, protocol, model documentation, attack taxonomy. REG ← compliance, incident reports, attack taxonomy. Every CPAS band is covered — **H** most by topology completeness, **R** most by the persona-specific corpora.

**Where to spend effort:** more sources is not strictly better — each doc is also something LightRAG can retrieve *wrongly*, adding noise that can *hurt* D and R. Put real effort into the four load-bearing sources — **topology, feature dictionary, the attack taxonomy (dataset paper + MITRE mapping), and the regulator corpus** — and keep the rest lean and dense (< ~2 pages each).

**The evidence trap (applies especially to `protocol_reference/`).** Section 1 established that the model sees *no protocol semantics* — only flow statistics. If the KB teaches the synthesizer about ASDU types and TESTFR frames, it will happily write "the attacker sent malformed ASDUs" — a claim that is *in the provided context* (so the H guardrail and judge won't flag it) but **unsupported by the evidence**, which is only flow timing/size statistics. This failure mode is subtler than hallucination: true of the world, unwarranted for this incident. Countermeasure, wired into Phase 3.4 and the judge rubric: distinguish **background context** ("IEC-104 runs on port 2404") from **incident evidence** (only what the flow features + fact sheet support), and require narratives to attribute observations only to evidence. This epistemic-provenance distinction is worth a paragraph in the methodology chapter.

**Public reference index.** Download a copy of each into `references/` before Phase 2 starts — URLs rot (the SANS Ukraine link below is already a Kaspersky-hosted mirror), and paraphrasing requires the full text anyway. Cite the canonical source in the thesis, work from the local copy.
- NIST SP 800-82 Rev. 3 — https://csrc.nist.gov/pubs/sp/800/82/r3/final
- MITRE ATT&CK for ICS — https://attack.mitre.org/matrices/ics/
- SANS/E-ISAC Ukraine DUC (2016) — https://media.kasperskycontenthub.com/wp-content/uploads/sites/43/2016/05/20081514/E-ISAC_SANS_Ukraine_DUC_5.pdf
- NERC CIP-008 — https://www.nerc.com/standards/reliability-standards/cip/cip-008-6
- IEC 60870-5-104 ASDU structure — https://scadaprotocols.com/iec104-asdu-structure/ (orientation only; cite lib60870 instead)
- lib60870 (code-verified IEC-104 reference) — https://github.com/mz-automation/lib60870
- CICFlowMeter (feature definitions) — https://github.com/ahlashkari/CICFlowMeter
- ESET Industroyer2 analysis — https://www.welivesecurity.com/2022/04/12/industroyer2-industroyer-reloaded/
- NERC Glossary of Terms — https://www.nerc.com/pa/stand/glossary%20of%20terms/glossary_of_terms.pdf

### 2.9 The authoring workflow — converting `references/` → `knowledge_base/`

**This is not find-and-replace, and it is not fully manual — it is deliberate synthesis on a mechanical backbone.** A script cannot map "NIST 800-82's incident-response section" onto "an operator playbook for *your* grid": there is no deterministic 1:1 transformation. You are *distilling* large real documents into small synthetic ones written in your fictional world's vocabulary (device names, IPs, breakers), kept consistent across files, paraphrased not copied, and bounded so **H** stays scorable. That needs reasoning. But part of the job is genuinely mechanical and must be scripted (a model would only introduce errors). Split the work on that line:

| Track | Documents | How | Model |
|---|---|---|---|
| **Mechanical (scripted, deterministic)** | `topology/ieee14_grid.md`, the IP list for `ip_device_map.md`, the feature-name list, `model_documentation/` (rendered from metrics), `check_kb.py` | Python scripts from `case14` / the CSVs / `headers_iec104.txt` / `models/metrics.json` | none |
| **Deliberate (LLM-authored on top of the skeleton)** | physics prose, attack taxonomy, protocol reference, playbooks, compliance, vendor manuals, incident reports | reasoning model, one document per session, against curated context | see below |

**The per-document authoring loop.** Author *one* KB file per session (never all at once — context bloat and consistency drift will corrupt entity naming, which §3.1b shows is fatal to graph extraction). Hand the agent a *tight, curated* context, not the whole library:

- the *specific* source(s) for that one doc from `references/source_library/` (PDF-reading required) — not all of them;
- the ground-truth skeleton it must stay consistent with: `topology/ieee14_grid.md`, `ip_device_map.md`, `headers_iec104.txt` (exact device names, IPs, feature strings);
- `docs/power_grid_crash_course.md` for correct terminology + the glossary;
- the rules from §2.6/§2.8 (paraphrase don't copy; facts live in one file; < 2 pages; cite; **never invent** — mark any physics number "to be verified by simulator" rather than fabricating it; keep background context separate from incident evidence per the §2.8 evidence trap);
- write access to the one target file, and the ability to run `scripts/check_kb.py` to validate its own output before finishing.

**Model choice.** Put the **load-bearing, fact-critical** docs (feature dictionary, physics facts that must match the simulator, compliance that must not invent clauses, topology narrative) on a **top-reasoning model (Opus-class)** with heavy human review — you fact-check the physics yourself per the no-expert constraint. The **prose-heavy synthetic** docs (incident reports, vendor manuals, playbook narrative) tolerate a strong *writing* model; if you want to try **Fable** here, A/B one document against Sonnet and compare *faithfulness to the source* before trusting it broadly — a smoother narrative that drifts from the evidence is worse than a plainer accurate one. Never put a cheap/fast model on a load-bearing doc. `[model: Opus for load-bearing; Sonnet/Fable candidate for prose-heavy, verify first]`

**Skill vs agent — use both; they are different layers.** A **skill** is the reusable *process* (required inputs, the guardrails above, a per-doc-type template, the final `check_kb.py` self-check). An **agent** is the *executor* that reads the source, writes the file, and runs the checker in a loop. The best implementation is a skill invoked by an agent (or by you in a focused chat), run one document at a time. Why a skill rather than re-prompting each time: you repeat this ~11 times over weeks, and an ad-hoc prompt drifts — a versioned skill keeps every KB doc consistent and is itself improvable, the same "contracts as shared memory" principle this plan runs on. **Practical rollout:** start with a committed **`knowledge_base/AUTHORING_GUIDE.md`** (the process + guardrails + templates, usable today by pasting to any model/agent); promote it to an installable **`SKILL.md`** once the process has stabilized over the first two or three documents. Do `topology/` and `feature_dictionary/` yourself first — they set the entity-naming conventions every later doc must match.

**The guardrail that makes this safe (non-negotiable).** The failure mode is a model writing *plausible but ungrounded* facts — a made-up device behavior, an invented line rating, a non-existent NERC clause. This is more dangerous than ordinary hallucination because it corrupts the KB *silently*, and a corrupted KB destroys your **H** baseline (if the KB itself is wrong, "did the narrative state a fact not in the KB" is meaningless). So every load-bearing doc gets human verification, physics numbers come only from the simulator, and `check_kb.py` must pass before a doc is considered done. Authoring speed is not the constraint here; groundedness is.

### 2.9 The transformation workflow — how references become KB files

Turning §2.8's references into KB documents is **not a find-and-replace script and not fully manual — it is a hybrid, and the split criterion is the provenance of each fact**: *does a machine-checkable source of truth exist for it?*

- **Yes → generate, never draft.** Topology tables (source: pandapower), model card (source: `models/metrics.json`), fact sheets (source: simulator runs), IP coverage (source: the CSVs). Find-and-replace intuition is genuinely correct *for this bucket only* — deterministic 1:1 transformation, so any LLM or human touching these can only introduce errors.
- **No → LLM-draft, then gate.** Paraphrased playbooks, attack narratives, feature-dictionary interpretations, vendor-manual prose. Paraphrasing NIST 800-82 into a playbook that names *your* breakers is a judgment task with no 1:1 mapping — but "judgment" does not mean "unchecked": every draft passes `check_kb.py`, and physics claims pass the simulator gate.

**Division of labor (skill / agent / code):**
- **Skill = the rulebook.** A Claude Code skill (`.claude/skills/kb-author/`) holding: the doc template per KB type, the direct-vs-synthesize rule, the §2.8 evidence-trap rule, citation format, length caps (< ~2 pages). *Why a skill:* authoring spans many files and sessions; rules kept only in conversation context drift and die — a skill reloads them fresh every time.
- **Agent = the executor.** One KB file per task, working from the downloaded reference text + the rulebook + the entity registry.
- **Code = the enforcement.** Any rule that matters is checked by `check_kb.py`, not merely stated in the skill — prose rules decay, asserts don't.

**The canonical entity registry (build FIRST, before any prose).** `knowledge_base/entities.yaml`: every fictional proper noun in one place — device names, breaker IDs, buses/zones, the fictional vendor, IP assignments. Every authoring agent reads it; `check_kb.py` validates every document's entity mentions against it. *Why:* the #1 failure of multi-document LLM authoring is naming drift ("RTU-3" vs "the Bus-4 RTU") — which becomes duplicate graph nodes at §3.1b. One shared vocabulary file is what makes independently drafted documents form one coherent graph.

**Supporting tools:** `pymupdf` (PDF text extraction, so agents paraphrase from the *actual* downloaded reference text, never from model memory); the §3.1b early ingest + graph visualization as the end-to-end test of naming discipline.

**Authoring order:** `entities.yaml` → `export_topology.py` (generated bucket) → `check_kb.py` → `ip_device_map.md` (first authored doc — sets the pattern) → remaining ★ docs, one agent task each, `check_kb.py` after every file.

**Capability boundaries (honest):** an AI agent can fully own the generated bucket and the drafting bucket; it may *draft* physics-adjacent prose but the simulator gate stands precisely because fluent LLM physics is the unverifiable kind the evidence trap warns about; and the final read-through ("does every claim trace to a source?") stays **human** — per the no-expert constraint it is a reading task, and it is your answer when the committee asks how you know the KB is sound.

**Exit check:** a human can trace one scenario end-to-end on paper: flagged flow → dst IP → device → attack class → physical consequence → operator action, using only these docs. Additionally, run a consistency script (`scripts/check_kb.py`) with five rules: every IP in the CSVs is in the map; every feature name in the dictionary matches `models/feature_list.json`; every breaker referenced anywhere exists in the topology; every MITRE technique ID cited matches the `T0xxx` format and appears in the taxonomy file exactly once; every entity mention in every KB file resolves to `entities.yaml`. Broken cross-references are the #1 silent killer of RAG quality.

---

## 6. Phase 3 — LightRAG contextualizer + multi-persona synthesizer (Week 6–9)

**Goal:** feed the anomaly-event JSON in, get three role-specific narratives out.

### Tools

- **LightRAG** — a Retrieval-Augmented-Generation library that builds a *knowledge graph* from your documents and retrieves both local facts and community summaries (its "dual-level retrieval"). Install with `pip install lightrag-hku`. *Why LightRAG over plain vector RAG:* your reasoning is relational ("this breaker protects that zone"), which a flat similarity search misses; a graph captures those edges. *Why not Neo4j:* LightRAG has a built-in store; only add Neo4j if you later need its query tooling.

### Tasks

- **3.1 Ingest the KB.** Point LightRAG at your Phase-2 Markdown files to build the graph once. *Why once:* graph construction uses an LLM and costs time/tokens; build it, then reuse. `[model: for ingestion, a mid model like Gemini Flash or Claude Haiku is fine and cheap]`
- **3.1b Visualize and verify the graph.** Two complementary views of the same `rag_storage/` data:
  - **Interactive (debugging):** install the server extra (`python -m pip install "lightrag-hku[api]"`), run `lightrag-server` pointed at `rag_storage/`, open the Web UI in a browser — it shows the knowledge graph interactively (the view from LightRAG's docs) plus a query playground.
  - **Static (thesis figures):** LightRAG persists the graph as a GraphML file inside `rag_storage/`; open it in **Gephi** (free desktop app) to lay out and export a publication-quality figure.
  *Why this is a verification step, not decoration:* the graph is your first test of Phase 2 quality. Spot-check: "RTU-3" should be one node connected to "Bus 4", its breakers, and its attacks — if instead you see duplicate nodes ("RTU-3" vs "RTU 3" vs "the RTU at bus 4") or a disconnected hairball, your KB documents use inconsistent entity names; fix the Markdown and re-ingest *before* building retrieval on top. Consistent, exact entity naming across all KB files is what makes graph extraction work. `[model: none — visual inspection by you]`
- **3.2 Build the orchestrator.** A Python script that: (a) takes the anomaly-event JSON, (b) forms one LightRAG query combining the SHAP features + dst IP, (c) retrieves the **Multi-Domain Context Block**. *Why one shared context block:* your proposal's efficiency claim — retrieve once, reuse for all three personas. `[model: Opus — orchestration logic]`
- **3.3 The 3-persona synthesizer loop.** Same context block, three system prompts (Operator / Data Scientist / Regulator), `temperature=0`. Run the *in-pipeline* LLM locally via Ollama. *Why local + temp 0:* reproducibility (a thesis needs re-runnable results) and cost control across many scenarios. *Recommended starting model:* **Llama 3.1 8B Instruct** or **Qwen2.5 7B Instruct** — both fit in 16 GB and follow role prompts well. **Then evaluate quality against CPAS + a human spot-check and choose your path (see Section 7.5):** if 7–8B is good enough, stop. If it hallucinates or ignores personas, either (a) swap to an API model (Gemini Pro as synthesizer, keeping Claude as judge) for strong reasoning with no HPC, or (b) host a 70B open model on Trillium GPU if you need a self-hosted/reproducible model. `[model: start local 7–8B; escalate per 7.5; use Opus to write and refine the prompts]`
- **3.4 Guardrail against hallucination — and against the evidence trap.** Two rules in the synthesizer prompt: (a) use *only* facts in the provided context block, saying "not in context" otherwise; (b) distinguish **background context** from **incident evidence** — the narrative may cite KB facts as background ("RTU-3 speaks IEC-104 on port 2404") but may only attribute *observations about this incident* to the flow features and fact sheet (never "malformed ASDUs were sent" — the model cannot see ASDUs; see §2.8's evidence trap). *Why:* (a) is what the CPAS **H** penalty tests; (b) catches claims that are in-context but unwarranted, which H alone cannot. `[model: Opus for prompt design]`

**Exit check:** one anomaly event yields three distinctly-voiced, context-grounded narratives.

---

## 7. Phase 4 — CPAS evaluation harness (Week 9–11)

**Goal:** quantify whether the full system beats the two baselines.

### The circularity problem you must design around
Your proposal has an LLM generate explanations grounded on a synthetic KB, then an LLM judge them against that same KB. If synthesizer and judge are the *same model family*, you measure self-preference, not quality. **Rule: the judge must be a different, stronger model than the synthesizer.** Concretely — synthesizer = local Llama/Qwen 7–8B; **judge = Claude (Opus/Sonnet) or Gemini Pro via API.** Also do a small **human spot-check** (you score ~5 scenarios yourself) to validate the judge agrees with a human. `[model: judge = Opus-class API model]`

### Tasks

- **4.1 Curate 15 scenarios:** 5 true-positive cyber, 5 true-positive physical, 5 false-positive noise (per your design). For each, fix the input flow and the expected key facts. **Where the 5 false positives come from (discovered in Phase 1):** the full model classifies the test set *perfectly* — it cannot produce a false positive to explain. Source them from a **deliberately feature-constrained model variant** (retrain with the top-N most separating features dropped until confidence spreads and errors appear; save as `models/ids_rf_constrained.joblib`). Methodologically honest as long as stated: FP scenarios are drawn from the constrained variant because the full model commits no errors on this testbed — and explaining the uncertain regime is exactly where explanation systems matter in deployment. `[model: Opus — designing fair test cases]`
- **4.2 Implement the three tiers:** (A) IDS output only; (B) IDS + raw SHAP; (C) full system. *Why:* this A/B/C is your evidence that context — not just XAI — drives the improvement. `[model: Sonnet to code the harness]`
- **4.3 Encode the CPAS rubric** (D, C, A, R each 1–5; H as a 0/1 penalty multiplier) as a strict judge prompt returning JSON scores. Pin down the weights `w` and *pre-register them* before running, so you can't be accused of tuning to the result. `[model: Opus — rubric + judge prompt]`
- **4.4 Ground the C (Cascading Impact) dimension in the simulator.** For each scenario, `scripts/simulate_consequences.py` (pandapower) computes the physical consequence — disable the mapped device / open its breaker, re-run the power flow, record overloads and voltage violations. The judge scores C as *agreement with the simulated consequence*, not plausibility. This is what removes the need for a human power-systems expert. `[model: Sonnet to code; the simulator supplies the judgment]`
- **4.5 Generate the gold fact sheets by script, not by hand.** `scripts/make_fact_sheets.py` assembles, per scenario: device + bus (from the IP map), attack class (from the CSV label), network fingerprint (from the feature dictionary), and simulated consequence (from 4.4). You review for readability only — no domain judgment involved. `[model: Sonnet]`
- **4.6 Run, aggregate, plot** CPAS by persona × tier. Expect C > B > A. `[model: Sonnet]`

**Exit check:** a table of CPAS scores across all 15 scenarios and 3 tiers, plus your human spot-check agreement rate.

---

## 7.5 Should you use the Trillium HPC cluster? (decision guide)

**Short answer: not by default, and not before Phase 3. There is exactly one high-value use, and one nice-to-have.**

Your instinct is correct in principle — a bigger GPU lets you run a **larger, stronger open-weight model** (Llama 3.3 70B, Qwen2.5 72B) than the 7–8B ceiling your 16 GB Mac imposes, and 70B-class models reason and follow role instructions noticeably better with less hallucination. That directly helps your synthesizer (Phase 3) and could lift CPAS. So the *quality* argument is real. The question is whether it's worth the cost and whether there's a cheaper route to the same quality.

**What HPC costs you:** Trillium is a **batch-scheduled** cluster (SLURM). You don't get an interactive GPU on demand — you submit jobs to a queue, wait, and load software "modules." That's a poor fit for the tight edit-run-inspect loop of building a RAG pipeline, and it's a real learning curve (SLURM `sbatch`/`salloc`, modules, serving a model with **vLLM**, port-forwarding to reach it). For **15 scenarios you do not need HPC for throughput** — the Mac handles the volume fine. The only thing HPC buys is *model size*, not *speed*.

**The cheaper route to the same quality:** if 7–8B is too weak, first try swapping the synthesizer to a strong **API model — Gemini Pro** — and keep **Claude as the judge** (this preserves the judge ≠ synthesizer rule). You get strong reasoning immediately, no HPC, no SLURM. The downside is per-call cost, needing internet, and that it's no longer "self-hosted."

**When HPC genuinely earns its keep — the one high-value case:** if your thesis wants to claim the synthesizer runs on a **self-hosted, open-weight, reproducible** model — which is a *legitimately stronger research story for OT/critical-infrastructure*, since real substation environments are often air-gapped and can't call a cloud API — then hosting Llama/Qwen 70B on Trillium GPU is the right move. That turns "we called a cloud API" into "we ran a self-contained model an operator could deploy on-prem," which reviewers in this space value. This is the decision point at the end of Phase 3.

**Recommended decision procedure:**
1. Phase 3: build with local **7–8B on the Mac** first. Measure it with CPAS + a human spot-check.
2. Good enough? **Stop — no HPC.**
3. Too weak, and reproducibility/self-hosting is *not* central to your claim? **Use Gemini Pro API as synthesizer** (Claude judge). No HPC.
4. Too weak, and self-hosting/air-gap *is* part of your contribution? **Use Trillium GPU to serve a 70B open model** (vLLM). Budget ~3–5 days to learn SLURM + vLLM; ask me for a step-by-step when you reach this branch. **Environment note:** do *not* install conda on Trillium (unsupported there — filesystem strain). The cluster pattern is `module load python` + `virtualenv` + `pip install vllm` (or an Apptainer container if the docs recommend one for vLLM). This is fine because Trillium only *serves the model over HTTP*; all pipeline code stays on your Mac, so the environments never need to match — reproducibility on the HPC side is captured by pinning the model weights version and the vLLM version in your report, not by sharing an env file.

**What HPC is *not* for here:** the RF IDS (trains in seconds on CPU), SHAP (fast), LightRAG ingestion (one-time, use an API), and the pandapower stretch simulation (CPU, tiny). Don't move those to HPC.

---

## 7.6 LLM-as-judge: the pitfalls, and how CPAS must be built to survive them

Section 7 already covers the circularity problem (judge ≠ synthesizer family). Here are the *other* documented failure modes of LLM judges, each with the concrete countermeasure to bake into the Phase 4 harness. A committee member who knows the LLM-eval literature will ask about these; having pre-empted them is worth real marks.

1. **Verbosity bias — longer answers score higher.** Judges systematically reward length even when content is equal. Your tier C (full system) will naturally produce longer text than tier A (raw IDS output), so a naive judge inflates exactly the comparison you care about. *Countermeasure:* (a) cap all three tiers to the same length budget in the synthesizer prompts (e.g., ≤200 words per persona); (b) instruct the judge to score each CPAS dimension against the rubric's anchor descriptions, never "overall quality"; (c) report answer lengths per tier in your results table so a reviewer can see the comparison wasn't length-confounded.

2. **Score compression — everything gets a 4.** LLM judges avoid scale extremes; a 1–5 scale often collapses to 3–4, destroying your statistical power on only 15 scenarios. *Countermeasure:* write **anchored rubrics** — for each dimension, a one-sentence description of what a 1, 3, and 5 concretely look like (e.g., D=5: "names the specific device and bus affected"; D=1: "no physical referent at all"). Anchors force spread. Pilot the judge on 3 scenarios first; if scores still compress, switch that dimension to pairwise comparison (see #5).

3. **Non-determinism — same input, different score.** Even at temperature 0, API models are not bit-reproducible, and a thesis needs re-runnable numbers. *Countermeasure:* pin the exact model version string (e.g., a dated snapshot, not a floating alias), run the judge **3 times per item and report the median**, and report score variance. Cheap insurance: 15 scenarios × 3 tiers × 3 personas × 3 repeats ≈ 400 judge calls — trivially affordable.

4. **Order and position effects.** If the judge sees tiers A/B/C in one prompt, it favors by position; if it scores C right after A, contrast effects inflate C. *Countermeasure:* score each output in **isolation** (one output + rubric + KB context per call, judge never told which tier it is), and randomize evaluation order. Blinding the judge to the tier label is the single highest-value design choice here.

5. **Rubric-dimension bleed.** One judge call scoring D, C, A, R, H simultaneously lets a strong impression on one dimension halo onto the rest. *Countermeasure:* if the pilot shows suspiciously correlated dimensions, split into one call per dimension. Costs more calls (still cheap at this scale) but gives clean per-dimension signal.

6. **The hallucination (H) check is really a fact-verification task, not a judgment task.** Asking a judge "did this hallucinate?" against a long KB is unreliable — the judge itself can miss or invent. *Countermeasure:* for each of the 15 scenarios, a **gold fact sheet** (5–10 key facts a correct explanation should use, plus the device/bus ground truth). Per the no-expert constraint, these are **generated by `scripts/make_fact_sheets.py`** (Phase 4.5) from the IP map + CSV label + pandapower consequence run — you review readability, never physics. The H check becomes: "list every factual claim in this output; mark each as supported / contradicted / absent from the provided fact sheet + KB excerpt." Structured extraction is far more reliable than a holistic yes/no. The fact sheet doubles as the scenario definition file (Phase 4.1).

7. **Judge–human disagreement discovered too late.** If your human spot-check (5 scenarios) disagrees with the judge after you've run everything, you have no time to redesign. *Countermeasure:* do the human spot-check **first**, during the pilot: you score 5 scenarios yourself with the same rubric, then run the judge on the same 5, and report agreement (Spearman correlation per dimension, or simple within-1-point agreement — at n=5 keep the statistics modest and honest). Only then run the full 15×3×3. If agreement is poor, fix the rubric anchors, not the judge model.

8. **Prompt leakage of the expected ranking.** If the judge prompt says "tier C is our full system," you've told it the answer. *Countermeasure:* the judge prompt contains only: the anomaly context, the KB excerpt/fact sheet, the persona definition, the rubric, and the anonymous output. Nothing about tiers, baselines, or hypotheses.

**Pre-registration, restated concretely:** before running the full evaluation, commit to git one file (`experiments/scenarios/cpas_protocol.md`) containing: the rubric with anchors, the dimension weights `w`, the judge model version, the number of repeats, and the aggregation rule. The commit timestamp is your evidence that you didn't tune the metric to the result. This is standard practice from the empirical-ML playbook and cheap credibility.

---

## 8. Phase 5 — Analysis, write-up, limitations (Week 11–14)

- **5.1 Results narrative:** does context close the semantic gap, and for which persona most? `[model: Opus]`
- **5.2 Limitations (be your own harshest reviewer):** synthetic topology (D/C measure coherence with a fictional grid, not field truth); no domain-expert validation — physics ground truth is simulator-derived (steady-state power flow only; no protection dynamics, no transient stability) and prose docs are paraphrased from public sources, so expert review is stated as follow-on work; real-vs-sim subnet domain shift; small attack-free sample; single-topology scope; judge-model bias mitigated but not eliminated. `[model: Opus]`
- **5.3 Figures + final report/deck** updates. `[model: Sonnet for drafting, Opus for the argument]`
- **5.4 Reproducibility package:** freeze the conda env (`conda env export`), commit code + KB + scenario definitions so results re-run. `[model: none — mechanical]`

---

## 9. Model strategy for your AI-native (multi-agent) workflow

You have Claude Pro and Gemini Pro, an M4 Pro (16 GB), and school HPC. Match the model to the task's cognitive load, not to habit:

| Work type | Use | Why |
|---|---|---|
| Architecture, schema design, leakage judgment, CPAS rubric, limitations | **Claude Opus** (heavy reasoning) | These decisions shape the whole thesis; a weak model here costs weeks. |
| Routine code: data wrangling, plotting, harness plumbing | **Claude Sonnet / Gemini Pro** | Fast, competent, cheaper; you'll iterate a lot. |
| Bulk/repetitive generation, KB graph *ingestion* | **Gemini Flash / Claude Haiku** | High volume, low stakes; save money. |
| **In-pipeline synthesizer** (the 3 personas, temp 0) | **Local Llama 3.1 8B / Qwen2.5 7B via Ollama** (start here) → escalate to **Gemini Pro API** or **70B open model on Trillium GPU** if too weak (see 7.5) | Must be reproducible + temp 0; fits 16 GB. Escalate only if CPAS/human check shows weakness. |
| **LLM-as-judge** (CPAS) | **Claude Opus/Sonnet or Gemini Pro** (must differ from synthesizer) | Independence removes self-preference bias; stronger reasoning = better rubric adherence. |

**A practical division of labor for delegating to agents:**
1. *Planner/architect agent (Opus)* — owns this plan, the JSON contract, the rubric. You talk to it when a decision has consequences.
2. *Builder agent (Sonnet)* — writes and debugs the Python for each phase, following the architect's contracts.
3. *KB author agent (Opus for topology/feature-dict, Sonnet for the rest)* — drafts the synthetic documents; you fact-check.
4. *Synthesizer (local, in the running system)* — not something you chat with; it's a component.
5. *Judge (API, different family)* — runs inside the eval harness.

Keep the *contracts* (the anomaly-event JSON schema, the CPAS rubric, the KB file list) in the repo as the shared memory between agents. That is what makes multi-agent work coherent instead of chaotic.

---

## 10. Immediate next actions (this week)

1. Do Phase 0.1–0.2: install Miniconda + VS Code + Ollama, create the `xai` env, re-run the benchmark notebook.
2. Confirm the Section-1 correction with Prof. Kundur / your mentor — that topology lives in the KG overlay, not the model features. This reframes the contribution and is worth a sign-off before you build.
3. Come back and I'll help you write the Phase 1 consolidation + SHAP script against the frozen JSON contract.

---

## Appendix A — Agent-executable build spec

This appendix restates the phases as concrete deliverables so an AI coding agent (Claude Code) can build each piece without ambiguity. The layer boundaries below are deliberately hard: **each layer is a separate module with a file-based interface**, which is exactly what makes your A/B/C tiers possible — tier A consumes layer-1 output only, tier B consumes layers 1–2, tier C consumes all three. If the layers share in-memory state instead of files, you can't ablate them.

**Ground rules for the agent:** activate the `xai` conda env before running anything; never modify files under `data/raw/`; never add IP addresses or topology fields as model training features; all generated artifacts go to `models/`, `rag_storage/`, or `experiments/results/` (git-ignored); every script must be runnable as `python -m ccir.<module>` or via `scripts/`, and must fail loudly (raise, don't warn) on missing inputs.

### A1 — Layer 1+2: IDS + SHAP (`src/ccir/ids/`, `src/ccir/xai/`)
| Deliverable | Path | Acceptance check |
|---|---|---|
| Data consolidation | `src/ccir/ids/dataset.py` — loads the 8 raw CSVs (84 columns, read-only), splits columns into **metadata** (`Flow ID`, `Src IP`, `Src Port`, `Dst IP`, `Timestamp` — kept per-row for the `AnomalyEvent`) vs **features** (flow stats; `Dst Port` pending the 1.3 audit), binary label, stratified 70/30 split with `random_state=42` | Prints class counts per split; asserts no metadata column is in the feature matrix; raw CSVs untouched |
| Binary RF model | `src/ccir/ids/train.py` — `class_weight="balanced"`; saves `models/ids_rf.joblib`, `models/feature_list.json`, `models/metrics.json` | Reports precision/recall/F1 + confusion matrix on the held-out test set; reloading the joblib reproduces the same test predictions |
| SHAP wrapper | `src/ccir/xai/explain.py` — `TreeExplainer`, returns top-k `FeatureAttribution`s for one flow | Feature names match `models/feature_list.json` exactly (column order enforced) |
| Event emitter | `src/ccir/xai/emit.py` — flow row → `AnomalyEvent` JSON (schema already in `src/ccir/schemas/anomaly_event.py`) | Round-trips through `AnomalyEvent.from_dict`; the `__main__` self-test passes |

### A2 — Knowledge base + simulator (`knowledge_base/`, `scripts/`)
Deliverables are the ★ files in the Section 2.6 manifest (○ files are deferred — do not build), authored **in the §2.9 order** (registry → generated docs → checker → authored docs, `check_kb.py` after every file), plus:
| Deliverable | Path | Acceptance check |
|---|---|---|
| Entity registry (**first, before any prose**) | `knowledge_base/entities.yaml` — every fictional proper noun: devices, breaker IDs, buses/zones, vendor, IP assignments | Every IP in the raw CSVs has an entry; no duplicate names |
| Topology exporter | `scripts/export_topology.py` — dumps `case14` buses/lines/limits + breaker names into `topology/ieee14_grid.md` | Doc regenerates identically from the same pandapower version; breaker names match `entities.yaml` |
| Consequence simulator | `scripts/simulate_consequences.py` — per scenario: disable mapped device → open its breaker(s) → run power flow → write overloads/voltage violations to `experiments/scenarios/consequences_<id>.json` | Baseline (no outage) case14 power flow converges with no violations |
| KB consistency check | `scripts/check_kb.py` — the five §2.9 rules: IP coverage, feature-name match vs `models/feature_list.json`, breaker existence, MITRE ID format/uniqueness, entity mentions resolve to `entities.yaml` | Exits 0 |
| KB authoring skill | `.claude/skills/kb-author/` — doc templates, direct-vs-synthesize rule, evidence-trap rule, citation format, length caps | Every authored KB file was produced under it (noted in file frontmatter) |

### A3 — Layer 3: contextualizer (`src/ccir/contextualizer/`)
| Deliverable | Path | Acceptance check |
|---|---|---|
| KB ingestion | `src/ccir/contextualizer/ingest.py` — LightRAG build from `knowledge_base/` into `rag_storage/` (run once) | Graph loads on restart without re-ingesting |
| Retrieval | `src/ccir/contextualizer/retrieve.py` — `AnomalyEvent` → one query string (top SHAP features + dst IP + prediction) → Multi-Domain Context Block (plain text) | For a known scenario, the block contains the correct device name from the IP map |
| Personas | `src/ccir/contextualizer/synthesize.py` — 3 system prompts (in `configs/personas/`), same context block, Ollama at `temperature=0`, ≤200 words each, "only facts from context" guardrail | Same event run twice → identical output (temp-0 determinism on local model) |

### A4 — Evaluation (`src/ccir/evaluation/`, `experiments/`)
| Deliverable | Path | Acceptance check |
|---|---|---|
| Scenario definitions | `experiments/scenarios/scenario_<01..15>.json` — frozen input flow + gold fact sheet, assembled by `scripts/make_fact_sheets.py` from the IP map, CSV label, feature dictionary, and `consequences_<id>.json` | Each references a real row in the test split; no hand-written physics claims |
| Tier runners | `src/ccir/evaluation/tiers.py` — tier A (IDS JSON only), B (A + raw SHAP list), C (full pipeline); each writes `experiments/results/<scenario>_<tier>_<persona>.txt` | All 15×3×3 output files exist |
| Judge | `src/ccir/evaluation/judge.py` — per Section 7.6: blinded, isolated calls, anchored rubric from `experiments/scenarios/cpas_protocol.md`, 3 repeats, median | Pilot on 3 scenarios matches your human scores within 1 point on ≥ 80% of dimension scores |
| Aggregation | `src/ccir/evaluation/report.py` — CPAS table + plot by persona × tier | Table renders; lengths per tier reported alongside scores |

---

## 11. Future improvements & research extensions

These are deliberately **out of the 3–4 month scope** but documented so the thesis can name them
as future work and so you can pick them up if ahead. The first two are prioritized because you
raised them directly; the rest are ranked roughly by research value.

### 11.1 One graph + persona-conditioned retrieval + persona generation (the retrieval ablation)

*See `docs/notes/adr-001-knowledge-graph-persona-architecture.md` for the full decision record.*

**What the baseline does (Phase 3):** one knowledge graph, one shared retrieval (the Multi-Domain
Context Block), three persona system prompts. Personalization happens only at generation.

**The improvement:** keep the *one* graph (single source of truth), but personalize *retrieval*
too. Do a **two-part retrieval** per event — a *shared core* keyed on the incident (dst-IP →
device, attack class, top SHAP features) that all personas see identically, plus a
*persona-scoped supplement* filtered to that persona's tagged sources with a persona-shaped query
(operator → device/action terms; regulator → reporting/compliance terms), and use LightRAG's
retrieval mode per persona (operator → local/specific, regulator → global/policy summaries).

**Why it should help CPAS:** the shared core keeps all three narratives factually consistent
(protects **H** and **D**); the persona supplement gives each persona tighter, less-noisy material
(lifts **A** and **R**). It is strictly more targeted than reusing one context block for everyone.

**Why NOT three separate graphs:** the sources overlap too much — topology, protocol, and attack
taxonomy are shared by all personas. Three graphs would either duplicate the topology (copies
drift, wrecking **H**) or sever the cross-domain edges that justify a graph over vector RAG
("attack → RTU → bus/line → CIP-008 obligation" spans personas), and risk the personas grounding on
different facts about the same incident.

**How to implement:** tag each KB doc at ingest with `personas: [...]` and `cpas: [...]` metadata;
run the two-part retrieval; concatenate core + supplement per persona. Caveat: LightRAG's
per-document metadata filtering is thinner than a vector store's, so the native path is
persona-shaped *queries* plus post-filtering retrieved chunks by stored source tags — verify the
API before committing.

**Why it's future work, not baseline:** treat it as a **measured ablation** — build the simple
shared-context version first, then add persona-conditioned retrieval and report the CPAS delta.
That turns an architecture opinion into a publishable result: *"does persona-specific retrieval
improve CPAS over a shared context block, and on which dimensions?"*

### 11.2 Fully open-source, self-hosted model stack (reproducibility + air-gap credibility)

**What the baseline does:** synthesizer is a local 7–8B model, but the **judge** (and any
synthesizer escalation) is a proprietary API (Claude/Gemini).

**The improvement:** run the *entire* pipeline — synthesizer **and** judge — on open-weight,
self-hosted models (e.g., synthesizer = Qwen2.5 7B locally; judge = Llama 3.3 70B / Qwen2.5 72B on
Trillium via vLLM), keeping the judge ≠ synthesizer rule by using a different open family/size.

**Why it matters:**
1. **Reproducibility.** Proprietary API models change silently under a fixed name; a thesis needs
   numbers that re-run years later. Pinned open weights are bit-stable.
2. **OT/critical-infrastructure relevance.** Real substations are often air-gapped and cannot call
   a cloud API. "An operator could deploy this on-prem" is a materially stronger research claim
   than "we called an API."
3. **Cost and vendor independence.** No per-call cost, no lock-in, no rate limits at eval scale.

**How to implement:** serve the open judge with vLLM on the Trillium GPU node (see §7.5), pin exact
weight versions and the sampling config, and re-validate the open judge against your human
spot-check — open judges are typically weaker at rubric adherence, so the anchored rubric (§7.6)
and human-agreement check matter more, not less. Run it as a **robustness/stability study**:
report whether CPAS conclusions hold when the judge is swapped from a proprietary to an
open model (if the ranking C > B > A survives both, that is strong evidence it isn't a
judge artifact).

### 11.3 Real protocol-level features (PCAP re-extraction)

Re-extract IEC-104 semantics (ASDU TypeID, IOA, Cause-of-Transmission) from the original `.pcap`
files so SHAP attributes to *protocol* fields, not just flow statistics. This makes the
topological mapping **literal** rather than a synthetic overlay, closing the day-one
"features have no physical home" gap at its root. Highest-value single extension; also the biggest
effort (needs the pcaps + tshark/scapy parsing + retraining).

### 11.4 Dynamic simulation for true cascading (beyond steady-state)

Replace steady-state pandapower with a dynamic simulator (e.g., **ANDES**) to model protection
operation, frequency dynamics, and genuine time-domain cascades. This upgrades the **C (Cascading
Impact)** ground truth from steady-state N-1 contingency to real cascade dynamics — a much richer
consequence narrative and a stronger claim.

### 11.5 Human / expert evaluation of CPAS

The LLM-as-judge is a *proxy* for human stakeholders. The definitive validation is having real OT
operators, data scientists, and regulators rate the narratives, and correlating their scores with
CPAS. This directly tests the "operational usefulness" thesis and answers the deepest reviewer
objection (that a synthetic judge grading synthetic text may not reflect real utility).

### 11.6 Retrieval ablation: quantify the graph's contribution

Compare LightRAG against (a) no RAG, (b) vanilla vector RAG, and (c) Microsoft GraphRAG on the
same scenarios and CPAS rubric. This isolates *how much of the gain comes from the knowledge graph
specifically* versus RAG in general — a clean, expected-by-reviewers ablation.

### 11.7 Generalization: multiple / larger topologies

Extend beyond the single IEEE 14-bus to IEEE 39- and 118-bus (and optionally a distribution feeder
via OpenDSS for a distribution-operator persona). Tests whether the method scales and whether CPAS
gains persist as the grid grows — addresses the "single synthetic topology" novelty question below.

### 11.8 Generalization across models and datasets (the agnosticism claims, tested)

Two tiers, very different costs:
- **Model swap (cheap — can even land in-scope as a stretch):** train a second model family (XGBoost / GradientBoosting) and emit events through the *unchanged* `AnomalyEvent` pipeline. `shap.TreeExplainer` covers both; the contextualizer never knows the difference. ~20 lines of code for direct evidence of the model-agnostic claim — a table row in the thesis with outsized credibility payoff.
- **Second dataset (real future work):** a new dataset is a new *network world* — the IP→device map, and possibly topology overlay and attack taxonomy, must be re-authored (most of Phase 2 again), which is why this is out of term scope. Concrete candidates already in hand: the same download includes an **IEC 61850 capture set** (`raw-iec61850.tgz` in the iCloud dataset folder) — cross-*protocol* generalization with consistent provenance — or another IEC-104 testbed for within-protocol generalization. Naming an owned dataset keeps this section concrete.

### 11.9 Multiclass attack typing and richer personas

Move Layer 1 from binary to multiclass (which attack), enabling attack-specific consequence
reasoning; and add stakeholders beyond the three (incident responder, executive) or make personas
user-configurable. Also consider **uncertainty communication** — propagating model confidence and
retrieval confidence into each narrative so a low-confidence detection reads differently per role.

---

## Appendix B — Environment facts & pitfalls (read before running anything)

Learned the hard way during Phase 0 on this machine (2026-07). Any agent executing this plan should treat these as ground truth; each one blocked a task once already.

**Python installations (post-cleanup, 2026-07).** The machine was cleaned so that **conda is the only Python you ever invoke directly**:
- Removed: python.org framework Python 3.14 (was first on PATH via `~/.zprofile` and hijacked bare `pip`/`python3`/Jupyter three separate times) and orphaned Homebrew `python@3.13`.
- Kept: Homebrew `python@3.14` — it is a *dependency* of ollama/texlive/yt-dlp/mlx, lives in `/opt/homebrew`, and must never be uninstalled or used for project work.
- Kept: conda base + envs (below).

Rules that still stand even after cleanup (they cost a debugging session each):
- Always `python -m pip`, never bare `pip` — `python -m` guarantees the pip of the interpreter you're in.
- Run project code as `conda run -n xai python …` (or after `conda activate xai`), never bare `python`/`python3`.
- With Jupyter/nbconvert, always name the kernel explicitly: `--ExecutePreprocessor.kernel_name=pycaret_env` for legacy notebooks, or pick "Python (pycaret_env)" in VS Code. Never trust an unqualified `python3` kernelspec.

**Two conda envs, deliberate split — do not merge them:**
- `xai` (Python 3.11) — everything new: pandas/sklearn/shap/lightrag-hku/pandapower, plus `ccir` editable-installed (`python -m pip install -e .`). `environment.yml` is its source of truth; after adding a package, re-freeze with `conda env export --no-builds > environment.yml`.
- `pycaret_env` — **legacy notebooks only** (`notebooks/legacy/*.ipynb` need pycaret 3.3.2 + mlflow + seaborn). PyCaret pins old library versions and would conflict with the `xai` stack; keep it quarantined. nbconvert + ipykernel are installed there.

**Data locations:**
- The repo copy `data/raw/iec104/` is **authoritative**. Raw CSVs have 84 columns (5 identity/metadata + 79 of `headers_iec104.txt`).
- The original download lives in iCloud at `…/UT-iC/01 Project/Dataset/15487636/` — note the `Dataset/` path segment (it moved once and broke the notebooks; expect iCloud paths to be unstable, never hardcode them in new code). Its `model-test1-iec104.pkl` contains only class-label names, not a model.

**Ollama** is installed via Homebrew but no model is pulled yet. Phase 3 first-run: `ollama serve` must be running (or `brew services start ollama`), then `ollama pull llama3.1:8b` (~5 GB download — do it on good wifi, once).

**Long jobs:** the legacy PyCaret benchmark takes tens of minutes (it trains ~14 models on 320k rows); run nbconvert with `--ExecutePreprocessor.timeout=3600` and in the background. Nothing else in Phases 0–2 is slow.

---

*Open questions to resolve with your advisors, flagged honestly:*
- Is a **single synthetic topology** (the one IEEE 14-bus overlay) enough novelty, or do they expect the method demonstrated on multiple grids? (Affects Phase 2 effort; see §11.7. Terminology note: earlier drafts said "feeder" — a leftover from the abandoned IEEE 13-node *distribution feeder* option. The 14-bus system is a meshed *transmission* grid, not a feeder.)
- Do they require **real protocol semantics** (re-extracting ASDU/IOA from PCAPs), or is the flow-based + KG-overlay framing acceptable? (This is the biggest scope lever; see §11.3.)
- Is **binary detection** sufficient for Layer 1, or must you also classify attack type? (See §11.9.)
