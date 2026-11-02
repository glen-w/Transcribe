"""Analysis unit-id helpers (page_v1 vs paragraph_v1 spans).

Host-agnostic: View row-shaping and product views must not own this mapping.
"""

from __future__ import annotations


def page_id_from_unit_id(unit_id: str | None) -> str | None:
    """Map analysis ``unit_id`` to a notebook ``page_id``.

    page_v1 unit ids equal page ids; paragraph_v1 uses ``{page_id}/span:…``.
    """
    if not isinstance(unit_id, str) or not unit_id:
        return None
    if "/span:" in unit_id:
        return unit_id.split("/span:", 1)[0] or None
    return unit_id
