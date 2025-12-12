"""Integration tests for root commands."""

from collections.abc import Callable
from pathlib import Path

import pytest


class TestPrefixCommand:
    def test_prints_package_directory(
        self,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("--prefix")

        captured = capsys.readouterr()
        output_path = Path(captured.out.strip())
        assert output_path.is_dir()
        assert (output_path / "__init__.py").exists()

    def test_output_ends_with_newline(
        self,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("--prefix")

        captured = capsys.readouterr()
        assert captured.out.endswith("\n")
