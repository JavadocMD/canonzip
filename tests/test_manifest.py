"""Tests for canonzip.manifest."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

from canonzip import BrokenSymlinkError, GitRepositoryError, SymlinkCycleError
from canonzip.manifest import build_manifest
from tests.util import init_repo, make_file

if TYPE_CHECKING:
    from pathlib import Path

# Basic traversal


def test_empty_directory_returns_empty_manifest(tmp_path: Path) -> None:
    assert build_manifest(tmp_path).entries == ()


def test_returns_regular_files(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    make_file(tmp_path / "b.txt")

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["a.txt", "b.txt"]


def test_files_are_sorted_lexicographically(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    make_file(tmp_path / "b.txt")
    make_file(tmp_path / "c.txt")

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["a.txt", "b.txt", "c.txt"]


def test_nested_files_are_traversed_recursively(tmp_path: Path) -> None:
    make_file(tmp_path / "top.txt")
    make_file(tmp_path / "sub" / "nested.txt")

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["sub/nested.txt", "top.txt"]


def test_empty_subdirectories_are_omitted(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    (tmp_path / "empty_dir").mkdir()

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["a.txt"]


# FileEntry attributes


def test_file_entry_attributes_for_regular_file(tmp_path: Path) -> None:
    path = tmp_path / "hello.txt"
    make_file(path, content="hello\n")

    manifest = build_manifest(tmp_path)
    assert len(manifest.entries) == 1
    e = manifest.entries[0]

    assert e.path == path
    assert e.is_file is True
    assert e.is_dir is False
    assert e.is_symlink is False
    assert e.is_broken is False
    assert e.size == len("hello\n")
    assert stat.S_ISREG(e.mode)


# Invalid target


def test_target_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_manifest(tmp_path / "no_such_dir")


def test_target_not_a_directory_raises(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    make_file(file, content="oops\n")

    with pytest.raises(NotADirectoryError):
        build_manifest(file)


def test_target_is_symlink(tmp_path: Path) -> None:
    make_file(tmp_path / "real.txt")
    symlink = tmp_path / "link.txt"
    (symlink).symlink_to(tmp_path / "real.txt")

    with pytest.raises(NotADirectoryError):
        build_manifest(symlink)


# Symlink handling


def test_symlinks_excluded_by_default(tmp_path: Path) -> None:
    make_file(tmp_path / "real.txt")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["real.txt"]


def test_follow_symlinks_includes_symlink_target(tmp_path: Path) -> None:
    make_file(tmp_path / "real.txt")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")

    manifest = build_manifest(tmp_path, follow_symlinks=True)
    assert list(manifest.relative_paths) == ["link.txt", "real.txt"]


def test_follow_symlinks_file_entry_has_correct_attributes(tmp_path: Path) -> None:
    make_file(tmp_path / "real.txt", content="data\n")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")

    manifest = build_manifest(tmp_path, follow_symlinks=True)
    link_entry = next(e for e in manifest.entries if e.path.name == "link.txt")

    assert link_entry.is_symlink is True
    assert link_entry.is_file is True
    assert link_entry.is_broken is False
    assert link_entry.size == len("data\n")


def test_broken_symlink_excluded_when_not_following(tmp_path: Path) -> None:
    make_file(tmp_path / "real.txt")
    (tmp_path / "broken.txt").symlink_to(tmp_path / "does_not_exist.txt")

    manifest = build_manifest(tmp_path)
    assert list(manifest.relative_paths) == ["real.txt"]


def test_broken_symlink_raises_when_following(tmp_path: Path) -> None:
    (tmp_path / "broken.txt").symlink_to(tmp_path / "does_not_exist.txt")

    with pytest.raises(BrokenSymlinkError):
        build_manifest(tmp_path, follow_symlinks=True)


def test_symlink_cycle_raises(tmp_path: Path) -> None:
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "cycle").symlink_to(tmp_path)

    with pytest.raises(SymlinkCycleError):
        build_manifest(tmp_path, follow_symlinks=True)


# Exclude patterns


def test_exclude_patterns_by_filename_glob(tmp_path: Path) -> None:
    make_file(tmp_path / "keep.txt")
    make_file(tmp_path / "drop.log")
    make_file(tmp_path / "nested" / "keep.py")
    make_file(tmp_path / "nested" / "drop.log")

    manifest = build_manifest(tmp_path, exclude=["*.log"])
    assert list(manifest.relative_paths) == ["keep.txt", "nested/keep.py"]


def test_exclude_patterns_prunes_entire_directory(tmp_path: Path) -> None:
    make_file(tmp_path / "keep.txt")
    make_file(tmp_path / ".venv" / "lib.py")
    make_file(tmp_path / "dist" / "out.whl")

    manifest = build_manifest(tmp_path, exclude=[".venv", "dist"])
    assert list(manifest.relative_paths) == ["keep.txt"]


def test_exclude_multiple_patterns(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    make_file(tmp_path / "b.log")
    make_file(tmp_path / "c.tmp")

    manifest = build_manifest(tmp_path, exclude=["*.log", "*.tmp"])
    assert list(manifest.relative_paths) == ["a.txt"]


def test_exclude_patterns_none_excludes_nothing(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    make_file(tmp_path / "b.txt")

    manifest = build_manifest(tmp_path, exclude=None)
    assert list(manifest.relative_paths) == ["a.txt", "b.txt"]


def test_exclude_patterns_empty_list_excludes_nothing(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    make_file(tmp_path / "b.txt")

    manifest = build_manifest(tmp_path, exclude=[])
    assert list(manifest.relative_paths) == ["a.txt", "b.txt"]


_PATTERN_TREE = [
    ".hidden",
    "a.txt",
    "b.log",
    "c.py",
    "deep/nested/f.txt",
    "sub/d.txt",
    "sub/e.log",
]


@pytest.fixture(scope="module")
def pattern_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp("pattern_tree")
    for name in _PATTERN_TREE:
        make_file(tmp_path / name)
    return tmp_path


@pytest.mark.parametrize(
    ("pattern", "excluded"),
    [
        # Extension globs match at any depth
        ("*.txt", {"a.txt", "sub/d.txt", "deep/nested/f.txt"}),
        ("*.log", {"b.log", "sub/e.log"}),
        ("*.py", {"c.py"}),
        # Exact filename matches anywhere in tree
        ("a.txt", {"a.txt"}),
        ("f.txt", {"deep/nested/f.txt"}),
        # Directory name prunes entire subtree
        ("sub", {"sub/d.txt", "sub/e.log"}),
        ("deep", {"deep/nested/f.txt"}),
        ("nested", {"deep/nested/f.txt"}),
        # Dotfile / hidden file glob
        (".*", {".hidden"}),
        # Single-character wildcard
        ("?.py", {"c.py"}),
        ("?.txt", {"a.txt", "sub/d.txt", "deep/nested/f.txt"}),
        ("?.log", {"b.log", "sub/e.log"}),
        # Character class
        ("[ab].*", {"a.txt", "b.log"}),
        ("[d-f].*", {"sub/d.txt", "sub/e.log", "deep/nested/f.txt"}),
        # Path with separator targets specific subtree
        ("sub/*.txt", {"sub/d.txt"}),
        ("sub/*.log", {"sub/e.log"}),
        ("deep/nested", {"deep/nested/f.txt"}),
        # Catch-all
        ("*", set(_PATTERN_TREE)),
        # No match
        ("*.rs", set()),
        ("nonexistent", set()),
        # Case-sensitivity
        ("*.TXT", set()),
        ("*.Py", set()),
        # ** globs (recursive wildcard)
        ("**/*.txt", {"sub/d.txt", "deep/nested/f.txt"}),  # not root-level a.txt
        ("**/*.log", {"sub/e.log"}),  # not root-level b.log
        ("**", set(_PATTERN_TREE)),  # matches everything
        ("**/nested/*.txt", {"deep/nested/f.txt"}),
        ("deep/**", {"deep/nested/f.txt"}),  # prunes via parent match
        ("**/sub/*.txt", set()),  # ** before sub needs a component; sub is top-level
    ],  # type: ignore  # noqa: PGH003
)
def test_exclude_pattern_matching(
    pattern_tree: Path,
    pattern: str,
    excluded: set[str],
) -> None:
    manifest = build_manifest(pattern_tree, exclude=[pattern])
    expected = sorted(p for p in _PATTERN_TREE if p not in excluded)
    assert list(manifest.relative_paths) == expected


# gitignore


def test_gitignore_requires_git_repository(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")

    with pytest.raises(GitRepositoryError):
        build_manifest(tmp_path, gitignore=True)


def test_gitignore_excludes_ignored_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="*.log\n")
    make_file(tmp_path / "project" / "keep.txt")
    make_file(tmp_path / "project" / "drop.log")

    manifest = build_manifest(tmp_path / "project", gitignore=True)
    assert list(manifest.relative_paths) == ["keep.txt"]


def test_gitignore_excludes_ignored_nested_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="*.pyc\n")
    make_file(tmp_path / "project" / "code.py")
    make_file(tmp_path / "project" / "__pycache__" / "code.pyc")

    manifest = build_manifest(tmp_path / "project", gitignore=True)
    assert list(manifest.relative_paths) == ["code.py"]


def test_multiple_gitignore_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="*.pyc\n")
    make_file(tmp_path / "project" / "code.py")
    make_file(tmp_path / "project" / "some.log")
    make_file(tmp_path / "project" / "__pycache__" / "code.pyc")
    make_file(tmp_path / "project" / "subdir" / "other_code.py")
    make_file(tmp_path / "project" / "subdir" / "other_code.log")
    make_file(tmp_path / "project" / "subdir" / "__pycache__" / "other_code.pyc")
    make_file(tmp_path / "project" / "subdir" / ".gitignore", content="*.log\n")

    manifest = build_manifest(tmp_path / "project", gitignore=True)
    assert list(manifest.relative_paths) == [
        "code.py",
        "some.log",
        "subdir/.gitignore",
        "subdir/other_code.py",
    ]


def test_gitignore_and_exclude_patterns_are_combined(tmp_path: Path) -> None:
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="*.log\n")
    make_file(tmp_path / "project" / "keep.txt")
    make_file(tmp_path / "project" / "drop.log")
    make_file(tmp_path / "project" / "drop.tmp")

    manifest = build_manifest(tmp_path / "project", gitignore=True, exclude=["*.tmp"])
    assert list(manifest.relative_paths) == ["keep.txt"]
