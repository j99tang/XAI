# XAI — Context-Aware Intrusion Response for IEC-104 Smart Grids

Post-hoc, **model- and XAI-agnostic** contextualizer that turns intrusion-detection +
SHAP output into **role-specific narratives** (Operator / Data Scientist / Regulator),
grounded in a power-grid knowledge graph. M.Eng project, ECE2500Y (Prof. Kundur's group).

## The pipeline (three layers)
1. **IDS** (`src/caie/ids`) — flow-based detector on IEC-104 traffic → prediction + confidence.
2. **XAI** (`src/caie/xai`) — SHAP attribution → an **`AnomalyEvent`** (the JSON contract in
   `src/caie/schemas`). This is the boundary that makes the system model-agnostic.
3. **Contextualizer** (`src/caie/contextualizer`) — LightRAG retrieves grid/physics context;
   one LLM at `temperature=0` produces three persona narratives.
   Evaluated by **CPAS** (`src/caie/evaluation`) with an independent LLM-as-judge.

## Repository map
| Path | What lives here | In git? |
|---|---|---|
| `docs/` | Implementation plan, proposal, design notes | yes |
| `data/` | Raw + processed IEC-104 CSVs (inputs) | no (only `data/README.md`) |
| `knowledge_base/` | Synthetic RAG source docs (topology, physics, …) | yes |
| `src/caie/` | The Python package (all pipeline code) | yes |
| `configs/`, `experiments/scenarios/` | Experiment + scenario definitions | yes |
| `notebooks/` | Exploration + legacy benchmark work | yes |
| `models/`, `rag_storage/`, `experiments/results/` | Generated artifacts | no (regenerable) |
| `references/` | External papers, dataset README | yes |

**Guiding rule:** `data/` + `knowledge_base/` are *inputs* you author; `models/`,
`rag_storage/`, `experiments/results/` are *outputs* your code regenerates. Never mix them.

## Setup
```bash
conda env create -f environment.yml
conda activate xai
pip install -e .          # makes `import caie` work everywhere (needs pyproject.toml)
```

## Status
- [x] Layer 1 IDS benchmarked (legacy, see `notebooks/`)
- [ ] Consolidated binary IDS + SHAP → `AnomalyEvent` (Phase 1)
- [ ] Knowledge base authored (Phase 2)
- [ ] LightRAG contextualizer + personas (Phase 3)
- [ ] CPAS evaluation (Phase 4)

## Demo

```bash
conda run -n xai streamlit run app.py
```

Live pipeline — the RandomForest and SHAP run on the flow you give it, and retrieval
and synthesis run on demand. Four input modes:

| mode | input | tiers A/B are |
|---|---|---|
| Pick a scenario | one of the 30 curated incidents | precomputed |
| **Paste a flow record** | 78 comma-separated feature values | **computed live** |
| **Search the capture** | any of 320k real captured flows | **computed live** |
| Resolve an alert | a tier-A alert | looked up (and shown to be ambiguous) |

The two live modes ask you to choose a target device as well as a flow. That is not a
shortcut: no attack flow in the capture targets a real RTU (D24 — attack traffic is on
the 121.x testbed subnet), so pairing real flow statistics with an authored target is
exactly what the scenario generator does.

Synthesizer switchable across the six models from the capability sweep; `llama3.1:8b`
runs fully offline.

See `docs/IMPLEMENTATION_PLAN.md` for the full phased plan,
`docs/model_map.md` for which model runs at which stage (and which stages use
no model at all), and `docs/decision_log.md` for why things are the way they are.
