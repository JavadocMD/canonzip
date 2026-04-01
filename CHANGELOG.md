# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version 1.0.0

Released 2026-03-31

### Added

- CLI commands: `canonzip hash` and `canonzip zip`.
- Python primary API: `hash()`, `zip()`.
- Python advanced API: `build_manifest()`, `hash_from_manifest()`, `zip_from_manifest()`.
- Glob-based file exclusion via `--exclude` / `exclude` parameter.
- `.gitignore`-aware filtering via `--gitignore` / `gitignore` parameter.
- Symlink handling with cycle and broken-link detection.
