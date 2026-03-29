"""Test utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygit2

if TYPE_CHECKING:
    from pathlib import Path


def init_repo(path: Path) -> pygit2.Repository:
    """Initialize a git repository at the given path."""  # noqa: DOC201
    return pygit2.init_repository(str(path), bare=False)


def make_file(
    path: Path,
    *,
    content: str = "content\n",
    mode: int | None = None,
) -> None:
    """Create a file with the given content and permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # writing bytes instead of text to avoid platform-specific newline conversions
    path.write_bytes(content.encode("utf-8"))
    if mode is not None:
        path.chmod(mode)


def make_example_project(path: Path) -> None:
    """Set up an example project directory structure for testing."""
    make_file(path / "README.md", content="# Example Project\n")
    make_file(path / ".gitignore", content="__pycache__/\n.venv/\n")
    make_file(path / "src" / "main.py", content='print("Hello, world!")\n')
    make_file(path / "src" / "utils.py", content="def add(a, b): return a + b\n")
    make_file(path / "src" / "__pycache__" / "main.pyc", content="(compiled code)\n")
    make_file(path / "src" / "__pycache__" / "utils.pyc", content="(compiled code)\n")
    make_file(path / "data" / "input.txt", content="input data\n")
    make_file(path / "data" / "output.txt", content="output data\n")
    make_file(path / ".venv" / "bin" / "activate", content="(venv activate script)\n")
    make_file(path / ".venv" / "bin" / "python", content="(venv python executable)\n")
    (path / "empty_dir").mkdir()
