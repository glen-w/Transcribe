from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from transcribe.errors import ProviderError
from transcribe.providers.factory import build_vision_provider, normalize_provider_id
from transcribe.providers.paddleocr import PaddleocrVisionProvider, plain_ocr_text


class _Resp:
    def __init__(self, payload: dict, code: int = 200):
        self._payload = payload
        self.code = code

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_plain_ocr_text_strips_layout_dump() -> None:
    dump = (
        "#################\n"
        "label:\ttext\n"
        "bbox:\t[1, 202, 1499, 796]\n"
        "content:\tflooding into the perceived vacuum when\n"
        "really I could do with a week to settle.\n"
        "#################\n\n"
        "#################\n"
        "label:\theader\n"
        "bbox:\t[0, 190, 824, 289]\n"
        "content:\t251106 1729 Aux Ours\n"
        "#################\n"
    )
    assert plain_ocr_text(dump) == (
        "flooding into the perceived vacuum when\n"
        "really I could do with a week to settle.\n\n"
        "251106 1729 Aux Ours"
    )


def test_plain_ocr_text_keeps_faithful_page() -> None:
    page = "Monday went well — coffee at Aut Day."
    assert plain_ocr_text(page) == page


def test_plain_ocr_text_drops_result_repr() -> None:
    dump = (
        "[{'input_path': '/tmp/paddleocr-abc.png', 'page_index': None, "
        "'doc_preprocessor_res': {'output_img': array([[[4, 0, 0]]])}}]"
    )
    assert plain_ocr_text(dump) == ""


def test_ocr_strips_layout_dump_from_sidecar() -> None:
    dump = (
        "#################\nlabel:\ttext\nbbox:\t[0, 1, 2, 3]\n"
        "content:\thello page\n#################\n"
    )

    def fake_urlopen(req, timeout=None):
        if req.full_url.endswith("/health"):
            return _Resp({"ok": True, "model": "PaddleOCR-VL-1.6", "digest": "d"})
        if req.full_url.endswith("/ocr"):
            return _Resp({"text": dump, "path": "pipeline", "digest": "d"})
        raise AssertionError(req.full_url)

    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        out = provider.transcribe_image(
            model="PaddleOCR-VL-1.6",
            prompt="OCR:",
            image_bytes=b"\x89PNG",
            options={},
        )
    assert out.text == "hello page"


def test_normalize_provider_aliases() -> None:
    assert normalize_provider_id(None) == "ollama"
    assert normalize_provider_id("paddle") == "paddleocr"
    assert normalize_provider_id("mlx") == "paddleocr"
    assert normalize_provider_id("PaddleOCR") == "paddleocr"


def test_factory_default_is_ollama() -> None:
    from transcribe.providers.ollama import OllamaVisionProvider

    provider = build_vision_provider("ollama", "http://127.0.0.1:11434")
    assert isinstance(provider, OllamaVisionProvider)
    assert provider.provider_id == "ollama"


def test_factory_paddleocr() -> None:
    provider = build_vision_provider("paddleocr", "http://127.0.0.1:8112")
    assert isinstance(provider, PaddleocrVisionProvider)
    assert provider.provider_id == "paddleocr"
    assert provider.base_url == "http://127.0.0.1:8112"


def test_factory_unknown_raises() -> None:
    with pytest.raises(ProviderError) as exc:
        build_vision_provider("litellm", "http://127.0.0.1:1")
    assert exc.value.code == "provider_unknown"


