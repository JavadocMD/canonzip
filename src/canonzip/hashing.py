"""Implements canonical hashing of directories."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from canonzip.manifest import build_manifest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from os import PathLike

    from canonzip.manifest import Manifest

__all__ = ["hash", "hash_from_manifest"]

CHUNK_SIZE = 1024 * 1024
"""The chunk size to use when reading files for hashing, in bytes.

1 MiB is a good balance between performance and memory usage.
"""


def hash(
    target: str | PathLike[str],
    *,
    exclude: Sequence[str] | None = None,
    gitignore: bool = False,
    follow_symlinks: bool = False,
) -> str:
    """Compute a canonical hash of the directory at the given target path.

    This hash should be stable across different platforms and runs, as long as the
    directory contents and structure remain the same.

    Args:
        target: The target path to hash.
        exclude: Optional sequence of glob patterns to exclude from the hash.
            Uses pathlib.Path.match() syntax, so "**" globs are not supported.
        gitignore: If True, exclude files matching .gitignore patterns.
            If True, the target directory must be in a valid git repository.
        follow_symlinks: If True, follow symbolic links; if False, ignore them.

    Returns:
        A stable SHA-1 hash representing the directory files' paths and contents.
    """
    manifest = build_manifest(
        Path(target).resolve(),
        exclude=exclude,
        gitignore=gitignore,
        follow_symlinks=follow_symlinks,
    )
    return hash_from_manifest(manifest)


def hash_from_manifest(manifest: Manifest) -> str:
    """Compute a canonical hash from a pre-built manifest.

    This is useful when you want to inspect the manifest (e.g. to print
    included paths) before hashing, without walking the directory twice.

    Args:
        manifest: The pre-built manifest to hash.

    Returns:
        A stable SHA-1 hash representing the directory files' paths and contents.
    """
    digest = hashlib.sha1()  # noqa: S324 (SHA-1 is not used for security here)
    for entry in manifest.entries:
        # For each file, digest:
        # - the relative path prefixed by its size, and
        # - the file content prefixed by its size.
        # The sizes act as separators to mitigate hash collisions.
        # For example, without the size prefixes, the following two file sets would
        # produce the same hash:
        # - foobar (content: "baz")
        # - foo (content: "barbaz")
        rel_path = entry.path.relative_to(manifest.target)
        rel_path_bytes = rel_path.as_posix().encode("utf-8")
        digest.update(len(rel_path_bytes).to_bytes(8))
        digest.update(rel_path_bytes)
        digest.update(entry.size.to_bytes(8))
        with entry.path.open("rb") as handle:
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)

    return digest.hexdigest()
