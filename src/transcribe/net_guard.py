"""Network bind + redaction guards for the local-first trust model.

Transcribe has no authentication. Binding the UI beyond loopback exposes
page images, OCR/analysis text, and destructive actions to the LAN — that
must be a deliberate, acknowledged choice, never an accident of defaults.
See SECURITY.md.
"""

from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from pathlib import Path

ALLOW_LAN_ENV = "TRANSCRIBE_ALLOW_LAN"
CONTAINER_ENV = "TRANSCRIBE_CONTAINER"


def is_loopback_bind(address: str | None) -> bool:
    host = (address or "").strip().lower()
    if host in {"", "localhost", "127.0.0.1", "::1", "[::1]"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def bind_warning(address: str | None) -> str | None:
    """Warning text when a bind would expose the unauthenticated UI."""
    if is_loopback_bind(address):
        return None
    return (
        f"Refusing to bind {address!r}: Transcribe has no authentication, so a "
        "non-loopback bind exposes page images, notebook text, and destructive "
        f"actions to the network. Set {ALLOW_LAN_ENV}=1 only if you accept "
        "that exposure (see SECURITY.md), or bind 127.0.0.1."
    )


def check_bind_allowed(
    address: str | None, *, env: Mapping[str, str] | None = None
) -> str | None:
    """Return an error message when the bind must be refused, else None.

    Container images bind 0.0.0.0 *inside* the container while the host
    publish (Compose TRANSCRIBE_BIND_HOST, loopback by default) decides real
    exposure, so a container bind warns but is allowed.
    """
    warning = bind_warning(address)
    if warning is None:
        return None
    environ = env if env is not None else os.environ
    if environ.get(CONTAINER_ENV) == "1":
        return None
    if environ.get(ALLOW_LAN_ENV) == "1":
        return None
    return warning


_URL_CREDENTIALS_RE = re.compile(r"(://[^:/@\s]+):[^@\s]+@")
_QUERY_SECRET_RE = re.compile(r"([?&](?:api_key|token|key|secret)=)[^&\s]+")


def redact_sensitive(text: str, *, roots: tuple[Path, ...] = ()) -> str:
    """Scrub credentials and absolute workspace roots from display text."""
    out = str(text)
    out = _URL_CREDENTIALS_RE.sub(r"\1:***@", out)
    out = _QUERY_SECRET_RE.sub(r"\1***", out)
    for root in roots:
        try:
            resolved = str(Path(root).resolve())
        except OSError:
            continue
        if resolved and resolved != "/":
            out = out.replace(resolved, "<workspace>")
    home = str(Path.home())
    if home and home != "/":
        out = out.replace(home, "~")
    return out


__all__ = [
    "ALLOW_LAN_ENV",
    "CONTAINER_ENV",
    "bind_warning",
    "check_bind_allowed",
    "is_loopback_bind",
    "redact_sensitive",
]
