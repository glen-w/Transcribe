#!/usr/bin/env python3
"""Capture documentation screenshots and workflow GIFs from the real UI.

Reproducible and offline: seeds a throwaway workspace with a synthetic notebook
(``seed_demo_workspace.py``), starts the Streamlit app on port 8510 (never 8501),
drives it with Playwright, then stops only the server it started. No OCR runs.

Usage:
    python scripts/docs/capture_docs_media.py                 # everything
    python scripts/docs/capture_docs_media.py --only home,review-transcription
    python scripts/docs/capture_docs_media.py --no-gifs

Requires: playwright (``pip install playwright && playwright install chromium``) and a
local Ollama (only so Home/Transcribe show the "reachable" state; nothing is generated).
Override the browser binary with ``PLAYWRIGHT_CHROMIUM_EXECUTABLE``.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed_demo_workspace import seed  # noqa: E402

PORT = 8510
URL = f"http://127.0.0.1:{PORT}/"
VIEWPORT = {"width": 1440, "height": 1000}
OLLAMA = os.environ.get("TRANSCRIBE_OLLAMA_BASE_URL_DOCS", "http://localhost:11434")


# ── browser plumbing ────────────────────────────────────────────────────────


def _chromium_exe() -> str | None:
    env = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if env:
        return env
    # Newer headless shells run on current macOS where older bundled builds may not.
    cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    hits = sorted(
        glob.glob(str(cache / "chromium_headless_shell-*" / "*" / "chrome-headless-shell"))
    )
    return hits[-1] if hits else None


def settle(pg, extra_ms: int = 700) -> None:
    """Wait for Streamlit to finish rerunning and for images to paint."""
    pg.wait_for_timeout(350)
    try:
        pg.wait_for_function(
            "!document.querySelector('[data-testid=stStatusWidget]')", timeout=25000
        )
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(extra_ms)


def open_app(pg) -> None:
    pg.goto(URL)
    pg.wait_for_selector("[data-testid=stApp]")
    pg.add_style_tag(
        content="header[data-testid=stHeader]{visibility:hidden}"
        "[data-testid=stToolbar]{display:none}"
    )
    settle(pg, 4500)  # first paint fades the sidebar in


def sidebar(pg):
    return pg.locator("section[data-testid=stSidebar]")


def main_area(pg):
    return pg.locator("[data-testid=stMain]")


def nav(pg, label: str) -> None:
    sidebar(pg).get_by_role("button", name=label, exact=True).first.click()
    settle(pg, 1200)


def open_review(pg) -> None:
    main_area(pg).get_by_role("button", name=re.compile(r"Review$")).first.click()
    settle(pg, 1500)


def lane(pg, label: str) -> None:
    main_area(pg).get_by_text(label, exact=True).first.click()
    settle(pg, 900)


def pick_queue(pg, label_re: str) -> None:
    main_area(pg).locator("[data-testid=stSelectbox]").first.click()
    pg.get_by_role("option", name=re.compile(label_re)).first.click()
    settle(pg, 1200)


# ── static shots ────────────────────────────────────────────────────────────


class Ctx:
    def __init__(self, out: Path, pg) -> None:
        self.out, self.pg = out, pg

    def shot(self, name: str, *, height: int | None = None) -> None:
        dest = self.out / f"{name}.png"
        if height:
            self.pg.set_viewport_size({"width": VIEWPORT["width"], "height": height})
            settle(self.pg, 500)
        self.pg.screenshot(path=str(dest))
        if height:
            self.pg.set_viewport_size(VIEWPORT)
            settle(self.pg, 300)
        _optimise_png(dest)
        print("  wrote", dest.relative_to(REPO))


def _optimise_png(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    img.save(path, format="PNG", optimize=True)


def s_home(c: Ctx) -> None:
    c.shot("home")


def s_library(c: Ctx) -> None:
    nav(c.pg, "Library")
    c.shot("library")


def s_new_notebook(c: Ctx) -> None:
    nav(c.pg, "New notebook")
    c.shot("new-notebook")


def s_import(c: Ctx) -> None:
    nav(c.pg, "Import")
    c.shot("import")


def s_import_batch(c: Ctx) -> None:
    nav(c.pg, "Import")
    main_area(c.pg).get_by_text("Batch", exact=True).first.click()
    settle(c.pg, 1200)
    c.shot("import-batch")


def choose(pg, label: str, option: str) -> None:
    """Pick a selectbox option by label; skip quietly if the option is not installed."""
    box = main_area(pg).locator("[data-testid=stSelectbox]").filter(has_text=label)
    if not box.count():
        return
    box.first.click()
    opt = pg.get_by_role("option", name=option, exact=True)
    if opt.count():
        opt.first.click()
    else:
        pg.keyboard.press("Escape")
    settle(pg, 700)


def s_transcribe(c: Ctx) -> None:
    nav(c.pg, "Transcribe")
    field = main_area(c.pg).get_by_label("Ollama base URL")
    if field.count():
        field.fill(OLLAMA)
        field.press("Enter")
        settle(c.pg, 800)
        refresh = main_area(c.pg).get_by_role("button", name=re.compile("Refresh Models"))
        if refresh.count():
            refresh.first.click()
            settle(c.pg, 2500)
        choose(c.pg, "Vision model", "glm-ocr:latest")
        choose(c.pg, "Text analysis model", "llama3.1:8b")
    c.shot("transcribe", height=1300)


def s_review_transcription(c: Ctx) -> None:
    nav(c.pg, "Review")
    c.shot("review-transcription", height=1250)


def s_review_ocr_evidence(c: Ctx) -> None:
    nav(c.pg, "Review")
    ev = main_area(c.pg).get_by_text("OCR evidence", exact=True).first
    if ev.count():
        ev.scroll_into_view_if_needed()
        settle(c.pg, 500)
    compare = main_area(c.pg).get_by_text("Compare full text", exact=True)
    if compare.count():
        compare.first.click()
        settle(c.pg, 900)
        compare.first.scroll_into_view_if_needed()
    c.shot("review-ocr-evidence", height=1250)


def s_review_date(c: Ctx) -> None:
    nav(c.pg, "Review")
    pick_queue(c.pg, r"Needs attention")
    lane(c.pg, "Date")
    c.shot("review-date-cluster")


def s_review_tags(c: Ctx) -> None:
    nav(c.pg, "Review")
    lane(c.pg, "Tags")
    c.shot("review-tags")


def s_review_cleanup(c: Ctx) -> None:
    nav(c.pg, "Review")
    lane(c.pg, "Cleanup")
    c.shot("review-cleanup")


def s_review_move(c: Ctx) -> None:
    nav(c.pg, "Review")
    lane(c.pg, "Other")
    c.shot("review-page-order")


def s_review_thumbnails(c: Ctx) -> None:
    nav(c.pg, "Review")
    pick_queue(c.pg, r"All pages")
    main_area(c.pg).get_by_role("button", name=re.compile("Thumbnails")).first.click()
    settle(c.pg, 2000)
    c.shot("review-thumbnails", height=1300)


def s_detect(c: Ctx) -> None:
    nav(c.pg, "Detect")
    c.shot("detect")


def s_analyse(c: Ctx) -> None:
    nav(c.pg, "Analyse")
    quick = main_area(c.pg).get_by_text("Quick", exact=True)
    if quick.count():
        quick.first.click()
        settle(c.pg, 1200)
    c.shot("analyse", height=1100)


def s_export(c: Ctx) -> None:
    nav(c.pg, "Export")
    c.shot("export", height=1250)


def s_export_finetune(c: Ctx) -> None:
    nav(c.pg, "Export")
    main_area(c.pg).get_by_text("Fine-tune dataset", exact=True).first.click()
    settle(c.pg, 1500)
    c.shot("export-finetune", height=1250)


def s_view_read(c: Ctx) -> None:
    nav(c.pg, "Read")
    c.shot("view-read", height=1100)


def s_settings(c: Ctx) -> None:
    nav(c.pg, "Settings")
    c.shot("settings", height=1100)


def s_diagnostics(c: Ctx) -> None:
    nav(c.pg, "Diagnostics")
    run = main_area(c.pg).get_by_text("Run diagnostics", exact=True)
    if run.count():
        run.first.click()
        settle(c.pg, 4000)
    c.shot("diagnostics", height=1100)


STATIC: dict[str, Callable[[Ctx], None]] = {
    "home": s_home,
    "library": s_library,
    "new-notebook": s_new_notebook,
    "import": s_import,
    "import-batch": s_import_batch,
    "transcribe": s_transcribe,
    "review-transcription": s_review_transcription,
    "review-ocr-evidence": s_review_ocr_evidence,
    "review-date-cluster": s_review_date,
    "review-tags": s_review_tags,
    "review-cleanup": s_review_cleanup,
    "review-page-order": s_review_move,
    "review-thumbnails": s_review_thumbnails,
    "detect": s_detect,
    "analyse": s_analyse,
    "export": s_export,
    "export-finetune": s_export_finetune,
    "view-read": s_view_read,
    "settings": s_settings,
    "diagnostics": s_diagnostics,
}

# Static shots run in this order inside one session (Review first opens the notebook).
ORDER = [
    "home",
    "library",
    "new-notebook",
    "import",
    "import-batch",
    "review-transcription",
    "review-ocr-evidence",
    "review-tags",
    "review-cleanup",
    "review-page-order",
    "review-date-cluster",
    "review-thumbnails",
    "transcribe",
    "detect",
    "analyse",
    "export",
    "export-finetune",
    "view-read",
    "settings",
    "diagnostics",
]


# ── GIFs ────────────────────────────────────────────────────────────────────


class Frames:
    """Collect cropped frames and write an optimised looping GIF."""

    def __init__(self, pg, *, width: int = 1040) -> None:
        self.pg, self.width = pg, width
        self.items: list[tuple[Image.Image, int]] = []

    def snap(self, hold_ms: int = 1400) -> None:
        box = main_area(self.pg).bounding_box() or {"x": 0, "y": 0, "width": 1440, "height": 900}
        x = max(0, int(box["x"]) - 10)
        png = self.pg.screenshot(
            clip={
                "x": x,
                "y": 0,
                "width": VIEWPORT["width"] - x,
                "height": min(self.pg.viewport_size["height"], 1000),
            }
        )
        img = Image.open(BytesIO(png)).convert("RGB")
        ratio = self.width / img.width
        img = img.resize((self.width, int(img.height * ratio)), Image.LANCZOS)
        self.items.append((img, hold_ms))

    def save(self, dest: Path) -> None:
        # Common height so frames stack cleanly; one adaptive palette for the whole loop.
        h = max(i.height for i, _ in self.items)
        canvas = []
        for img, _ in self.items:
            frame = Image.new("RGB", (self.width, h), (255, 255, 255))
            frame.paste(img, (0, 0))
            canvas.append(frame)
        strip = Image.new("RGB", (self.width, h * len(canvas)))
        for i, frame in enumerate(canvas):
            strip.paste(frame, (0, i * h))
        palette = strip.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
        quant = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in canvas]
        quant[0].save(
            dest,
            save_all=True,
            append_images=quant[1:],
            duration=[ms for _, ms in self.items],
            loop=0,
            optimize=True,
            disposal=1,
        )
        kb = dest.stat().st_size // 1024
        print(f"  wrote {dest.relative_to(REPO)} ({len(canvas)} frames, {kb} KB)")


def g_review_workflow(c: Ctx, reset: Callable[[], None]) -> None:
    """Queue → compare OCR evidence → date → tags → save and mark reviewed."""
    reset()
    open_app(c.pg)
    open_review(c.pg)
    f = Frames(c.pg)
    f.snap(1800)  # Transcription lane, scan beside text
    ev = main_area(c.pg).get_by_text("OCR evidence", exact=True).first
    if ev.count():
        ev.scroll_into_view_if_needed()
        settle(c.pg, 600)
        f.snap(2200)  # two OCR attempts disagree
        main_area(c.pg).get_by_text("Transcription", exact=True).first.scroll_into_view_if_needed()
    lane(c.pg, "Date")
    f.snap(1500)
    lane(c.pg, "Tags")
    f.snap(1500)
    lane(c.pg, "Transcription")
    f.snap(1200)
    main_area(c.pg).get_by_role("button", name=re.compile("Save \\+ Mark reviewed")).first.click()
    settle(c.pg, 1500)
    f.snap(2200)  # next page in the queue
    f.save(c.out / "workflow-review.gif")


def g_reorder_workflow(c: Ctx, reset: Callable[[], None]) -> None:
    """Date regression flagged → Move to date cluster → notebook order repaired."""
    reset()
    open_app(c.pg)
    open_review(c.pg)
    pick_queue(c.pg, r"All pages")
    main_area(c.pg).get_by_role("button", name=re.compile("Thumbnails")).first.click()
    settle(c.pg, 2000)
    f = Frames(c.pg)
    f.snap(2200)  # order as scanned: 4 March sits after 9 March
    pick_queue(c.pg, r"Needs attention")
    main_area(c.pg).get_by_role("button", name=re.compile("Page view")).first.click()
    settle(c.pg, 1500)
    lane(c.pg, "Date")
    f.snap(2200)  # Move to date cluster
    main_area(c.pg).get_by_role("button", name="Move to date cluster").first.click()
    settle(c.pg, 2000)
    f.snap(1500)
    pick_queue(c.pg, r"All pages")
    main_area(c.pg).get_by_role("button", name=re.compile("Thumbnails")).first.click()
    settle(c.pg, 2000)
    f.snap(2600)  # repaired order
    f.save(c.out / "workflow-reorder-pages.gif")


GIFS: dict[str, Callable[[Ctx, Callable[[], None]], None]] = {
    "workflow-review": g_review_workflow,
    "workflow-reorder-pages": g_reorder_workflow,
}


# ── orchestration ───────────────────────────────────────────────────────────


def _wait_for_server(timeout: float = 60.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(URL, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise SystemExit("Streamlit did not become ready on 8510")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", default=str(REPO / "docs" / "images"))
    ap.add_argument("--only", default="", help="comma-separated shot/gif names")
    ap.add_argument("--no-gifs", action="store_true")
    ap.add_argument("--no-static", action="store_true")
    ap.add_argument("--no-server", action="store_true", help="reuse a server already on 8510")
    ap.add_argument("--workspace", default="", help="reuse/create this throwaway workspace dir")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    ws = (
        Path(args.workspace)
        if args.workspace
        else Path(tempfile.mkdtemp(prefix="transcribe-docs-"))
    )
    if ws.exists() and args.workspace:
        shutil.rmtree(ws)
    ws.mkdir(parents=True, exist_ok=True)
    for sub in ("data", "inbox", "exports"):
        (ws / sub).mkdir(exist_ok=True)
    notebook = seed(ws)
    pristine = ws / "_pristine"
    shutil.copytree(notebook, pristine)

    def reset() -> None:
        shutil.rmtree(notebook, ignore_errors=True)
        shutil.copytree(pristine, notebook)

    env = dict(os.environ)
    env.update(
        TRANSCRIBE_DATA_DIR=str(ws / "data"),
        TRANSCRIBE_PROJECTS_DIR=str(ws / "projects"),
        TRANSCRIBE_INBOX_DIR=str(ws / "inbox"),
        TRANSCRIBE_EXPORT_DIR=str(ws / "exports"),
        TRANSCRIBE_PORT=str(PORT),
        TRANSCRIBE_HOST="127.0.0.1",
        TRANSCRIBE_OLLAMA_BASE_URL=OLLAMA,
    )
    server = None
    if not args.no_server:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(REPO / "src/transcribe/ui/app.py"),
                "--server.port",
                str(PORT),
                "--server.address",
                "127.0.0.1",
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            env=env,
            cwd=str(REPO),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    try:
        _wait_for_server()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = _chromium_exe()
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            try:
                if not args.no_static:
                    reset()
                    pg = browser.new_page(viewport=VIEWPORT, color_scheme="dark")
                    open_app(pg)
                    ctx = Ctx(out, pg)
                    # Open the notebook once so View/Review state exists.
                    if not only or "home" in only:
                        s_home(ctx)
                    open_review(pg)
                    print("static shots")
                    for name in ORDER:
                        if name == "home" or (only and name not in only):
                            continue
                        STATIC[name](ctx)
                    pg.close()
                if not args.no_gifs:
                    print("gifs")
                    for name, fn in GIFS.items():
                        if only and name not in only:
                            continue
                        pg = browser.new_page(viewport=VIEWPORT, color_scheme="dark")
                        fn(Ctx(out, pg), reset)
                        pg.close()
            finally:
                browser.close()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        reset()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
