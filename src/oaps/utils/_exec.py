"""Shell script execution utilities.

This module provides reusable utilities for executing shell commands and scripts
with proper timeout handling, output capture, and temporary file management.
"""

import contextlib
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# Default timeout in milliseconds
DEFAULT_TIMEOUT_MS: int = 10000  # 10 seconds

# Maximum output size in bytes
MAX_OUTPUT_BYTES: int = 102400  # 100KB


@dataclass(frozen=True, slots=True)
class ScriptConfig:
    """Configuration for script execution.

    Attributes:
        command: Single-line command to execute.
        script: Multi-line script content to execute via temp file.
        shell: Shell to use (default: /bin/sh for scripts, None for commands).
        cwd: Working directory for execution.
        env: Additional environment variables to set.
        stdin: Optional stdin data to pipe to the command.
        timeout_ms: Execution timeout in milliseconds.
    """

    command: str | None = None
    script: str | None = None
    shell: str | None = None
    cwd: str | Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    stdin: bytes | None = None
    timeout_ms: int = DEFAULT_TIMEOUT_MS


@dataclass(frozen=True, slots=True)
class ScriptResult:
    """Result from script execution.

    Attributes:
        success: Whether the command executed without errors.
        exit_code: Process exit code, or None if execution failed.
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        error: Error message if execution failed (timeout, not found, etc.).
        timed_out: Whether the command timed out.
        command_not_found: Whether the command was not found.
    """

    success: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    timed_out: bool = False
    command_not_found: bool = False


def truncate_output(output: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncate output to max bytes, preserving valid UTF-8.

    Args:
        output: The string to truncate.
        max_bytes: Maximum size in bytes.

    Returns:
        Truncated string with indicator if truncated.
    """
    if not output:
        return output

    encoded = output.encode("utf-8")
    if len(encoded) <= max_bytes:
        return output

    # Truncate at byte boundary, then decode safely
    truncated_bytes = encoded[:max_bytes]

    # Decode with error handling to avoid breaking UTF-8 sequences
    # Use 'ignore' to skip incomplete multi-byte sequences at the end
    truncated = truncated_bytes.decode("utf-8", errors="ignore")

    return truncated + "\n... [output truncated]"


def build_command(config: ScriptConfig) -> tuple[list[str], str | None]:
    """Build command list and determine if temp file is needed.

    Args:
        config: Script configuration.

    Returns:
        Tuple of (command list, temp script path or None).
    """
    if config.script:
        shell_cmd = config.shell or "/bin/sh"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            _ = f.write(config.script)
            return [shell_cmd, f.name], f.name

    if config.command:
        if config.shell:
            return [config.shell, "-c", config.command], None
        return shlex.split(config.command), None

    return [], None


def run_script(config: ScriptConfig) -> ScriptResult:
    """Execute a shell command or script.

    Supports both single-line commands and multi-line scripts (via temp file).
    Handles timeouts, missing commands, and captures stdout/stderr.

    Args:
        config: Script configuration specifying command, env, cwd, timeout, etc.

    Returns:
        ScriptResult with execution outcome.
    """
    cmd, temp_script_path = build_command(config)
    if not cmd:
        return ScriptResult(
            success=False,
            error="No command or script specified",
        )

    env = {**os.environ, **config.env}
    cwd = str(config.cwd) if config.cwd else None
    timeout_seconds = config.timeout_ms / 1000.0

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            env=env,
            cwd=cwd,
            input=config.stdin,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )

        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        return ScriptResult(
            success=True,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    except subprocess.TimeoutExpired:
        return ScriptResult(
            success=False,
            error=f"Command timed out after {timeout_seconds}s",
            timed_out=True,
        )
    except FileNotFoundError as e:
        return ScriptResult(
            success=False,
            error=str(e),
            command_not_found=True,
        )
    except Exception as e:  # noqa: BLE001
        return ScriptResult(
            success=False,
            error=str(e),
        )
    finally:
        if temp_script_path:
            with contextlib.suppress(OSError):
                Path(temp_script_path).unlink()
