"""Filesystem locations for immutable bundled data and local user imports."""

import os
from pathlib import Path
from typing import Tuple


BUNDLED_DATA_ROOT = Path("data")
USER_DATA_ENV = "FS_FILTERLAB_USER_DATA_DIR"


def get_user_data_root() -> Path:
    """Return the configurable local root used only for user imports."""
    return Path(os.environ.get(USER_DATA_ENV, "user_data"))


def get_collection_roots(relative_path: str) -> Tuple[Path, Path]:
    """Return bundled first, then user-owned collection directories."""
    return (
        BUNDLED_DATA_ROOT / relative_path,
        get_user_data_root() / relative_path,
    )


def discover_tsv_files(relative_path: str, recursive: bool = False) -> list[Path]:
    """Discover deterministic bundled and user files without creating folders."""
    pattern = "**/*.tsv" if recursive else "*.tsv"
    files = []
    for root in get_collection_roots(relative_path):
        if root.exists():
            files.extend(sorted(root.glob(pattern), key=lambda item: item.as_posix()))
    return files
