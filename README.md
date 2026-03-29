# canonzip

Produce canonical zips and hashes from directory contents.

A canonical zip produces the exact same file for the same inputs,
regardless of when it was made or what machine made it.

A canonical hash produces the exact same hash for the same inputs,
regardless of when it was made or what machine made it.

This is particularly useful when zipping things like code for
AWS Lambda Functions, where you want to upload a new zip if and
only if the code has truly changed.

canonzip supports two usage modes: as a CLI or as an API.

## Command Line Interface (CLI)

### `canonzip hash [OPTIONS] TARGET`

Print a canonical SHA-1 hash of `TARGET` to stdout.

```
$ canonzip hash path/to/target
4959e4b9a1812e511570eee14fe65b90098a0db6
```

### `canonzip zip [OPTIONS] OUTPUT_PATH TARGET`

Write a canonical zip archive of `TARGET` to `OUTPUT_PATH`.

```
$ canonzip zip path/to/output.zip path/to/target
```

NOTE: the output of `hash` is *NOT* the same as the SHA-1 hash of the output
from `zip`. `hash` is specifically designed to avoid the extra overhead of
writing a zip file while fulfilling a similar use-case &mdash; detecting
changes in the files.

### CLI options

Both commands accept:

| Option | Description |
|---|---|
| `--exclude TEXT, -e TEXT` | Glob pattern to exclude (repeatable) |
| `--gitignore` | Exclude files based on `.gitignore` rules from the target's git repository |
| `--follow-symlinks` | Follow symbolic links; otherwise symlinks are ignored |
| `--verbose, -v` | Print included file paths (relative to target) to stderr |
| `--json` | Output result as JSON (e.g. `{"hash": "..."}`) |

NOTE: exclude double-star globs (**) match one-or-more path segments;
contrary to gitignore syntax.where they match zero-or-more.

## Programmatic Interface (API)

### `canonzip.hash(target, *, exclude, gitignore, follow_symlinks) -> str`

Compute a canonical SHA-1 hash of a directory.

```python
import canonzip

digest = canonzip.hash("path/to/target")
#> "4959e4b9a1812e511570eee14fe65b90098a0db6"
```

### `canonzip.zip(output_path, target, *, exclude, gitignore, follow_symlinks) -> None`

Create a canonical zip archive of a directory.

```python
canonzip.zip("path/to/output.zip", "path/to/target")
```

### Shared options

Both functions accept:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `exclude` | `list[str] \| None` | `None` | Glob patterns to exclude |
| `gitignore` | `bool` | `False` | Exclude files based on `.gitignore` rules from the target's git repository |
| `follow_symlinks` | `bool` | `False` | Follow symbolic links; if `False`, symlinks are ignored |

NOTE: exclude double-star globs (**) match one-or-more path segments;
contrary to gitignore syntax.where they match zero-or-more.

### Exceptions

canonzip will raise standard errors if it cannot read or write files,
typically inheriting from `OSError`.

Additionally there are special cases which raise errors which inherit
from `canonzip.CanonzipError`:

| Exception | Raised when |
|---|---|
| `OutputPathError` | `output_path` is inside `target` |
| `GitRepositoryError` | `gitignore=True` but target is not in a git repo |
| `BrokenSymlinkError` | A broken symlink is encountered with `follow_symlinks=True` |
| `SymlinkCycleError` | A symlink cycle is detected with `follow_symlinks=True` |

### Advanced: build manifests explicitly

If you need direct access to the list of files that *would* be included in the
canonical hash or zip, you can use `build_manifest` to read the target
directory and return a `Manifest` object containing the list of files.
To save yourself from having to generate the manifest twice, you can then pass
it directly to `hash_from_manifest` or `zip_from_manifest` to complete the
operation.

```python
from canonzip import build_manifest, hash_from_manifest, zip_from_manifest

manifest = build_manifest("path/to/target", exclude=[".venv"])

# Do something interesting with the manifest...
print(manifest.target.as_posix())

for entry in manifest.entries:
    print(entry.path.as_posix())

# Then compute the hash or zip
digest = hash_from_manifest(manifest)
zip_from_manifest("path/to/output.zip", manifest)
```
