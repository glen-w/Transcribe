"""Notebook page-order controls (Review / thumbnail grid). Kernel stays in ProjectService."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from transcribe.errors import JobConflictError, ProjectError, TranscribeError
from transcribe.runtime_paths import build_runtime_paths
from transcribe.services.archive import bump_archive_generation
from transcribe.services.project import ProjectService
from transcribe.ui import icons as ic
from transcribe.ui.components.info_tooltip import widget_help

_DIRTY_MSG = "Save or discard unsaved Review text before reordering pages."
_ORDER_INPUT_LABEL = "Notebook page order (drag)"


def permutation_move(page_ids: Sequence[str], page_id: str, delta: int) -> list[str]:
    """Return a new order with ``page_id`` shifted by ``delta`` (−1 up, +1 down)."""
    ordered = list(page_ids)
    try:
        idx = ordered.index(page_id)
    except ValueError as exc:
        raise ProjectError(f"unknown page_id: {page_id}") from exc
    dest = idx + int(delta)
    if dest < 0 or dest >= len(ordered):
        return ordered
    ordered.pop(idx)
    ordered.insert(dest, page_id)
    return ordered


def permutation_to_position(page_ids: Sequence[str], page_id: str, position: int) -> list[str]:
    """1-based notebook position (1 = first page)."""
    ordered = list(page_ids)
    try:
        idx = ordered.index(page_id)
    except ValueError as exc:
        raise ProjectError(f"unknown page_id: {page_id}") from exc
    dest = int(position) - 1
    if dest < 0 or dest >= len(ordered) or dest == idx:
        return ordered
    ordered.pop(idx)
    ordered.insert(dest, page_id)
    return ordered


def sync_view_session_after_reorder(project, *, paths) -> None:
    """Refresh viewer session lists from the new notebook order."""
    full = [page.page_id for page in project.pages]
    current = list(st.session_state.get("view_page_ids") or full)
    rank = {pid: i for i, pid in enumerate(full)}
    subset = [pid for pid in current if pid in rank]
    if not subset:
        subset = list(full)
    else:
        subset.sort(key=lambda pid: rank[pid])
    cover = project.cover_page_id
    if (
        cover
        and current
        and current[0] == cover
        and cover in subset
        and subset
        and subset[0] != cover
    ):
        subset = [cover] + [pid for pid in subset if pid != cover]
    root = str(paths.root)
    st.session_state["view_page_ids"] = subset
    st.session_state["view_entries"] = [{"page_id": pid, "project_root": root} for pid in subset]


def apply_reorder(projects: ProjectService, page_ids: Sequence[str], *, dirty: bool) -> str | None:
    """Permute notebook order. Returns an error message, or None on success/no-op."""
    if dirty:
        return _DIRTY_MSG
    try:
        updated = projects.reorder_pages(page_ids)
    except (JobConflictError, ProjectError, TranscribeError) as exc:
        return str(exc)
    bump_archive_generation(build_runtime_paths())
    sync_view_session_after_reorder(updated, paths=projects.paths)
    return None


def apply_move_to_date_cluster(
    projects: ProjectService, page_id: str, *, dirty: bool
) -> str | None:
    if dirty:
        return _DIRTY_MSG
    try:
        updated = projects.move_page_to_date_cluster(page_id)
    except (JobConflictError, ProjectError, TranscribeError) as exc:
        return str(exc)
    bump_archive_generation(build_runtime_paths())
    sync_view_session_after_reorder(updated, paths=projects.paths)
    return None


def render_move_controls(
    *,
    projects: ProjectService,
    page_id: str,
    key_prefix: str,
    dirty: bool = False,
) -> None:
    """Move up / down / to position. Uses notebook ``pages`` array order."""
    project = projects.load(reconcile=False)
    ids = [page.page_id for page in project.pages]
    if page_id not in ids:
        st.caption("This page is not in the notebook order.")
        return
    idx = ids.index(page_id)
    st.markdown("#### Page order")
    st.caption("Notebook order is the pages list, not the on-disk page folder number.")
    up_col, down_col = st.columns(2)
    with up_col:
        if st.button(
            "Move up",
            key=f"{key_prefix}_move_up",
            icon=ic.ARROW_UPWARD,
            width="stretch",
            disabled=idx == 0 or dirty,
            help=widget_help(
                _DIRTY_MSG if dirty else "Swap with the previous page in the notebook"
            ),
        ):
            err = apply_reorder(projects, permutation_move(ids, page_id, -1), dirty=dirty)
            if err:
                st.error(err)
            else:
                st.rerun()
    with down_col:
        if st.button(
            "Move down",
            key=f"{key_prefix}_move_down",
            icon=ic.ARROW_DOWNWARD,
            width="stretch",
            disabled=idx >= len(ids) - 1 or dirty,
            help=widget_help(_DIRTY_MSG if dirty else "Swap with the next page in the notebook"),
        ):
            err = apply_reorder(projects, permutation_move(ids, page_id, 1), dirty=dirty)
            if err:
                st.error(err)
            else:
                st.rerun()
    dest = st.number_input(
        "Move to position",
        min_value=1,
        max_value=len(ids),
        value=idx + 1,
        step=1,
        key=f"{key_prefix}_move_pos",
        disabled=dirty,
    )
    if st.button(
        "Move to position",
        key=f"{key_prefix}_move_pos_go",
        width="stretch",
        disabled=dirty or int(dest) == idx + 1,
    ):
        err = apply_reorder(projects, permutation_to_position(ids, page_id, int(dest)), dirty=dirty)
        if err:
            st.error(err)
        else:
            st.rerun()


def render_date_cluster_action(
    *,
    projects: ProjectService,
    page,
    project,
    key_prefix: str,
    dirty: bool = False,
) -> None:
    """Date-lane control when this page is a notebook-order date regression."""
    if page.date is None:
        return
    regs = projects.list_date_regressions(project)
    if not any(hit.page_id == page.page_id for hit in regs):
        return
    if st.button(
        "Move to date cluster",
        key=f"{key_prefix}_date_cluster",
        width="stretch",
        disabled=dirty,
        help=widget_help(
            _DIRTY_MSG
            if dirty
            else "Place this page after other confirmed pages with the same date"
        ),
    ):
        err = apply_move_to_date_cluster(projects, page.page_id, dirty=dirty)
        if err:
            st.error(err)
        else:
            st.rerun()


def inject_thumbs_reorder_island(page_ids: Sequence[str], *, key_prefix: str) -> None:
    """Optional HTML5-drag island. Numbered Move controls remain the product path."""
    order_key = f"{key_prefix}_dnd_order"
    if order_key not in st.session_state:
        st.session_state[order_key] = " ".join(page_ids)
    st.text_input(
        _ORDER_INPUT_LABEL,
        key=order_key,
        help=widget_help("Filled by drag-and-drop when the host allows it"),
        label_visibility="collapsed",
    )
    ids_js = ",".join(page_ids)
    st.iframe(
        f"""
