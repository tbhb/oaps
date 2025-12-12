"""Pytest fixtures for hook unit tests.

This module provides fixtures for testing hooks without spawning the full
Claude CLI. Import individual fixtures from fixtures/ subpackage for more
specialized needs.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from .fixtures import HookContextFactory, RuleBuilder, ScriptRunner

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def ctx_factory(tmp_path: Path) -> HookContextFactory:
    """Create a HookContextFactory for the test.

    The factory creates properly initialized HookContext instances
    for each event type with sensible defaults.

    Returns:
        HookContextFactory bound to tmp_path.
    """
    return HookContextFactory(tmp_path)


@pytest.fixture
def rule_builder() -> Callable[[str], RuleBuilder]:
    """Factory fixture for creating RuleBuilder instances.

    Returns:
        Factory function that takes a rule_id and returns a RuleBuilder.

    Example:
        rule = rule_builder("my-rule").when('tool_name == "Bash"').blocks().build()
    """

    def _create(rule_id: str) -> RuleBuilder:
        return RuleBuilder(rule_id)

    return _create


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger with all expected methods.

    Returns:
        MagicMock configured as a logger.
    """
    from .fixtures.contexts import create_mock_logger

    return create_mock_logger()


@pytest.fixture
def script_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test scripts.

    Returns:
        Path to the script directory.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    return scripts


@pytest.fixture
def script_runner(script_dir: Path) -> ScriptRunner:
    """Create a ScriptRunner for managing test scripts.

    Returns:
        ScriptRunner bound to script_dir.
    """
    return ScriptRunner(script_dir)
