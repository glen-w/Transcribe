"""Coordinator: legacy sampler keys in stored digest must still skip (no re-OCR)."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from transcribe.domain.fingerprint import canonical_json_bytes
from transcribe.ingest import IngestService
from transcribe.services.job import JobCoordinator
from transcribe.services.project import ProjectService, open_project_paths
from tests.conftest import FakeClock, SequentialIds
from tests.fakes import FakeVisionOCRProvider
from tests.ingest.test_ingest import _png_bytes


def _legacy_digest_with_sampler_keys(payload: dict, **extra_opts) -> tuple[str, dict]:
    old = copy.deepcopy(payload)
    opts = dict(old.get("generation_options") or {})
    opts.update(extra_opts)
    old["generation_options"] = opts
    digest = hashlib.sha256(canonical_json_bytes(old)).hexdigest()
    return digest, old


def _project_with_one_page(tmp_path: Path):
    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds()
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("compat")
    ingest = IngestService(paths, clock=clock, ids=ids)
    ingest.import_bytes("p0.png", _png_bytes(color=(10, 20, 30)))
    project = projects.load()
    settings = project.settings
    settings.model_name = "fake-vision"
    projects.save_settings(project, settings)
    provider = FakeVisionOCRProvider(digest="digest-aaa", verified=True)
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    return paths, projects, coord, provider, project


def test_legacy_repeat_penalty_success_is_skipped_without_regenerate(tmp_path: Path):
    paths, projects, coord, provider, project = _project_with_one_page(tmp_path)
    page_id = project.pages[0].page_id
    progress = coord.run_blocking()
    assert progress.status == "completed"
    assert provider.calls == 1

    result = projects.load_page_result(page_id)
    assert result is not None
    attempt = result.active_attempt()
    assert attempt is not None and attempt.status == "succeeded"

    legacy_digest, legacy_payload = _legacy_digest_with_sampler_keys(
        attempt.fingerprint_payload, repeat_penalty=1.2, stop=["```\n```"]
    )
    attempt.input_fingerprint = legacy_digest
    attempt.fingerprint_payload = legacy_payload
    projects.record_generation(page_id, attempt, activate=True)

    progress2 = coord.run_blocking()
    assert provider.calls == 1
    assert progress2.skipped == 1


def test_prompt_change_still_reruns(tmp_path: Path):
    paths, projects, coord, provider, project = _project_with_one_page(tmp_path)
    coord.run_blocking()
    assert provider.calls == 1
    settings = projects.load().settings
    settings.custom_prompt = "Extract EXACTLY differently."
    projects.save_settings(projects.load(), settings)
    progress = coord.run_blocking()
    assert progress.skipped == 0
    assert provider.calls == 2
