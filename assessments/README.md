# OCR / vision assessments

Public pack at repo-root `/assessments/`. Maintainer surveys of Transcribe vs TranscriptX live in [`docs/assessments/`](../docs/assessments/README.md). This folder holds corpus rollups, Nightshift scrapes, live Ollama probes, and the model-assessment narrative (hardware-labelled; notebook titles and page ids appear in the JSON).

## Pins (2026-11-10)

| | |
|--|--|
| Hardware | MacBook Pro, Apple M5 Pro, 64 GB, 20-core GPU |
| Transcribe vision | Local Ollama only (`VisionOCRProvider`) |
| Nightshift target tags | `qwen2.5vl:7b` + `glm-ocr` + `granite3.2-vision` (rank `qwen3:8b`) |
| Projects | `~/Documents/transcribe-projects` |
| Nightshift logs | `~/Documents/nightshift/logs/` · job log `~/Library/Logs/nightshift-transcribe-night.log` |

## Refresh

From the Transcribe repo root:

```bash
python3 assessments/scripts/collect_model_stats.py
python3 assessments/scripts/probe_focus.py
# Full library probe (slow; includes 27b thinking tags):
# PYTHONPATH=src python scripts/probe_ollama_vision_models.py \
#   --json assessments/data/probe-results.json
```

Optional: skip the 2 MB job-log parse with `--skip-job-log`.

Collector semantics match Nightshift `list_tier.py`: `:latest` stripped, vision attempts only, nonempty text counts as succeeded.

## Artifacts

| Path | |
|------|--|
| [2026-11-10-model-assessment.md](2026-11-10-model-assessment.md) | Narrative: performance, errors, Nightshift backlog recipe, `feat/selective-remote-ocr` spec |
| [data/corpus-stats.json](data/corpus-stats.json) | Pages, tiers, per-notebook completion |
| [data/error-by-model.json](data/error-by-model.json) | Attempt status + `error.code` histogram |
| [data/coverage-by-tier.json](data/coverage-by-tier.json) | Succeeded counts per date tier per model |
| [data/nightshift-throughput.json](data/nightshift-throughput.json) | Night markdown scrape, snapshots, job-log outcomes |
| [data/probe-results.json](data/probe-results.json) | Live mini-page probe (focused tag list) |
| [data/probe-green-sample.json](data/probe-green-sample.json) | Four green pages; not written to page-results |
| [data/chat-evidence.md](data/chat-evidence.md) | Curated agent-transcript excerpts |
| [scripts/collect_model_stats.py](scripts/collect_model_stats.py) | Rerun collector (stdlib) |
| [scripts/probe_focus.py](scripts/probe_focus.py) | Focused live probe |
| [scripts/compare_notebook_models.py](scripts/compare_notebook_models.py) | One-notebook paddle vs 7b/granite/DeepSeek |
| [2026-11-10-paddleocr-mlx.md](2026-11-10-paddleocr-mlx.md) | MLX PaddleOCR-VL probe write-up (`feat/paddleocr-mlx`) |

## Repo split

- **Transcribe product code:** this pack is reports and collectors, not providers or CLI.
- **Nightshift:** implement per-tier models after a report names a rest-tier winner.
- **`feat/selective-remote-ocr`:** later Transcribe branch for named miss-desk pages only — spec in the 2026-11-10 assessment, not implemented here.
