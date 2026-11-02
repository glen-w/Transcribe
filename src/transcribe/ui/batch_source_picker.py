"""Shared pending / import-run / pick radio for OCR and Analyse batch launchers.

Session widget keys stay purpose-prefixed (``tx_*`` / ``ax_*``) so existing
hops from Inbox and in-flight sessions do not reset.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

import streamlit as st

from transcribe.errors import TranscribeError, ValidationError
from transcribe.ui import icons as ic

CandidateList = list[Any]


@dataclass(frozen=True)
class BatchSourcePickerSpec:
    """Purpose-specific labels and session keys for one batch launcher."""

    prefix: str
    queued_source_key: str
    queued_run_key: str
    queued_ids_key: str
    source_options: tuple[str, ...]
    source_labels: dict[str, str]
    default_source: str | None = None
    radio_help: str | None = None
    pending_button_help: str = "Refresh the pending list."
    pending_empty: str | None = None
    pick_label: str = "Notebooks"
    pick_placeholder: str | None = None
    pick_help: str | None = None
    pick_empty: str | None = None
    hide_pick_when_empty: bool = False
    require_pick: bool = False


def widget_keys(prefix: str) -> dict[str, str]:
    """Streamlit widget keys for one purpose-prefixed picker (``tx`` / ``ax``)."""
    return {
        "source": f"{prefix}_batch_source",
        "pending_refresh": f"{prefix}_batch_pending_refresh",
        "import_run": f"{prefix}_batch_import_run",
        "pick": f"{prefix}_batch_pick",
    }


def apply_queued_source(
    session: MutableMapping[str, Any],
    *,
    queued_key: str,
    widget_key: str,
    options: Sequence[str],
    default: str | None = None,
    only_if_unset: bool = False,
) -> None:
    """Copy a one-shot queued source into the radio widget key."""
    queued = session.pop(queued_key, None)
    if queued in options and (not only_if_unset or widget_key not in session):
        session[widget_key] = queued
    elif default is not None and widget_key not in session:
        session[widget_key] = default


@dataclass(frozen=True)
class BatchSourceHooks:
    load_pending: Callable[..., CandidateList]
    pending_caption: Callable[[CandidateList], None]
    load_import_runs: Callable[[], CandidateList]
    load_picker: Callable[[], CandidateList]
    select_from_import: Callable[[str, CandidateList], CandidateList]
    import_caption: Callable[[CandidateList], None]
    pick_label: Callable[[Any], str]
    select_picked: Callable[[CandidateList, list[str]], CandidateList]
    default_pick_ids: Callable[[CandidateList], list[str]] | None = None


def render_batch_notebook_source(
    spec: BatchSourcePickerSpec,
    hooks: BatchSourceHooks,
) -> tuple[CandidateList, str | None]:
    """Render the notebook-source radio and return ``(selected, import_run_id)``."""
    keys = widget_keys(spec.prefix)
    source_key = keys["source"]
    apply_queued_source(
        st.session_state,
        queued_key=spec.queued_source_key,
        widget_key=source_key,
        options=spec.source_options,
        default=spec.default_source,
        only_if_unset=spec.default_source is None,
    )
    source = st.radio(
        "Notebooks",
        options=list(spec.source_options),
        format_func=lambda s: spec.source_labels[s],
        key=source_key,
        horizontal=True,
        help=spec.radio_help,
    )
    selected: CandidateList = []
    import_run_id: str | None = None
    if source == "pending":
        refresh = st.button(
            "Refresh list",
            key=keys["pending_refresh"],
            help=spec.pending_button_help,
            icon=ic.REFRESH,
        )
        selected = hooks.load_pending(force=refresh)
        hooks.pending_caption(selected)
        if not selected and spec.pending_empty:
            st.info(spec.pending_empty)
    elif source == "import_run":
        runs = hooks.load_import_runs()
        queued_run = st.session_state.pop(spec.queued_run_key, None)
        labels = {r.import_run_id: f"{r.import_run_id} · {r.status}" for r in runs}
        run_ids = [r.import_run_id for r in runs]
        run_key = keys["import_run"]
        if queued_run in run_ids:
            st.session_state[run_key] = queued_run
        if not run_ids:
            st.info("No import runs yet. Batch-import folders under Import → Batch.")
        else:
            chosen = st.selectbox(
                "Import run",
                options=run_ids,
                format_func=lambda rid: labels.get(rid, rid),
                key=run_key,
            )
            import_run_id = str(chosen) if chosen else None
            if import_run_id:
                try:
                    picker = hooks.load_picker()
                    selected = hooks.select_from_import(import_run_id, picker)
                    hooks.import_caption(selected)
                except (TranscribeError, ValidationError) as exc:
                    st.error(str(exc))
    else:
        picker = hooks.load_picker()
        queued_ids = st.session_state.pop(spec.queued_ids_key, None)
        options = [c.notebook_id for c in picker]
        labels = {c.notebook_id: hooks.pick_label(c) for c in picker}
        pick_key = keys["pick"]
        default = [nid for nid in (queued_ids or []) if nid in options]
        if default and pick_key not in st.session_state:
            st.session_state[pick_key] = default
        elif pick_key not in st.session_state and hooks.default_pick_ids is not None:
            seeded = [nid for nid in hooks.default_pick_ids(picker) if nid in options]
            if seeded:
                st.session_state[pick_key] = seeded
        if not options and spec.hide_pick_when_empty:
            st.info(
                spec.pick_empty
                or (
                    "No notebooks yet. Create one under Workflow → New notebook, "
                    "or batch-import folders."
                )
            )
        else:
            pick_kwargs: dict[str, Any] = {}
            if spec.pick_placeholder is not None:
                pick_kwargs["placeholder"] = spec.pick_placeholder
            if spec.pick_help is not None:
                pick_kwargs["help"] = spec.pick_help
            picked = st.multiselect(
                spec.pick_label,
                options=options,
                format_func=lambda nid: labels.get(nid, nid),
                key=pick_key,
                **pick_kwargs,
            )
            if picked:
                try:
                    selected = hooks.select_picked(picker, list(picked))
                except TranscribeError as exc:
                    st.error(str(exc))
            elif spec.require_pick:
                st.caption("Select at least one notebook.")
    return selected, import_run_id
