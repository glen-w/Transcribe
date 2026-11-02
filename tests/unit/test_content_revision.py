"""Notebook content_revision identity helpers."""

from __future__ import annotations

from transcribe.domain.content_revision import (
    CONTENT_REVISION_VERSION,
    build_content_revision_object,
    content_revision_from_pages,
    content_revision_hex,
)
from transcribe.domain.models import (
    GenerationOptions,
    OCRAttempt,
    OCRSettings,
    PageIndex,
    PageResult,
    Project,
)


def _project() -> Project:
    return Project(
        id="proj-1",
        title="T",
        created_at="t0",
        updated_at="t0",
        settings=OCRSettings(generation_options=GenerationOptions()),
        pages=[
            PageIndex(
                page_id="p1",
                source_id="s1",
                page_index=0,
                active_render_id="r1",
                width=10,
                height=10,
            )
        ],
    )


def _result(*, edited: str | None, raw: str) -> PageResult:
    return PageResult(
        page_id="p1",
        active_attempt_id="a1",
        edited_text=edited,
        attempts=[
            OCRAttempt(
                attempt_id="a1",
                status="succeeded",
                input_fingerprint="fp",
                fingerprint_payload={},
                raw_text=raw,
                provenance=None,
                provider_metadata={},
                started_at="t0",
                completed_at="t1",
            )
        ],
    )


def test_content_revision_from_pages_is_stable() -> None:
    pages = [
        {
            "page_id": "p1",
            "global_index": 0,
            "text": "hello",
            "edited": False,
            "status": "succeeded",
            "date": None,
            "date_approved": False,
            "date_source": None,
            "tags": [],
        }
    ]
    a = content_revision_from_pages(project_id="proj-1", pages=pages)
    b = content_revision_from_pages(project_id="proj-1", pages=list(pages))
    assert a == b
    assert len(a) == 64


def test_edit_changes_content_revision_hex() -> None:
    project = _project()
    raw_only = content_revision_hex(project, {"p1": _result(edited=None, raw="vision")})
    with_edit = content_revision_hex(project, {"p1": _result(edited="human", raw="vision")})
    assert raw_only != with_edit


def test_build_content_revision_object_marks_edited_and_version() -> None:
    project = _project()
    body = build_content_revision_object(project, {"p1": _result(edited="x", raw="y")})
    assert body["content_revision_version"] == CONTENT_REVISION_VERSION
    assert body["project_id"] == "proj-1"
    assert body["pages"][0]["edited"] is True
    assert body["pages"][0]["text"] == "x"
    assert body["pages"][0]["status"] == "succeeded"


def test_missing_page_result_is_pending_none_text() -> None:
    project = _project()
    body = build_content_revision_object(project, {})
    assert body["pages"][0]["status"] == "pending"
    assert body["pages"][0]["text"] is None
    assert body["pages"][0]["edited"] is False
