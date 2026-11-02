# Refactor waves toward 1.0.1

Staged, PR-sized decoupling. No Streamlit rewrite, no database system of record, no event bus, no split of CLI vs UI service implementations. Evidence: the 2026-11-02 refactor assessment and [architecture_from_evidence.md](../reviews/architecture_from_evidence.md).

**Deep-test after wave N treats only that wave’s acceptance table as required.** Later waves stay sequenced, not missing.

Non-goals for the whole programme: rename `tx_*` session keys, merge OCR and Analyse batch coordinators, change `effective_text()` semantics, add `completed_partial` job status.

---

## Wave 1 — Layering hygiene (this commit)

| Item | Acceptance |
|------|------------|
| Chart palettes | Defaults + `sanitise_chart_colors` live in `transcribe.config.chart_colors`. `ChartColorsConfig` does not import `transcribe.ui`. Streamlit render stays in `ui.chart_colors`. |
| Unit ids | `page_id_from_unit_id` lives in `transcribe.analysis.units`. Display helpers import analysis, not UI navigation. |
| Schema registry | `persistence.schema.SUPPORTED` lists `transcribe.settings`, `transcribe.profile`, `transcribe.job-record`, `transcribe.interface-menus`, `transcribe.geocode-cache` at version 1. Settings/profile load still raises `ConfigError` (no error-type change). Interface-menus on-disk files may still omit `format`. |
| Tests | Core AST gate forbids `transcribe.ui` imports. Palette subprocess test forbids Streamlit **and** `transcribe.ui`. |

---

## Wave 2 — CLI command modules

Split `__main__.py` into `transcribe.cli` (parser + one module per command family). `python -m transcribe` and the `transcribe` console script still dispatch through `__main__.main`. No flag or exit-code change.

| Item | Acceptance |
|------|------------|
| Parser | `transcribe.cli.parser.build_parser` owns argparse |
| Commands | notebook / export / bulk / rag / backup live under `transcribe.cli` |
| Entry | `transcribe.__main__.main` still imported by tests; `PATHS` still patchable there |
| Flags | Identical subcommands and exit codes |

---

## Wave 3 — Shared batch notebook picker

Extract the pending / import-run / pick radio from `run_transcribe.py` and `run_analysis_batch.py` into a shared widget parameterized by purpose. Keep `BatchOcrCoordinator` and `BatchAnalysisCoordinator` separate. Session-key prefixes stay (`tx_*` / `ax_*`).

| Item | Acceptance |
|------|------------|
| Shared widget | `ui.batch_source_picker.render_batch_notebook_source` owns radio / import-run select / pick multiselect |
| Callers | Thin `_render_batch_notebook_source` wrappers remain in Transcribe and Analyse batch pages |
| Keys | Widget keys stay `tx_batch_*` / `ax_batch_*`; queued Inbox hops still use `targets.py` constants |
| Coordinators | `BatchOcrCoordinator` and `BatchAnalysisCoordinator` stay separate |

---

## Wave 4 — Decompose Review / Reading / View

Extract `render_page_viewer` into nav-resolve / chrome / body. Split Review so `render_review_page` is orchestration over existing tab helpers. Pull remaining row-shaping out of `analysis_product_views.py` into Streamlit-free helpers. Behaviour unchanged.

| Item | Acceptance |
|------|------------|
| Page viewer | `render_page_viewer` orchestrates `_resolve_viewer_session` / `_render_viewer_chrome` / `_render_viewer_body` |
| Review | `render_review_page` orchestrates resolve / chrome / lane body; tab helpers stay |
| View rows | `page_id_for_moment`, entity-tone rows, highlight-quote rows, foundations headline live in Streamlit-free `analysis_display_helpers` |
| Behaviour | Session keys, Jump-to-page, Review lanes, and product copy unchanged |

---

## Wave 5 — ProjectService collaborators + load vs reconcile

Date / review-repair / declutter become collaborators that `ProjectService` delegates to. `load()` remains the public API; reconcile stays explicit and documented. Do not change `effective_text()`, fingerprints, or lock order.

| Item | Acceptance |
|------|------------|
| Dates | `project_dates.ProjectDateOps`; `approve_page_date` / suggest / fill still on `ProjectService` |
| Review repair | `project_review_repair.ProjectReviewRepair`; empty/truncated/validity repairs still on `ProjectService` |
| Declutter | `project_declutter.ProjectDeclutter` + `DeclutterReapplyStats` re-exported from `project.py` |
| load() | Still the public API; default `reconcile=True` unchanged; docstring names `reconcile=False` as the mid-run read |
| reconcile | Public `reconcile_interrupted()` is the explicit reopen path; lock order unchanged |

---

## Wrap-up

Docs sync, offline coverage expansion (UI still omitted from `.coveragerc`; floor **80**), leftover ingest/export/provider/job isolation tests, package **1.0.1**, local `# pre-release`.
