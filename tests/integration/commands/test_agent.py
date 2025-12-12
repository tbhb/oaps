"""Integration tests for the agent command."""

from collections.abc import Callable

import pytest

from tests.conftest import OapsProject


class TestAgentOrient:
    def test_displays_agent_context_header(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("agent", "orient", "test-agent", "--project")

        captured = capsys.readouterr()
        assert "## test-agent agent context" in captured.out

    def test_displays_environment_section(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("agent", "orient", "test-agent", "--project")

        captured = capsys.readouterr()
        assert "### Environment" in captured.out


class TestAgentContext:
    def test_displays_context_message(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("agent", "context", "test-agent", "--project")

        captured = capsys.readouterr()
        assert "Context for project agent: test-agent" in captured.out
