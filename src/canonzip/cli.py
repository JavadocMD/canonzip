"""Command-line interface for canonzip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from canonzip.exceptions import CanonzipError
from canonzip.hashing import hash_from_manifest
from canonzip.manifest import build_manifest
from canonzip.zipping import zip_from_manifest

app = typer.Typer(no_args_is_help=True, help="Produce canonical zips and hashes.")

ExcludeOption = Annotated[
    list[str] | None,
    typer.Option("--exclude", "-e", help="Glob pattern to exclude (repeatable)."),
]
GitignoreOption = Annotated[
    bool,
    typer.Option("--gitignore", help="Exclude files matching .gitignore patterns."),
]
FollowSymlinksOption = Annotated[
    bool,
    typer.Option("--follow-symlinks", help="Follow symbolic links."),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", "-v", help="Print included file paths to stderr."),
]
JsonOption = Annotated[
    bool,
    typer.Option("--json", help="Output result as JSON."),
]
TargetArgument = Annotated[
    Path,
    typer.Argument(
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Target directory.",
    ),
]
OutputArgument = Annotated[
    Path,
    typer.Argument(dir_okay=False, help="Output zip file path."),
]


@app.command("hash")
def hash_command(  # noqa: PLR0913
    target: TargetArgument,
    *,
    exclude: ExcludeOption = None,
    gitignore: GitignoreOption = False,
    follow_symlinks: FollowSymlinksOption = False,
    verbose: VerboseOption = False,
    output_json: JsonOption = False,
) -> None:
    """Compute a canonical hash of a directory."""  # noqa: DOC501
    try:
        manifest = build_manifest(
            target,
            exclude=exclude,
            gitignore=gitignore,
            follow_symlinks=follow_symlinks,
        )
        if verbose:
            for path in manifest.relative_paths:
                typer.echo(path, err=True)
        digest = hash_from_manifest(manifest)
        output = json.dumps({"hash": digest}) if output_json else digest
        typer.echo(output)
    except CanonzipError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None


@app.command("zip")
def zip_command(  # noqa: PLR0913
    output_path: OutputArgument,
    target: TargetArgument,
    *,
    exclude: ExcludeOption = None,
    gitignore: GitignoreOption = False,
    follow_symlinks: FollowSymlinksOption = False,
    verbose: VerboseOption = False,
    output_json: JsonOption = False,
) -> None:
    """Create a canonical zip archive of a directory."""  # noqa: DOC501
    try:
        manifest = build_manifest(
            target,
            exclude=exclude,
            gitignore=gitignore,
            follow_symlinks=follow_symlinks,
        )
        if verbose:
            for path in manifest.relative_paths:
                typer.echo(path, err=True)
        zip_from_manifest(output_path, manifest)
        if output_json:
            output = json.dumps({"hash": hash_from_manifest(manifest)})
            typer.echo(output)
    except CanonzipError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
