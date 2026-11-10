"""HTTP client for the local PaddleOCR-VL sidecar (layout + MLX recognizer)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from transcribe.domain.models import DEFAULT_VISION_NUM_PREDICT
from transcribe.errors import ProviderError
from transcribe.providers.base import DiscoveryResult, ModelInfo, ProviderResult
from transcribe.providers.ollama import (
    DEFAULT_MAX_RETRIES,
    call_with_retries,
    normalize_base_url,
)

DEFAULT_PADDLEOCR_MODEL = "PaddleOCR-VL-1.6"

_BLOCK_CONTENT_RE = re.compile(
    r"^content:\s*(.*?)(?=^#{5,}|\Z)",
    re.MULTILINE | re.DOTALL,
)


def plain_ocr_text(text: str) -> str:
    """Keep recognized page text; drop Paddle layout dumps and Result reprs."""
    raw = (text or "").strip()
    if not raw:
        return ""
    if "#################" in raw and "content:" in raw:
        parts = [match.group(1).strip() for match in _BLOCK_CONTENT_RE.finditer(raw)]
        parts = [part for part in parts if part]
        if parts:
            return "\n\n".join(parts)
    if "doc_preprocessor_res" in raw and "output_img" in raw:
        return ""
    stripped = raw.lstrip()
    if stripped.startswith("[{'input_path'") or stripped.startswith('[{"input_path"'):
        return ""
    return raw


class PaddleocrVisionProvider:
    """Loopback client for Nightshift ``paddle-probe`` pipeline HTTP.

    Does not import PaddlePaddle or MLX. The sidecar owns those runtimes.
    """

    provider_id = "paddleocr"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8112",
        *,
        request_timeout: float = 300.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.request_timeout = request_timeout
        self.max_retries = max_retries

    def healthcheck(self) -> None:
        payload = self._http_get("/health", timeout=min(10.0, self.request_timeout))
        if isinstance(payload, dict) and payload.get("ok") is False:
            raise ProviderError(
                "PaddleOCR sidecar is not ready",
                code="connection",
                retriable=True,
            )

    def list_models(self, *, refresh: bool = False) -> DiscoveryResult:
        del refresh
        try:
            payload = self._http_get("/health", timeout=min(10.0, self.request_timeout))
        except ProviderError as exc:
            return DiscoveryResult(models=[], error=str(exc))
        models: list[ModelInfo] = []
        rows = payload.get("models") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or not row.get("name"):
                    continue
                caps = row.get("capabilities")
                cap_list = [str(c) for c in caps] if isinstance(caps, list) else ["vision"]
                digest = row.get("digest")
                models.append(
                    ModelInfo(
                        name=str(row["name"]),
                        digest=str(digest) if digest else None,
                        capabilities=cap_list,
                        capability_known=True,
                    )
                )
        if not models and isinstance(payload, dict) and payload.get("model"):
            digest = payload.get("digest")
            models.append(
                ModelInfo(
                    name=str(payload["model"]),
                    digest=str(digest) if digest else None,
                    capabilities=["vision"],
                    capability_known=True,
                )
            )
        if not models:
            models.append(
                ModelInfo(
                    name=DEFAULT_PADDLEOCR_MODEL,
                    digest=None,
                    capabilities=["vision"],
                    capability_known=True,
                )
            )
        return DiscoveryResult(models=models, error=None)

    def list_vision_models(self, *, refresh: bool = False) -> DiscoveryResult:
        return self.list_models(refresh=refresh)

    def resolve_model_identity(self, model_name: str) -> tuple[str | None, bool]:
        result = self.list_models()
        want = (model_name or "").strip()
        for model in result.models:
            if model.name == want or model.name.endswith("/" + want):
                if model.digest:
                    return model.digest, True
                return want, True
        if want:
            return want, True
        return None, False

    def transcribe_image(
        self,
        *,
        model: str,
        prompt: str,
        image_bytes: bytes,
        options: dict[str, Any],
    ) -> ProviderResult:
        import base64

        gen_options = dict(options or {})
        if "num_predict" not in gen_options:
            gen_options["num_predict"] = DEFAULT_VISION_NUM_PREDICT
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        body = {
            "model": model,
            "prompt": prompt,
            "image_b64": image_b64,
            "options": gen_options,
        }
        digest, verified = self.resolve_model_identity(model)

        def once() -> dict[str, Any]:
            payload = self._http_post("/ocr", body, timeout=self.request_timeout)
            if not isinstance(payload, dict):
                raise ProviderError(
                    "PaddleOCR sidecar returned a non-object JSON response",
                    code="bad_response",
                )
            err = payload.get("error")
            if isinstance(err, str) and err.strip():
                raise ProviderError(err, code=str(payload.get("code") or "http_error"))
            text = payload.get("text")
            if not isinstance(text, str):
                raise ProviderError(
                    "PaddleOCR sidecar response missing text field",
                    code="bad_response",
                )
            payload["text"] = plain_ocr_text(text)
            return payload

        payload, attempt = call_with_retries(once, max_retries=self.max_retries)
        meta = {
            "retry_count": attempt,
            "path": payload.get("path"),
        }
        if payload.get("eval_count") is not None:
            meta["eval_count"] = payload.get("eval_count")
        return ProviderResult(
            text=str(payload["text"]),
            model=model,
            model_digest=digest or str(payload.get("digest") or ""),
            model_identity_verified=verified,
            provider_metadata=meta,
        )

    def abort_generate(self, model: str) -> None:
        del model
        return

    def _http_get(self, path: str, *, timeout: float) -> Any:
        return self._request("GET", path, None, timeout=timeout)

    def _http_post(self, path: str, body: dict[str, Any], *, timeout: float) -> Any:
        return self._request("POST", path, body, timeout=timeout)

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None, *, timeout: float
    ) -> Any:
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass
            message = err_body or str(exc)
            retriable = exc.code >= 500
            code = "http_error"
            if 400 <= exc.code < 500:
                retriable = False
            raise ProviderError(message, retriable=retriable, code=code) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                raise ProviderError(
                    "PaddleOCR sidecar request timed out",
                    retriable=False,
                    code="timeout",
                ) from exc
            raise ProviderError(
                f"Cannot reach PaddleOCR sidecar at {self.base_url}: {exc.reason}",
                retriable=True,
                code="connection",
            ) from exc
        except TimeoutError as exc:
            raise ProviderError(
                "PaddleOCR sidecar request timed out",
                retriable=False,
                code="timeout",
            ) from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "PaddleOCR sidecar returned non-JSON response",
                code="bad_response",
            ) from exc
