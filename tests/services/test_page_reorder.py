"""Notebook page reorder permutes the pages array without renaming page_index."""

from __future__ import annotations

from pathlib import Path

import pytest

from transcribe.cli.notebook import dispatch_notebook
from transcribe.cli.parser import build_parser
from transcribe.domain.dates import ApproximateDate
from transcribe.domain.models import PageIndex
from transcribe.errors import JobConflictError, ProjectError
from transcribe.ingest import IngestService
from transcribe.persistence.locks import AnalysisLock, JobLock
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.project_dates import splice_page_after_date_cluster
from tests.conftest import FakeClock, SequentialIds
from tests.ingest.test_ingest import _png_bytes


def _page(
    page_id: str,
    page_index: int,
    *,
    date: ApproximateDate | None = None,
    approved: bool = True,
    source: str | None = None,
) -> PageIndex:
    return PageIndex(
        page_id=page_id,
        source_id="src",
        page_index=page_index,
        active_render_id=f"r-{page_id}",
        width=10,
        height=10,
        date=date,
        date_approved=approved,
        date_source=source,
    )


def _svc(tmp_path: Path, n_pages: int = 3) -> tuple[ProjectService, list[str], dict[str, int]]:
    paths = open_project_paths(tmp_path / "nb")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("Reorder")
    ingest = IngestService(paths, clock=clock, ids=ids)
    project = None
    for i in range(n_pages):
        project = ingest.import_bytes(f"{i}.png", _png_bytes(color=(i + 1, i + 1, i + 1)))
    assert project is not None
    page_ids = [page.page_id for page in project.pages]
    indexes = {page.page_id: page.page_index for page in project.pages}
    return projects, page_ids, indexes


def test_splice_inserts_after_confirmed_same_date_cluster() -> None:
    d = ApproximateDate(2026, 5, 23)
    pages = [
        _page("a", 0, date=ApproximateDate(2026, 1, 1)),
        _page("b", 1, date=d),
        _page("c", 2, date=d),
        _page("p", 3, date=d),
        _page("e", 4, date=ApproximateDate(2026, 6, 1)),
    ]
    out = splice_page_after_date_cluster(pages, "p")
    assert [p.page_id for p in out] == ["a", "b", "c", "p", "e"]
    assert [p.page_index for p in out] == [0, 1, 2, 3, 4]


def test_splice_chronological_when_no_cluster() -> None:
    pages = [
        _page("jan", 0, date=ApproximateDate(2026, 1, 1)),
        _page("mar", 1, date=ApproximateDate(2026, 3, 1)),
        _page("feb", 2, date=ApproximateDate(2026, 2, 1)),
        _page("dec", 3, date=ApproximateDate(2026, 12, 1)),
    ]
    out = splice_page_after_date_cluster(pages, "feb")
    assert [p.page_id for p in out] == ["jan", "feb", "mar", "dec"]


def test_splice_already_last_of_cluster_is_stable() -> None:
    d = ApproximateDate(2026, 5, 1)
    pages = [
        _page("a", 0, date=d),
        _page("b", 1, date=d),
        _page("c", 2, date=ApproximateDate(2026, 6, 1)),
    ]
    out = splice_page_after_date_cluster(pages, "b")
    assert [p.page_id for p in out] == ["a", "b", "c"]


def test_splice_refuses_undated() -> None:
    pages = [_page("a", 0, date=ApproximateDate(2026, 1, 1)), _page("u", 1, date=None)]
    with pytest.raises(ProjectError, match="undated"):
        splice_page_after_date_cluster(pages, "u")


def test_reorder_pages_permutes_order_not_page_index(tmp_path: Path) -> None:
    projects, ids, indexes = _svc(tmp_path)
    reversed_ids = list(reversed(ids))
    before = projects.load(reconcile=False)
    render_paths = {
        page.page_id: before.renders[page.active_render_id].image_relpath for page in before.pages
    }
    rev_before = projects.content_revision(before)

    updated = projects.reorder_pages(reversed_ids)
    assert [p.page_id for p in updated.pages] == reversed_ids
    for page in updated.pages:
        assert page.page_index == indexes[page.page_id]
        rel = updated.renders[page.active_render_id].image_relpath
        assert rel == render_paths[page.page_id]
        assert projects.paths.resolve_contained(rel).is_file()
    assert projects.content_revision(updated) != rev_before


