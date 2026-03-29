"""Custom exception types for canonzip."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "BrokenSymlinkError",
    "CanonzipError",
    "GitRepositoryError",
    "OutputPathError",
    "SymlinkCycleError",
]


class CanonzipError(Exception):
    """Base exception for all canonzip errors."""


class SymlinkCycleError(CanonzipError):
    """A symlink cycle was detected during directory traversal."""

    path: Path
    """The path where the cycle was detected."""

    def __init__(self, path: Path) -> None:
        """Initialize with the path where the cycle was detected."""
        super().__init__(f"Symlink cycle detected at {path}")
        self.path = path


class BrokenSymlinkError(CanonzipError):
    """A broken symlink was found during directory traversal."""

    path: Path
    """The path of the broken symlink."""

    def __init__(self, path: Path) -> None:
        """Initialize with the path of the broken symlink."""
        super().__init__(f"Broken symlink found at {path}")
        self.path = path


class GitRepositoryError(CanonzipError):
    """The target is not in a valid (non-bare) git repository."""

    path: Path
    """The path that is not in a valid git repository."""

    def __init__(self, path: Path) -> None:
        """Initialize with the path that is not in a valid git repository."""
        super().__init__(f"Not a valid (non-bare) git repository: {path}")
        self.path = path


class OutputPathError(CanonzipError):
    """The output path is inside the target directory."""

    output_path: Path
    """The (invalid) output path attempted."""
    target: Path
    """The target directory that contains the output path."""

    def __init__(self, output_path: Path, target: Path) -> None:
        """Initialize with the output path and target directory."""
        super().__init__(
            f"Output path ({output_path}) cannot be inside target directory ({target})",
        )
        self.output_path = output_path
        self.target = target