def test_healthcheck_and_ocr(monkeypatch) -> None:
    calls: list[str] = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        calls.append(url)
        if url.endswith("/health"):
            return _Resp(
                {
                    "ok": True,
                    "model": "PaddlePaddle/PaddleOCR-VL-1.6",
                    "digest": "PaddlePaddle/PaddleOCR-VL-1.6",
                    "models": [
                        {
                            "name": "PaddlePaddle/PaddleOCR-VL-1.6",
                            "digest": "abc",
                            "capabilities": ["vision"],
                        }
                    ],
                }
            )
        if url.endswith("/ocr"):
            body = json.loads(req.data.decode())
            assert "image_b64" in body
            assert body["prompt"] == "OCR:"
            return _Resp({"text": "hello page", "path": "pipeline", "digest": "abc"})
        raise AssertionError(url)

    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.healthcheck()
        result = provider.list_models()
        assert result.models[0].name == "PaddlePaddle/PaddleOCR-VL-1.6"
        out = provider.transcribe_image(
            model="PaddleOCR-VL-1.6",
            prompt="OCR:",
            image_bytes=b"\x89PNG",
            options={"num_predict": 64},
        )
        assert out.text == "hello page"
        assert out.provider_metadata.get("path") == "pipeline"
        assert out.model_identity_verified is True


def test_seal_provider_rebuilds_paddleocr_on_url_change() -> None:
    from transcribe.services.job import JobCoordinator

    coord = JobCoordinator.__new__(JobCoordinator)
    start = PaddleocrVisionProvider("http://127.0.0.1:8112")
    plan = type("Plan", (), {"base_url": "http://127.0.0.1:8113", "provider_id": "paddleocr"})()
    sealed = JobCoordinator._seal_provider(coord, plan, start)
    assert isinstance(sealed, PaddleocrVisionProvider)
    assert sealed.base_url == "http://127.0.0.1:8113"
    assert sealed is not start


def test_run_blocking_paddleocr_persists_fingerprint(tmp_path) -> None:
    from tests.conftest import FakeClock, SequentialIds
    from tests.ingest.test_ingest import _png_bytes
    from transcribe.ingest import IngestService
    from transcribe.services.job import JobCoordinator
    from transcribe.services.project import ProjectService, open_project_paths

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        if url.endswith("/health"):
            return _Resp(
                {
                    "ok": True,
                    "model": "PaddleOCR-VL-1.6",
                    "digest": "paddle-digest",
                    "models": [
                        {
                            "name": "PaddleOCR-VL-1.6",
                            "digest": "paddle-digest",
                            "capabilities": ["vision"],
                        }
                    ],
                }
            )
        if url.endswith("/ocr"):
            return _Resp(
                {"text": "stub paddle page", "path": "pipeline", "digest": "paddle-digest"}
            )
        raise AssertionError(url)

    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds("pad")
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("pad")
    IngestService(paths, clock=clock, ids=ids).import_bytes("page.png", _png_bytes())
    project = projects.load()
    settings = project.settings
    settings.model_name = "PaddleOCR-VL-1.6"
    settings.base_url = "http://127.0.0.1:8112"
    projects.save_settings(project, settings)
    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        progress = coord.run_blocking(force=True)
    assert progress.status == "completed"
    page = projects.load().pages[0]
    result = projects.load_page_result(page.page_id)
    assert result is not None
    assert result.status == "succeeded"
    attempt = result.active_attempt()
    assert attempt is not None
    assert attempt.raw_text == "stub paddle page"
    assert attempt.fingerprint_payload.get("provider") == "paddleocr"
    assert "path" not in (attempt.fingerprint_payload or {})
    assert attempt.provider_metadata.get("path") == "pipeline"
    assert "pipeline_error" not in attempt.provider_metadata
    assert attempt.provenance is not None
    assert attempt.provenance.recipe_id == "paddleocr_vl"
    assert attempt.provenance.prompt_text.strip() == "OCR:"


def test_fingerprint_provider_separates_paddle_from_ollama() -> None:
    from transcribe.domain.fingerprint import compute_input_fingerprint

    kwargs = dict(
        model_name="PaddleOCR-VL-1.6",
        model_digest="d",
        model_identity_verified=True,
        input_sha256="a" * 64,
        prompt_sha256="b" * 64,
        preprocess_profile="none",
        preprocess_version=1,
        generation_options={"temperature": 0.0},
    )
    paddle, _ = compute_input_fingerprint(provider="paddleocr", **kwargs)
    ollama, _ = compute_input_fingerprint(provider="ollama", **kwargs)
    assert paddle != ollama


