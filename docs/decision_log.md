# Decision Log — CCIR / IEC-104 XAI project

Chronological record of problems encountered during implementation and the
decisions/mitigations made. Complements the plan (`IMPLEMENTATION_PLAN.md`, the
*intended* design) and the authoring/findings notes (the *how*). This is the
*why we changed course* record — read it to avoid re-deriving settled decisions.

Format per entry: **Problem → Decision → Why**. Newest phases at the bottom.

---

## Planning phase — architecture corrections

### D1. SHAP cannot attribute to protocol semantics (the core reframe)
- **Problem:** the proposal's story ("SHAP flags ASDU TypeID → map to a breaker")
  is impossible: the model trains on CICFlowMeter *flow statistics*, which contain
  no ASDU/IOA/protocol fields.
- **Decision:** separate the two worlds — a flow-stat IDS (learned) and a synthetic
  physical overlay (authored), joined at the contextualizer by IP, not in the model.
- **Why:** keeps the ML honest (SHAP genuinely explains network behavior); the grid
  mapping is a defensible authored overlay, not a circular feature injection.

### D2. IP is a label leak → never a model feature
- **Problem:** real (attack-free) traffic is on `10.0.0.x`; every simulated attack is
  on other subnets — source IP alone nearly separates the classes.
- **Decision:** split columns by role — metadata (IPs, ports, timestamp) travels with
  each row for the contextualizer join but never enters the feature matrix; an assert
  guards the boundary. Do not delete the raw data.
- **Why:** prevents leakage while preserving the join key; raw data stays immutable.

### D3. IEEE 14-bus over 13-node feeder
- **Problem:** which grid model.
- **Decision:** IEEE 14-bus transmission case.
- **Why:** cascading (the C-score differentiator) is a *meshed transmission*
  phenomenon; a radial feeder can't cascade. Also 14-bus is native to pandapower;
  the 13-node needs unbalanced-3φ tooling. (Stale "13-bus"/"feeder" wording later
  purged from the plan.)

### D4. The no-expert constraint (user has no power-systems background)
- **Problem:** user cannot author or validate physical ground truth, and has no
  access to domain experts.
- **Decision:** no ground truth may depend on human judgment — derive everything from
  published benchmark data (case14), the simulator (pandapower), own construction
  (the fictional IP map), or public prose (NIST/NERC/SANS). pandapower promoted from
  stretch to core scope.
- **Why:** the solver becomes the "domain expert"; consequences are computed, not
  opined. Turned a constraint into a stronger (simulator-grounded) thesis claim.

### D5. Benchmark reproduction (task 0.2) descoped
- **Problem:** the legacy 14-model PyCaret sweep takes ~7 h locally and kept
  failing on timeouts; the bundled `.pkl` turned out to hold only class labels, no
  model.
- **Decision:** reproduce only the RandomForest row (~10 min); cite the authors' full
  table from their log. Pipeline control was independently shown by Phase 1.
- **Why:** nothing downstream consumes it; 7 h for a provenance check isn't worth it.

### D6. HPC (Trillium) deferred; conda scoped to the Mac
- **Problem:** does the project need the HPC cluster; Trillium discourages conda.
- **Decision:** HPC only for the one optional case (serving a 70B model over HTTP in
  Phase 3+). Conda is Mac-only; the cluster would use module+venv. Environments never
  need to match because machines communicate over HTTP, not shared code.
- **Why:** the layered contract makes "where the model runs" a deployment detail.

---

## Environment (Phase 0)

### D7. Three-Pythons hazard → conda-only discipline
- **Problem:** system python.org 3.14 was first on PATH and hijacked bare `pip`
  (installed `ccir` into the wrong interpreter) and the default Jupyter kernel
  (crashed on missing seaborn).
- **Decision:** removed python.org 3.14 + brew python@3.13; kept brew python@3.14
  (a dependency of ollama/texlive — never used for project work). Rules: always
  `python -m pip`, `conda run -n xai`, and explicitly-named Jupyter kernels.
- **Why:** implicit interpreter selection silently picks the wrong Python. (Plan
  Appendix B.)

