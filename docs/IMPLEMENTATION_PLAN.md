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
- Synthetic IEEE-13-bus knowledge base + IP→device mapping.
- LightRAG contextualizer + 3-persona synthesizer at temperature 0.
- CPAS evaluation on 15 curated scenarios, with the A/B/C tiers.

**Stretch (only if ahead):**
- Multiclass attack typing (which attack), beyond binary.
- A real power-flow simulator (pandapower) to give the **C — Cascading Impact** dimension a ground truth instead of plausibility-vs-KB.
- Re-extracting real IEC-104 protocol fields from the original PCAPs (you only have CSVs now).

**Explicitly out of scope:** Neo4j is *optional* — LightRAG ships with its own lightweight graph store. Skip Neo4j unless you have a reason.

**On the Trillium HPC cluster — a real decision, see Section 7.5.** Short version: none of Phases 0–2 need it (the RF model, SHAP, and KB authoring are trivial on your Mac). It becomes genuinely worth the onboarding cost in exactly one situation — hosting a *large open-weight* model (70B-class) for the synthesizer in Phase 3, if the small local model proves too weak *and* you want a self-hosted/reproducible model rather than a cloud API. Defer the HPC learning curve until Phase 3 tells you whether you need it.

---

## 3. Phase 0 — Environment & foundations (Week 1–2)

**Goal:** a working, reproducible dev setup, and you can re-run the existing IDS benchmark yourself.

### Tools to install (each explained)

- **Miniconda** — a manager that keeps each project's Python packages isolated so they don't conflict. Install from the Miniconda site (Apple Silicon / arm64 build). *Why:* your school VM and your Mac must run the *same* package versions for results to reproduce; conda "environments" make that possible.
- **VS Code** — the code editor. Install the *Python* and *Jupyter* extensions. *Why:* it runs notebooks, shows errors inline, and integrates with git and with AI coding assistants.
- **Git + a GitHub account** — version control. *Why:* you will change code daily; git lets you undo mistakes and lets an AI agent and you both track exactly what changed. Your folder is already a git repo (`.git` exists) — good.
- **Ollama** — runs Large Language Models *locally* on your Mac (from the Ollama site). *Why:* your in-pipeline synthesizer must run at `temperature=0` reproducibly and ideally offline/free. On 16 GB RAM you can run a 7–8B model. We'll use this in Phase 3.

### Tasks

- **0.1 Create the conda environment.** In VS Code's terminal:
  ```bash
  conda create -n xai python=3.11 -y
  conda activate xai
  pip install pandas scikit-learn shap matplotlib jupyter imbalanced-learn
  ```
  *Why Python 3.11:* current, stable, and every library here supports it. `[model: none — just follow the commands]`
- **0.2 Reproduce the benchmark.** Open `references/notebooks/iec104_benchmark.ipynb`, point it at the CSVs, and run it. Confirm you get numbers similar to the saved `.pkl`. *Why:* if you can't reproduce the existing result, you don't yet control the pipeline. `[model: Sonnet-class to help debug path/library errors]`
- **0.3 Write a one-page "data reality" note** capturing the two facts from Section 1 (flow-only features; real vs sim on different subnets). This becomes a *Limitations* paragraph in your report later. `[model: Opus-class — this is analysis/writing]`

**Exit check:** benchmark re-runs on your Mac; you can explain what one row of the CSV represents.

---

## 4. Phase 1 — IDS + SHAP layer, producing a clean "anomaly event" (Week 2–4)

**Goal:** a script that takes a flow, predicts attack/normal, runs SHAP, and outputs one JSON object. This JSON is the *contract* between the ML side and the contextualizer — the "model-agnostic" boundary your proposal sells.

### Why re-do Layer 1 if models already exist
The saved models were trained multiclass with SMOTE on a 256-vs-304k imbalance. For your thesis you want (a) a **binary** attack/normal head that is simple and robust, (b) a **train/test split that never mixes** so metrics are honest, and (c) **no leaky features** (drop or audit `Dst Port`; never add IP). Clean this up now so SHAP explains signal, not artifacts.

### Tasks

