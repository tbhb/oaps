#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Verify package installation from PyPi/TestPyPI in an isolated environment."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_ARGS = 3


def main() -> int:
    """Verify package installation from PyPi/TestPyPI."""
    if len(sys.argv) != EXPECTED_ARGS:
        print("Usage: verify_release.py <pypi|testpypi> <version>", file=sys.stderr)
        return 1

    index = sys.argv[1]
    version = sys.argv[2]

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        print(f"Creating isolated environment in {tmpdir}...")

        _ = subprocess.run(  # noqa: S603
            ["uv", "venv", str(venv_path)],  # noqa: S607
            check=True,
        )

        env = {**os.environ, "VIRTUAL_ENV": str(venv_path)}
        index_args = []
        if index == "testpypi":
            index_args = [
                "--index-url",
                "https://test.pypi.org/simple/",
                "--extra-index-url",
                "https://pypi.org/simple/",
                "--index-strategy",
                # Allow TestPyPI version even when PyPI has the package.
                "unsafe-best-match",
            ]
        else:
            index_args = [
                "--index-url",
                "https://pypi.org/simple/",
            ]
        _ = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "pip",
                "install",
                *index_args,
                f"oaps=={version}",
            ],
            env=env,
            check=True,
        )

        # Verify installation
        python_path = venv_path / "bin" / "python"
        print(f"Verifying installation from {index}...")

        version_check = "import oaps; print(f'Installed: oaps {oaps.__version__}')"
        _ = subprocess.run(  # noqa: S603
            [str(python_path), "-c", version_check],
            check=True,
        )

        print("\u2713 Verification passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