def test_reorder_pages_refuses_bad_permutations_and_noop(tmp_path: Path) -> None:
    projects, ids, _indexes = _svc(tmp_path, n_pages=2)
    with pytest.raises(ProjectError, match="empty"):
        projects.reorder_pages([])
    with pytest.raises(ProjectError, match="duplicate"):
        projects.reorder_pages([ids[0], ids[0]])
    with pytest.raises(ProjectError, match="exactly once"):
        projects.reorder_pages([ids[0]])
    same = projects.reorder_pages(ids)
    assert [p.page_id for p in same.pages] == ids


def test_reorder_pages_refuses_ocr_and_analysis_locks(tmp_path: Path) -> None:
    projects, ids, _indexes = _svc(tmp_path, n_pages=2)
    flipped = list(reversed(ids))
    held = JobLock(projects.paths.job_lock)
    assert held.try_acquire()
    try:
        with pytest.raises(JobConflictError, match="OCR job"):
            projects.reorder_pages(flipped)
    finally:
        held.release()
    analysis = AnalysisLock(projects.paths.analysis_lock)
    assert analysis.try_acquire()
    try:
        with pytest.raises(JobConflictError, match="analysis job"):
            projects.reorder_pages(flipped)
    finally:
        analysis.release()


def test_move_page_to_date_cluster_happy_and_edges(tmp_path: Path) -> None:
    projects, ids, indexes = _svc(tmp_path, n_pages=4)
    a, b, c, p = ids
    projects.approve_page_date(a, ApproximateDate(2026, 1, 1))
    projects.approve_page_date(b, ApproximateDate(2026, 5, 23))
    projects.approve_page_date(c, ApproximateDate(2026, 5, 23))
    projects.approve_page_date(p, ApproximateDate(2026, 5, 23))
    updated = projects.move_page_to_date_cluster(p)
    assert [page.page_id for page in updated.pages] == [a, b, c, p]
    for page in updated.pages:
        assert page.page_index == indexes[page.page_id]

    again = projects.move_page_to_date_cluster(p)
    assert [page.page_id for page in again.pages] == [a, b, c, p]

    with pytest.raises(ProjectError, match="unknown"):
        projects.move_page_to_date_cluster("missing")
    projects.approve_page_date(a, None)
    with pytest.raises(ProjectError, match="undated"):
        projects.move_page_to_date_cluster(a)


def test_move_page_to_date_cluster_chronological_without_cluster(tmp_path: Path) -> None:
    projects, ids, _indexes = _svc(tmp_path, n_pages=4)
    jan, mar, feb, dec = ids
    projects.approve_page_date(jan, ApproximateDate(2026, 1, 1))
    projects.approve_page_date(mar, ApproximateDate(2026, 3, 1))
    projects.approve_page_date(feb, ApproximateDate(2026, 2, 1))
    projects.approve_page_date(dec, ApproximateDate(2026, 12, 1))
    updated = projects.move_page_to_date_cluster(feb)
    assert [page.page_id for page in updated.pages] == [jan, feb, mar, dec]


def test_cli_pages_reorder(tmp_path: Path, capsys) -> None:
    projects, ids, _indexes = _svc(tmp_path, n_pages=2)
    parser = build_parser()
    flipped = list(reversed(ids))
    args = parser.parse_args(["pages", "reorder", str(projects.paths.root), *flipped])
    assert dispatch_notebook(args, clock=projects.clock, ids=projects.ids) == 0
    out = capsys.readouterr().out.strip().split()
    assert out == flipped
    loaded = projects.load(reconcile=False)
    assert [p.page_id for p in loaded.pages] == flipped


def test_permutation_move_and_position() -> None:
    from transcribe.ui.page_reorder import permutation_move, permutation_to_position

    ids = ["a", "b", "c"]
    assert permutation_move(ids, "b", -1) == ["b", "a", "c"]
    assert permutation_move(ids, "a", -1) == ["a", "b", "c"]
    assert permutation_move(ids, "c", 1) == ["a", "b", "c"]
    assert permutation_to_position(ids, "c", 1) == ["c", "a", "b"]
    assert permutation_to_position(ids, "a", 1) == ["a", "b", "c"]
    with pytest.raises(ProjectError, match="unknown"):
        permutation_move(ids, "z", 1)