- **1.1 Consolidate + label.** Merge the 8 CSVs, create a binary label (`attackfree` → 0, everything else → 1). Do a stratified 70/30 train/test split. *Why stratified:* keeps the rare normal class present in both halves. `[model: Sonnet — routine data wrangling]`
- **1.2 Handle imbalance honestly.** Use `class_weight="balanced"` in a `RandomForestClassifier` rather than SMOTE-ing 300k synthetic rows. *Why:* class weighting doesn't fabricate data, so SHAP stays interpretable; report precision/recall/F1 and a confusion matrix, **not** accuracy (accuracy is meaningless at this imbalance). `[model: Sonnet]`
- **1.3 Leakage audit.** Train once, look at feature importances. If `Dst Port` or any single feature gives near-perfect separation, investigate — it likely encodes the real-vs-sim subnet artifact. Document what you keep and why. `[model: Opus — judgment call]`
- **1.4 Wire SHAP.** Use `shap.TreeExplainer` (fast and exact for tree models). For a given flagged flow, output the top-k features with their SHAP values and the feature's actual value. `[model: Sonnet, with Opus if the SHAP API confuses]`
- **1.5 Emit the anomaly-event JSON.** Design and freeze this schema, e.g.:
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

## 5. Phase 2 — Knowledge base + synthetic IEEE-13-bus overlay (Week 4–6)

**Goal:** the authored "physical world" — the documents LightRAG will turn into a graph, plus the IP→device mapping that joins network to physics.

Your slides already scoped these documents well. Author them as plain Markdown files; keep everything **synthetic and paraphrased from open standards** (you already stated this — good for IP/licensing).

### The documents (each is a graph "source")

- **2.1 Grid topology (the single source of truth).** The IEEE 14-bus system: buses, lines, generators/synchronous condensers, transformer taps, breakers/relays, normal operating ranges (voltages, line thermal limits). Then add the **IP→device mapping table** joining `10.0.0.5` → "RTU-3 @ Bus 4 …". Tip: pull the exact `case14` bus/line numbers straight from MATPOWER so your synthetic doc stays consistent with the simulator you may use in the stretch goal. *Why first:* every other document and every CPAS dimension except R depends on it. `[model: Opus — needs correctness and internal consistency]`
- **2.2 Feature dictionary (the crucial bridge).** For each of the ~79 flow features: plain-English meaning, and which attack behaviors a high/low value implies (e.g., "very low `Flow IAT Std` + high `Flow Packets/s` ⇒ flooding/DoS"). *Why this is the linchpin:* this is what lets the system translate "SHAP said `Flow IAT Std`" into "this looks like a flooding pattern," which is the actual semantic hop. Without it, the LLM guesses. `[model: Opus — this is the intellectual core]`
- **2.3 Attack taxonomy.** For each attack class in your data (DoS, flood, fuzzy, MITM, NTP-DDoS, port-scan, starvation): signature, network fingerprint, and *physical* consequence on the feeder. `[model: Sonnet, reviewed by Opus]`
- **2.4 Physics reference.** Paraphrased power-flow/protection principles needed for consequence reasoning (relay grading, load-shed thresholds, fault types). `[model: Opus for accuracy]`
- **2.5 Operator playbooks.** Role-specific response steps per attack class. `[model: Sonnet]`

**Exit check:** a human can trace one scenario end-to-end on paper: flagged flow → dst IP → device → attack class → physical consequence → operator action, using only these docs.

---

## 6. Phase 3 — LightRAG contextualizer + multi-persona synthesizer (Week 6–9)

**Goal:** feed the anomaly-event JSON in, get three role-specific narratives out.

### Tools

- **LightRAG** — a Retrieval-Augmented-Generation library that builds a *knowledge graph* from your documents and retrieves both local facts and community summaries (its "dual-level retrieval"). Install with `pip install lightrag-hku`. *Why LightRAG over plain vector RAG:* your reasoning is relational ("this breaker protects that zone"), which a flat similarity search misses; a graph captures those edges. *Why not Neo4j:* LightRAG has a built-in store; only add Neo4j if you later need its query tooling.

### Tasks

- **3.1 Ingest the KB.** Point LightRAG at your Phase-2 Markdown files to build the graph once. *Why once:* graph construction uses an LLM and costs time/tokens; build it, then reuse. `[model: for ingestion, a mid model like Gemini Flash or Claude Haiku is fine and cheap]`
- **3.2 Build the orchestrator.** A Python script that: (a) takes the anomaly-event JSON, (b) forms one LightRAG query combining the SHAP features + dst IP, (c) retrieves the **Multi-Domain Context Block**. *Why one shared context block:* your proposal's efficiency claim — retrieve once, reuse for all three personas. `[model: Opus — orchestration logic]`
- **3.3 The 3-persona synthesizer loop.** Same context block, three system prompts (Operator / Data Scientist / Regulator), `temperature=0`. Run the *in-pipeline* LLM locally via Ollama. *Why local + temp 0:* reproducibility (a thesis needs re-runnable results) and cost control across many scenarios. *Recommended starting model:* **Llama 3.1 8B Instruct** or **Qwen2.5 7B Instruct** — both fit in 16 GB and follow role prompts well. **Then evaluate quality against CPAS + a human spot-check and choose your path (see Section 7.5):** if 7–8B is good enough, stop. If it hallucinates or ignores personas, either (a) swap to an API model (Gemini Pro as synthesizer, keeping Claude as judge) for strong reasoning with no HPC, or (b) host a 70B open model on Trillium GPU if you need a self-hosted/reproducible model. `[model: start local 7–8B; escalate per 7.5; use Opus to write and refine the prompts]`
- **3.4 Guardrail against hallucination.** Instruct the synthesizer to use *only* facts in the provided context block, and to say "not in context" otherwise. *Why:* this is exactly what your CPAS **H** (hallucination) penalty will test — build for it. `[model: Opus for prompt design]`

