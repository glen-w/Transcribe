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

---

## Wave 3 — Shared batch notebook picker

Extract the pending / import-run / pick radio from `run_transcribe.py` and `run_analysis_batch.py` into a shared widget parameterized by purpose. Keep `BatchOcrCoordinator` and `BatchAnalysisCoordinator` separate. Session-key prefixes stay (`tx_*` / `ax_*`).

---

## Wave 4 — Decompose Review / Reading / View

Extract `render_page_viewer` into nav-resolve / chrome / body. Split Review so `render_review_page` is orchestration over existing tab helpers. Pull remaining row-shaping out of `analysis_product_views.py` into Streamlit-free helpers. Behaviour unchanged.

---

## Wave 5 — ProjectService collaborators + load vs reconcile

Date / review-repair / declutter become collaborators that `ProjectService` delegates to. `load()` remains the public API; reconcile stays explicit and documented. Do not change `effective_text()`, fingerprints, or lock order.

---

## Wrap-up

Docs sync, offline coverage expansion (UI still omitted from `.coveragerc`), incremental package version, local `# pre-release`.
