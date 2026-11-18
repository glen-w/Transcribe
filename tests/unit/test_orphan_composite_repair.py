from __future__ import annotations

import json
from pathlib import Path

from transcribe.domain.models import OCRAttempt, PageResult
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds


def test_repair_orphan_composite_drops_broken_row(tmp_path: Path) -> None:
    paths = open_project_paths(tmp_path / "nb")
    projects = ProjectService(paths, clock=FakeClock(), ids=SequentialIds())
    page_id = "page1"
    orphan = OCRAttempt(
        attempt_id="c1",
        status="succeeded",
        input_fingerprint="fp",
        fingerprint_payload={},
        raw_text="merged",
        provenance=None,
        provider_metadata={},
        started_at="t0",
        completed_at="t1",
        attempt_kind="composite",
        source_attempt_ids=["missing-vision"],
    )
    result = PageResult(
        page_id=page_id,
        active_attempt_id="c1",
        attempts=[orphan],
    )
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    paths.result_path(page_id).write_text(
        json.dumps(result.as_dict()), encoding="utf-8"
    )

    fixed = projects.repair_orphan_composite_sources(page_id)
    assert fixed is not None
    loaded = projects.load_page_result(page_id)
    assert loaded is not None
    assert loaded.attempts == []
    assert loaded.active_attempt_id is None