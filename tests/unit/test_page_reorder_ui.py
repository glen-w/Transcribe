"""Contracts for Review / thumbnail page-order controls."""

from __future__ import annotations

from pathlib import Path

REVIEW = Path("src/transcribe/ui/review_workbench.py").read_text(encoding="utf-8")
THUMBS = Path("src/transcribe/ui/thumbnails_view.py").read_text(encoding="utf-8")
REORDER = Path("src/transcribe/ui/page_reorder.py").read_text(encoding="utf-8")


def test_review_wires_move_controls_and_date_cluster() -> None:
    assert "render_move_controls" in REVIEW
    assert "render_date_cluster_action" in REVIEW
    assert "allow_reorder=True" in REVIEW
    assert "_is_dirty(page_id)" in REVIEW


def test_thumbs_reorder_only_when_allowed() -> None:
    assert "allow_reorder: bool = False" in THUMBS
    assert "inject_thumbs_reorder_island" in THUMBS
    assert "render_thumbs_reorder_apply" in THUMBS


def test_reading_viewer_does_not_enable_reorder() -> None:
    viewer = Path("src/transcribe/ui/page_viewer.py").read_text(encoding="utf-8")
    assert "allow_reorder=True" not in viewer


def test_reorder_island_is_optional_and_offline() -> None:
    assert "inject_thumbs_reorder_island" in REORDER
    assert "Apply dragged order" in REORDER
    assert "cdn" not in REORDER.lower()
    assert "_DIRTY_MSG" in REORDER
    assert "Save or discard unsaved Review text" in REORDER


def test_icons_include_up_down() -> None:
    from transcribe.ui import icons as ic

    assert "arrow_upward" in ic.ARROW_UPWARD
    assert "arrow_downward" in ic.ARROW_DOWNWARD
