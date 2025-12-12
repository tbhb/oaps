# pyright: reportUnusedCallResult=false
# ruff: noqa: TC003  # Path needed at runtime for cyclopts parameter parsing
"""OAPS start command - launches all services."""

import socket
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, cast

import anyio
from cyclopts import App, Parameter

if TYPE_CHECKING:
    from oaps.supervisor import ServiceConfig

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]
LoopImpl = Literal["auto", "asyncio", "uvloop"]
HttpImpl = Literal["auto", "h11", "httptools"]
WsImpl = Literal["auto", "none", "websockets", "wsproto"]
LifespanImpl = Literal["auto", "on", "off"]

app = App(
    name="start",
    help="Start all OAPS services (API, docs, watcher)",
    help_on_error=True,
)


def find_open_port() -> int:
    """Find an available port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        addr: tuple[str, int] = cast("tuple[str, int]", s.getsockname())
        return addr[1]


@app.default
def start(  # noqa: PLR0913
    *,
    port: Annotated[
        int,
        Parameter(help="Port for the API server."),
    ] = 6277,
    docs_port: Annotated[
        int,
        Parameter(help="Port for the docs server."),
    ] = 6278,
    control_port: Annotated[
        int,
        Parameter(help="Port for the supervisor control API."),
    ] = 6279,
    dev: Annotated[
        bool,
        Parameter(help="Development mode: enable reload with oaps package directory."),
    ] = False,
    no_docs: Annotated[
        bool,
        Parameter(help="Disable the docs server."),
    ] = False,
    no_api: Annotated[
        bool,
        Parameter(help="Disable the API server."),
    ] = False,
    no_watcher: Annotated[
        bool,
        Parameter(help="Disable the file watcher."),
    ] = False,
) -> None:
    """Start all OAPS services.

    Launches the API server, documentation server, and file watcher
    as managed subprocesses. A control API is also started for
    managing the services at runtime.

    Services can be individually disabled using --no-docs, --no-api,
    or --no-watcher flags.
    """
    from ._runner import run_start
    from ._services import (
        create_api_service,
        create_docs_service,
        create_watcher_service,
    )

    configs: list[ServiceConfig] = []
    docs_service: ServiceConfig | None = None
    api_service: ServiceConfig | None = None

    # Add docs server if enabled
    if not no_docs:
        docs_service = create_docs_service(docs_port)
        configs.append(docs_service)

    # Add API server if enabled
    if not no_api:
        api_service = create_api_service(
            port, docs_service.port if docs_service else None, dev=dev
        )
        configs.append(api_service)

    # Add file watcher if enabled
    if not no_watcher:
        configs.append(create_watcher_service())

    if not configs:
        print("No services enabled. Use at least one service.")
        return

    # Print startup info
    print(f"Starting OAPS services (control API on port {control_port})")
    if api_service is not None:
        print(f"  API server: http://localhost:{api_service.port}")
    if docs_service is not None:
        print(f"  Docs server: http://localhost:{docs_service.port}")
    if not no_watcher:
        print("  File watcher: enabled")
    print()

    # Run the async supervisor
    anyio.run(run_start, configs, control_port)


@app.command(name="api")
def api(  # noqa: PLR0913
    *,
    host: Annotated[
        str,
        Parameter(help="Bind socket to this host."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        Parameter(
            help="Bind socket to this port. If 0, an available port is selected."
        ),
    ] = 6277,
    dev: Annotated[
        bool,
        Parameter(help="Development mode: enable reload with oaps package directory."),
    ] = False,
    reload: Annotated[
        bool,
        Parameter(help="Enable auto-reload."),
    ] = False,
    reload_dir: Annotated[
        list[str] | None,
        Parameter(help="Set reload directories explicitly."),
    ] = None,
    workers: Annotated[
        int | None,
        Parameter(help="Number of worker processes. Not valid with --reload."),
    ] = None,
    log_level: Annotated[
        LogLevel,
        Parameter(help="Log level."),
    ] = "info",
    access_log: Annotated[
        bool,
        Parameter(help="Enable access log."),
    ] = True,
    loop: Annotated[
        LoopImpl,
        Parameter(help="Event loop implementation."),
    ] = "auto",
    http: Annotated[
        HttpImpl,
        Parameter(help="HTTP protocol implementation."),
    ] = "auto",
    ws: Annotated[
        WsImpl,
        Parameter(help="WebSocket protocol implementation."),
    ] = "auto",
    lifespan: Annotated[
        LifespanImpl,
        Parameter(help="Lifespan implementation."),
    ] = "auto",
    timeout_keep_alive: Annotated[
        int,
        Parameter(
            help="Close Keep-Alive connections if no new data received in timeout."
        ),
    ] = 5,
    limit_concurrency: Annotated[
        int | None,
        Parameter(help="Maximum number of concurrent connections to allow."),
    ] = None,
    ssl_keyfile: Annotated[
        str | None,
        Parameter(help="SSL key file."),
    ] = None,
    ssl_certfile: Annotated[
        str | None,
        Parameter(help="SSL certificate file."),
    ] = None,
    proxy_headers: Annotated[
        bool,
        Parameter(
            help="Enable X-Forwarded-Proto, X-Forwarded-For for remote address info."
        ),
    ] = True,
    forwarded_allow_ips: Annotated[
        str | None,
        Parameter(help="Comma-separated list of IPs to trust with proxy headers."),
    ] = None,
    uds: Annotated[
        str | None,
        Parameter(help="Bind to a UNIX domain socket."),
    ] = None,
) -> None:
    """Run the OAPS API server using uvicorn."""
    import uvicorn

    from oaps.utils import get_package_dir

    from ._services import find_open_port

    # Find available port if 0 is specified
    port = find_open_port() if port == 0 else port

    # Dev mode implies reload with package directory
    effective_reload = reload or dev
    effective_reload_dirs = reload_dir
    if dev and reload_dir is None:
        effective_reload_dirs = [str(get_package_dir())]

    config: dict[str, object] = {
        "app": "oaps.server:app",
        "host": host,
        "port": port,
        "reload": effective_reload,
        "log_level": log_level,
        "access_log": access_log,
        "loop": loop,
        "http": http,
        "ws": ws,
        "lifespan": lifespan,
        "timeout_keep_alive": timeout_keep_alive,
        "proxy_headers": proxy_headers,
    }

    if effective_reload_dirs is not None:
        config["reload_dirs"] = effective_reload_dirs

    if workers is not None:
        config["workers"] = workers

    if limit_concurrency is not None:
        config["limit_concurrency"] = limit_concurrency

    if ssl_keyfile is not None:
        config["ssl_keyfile"] = ssl_keyfile

    if ssl_certfile is not None:
        config["ssl_certfile"] = ssl_certfile

    if forwarded_allow_ips is not None:
        config["forwarded_allow_ips"] = forwarded_allow_ips

    if uds is not None:
        config["uds"] = uds

    print(f"Starting OAPS API server on {host}:{port}")
    uvicorn.run(**config)  # pyright: ignore[reportArgumentType]


@app.command(name="docs")
def docs(
    port: Annotated[
        int,
        Parameter(
            help="Bind socket to this port. If 0, an available port is selected."
        ),
    ] = 6278,
) -> None:
    from zensical import serve

    from oaps.utils import get_oaps_dir

    from ._services import find_open_port

    port = find_open_port() if port == 0 else port
    config_path = get_oaps_dir() / "mkdocs.yml"
    serve(
        config_file=str(config_path.absolute()),
        options={"dev_addr": f"localhost:{port}", "open": False},  # pyright: ignore[reportCallIssue]
    )


@app.command(name="watcher")
def watcher(
    watch_dir: Annotated[Path | None, Parameter(help="Directory to watch.")] = None,
) -> None:
    """Run the OAPS file watcher service."""
    import contextlib

    from oaps.utils import get_worktree_root
    from oaps.utils._ignore import create_pathspec
    from oaps.watch import watch_directory

    watch_dir = watch_dir or get_worktree_root()

    # Create pathspec from gitignore files and defaults
    spec = create_pathspec(worktree_root=watch_dir)

    with contextlib.suppress(KeyboardInterrupt):
        watch_directory(watch_dir, pathspec=spec)


if __name__ == "__main__":
    app()
