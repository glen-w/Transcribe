"""1.2 expansion services: saved searches, collections, quality, custom fonts."""

from __future__ import annotations

from pathlib import Path

import pytest

from transcribe.domain.dates import ApproximateDate
from transcribe.persistence.schema import SUPPORTED
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.archive import ArchiveFilters
from transcribe.services.collections import NotebookCollectionsStore
from transcribe.services.custom_fonts import list_custom_fonts, register_custom_font
from transcribe.services.quality import (
    QualityRatingStore,
    character_error_rate,
    edit_distance,
    sample_page_ids,
)
from transcribe.services.saved_searches import SavedSearchStore
from transcribe.domain.models import PageIndex, Project, OCRSettings
from tests.conftest import FakeClock, SequentialIds


def _runtime(tmp_path: Path) -> RuntimePaths:
    runtime = RuntimePaths(
        repo_root=tmp_path,
        data_dir=tmp_path / "data",
        projects_dir=tmp_path / "data" / "projects",
        inbox_dir=tmp_path / "data" / "inbox",
        export_dir=tmp_path / "data" / "exports",
    )
    runtime.ensure_layout()
    return runtime


def test_formats_registered():
    for fmt in (
        "transcribe.saved-searches",
        "transcribe.notebook-collections",
        "transcribe.quality-ratings",
    ):
        assert SUPPORTED[fmt] == 1


def test_saved_search_roundtrip_and_name_update(tmp_path: Path):
    runtime = _runtime(tmp_path)
    store = SavedSearchStore(runtime, clock=FakeClock(), ids=SequentialIds("s"))
    filters = ArchiveFilters(
        period="range",
        range_start=ApproximateDate(2020, 1, 1),
        range_end=ApproximateDate(2020, 12, 31),
        tags=("diary",),
        people=("Anna",),
        places=("Paris",),
        include_archived=True,
        collection_id="col-1",
    )
    saved = store.upsert("Anna in Paris", query="travel", order="newest", filters=filters)
    loaded = store.get(saved.search_id)
    assert loaded is not None
    assert loaded.filters.people == ("Anna",)
    assert loaded.filters.places == ("Paris",)
    assert loaded.filters.range_start == ApproximateDate(2020, 1, 1)
    assert loaded.filters.collection_id == "col-1"

    updated = store.upsert("anna in paris", query="changed")
    assert updated.search_id == saved.search_id
    assert len(store.list()) == 1
    assert store.delete(saved.search_id) is True
    assert store.list() == []


def test_saved_search_malformed_fails_closed(tmp_path: Path):
    runtime = _runtime(tmp_path)
    path = runtime.data_dir / "config" / "saved-searches.json"
    path.write_text('{"format": "nope", "schema_version": 1}', encoding="utf-8")
    with pytest.raises(Exception):
        SavedSearchStore(runtime).list()


def test_collections_lifecycle_and_archive(tmp_path: Path):
    runtime = _runtime(tmp_path)
    store = NotebookCollectionsStore(runtime, clock=FakeClock(), ids=SequentialIds("c"))
    created = store.create("Shelf A", project_ids=("nb1",))
    with pytest.raises(ValueError):
        store.create("shelf a")
    store.assign(created.collection_id, "nb2")
    state = store.load()
    assert state.collections_for("nb2")[0].collection_id == created.collection_id
    store.set_archived("nb1", archived=True)
    assert store.load().is_archived("nb1") is True
    store.set_archived("nb1", archived=False)
    assert store.load().is_archived("nb1") is False
    renamed = store.rename(created.collection_id, "Shelf B")
    assert renamed.name == "Shelf B"
    assert store.delete(created.collection_id) is True
    assert store.load().collections == ()


def test_collections_malformed_fails_closed(tmp_path: Path):
    runtime = _runtime(tmp_path)
    path = runtime.data_dir / "config" / "notebook-collections.json"
    path.write_text('{"format": "transcribe.notebook-collections", "schema_version": 99}',
                     encoding="utf-8")
    with pytest.raises(Exception):
        NotebookCollectionsStore(runtime).load()


def test_quality_ratings_and_cer(tmp_path: Path):
    runtime = _runtime(tmp_path)
    store = QualityRatingStore(runtime, clock=FakeClock(), ids=SequentialIds("q"))
    rating = store.record_ocr_sample(
        project_id="nb1",
        page_id="p1",
        ocr_text="helo wrld",
        reviewed_text="hello world",
    )
    assert rating.verdict == "edit"
    assert rating.cer is not None and rating.cer > 0
    store.record("cleanup", "accept", project_id="nb1")
    store.record("cleanup", "reject", project_id="nb1")
    store.record("analysis", "up", project_id="nb1", module_id="stats")
    with pytest.raises(ValueError):
        store.record("analysis", "accept", project_id="nb1")
    summary = store.summary(project_id="nb1")
    assert summary["total"] == 4
    assert summary["ocr_samples"] == 1
    assert summary["cleanup_acceptance"] == 0.5
    assert summary["analysis_up_ratio"] == 1.0

    assert edit_distance("kitten", "sitting") == 3
    assert character_error_rate("abcd", "abce") == 0.25
    assert character_error_rate("", "x") is None


def test_sample_page_ids_deterministic():
    project = Project(
        id="nb",
        title="t",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        settings=OCRSettings(),
        pages=[
            PageIndex(
                page_id=f"p{i}",
                source_id="s",
                page_index=i,
                active_render_id="r",
                width=10,
                height=10,
            )
            for i in range(10)
        ],
    )
    assert sample_page_ids(project, 3) == ["p0", "p3", "p6"]
    assert sample_page_ids(project, 0) == []
    assert len(sample_page_ids(project, 99)) == 10


def test_custom_font_registration(tmp_path: Path):
    runtime = _runtime(tmp_path)
    key = register_custom_font("My Hand", b"fake-font-bytes", suffix=".ttf", runtime=runtime)
    assert key == "custom:My Hand"
    assert list_custom_fonts(runtime) == ["my-hand.ttf"]
    with pytest.raises(ValueError):
        register_custom_font("Bad", b"x", suffix=".exe", runtime=runtime)
    with pytest.raises(ValueError):
        register_custom_font("Empty", b"", suffix=".ttf", runtime=runtime)
