# Developer docs index

Active developer and maintainer docs. Historical material is listed only via [ARCHIVE_INDEX](archive/ARCHIVE_INDEX.md).

## Orientation

| Doc | Purpose |
|-----|---------|
| [developer_quickstart.md](developer_quickstart.md) | Mental model, venv, Makefile test lanes, extension points |
| [dev/CONTRIBUTING.md](dev/CONTRIBUTING.md) | Docs authority model and sync checklist |
| [dev/docs_architecture.md](dev/docs_architecture.md) | Docs surfaces map; [how screenshots and GIFs are generated](dev/docs_architecture.md#documentation-media) (`make docs-media`) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System shape and ownership boundaries |
| [PRODUCT.md](PRODUCT.md) | Product definition |
| [CONTRACT_INDEX.md](CONTRACT_INDEX.md) | Concept → authoritative contract |

## Active product

| Doc | Purpose |
|-----|---------|
| [ROADMAP.md](ROADMAP.md) | Product roadmap. **1.4.0** tags 1.3 correct waves. Ladder **1.4** shelf and **1.5** continue-reading remain. Autobiography write-up is on file, not this repo’s backlog |
| [dev/expansion_hardening_wave_1_3.md](dev/expansion_hardening_wave_1_3.md) | 1.3.0 durability and OCR truth (restore one notebook, scoreboard, reading marks, skip-OCR, declutter v6) |
| [dev/durable_notebook_1_3.md](dev/durable_notebook_1_3.md) | 1.3 correct W1–W8 implemented. Remaining: 1.4 hand shelf, 1.5 continue-reading |
| [dev/deepen_waves_1_1.md](dev/deepen_waves_1_1.md) | 1.1 deepen-in-place waves (Inbox, declutter v4, reorder, hand-model bring-back, leftover architecture) — folded into 1.2 |
| [dev/expansion_hardening_wave_1_2.md](dev/expansion_hardening_wave_1_2.md) | 1.2 expansion & hardening wave (H1–H4, E1–E5, Q) — shipped as **1.2.0** |
| [usability_wave_plan.md](usability_wave_plan.md) | Usability-wave tracks U0–U4 (done; Inbox polish may continue) |
| [infrastructure_wave_0_9_plan.md](infrastructure_wave_0_9_plan.md) | 0.9 infrastructure wave: **I0–I6** landed |
| [runtime/install_verification_matrix.md](runtime/install_verification_matrix.md) | Tag evidence cells (Docker / native / Ollama) |
| [assessments/README.md](assessments/README.md) | Transcribe vs TranscriptX survey (2026-10-23) and v1 gap register |
| [dev/release_governance.md](dev/release_governance.md) | Authoritative next-tag checklist (I2); `# pre-release` is local confidence only |
| [dev/release_severity_triage.md](dev/release_severity_triage.md) | What blocks a **1.0** tag vs what waits |
| [dev/release_ops.md](dev/release_ops.md) | Support policy: Docker preferred, no PyPI, local tags |
| [dev/manual_acceptance_1_0.md](dev/manual_acceptance_1_0.md) | Maintainer 1.0 journeys (offline vs live OCR) |
| [dev/analysis_quality_audit.md](dev/analysis_quality_audit.md) | Frozen core-module honesty sheet |
| [dev/dependency_audit.md](dev/dependency_audit.md) | CVE / waiver log |
| [dev/user_testing_0_9.md](dev/user_testing_0_9.md) | Stranger-testing is not a release gate |
| [dev/smoke_kit_import_ocr.md](dev/smoke_kit_import_ocr.md) | Design only: import → OCR smoke; `edited_text` survives re-OCR. Not a PR CI vision run |
| [public_surfaces.md](public_surfaces.md) | GUI IA and supported entrypoints |
| [INTEGRATION_SEAM.md](INTEGRATION_SEAM.md) | Future notebook handoff (not shipped) |

## Reviews

Product and module reviews (critique and follow-ups — not contracts): [reviews/README.md](reviews/README.md).

## Engineering notes

| Doc | Purpose |
|-----|---------|
| [runtime/installation.md](runtime/installation.md) | Install extras and env vars |
| [runtime/docker.md](runtime/docker.md) | Container layout |
| [dev/analysis_module_porting.md](dev/analysis_module_porting.md) | TX → Transcribe dispositions (living map) |
| [dev/analysis_port_pins.md](dev/analysis_port_pins.md) | Exact TX commit/file pin registry |
| [dev/places_tx_alignment.md](dev/places_tx_alignment.md) | NER/places map alignment with TranscriptX |
| [dev/settings_tx_alignment.md](dev/settings_tx_alignment.md) | Settings / profiles / models / prompts alignment |
| [dev/ocr_review_workbench_plan.md](dev/ocr_review_workbench_plan.md) | Post-U3 OCR Review workbench (scan / tabbed lanes / evidence / merged draft / transcription) |
| [dev/streamlit_efficiency_audit.md](dev/streamlit_efficiency_audit.md) | Streamlit every-rerun / Review / View cost audit and PR1 fluidity fixes |
| [dev/refactor_waves_1_0_1.md](dev/refactor_waves_1_0_1.md) | Staged decoupling waves (layering, CLI, batch picker, Review/View split, ProjectService) |
| [dev/deepen_waves_1_1.md](dev/deepen_waves_1_1.md) | 1.1 deepen-in-place wave acceptance tables |
| [runtime/ocr_model_recipes.md](runtime/ocr_model_recipes.md) | Per-model OCR recipes (builtins + workspace overlay). PaddleOCR-VL `OCR:` lane is `feat/paddleocr-mlx` (`--provider paddleocr`) |
| [contracts/ocr-model-recipes.md](contracts/ocr-model-recipes.md) | Recipe overlay schema, merge, fingerprint |

## Archive

Historical delivery plans (Wave 1 analysis, Detection wave 2, bulk Analyse, U0/U1 hardening checklist): [archive/ARCHIVE_INDEX.md](archive/ARCHIVE_INDEX.md).

Default suite stays offline (fake Ollama provider). Live OCR probes are optional and environmental.
