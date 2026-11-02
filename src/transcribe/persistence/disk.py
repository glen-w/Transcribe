"""Free-disk budget guard shared by long-running writers."""

from __future__ import annotations

import shutil
from pathlib import Path

from transcribe.errors import DiskFullError

MIN_FREE_DISK_BYTES = 256 * 1024 * 1024


def free_disk_bytes(path: Path) -> int:
    probe = Path(path)
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return int(shutil.disk_usage(probe).free)


def ensure_disk_budget(
    root: Path,
    *,
    additional: int = 0,
    min_free_bytes: int = MIN_FREE_DISK_BYTES,
) -> None:
    """Raise DiskFullError before a writer starts if headroom is too low."""
    free = free_disk_bytes(root)
    if free - max(0, additional) < min_free_bytes:
        raise DiskFullError(
            f"insufficient free disk space ({free} bytes free; "
            f"need at least {min_free_bytes} bytes headroom"
            + (f" plus {additional} bytes estimated" if additional else "")
            + ")"
        )


__all__ = ["MIN_FREE_DISK_BYTES", "ensure_disk_budget", "free_disk_bytes"]
