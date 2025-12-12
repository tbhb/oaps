"""Fixtures for script-based action testing.

Provides fixtures and factories for creating test scripts that can be used
with shell and python hook actions.
"""

import json
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from typing import final

import pytest


@pytest.fixture
def script_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test scripts.

    Returns:
        Path to the script directory.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    return scripts


def create_shell_script(script_dir: Path, name: str, content: str) -> Path:
    """Create a shell script in the script directory.

    Args:
        script_dir: Directory to create the script in.
        name: Script file name (without extension).
        content: Shell script content.

    Returns:
        Path to the created script.
    """
    script_path = script_dir / name
    script_path.write_text(f"#!/bin/sh\n{content}")
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    return script_path


def create_python_script(script_dir: Path, name: str, content: str) -> Path:
    """Create a Python script in the script directory.

    Args:
        script_dir: Directory to create the script in.
        name: Script file name (with .py extension).
        content: Python script content.

    Returns:
        Path to the created script.
    """
    script_path = script_dir / name
    script_path.write_text(f"#!/usr/bin/env python3\n{content}")
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    return script_path


@pytest.fixture
def echo_script(script_dir: Path) -> Path:
    """Create a shell script that echoes its stdin.

    Returns:
        Path to the echo script.
    """
    return create_shell_script(script_dir, "echo_stdin.sh", "cat")


@pytest.fixture
def exit_script(script_dir: Path) -> Callable[[int], Path]:
    """Factory for creating scripts that exit with a specific code.

    Returns:
        Factory function that takes exit code and returns script path.
    """

    def _create(exit_code: int) -> Path:
        return create_shell_script(
            script_dir, f"exit_{exit_code}.sh", f"exit {exit_code}"
        )

    return _create


@pytest.fixture
def json_response_script(script_dir: Path) -> Callable[[dict[str, object]], Path]:
    """Factory for creating scripts that output JSON responses.

    Returns:
        Factory function that takes a dict and returns script path.
    """
    counter = 0

    def _create(response: dict[str, object]) -> Path:
        nonlocal counter
        counter += 1
        json_str = json.dumps(response)
        return create_shell_script(
            script_dir,
            f"json_response_{counter}.sh",
            f"echo '{json_str}'",
        )

    return _create


@pytest.fixture
def stdin_to_json_script(script_dir: Path) -> Path:
    """Create a Python script that reads JSON from stdin and echoes it.

    Useful for testing that stdin is properly passed to scripts.

    Returns:
        Path to the script.
    """
    content = """
import json
import sys

data = json.load(sys.stdin)
print(json.dumps(data, indent=2))
"""
    return create_python_script(script_dir, "stdin_to_json.py", content)


@pytest.fixture
def transform_script(script_dir: Path) -> Callable[[str], Path]:
    """Factory for creating scripts that transform stdin with a command.

    Returns:
        Factory function that takes a transformation command and returns script path.
    """
    counter = 0

    def _create(transform_cmd: str) -> Path:
        nonlocal counter
        counter += 1
        return create_shell_script(
            script_dir,
            f"transform_{counter}.sh",
            transform_cmd,
        )

    return _create


@pytest.fixture
def slow_script(script_dir: Path) -> Callable[[float], Path]:
    """Factory for creating scripts that sleep for a given duration.

    Returns:
        Factory function that takes sleep duration and returns script path.
    """

    def _create(sleep_seconds: float) -> Path:
        return create_shell_script(
            script_dir,
            f"slow_{sleep_seconds}s.sh",
            f"sleep {sleep_seconds}",
        )

    return _create


@pytest.fixture
def env_echo_script(script_dir: Path) -> Callable[[str], Path]:
    """Factory for creating scripts that echo an environment variable.

    Returns:
        Factory function that takes var name and returns script path.
    """

    def _create(var_name: str) -> Path:
        return create_shell_script(
            script_dir,
            f"echo_{var_name}.sh",
            f'echo "${var_name}"',
        )

    return _create


@pytest.fixture
def python_action_module(script_dir: Path) -> Path:
    """Create a Python module with test action functions.

    The module provides several functions that can be used as python
    action entrypoints in tests:
    - noop: Does nothing, returns None
    - echo_input: Returns the hook input as a dict
    - raise_error: Raises a RuntimeError
    - return_json: Returns a JSON-serializable dict
    - modify_accumulator: Adds to the output accumulator

    Returns:
        Path to the Python module.
    """
    content = '''
"""Test action module for hook testing."""

import json


def noop(context, config, accumulator):
    """Do nothing."""
    pass


def echo_input(context, config, accumulator):
    """Return the hook input as JSON."""
    input_dict = context.hook_input.model_dump()
    accumulator.add_output(json.dumps(input_dict))


def raise_error(context, config, accumulator):
    """Raise a RuntimeError."""
    raise RuntimeError("Test error from python action")


def return_json(context, config, accumulator):
    """Add a JSON response to the accumulator."""
    accumulator.add_output(json.dumps({"status": "ok", "message": "test"}))


def block_action(context, config, accumulator):
    """Block the action."""
    accumulator.block("Blocked by python action")


def warn_action(context, config, accumulator):
    """Add a warning."""
    accumulator.add_warning("Warning from python action")


def get_tool_name(context, config, accumulator):
    """Return the tool name from a PreToolUse context."""
    if hasattr(context.hook_input, "tool_name"):
        accumulator.add_output(context.hook_input.tool_name)
    else:
        accumulator.add_output("N/A")
'''
    module_path = script_dir / "test_actions.py"
    module_path.write_text(content)
    return module_path


@pytest.fixture
def add_script_dir_to_path(script_dir: Path) -> Callable[[], Callable[[], None]]:
    """Factory that adds script_dir to sys.path.

    Returns:
        A function that adds script_dir to sys.path when called.
        The function also returns a cleanup function.
    """

    def _add() -> Callable[[], None]:
        script_dir_str = str(script_dir)
        if script_dir_str not in sys.path:
            sys.path.insert(0, script_dir_str)

        def _cleanup() -> None:
            if script_dir_str in sys.path:
                sys.path.remove(script_dir_str)

        return _cleanup

    return _add


@final
class ScriptRunner:
    """Helper class for running test scripts and capturing output."""

    def __init__(self, script_dir: Path) -> None:
        self._script_dir = script_dir

    @property
    def script_dir(self) -> Path:
        """The directory containing test scripts."""
        return self._script_dir

    def create_shell(self, name: str, content: str) -> Path:
        """Create a shell script.

        Args:
            name: Script name.
            content: Script content (without shebang).

        Returns:
            Path to the created script.
        """
        return create_shell_script(self._script_dir, name, content)

    def create_python(self, name: str, content: str) -> Path:
        """Create a Python script.

        Args:
            name: Script name (should end in .py).
            content: Script content (without shebang).

        Returns:
            Path to the created script.
        """
        return create_python_script(self._script_dir, name, content)

    def create_json_response(
        self, response: dict[str, object], name: str | None = None
    ) -> Path:
        """Create a script that outputs a JSON response.

        Args:
            response: Dict to output as JSON.
            name: Optional script name.

        Returns:
            Path to the created script.
        """
        script_name = name or "json_response.sh"
        json_str = json.dumps(response)
        return self.create_shell(script_name, f"echo '{json_str}'")


@pytest.fixture
def script_runner(script_dir: Path) -> ScriptRunner:
    """Create a ScriptRunner instance.

    Returns:
        ScriptRunner for creating and managing test scripts.
    """
    return ScriptRunner(script_dir)
