"""Smoke test for canonzip package."""

# Run in an isolated environment to validate the built distribution:
#
# uv run --isolated --no-project --with pytest --with dist/*.whl \
#     pytest tests/smoke_test.py
#
# uv run --isolated --no-project --with pytest --with dist/*.tar.gz \
#     pytest tests/smoke_test.py

import tempfile
from pathlib import Path


def test_smoke() -> None:
    # Verify core imports.
    import canonzip  # noqa: PLC0415

    assert hasattr(canonzip, "__version__"), "missing __version__"
    assert isinstance(canonzip.__version__, str), "__version__ is not a string"
    for name in ["hash", "zip"]:
        assert hasattr(canonzip, name), f"missing expected export: {name}"

    # Verify basic functionality with a temporary directory.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        target.mkdir()
        (target / "hello.txt").write_text("hello world")

        # hash should return a hex string
        h = canonzip.hash(target)
        assert isinstance(h, str), "hash did not return a string"
        expected_len = 40
        assert len(h) == expected_len, f"hash length {len(h)} != {expected_len}"

        # zip should produce a file
        out = Path(tmp) / "output.zip"
        canonzip.zip(out, target)
        assert out.exists(), "zip did not create output file"
        assert out.stat().st_size > 0, "zip file is empty"
