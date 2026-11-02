# Durability and OCR truth — 1.3.0

Single release after 1.2.0. Hardening (H) and expansion (E) stay on the four notebook jobs. This package version is **not** the parked autobiography row “1.3 People as confirmed identities”.

The longer programme in [durable_notebook_1_3.md](durable_notebook_1_3.md) stays open for the miss desk, confirmed spellings, the hand shelf, and continue-reading. This tag does not close that file’s Waves 1–8.

Authority: [PRODUCT.md](../PRODUCT.md) · [ROADMAP.md](../ROADMAP.md).

## Invariants

JSON-on-disk stays authority. SQLite stays a disposable cache. `schema_version` stays 1. No migrator. No `completed_partial`. `effective_text()` does not include bookmarks, marginal notes, or skip-OCR flags. No autobiography imports, new analysis modules, in-app trainer, auth, or backup encryption.

## Track H — Hardening [x]

| Item | Evidence |
|------|----------|
| H1 format census | `services/format_census.py` inside `workspace-doctor`. Unknown files are reported and left untouched. |
| H2 restore one notebook | `WorkspaceBackupService.restore_notebook`. CLI `backup restore-notebook` (`--dry-run`, `--force`). Crash-before-rename test in `tests/services/test_wave_1_3.py`. |
| H3 archive hot path | `cheap_project_stat` plus `data/cache/archive.signatures.json`. TTL refresh skips `ProjectService.load` when the stat still matches. Nightly 100×40 test is `slow`; the 25×20 fixture stays on the PR suite. |
| H4 job outcome | `services/job_outcome.py`. `completed` + `circuit_open` displays as completed-with-gaps. `transcribe run --retry-failed`. |

## Track E — Expansion [x]

| Item | Evidence |
|------|----------|
| E1 scoreboard | `quality.build_scoreboard`, CLI `quality scoreboard`, Diagnostics. |
| E2 cleanup judgement | Review accept/reject records a `cleanup` quality rating and does not delete the attempt. |
| E3 reading marks | `transcribe.reading-marks` sidecar. Contract: [reading-marks.md](../contracts/reading-marks.md). |
| E4 do-not-OCR | Optional page `ocr_policy: skip`. Jobs omit those pages. Export uses the marginal note, not OCR text. |
| E5 batch metadata | `transcribe pages batch` is a dry run unless `--apply`. Empty selections are refused. |
| E6 declutter v6 | Punch-hole margins and calibration stripes. `DECLUTTER_VERSION` 6. |

## Explicitly out

Autobiography and context imports, Person identities, related pages by date, new analysis modules, RAG auto-ingest after OCR, in-app training, a new UI host, LAN auth, backup encryption, page-level merge, `completed_partial`, and a schema_version 2 migrator.
