"""Integration tests for the command command."""

from collections.abc import Callable

import pytest

from tests.conftest import OapsProject


class TestCommandOrient:
    def test_displays_command_context_header(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("command", "orient", "test-command", "--project")

        captured = capsys.readouterr()
        assert "## test-command command context" in captured.out

    def test_displays_environment_section(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("command", "orient", "test-command", "--project")

        captured = capsys.readouterr()
        assert "### Environment" in captured.out


class TestCommandContext:
    def test_displays_context_message(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("command", "context", "test-command", "--project")

        captured = capsys.readouterr()
        assert "# Context for project command: test-command" in captured.out
