"""Environment configuration for Claude Code CLI integration tests.

This module provides the ClaudeTestEnvironment class for creating isolated
test environments with proper directory structure, git initialization,
and marketplace configuration.
"""

import json
import logging
import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

_logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BASE_DELAY = 0.1


def _reap_zombies() -> int:
    """Reap any zombie child processes to free up process table entries.

    Returns:
        Number of zombie processes reaped.
    """
    reaped = 0
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            reaped += 1
        except ChildProcessError:
            break
    return reaped


def _compute_backoff_delay(attempt: int) -> float:
    """Compute exponential backoff delay for a retry attempt."""
    return _BASE_DELAY * (1 << attempt)


def _is_transient_error(returncode: int) -> bool:
    """Check if a process exit code indicates a transient resource error.

    Args:
        returncode: The process exit code.

    Returns:
        True if the error is likely transient and worth retrying.
    """
    # Negative codes are signals
    if returncode == -signal.SIGKILL:
        return True
    # Positive codes that may indicate resource exhaustion on macOS
    # 71 = EREMOTE (observed during resource pressure)
    return returncode in {71}


def _run_git_command_with_retry(
    args: list[str],
    cwd: str,
) -> subprocess.CompletedProcess[bytes]:
    """Run a git command with retry logic for transient resource errors.

    Retries on BlockingIOError (EAGAIN/EWOULDBLOCK) and CalledProcessError
    with SIGKILL or other transient exit codes that indicate resource exhaustion.

    Args:
        args: Command arguments (e.g., ["git", "init"]).
        cwd: Working directory for the command.

    Returns:
        Completed process result.

    Raises:
        BlockingIOError: If retries exhausted on resource unavailability.
        subprocess.CalledProcessError: If command fails for non-transient reasons.
    """
    last_exception: BlockingIOError | subprocess.CalledProcessError | None = None

    # Reap any zombie processes before attempting subprocess spawn
    _reap_zombies()

    for attempt in range(_MAX_RETRIES):
        try:
            return subprocess.run(  # noqa: S603
                args,
                cwd=cwd,
                capture_output=True,
                check=True,
            )
        except BlockingIOError as e:
            last_exception = e
            delay = _compute_backoff_delay(attempt)
            _logger.warning(
                "BlockingIOError on attempt %d/%d for %s, retrying in %.2fs: %s",
                attempt + 1,
                _MAX_RETRIES,
                args,
                delay,
                e,
            )
            time.sleep(delay)
            _reap_zombies()
        except subprocess.CalledProcessError as e:
            if _is_transient_error(e.returncode):
                last_exception = e
                delay = _compute_backoff_delay(attempt)
                _logger.warning(
                    "Transient error (code %d) on attempt %d/%d for %s, retrying in %.2fs",  # noqa: E501
                    e.returncode,
                    attempt + 1,
                    _MAX_RETRIES,
                    args,
                    delay,
                )
                time.sleep(delay)
                _reap_zombies()
            else:
                raise

    if last_exception is not None:
        raise last_exception

    msg = "Unexpected state: no exception but loop completed"
    raise RuntimeError(msg)


def _init_git_repo(path: Path) -> None:
    """Initialize a minimal git repository in the given path."""
    cwd = str(path)
    _run_git_command_with_retry(["git", "init"], cwd)
    _run_git_command_with_retry(
        ["git", "config", "user.email", "test@example.com"], cwd
    )
    _run_git_command_with_retry(["git", "config", "user.name", "Test User"], cwd)


@dataclass(frozen=True, slots=True)
class ClaudeTestEnvironment:
    """Isolated environment for Claude Code CLI integration tests.

    This class manages the directory structure required for testing
    OAPS hooks with the Claude Code CLI. It creates:
    - A test project directory with git initialization
    - A .oaps directory for OAPS configuration
    - A CLAUDE_HOME directory with marketplace configuration
    - Log directories for hook output

    Attributes:
        project_root: Test project directory.
        oaps_dir: .oaps directory within the project.
        claude_home: CLAUDE_HOME directory for Claude Code.
        logs_dir: .oaps/logs directory for log files.
        hooks_log_path: Path to .oaps/logs/hooks.log.
        session_id: UUID for this test session.
        oaps_repo_path: Path to actual OAPS repo (for marketplace).
    """

    project_root: Path
    oaps_dir: Path
    claude_home: Path
    logs_dir: Path
    hooks_log_path: Path
    session_id: str
    oaps_repo_path: Path
    _env_vars: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        tmp_path: Path,
        oaps_repo_path: Path,
    ) -> Self:
        """Create a new isolated test environment.

        This factory method initializes all required directories and
        configuration files for running Claude Code CLI integration tests.

        Args:
            tmp_path: Temporary directory from pytest fixture.
            oaps_repo_path: Path to the actual OAPS repository.

        Returns:
            A fully initialized ClaudeTestEnvironment.
        """
        # Create project directory structure
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize git repo
        _init_git_repo(project_root)

        # Create .oaps directory structure
        oaps_dir = project_root / ".oaps"
        oaps_dir.mkdir()

        logs_dir = oaps_dir / "logs"
        logs_dir.mkdir()

        hooks_log_path = logs_dir / "hooks.log"

        # Create state directories
        state_dir = oaps_dir / "state"
        state_dir.mkdir()
        sessions_dir = state_dir / "sessions"
        sessions_dir.mkdir()

        # Create CLAUDE_HOME directory structure
        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        plugins_dir = claude_home / "plugins"
        plugins_dir.mkdir()

        # Write marketplace configuration
        marketplace_config = {"oaps": {"installLocation": str(oaps_repo_path)}}
        marketplace_file = plugins_dir / "known_marketplaces.json"
        marketplace_file.write_text(json.dumps(marketplace_config))

        # Create session-env directory for hook environment files
        session_env_dir = claude_home / "session-env"
        session_env_dir.mkdir()

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Prepare environment variables
        env_vars = {
            "CLAUDE_HOME": str(claude_home),
            "OAPS_DIR": str(oaps_dir),
        }

        return cls(
            project_root=project_root,
            oaps_dir=oaps_dir,
            claude_home=claude_home,
            logs_dir=logs_dir,
            hooks_log_path=hooks_log_path,
            session_id=session_id,
            oaps_repo_path=oaps_repo_path,
            _env_vars=env_vars,
        )

    def get_env_vars(self) -> dict[str, str]:
        """Get environment variables for subprocess calls.

        Returns:
            Dictionary of environment variables to set for Claude CLI execution.
        """
        return dict(self._env_vars)

    def get_oaps_toml_path(self) -> Path:
        """Get the path to the oaps.toml configuration file.

        Returns:
            Path to .oaps/oaps.toml.
        """
        return self.oaps_dir / "oaps.toml"

    def get_transcript_path(self) -> Path:
        """Get the path to a mock transcript file.

        Returns:
            Path to a transcript file in the project root.
        """
        return self.project_root / "transcript.json"