### D8. Two quarantined conda envs
- **Problem:** legacy notebooks need pycaret 3.3.2, which pins old libs conflicting
  with the modern stack.
- **Decision:** `xai` (all new work) vs `pycaret_env` (legacy notebooks only); never
  merge. Notebook data paths repointed to the repo copy (iCloud folder had moved).
- **Why:** isolation keeps the reproducible stack clean.

---

## Phase 1 — IDS + SHAP

### D9. class_weight over SMOTE
- **Problem:** severe imbalance (~255 normal vs ~320k attack rows).
- **Decision:** `class_weight="balanced"` RandomForest, not SMOTE oversampling.
- **Why:** SMOTE fabricates rows; SHAP on a model shaped by synthetic data is hard to
  defend. Class weighting reweights real rows only.

### D10. Perfect 1.0 test scores — documented, not celebrated
- **Problem:** the binary model scores perfectly (0 errors on 95,992 test flows).
- **Decision:** treat as a *finding* — a diffuse real-vs-sim artifact spread across
  many features (audit found NO single leaky feature; `Dst Port` isn't top-10).
  Report precision/recall/F1, state the artifact in Limitations.
- **Why:** detection was never the contribution; suspiciously-perfect must be
  explained, not hidden. Consequence → D14.

### D11. joblib + feature_list.json as the persistence contract
- **Problem:** SHAP/inference must feed columns in the exact training order — wrong
  order is a *silent* wrong-answer bug, not a crash.
- **Decision:** persist `ids_rf.joblib` + `feature_list.json` + `metrics.json`; all
  downstream code joins on the frozen feature-name list. Also: this shap version
  returns `(rows, features, classes)` — slice class 1.
- **Why:** makes the ML↔XAI boundary explicit and reproducible.

---

## Phase 2 — Knowledge base

### D12. Provenance split (generate vs draft+gate)
- **Problem:** how to author a KB with no domain expertise without fabricating.
- **Decision:** route every fact by provenance — machine-checkable source → generate
  by script (topology, model card, consequences, IP coverage); no source → draft from
  a cited reference then gate via `check_kb.py` (+ simulator for physics numbers).
- **Why:** find-and-replace intuition is right only for the generated bucket; the rest
  needs judgment but not *unchecked* judgment. (Plan §2.9.)

### D13. Canonical entity registry + skill/agent/code split
- **Problem:** multi-document LLM authoring drifts on names ("RTU-3" vs "RTU 3") →
  duplicate graph nodes.
- **Decision:** `entities.yaml` as the single source of every fictional proper noun,
  built first; a `kb-author` skill holds the rules; `check_kb.py` enforces them.
  Device roles were *derived from the captures*, not invented (10.0.0.2 = only
  port-2404 client = SCADA master; etc.).
- **Why:** shared vocabulary is what makes independently-drafted docs one coherent
  graph. Later validated by D18.

### D14. False-positive scenarios need a weakened model
- **Problem:** Phase 4 needs 5 false-positive scenarios, but the perfect model (D10)
  can't produce a false positive.
- **Decision:** source them from a deliberately feature-constrained model variant;
  state it honestly.
- **Why:** the perfect model turned a latent Phase-4 gap into a deliberate design.

### D15. Source-catalogue tiering + evidence trap
- **Problem:** the source list ballooned to 12 doc types (contradicting its own "more
  is not better"); and teaching the LLM protocol facts invites in-context-but-
  unwarranted claims ("malformed ASDU sent") the model can't actually see.
- **Decision:** tier docs ★ core / ○ deferred (build ○ only on a measured CPAS gap);
  add the "background context vs incident evidence" rule to prompts + judge. Primary
  attack source = the SANDI-2024 paper (owned); MITRE IDs cross-mapped but flagged
  for verification. Kundur textbook cited sparingly (dynamics ≠ our steady-state
  scope; also: Prabha Kundur ≠ supervisor Deepa Kundur).
- **Why:** each extra doc is retrieval noise; the evidence boundary is a subtler
  failure than hallucination.

### D16. check_kb rules relaxed on contact with reality
- **Problem:** rule 4 required unique MITRE IDs (but DoS is legitimately shared by
  several attacks); rule 2 read backticked *file paths* as feature names.
- **Decision:** rule 4 → format-validation only; rule 2 → Title-Case tokens only.
- **Why:** over-strict checks produce false failures; the checks self-corrected during
  authoring (a good sign the gate works).

### D17. Topology voltage-limit inconsistency
- **Problem:** the exporter hardcoded a 1.06 p.u. ceiling the solved base case (1.090)
  violates — generator buses regulate high.
- **Decision:** state limits as 0.94–1.10 p.u. and regenerate the topology doc.
- **Why:** the KB must not contradict the simulator it's derived from.

---

## Phase 3 — LightRAG contextualizer

### D18. §3.1b graph-verification: naming consistent, extraction sparse
- **Problem:** the 8B model under-extracted — generic `RTU`/`RTUs` nodes, only `RTU-3`
  individuated, zero breakers/buses.
- **Decision:** accept the (consistent) naming; flag the sparsity for remediation.
- **Why:** validated D13's discipline held where entities appeared; identified the
  real gap (missing systematic entities). Led to D22.

### D19. Embedding dimension mismatch (768 vs 1024)
- **Problem:** LightRAG's bundled `ollama_embed` is pre-decorated `embedding_dim=1024`
  (for bge-m3), which halts the pipeline against nomic's true 768.
- **Decision:** bypass the helper — call Ollama directly, wrapped in one correct
  `EmbeddingFunc(768)`. Also: wipe a partial `rag_storage/` before re-ingesting.
- **Why:** one embedding path, one declared dimension, no wrapper conflict.

### D20. Persona collapse + meta-pollution (first synthesis)
- **Problem:** all three personas produced identical, generic output that leaked KB
  scaffolding ("Phase 2", "CPAS dimensions").
- **Decision (free fixes):** exclude README.md from ingestion; cap the context
  (a 44k block drowned 8B instruction-following); repeat the role instruction in the
  *user* turn (8B under-weights the system role).
- **Why:** fixed persona collapse; isolated the remaining issue as content, not voice.

### D21. Entity hallucination ("RTU-123")
- **Problem:** with an honest small context, the 8B model invented device/breaker
  names absent from the sparse graph (D18).
- **Decision:** → D22.
- **Why:** confirmed the failure was *missing facts*, not reasoning — so a stronger
  model wouldn't fix it; the graph had to be completed.

### D22. Graph pre-seeding + deterministic device join (RESOLVED)
- **Problem:** D21.
- **Decision:** (a) `seed_graph.py` injects canonical entities.yaml facts into the
  graph via `ainsert_custom_kg` (run after ingest); (b) resolve the dst_ip
  *deterministically* from entities.yaml and prepend an authoritative DEVICE block —
  the IP is a table **join key** (plan §1), not a semantic-search target. Replaced the
  `max_total_tokens` re-budget (which dropped seeded facts) with a plain char cap.
- **Why:** don't make an 8B model + vector search do a dictionary's job. Result: all
  personas now correctly name RTU-3 / 10.0.0.5 / Bus 6 / real breakers; hallucination
  gone.

### D23. Residual model-quality gaps deferred to §7.5
- **Problem:** the 8B synthesizer still gets the CIP timeline wrong ("24 h" vs
  1 h/next-day) and names features loosely — facts are in the KB, the model
  under-uses them.
- **Decision:** defer the model-escalation decision (bigger local / API model) until
  Phase 4 CPAS scores quantify the gap; keep 8B for the baseline.
- **Why:** the plan pre-registered exactly this "measure, then decide" checkpoint;
  device/topology grounding (the architecture question) is solved.

---

## Phase 4 — CPAS evaluation harness

### D24. Scenarios pair real attack flows with authored target RTUs
- **Problem:** NO attack flow in the captures targets a real RTU — all attack
  traffic is on the 121.x testbed subnet; only normal traffic reaches 10.0.0.x
  (the real/sim domain shift, D2, at its starkest). So an attack flow's dst IP
  cannot supply a physical target.
- **Decision:** a scenario uses the real attack flow's *statistics + SHAP* (learned
  network evidence) and *assigns* a target RTU (authored physical overlay, joined at
  the contextualizer per D1). Physical-consequence RTUs (1,3) → tp_physical;
  absorbed RTUs (2,4) → tp_cyber. Fact-sheet consequences come from the simulator.
- **Why:** the only honest construction given the data; consistent with the core
  architecture (network learned, physical authored). Stated explicitly in
  `cpas_protocol.md` and every scenario file.

### D25. False-positive pool needs a heavily weakened model
- **Problem:** even dropping the top 25 features, the model stays perfect (D10's
  redundancy) — no false positives to explain.
- **Decision:** drop top 50 features + shallow trees (max_depth 4); FP scenarios =
  the 5 real normal flows this weakened model scores most attack-like (top one hits
  0.59 attack-prob). Saved as `ids_rf_constrained.joblib`.
- **Why:** reaches the uncertain regime honestly; the separation is so redundant a
  mild constraint isn't enough.

### D26. Judge model is a pending user decision (blocks scoring only)
- **Problem:** the plan requires judge ≠ synthesizer, stronger; no API keys are set
  and only llama3.1:8b is local.
- **Decision:** built the harness judge-agnostic (`CCIR_JUDGE`); the actual model
  choice (Claude/Gemini API vs a distinct local model) is surfaced to the user. All
  judge-independent work (scenarios, fact sheets, tiers, pre-registered rubric) done
  first so only final scoring waits.
- **Why:** a genuine decision needing the user's key/preference; everything else
  proceeds without it. *(Resolved: user chose Claude Opus 4.8 via the Anthropic API;
  `judge.py` uses the SDK, key loaded from a gitignored `.env` via python-dotenv.)*

### D27. Judge pilot: narrow H to grounded-fact contradictions
- **Problem:** the first judge smoke-test (scenario_02 tier-C operator) scored CPAS
  0.0 — H=0 fired because the narrative inferred a "flood/scan" attack when the gold
  class is `starvation`. But the binary detector never conveys the class, and
  flooding-family attacks (DoS/flood/starvation) are near-indistinguishable from flow
  statistics, so the narrative *cannot* name the exact class — it grounded the
  device/bus/breakers perfectly. Left as-is, H would systematically zero tier-C and
  make the whole report uninformative (a false negative about the system's grounding).
- **Decision:** narrow the **H** penalty to contradicted *grounded facts* (device,
  bus, breaker, consequence, reporting duty); a wrong attack-*type* inference now
  lowers **D** (diagnostic accuracy), not H. Also added a persona-prompt line telling
  the synthesizer to describe attack *behavior* (flooding-family) rather than assert
  a class it can't determine; tier-C regenerated to match. Amended in both
  `judge.py` and the pre-registered `cpas_protocol.md` with a dated note.
- **Why:** grounded-fact contradictions (hallucinations) and evidence-based
  inferences are different failures — the §2.8 evidence-trap distinction. H guards
  the former, D grades the latter. **Legitimate because it was a pilot finding made
  *before* the full run** (exactly the §7.6 #2 workflow: pilot the judge, fix rubric
  misfires, then run) — not tuning to results. Verified: the same narrative rescored
  0.0 → 3.0, with D=3 (class not named — the honest binary ceiling multiclass would
  lift, [[D24]]/§11.9) and C=2 (didn't use the specific simulated consequence — a real
  8B quality signal, correctly under C).

## Cross-cutting conventions established
- Raw data immutable; inputs (`data/`, `knowledge_base/`) vs regenerable outputs
  (`models/`, `rag_storage/`, `experiments/results/`) never mixed.
- Commit straight to `main` (solo repo, linear history); no branch/PR overhead.
- `python -m ccir.<module>` entry points; scripts fail loudly on missing inputs.
- Every KB fact traces to one file; `check_kb.py` gate must pass before Phase 3.
