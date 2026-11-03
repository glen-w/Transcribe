"""Read-only divergence of a later OCR reading from a human correction.

Uses the same Levenshtein character-error rate as the quality store. Changing
the threshold never rewrites page results. This is not an analysis module.
"""

from __future__ import annotations

from transcribe.domain.models import PageResult
from transcribe.services.quality import character_error_rate

DEFAULT_EDIT_DIVERGENCE_CER = 0.15


def edit_diverges(
    *,
    edited_text: str | None,
    raw_text: str | None,
    threshold: float = DEFAULT_EDIT_DIVERGENCE_CER,
) -> bool:
    """True when a succeeded reading is far from the saved correction."""
    edit = edited_text if edited_text is not None else None
    raw = raw_text if raw_text is not None else None
    if edit is None or not str(edit) or raw is None or not str(raw).strip():
        return False
    try:
        cut = float(threshold)
    except (TypeError, ValueError):
        cut = DEFAULT_EDIT_DIVERGENCE_CER
    if cut < 0:
        cut = 0.0
    cer = character_error_rate(str(edit), str(raw))
    if cer is None:
        return False
    return cer >= cut


def result_edit_diverges(
    result: PageResult | None,
    *,
    threshold: float = DEFAULT_EDIT_DIVERGENCE_CER,
) -> bool:
    if result is None or result.edited_text is None:
        return False
    attempt = result.active_attempt()
    if attempt is None or attempt.status != "succeeded":
        return False
    return edit_diverges(
        edited_text=result.edited_text,
        raw_text=attempt.raw_text,
        threshold=threshold,
    )
