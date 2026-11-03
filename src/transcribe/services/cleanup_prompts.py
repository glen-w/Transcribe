"""Versioned OCR cleanup prompt templates."""

from __future__ import annotations

from transcribe.prompts import PromptTemplate

CLEANUP_STRIP_LEAK = PromptTemplate(
    prompt_id="cleanup_strip_leak",
    version="1",
    body=(
        "You are cleaning OCR output from a handwritten notebook page.\n"
        "Remove only leaked system/instruction text, meta writing guidelines, "
        "and prompt artefacts that are not part of the page.\n"
        "Do not paraphrase, rewrite, summarize, or invent content.\n"
        "Preserve the page transcription otherwise exactly.\n"
        "Return only the cleaned page text with no commentary and no markdown fences.\n\n"
        "OCR text:\n{ocr_text}"
    ),
)

CLEANUP_SANITIZE_LIGHT = PromptTemplate(
    prompt_id="cleanup_sanitize_light",
    version="1",
    body=(
        "You are lightly sanitizing OCR output from a handwritten notebook page.\n"
        "Remove leaked instructions/prompt artefacts and fix only obvious OCR artefacts "
        "(broken whitespace, duplicated punctuation) while staying faithful to the page.\n"
        "Do not paraphrase meaning or add new content.\n"
        "Return only the cleaned page text with no commentary and no markdown fences.\n\n"
        "OCR text:\n{ocr_text}"
    ),
)

CLEANUP_REWRITE = PromptTemplate(
    prompt_id="cleanup_rewrite",
    version="1",
    body=(
        "You are normalizing OCR output from a handwritten notebook page.\n"
        "You may lightly polish spelling/punctuation and remove leaked instruction text, "
        "but preserve the author's meaning and content.\n"
        "Do not invent topics that are not present.\n"
        "Return only the cleaned page text with no commentary and no markdown fences.\n\n"
        "OCR text:\n{ocr_text}"
    ),
)

CLEANUP_REGISTRY: dict[str, PromptTemplate] = {
    "strip_leak": CLEANUP_STRIP_LEAK,
    "sanitize_light": CLEANUP_SANITIZE_LIGHT,
    "rewrite": CLEANUP_REWRITE,
}


def spelling_hint_block(pairs: tuple[tuple[str, str], ...] | list[tuple[str, str]]) -> str:
    """Append-only hint. Empty pairs yield empty string so fingerprints stay stable."""
    if not pairs:
        return ""
    lines = "\n".join(f"- {src} → {dst}" for src, dst in pairs if src and dst)
    if not lines:
        return ""
    return (
        "\n\nConfirmed spellings for this handwriting (hints only; do not invent):\n"
        + lines
    )


def render_cleanup_prompt(
    *,
    mode: str,
    ocr_text: str,
    spelling_pairs: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
) -> tuple[str, str, str]:
    """Return (prompt_id, prompt_version, exact prompt text)."""
    template = CLEANUP_REGISTRY.get(mode)
    if template is None:
        raise KeyError(f"unknown cleanup mode: {mode}")
    body = template.body.format(ocr_text=ocr_text) + spelling_hint_block(spelling_pairs)
    return (
        template.prompt_id,
        template.version,
        body,
    )
