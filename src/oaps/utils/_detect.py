"""Detection utilities for tooling and environment."""

import subprocess
import sys
import time

_MAX_RETRIES = 3
_BASE_DELAY = 0.1


def _run_with_retry(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run subprocess with retry on BlockingIOError.

    Args:
        cmd: Command to run.
        timeout: Timeout in seconds.

    Returns:
        CompletedProcess result.

    Raises:
        BlockingIOError: If all retries exhausted.
        subprocess.TimeoutExpired: If command times out.
        FileNotFoundError: If executable not found.
    """
    last_error: BlockingIOError | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            return subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except BlockingIOError as e:
            last_error = e
            delay = _BASE_DELAY * (1 << attempt)
            time.sleep(delay)

    if last_error is not None:
        raise last_error
    msg = "Unexpected state: no exception but loop completed"
    raise RuntimeError(msg)


def detect_tooling() -> dict[str, str | None]:
    """Detect Python version and installed tooling.

    Returns:
        A dict mapping tool name to version or None if not installed.
        Always includes 'python' with the current interpreter version.
    """
    tools: dict[str, str | None] = {}

    # Python version (always available)
    tools["python"] = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Check for common tools
    tool_checks = [
        ("basedpyright", ["uv", "run", "basedpyright", "--version"]),
        ("codespell", ["uv", "run", "codespell", "--version"]),
        ("ruff", ["uv", "run", "ruff", "--version"]),
        ("pytest", ["uv", "run", "pytest", "--version"]),
    ]

    for tool_name, cmd in tool_checks:
        try:
            result = _run_with_retry(cmd, timeout=5)
            if result.returncode == 0:
                # Extract version from first line
                version_line = result.stdout.strip().split("\n")[0]
                # Try to extract just the version number
                parts = version_line.split()
                tools[tool_name] = parts[-1] if parts else "installed"
            else:
                tools[tool_name] = None
        except (subprocess.TimeoutExpired, FileNotFoundError, BlockingIOError):
            tools[tool_name] = None

    return tools
