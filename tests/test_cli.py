"""Tests for the canonzip CLI."""

from __future__ import annotations

import json
import zipfile
from typing import TYPE_CHECKING

from typer.testing import CliRunner

import canonzip
from canonzip.cli import app
from tests.util import init_repo, make_file

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_hash_basic(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="hello\n")
    result = runner.invoke(app, ["hash", str(tmp_path)])
    assert result.exit_code == 0
    expected = canonzip.hash(tmp_path)
    assert result.output.strip() == expected


def test_hash_with_exclude(tmp_path: Path) -> None:
    make_file(tmp_path / "keep.txt", content="keep\n")
    make_file(tmp_path / ".venv" / "ignored.txt", content="ignored\n")
    result = runner.invoke(app, ["hash", str(tmp_path), "--exclude", ".venv"])
    assert result.exit_code == 0
    expected = canonzip.hash(tmp_path, exclude=[".venv"])
    assert result.output.strip() == expected


def test_hash_with_gitignore(tmp_path: Path) -> None:
    init_repo(tmp_path)
    make_file(tmp_path / ".gitignore", content="ignored.txt\n")
    make_file(tmp_path / "keep.txt", content="keep\n")
    make_file(tmp_path / "ignored.txt", content="ignored\n")
    result = runner.invoke(app, ["hash", str(tmp_path), "--gitignore"])
    assert result.exit_code == 0
    expected = canonzip.hash(tmp_path, gitignore=True)
    assert result.output.strip() == expected


def test_hash_verbose(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="alpha\n")
    make_file(tmp_path / "subdir" / "b.txt", content="beta\n")
    # Mix stderr=True to capture verbose output separately
    result = runner.invoke(app, ["hash", str(tmp_path), "--verbose"])
    assert result.exit_code == 0
    # Verbose paths appear in the combined output (CliRunner merges streams)
    assert "a.txt" in result.output
    assert "subdir/b.txt" in result.output


def test_hash_nonexistent_target() -> None:
    result = runner.invoke(app, ["hash", "/nonexistent/path"])
    assert result.exit_code == 2  # noqa: PLR2004 (Typer's argument validation error code)


def test_zip_basic(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt", content="hello\n")
    output_path = tmp_path / "bundle.zip"
    result = runner.invoke(app, ["zip", str(output_path), str(input_path)])
    assert result.exit_code == 0
    assert output_path.exists()
    with zipfile.ZipFile(output_path) as archive:
        assert archive.namelist() == ["a.txt"]


def test_zip_with_exclude(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "keep.txt", content="keep\n")
    make_file(input_path / ".venv" / "ignored.txt", content="ignored\n")
    output_path = tmp_path / "bundle.zip"
    result = runner.invoke(
        app,
        ["zip", str(output_path), str(input_path), "--exclude", ".venv"],
    )
    assert result.exit_code == 0
    with zipfile.ZipFile(output_path) as archive:
        assert archive.namelist() == ["keep.txt"]


def test_zip_verbose(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt", content="alpha\n")
    output_path = tmp_path / "bundle.zip"
    result = runner.invoke(
        app,
        ["zip", str(output_path), str(input_path), "--verbose"],
    )
    assert result.exit_code == 0
    assert "a.txt" in result.output
    assert output_path.exists()


def test_zip_output_inside_target(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt", content="hello\n")
    result = runner.invoke(
        app,
        ["zip", str(input_path / "bundle.zip"), str(input_path)],
    )
    assert result.exit_code == 1
    assert "cannot be inside target" in result.output.lower()


def test_zip_nonexistent_target(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["zip", str(tmp_path / "bundle.zip"), str(tmp_path / "nope")],
    )
    assert result.exit_code == 2  # noqa: PLR2004 (Typer's argument validation error code)


def test_hash_json(tmp_path: Path) -> None:
    make_file(tmp_path / "a.txt", content="hello\n")
    result = runner.invoke(
        app,
        ["hash", str(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    expected = canonzip.hash(tmp_path)
    assert data == {"hash": expected}


def test_zip_json(tmp_path: Path) -> None:
    input_path = tmp_path / "input"
    make_file(input_path / "a.txt", content="hello\n")
    output_path = tmp_path / "bundle.zip"
    result = runner.invoke(
        app,
        ["zip", str(output_path), str(input_path), "--json"],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    data = json.loads(result.output)
    expected = canonzip.hash(input_path)
    assert data == {"hash": expected}
