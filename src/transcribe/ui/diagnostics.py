"""Diagnostics: workspace corpus-doctor always; notebook doctor when selected."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from transcribe.corpus.paths import CorpusPaths
from transcribe.errors import ProjectError, TranscribeError
from transcribe.ports import SystemClock, UuidGenerator
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.corpus_doctor import CorpusDoctorService
from transcribe.services.doctor import DoctorService
from transcribe.net_guard import redact_sensitive
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.ui import icons as ic
from transcribe.ui.home import ollama_health_line

_WORKSPACE_REPORT_KEY = "diagnostics_workspace_report"
_WORKSPACE_ERROR_KEY = "diagnostics_workspace_error"
_NOTEBOOK_REPORT_KEY = "diagnostics_notebook_report"
_NOTEBOOK_ERROR_KEY = "diagnostics_notebook_error"
_NOTEBOOK_SKIP_KEY = "diagnostics_notebook_skip"


def _render_findings(findings) -> None:
    if not findings:
        st.success("No findings.")
        return
    for f in findings:
        line = f"**{f.severity}** `{f.code}` — {redact_sensitive(f.message)}"
        if f.severity == "error":
            st.error(line)
        elif f.severity == "warning":
            st.warning(line)
        else:
            st.info(line)


def diagnostics_reports_cached() -> bool:
    return _WORKSPACE_REPORT_KEY in st.session_state or _WORKSPACE_ERROR_KEY in st.session_state


def _clear_diagnostics_cache() -> None:
    for key in (
        _WORKSPACE_REPORT_KEY,
        _WORKSPACE_ERROR_KEY,
        _NOTEBOOK_REPORT_KEY,
        _NOTEBOOK_ERROR_KEY,
        _NOTEBOOK_SKIP_KEY,
    ):
        st.session_state.pop(key, None)


def ensure_diagnostics_reports(
    runtime: RuntimePaths, *, root: str | None, used_deep: bool
) -> None:
    """Run doctors unless session already holds a report from this button press."""
    if diagnostics_reports_cached():
        return
    corpus = CorpusPaths.from_runtime(runtime)
    try:
        st.session_state[_WORKSPACE_REPORT_KEY] = CorpusDoctorService(corpus).run(
            deep=used_deep, per_notebook=False
        )
    except Exception as exc:  # noqa: BLE001
        st.session_state[_WORKSPACE_ERROR_KEY] = str(exc)
    if not root:
        st.session_state[_NOTEBOOK_SKIP_KEY] = (
            "Select a notebook in View to run the notebook doctor."
        )
        return
    try:
        paths = open_project_paths(Path(root))
        projects = ProjectService(paths, clock=SystemClock(), ids=UuidGenerator())
        st.session_state[_NOTEBOOK_REPORT_KEY] = DoctorService(paths, projects).run(
            deep=used_deep
        )
    except (ProjectError, TranscribeError, OSError) as exc:
        st.session_state[_NOTEBOOK_ERROR_KEY] = str(exc)


def render_diagnostics(runtime: RuntimePaths, *, root: str | None) -> None:
    st.caption(ollama_health_line())
    deep = st.checkbox("Deep hashing (slower)", value=False, key="diagnostics_deep")
    if st.button("Run diagnostics", type="primary", key="diagnostics_run", icon=ic.RUN):
        st.session_state["diagnostics_ran"] = True
        st.session_state["diagnostics_deep_used"] = bool(deep)
        _clear_diagnostics_cache()

    if not st.session_state.get("diagnostics_ran"):
        st.info("Run diagnostics to check the workspace corpus and, if selected, this notebook.")
        return

    used_deep = bool(st.session_state.get("diagnostics_deep_used"))
    ensure_diagnostics_reports(runtime, root=root, used_deep=used_deep)

    st.markdown("#### Workspace")
    workspace_error = st.session_state.get(_WORKSPACE_ERROR_KEY)
    if workspace_error:
        st.error(f"Workspace doctor failed: {workspace_error}")
    else:
        report = st.session_state.get(_WORKSPACE_REPORT_KEY)
        if report is not None:
            if report.ok:
                st.success("Workspace corpus doctor passed.")
            else:
                st.error("Workspace corpus doctor reported errors.")
            _render_findings(report.findings)

    st.markdown("#### This notebook")
    skip = st.session_state.get(_NOTEBOOK_SKIP_KEY)
    if skip:
        st.caption(str(skip))
        return
    notebook_error = st.session_state.get(_NOTEBOOK_ERROR_KEY)
    if notebook_error:
        st.error(str(notebook_error))
        return
    nb_report = st.session_state.get(_NOTEBOOK_REPORT_KEY)
    if nb_report is None:
        return
    if nb_report.ok:
        st.success("Notebook doctor passed.")
    else:
        st.error("Notebook doctor reported errors.")
    _render_findings(nb_report.findings)

    try:
        from transcribe.services.quality import QualityRatingStore

        quality = QualityRatingStore(runtime).summary()
    except Exception:  # noqa: BLE001
        quality = None
    if quality is not None and quality["total"]:
        st.markdown("#### Quality (local ratings)")
        st.caption(
            "Collect-only local signals from Review corrections, cleanup "
            "accept/reject, and analysis ratings. Nothing leaves this machine."
        )
        st.markdown(
            f"Ratings: **{quality['total']}** · OCR samples: "
            f"**{quality['ocr_samples']}** · Mean character error rate: "
            f"**{quality['mean_cer'] if quality['mean_cer'] is not None else '—'}**"
        )

    if root:
        from transcribe.services.job_timeline import build_job_timeline

        st.markdown("#### Job timeline")
        st.caption(
            "Recent OCR, Analyse, and Detect runs for this notebook. "
            "The run id is the correlation id for its records on disk."
        )
        try:
            entries = build_job_timeline(open_project_paths(Path(root)), limit=25)
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Job timeline unavailable: {exc}")
            entries = []
        if not entries:
            st.caption("No job records yet for this notebook.")
        for entry in entries:
            when = entry.started_at or entry.ended_at or "unknown time"
            counts = (
                f"{entry.completed}/{entry.total} done"
                if entry.total
                else "—"
            )
            label = (
                f"**{entry.kind}** `{entry.status}` · {when} · {counts}"
                f" · `{entry.correlation_id[:12]}`"
            )
            if entry.detail:
                label += f" · {entry.detail}"
            if not entry.valid:
                st.error(f"{label} — unreadable record: {redact_sensitive(entry.error)}")
            else:
                st.markdown(label)
                if entry.message:
                    st.caption(redact_sensitive(entry.message))
