# Expansion & hardening wave — 1.2.0

Balanced-max programme in a single release: parallel hardening (H),
expansion (E), and quality (Q) tracks of PR-sized waves converging on the
**1.2.0** tag. It folds in the unreleased 1.1 deepen waves (W1–W8) and closes
W9 (L2). Scope-lean invariants hold throughout: no autobiography/context
corpus, no new analysis modules, no UI rewrite, no in-app trainer, SQLite
stays a disposable cache, additive-only formats, no `completed_partial`.

Authority: [PRODUCT.md](../PRODUCT.md) · [ROADMAP.md](../ROADMAP.md) ·
[ARCHITECTURE.md](../ARCHITECTURE.md). Plan origin: maintainer request
“robust and ambitious expansion and hardening wave” (balanced-max, one
release).

## Wave 0 — Close the 1.1 kernel [x]

| Item | Evidence |
|------|----------|
| L2 `load()` default | `ProjectService.load(reconcile=False)` is now the default read; notebook-open (`ui/app.py` once-per-session), Analysis plan/runner freeze, batch OCR/Analyse, and job build keep deliberate `reconcile=True` with `# Deliberate reopen (L2)` comments. Gate test: `test_gate_default_load_is_read_explicit_reconcile_interrupts` |
| Evidence refresh | Encrypted-PDF rejection is in fact tested (`tests/ingest/test_ingest.py::test_rejects_encrypted_pdf`); the 2026-09-03 review's “untested” note is stale. Cleanup-fingerprint P1, L1, L3, L4 remain landed — not re-litigated |

## Track H — Hardening

### H1 — Failure & recovery [x]
- Disk-full pre-check before any OCR page write: `transcribe.persistence.disk.ensure_disk_budget` (256 MiB headroom + 16 KiB/page estimate) called from `JobCoordinator.start` / `run_blocking` / `run_frozen_plan_blocking`; raises `DiskFullError` before scheduling.
- Diagnostics job timeline: `transcribe.services.job_timeline.build_job_timeline` aggregates OCR job records (validated via `require_format`), analysis run records, and latest detection attempts; malformed records appear as invalid entries, never trusted silently. Rendered in System → Diagnostics with the record id as correlation id.
- Existing crash/lock corpus (restore mid-replace, kill mid-run, lock contention) in `tests/acceptance/` remains the crash-injection base; L2 gate added above.

### H2 — Security & supply chain [x]
- Non-loopback bind guard: `transcribe.net_guard.check_bind_allowed` in `transcribe-ui` startup. Native non-loopback binds refuse without `TRANSCRIBE_ALLOW_LAN=1`; container binds (`TRANSCRIBE_CONTAINER=1`, set in the Dockerfile) warn only, because Compose's `TRANSCRIBE_BIND_HOST` (loopback by default) decides host exposure. No auth is added — see SECURITY.md.
- Redaction: `redact_sensitive` scrubs URL credentials, `api_key`/`token` query values, workspace roots, and the home directory; applied to Diagnostics findings, timeline errors, and messages.
- Supply chain: `.github/dependabot.yml` (actions / pip / docker, weekly) plus a nightly `dependency-audit` job running `pip-audit` and uploading a CycloneDX SBOM. **Decision:** Dependabot keeps action pins current instead of hand-pinning SHAs from memory (a wrong SHA breaks CI silently); audit/SBOM evidence lands in nightly.

### H3 — Scale & performance [x]
- `tests/acceptance/scale/` (`scale` marker, `make test-scale`, nightly step): 25 notebooks × 20 pages, Archive search + listing budgets (20 s guards). Healthy run ≈ 6 s locally.
- Streamlit efficiency round 2: no new measured hotspot beyond the 1.0.1 audit; shell contracts in `tests/unit/test_shell_perf.py` remain the guard. New Library/Search widgets are plain inputs — no extra rerun caches were needed.

### H4 — Longevity & integrity [x]
- `transcribe export verify`-style standalone check: CLI `transcribe verify-export <dir>` (`services/export_verify.py`) validates manifest, checksums, notebook JSON, revision stamps, EPUB zip, and PDF header — an export is readable without Transcribe.
- Workspace sweep: CLI `transcribe workspace-doctor [--deep]` (`services/workspace_doctor.py`) runs corpus-doctor plus a DoctorService pass per notebook; one bad notebook does not hide the rest.
- Schema registry: `transcribe.saved-searches`, `transcribe.notebook-collections`, `transcribe.quality-ratings` registered in `persistence/schema.py`. Migration rehearsal test: a stripped 1.0.1-shaped notebook loads (default read), exports, and verifies; absent 1.2 workspace files are valid.

## Track E — Expansion (shipped surfaces only)

### E1 — Search first-class [x]
- `ArchiveFilters.people` / `places` over published NER (contract: [saved-searches.md](../contracts/saved-searches.md)); archive index stores `pages.entities_json` at reindex, signature includes the NER published file.
- Saved searches: `transcribe.saved-searches` store, Search-page expander (apply / save current / delete), CLI `saved-search` + `search --saved`.

### E2 — Collections & archived state [x]
- Contract [notebook-collections.md](../contracts/notebook-collections.md); `NotebookCollectionsStore`; Library manager expander, archived/collection filters, Archived card caption; CLI `collections …`. Archive cache carries derived `archived` / `collections_json` only.

### E3 — Export expansion [x]
- Reading-format page tag filters: `ExportOptions.include_tags` (AND) / `exclude_tags` (any), in Export panel + CLI (`--include-tag` / `--exclude-tag`); notebook JSON always keeps every page.
- Anthology by collection: Export panel Scope → Collection, CLI `--collection`.
- Custom body fonts: `custom:<Family>` typography keys + `services/custom_fonts.register_custom_font` (validated .ttf/.otf/.woff/.woff2 ≤ 5 MiB under `data/config/fonts/`); CLI `--custom-font`, Export panel family field.

### E4 — Quality & evaluation loop [x]
- Import→OCR smoke kit implemented (contract: [quality-ratings.md](../contracts/quality-ratings.md)).
- Quality store: sampled OCR (auto-recorded on first Review correction), cleanup accept/reject, analysis thumbs — all local; Diagnostics summary; CLI `quality summary|rate`.

### E5 — Capture & reading polish [x]
- Declutter v5: `remove_lid_slivers` (4–15 px uniform dark/coloured edge slivers below the normal min band; near-paper means excluded), `DECLUTTER_VERSION` 5, provenance identity updated. The former “narrow gutter below min band no-ops” test now asserts the v5 crop.
- Page-scan lightbox: `ui/page_lightbox.py` parent-frame island wired into Reading (`page_viewer`) and Review (`review_workbench`); plain `st.image` hover fullscreen remains the fallback.

## Track Q — Convergence [x]

- Docs in-wave: contracts above, CONTRACT_INDEX, user guide, known
  limitations, ROADMAP status/decision log, CHANGELOG.
- Release gate: smoke / fast / contracts / acceptance / coverage, lint,
  release hygiene, Docker smoke, Sphinx docs, scale lane.
- Version: package **1.2.0**.

## Explicitly out

Autobiography/context imports, Person store, Slices, reconstruction, new or
reinterpreted analysis modules (incl. `ocr_quality`), in-app training,
Streamlit replacement, corpus-level Analyse synthesis, backup encryption or
merge-restore, `data/context/`.
