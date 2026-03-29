"""Implements canonical zipping of directories."""

from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from canonzip.exceptions import OutputPathError
from canonzip.manifest import build_manifest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike

    from canonzip.manifest import Manifest

__all__ = ["zip", "zip_from_manifest"]

CHUNK_SIZE = 1024 * 1024
"""The chunk size to use when copying files into the zip, in bytes.

1 MiB is a good balance between performance and memory usage.
"""


def zip(
    output_path: str | PathLike[str],
    target: str | PathLike[str],
    *,
    exclude: Sequence[str] | None = None,
    gitignore: bool = False,
    follow_symlinks: bool = False,
) -> None:
    """Create a canonical zip file of the directory at the given target path.

    Args:
        output_path: The path to write the zip file to.
            Must not be inside the target directory.
        target: The target directory to zip.
        exclude: Optional sequence of glob patterns to exclude from the zip.
            Uses pathlib.Path.match() syntax, so "**" globs are not supported.
        gitignore: If True, exclude files matching .gitignore patterns.
            If True, the target directory must be in a valid git repository.
        follow_symlinks: If True, follow symbolic links; if False, ignore them.
    """
    manifest = build_manifest(
        Path(target).resolve(),
        exclude=exclude,
        gitignore=gitignore,
        follow_symlinks=follow_symlinks,
    )
    zip_from_manifest(output_path, manifest)


def zip_from_manifest(output_path: str | PathLike[str], manifest: Manifest) -> None:
    """Create a canonical zip file from a pre-built manifest.

    This is useful when you want to inspect the manifest (e.g. to print
    included paths) before zipping, without walking the directory twice.

    Args:
        output_path: The path to write the zip file to.
            Must not be inside the target directory.
        manifest: The pre-built manifest whose entries to include.

    Raises:
        OutputPathError: If the output path is inside the target directory.
    """
    destination = Path(output_path).resolve()
    target_path = manifest.target

    # Ensure the output path is not inside the target directory;
    # I'm not sure this would cause problems, but it seems better to rule this case out.
    try:
        destination.relative_to(target_path)
    except ValueError:
        pass
    else:
        raise OutputPathError(destination, target_path)

    destination.parent.mkdir(parents=True, exist_ok=True)

    fixed_timestamp = (1980, 1, 1, 0, 0, 0)
    compression = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=compression,
        compresslevel=9,
    ) as zip:
        for entry in manifest.entries:
            rel_path = entry.path.relative_to(target_path)
            # This seems like a decent reference on zip file format:
            # https://pkwaredownloads.blob.core.windows.net/pkware-general/Documentation/APPNOTE-6.3.9.TXT
            # create_system=3 indicates file attributes are UNIX compatible
            # attr is shifted because left two bytes are for UNIX, right two for Windows
            info = zipfile.ZipInfo(rel_path.as_posix(), fixed_timestamp)
            info.compress_type = compression
            info.create_system = 3
            info.external_attr = normalized_mode(entry.mode) << 16
            with entry.path.open("rb") as src, zip.open(info, "w") as dst:
                shutil.copyfileobj(src, dst, length=CHUNK_SIZE)


def normalized_mode(mode: int) -> int:
    """Normalize the mode of zipped files (for cross-platform stability)."""  # noqa: DOC201
    if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        return 0o755
    return 0o644
