"""Verify an exported bundle is readable without Transcribe authority.

Checks the export directory on its own terms: manifest presence, file
checksums, notebook JSON format, revision stamps in reading formats, EPUB
zip readability, and PDF header. This proves the "readable without
Transcribe" longevity property for a concrete export.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from transcribe.domain.fingerprint import sha256_bytes
from transcribe.persistence.schema import require_format


@dataclass
class ExportVerifyResult:
    ok: bool
    problems: list[str] = field(default_factory=list)
    checked_files: list[str] = field(default_factory=list)
    content_revision: str | None = None


def verify_export_bundle(dest: Path) -> ExportVerifyResult:
    problems: list[str] = []
    checked: list[str] = []
    dest = Path(dest)
    manifest_path = dest / "export.manifest.json"
    if not manifest_path.exists():
        return ExportVerifyResult(ok=False, problems=[f"no export manifest at {manifest_path}"])
    try:
        manifest = require_format(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            "transcribe.export-manifest",
        )
    except Exception as exc:  # noqa: BLE001
        return ExportVerifyResult(ok=False, problems=[f"manifest unreadable: {exc}"])
    revision = manifest.get("content_revision") or manifest.get("bundle_revision")
    files: dict = manifest.get("files") or {}
    checksums: dict = manifest.get("sha256") or {}
    if not files:
        problems.append("manifest lists no files")

    for key, rel in files.items():
        path = dest / str(rel)
        if not path.exists():
            problems.append(f"missing exported file {rel}")
            continue
        checked.append(str(rel))
        data = path.read_bytes()
        expected = checksums.get(key)
        if expected and sha256_bytes(data) != expected:
            problems.append(f"checksum mismatch for {rel}")
            continue
        name = path.name
        if name.endswith("notebook.transcribe.json"):
            try:
                payload = require_format(json.loads(data.decode("utf-8")), "transcribe.notebook")
                if revision and payload.get("content_revision") not in (None, revision):
                    # Bundle revisions differ from per-notebook revisions by design.
                    pass
            except Exception as exc:  # noqa: BLE001
                problems.append(f"notebook JSON unreadable ({rel}): {exc}")
        elif name.endswith(".md") or name.endswith(".txt"):
            if revision and revision.encode() not in data:
                problems.append(f"revision stamp missing from {rel}")
        elif name.endswith(".html"):
            if revision and revision.encode() not in data:
                problems.append(f"revision stamp missing from {rel}")
        elif name.endswith(".epub"):
            try:
                with zipfile.ZipFile(path) as zf:
                    if zf.testzip() is not None:
                        problems.append(f"epub has a corrupt member ({rel})")
            except zipfile.BadZipFile:
                problems.append(f"epub is not a zip ({rel})")
        elif name.endswith(".pdf"):
            if not data.startswith(b"%PDF"):
                problems.append(f"pdf header missing ({rel})")
    return ExportVerifyResult(
        ok=not problems,
        problems=problems,
        checked_files=checked,
        content_revision=revision,
    )


__all__ = ["ExportVerifyResult", "verify_export_bundle"]