def test_abort_generate_is_noop() -> None:
    PaddleocrVisionProvider("http://127.0.0.1:8112").abort_generate("PaddleOCR-VL-1.6")


def test_run_blocking_empty_layout_dump_is_empty_output(tmp_path) -> None:
    from tests.conftest import FakeClock, SequentialIds
    from tests.ingest.test_ingest import _png_bytes
    from transcribe.ingest import IngestService
    from transcribe.services.job import JobCoordinator
    from transcribe.services.project import ProjectService, open_project_paths

    dump = (
        "[{'input_path': '/tmp/paddleocr-abc.png', 'page_index': None, "
        "'doc_preprocessor_res': {'output_img': 'array(...)'}}]"
    )

    def fake_urlopen(req, timeout=None):
        if req.full_url.endswith("/health"):
            return _Resp(
                {
                    "ok": True,
                    "model": "PaddleOCR-VL-1.6",
                    "digest": "paddle-digest",
                    "models": [
                        {
                            "name": "PaddleOCR-VL-1.6",
                            "digest": "paddle-digest",
                            "capabilities": ["vision"],
                        }
                    ],
                }
            )
        if req.full_url.endswith("/ocr"):
            return _Resp({"text": dump, "path": "pipeline", "digest": "paddle-digest"})
        raise AssertionError(req.full_url)

    paths = open_project_paths(tmp_path / "proj")
    clock, ids = FakeClock(), SequentialIds("pade")
    projects = ProjectService(paths, clock=clock, ids=ids)
    projects.create("pade")
    IngestService(paths, clock=clock, ids=ids).import_bytes("page.png", _png_bytes())
    project = projects.load()
    settings = project.settings
    settings.model_name = "PaddleOCR-VL-1.6"
    settings.base_url = "http://127.0.0.1:8112"
    projects.save_settings(project, settings)
    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    coord = JobCoordinator(paths, projects, provider, clock=clock, ids=ids)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        progress = coord.run_blocking(force=True)
    assert progress.status == "completed"
    assert progress.failed == 1
    result = projects.load_page_result(projects.load().pages[0].page_id)
    assert result is not None
    attempt = result.attempts[-1]
    assert attempt.status == "failed"
    assert attempt.error is not None
    assert attempt.error.code == "empty_output"
    assert (attempt.raw_text or "") == ""


def test_ocr_sidecar_error_payload() -> None:
    def fake_urlopen(req, timeout=None):
        if req.full_url.endswith("/health"):
            return _Resp({"ok": True, "model": "PaddleOCR-VL-1.6", "digest": "d"})
        if req.full_url.endswith("/ocr"):
            return _Resp({"error": "layout failed", "code": "pipeline"})
        raise AssertionError(req.full_url)

    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(ProviderError) as exc:
            provider.transcribe_image(
                model="PaddleOCR-VL-1.6",
                prompt="OCR:",
                image_bytes=b"\x89PNG",
                options={},
            )
        assert exc.value.code == "pipeline"


def test_http_4xx_not_retriable() -> None:
    import io
    import urllib.error
    from email.message import Message

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 400, "bad", hdrs=Message(), fp=io.BytesIO(b"nope")
        )

    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(ProviderError) as exc:
            provider.healthcheck()
        assert exc.value.code == "http_error"
        assert exc.value.retriable is False


def test_connection_error() -> None:
    import urllib.error

    def boom(req, timeout=None):
        raise urllib.error.URLError("refused")

    provider = PaddleocrVisionProvider("http://127.0.0.1:8112")
    with patch("urllib.request.urlopen", side_effect=boom):
        with pytest.raises(ProviderError) as exc:
            provider.healthcheck()
        assert exc.value.code == "connection"
        assert exc.value.retriable is True
