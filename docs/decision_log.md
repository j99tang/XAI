# Decision Log — CAIE (Context-Aware Intrusion Explanation) / IEC-104 XAI project

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
  (installed `caie` into the wrong interpreter) and the default Jupyter kernel
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
- **Decision:** built the harness judge-agnostic (`CAIE_JUDGE`); the actual model
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

### D28. Synthesizer backend made pluggable; upgrade decision deferred to post-baseline
- **Problem:** the local 8B synthesizer has known quality gaps (D23: wrong CIP
  timeline, doesn't use the specific simulated consequence). Tempting to upgrade the
  model now — but that would be reacting to anecdote, not the pre-registered CPAS
  measurement (§7.5 is a "measure, then decide" gate).
- **Decision:** built the enabling infrastructure but **did not upgrade**.
  `synthesize.py` now dispatches on `CAIE_SYNTH_BACKEND` — `ollama` (default,
  baseline unchanged) or `openai` (any OpenAI-compatible endpoint: OpenRouter, a
  hosted 70B, Gemini-compat). The upgrade is now a one-env-var swap. Sequence: run
  the 8B baseline CPAS first → read which dimensions are weak → only if R/C
  (reasoning/retrieval) are low is a stronger model worth testing (cheaply, via
  OpenRouter, same scenarios+judge) → only then consider HPC if air-gap self-hosting
  is a thesis claim.
- **Why:** a bigger model does **not** fix the class-naming miss (that's structural —
  binary detector never conveys the class; multiclass is the lever, [[D27]]/§11.9).
  It only helps the reasoning/retrieval gaps, and whether those dominate is a
  question only the baseline table answers. Swapping the synthesizer through the
  unchanged `AnomalyEvent` contract is also itself a result (agnosticism demo).
  Enabled cheaply-first via OpenRouter per the earlier reseller discussion (avoids
  the HPC learning curve until proven worth it).

### D29. Baseline CPAS (8B): context improves substance but hallucination gates it
- **Problem/result:** first full CPAS run (Opus 4.8 judge, batch API, 8B synthesizer)
  did NOT show C > B > A on the multiplied score — tier C often scored *worse* (regulator
  C = 0.21). Details + table: `docs/notes/phase4_baseline_cpas.md`.
- **Finding (not a bug):** on raw dimensions C wins on all four (D2.87/C1.73/A2.49/R2.56
  vs A/B ~1–2.3) — the contextualizer genuinely improves narrative quality. But the H
  (hallucination) penalty zeroes 25/45 tier-C narratives, dropping multiplied CPAS below
  the sparse A/B floor (A/B have almost no grounded facts to contradict → never zeroed).
  Failure is concentrated + retrievable: regulator 14/15 state a wrong CIP timeline
  ("24 hours" vs the KB's 1 hour), operator 10/15 hallucinate a grounded fact. The
  correct timeline is in the KB (one narrative got "60 minutes" right), so the 8B is
  ignoring context for its training prior.
- **Why it matters:** the thesis result is richer than "C>B>A" — context improves
  substance (raw D/C/A/R) but the value is bottlenecked by synthesizer reliability; a
  confidently-wrong grounded fact is worse than sparse-but-correct output. Present both
  tables. And this is the clear §7.5 signal: the dominant failure is a *retrievable-fact*
  hallucination (fixable by a stronger model, [[D28]]), not the structural class-naming
  limit ([[D27]], needs multiclass). The upgrade test is now justified — predicted to
  flip ~24 H=0→H=1 and lift tier-C CPAS above A/B.

### D30. CPAS formula corrected to the proposal's subtractive form
- **Problem:** the implemented `CPAS = H·raw` (multiplicative gate) zeroed any tier-C
  narrative with one contradicted grounded fact, letting sparse A/B tiers float on a
  floor — structurally rewarding saying less (surfaced by D29).
- **Decision:** restore the **original proposal's additive/subtractive** form
  `CPAS = w_D·D+w_C·C+w_A·A+w_R·R − λ·H`, λ=2.0, H polarity flipped (H=1 = hallucination
  present). Updated `judge.py` + `cpas_protocol.md`. The 2026-07-10 baseline was
  **recomputed from the stored raw D/C/A/R/H** (no re-judging) into
  `cpas_scores_corrected.json`; table in `phase4_baseline_cpas.md`.
- **Why:** a correction *to* pre-registration (matches the proposal), not post-hoc
  tuning. Effect: hallucinations now degrade (−2) instead of erasing; operator C rises
  above A/B, regulator C 0.21→0.55. But it does **not** overturn D29 — 25/45 tier-C
  still hallucinate a grounded fact, so C still doesn't clearly beat B on the composite
  (the hypothesis holds on raw dimensions, [[D29]]). Still the §7.5 upgrade signal.

### D31. Per-dimension reasons added; a coverage metric considered and rejected
- **Prompt:** surveyed Microsoft's Azure AI Foundry evaluators. They split grounding
  into `Groundedness` (precision — no fabrication) and `Response Completeness`
  (recall — nothing critical missing). CPAS appeared to have only the precision half
  (H), suggesting sparse tier-A/B narratives went unpunished for omission ([[D29]]).
- **Rejected — the premise was wrong.** Checked against the stored baseline: the
  share of narratives scoring the FLOOR (=1) is A: C=73% A=100% R=82% /
  B: C=69% A=100% R=58% / C: C=40% A=11% R=0%. The 1-anchors ("no actionable step",
  "no physical referent") **already** score omission, and do so hard. A separate
  coverage term would double-count — a narrative omitting the consequence is charged
  once at C=1 and again on coverage — inflating the tier gap artificially. Reporting
  it alongside CPAS is no better: a second number ~collinear with the first is the
  same evidence printed twice, not corroboration.
- **Corrected diagnosis of D29/D30:** the sparse-tiers-float problem is NOT a missing
  recall term. Raw D/C/A/R separates the tiers cleanly (C wins all four, gap ~1.0-1.5).
  The problem is confined to the composite, where a flat λ=2 swamps that gap. **λ is
  the whole issue**; coverage would not have touched it.
- **Kept:** a one-sentence judge reason per dimension, emitted *before* the score.
  Diagnostic only, no formula change. Motivated by D29 costing manual re-reading to
  find "regulator 14/15 state a wrong CIP timeline" — now greppable in `reasons.R`.
- **Residual gap (accepted):** the floor is 1, so "stated it wrongly" and "never
  mentioned it" are indistinguishable in the scores. The reasons now carry that
  distinction in prose, which is sufficient; no metric change.
- **Caveat:** requiring written reasons is a mild chain-of-thought intervention, so a
  re-judged run is not byte-comparable to the 2026-07-10 baseline. Quote both with
  their judge-prompt version.
- **Also not adopted from Foundry:** `applicable: false` dimension-skip (R is scored
  everywhere — persona alignment is the thesis contribution, so R is most diagnostic
  exactly where it would have been skipped); tool-call and safety evaluators.
- **Still open, and now the priority:** λ sensitivity sweep (λ ∈ {1,2,3} recomputed
  from stored raw scores, no re-judging) and a human-agreement check (~20 hand-scored
  narratives vs the Opus judge).

### D32. Model map written; the KB-authoring model was missing from every diagram
- **Problem:** no artifact answered "which model runs where". §1 diagrams the
  network/physical split and §2.9 states the authoring policy, but nothing mapped the
  five model touchpoints end to end. Two things were being mis-stated as a result:
  (a) the system was described as **multi-agent** — it is not: no component chooses
  its own next action, selects tools, loops, or messages another. It is a staged
  pipeline with two independent LLM roles (in-loop generator, out-of-loop judge).
  The determinism is load-bearing — an agent that picked its own retrieval strategy
  would confound tier C's advantage with agent behaviour and break the ablation.
  (b) the **KB-authoring model was invisible**. `knowledge_base/*.md` was drafted by
  Claude via the `kb-author` skill (plan §2.9) from `kb_extract.py` output. Build-time,
  not runtime — but still a model that shaped the results.
- **Decision:** `docs/model_map.md` is now the single source of truth for model usage,
  covering build time (0a-0c, 1, 2), runtime (3), and evaluation (4), and marking
  which stages use **no model at all** (device join, gold facts, tiers A/B, `cpas()`).
- **Why it matters:** the system is framed as a local-8B deployment, but its knowledge
  substrate was authored with frontier-model help. A reviewer will ask whether Claude's
  training data leaked into the KB (e.g. did the 1-hour CIP timeline come from the NERC
  PDF or from model memory?). The mitigations already exist and must be *stated*:
  `kb_extract.py` extracts from the actual PDFs deterministically, `check_kb.py` gates
  five consistency rules, provenance headers declare synthetic overlays, and gold fact
  sheets are LLM-free entirely. Claim LLM-assisted authoring with enforced provenance —
  never a hand-written KB.

### D33. Full-KB control condition — isolating retrieval from synthesis (PARKED)
- **Problem:** when a tier-C narrative is wrong, we cannot currently attribute it.
  Either retrieval never placed the fact in the context block, or the fact was there
  and the 8B ignored it. Both look identical in the output. [[D29]] asserts the second
  ("the correct timeline is in the KB") — but *in the KB* is not *in the context block*,
  and retrieval sits between them.
- **Measurement that forces the issue:** whole KB = 26,615 chars (~6.6k tokens);
  `retrieve_context` caps the block at 9,000 chars. Retrieval discards ~2/3 of a corpus
  that fits in the 8B's context window ~19x over.
- **Decision:** add a `C_full` control — skip retrieval, concatenate all KB files,
  synthesize. Identical model, personas, temperature, judge, and gold facts; the single
  changed variable is whether retrieval happened.
- **How to read it:** C_full is the no-retrieval **ceiling**, so the C→C_full gap is the
  upper bound on what better retrieval could ever buy. Gap ≈ 0 → retrieval is exonerated,
  the synthesizer is the bottleneck, and models [1] and [2] are ruled out without testing
  them. Large gap → retrieval is dropping facts and [1]/[2] become worth money.
- **Scope:** a methodological control, NOT a fourth tier of the main hypothesis and NOT
  a proposed replacement for the graph — a real utility KB fits in no context window, so
  retrieval remains the right architecture. This measures its cost at a scale where the
  ceiling happens to be knowable.
- **Status: PARKED (2026-08-18), not rejected.** Superseded in priority by the
  capability-sweep programme ([[D34]]): if that sweep shows context helps once the
  synthesizer is strong enough, retrieval is exonerated by a stronger argument than
  this control provides. Revisit only if the sweep shows context failing to help at
  EVERY capability level — that is the outcome where retrieval becomes the prime
  suspect and this control becomes the cheapest way to confirm it.
- **Upgrade ordering (one variable at a time):** C_full control (free) → synthesizer
  [3] (§7.5, pre-registered, and the ONLY upgrade that does not rebuild the graph) →
  extractor [2] only if the control demands it. Never [2] and [3] in the same run:
  both are `llama3.1:8b` so it feels like one change, but it is two, and a rebuilt graph
  changes tier C and forces re-running tiers *and* re-judging. Embeddings [1] are lowest
  value at this KB size and carry the `EMBED_DIM` re-index trap.

### D34. Programme change: drop Trillium; frontier-ceiling then open-weights capability sweep
- **Decision (2026-08-19):** abandon the Trillium HPC path ([[D28]] §7.5). Instead:
  (1) a **ceiling run** on a frontier closed-weights synthesizer via API, to establish
  that CPAS A<B<C is attainable at all; (2) the **pivot** — OT deployment constraints
  make an external API call an unsafe dependency for critical infrastructure; (3) a
  **capability sweep** over open-weights synthesizers via OpenRouter. Model swapping
  rides the existing `CAIE_SYNTH_BACKEND` seam, so the `AnomalyEvent` contract is
  untouched — the swap *is* the model-agnosticism claim.
- **Reframe (the important part): aim to LOCATE A CAPABILITY THRESHOLD, not to prove
  generalization.** "The framework generalizes" is a hope that [[D29]] already
  contradicts (llama3.1:8b does not beat tier B). Asking *"at what model capability
  does grounded context start to help?"* makes every outcome a result: low threshold =
  deployment story; mid threshold = a concrete minimum on-prem spec; above all open
  weights = a genuine negative finding (context grounding demands capability current
  air-gappable models lack) — which is publishable and useful to the OT audience.
  Under this framing D29 becomes supporting evidence rather than a disappointment.
- **Hard constraint — vendor independence.** The synthesizer and the judge must never
  share a vendor. OpenRouter puts Claude one string away from the synthesis slot, which
  would have the judge grading its own family and destroy the §7.6 independence control.
  Frontier synthesis must be GPT-5.x / Gemini class while Claude judges. Enforce in
  code, not in prose.
- **One axis only.** "Runtime models" = synthesis + embedding + extraction. Embedding
  changes force a full re-index (the `EMBED_DIM=768` trap); extraction changes rebuild
  the graph, which changes tier C and forces re-running tiers AND re-judging. **Vary the
  synthesis slot only; hold the graph fixed across the entire sweep.**
- **The evaluator is NOT part of the sweep.** The judge is the measuring instrument;
  varying the ruler and the measured object together yields nothing. Judge sensitivity
  is a separate robustness appendix: freeze one narrative set, score with 2-3 judges,
  report whether the tier ordering survives.
- **Self-hosting honesty.** Open-weights models will be run *via OpenRouter*, a cloud
  API, to argue for on-prem deployment. State plainly that the API is experimental
  convenience and the weights are self-hostable — that is the deployment claim. Keep
  at least one genuinely local model (llama3.1:8b on Ollama) in the sweep as the anchor
  datapoint proving the local path actually runs.
- **Statistics.** Claiming A<B<C requires a paired test (Wilcoxon signed-rank, paired by
  scenario), not a comparison of means, plus multiple-comparison handling across models.
  See [[D35]] for the unit-of-analysis problem that makes the current n much smaller
  than it appears.

### D35. Scenario set lacks consequence diversity — C and R are barely tested
- **Problem (measured 2026-08-19, not suspected):** across all 15 scenarios there are
  only **4 distinct `physical_consequence` strings** and **2 distinct `reportable`
  strings**. Worse, consequence is a pure function of the *device*: each
  `consequences_RTU-N.json` is one simulation opening ALL of that RTU's breakers, so
  scenario_01 and scenario_02 are identical on C, A and R and differ only in attack class.
- **Effective sample size is not 15.** For D (attack class) n≈8; for C/A/R the effective
  n is **4** — the number of RTUs. And 45 rows is not 45 independent observations:
  the three personas share a scenario and a context block, so the unit of analysis is
  the scenario. Treating n=45 is pseudoreplication.
- **Consequence of this for [[D29]]:** "regulator 14/15 state a wrong CIP timeline" is
  14 restatements of ONE fact, because only one reportable timeline exists in the whole
  set. Real n for that finding is closer to 1. The writeup currently overstates it.
- **The cascade gap.** Plan §1 justifies IEEE 14-bus specifically because *"cascading is
  a transmission phenomenon"* and the C score is the differentiator. But the simulator
  produces **zero overload violations and zero cascades** — every consequence file has
  `"overload": []`, and two of four say the grid absorbs the outage because
  "base-case headroom is large". The cascading-impact story currently has no instances.
- **Fix is diversity, not count.** More near-duplicate scenarios add rows without adding
  information. Vary the *simulation*: (a) open SUBSETS of an RTU's breakers (a realistic
  partial compromise) instead of all of them, which yields many distinct outcomes per
  device; (b) scale base load (1.2x, 1.5x) so outages actually violate thermal limits —
  this is what produces the overload and cascade cases §1 promised; (c) add the
  CIP-008-6 **"attempt"** case (end of next calendar day) already documented in
  `knowledge_base/regulatory_compliance/compliance.md` but never instantiated — without
  it R cannot distinguish a model that knows the nuance from one pattern-matching
  "attack -> 1 hour".
- **Target:** ~30 scenarios, stratified so consequence varies INDEPENDENTLY of device.
  30 is where a paired Wilcoxon has adequate power for a medium effect while the judge
  batch stays at 810 requests per model config. Diversity is the binding constraint,
  not n: 30 well-stratified scenarios beat 60 near-duplicates.

### D36. The overload branch of the consequence simulator is DEAD CODE
- **Found (2026-08-19), root cause of [[D35]]:** `pn.case14()` ships placeholder thermal
  ratings — `max_i_ka = 42.3` on every line (a real 132 kV line is ~0.5-1 kA) and
  `sn_mva = 9900` on the transformers. MATPOWER's case14 sets `rateA = 0` ("unlimited")
  and pandapower converts that to an effectively infinite limit.
- **Measured:** at **2x load with no outage at all, max line loading is 3.7%**. The
  thresholds in `simulate_consequences.py` are `LOAD_ALARM = 90` / `LOAD_VIOL = 100`.
  The overload branch of `violations()` and `_describe()` has never executed and cannot.
- **Why this matters more than the scenario count:** plan §1 justifies choosing IEEE
  14-bus over the 13-node feeder *specifically* because "cascading is a transmission
  phenomenon" involving thermal overload. Thermal overload is currently unrepresentable.
  The cascading-impact story the grid choice rests on has no mechanism, not merely no
  instances. Load-scaling alone does NOT fix it — the network collapses into
  non-convergence (islanding) before any branch reaches a limit that does not exist.
- **Fix (IMPLEMENTED 2026-08-19):** rate lines on the standard **N-1 planning
  criterion** rather than an arbitrary N-0 target — `max_i_ka` = the worst current a
  line carries across every single-branch outage, x `N1_MARGIN`. The system is N-1
  secure *by construction* (any one breaker may open with no thermal violation) while
  N-2 and deeper bite. A citable criterion beats a tuned constant: an arbitrary "N-0 at
  15%" invites "why 15?", whereas N-1 security is what planners actually design to.
- **Calibration (`N1_MARGIN = 1.25`, giving N-0 at ~60% of rating, realistic for
  transmission).** Over 76 breaker subsets x 4 load levels (304 flows, solved once and
  re-classified per margin — ratings change the verdict, never the flow):

  | margin | ABSORBED | OVERLOAD | OVER+VOLT | ISLAND | N-0 max |
  |---|---|---|---|---|---|
  | 1.00 | 39 | 202 | 35 | 28 | 75% |
  | **1.25** | **107** | **134** | **35** | **28** | **60%** |
  | 1.40 | 138 | 103 | 35 | 28 | 53% |

  1.25 gives every class >= 28 instances — enough to stratify ~30 scenarios — without
  the overload-domination of tighter margins. Pure voltage-only violations do not occur
  under N-1 ratings on this network: when voltage collapses, branches are already
  overloaded. That is physical, not a gap in the sampling.
- **`selfcheck()` now asserts the property, not just the baseline:** (1) N-0 clean,
  (2) no single breaker violates a thermal limit (the criterion the ratings encode),
  (3) the overload path is REACHABLE — this third check is what would have caught the
  original dead-code bug, and prevents silently regressing to unlimited ratings.
- **Immediate evidence the bug was real:** RTU-2's full outage previously reported
  "no physical violation". Under real ratings the same outage overloads **three lines
  (up to 120%)**. The overloads were always physically present; the simulator could not
  see them. Two of the four device-level consequences were wrong, not merely coarse.
- **Transformer trap:** do NOT rate transformers by scaling `sn_mva`. In pandapower
  `sn_mva` participates in the impedance model (`vk_percent` is relative to it), so
  changing it alters the power flow itself, not just the limit. Verified: it breaks
  convergence on the base case. Rate lines only, or carry a separate trafo rating field.
- **Scenario space this unlocks:** 76 breaker subsets x 4 load levels = **304 candidate
  scenarios** spanning 5 consequence classes, versus the current 4 consequences fully
  determined by device identity. `simulate()` already accepts an arbitrary breaker list
  and `--breaker` already runs single-breaker cases — the physics engine needs no change,
  only the enumeration in `--all` and a ratings step.
- **Division of labour (was unclear, now recorded):** `simulate_consequences.py` is the
  physics ORACLE (breakers -> consequence); `make_fact_sheets.py` is the scenario
  GENERATOR (pairs a real attack flow + SHAP with an authored target, reading the
  oracle's output). The diversity bottleneck is the oracle writing exactly one file per
  device, not the generator.

### D37. Scenario set rebuilt: 30 stratified scenarios, consequence decoupled from device
- **Done (2026-08-19), implementing plan §4.0 / [[D35]] / [[D36]].** Two-step pipeline,
  both deterministic and LLM-free:
  `simulate_consequences.py --library` enumerates every breaker SUBSET x 4 load levels
  -> `consequence_library.json` (304 entries, **126 distinct consequence texts**), then
  `make_fact_sheets.py` stratifies 30 scenarios across consequence CLASS.
- **Result vs the old set:**

  | | before | after |
  |---|---|---|
  | scenarios | 15 | 30 |
  | distinct consequences | 4 | **18** |
  | distinct reportable classes | 2 | **3** |
  | consequence classes | voltage / none | OVERLOAD / OVER+VOLT / ISLAND / ABSORBED |
  | consequence determined by device? | **yes** | **no** |

- **Strata:** OVERLOAD 9, OVER+VOLT 6, ISLAND 4, ABSORBED 6, fp_noise 5. ABSORBED is
  deliberately smaller — "the grid absorbs it" has exactly ONE consequence text however
  many breakers open, so extra ABSORBED rows add no discriminative power on C.
- **The CIP-008-6 ATTEMPT case now exists** (N_ATTEMPT=3): reconnaissance is reportable
  by end of next calendar day, not the 1-hour clock. Freely cycling attack classes gave
  exactly **one** attempt scenario — the same n=1 trap D35 identifies in the old set,
  where "14/15 regulator failures" were 14 restatements of a single fact. A dimension
  with one instance cannot be measured, so the count is now pinned.
- **Coherence rule:** an ATTEMPT may only pair with ABSORBED. A port scan probes; it does
  not open breakers. Pairing reconnaissance with an overload would make the gold facts
  self-contradictory — C asserting a physical violation that R simultaneously calls a mere
  attempt. Asserted in `tests/test_scenarios.py`.
- **Two bugs found and fixed while building this, both worth remembering:**
  1. The first picker pre-filtered for unique consequence text, which starved every device
     but the first in classes that legitimately share one text — collapsing ISLAND and
     ABSORBED onto RTU-1 and silently *reinstating* the device/consequence coupling the
     rebuild exists to remove. Round-robin over devices FIRST, prefer fresh text second.
  2. The first version of `tests/test_scenarios.py` keyed devices on `device[:40]`. Every
     device sentence begins with the same 40-char prefix, so all four collapsed into one
     bucket and the anti-coupling assertions passed **vacuously**. Key on `dst_ip`.
     A test that cannot fail is worse than no test.
- **Consequence for prior results:** `experiments/results/*.txt` and both
  `cpas_scores*.json` were produced against the OLD 15 scenarios and are now stale — the
  baseline in `docs/notes/phase4_baseline_cpas.md` must be quoted as the 15-scenario,
  pre-D36 result and cannot be pooled with anything generated from here on. Note also
  that under unlimited ratings RTU-2's outage was graded as "no physical violation" when
  it in fact overloaded three lines, so some tier-C narratives were scored against
  incorrect ground truth.

### D38. Evaluation harness hardened before the sweep: run namespacing, staleness guard, statistics
- **Reviewed `tiers.py` / `report.py` / `judge.py` before generating narratives for the
  30-scenario set. Six problems, two of which would have silently corrupted results.**
- **(1) No model dimension in output paths — blocks §7.7 entirely.** Every run wrote to
  `experiments/results/scenario_XX_<tier>_<persona>.txt` and a single `cpas_scores.json`.
  The capability sweep runs N synthesizers; each would have silently overwritten the
  previous one's narratives and scores. N models, 1 set of files. Fixed: `run_tag()` in
  `synthesize.py` derives a filesystem-safe id from backend+model
  (e.g. `ollama-llama3.1-8b`), and all artifacts live in `experiments/results/<run_tag>/`.
- **(2) Stale narratives would be judged against the wrong incident — silent and
  confident.** Scenario ids are POSITIONAL: after the D37 rebuild, `scenario_01` is
  RTU-1/mitmattack/OVERLOAD, but the narrative on disk still described RTU-3 from the old
  set. `build_requests()` would have paired it with the new gold facts and scored it as a
  hallucination — with no error, no warning, and a full-looking table. Fixed: `tiers.py`
  writes a manifest of per-scenario gold-fact fingerprints; `report.py` refuses to run on
  any mismatch.
- **(3) Missing narratives were silently dropped.** `if not fp.exists(): continue` meant
  scenarios 16-30 (which had no narratives yet) would vanish from the run and the table
  would still print, looking complete. Now a hard failure listing what is missing.
  *A partial result that looks whole is worse than a crash.*
- **(4) No resume.** 30 scenarios x 3 personas = 90 local generations; a crash at 85 lost
  everything. `tiers.py` now resumes by default (skipping scenarios whose fingerprint is
  unchanged and whose tier-C files are non-empty), checkpoints the manifest each loop,
  and takes `--fresh` to force regeneration. It also deletes narratives for scenarios
  that no longer exist.
- **(5) Vendor independence was documented, not enforced.** OpenRouter puts
  `anthropic/claude-*` one string away from the synthesis slot, which would have the
  judge grading its own family. `assert_independent_of()` now fails the run.
- **(6) Means without a test.** Added `THRESHOLD = 3.0` pass rate (the deferred half of
  [[D31]] — far less λ-sensitive than a mean) and a **paired Wilcoxon signed-rank test,
  paired by SCENARIO with personas averaged within**. The three personas share a scenario
  and a context block, so 90 rows are not 90 independent observations; pairing on the
  scenario is what avoids pseudoreplication. `tests/test_report.py` asserts the test
  reports n=30 pairs rather than n=90, and declines to emit a p-value when underpowered.
  Also added a mean-CPAS-by-consequence-class table, answerable only since [[D37]]:
  does context help more where the physics is harder?
- **Two bugs in the fix itself, caught only by testing the harness end to end** (with
  the model call stubbed, so no Ollama or API needed):
  1. The stale-narrative cleanup parsed filenames back into fields via
     `name.rsplit("_", 2)[0]`. The persona `data_scientist` contains the same `_`
     separator, so `scenario_01_A_data_scientist.txt` resolved to scenario id
     `scenario_01_A`, which is never in the live set — **every run silently deleted all
     90 data_scientist narratives** (270 files written, 180 surviving).
  2. That deletion then defeated resume: the missing tier-C files failed the
     `all(f.exists())` check, so every rerun regenerated all 30 scenarios while
     reporting "0 resumed".
  Fix: compare against the set of filenames we EXPECT to exist, never parse a filename
  back into fields. Lesson worth keeping — a delimiter that also occurs inside a field
  is not a delimiter. `tests/test_harness.py` pins both behaviours.
- **Legacy results archived** to `experiments/results/_legacy_15scenario_preD36/` with a
  README stating why they cannot be pooled — rather than deleted, since they are the
  published baseline, and rather than left in place, where the filenames collide
  conceptually with the new set.

### D39. Rubric corrected before committing to the new baseline
- **Context:** the 15-scenario baseline is abandoned ([[D35]]/[[D37]]), so the rubric can
  be corrected without breaking a live pre-registration. Audited it against the new
  30-scenario set BEFORE generating anything. Four faults, full text in
  `cpas_protocol.md` (Amendment 2026-08-21).
- **The serious one — D rewarded lucky guessing over honest uncertainty.** The anchor
  required the "correct attack class" for D=5, while the H rule states (correctly) that
  the class is an inference a BINARY detector never conveys. So a narrative confidently
  asserting "DoS" and happening to be right outscored one saying "the features indicate
  flooding; the detector cannot identify the specific class" — the better explanation,
  and the one the persona prompts explicitly demand ("never guess"). **The rubric was
  penalising the behaviour the system prompts require.** D now measures GROUNDING: a
  correct hedge scores as well as a correct name; only false confidence is punished.
- **C was undefined for 17% of the set.** The 5 fp_noise scenarios carry
  `physical_consequence = "not simulated"` and the anchor offered no way to score them,
  yet the judge must still emit 1-5. Now anchored: 5 = correctly states no physical
  impact is established, 1 = invents one — which is precisely the failure the FP class
  exists to detect.
- **R and A were role-generic.** Both are role-dependent, so one anchor measured a
  different construct per persona while pooling all three on one scale — "reporting duty
  where relevant" is all of R for the regulator and never relevant for the data
  scientist. Likely part of why regulator scores behaved so differently in the old run.
  The judge also received only the persona's NAME, so **the grader held a weaker
  definition of the target than the generator did**; it now gets each persona's
  deliverable spec (`PERSONA_EXPECT`).
- **No anti-verbosity instruction.** §7.6 #1 logged answer lengths, which detects length
  bias but does not counter it, across a 77-char vs ~1000-char gap. The judge is now told
  explicitly that a short correct answer must outscore a padded one.
- **`top_features` was an unscoped gold fact.** Traced it: `ev.top_features` (the SHAP
  attributions) is load-bearing — it IS tier B, and `event_to_query` embeds it so it
  drives retrieval. But `gold_facts["top_features"]` has **no reader anywhere in the
  code**; its only consumer is the judge, which sees it inside the blob labelled GOLD
  FACTS. Unqualified, that implies every narrative should contain it — so the judge could
  reward feature recitation from the operator and regulator personas, which their own
  prompts call clutter. Same class of fault as the D anchor: the rubric rewarding what
  the persona specs forbid. Kept (not removed) because it is the only way to catch a
  feature hallucination — a live failure mode for the data-scientist persona — but now
  explicitly scoped: wrong features = a false claim about the model (contradicted claim,
  reflected in D; H stays 0, since a feature name is not one of the grounded facts H
  covers); credit for the data scientist only; recitation earns nothing elsewhere and
  omission is not a fault.
- **Weights, λ and the formula are UNCHANGED** — these amendments change what the anchors
  mean, not how they combine. `tests/test_cpas.py` still asserts the arithmetic.
- **Added `attack_class_correct` as a DIAGNOSTIC** (never in CPAS): does the narrative
  name the gold class? Reported per tier x persona. Quantifies [[D27]] — if it stays low
  for tier C under a frontier synthesizer, the lever is a multiclass detector, not a
  bigger model. That distinction is a thesis claim currently supported only anecdotally.

### D40. Tier C had LESS evidence than tier B — the ablation was not monotonic
- **Found by reading the first generated narratives before spending the judge batch**
  (2026-08-21). The tier-C data-scientist narrative for scenario_01 claimed
  `"Total Bwd packets" with a SHAP contribution of 0.35` and `"SYN/RST Flag Count" ... 0.25`.
  Neither feature nor either value exists: the real top driver is `Bwd IAT Min` at `+0.068`.
- **Root cause:** `event_to_query()` embeds the SHAP features into the RETRIEVAL QUERY, but
  `retrieve_context()` returned only `device + rag_block` — the retrieved KB prose, never
  the query. **The synthesizer was never told which features drove the prediction.** The
  data-scientist persona is explicitly asked "which flow features drove the prediction and
  what they mean", so it had no option but to invent them.
- **Why this was about to produce a FALSE FINDING:** tier B *is* the raw SHAP list, so tier B
  carried evidence tier C lacked. C was a SUBSET of B, not a superset. The batch would
  plausibly have reported "context makes the data scientist WORSE" — a plumbing artifact
  presented as a result, and one that would have survived into the thesis because it is
  directionally plausible (verbosity, persona collapse) and nobody re-reads 270 narratives.
- **Fix:** `evidence_block(ev)` in `retrieve.py` is now the single formatter for the network
  evidence, used BOTH by `tier_b()` and by the tier-C context block, so **A subset B subset C
  holds by construction rather than by care**. Ordering in the context block is device join →
  evidence → retrieved prose, and the `max_chars` cap applies to the retrieved TAIL only, so
  neither the device chain nor the SHAP evidence can be trimmed. Tier A and tier B output is
  byte-identical to before; only tier C changes.
- **`tests/test_harness.py::test_tier_monotonicity`** asserts B startswith A, C-context
  contains B verbatim, and every top feature appears in the evidence.
- **Cost:** all 90 tier-C narratives regenerated (`--fresh`); tiers A and B unaffected.
- **Pattern, now four deep.** [[D39]] fixed three cases of the RUBRIC demanding what the
  system cannot produce; this is the same fault one layer down — the SYSTEM being asked for
  what it was never given. Worth a methodology note: every persona instruction should be
  traced to the input that makes it satisfiable. The data-scientist prompt asked for
  features; nothing supplied them.
- **Process note:** this was caught by reading three narratives for ~60 seconds, not by any
  test or metric. Sanity-read real outputs before committing to a batch.

### D41. D29 was WRONG: the CIP rule never reached the model — `max_chars` truncation
- **Measured 2026-08-21, 0 API cost.** For all 30 scenarios, the retrieved context block
  handed to the synthesizer contains the CIP reporting timeline **0/30 times**. Meanwhile
  27/30 regulator narratives assert "24 hours" — a figure that appears **nowhere in the KB**
  (checked: no 24/72h decoy exists). The model was not choosing between a retrieved fact and
  its prior; it had only its prior.
- **Root cause — one line.** Retrieval WORKS: the untruncated block is **28,672 chars** and
  contains `1 hour`, `one hour`, `CIP-008`, `E-ISAC`, and `next calendar day`. But
  `retrieve_context` ends with `rag_block[:max_chars]` at `max_chars = 9000`, discarding
  **68% of what was retrieved** — and the compliance content sits in the discarded tail.
  Blind head-truncation keeps whatever happens to rank first, with no regard for what the
  persona needs.
- **This overturns [[D29]].** D29 concluded "the 8B is ignoring context for its training
  prior" and made that the headline reliability finding, reasoning that the timeline "is in
  the KB". *In the KB* is not *in the context block* — retrieval, then truncation, sit
  between them. The correct statement is: **the fact never reached the model.** D29's
  conclusion must be withdrawn, not merely qualified. It also means the §7.7 capability
  sweep would have measured the wrong thing for the regulator persona: no synthesizer
  upgrade can use a fact that was truncated away.
- **The cap is a real tradeoff, not simple carelessness.** It is documented as preventing
  8B persona-collapse. A controlled n=1 probe (same scenario, same persona, cap 9k vs 30k):
  at 9k the rule is absent and no timeline is stated; at 30k the rule is present and the
  model states "within one hour" correctly, twice. Persona collapse did NOT occur at 30k
  (no switching instructions in the regulator brief) and length barely moved (151 -> 169
  words) — **but the device was misidentified as 10.0.0.2 instead of 10.0.0.1**, despite
  `resolve_device` being the first thing in the block. So the cost of a longer block is
  grounding drift (lost-in-the-middle), not persona bleed.
- **Do NOT pick a cap from n=1.** Required next: sweep `max_chars` over {9k, 15k, 20k, 30k}
  x 3 personas x ~5 scenarios (~60 local generations, ~15 min, no API cost) measuring two
  things per cell — (a) does the fact that persona needs appear in the OUTPUT, (b) does the
  device/bus stay correct. Pick the cap on that evidence, or adopt persona-conditioned
  retrieval (plan §11.1, currently listed as future work), which targets this directly:
  each persona retrieves what it needs inside a small budget, avoiding both truncation loss
  and dilution. Note §11.1 costs the "retrieve once, reuse 3x" efficiency claim — that
  tradeoff should be stated, not hidden.
- **Everything downstream of this is provisional.** The 30-scenario tier-C narratives just
  generated were produced at `max_chars = 9000` and therefore under-inform the regulator
  persona systematically. Do not spend the judge batch until the cap is settled.
- **Method note:** this was found by a free 30-scenario retrieval grep, after a 60-second
  read of three narratives raised the question. Both checks cost nothing and each overturned
  a conclusion that had already been written into the log.

### D42. No `max_chars` value works — the "retrieve once, reuse 3x" design is the cause
- **Swept `max_chars` over {9k, 15k, 20k, 30k} x 3 personas x 5 scenarios (60 local
  generations, no API cost).** There is no good value:

  | cap | operator | data_scientist | regulator | both fact+device |
  |---|---|---|---|---|
  | 9,000 | 80% fact / 100% dev | 100% / 0% | **20%** / 100% | 33% |
  | 15,000 | 0% / 0% | 0% / 0% | 0% / 0% | 0% |
  | 20,000 | 0% / 0% | 0% / 0% | 0% / 0% | 0% |
  | 30,000 | 0% / 0% | 0% / 0% | 60% / 0% | 0% |

- **At 30k the model collapses completely.** Output is **byte-identical (same SHA256)
  across 2 different scenarios x 3 different personas** — a generic "Regulator Briefing"
  about `10.0.0.2` (SCADA-1, not the incident's device), ignoring persona, ignoring the
  incident, and summarising the KB in direct violation of the prompt's "Do not summarize
  the knowledge base; analyze THIS incident". The incident-specific header is ~500 chars
  against ~29k of shared KB text — 1.7% signal. So the cap's original justification
  (8B persona-collapse) is REAL and more severe than documented.
- **Exact mechanism (measured).** The retrieved block is ordered
  `[header][Entities 15%][Relations][Document Chunks 27%..100%]`, total 28,672 chars.
  `max_chars = 9000` keeps the first **31%** — the entity/relation preamble plus ~1,300
  chars of actual KB prose. **The CIP rule sits at char 26,531, i.e. 93% through**, because
  the compliance chunk ranked LAST of the 7 chunks returned. Two failures compound: the
  shared query deprioritises compliance, then the cap discards everything past rank ~1.
- **Root cause is the design, not the constant.** `event_to_query` builds ONE
  persona-agnostic query (device / attack / consequence / "required response" — it never
  mentions reporting or regulation), and its block is reused for all three personas. One
  ranking cannot serve three different information needs: the operator needs playbooks, the
  data scientist the feature dictionary, the regulator the compliance doc. Averaged
  relevance serves none of them.
- **Decision: adopt persona-conditioned retrieval (plan §11.1), promoted from future work
  to required.** Three persona-specific queries against the SAME graph, each returning a
  small block containing what that role needs — avoiding both truncation loss and the
  dilution collapse.
- **Cost, stated not hidden:** this forfeits the proposal's "retrieve ONCE, reuse for three
  personas" efficiency claim (3 retrievals per alert instead of 1). That claim was only ever
  valid if one block adequately served all three personas, which this measurement shows it
  does not. Report the efficiency delta honestly rather than dropping the claim silently.
- **Correction to my own analysis:** I initially claimed retrieval "returns ~the whole
  corpus", based on 97-99% word-set overlap between two scenarios' blocks. That metric was
  crude (small shared vocabulary). Chunk-level, a query returns **7 of 16 chunks (44%)** —
  retrieval IS selecting. The block merely exceeds the KB's own size (28.7k vs 27.2k)
  because entity and relation descriptions are prepended to the chunks.

### D43. §11.1 implemented: persona-conditioned retrieval fixes the 0/30 failure
- **Implemented 2026-08-22 (plan §11.1, promoted from future work by [[D42]]).** Each
  persona issues its own retrieval query against the SAME graph:
  operator -> playbook / breakers / manual control / physical risk; data scientist -> what
  the flow features mean and what they can and cannot prove; regulator -> CIP-008-6
  reportability, the one-hour vs next-calendar-day clock, E-ISAC/NCCIC, CSF function.
  `retrieve_context(rag, ev, persona)` + `retrieve_all()`; `event_to_query(ev, persona=None)`
  still reproduces the pre-§11.1 shared query so the D42 comparison stays reproducible.
- **Result — the D41 failure is fixed:**

  | | before (shared query) | after (§11.1) |
  |---|---|---|
  | regulator block contains the CIP timeline | **0/30** | **30/30** |
  | operator block contains playbook/breakers | — | 30/30 |
  | data-scientist block contains feature-dict | — | 30/30 |

- **The blocks are genuinely different, not merely reordered.** Pairwise similarity:
  operator vs regulator **9%**, data-scientist vs regulator **12%**, operator vs
  data-scientist 56-68% (both need technical/operational material — sensible). Only the
  regulator block carries the CIP timeline.
- **Why it works, and it is not what I assumed.** The `max_chars` cap still binds on
  **90/90** blocks — even `top_k=3` returns 10,680 chars, because the entity/relation
  preamble is a fixed ~7.7k, so no `top_k` gets a block under 9,000. The fix therefore
  did NOT come from making blocks small. It came from changing what RANKS FIRST: the
  timeline survives inside the **entity/relation descriptions** the graph extracted, and
  the persona query changes which entities are pulled. The cap now trims the tail of a
  correctly-ranked list instead of deleting the one chunk the regulator needed.
- **`top_k` 12 -> 8.** With targeted queries, fewer well-ranked chunks beat more diluted
  ones. `max_chars` stays 9,000 — the only value measured not to collapse the 8B (D42) —
  but is now a safety rail rather than the de facto content selector.
- **Cost, stated openly:** three retrievals per alert instead of one. The proposal's
  "retrieve ONCE, reuse for three personas" efficiency claim is **forfeited**, and should
  be reported as such rather than quietly dropped — it was only ever valid if one block
  adequately served all three personas, which D42 showed it did not. The efficiency delta
  (1 vs 3 retrievals) is worth measuring and stating.
- **`tests/test_harness.py::test_persona_queries`** pins that every persona has a distinct
  intent, that the queries differ, that the regulator query actually asks for the fact that
  was missing 30/30, and that incident evidence stays in every query.

### D44. §11.1 validated end-to-end — and a new failure mode: the model never declines to report
- **Row 0 regenerated under §11.1 (30 scenarios, local 8B). Regulator clock accuracy:**

  | gold class | n | correct | asserted 24/72h |
  |---|---|---|---|
  | INCIDENT (1 hour) | 22 | **21 (95%)** | 0 |
  | ATTEMPT (next calendar day) | 3 | **2 (67%)** | 0 |
  | NOT reportable | 5 | **0 (0%)** | 0 |
  | **TOTAL** | 30 | **23 (77%)** | **0** |

  Before §11.1: rule present in context **0/30**, narratives asserting "24 hours" **27/30**,
  correct clock **0/30**. The "24 hours" hallucination — a figure absent from the KB — is now
  **entirely gone**, and the ATTEMPT stratum (the discriminating case, requiring the model to
  distinguish an attempted from an actual compromise) went 0/3 -> 2/3.
- **This settles [[D29]] vs [[D41]] empirically.** D29 claimed the 8B ignores retrieved
  context in favour of its training prior. False: given the rule, it uses it 77% of the time
  and abandons the prior completely. The failure was retrieval delivery, exactly as D41
  concluded. **A capability sweep run before this fix would have attributed a retrieval bug
  to model capability across all six rows.**
- **NEW FINDING — over-reporting bias.** On the 5 NOT-reportable scenarios the model
  **never once declines to report**. Reading them individually: scenario_26 asserts
  reportable (defensible — its evidence says `prediction: attack, confidence 0.59`);
  scenario_27 escalates but *downgrades the clock* ("since this is an attempted compromise,
  notification by end of the next calendar day"), showing it partially used the confidence
  signal; scenarios 28/29/30 assert "plausibly meets the threshold" while their evidence
  reads `prediction: normal, confidence 0.14-0.19`. So it ignores its own confidence input
  and escalates. For a compliance persona this is the alarm-fatigue failure — crying wolf to
  E-ISAC — and it is exactly what the FP stratum was built to catch. It will surface in CPAS
  as low C (inventing an impact on a false positive) and low R.
- **Scenario-design caveat, must be stated in the write-up.** The `fp_noise` stratum is
  mislabelled: 4 of its 5 scenarios carry `prediction: normal` at confidence 0.14-0.19 —
  they are correctly-classified NEGATIVES that merely ranked highest among normals, not
  false positives. (The constrained model never produces a confident false positive on this
  testbed; see [[D24]].) The stratum therefore tests "does the model over-escalate on a
  low-confidence normal?", which is a legitimate and arguably more useful question — but it
  is NOT "does the model recognise a false positive", and must not be described as such.
- **Correction to my own scoring:** the first pass reported NOT-reportable as 0/5 via a
  strict "not reportable" regex. Manual reading confirms 0/5 is right, but the regex would
  equally have scored a correct-but-differently-phrased answer as wrong. Class-level numbers
  on small strata need eyeballing before they are quoted.

### D45. RESOLVED by [[D46]] — gold `reportable` encoded knowledge the narrative cannot have
- **Surfaced 2026-08-22 by the ceiling run (gpt-5.5), at scenario 3 of 30.** Our gold assigns
  **INCIDENT -> one hour** to all 22 true-positive scenarios, on the scenario designer's
  omniscient view that a compromise occurred. But the narrative only ever sees an **IDS flow
  classification**; it is never given the physical consequence (not in the KB, not in
  `AnomalyEvent`). From the evidence available to it, compromise/disruption is not
  established — so CIP-008-6's **attempted compromise -> end of next calendar day** is the
  defensible determination.
- **What gpt-5.5 wrote** (scored WRONG by `check_regulator_clocks.py`, and almost certainly
  more correct than the gold): *"The detector does not establish protocol contents,
  compromise, disruption, or a specific attack class... this plausibly meets the attempted
  compromise reporting threshold; actual compromise or disruption is not in context.
  Timeline: by the end of the next calendar day... If later determined to be a compromise or
  disruption, the one-hour initial notification timeline applies."* It also cited E-ISAC and
  NCCIC/CISA and opened with the scope-honesty caveat from our own `compliance.md`. That is
  precisely the plan §2.8 evidence-trap discipline the persona prompts demand.
- **Why this is urgent: it INVERTS the result.** Row 0's 8B asserts "within one hour" and
  scores correct; the frontier model reasons from the evidence and scores wrong. Judged
  as-is, **the ceiling would appear WORSE than the local 8B on the R dimension** — a purely
  artefactual finding, and one that would look plausible enough to survive into the thesis.
- **Fifth instance of one pattern.** [[D39]] fixed three cases of the RUBRIC demanding what
  the system cannot produce; [[D40]] fixed the SYSTEM being asked for what it was never
  given; this is the GOLD FACTS encoding knowledge the narrative has no access to. The
  general lesson for the methodology chapter: *every graded expectation must be traceable to
  an input the narrative actually receives.*
- **Options (needs a domain decision, not an engineering one):**
  1. Revise gold: INCIDENT scenarios become "attempt / next calendar day unless compromise is
     established". Most faithful to the evidence trap; requires re-deriving `reportable` in
     `make_fact_sheets.py`.
  2. Give the narrative the simulated consequence, so disruption IS established and one hour
     is genuinely correct. Larger change, but would also fix the C dimension being
     near-unreachable (predicted ~2.5 ceiling).
  3. Accept either clock in the rubric when the conditional reasoning is correct. Cheapest;
     weakens R's discriminating power.
- **STATUS: RESOLVED 2026-08-22 via option 1 — see [[D46]].** (was: do not submit a judge batch) — every R and H score
  for all 22 INCIDENT scenarios depends on it. The ceiling narratives themselves remain valid
  under any option; only the scoring changes.

### D46. Gold `reportable` revised: detection establishes an ATTEMPT, not a compromise
- **Decision (option 1 of [[D45]]), 2026-08-22.** The gold no longer assigns the one-hour
  clock to any scenario. A bare IDS flow classification does not establish compromise or
  disruption, so the evidentially-supported duty is **attempt -> end of next calendar day**,
  with the one-hour clock stated as the CONDITIONAL it is in the standard.
- **Grounded in the source text, not in a judgement call.** CIP-008-6 R4 Part 4.2, verified
  against the PDF in `references/`: *"One hour after the **determination** of a Reportable
  Cyber Security Incident"* / *"By the end of the next calendar day after **determination**
  that a Cyber Security Incident was an attempt to compromise..."*. The clock runs from a
  determination the entity makes; the narrative is given no basis to determine compromise.
  The old gold asserted a determination on the model's behalf.
- **New gold distribution:** attempt-by-evidence 22, attempt-recon 3, not-reportable 5.
  Recon (port scan) remains a distinct attempt on its own merits, not merely for want of
  evidence.
- **Effect — the ranking inverts, which is the point:**

  | | old gold | revised gold |
  |---|---|---|
  | row 0, local `llama3.1:8b` | 23/30 (77%) | **2/30 (7%)** |
  | ceiling, `openai/gpt-5.5` | 13/30 (43%) | **20/30 (67%)** |

  Under the old gold a model that asserted the retrieved 1-hour figure outscored one that
  reasoned about what the evidence supports. The 8B still essentially cannot do this (2/30);
  gpt-5.5 reaches 67%, and 3/3 on recon, 4/5 on declining to report a low-confidence normal.
- **`fingerprint()` narrowed to `anomaly_event` only.** It previously hashed `gold_facts`
  too, so revising the answer key invalidated 540 valid narratives and demanded ~2 hours of
  regeneration that would have produced byte-identical output. The synthesizer never sees
  gold facts; what must trigger regeneration is a change to what the model was GIVEN, not to
  what it is graded against. A gold change still forces a re-judge — one batch, not two runs.
- **Migration verified before applying:** tier B is generated verbatim from `anomaly_event`,
  and matched the current scenarios **30/30 in both runs**, proving the inputs were unchanged
  and only the hash scheme differed. Manifests were then rewritten in place; `report.py` now
  accepts both runs (810 requests each). No narrative was regenerated.
- **Sixth and final instance of the pattern** ([[D39]] rubric x3, [[D40]] system input,
  [[D45]] gold facts). Methodology-chapter lesson, stated once: *every graded expectation
  must be traceable to an input the narrative actually receives.*

### D47. CIP asset classification added — R was unanswerable without it
- **Found by the $0.07 judge smoke test (2026-08-22), before the $23 batch.** Grading one
  gpt-5.5 tier-C regulator narrative returned D4 C1 A2 R3 **H1** (CPAS 0.55). The H reason:
  the narrative "asserts reportability is not established" against a gold that says it IS
  reportable as an attempt.
- **The narrative was right.** It wrote: *"The context does not state that RTU-1 is a BES
  Cyber System, EACMS/PACS, or that compromise/disruption occurred. Therefore, reportability
  is not established on the provided facts."* Verified: the regulator's retrieved block
  contains `BES Cyber System` (from the CIP-008 *definition*) but **never states that RTU-1
  is one**. The KB asserts that link exactly once, in a passing instructional sentence in
  `compliance.md` ("an attack on an RTU (a BES Cyber Asset)"), and it did not survive into
  the block.
- **The model was obeying its own system prompt** — `configs/personas/*.md` say "Use ONLY
  facts in the provided context. If something is not in the context, say 'not in context' —
  never guess." It followed the instruction and was penalised for it. Same shape as the D39
  D-anchor fault: the grading rewarded what the prompt forbids.
- **Why this is not "planting the answer".** CIP-008-6 only triggers for a BES Cyber System
  or an associated EACMS/PACS, so asset scope is a PRECONDITION of the reportability
  question, not its answer. The model must still decide attempt vs compromise and apply the
  clock. Without it, R is unanswerable by any instruction-following model — which means R was
  measuring KB completeness, not capability.
- **Fix:** `cip_class` added to every device in `entities.yaml`, emitted by
  `resolve_device()` — the deterministic join that always sits at the top of every context
  block, so no graph rebuild and no retrieval dependency. RTUs and SCADA-1 = BES Cyber Asset;
  ENG-WS-1 = EACMS (it controls electronic access to BES Cyber Systems).
- **Declared as AUTHORED, not cited.** `ip_device_map.md` now states these classifications
  are part of the synthetic overlay, plausible for a testbed but not a jurisdictional
  determination — a real entity performs its own CIP-002 categorisation. Per plan §2.9, a CIP
  determination must not be presented as sourced when it came from authoring judgement.
- **Seventh instance of the pattern** ([[D39]] x3 rubric, [[D40]] system input, [[D45]]/[[D46]]
  gold facts, this one KB completeness). Every instance was caught by a free check before a
  paid one. The smoke test's entire purpose was validating the schema; it found a
  seventh-order design defect instead, for seven cents.
- **Cost:** both rows regenerated (row 0 local ~50 min free; ceiling ~15 min, ~$2). Scenarios
  regenerated first so the gold's device string carries the classification too.

### D48. Judge sensitivity: ordering robust, effect SIZE is not
- **Three grading configurations** (2026-08-23): primary `claude-opus-5` on all 4,860
  calls; `gemini-3.1-pro-preview` on a blind 20-item sample; and a **clean panel** where
  every item is scored by a second judge that did NOT author it (`gpt-5.4` on the 11
  llama-authored items, Gemini on the 9 gpt-5.5-authored ones).
- **The tier ordering survives all three.** Clean panel: A 1.85 < B 2.26 < C 2.80.
  Gemini alone: A 1.50 < B 1.59 < C 2.84. H agreement 95-100% throughout — the dimension
  carrying the λ=2 penalty is the most reproducible thing in the metric.
- **Same-family bias measured, none found.** `gpt-5.4` scored its sibling gpt-5.5's
  narratives **+2.44** vs the primary judge and other narratives **+2.55** — a difference
  of −0.10, i.e. marginally harsher on its own family. Keep the independence rule as the
  default (it costs nothing), but self-preference was not detectable here at n=20.
- **The qualifier that matters: disagreement is TIER-DEPENDENT, so it does not cancel.**
  Second judges are far more generous to the sparse tiers on the C dimension
  (A +1.00, B +1.57) but not to tier C (+0.14). The measured gap shrinks:
  **C−A = +1.30 (primary) vs +0.95 (clean panel), ~27% smaller.** Direction and
  significance are robust; the MAGNITUDE carries ~±25% grader-dependent uncertainty.
  Report the effect as "roughly 1.0-1.3 CPAS depending on grader", never as a point value.
- **Root cause is a rubric gap identified in [[D39]] and only half-fixed.** The C anchor
  reads *5 = matches / 3 = vague or partial / 1 = contradicts*, and **silence is not
  "contradicts"**. A tier-A alert says nothing about consequence: a strict judge scores 1,
  a lenient one scores 3 for "vague". D39 patched this in the *reason* text (the judge is
  asked to say whether a 1 means wrong or absent) but never in the anchors. It is now
  costed at ~0.35 of effect size. **Fix for any future run: give "absent" its own anchor,
  distinct from "contradicts", on every dimension whose floor conflates them.**
- **Method note:** the tier-dependence was only visible because the offset was checked
  PER TIER. A pooled mean Δ would have shown a small overall difference and looked like
  harmless noise. Always test whether a judge offset varies across the comparison you are
  actually making.
- **Also fixed here:** OpenRouter rate-limits new accounts (10 rpm on gpt-5.4), which
  silently truncated the first sensitivity run to n=10 with one tier-A item. The script
  now paces requests and backs off on 429 — a partial sample is worse than a slow one,
  because agreement on 10 arbitrary items is not agreement.

### D49. `MAX_OUTPUT_TOKENS` 4,000 -> 16,000: a guard rail is not a treatment
- **Trigger (2026-11-08).** Extending the §7.7 sweep with two newer open-weight models,
  `qwen/qwen3.8-27b` raised `TruncatedNarrative` on its first tier-C call. Diagnosis was
  not narrative length: a trivial 150-word prompt returned `finish_reason="length"`,
  `reasoning_tokens=4000`, and **`content` of length zero**. The model is a reasoning model
  that spent the entire budget on its reasoning trace and never emitted an answer.
- **The invariant question.** §7.7 fixes "only the model differs between rows", and
  `MAX_OUTPUT_TOKENS` is a setting. Raising it for one row only would breach that.
- **Resolution: raise it GLOBALLY, which preserves the invariant rather than breaking it.**
  The ceiling is a guard rail against runaway generation, not an experimental treatment.
  Holding it at 4,000 does *not* treat all models alike -- it gives a non-reasoning model a
  full answer budget and a reasoning model zero. Every row now shares one identical value;
  only a reasoning model consumes the headroom, and that is model behaviour, i.e. part of
  what the sweep measures.
- **No prior row needs regenerating or re-judging, and this was verified, not assumed.**
  The old ceiling was non-binding everywhere. Longest narrative per run, in words
  (~tokens at 1.33, as % of 4,000):

  | run | max words | ~tok | % of 4,000 |
  |---|---|---|---|
  | ollama-llama3.1-8b | 208 | 277 | 7% |
  | openai-meta-llama-llama-3.1-8b-instruct | 283 | 377 | 9% |
  | openai-meta-llama-llama-3.3-70b-instruct | 181 | 241 | 6% |
  | openai-openai-gpt-5.5 | 191 | 254 | 6% |
  | openai-qwen-qwen3-32b | 246 | 328 | 8% |
  | openai-qwen-qwen3-235b-a22b-2507 | 213 | 284 | 7% |
  | openai-deepseek-deepseek-v4.1-flash-1017 | 243 | 324 | 8% |

  Peak usage is 9% of the old ceiling, so raising it cannot change any prior row's output
  distribution. 16,000 chosen against observed reasoning usage of 1,192-2,218 tokens
  (~7-13x headroom); at 4,000 the same prompt consumed all 4,000.
- **Rejected alternative: `reasoning: {enabled: false}`.** It produces a clean answer inside
  the original 4,000, but it tests a *configuration* of the model rather than the model as
  shipped, and it would make this row non-comparable to the two existing Qwen rows in a way
  the token ceiling does not. Prefer giving a model room over changing what it is.
- **Reverses the reasoning in the original comment, not its intent.** The 4,000 value came
  from a 402-on-low-balance incident (65,536 reserved against a ~$0.023 call). That comment
  already warned "pinning it LOW would be worse: it would truncate reasoning models
  mid-answer" -- which is exactly what happened. Reservation rises ~4x; acceptable on
  OpenRouter pricing, and worth watching if the balance runs low again.
- **Generation cost of reasoning is wall-clock, not dollars:** qwen3.8-27b took 52 min for
  270 narratives vs 12 min for deepseek-v4.1-flash.
- **Reproducibility caveat surfaced while diagnosing.** The identical prompt to
  `qwen/qwen3.8-27b` used 4,000 reasoning tokens on one call and 1,192 on another.
  OpenRouter routes this model across ~23 providers which do not appear to configure
  reasoning identically, so part of that spread is provider routing, not the model. All
  OpenRouter rows share this exposure -- "we called model X" is really "we called whichever
  provider OpenRouter picked for X". Belongs in the limitations section.

### D50. Sweep extended to two 2026 open-weight models: the open/ceiling gap is no longer resolvable
- **Rows added (2026-11-08),** judge frozen at `claude-opus-5`, synthesizer the only change
  (see [[D49]] for the one settings change and why it preserves the §7.7 invariant):
  `deepseek/deepseek-v4.1-flash-1017` (MIT, verified at `deepseek-ai/DeepSeek-V4.1-Flash-1017`)
  and `qwen/qwen3.8-27b` (Apache-2.0, verified at `Qwen/Qwen3.8-27B`). Licences checked at
  the vendor's own HF namespace, not inferred from the OpenRouter id prefix -- an earlier
  catalogue filter had wrongly treated every `qwen/*` as open-weight, which is false for the
  proprietary `qwen3.8-max-*` line.
- **Tier-C results** (A<B<C significant at p<0.0001 in both rows; 810 judge calls each, zero errors):

  | run | CPAS_C | raw D/C/A/R | H rate | op | ds | reg |
  |---|---|---|---|---|---|---|
  | qwen3-32b | 2.86 | 3.40 | 27% | 2.60 | 3.51 | 2.48 |
  | llama-3.3-70b | 3.15 | 3.46 | 16% | 3.74 | 3.32 | 2.39 |
  | qwen3-235b-a22b | 3.29 | 3.62 | 17% | 3.42 | 3.33 | 3.11 |
  | **deepseek-v4.1-flash-1017** | **3.72** | 3.94 | 11% | 3.79 | 3.45 | 3.93 |
  | **qwen3.8-27b** | **3.76** | 3.98 | 11% | 3.77 | 3.63 | 3.87 |
  | gpt-5.5 (ceiling) | 3.95 | 4.04 | 4% | 4.13 | 3.61 | 4.11 |

- **Paired Wilcoxon, unit = scenario, personas averaged (n=30):**
  - generational, same vendor/size class (qwen3-32b -> qwen3.8-27b): **d=+0.894, p<0.0001 \*\*\***
  - 27B vs 235B, same vendor: **d=+0.471, p=0.020 \***  -- ~9x fewer params, significantly better
  - best open vs closed ceiling: **d=+0.194, p=0.063 n.s.**
  - the two new rows against each other: d=+0.036, p=0.360 n.s.
- **Claim discipline on the headline.** p=0.063 is *failure to reject* at alpha=0.05 on n=30, NOT
  demonstrated parity. [[D48]] put ~+/-25% grader-dependent uncertainty on effect magnitudes,
  which exceeds the 0.19 gap itself. Defensible wording: *"the remaining gap between the best
  open-weight model and the closed ceiling is smaller than this study can resolve."* Prior to
  these rows the gap was 0.66 and significant, so the movement is the result, not the parity.
- **Convergent evidence.** Two unrelated vendors land 0.04 apart (p=0.36). Harder to explain as
  one vendor's benchmark-chasing than either row alone would be.
- **The remaining gap is mostly hallucination, not explanation quality.** deepseek raw 3.94 vs
  ceiling 4.04 (0.10 apart) but H 11% vs 4%, which at lambda=2.0 costs 0.14. The models have
  learned to explain about as well; factual discipline is what still separates them -- exactly
  the failure mode lambda was pre-registered to price.
- **H rate is monotone with CPAS across all 7 rows** (38% -> 4%). The lambda term tracks the single
  dimension that most orders model capability on this task; a defence of a pre-registered choice.
- **CORRECTS the earlier "regulator stays flat" explanation, which blamed retrieval.** Capability
  range across models: regulator 0.99->4.11 (range **3.12**), operator 2.60->4.13 (1.53), data
  scientist 2.80->3.63 (0.83). Regulator is by far the most capability-sensitive persona -- it was
  flat because the models then under test could not do it, not because retrieval failed it. Given
  a capable model it is the STRONGEST persona. CIP-008-6 reportability reasoning over retrieved
  rules is the hardest task in the pipeline and therefore the best capability discriminator.

### D51. Capability progression reported against weight-release date, not run date
- **Why not the run date.** The natural "when did this happen" column is the run timestamp in
  each `manifest.json`, but it takes only two values -- six rows 2026-08-23, two 2026-11-09
  ([[D50]]) -- because it records when the job was executed, not when capability moved. Shown as
  a progression axis it invites the inference that two models scored higher *by being evaluated
  eleven weeks later*. It is kept in T1b as provenance (it pairs with the [[D49]] ceiling change,
  which falls between the two batches and was verified non-binding for the first six), and the
  progression claim is carried entirely by the release-date column.
- **Release dates** come from the OpenRouter catalogue `created` field, verified 2026-11-09, and
  are hard-coded in `scripts/make_presentation_tables.py` (`MODEL_META`) because they are external
  facts with no machine-readable source in the repo -- recording them in the generator rather than
  typing them into the markdown keeps the table reproducible.
- **Spearman is computed over releases, not rows.** The API and local `llama-3.1-8b` rows are the
  same weights served two ways, so counting both gives one release two votes in a rank statistic.
  De-duplicated: **rho=0.821, p=0.0234 (n=7)**; open-weight releases only **rho=0.886, p=0.0188
  (n=6)**. All eight rows would give rho=0.874, p=0.0045 -- the same conclusion, and it is reported
  alongside so the choice is visible rather than silently favourable.
- **The relation is strong but not monotone, and the exception is reported, not smoothed.**
  `llama-3.3-70b` (Dec 2024) outscores `qwen3-32b` (Apr 2025) by 0.29 at roughly twice the
  parameter count, and the closed `gpt-5.5` (Apr 2026) still leads both later-released open
  models. Release date predicts capability on this task; scale and vendor still move it. The
  figure sorts by date rather than by score so the inversion is visible, and annotates it.
- **Artefacts.** `docs/figures/fig6_release_vs_cpas.png` (+ `.pdf`), T1b in
  `docs/notes/presentation_tables.md`, both regenerated by their existing scripts. No API cost;
  no row was re-run or re-judged.

## Cross-cutting conventions established
- Raw data immutable; inputs (`data/`, `knowledge_base/`) vs regenerable outputs
  (`models/`, `rag_storage/`, `experiments/results/`) never mixed.
- Commit straight to `main` (solo repo, linear history); no branch/PR overhead.
- `python -m caie.<module>` entry points; scripts fail loudly on missing inputs.
- Every KB fact traces to one file; `check_kb.py` gate must pass before Phase 3.
