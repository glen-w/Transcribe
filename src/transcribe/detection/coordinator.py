"""In-process Detect run coordinator (mirrors AnalysisCoordinator cancel)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace
from typing import Any

from transcribe.detection.api import DetectionService
from transcribe.services.project import ProjectService


@dataclass
class DetectionProgress:
    status: str = "idle"  # idle|running|completed|cancelled|failed
    total: int = 0
    completed: int = 0
    current_detector_id: str = ""
    message: str = ""
    cancel_requested: bool = False
    error: str | None = None
    outcomes: dict[str, str] = field(default_factory=dict)


@dataclass
class _RunState:
    progress: DetectionProgress
    thread: threading.Thread | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    results: list[dict[str, Any]] = field(default_factory=list)


class DetectionRunCoordinator:
    """One Detect batch per process; survives Streamlit reruns via cache_resource."""

    def __init__(self, project_service: ProjectService) -> None:
        self.projects = project_service
        self._lock = threading.Lock()
        self._run: _RunState | None = None

    def get_progress(self) -> DetectionProgress:
        with self._lock:
            if self._run is None:
                return DetectionProgress()
            return replace(self._run.progress, outcomes=dict(self._run.progress.outcomes))

    def is_running(self) -> bool:
        with self._lock:
            return bool(
                self._run is not None
                and self._run.thread is not None
                and self._run.thread.is_alive()
            )

    def get_results(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._run is None:
                return []
            return [dict(row) for row in self._run.results]

    def request_cancel(self) -> None:
        with self._lock:
            if self._run is None:
                return
            self._run.cancel_event.set()
            self._run.progress.cancel_requested = True
            self._run.progress.message = "Stopping after current window…"

    def start(
        self,
        detector_ids: list[str],
        *,
        page_ids: list[str] | None = None,
        force: bool = False,
        auto_tag: bool = False,
    ) -> None:
        if not detector_ids:
            raise ValueError("select at least one detector")
        with self._lock:
            if self._run is not None and self._run.thread is not None and self._run.thread.is_alive():
                raise RuntimeError("a detection run is already in progress")
            state = _RunState(
                progress=DetectionProgress(
                    status="running",
                    total=len(detector_ids),
                    message="Starting…",
                )
            )
            self._run = state
            thread = threading.Thread(
                target=self._run_loop,
                args=(state, list(detector_ids), page_ids, force, auto_tag),
                daemon=True,
                name="transcribe-detect",
            )
            state.thread = thread
            thread.start()

    def _run_loop(
        self,
        state: _RunState,
        detector_ids: list[str],
        page_ids: list[str] | None,
        force: bool,
        auto_tag: bool,
    ) -> None:
        svc = DetectionService(self.projects)
        cancelled = False
        failed = False
        for index, detector_id in enumerate(detector_ids):
            if state.cancel_event.is_set():
                cancelled = True
                break
            with self._lock:
                state.progress.current_detector_id = detector_id
                state.progress.message = f"Running `{detector_id}`…"
                state.progress.completed = index

            def _progress(done: int, total: int, *, _did: str = detector_id) -> None:
                with self._lock:
                    state.progress.message = f"{_did}: {done}/{total} windows"

            try:
                result = svc.run_detector(
                    detector_id,
                    page_ids=page_ids,
                    force=force,
                    cancel_check=state.cancel_event.is_set,
                    progress_callback=_progress,
                    auto_tag=auto_tag,
                )
            except Exception as exc:  # noqa: BLE001 — surface in progress, keep remaining detectors
                failed = True
                with self._lock:
                    state.progress.outcomes[detector_id] = "failed"
                    state.progress.error = str(exc)
                    state.results.append({"detector_id": detector_id, "outcome": "failed", "error": str(exc)})
                continue
            outcome = str(result.get("attempt_state") or result.get("outcome") or "success")
            if outcome == "cancelled" or state.cancel_event.is_set():
                cancelled = True
            with self._lock:
                state.progress.outcomes[detector_id] = outcome
                state.results.append(dict(result) if isinstance(result, dict) else {"outcome": outcome})
                state.progress.completed = index + 1
            if cancelled:
                break
        with self._lock:
            if cancelled:
                state.progress.status = "cancelled"
                state.progress.message = "Stopped after current window."
            elif failed:
                state.progress.status = "failed"
                state.progress.message = state.progress.error or "Detection failed."
            else:
                state.progress.status = "completed"
                state.progress.message = "Detection finished."
            state.progress.current_detector_id = ""