**Exit check:** one anomaly event yields three distinctly-voiced, context-grounded narratives.

---

## 7. Phase 4 — CPAS evaluation harness (Week 9–11)

**Goal:** quantify whether the full system beats the two baselines.

### The circularity problem you must design around
Your proposal has an LLM generate explanations grounded on a synthetic KB, then an LLM judge them against that same KB. If synthesizer and judge are the *same model family*, you measure self-preference, not quality. **Rule: the judge must be a different, stronger model than the synthesizer.** Concretely — synthesizer = local Llama/Qwen 7–8B; **judge = Claude (Opus/Sonnet) or Gemini Pro via API.** Also do a small **human spot-check** (you score ~5 scenarios yourself) to validate the judge agrees with a human. `[model: judge = Opus-class API model]`

### Tasks

- **4.1 Curate 15 scenarios:** 5 true-positive cyber, 5 true-positive physical, 5 false-positive noise (per your design). For each, fix the input flow and the expected key facts. `[model: Opus — designing fair test cases]`
- **4.2 Implement the three tiers:** (A) IDS output only; (B) IDS + raw SHAP; (C) full system. *Why:* this A/B/C is your evidence that context — not just XAI — drives the improvement. `[model: Sonnet to code the harness]`
- **4.3 Encode the CPAS rubric** (D, C, A, R each 1–5; H as a 0/1 penalty multiplier) as a strict judge prompt returning JSON scores. Pin down the weights `w` and *pre-register them* before running, so you can't be accused of tuning to the result. `[model: Opus — rubric + judge prompt]`
- **4.4 Re-scope the C (Cascading Impact) dimension honestly.** You have no power-flow ground truth, so define C as *plausibility and consistency with the physics KB*, not physical truth — unless you add the stretch item below. State this in the report. `[model: Opus]`
- **4.5 Run, aggregate, plot** CPAS by persona × tier. Expect C > B > A. `[model: Sonnet]`

**Stretch — real C ground truth:** install **pandapower** (a Python power-flow simulator, ships the IEEE 14-bus case built-in), model the 14-bus system, and simulate the physical consequence of each scenario (e.g., open a line and check for overloads/voltage violations). Then C becomes measurable against a simulation, which materially strengthens the thesis. This is CPU-only and tiny — it does **not** need HPC. Only attempt if Phases 0–4 are done with weeks to spare.

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
4. Too weak, and self-hosting/air-gap *is* part of your contribution? **Use Trillium GPU to serve a 70B open model** (vLLM). Budget ~3–5 days to learn SLURM + vLLM; ask me for a step-by-step when you reach this branch.

**What HPC is *not* for here:** the RF IDS (trains in seconds on CPU), SHAP (fast), LightRAG ingestion (one-time, use an API), and the pandapower stretch simulation (CPU, tiny). Don't move those to HPC.

---

## 8. Phase 5 — Analysis, write-up, limitations (Week 11–14)

- **5.1 Results narrative:** does context close the semantic gap, and for which persona most? `[model: Opus]`
- **5.2 Limitations (be your own harshest reviewer):** synthetic topology (D/C measure coherence with a fictional grid, not field truth); real-vs-sim subnet domain shift; small attack-free sample; single-feeder scope; judge-model bias mitigated but not eliminated. `[model: Opus]`
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

*Open questions to resolve with your advisors, flagged honestly:*
- Is a **single synthetic feeder** enough novelty, or do they expect multiple topologies? (Affects Phase 2 effort.)
- Do they require **real protocol semantics** (re-extracting ASDU/IOA from PCAPs), or is the flow-based + KG-overlay framing acceptable? (This is the biggest scope lever.)
- Is **binary detection** sufficient for Layer 1, or must you also classify attack type?
