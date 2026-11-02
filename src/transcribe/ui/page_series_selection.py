"""Parse Altair/Vega point selections from clickable page-series charts."""

from __future__ import annotations

from transcribe.analysis.units import page_id_from_unit_id

PAGE_SELECT = "page_select"

__all__ = ["PAGE_SELECT", "page_id_from_unit_id", "selected_page_id"]


def selected_page_id(event: object) -> str | None:
    """Extract the clicked ``page_id`` from an Altair ``on_select`` event."""
    if event is None:
        return None
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if selection is None:
        return None
    points = None
    if isinstance(selection, dict):
        points = selection.get(PAGE_SELECT)
    else:
        points = getattr(selection, PAGE_SELECT, None)
        if points is None and hasattr(selection, "get"):
            points = selection.get(PAGE_SELECT)
    if not points or isinstance(points, dict):
        return None
    if not isinstance(points, (list, tuple)):
        return None
    first = points[0] if points else None
    if not isinstance(first, dict):
        return None
    page_id = first.get("page_id")
    return str(page_id) if page_id else None
