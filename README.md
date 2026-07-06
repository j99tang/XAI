# XAI — Context-Aware Intrusion Response for IEC-104 Smart Grids

Post-hoc, **model- and XAI-agnostic** contextualizer that turns intrusion-detection +
SHAP output into **role-specific narratives** (Operator / Data Scientist / Regulator),
grounded in a power-grid knowledge graph. M.Eng project, ECE2500Y (Prof. Kundur's group).

## The pipeline (three layers)
1. **IDS** (`src/ccir/ids`) — flow-based detector on IEC-104 traffic → prediction + confidence.
2. **XAI** (`src/ccir/xai`) — SHAP attribution → an **`AnomalyEvent`** (the JSON contract in
   `src/ccir/schemas`). This is the boundary that makes the system model-agnostic.
3. **Contextualizer** (`src/ccir/contextualizer`) — LightRAG retrieves grid/physics context;
   one LLM at `temperature=0` produces three persona narratives.
   Evaluated by **CPAS** (`src/ccir/evaluation`) with an independent LLM-as-judge.

## Repository map
| Path | What lives here | In git? |
|---|---|---|
| `docs/` | Implementation plan, proposal, design notes | yes |
| `data/` | Raw + processed IEC-104 CSVs (inputs) | no (only `data/README.md`) |
| `knowledge_base/` | Synthetic RAG source docs (topology, physics, …) | yes |
| `src/ccir/` | The Python package (all pipeline code) | yes |
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
pip install -e .          # makes `import ccir` work everywhere (needs pyproject.toml)
```

## Status
- [x] Layer 1 IDS benchmarked (legacy, see `notebooks/`)
- [ ] Consolidated binary IDS + SHAP → `AnomalyEvent` (Phase 1)
- [ ] Knowledge base authored (Phase 2)
- [ ] LightRAG contextualizer + personas (Phase 3)
- [ ] CPAS evaluation (Phase 4)

See `docs/IMPLEMENTATION_PLAN.md` for the full phased plan.
