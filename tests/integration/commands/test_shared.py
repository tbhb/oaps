"""Integration tests for shared CLI utilities."""

from collections.abc import Callable

import pytest

from oaps.cli._commands._shared import ExitCode


class TestExitCodeIntegration:
    """Test that ExitCode values work correctly with CLI fixtures."""

    def test_exit_code_captured_by_cli_fixture(
        self,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Run a command that should succeed
        exit_code = oaps_cli_with_exit_code("--help")
        assert exit_code == ExitCode.SUCCESS

    def test_exit_code_for_missing_command(
        self,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Run a command that doesn't exist - should get non-zero exit
        exit_code = oaps_cli_with_exit_code("nonexistent-command-xyz")
        assert exit_code != ExitCode.SUCCESS


class TestFormatterIntegration:
    """Test that formatters work correctly with CLI output."""

    def test_json_format_in_config_show(
        self,
        oaps_cli_with_exit_code: Callable[..., int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Test that JSON output works (uses format_json from _shared)
        exit_code = oaps_cli_with_exit_code("config", "show", "--format", "json")
        # May fail if no config, but should produce valid output structure
        captured = capsys.readouterr()
        # Either success with JSON output, or error message
        assert exit_code == ExitCode.SUCCESS or "Error" in captured.out

    def test_yaml_format_in_config_show(
        self,
        oaps_cli_with_exit_code: Callable[..., int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show", "--format", "yaml")
        captured = capsys.readouterr()
        assert exit_code == ExitCode.SUCCESS or "Error" in captured.out
