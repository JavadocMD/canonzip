"""Tests for canonzip.hash."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

import canonzip
from canonzip import BrokenSymlinkError, GitRepositoryError
from canonzip.manifest import build_manifest
from tests.util import init_repo, make_example_project, make_file

if TYPE_CHECKING:
    from pathlib import Path


def test_hash_example(tmp_path: Path) -> None:
    # These should remain stable regardless of implementation, python version, and OS.
    make_example_project(tmp_path)
    hash1 = canonzip.hash(tmp_path)
    init_repo(tmp_path)
    hash2 = canonzip.hash(tmp_path, gitignore=True)
    hash3 = canonzip.hash(tmp_path, gitignore=True, exclude=["data"])
    assert hash1 == "a692efefdf7bca5e067bd25cf771c7bed5eda53e"
    assert hash2 == "59f03adb8bb548f0ad7f1626ca8d519048f02fd1"
    assert hash3 == "665352ebec2af38d2ba0bdcba49c66219b43539a"


def test_hash_is_stable_across_runs(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="alpha\n")
    make_file(tmp_path / "subdir" / "b.txt", content="beta\n")

    first = canonzip.hash(tmp_path)
    second = canonzip.hash(tmp_path)
    assert first == second


def test_hash_changes_when_paths_change(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="shared\n")
    first = canonzip.hash(tmp_path)

    (tmp_path / "a.txt").rename(tmp_path / "renamed.txt")
    second = canonzip.hash(tmp_path)

    assert first != second


def test_hash_is_stable_regardless_of_parent_path(tmp_path: Path) -> None:
    tmp_path_a = tmp_path / "input_a"
    tmp_path_b = tmp_path / "input_b"
    make_file(tmp_path_a / "a.txt")
    make_file(tmp_path_b / "a.txt")
    first = canonzip.hash(tmp_path_a)
    second = canonzip.hash(tmp_path_b)
    assert first == second


def test_gitignore_requires_repository(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")

    with pytest.raises(GitRepositoryError):
        canonzip.hash(tmp_path, gitignore=True)


def test_broken_symlink_raises_when_following(tmp_path: Path) -> None:
    (tmp_path / "missing.txt").symlink_to(tmp_path / "does-not-exist.txt")

    canonzip.hash(tmp_path, follow_symlinks=False)  # Should not raise
    with pytest.raises(BrokenSymlinkError):
        canonzip.hash(tmp_path, follow_symlinks=True)


def test_empty_directories_do_not_affect_outputs(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt")
    first_hash = canonzip.hash(tmp_path)

    (tmp_path / "empty").mkdir()
    second_hash = canonzip.hash(tmp_path)

    assert first_hash == second_hash


@pytest.mark.skipif(sys.platform == "win32", reason="chmod is not reliable on Windows")
def test_unreadable_file_raises(tmp_path: Path) -> None:
    make_file(tmp_path / "secret.txt", content="secret\n", mode=0o000)

    try:
        with pytest.raises(PermissionError):
            canonzip.hash(tmp_path)
    finally:
        # Reset permissions so the file can be cleaned up after the test.
        (tmp_path / "secret.txt").chmod(0o644)


def test_hash_from_manifest(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="alpha\n")
    make_file(tmp_path / "subdir" / "b.txt", content="beta\n")

    manifest = build_manifest(tmp_path)
    result = canonzip.hash_from_manifest(manifest)
    expected = canonzip.hash(tmp_path)
    assert result == expected
