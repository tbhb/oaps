"""Service configuration helpers for the start command.

This module provides factory functions for creating ServiceConfig instances
for the managed services: API server, docs server, and file watcher.
"""

import socket
from pathlib import Path  # noqa: TC003 - Used in runtime type annotations
from typing import cast

from oaps.supervisor import ServiceConfig
from oaps.utils import get_oaps_dir, get_worktree_root


def find_open_port(host: str = "localhost") -> int:
    """Find an available port on the given host.

    Note: There is an inherent TOCTOU race condition between discovering
    the port and binding to it. The service should handle EADDRINUSE
    gracefully if another process claims the port first.

    Args:
        host: The host to bind to for port discovery.

    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))
        addr = cast("tuple[str, int]", sock.getsockname())
        return addr[1]


def get_mkdocs_path() -> Path:
    """Get the path to the mkdocs.yml configuration file.

    Returns:
        Path to the mkdocs.yml file in the .oaps directory.
    """
    return get_oaps_dir() / "mkdocs.yml"


def create_docs_service(port: int) -> ServiceConfig:
    """Create a service configuration for the docs server.

    Uses zensical to serve documentation with live reload.

    Args:
        port: The port to serve docs on.

    Returns:
        ServiceConfig for the docs subprocess.
    """
    command = (
        "uv",
        "run",
        "oaps",
        "start",
        "docs",
        "--port",
        str(port),
    )

    return ServiceConfig(
        name="docs",
        command=command,
        cwd=get_worktree_root(),
        port=port,
        startup_timeout=30.0,
        shutdown_timeout=5.0,
        max_restarts=3,
    )


def create_api_service(
    port: int, docs_port: int | None, *, dev: bool = False
) -> ServiceConfig:
    """Create a service configuration for the API server.

    Runs uvicorn with the OAPS FastAPI application. Optionally passes
    the docs port via environment variable for proxying.

    Args:
        port: The port to serve the API on.
        docs_port: The port where docs are served, or None if disabled.
        dev: Whether to run in development mode with reload enabled.

    Returns:
        ServiceConfig for the API subprocess.
    """
    env: dict[str, str] = {}
    if docs_port is not None:
        env["OAPS_DOCS_PORT"] = str(docs_port)

    command = ("uv", "run", "oaps", "start", "api", "--port", str(port))
    if dev:
        command += ("--dev",)

    return ServiceConfig(
        name="api",
        command=command,
        cwd=get_worktree_root(),
        env=env,
        port=port,
        startup_timeout=30.0,
        shutdown_timeout=10.0,
        max_restarts=5,
    )


def create_watcher_service() -> ServiceConfig:
    """Create a service configuration for the file watcher.

    Runs the watchfiles-based file watcher that monitors the project
    directory for changes.

    Returns:
        ServiceConfig for the watcher subprocess.
    """
    return ServiceConfig(
        name="watcher",
        command=("uv", "run", "oaps", "start", "watcher"),
        cwd=get_worktree_root(),
        startup_timeout=10.0,
        shutdown_timeout=2.0,
        max_restarts=5,
    )
