"""Docs media guards: image links resolve, nothing is orphaned, budgets hold."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "docs" / "images"
_IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

PNG_BUDGET = 350 * 1024
GIF_BUDGET = 1024 * 1024


def _markdown_files() -> list[Path]:
    files = [ROOT / "README.md"]
    files += [p for p in (ROOT / "docs").rglob("*.md") if "_build" not in p.parts]
    return files


def _refs(path: Path) -> list[str]:
    return [m for m in _IMG.findall(path.read_text(encoding="utf-8")) if "://" not in m]


def test_markdown_image_links_resolve() -> None:
    missing: list[str] = []
    for md in _markdown_files():
        for ref in _refs(md):
            target = (md.parent / ref.split("#", 1)[0]).resolve()
            if not target.is_file():
                missing.append(f"{md.relative_to(ROOT)} -> {ref}")
    assert not missing, "broken image links:\n" + "\n".join(missing)


def test_every_docs_image_is_referenced() -> None:
    referenced: set[str] = set()
    for md in _markdown_files():
        for ref in _refs(md):
            referenced.add((md.parent / ref).resolve().name)
    orphans = sorted(p.name for p in IMAGES.iterdir() if p.is_file() and p.name not in referenced)
    assert not orphans, f"unreferenced docs images (delete or link them): {orphans}"


def test_docs_image_size_budgets() -> None:
    over: list[str] = []
    for path in IMAGES.iterdir():
        limit = GIF_BUDGET if path.suffix == ".gif" else PNG_BUDGET
        if path.stat().st_size > limit:
            over.append(f"{path.name}: {path.stat().st_size // 1024} KB > {limit // 1024} KB")
    assert not over, "\n".join(over)


def test_workflow_tour_is_in_the_hosted_nav() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    assert re.search(r"^workflows$", index, flags=re.MULTILINE)


def test_landing_page_images_exist() -> None:
    html = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'src="(images/[^"]+)"', html)
    assert refs, "landing page should show at least one still"
    for ref in refs:
        assert (ROOT / "website" / ref).is_file(), ref


def _load_seed():
    spec = importlib.util.spec_from_file_location(
        "seed_demo_workspace", ROOT / "scripts" / "docs" / "seed_demo_workspace.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seed_demo_workspace_builds_the_regression_the_gif_needs(tmp_path: Path) -> None:
    seed_mod = _load_seed()
    root = seed_mod.seed(tmp_path)
    from transcribe.ports import SystemClock, UuidGenerator
    from transcribe.services.project import ProjectService, open_project_paths

    svc = ProjectService(open_project_paths(root), clock=SystemClock(), ids=UuidGenerator())
    project = svc.load(reconcile=False)
    assert len(project.pages) == len(seed_mod.PAGES) == 6
    regressions = svc.list_date_regressions(project)
    assert len(regressions) == 1
    flagged = next(p for p in project.pages if p.page_id == regressions[0].page_id)
    assert flagged.review_status == "needs_attention"
    # Two OCR readings per page, so Review has evidence to compare.
    first = svc.load_page_result(project.pages[0].page_id)
    assert first is not None and len(first.attempts) == 2


def test_seed_refuses_to_overwrite(tmp_path: Path) -> None:
    seed_mod = _load_seed()
    seed_mod.seed(tmp_path)
    with pytest.raises(SystemExit):
        seed_mod.seed(tmp_path)
