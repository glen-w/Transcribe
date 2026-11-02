"""Page-scan lightbox: click a large scan -> black fullscreen overlay.

Streamlit has no click-to-fullscreen API (streamlit#8031), so this uses the
same parent-frame JS island pattern as Review hotkeys. Clicking a large
rendered scan opens it in a black overlay; Esc or a click on the backdrop
closes it. If the island never runs (JS disabled, frame restrictions), the
plain ``st.image`` and its hover fullscreen toolbar remain the fallback.
"""

from __future__ import annotations

import streamlit as st

_MIN_CLICKABLE_WIDTH_PX = 250

_SCRIPT = """
<script>
(function () {
  const parent = window.parent;
  if (!parent) return;
  if (parent.__txPageLightboxBound) return;
  parent.__txPageLightboxBound = true;

  function ensureOverlay() {
    let overlay = parent.document.getElementById("tx-page-lightbox");
    if (overlay) return overlay;
    overlay = parent.document.createElement("div");
    overlay.id = "tx-page-lightbox";
    overlay.style.cssText = [
      "display:none", "position:fixed", "inset:0", "z-index:999999",
      "background:#000", "cursor:zoom-out", "align-items:center",
      "justify-content:center", "padding:1rem", "box-sizing:border-box",
    ].join(";");
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Page scan fullscreen");

    const img = parent.document.createElement("img");
    img.id = "tx-page-lightbox-img";
    img.style.cssText = [
      "max-width:100%", "max-height:100%", "object-fit:contain",
      "cursor:default", "user-select:none",
    ].join(";");
    img.addEventListener("click", (e) => e.stopPropagation());

    overlay.appendChild(img);
    overlay.addEventListener("click", () => {
      overlay.style.display = "none";
      img.removeAttribute("src");
    });
    parent.document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay.style.display !== "none") {
        overlay.style.display = "none";
        img.removeAttribute("src");
      }
    });
    parent.document.body.appendChild(overlay);
    return overlay;
  }

  parent.txOpenPageLightbox = function (src) {
    const overlay = ensureOverlay();
    const img = parent.document.getElementById("tx-page-lightbox-img");
    img.src = src;
    overlay.style.display = "flex";
  };

  // Bind clicks on large rendered scans (small thumbs stay plain clicks).
  parent.document.addEventListener("click", (e) => {
    const target = e.target;
    if (!target || target.tagName !== "IMG") return;
    if (target.id === "tx-page-lightbox-img") return;
    const rendered = target.getBoundingClientRect();
    if (rendered.width < __MIN_WIDTH__) return;
    if (!target.closest('[data-testid="stImage"]')) return;
    e.preventDefault();
    e.stopPropagation();
    parent.txOpenPageLightbox(target.src);
  }, true);
})();
</script>
"""


def inject_page_lightbox() -> None:
    """Emit the lightbox island once per page render (guard is parent-side)."""
    st.iframe(_SCRIPT.replace("__MIN_WIDTH__", str(_MIN_CLICKABLE_WIDTH_PX)), height=0)


__all__ = ["inject_page_lightbox"]
