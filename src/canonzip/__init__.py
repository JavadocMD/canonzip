"""canonzip is a library for producing canonical zips and hashes."""

from canonzip.exceptions import (
    BrokenSymlinkError,
    CanonzipError,
    GitRepositoryError,
    OutputPathError,
    SymlinkCycleError,
)
from canonzip.hashing import hash, hash_from_manifest
from canonzip.manifest import FileEntry, Manifest, build_manifest
from canonzip.zipping import zip, zip_from_manifest

__all__ = [
    "BrokenSymlinkError",
    "CanonzipError",
    "FileEntry",
    "GitRepositoryError",
    "Manifest",
    "OutputPathError",
    "SymlinkCycleError",
    "build_manifest",
    "hash",
    "hash_from_manifest",
    "zip",
    "zip_from_manifest",
]
