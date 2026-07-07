# Knowledge-Base Source Library — download checklist

These are **reference materials to paraphrase from** when authoring the `knowledge_base/`
documents. They are **NOT** the knowledge base itself — do not put these PDFs in
`knowledge_base/` and do not let LightRAG ingest them (licensing + you must control exactly what
facts are in the KB). Download them, read/paraphrase, cite in the thesis.

**Where they go:** `references/source_library/<category>/` — this folder is **git-ignored**
(large binaries, some copyrighted), so the PDFs stay on your machine and never hit GitHub. This
index file *is* committed, so the checklist travels with the repo.

Legend: 📄 = downloadable file · 🔖 = web reference (read/bookmark, no file needed).

## standards/ → feeds `regulatory_compliance/`, `playbooks/`
| # | Document | Type | Link | Save as |
|---|---|---|---|---|
| 1 | NIST SP 800-82 Rev. 3 — Guide to OT Security | 📄 | https://csrc.nist.gov/pubs/sp/800/82/r3/final | `standards/NIST.SP.800-82r3.pdf` |
| 2 | NIST SP 800-61 Rev. 3 — Incident Response (CSF 2.0 profile) | 📄 | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf | `standards/NIST.SP.800-61r3.pdf` |
| 3 | NIST CSF 2.0 (CSWP 29) | 📄 | https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf | `standards/NIST.CSWP.29-CSF2.0.pdf` |
| 4 | NERC CIP-008 — Incident Reporting & Response Planning | 📄 | https://www.nerc.com/pa/Stand/Reliability%20Standards/CIP-008-6.pdf | `standards/NERC-CIP-008-6.pdf` |

## threat_intel/ → feeds `attack_taxonomy/`, `incident_reports/`
| # | Document | Type | Link | Save as |
|---|---|---|---|---|
| 5 | MITRE ATT&CK for ICS — techniques matrix | 🔖 | https://attack.mitre.org/matrices/ics/ | (browse online; optionally export the ICS technique list to `threat_intel/attack_ics_techniques.xlsx`) |
| 6 | SANS / E-ISAC — Ukraine 2015 grid attack (Defense Use Case) | 📄 | https://media.kasperskycontenthub.com/wp-content/uploads/sites/43/2016/05/20081514/E-ISAC_SANS_Ukraine_DUC_5.pdf | `threat_intel/E-ISAC_SANS_Ukraine_DUC.pdf` |
| 7 | Dragos — CRASHOVERRIDE (Industroyer, abused IEC-101/104) | 📄 | https://www.dragos.com/resources/whitepaper/crashoverride-analyzing-the-malware-that-attacks-power-grids/ | `threat_intel/Dragos_CRASHOVERRIDE.pdf` |
| 8 | CISA alert — CrashOverride malware (corroborating) | 🔖 | https://www.cisa.gov/news-events/alerts/2017/06/12/crashoverride-malware | (web) |

## protocol/ → feeds `protocol_reference/`
| # | Document | Type | Link | Save as |
|---|---|---|---|---|
| 9 | IEC 60870-5-104 ASDU structure explained | 🔖 | https://scadaprotocols.com/iec104-asdu-structure/ | (save page as `protocol/iec104_asdu_structure.pdf` if you want it offline) |
| 10 | Survey: Vulnerabilities & Attacks Against ICS (covers IEC-104) | 📄 | https://arxiv.org/pdf/2109.03945 | `protocol/ICS_attacks_survey.pdf` |

## ml_docs/ → feeds `model_documentation/`, `feature_dictionary/`
| # | Document | Type | Link | Save as |
|---|---|---|---|---|
| 11 | Model Cards for Model Reporting (Mitchell et al.) | 📄 | https://arxiv.org/pdf/1810.03993 | `ml_docs/model_cards_1810.03993.pdf` |
| 12 | Datasheets for Datasets (Gebru et al.) | 📄 | https://arxiv.org/pdf/1803.09010 | `ml_docs/datasheets_1803.09010.pdf` |
| 13 | CICFlowMeter — feature definitions | 🔖 | https://github.com/ahlashkari/CICFlowMeter | (read the ReadMe / feature list online; the definitions go into `feature_dictionary/`) |
| 14 | SHAP documentation | 🔖 | https://shap.readthedocs.io/ | (web) |

## power_systems/ → feeds `physics/`, `protection_control/`
| # | Document | Type | Link | Save as |
|---|---|---|---|---|
| 15 | MATPOWER manual (context for `case14`) | 🔖 | https://matpower.org/docs/ | (optional; `case14` itself ships inside pandapower — no download) |
| 16 | SEL application guides (protection principles) | 🔖 | https://selinc.com/support/documentation/ | (free with a SEL account; use for `protection_control/` style) |

## Already in the repo
- SANDI-2024 dataset paper → `references/data explaination paper.pdf`
- SANDI-2024 dataset README → `references/SANDI-2024_dataset_README.md`

---

### Priority order (don't download everything at once)
The four load-bearing KB docs are topology, feature dictionary, the MITRE ATT&CK mapping, and the
regulator corpus. So grab these first: **#5 (MITRE ATT&CK ICS), #13 (CICFlowMeter features),
#4 + #1 (NERC CIP-008 + NIST 800-82)**. `case14` topology needs no download. Everything else is
supporting depth you can fetch as you write each document.
