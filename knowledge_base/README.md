# Knowledge Base

Source documents that LightRAG ingests to build the domain knowledge graph.
Everything here is **synthetic**, paraphrased from open standards/textbooks — no copyrighted text.
Each subfolder = one document type from Phase 2 of the implementation plan.

| Folder | Contents | CPAS dimension it supports |
|---|---|---|
| `topology/` | IEEE 14-bus grid + IP→device mapping (the single source of truth) | D, C |
| `physics/` | Power-system physics reference (paraphrased) | C |
| `attack_taxonomy/` | Per-attack signature + physical consequence | D, C |
| `feature_dictionary/` | Flow feature → meaning → attack signature (the semantic bridge) | D |
| `playbooks/` | Role-specific operator response steps | A |
| `incident_reports/` | Synthetic past incidents | D, C |
