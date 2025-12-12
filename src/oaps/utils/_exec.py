"""Execution utilities for shell scripts and Python functions.

This module provides reusable utilities for executing shell commands, scripts,
and Python functions with proper timeout handling, output capture, and error
management.
"""

import concurrent.futures
import contextlib
import importlib
import os
import shlex
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

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


@dataclass(frozen=True, slots=True)
class PythonConfig:
    """Configuration for Python function execution.

    Attributes:
        entrypoint: Function reference as "module.path:function_name".
        timeout_ms: Execution timeout in milliseconds.
    """

    entrypoint: str
    timeout_ms: int = DEFAULT_TIMEOUT_MS


@dataclass(frozen=True, slots=True)
class PythonResult[T]:
    """Result from Python function execution.

    Attributes:
        success: Whether the function executed without errors.
        result: The return value from the function, or None if execution failed.
        error: Error message if execution failed.
        error_type: Type of error that occurred.
    """

    success: bool
    result: T | None = None
    error: str | None = None
    error_type: (
        Literal[
            "invalid_entrypoint",
            "import_error",
            "not_callable",
            "not_found",
            "timeout",
            "execution_error",
        ]
        | None
    ) = None


def parse_entrypoint(entrypoint: str) -> tuple[str, str] | None:
    """Parse an entrypoint string into module path and function name.

    Args:
        entrypoint: Function reference as "module.path:function_name".

    Returns:
        Tuple of (module_path, function_name) or None if invalid format.
    """
    if ":" not in entrypoint:
        return None
    return entrypoint.rsplit(":", 1)  # pyright: ignore[reportReturnType]


# Type alias for any callable loaded dynamically
type _LoadedCallable = Callable[..., object]


def _load_callable(entrypoint: str) -> PythonResult[_LoadedCallable]:
    """Load a callable from an entrypoint string.

    Args:
        entrypoint: Function reference as "module.path:function_name".

    Returns:
        PythonResult with the callable on success, or error details on failure.
    """
    parsed = parse_entrypoint(entrypoint)
    if parsed is None:
        return PythonResult(
            success=False,
            error=f"Invalid entrypoint format: {entrypoint}",
            error_type="invalid_entrypoint",
        )

    module_path, function_name = parsed

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        return PythonResult(
            success=False,
            error=f"Failed to import module '{module_path}': {e}",
            error_type="import_error",
        )

    try:
        func = getattr(module, function_name)  # pyright: ignore[reportAny]
    except AttributeError as e:
        return PythonResult(
            success=False,
            error=f"Function not found: {module_path}:{function_name} ({e})",
            error_type="not_found",
        )

    if not callable(func):  # pyright: ignore[reportAny]
        return PythonResult(
            success=False,
            error=f"Entrypoint '{entrypoint}' is not callable",
            error_type="not_callable",
        )

    return PythonResult(success=True, result=func)


def run_python[T](
    config: PythonConfig,
    *args: object,
    reraise: tuple[type[BaseException], ...] = (),
    **kwargs: object,
) -> PythonResult[T]:
    """Execute a Python function by entrypoint with timeout.

    Imports the module, retrieves the function, and executes it with the provided
    arguments. Uses ThreadPoolExecutor for timeout enforcement.

    Args:
        config: Python execution configuration with entrypoint and timeout.
        *args: Positional arguments to pass to the function.
        reraise: Tuple of exception types that should be re-raised instead of
            being converted to error results. Useful for control-flow exceptions
            like BlockHook that callers need to handle specially.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        PythonResult with execution outcome and return value.

    Raises:
        Any exception type specified in `reraise` if raised by the function.
    """
    load_result = _load_callable(config.entrypoint)
    if not load_result.success:
        return PythonResult(
            success=False,
            error=load_result.error,
            error_type=load_result.error_type,
        )

    # This is guaranteed to be non-None when success is True
    func = load_result.result
    if func is None:  # pragma: no cover - defensive check
        return PythonResult(
            success=False,
            error="Internal error: callable is None",
            error_type="execution_error",
        )
    timeout_seconds = config.timeout_ms / 1000.0

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                # The callable returns object, but callers annotate the expected type
                result = future.result(timeout=timeout_seconds)
                return PythonResult(success=True, result=cast("T", result))
            except concurrent.futures.TimeoutError:
                return PythonResult(
                    success=False,
                    error=f"Function timed out after {timeout_seconds}s",
                    error_type="timeout",
                )
    except BaseException as e:
        # Re-raise specified exception types
        if reraise and isinstance(e, reraise):
            raise
        return PythonResult(
            success=False,
            error=f"Execution failed: {e}",
            error_type="execution_error",
        )
