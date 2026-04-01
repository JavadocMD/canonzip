"""Implements canonical ordering of files in directories.

Hashing and zipping use this manifest to ensure consistent behavior.
"""

from __future__ import annotations

import stat
from collections.abc import Callable, Generator, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pygit2

from canonzip.exceptions import (
    BrokenSymlinkError,
    GitRepositoryError,
    SymlinkCycleError,
)

__all__ = ["FileEntry", "Manifest", "build_manifest"]


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Represents a file or directory entry in the manifest."""

    path: Path
    """The absolute path to the file or directory."""
    path_relative: Path
    """The path relative to the manifest target directory."""
    mode: int
    """The file mode (permissions and type) as returned by os.stat()."""
    is_dir: bool
    """Indicates if the entry is a directory."""
    is_file: bool
    """Indicates if the entry is a file."""
    is_symlink: bool
    """Indicates if the entry is a symbolic link."""
    is_broken: bool
    """Indicates if the entry is a broken symbolic link."""
    size: int
    """The size of the file in bytes."""

    @staticmethod
    def from_path(path: Path, path_relative: Path) -> FileEntry:
        """Create a FileEntry from a given path, gathering necessary metadata.

        Args:
            path: The absolute path to a file or directory.
            path_relative: The path relative to the manifest target directory.

        Returns:
            The FileEntry object.
        """
        # Take care to handle broken symlinks correctly.
        # First stat without following symlinks to determine if it's a symlink.
        # If so, stat again with following enabled to determine if it's broken.
        stat_nofollow = path.stat(follow_symlinks=False)
        is_symlink = stat.S_ISLNK(stat_nofollow.st_mode)
        if not is_symlink:
            stat_result = stat_nofollow
            is_broken = False
        else:
            try:
                stat_result = path.stat(follow_symlinks=True)
                is_broken = False
            except OSError:
                stat_result = stat_nofollow
                is_broken = True
        mode = stat_result.st_mode
        return FileEntry(
            path=path,
            path_relative=path_relative,
            mode=mode,
            is_dir=stat.S_ISDIR(mode),
            is_file=stat.S_ISREG(mode),
            is_symlink=is_symlink,
            is_broken=is_broken,
            size=stat_result.st_size,
        )


@dataclass(frozen=True, slots=True)
class Manifest:
    """A canonical ordered collection of files for a given target directory."""

    target: Path
    """The resolved path of the target directory."""
    entries: tuple[FileEntry, ...]
    """The canonical ordered file entries."""

    @property
    def relative_paths(self) -> Iterable[str]:
        """The relative paths of the manifest entries (posix-formatted strings)."""
        return (entry.path_relative.as_posix() for entry in self.entries)


ExcludePredicate = Callable[[FileEntry], bool]
"""A predicate function: should a FileEntry be excluded from the manifest?"""


def exclude_none(_file_entry: FileEntry) -> bool:
    """The default exclusion predicate: exclude nothing."""  # noqa: DOC201
    return False


def exclude_symlinks(prev: ExcludePredicate) -> ExcludePredicate:
    """Exclude symbolic links."""  # noqa: DOC201

    def exclude(file_entry: FileEntry) -> bool:
        return file_entry.is_symlink or prev(file_entry)

    return exclude


def exclude_by_patterns(
    patterns: Sequence[str],
    prev: ExcludePredicate,
) -> ExcludePredicate:
    """Exclude files matching any of the given glob patterns."""  # noqa: DOC201
    patterns_list = list(patterns)

    def exclude(file_entry: FileEntry) -> bool:
        path = PurePosixPath(file_entry.path_relative)
        match = any(
            any(candidate.match(p) for p in patterns_list)  # check each pattern
            for candidate in [path, *path.parents[:-1]]  # check each path and parents
        )
        return match or prev(file_entry)

    return exclude


def exclude_gitignored(path: Path, prev: ExcludePredicate) -> ExcludePredicate:
    """Exclude files using the .gitignore of the repository containing the path."""  # noqa: DOC201, DOC501
    try:
        repository = pygit2.Repository(path)
    except pygit2.GitError:
        raise GitRepositoryError(path) from None
    if repository.is_bare:
        raise GitRepositoryError(path) from None
    workdir = Path(repository.workdir).resolve()

    def is_ignored(file_entry: FileEntry) -> bool:
        rel_path = file_entry.path.relative_to(workdir).as_posix()
        if file_entry.is_dir:
            rel_path = f"{rel_path}/"
        return repository.path_is_ignored(rel_path)

    def exclude(file_entry: FileEntry) -> bool:
        return is_ignored(file_entry) or prev(file_entry)

    return exclude


def build_manifest(
    target: Path,
    *,
    exclude: Sequence[str] | None = None,
    gitignore: bool = False,
    follow_symlinks: bool = False,
) -> Manifest:
    """Build the canonical manifest for the given target directory.

    Args:
        target: The target directory to build the manifest for.
        exclude: Optional sequence of glob patterns to exclude from themanifest.
            Uses pathlib.Path.match() syntax, so "**" globs are not supported.
        gitignore: If True, exclude files matching .gitignore patterns.
            If True, the target directory must be in a valid git repository.
        follow_symlinks: If True, follow symbolic links; if False, ignore them.

    Returns:
        A Manifest containing the resolved target path and its canonical file entries.

    Raises:
        FileNotFoundError: If the target directory does not exist.
        NotADirectoryError: If the target path is not a directory.
        SymlinkCycleError: If a symlink cycle is detected.
        GitRepositoryError: If gitignore=True but the target is not in a valid
            git repository.
        BrokenSymlinkError: If a broken symlink is found when follow_symlinks=True.
    """  # noqa: DOC502
    if not target.exists():
        raise FileNotFoundError(target)
    if not target.is_dir():
        raise NotADirectoryError(target)
    target = target.resolve()

    # Build up the exclude predicate based on the options.
    # Chained function application implements a logical or of the selected conditions,
    # so a file is excluded if it matches any of the criteria.
    exclude_fn = exclude_none
    if not follow_symlinks:
        exclude_fn = exclude_symlinks(exclude_fn)
    if exclude:
        exclude_fn = exclude_by_patterns(exclude, exclude_fn)
    if gitignore:
        exclude_fn = exclude_gitignored(target, exclude_fn)

    walk = walk_directory(
        target,
        target,
        walked_dirs=set(),
        exclude=exclude_fn,
        follow_symlinks=follow_symlinks,
    )

    return Manifest(target=target, entries=tuple(walk))


def walk_directory(
    root: Path,
    path: Path,
    *,
    walked_dirs: set[Path],
    exclude: ExcludePredicate,
    follow_symlinks: bool,
) -> Generator[FileEntry, None, None]:
    """Recursively yield FileEntry objects for non-excluded files in a directory.

    Args:
        root: The root directory for relative path calculations.
        path: The directory to walk.
        walked_dirs: A set of directories that have already been walked.
        exclude: A predicate that returns True for files that should be excluded.
        follow_symlinks: If True, follow symbolic links; if False, ignore them.

    Yields:
        FileEntry objects for files that are not excluded.

    Raises:
        SymlinkCycleError: If a symlink cycle is detected.
        BrokenSymlinkError: If a broken symlink is found when follow_symlinks=True.
    """
    if any(path.samefile(x) for x in walked_dirs):
        raise SymlinkCycleError(path)
    walked_dirs.add(path)

    # Sorting entries by name ensures a stable order regardless of filesystem behavior.
    for entry in sorted(path.iterdir(), key=lambda p: p.name):
        file_entry = FileEntry.from_path(entry, entry.relative_to(root))
        if follow_symlinks and file_entry.is_broken:
            raise BrokenSymlinkError(entry)
        if exclude(file_entry):
            continue

        if file_entry.is_file:
            yield file_entry
        elif file_entry.is_dir:
            yield from walk_directory(
                root,
                entry,
                walked_dirs=walked_dirs,
                exclude=exclude,
                follow_symlinks=follow_symlinks,
            )
