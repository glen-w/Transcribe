# Watch — paddle-probe (PaddleOCR-VL-1.6)

- **Command:** `NIGHT_JOB_PAUSED=/nonexistent NIGHT_STOP= ./run.sh` (already running; Cursor terminal `405893`)
- **Goal:** watch until the one-shot paddle probe completes (sidecar → mini-page → `bulk-run notebooks` newest notebook `--provider paddleocr` → compare assessment)
- **Started watching:** 2026-11-10T16:33:00Z
- **Hang quiet window:** 10 minutes (sidecar model load / first page allowed longer)
- **Also:** stop daytime fiveyear OCR; leftover qwen+granite work stays for overnight `transcribe-night` (23:45, `focus-ocr.env`)

## Events

- 16:33Z watch start. MLX server already up (`Model and processor loaded successfully`, Uvicorn `:8111`). Pipeline sidecar still coming up. Orphan `transcribe bulk-run` (black, qwen+granite) still alive after dayshift shells died; stale dayshift/transcribe-night locks remain.
- 16:33Z INT then KILL orphan bulk-run; removed stale dayshift/transcribe-night locks. Overnight `transcribe-night` LaunchAgent stays loaded (23:45, `focus-ocr.env` qwen+granite, skip rest).
- 16:34Z pipeline `PP-DocLayoutV3` fetched; `:8112` healthy. Mini-page probe **ok** (`chars=397`, "Deep test mini page"). Notebook `black`, `PaddleOCR-VL-1.6`.
- 16:35Z `transcribe bulk-run … --provider paddleocr --workers 1` pid 57319. Per-page lines in night_run capture (not the Cursor terminal until the step ends).
- 16:40Z **46/184 succeeded, failed=0**. ~8s/page; ETA ~20 min remaining on the notebook.
- 16:51Z bulk-run **184/184 succeeded, failed=0**. Compare script wrote `assessments/data/paddle-black-compare.json` and `assessments/2026-11-10-paddleocr-mlx.md`. Job **exit 0**. Sidecar torn down; paddle lock gone.

## Result

- **completed**
- **Duration (watch):** ~18 min (16:33–16:51Z). Probe wall clock from 12:41Z includes the lock wait.
- **Failures fixed:** none (no code edits this watch)
- **Hangs/kills:** killed leftover fiveyear `bulk-run` (qwen+granite) so paddle could own Metal; that OCR is deferred to overnight `transcribe-night` (23:45).
- **Diff this watch:** watch log only (no product patch). Pre-existing `feat/paddleocr-mlx` tree is dirty from the paddle feature, not from this babysit.
