import json
import os
import subprocess
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.integration)


def init_git_repo(path: Path) -> None:
    """Initialize a minimal git repository in the given path."""
    subprocess.run(
        ["git", "init"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )


@dataclass(frozen=True, slots=True)
class HookTestEnv:
    """Environment for hook integration tests."""

    tmp_path: Path
    claude_home: Path
    session_id: str


@pytest.fixture
def hook_test_env(tmp_path: Path) -> HookTestEnv:
    """Create an isolated environment for hook integration tests."""
    init_git_repo(tmp_path)
    claude_home = tmp_path / "claude_home"
    claude_home.mkdir()
    session_id = str(uuid.uuid4())
    return HookTestEnv(
        tmp_path=tmp_path,
        claude_home=claude_home,
        session_id=session_id,
    )


def run_hook(
    event: str,
    input_data: Mapping[str, object],
    env: HookTestEnv,
) -> subprocess.CompletedProcess[str]:
    """Run a hook event via subprocess.

    Args:
        event: The hook event type (e.g., "session_start").
        input_data: The input data to pass via stdin.
        env: The hook test environment.

    Returns:
        The completed process result.
    """
    os_env = os.environ.copy()
    os_env["CLAUDE_HOME"] = str(env.claude_home)

    return subprocess.run(  # noqa: S603 - Safe: running our own CLI tool
        ["uv", "run", "oaps-hook", event],
        input=json.dumps(dict(input_data)),
        capture_output=True,
        text=True,
        env=os_env,
        check=False,
        cwd=str(env.tmp_path),
    )


def run_session_start(env: HookTestEnv) -> subprocess.CompletedProcess[str]:
    """Run session_start hook to initialize the session store."""
    start_input = {
        "session_id": env.session_id,
        "transcript_path": str(env.tmp_path / "transcript.json"),
        "source": "startup",
    }
    return run_hook("session_start", start_input, env)
