"""CLI command modules. ``python -m transcribe`` still enters via ``__main__.main``."""

from __future__ import annotations

from transcribe.cli.parser import build_parser

__all__ = ["build_parser"]
