"""Pytest fixtures for Claude Code CLI hook integration tests."""

from pathlib import Path

import pytest

from ._environment import ClaudeTestEnvironment
from ._runner import ClaudeRunner
from ._test_case import ClaudeHookTestCase


@pytest.fixture
def oaps_repo_path() -> Path:
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def claude_test_env(tmp_path: Path, oaps_repo_path: Path) -> ClaudeTestEnvironment:
    return ClaudeTestEnvironment.create(tmp_path, oaps_repo_path)


@pytest.fixture
def claude_test_case(claude_test_env: ClaudeTestEnvironment) -> ClaudeHookTestCase:
    return ClaudeHookTestCase(
        env=claude_test_env,
        runner=ClaudeRunner(env=claude_test_env),
    )