<script>
(function () {{
  const parent = window.parent;
  if (!parent) return;
  const seed = {ids_js!r};
  const label = {_ORDER_INPUT_LABEL!r};
  function orderInput() {{
    const nodes = parent.document.querySelectorAll("input");
    for (const n of nodes) {{
      const aria = (n.getAttribute("aria-label") || "").trim();
      if (aria === label) return n;
    }}
    return null;
  }}
  function gridButtons() {{
    return Array.from(parent.document.querySelectorAll("button")).filter((b) => {{
      const cls = b.className || "";
      return cls.indexOf("st-key-tx_grid_open_") !== -1;
    }});
  }}
  let dragging = null;
  parent.document.addEventListener(
    "dragstart",
    function (e) {{
      const b = e.target && e.target.closest && e.target.closest("button");
      if (!b || gridButtons().indexOf(b) < 0) return;
      dragging = b;
      try {{ e.dataTransfer.setData("text/plain", "tx-page"); }} catch (err) {{}}
    }},
    true
  );
  parent.document.addEventListener("dragover", function (e) {{
    if (!dragging) return;
    const b = e.target && e.target.closest && e.target.closest("button");
    if (b && gridButtons().indexOf(b) >= 0) e.preventDefault();
  }}, true);
  parent.document.addEventListener("drop", function (e) {{
    const buttons = gridButtons();
    const b = e.target && e.target.closest && e.target.closest("button");
    if (!dragging || !b || buttons.indexOf(b) < 0) return;
    e.preventDefault();
    const from = buttons.indexOf(dragging);
    const to = buttons.indexOf(b);
    dragging = null;
    const ids = seed.split(",");
    if (from < 0 || to < 0 || from === to || ids.length !== buttons.length) return;
    const moved = ids.splice(from, 1)[0];
    ids.splice(to, 0, moved);
    const inp = orderInput();
    if (!inp) return;
    inp.value = ids.join(" ");
    inp.dispatchEvent(new Event("input", {{ bubbles: true }}));
    inp.dispatchEvent(new Event("change", {{ bubbles: true }}));
  }}, true);
  gridButtons().forEach((b) => {{ b.setAttribute("draggable", "true"); }});
}})();
</script>
        """,
        height=1,
    )


def render_thumbs_reorder_apply(
    *,
    projects: ProjectService,
    notebook_ids: Sequence[str],
    key_prefix: str,
    dirty: bool,
) -> None:
    """Read the hidden drag field and apply if it is a full permutation."""
    order_key = f"{key_prefix}_dnd_order"
    raw = str(st.session_state.get(order_key) or "")
    proposed = [part for part in raw.replace(",", " ").split() if part]
    if st.button(
        "Apply dragged order",
        key=f"{key_prefix}_dnd_apply",
        help=widget_help("Use numbered Move controls if drag does not apply"),
        disabled=dirty or proposed == list(notebook_ids) or not proposed,
    ):
        err = apply_reorder(projects, proposed, dirty=dirty)
        if err:
            st.error(err)
        else:
            st.rerun()
