"""Tests for canonzip.zip."""

from __future__ import annotations

import hashlib
import stat
import sys
import zipfile
from typing import TYPE_CHECKING

import pytest

import canonzip
from canonzip import OutputPathError
from canonzip.manifest import build_manifest
from tests.util import init_repo, make_example_project, make_file

if TYPE_CHECKING:
    from pathlib import Path


def test_hash_example(tmp_path: Path) -> None:
    # These should remain stable regardless of implementation, python version, and OS.
    make_example_project(tmp_path / "input")
    canonzip.zip(tmp_path / "bundle1.zip", tmp_path / "input")
    init_repo(tmp_path / "input")
    canonzip.zip(tmp_path / "bundle2.zip", tmp_path / "input", gitignore=True)
    canonzip.zip(
        tmp_path / "bundle3.zip",
        tmp_path / "input",
        gitignore=True,
        exclude=["data"],
    )
    hash1 = hashlib.sha1((tmp_path / "bundle1.zip").read_bytes()).hexdigest()  # noqa: S324
    hash2 = hashlib.sha1((tmp_path / "bundle2.zip").read_bytes()).hexdigest()  # noqa: S324
    hash3 = hashlib.sha1((tmp_path / "bundle3.zip").read_bytes()).hexdigest()  # noqa: S324
    assert hash1 == "c58e88160ad5f66b3fc1557b4d2b4952c5113d8c"
    assert hash2 == "6ff033e0cdd35bd468be6cb3a107a9afdd4e2c7c"
    assert hash3 == "b6a06aa5f09fb9e9a5462d2ce662c754bc076c13"


def test_zip_is_byte_identical_across_runs(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt")
    make_file(input_path / "script.sh", content="#!/bin/sh\necho hi\n", mode=0o755)

    first_zip = tmp_path / "out" / "bundle1.zip"
    second_zip = tmp_path / "out" / "bundle2.zip"

    canonzip.zip(first_zip, input_path)
    canonzip.zip(second_zip, input_path)

    assert first_zip.read_bytes() == second_zip.read_bytes()

    with zipfile.ZipFile(first_zip) as archive:
        file_info = archive.getinfo("a.txt")
        script_info = archive.getinfo("script.sh")

    assert file_info.date_time == (1980, 1, 1, 0, 0, 0)
    assert script_info.date_time == (1980, 1, 1, 0, 0, 0)
    assert stat.S_IMODE(file_info.external_attr >> 16) == 0o644  # noqa: PLR2004
    if sys.platform != "win32":  # chmod does not set executable bits on Windows
        assert stat.S_IMODE(script_info.external_attr >> 16) == 0o755  # noqa: PLR2004


def test_zip_is_byte_identical_regardless_of_parent_path(tmp_path: Path) -> None:
    tmp_path_a = tmp_path / "input_a"
    tmp_path_b = tmp_path / "input_b"
    make_file(tmp_path_a / "a.txt")
    make_file(tmp_path_b / "a.txt")

    first_zip = tmp_path / "out" / "bundle_a.zip"
    second_zip = tmp_path / "out" / "bundle_b.zip"

    canonzip.zip(first_zip, tmp_path_a)
    canonzip.zip(second_zip, tmp_path_b)

    assert first_zip.read_bytes() == second_zip.read_bytes()


def test_exclude_patterns_apply_to_nested_paths(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "keep.txt")
    make_file(input_path / ".venv" / "ignored.txt")

    archive_path = tmp_path / "nested" / "bundle.zip"
    canonzip.zip(archive_path, input_path, exclude=[".venv"])

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["keep.txt"]


def test_output_cannot_be_inside_target(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt")

    with pytest.raises(OutputPathError):
        canonzip.zip(input_path / "bundle.zip", input_path)
    with pytest.raises(OutputPathError):
        canonzip.zip(input_path / "dist" / "bundle.zip", input_path)


def test_gitignore_and_exclude_are_combined(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="input/ignored.txt\n")
    make_file(input_path / "ignored.txt", content="ignored\n")
    make_file(input_path / "excluded.txt", content="excluded\n")
    make_file(input_path / "keep.txt", content="keep\n")

    archive_path = tmp_path / "bundle.zip"
    canonzip.zip(archive_path, input_path, gitignore=True, exclude=["excluded.txt"])

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["keep.txt"]


def test_symlinks_are_ignored_by_default(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "target.txt")
    (input_path / "link.txt").symlink_to(input_path / "target.txt")

    archive_path = tmp_path / "bundle.zip"
    canonzip.zip(archive_path, input_path)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["target.txt"]


def test_follow_symlinks_includes_linked_file(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "target.txt", content="target\n")
    (input_path / "link.txt").symlink_to(input_path / "target.txt")

    archive_path = tmp_path / "bundle.zip"
    canonzip.zip(archive_path, input_path, follow_symlinks=True)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["link.txt", "target.txt"]
        assert archive.read("link.txt") == b"target\n"


def test_empty_directories_do_not_affect_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt")
    (input_path / "empty").mkdir()

    archive_path = tmp_path / "bundle.zip"
    canonzip.zip(archive_path, input_path)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["a.txt"]


def test_zip_from_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt", content="hello\n")
    make_file(input_path / "b.txt", content="world\n")

    manifest = build_manifest(input_path)
    zip_a = tmp_path / "bundle_a.zip"
    zip_b = tmp_path / "bundle_b.zip"
    canonzip.zip_from_manifest(zip_a, manifest)
    canonzip.zip(zip_b, input_path)
    assert zip_a.read_bytes() == zip_b.read_bytes()
