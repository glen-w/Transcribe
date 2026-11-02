"""CLI workspace-path lookup.

Tests patch ``transcribe.__main__.PATHS``. Command modules call this helper so
that patch still wins after the CLI split.
"""

from __future__ import annotations

import sys

from transcribe.runtime_paths import PATHS, RuntimePaths


def runtime_paths() -> RuntimePaths:
    main = sys.modules.get("transcribe.__main__")
    if main is not None:
        paths = getattr(main, "PATHS", None)
        if paths is not None:
            return paths
    return PATHS
