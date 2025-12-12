"""Claude CLI runner for integration tests.

This module provides the ClaudeRunner class for executing Claude Code CLI
commands in isolated test environments.
"""

import contextlib
import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import cast

from ._environment import ClaudeTestEnvironment


@dataclass(frozen=True, slots=True)
class ClaudeExecutionResult:
    """Result from running Claude CLI.

    Attributes:
        return_code: Process exit code.
        stdout: Standard output from the process.
        stderr: Standard error from the process.
        execution_time_ms: Execution time in milliseconds.
        json_output: Parsed JSON output if available, None otherwise.
    """

    return_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    json_output: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class ClaudeRunner:
    """Executes Claude CLI commands in test environment.

    This class wraps subprocess execution of the Claude Code CLI
    with proper environment configuration and output parsing.

    Attributes:
        env: The test environment configuration.
        timeout_seconds: Maximum execution time in seconds (default: 60).
    """

    env: ClaudeTestEnvironment
    timeout_seconds: float = 60.0

    def run_prompt(
        self,
        prompt: str,
        *,
        json_output: bool = True,
    ) -> ClaudeExecutionResult:
        """Execute a prompt using the Claude CLI.

        Runs `claude -p "prompt" [--output-format json]` in the test environment.

        Args:
            prompt: The prompt to send to Claude.
            json_output: Whether to request JSON output (default: True).

        Returns:
            ClaudeExecutionResult with return code, output, and timing.
        """
        # Build command
        cmd = ["claude", "-p", prompt]
        if json_output:
            cmd.extend(["--output-format", "json"])

        # Prepare environment
        process_env = os.environ.copy()
        process_env.update(self.env.get_env_vars())

        # Execute with timing
        start_time = time.perf_counter()
        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                env=process_env,
                cwd=str(self.env.project_root),
                timeout=self.timeout_seconds,
                check=False,
            )
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            # Parse JSON output if available
            parsed_json: dict[str, object] | None = None
            if json_output and result.stdout.strip():
                with contextlib.suppress(json.JSONDecodeError):
                    parsed_json = cast(dict[str, object], json.loads(result.stdout))

            return ClaudeExecutionResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time_ms=execution_time_ms,
                json_output=parsed_json,
            )
        except subprocess.TimeoutExpired:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            return ClaudeExecutionResult(
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout_seconds} seconds",
                execution_time_ms=execution_time_ms,
                json_output=None,
            )

    def run_command(
        self,
        args: list[str],
        *,
        stdin: str | None = None,
    ) -> ClaudeExecutionResult:
        """Execute a raw Claude CLI command.

        Runs `claude [args...]` in the test environment with optional stdin.

        Args:
            args: Command arguments to pass to claude.
            stdin: Optional input to send via stdin.

        Returns:
            ClaudeExecutionResult with return code, output, and timing.
        """
        # Build command
        cmd = ["claude", *args]

        # Prepare environment
        process_env = os.environ.copy()
        process_env.update(self.env.get_env_vars())

        # Execute with timing
        start_time = time.perf_counter()
        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                env=process_env,
                cwd=str(self.env.project_root),
                timeout=self.timeout_seconds,
                check=False,
            )
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            return ClaudeExecutionResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time_ms=execution_time_ms,
                json_output=None,
            )
        except subprocess.TimeoutExpired:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            return ClaudeExecutionResult(
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout_seconds} seconds",
                execution_time_ms=execution_time_ms,
                json_output=None,
            )
