# pyright: reportUnusedCallResult=false
"""OAPS API server command."""

from typing import Annotated, Literal, cast

from cyclopts import App, Parameter

app = App(name="serve", help="Run the OAPS API server", help_on_error=True)

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]
LoopImpl = Literal["auto", "asyncio", "uvloop"]
HttpImpl = Literal["auto", "h11", "httptools"]
WsImpl = Literal["auto", "none", "websockets", "wsproto"]
LifespanImpl = Literal["auto", "on", "off"]


@app.default
def serve(  # noqa: PLR0913
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
    import socket

    import uvicorn

    from oaps.utils import get_package_dir

    effective_port = port

    # Find available port if 0 is specified
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            addr = cast("tuple[str, int]", s.getsockname())
            effective_port = addr[1]

    # Dev mode implies reload with package directory
    effective_reload = reload or dev
    effective_reload_dirs = reload_dir
    if dev and reload_dir is None:
        effective_reload_dirs = [str(get_package_dir())]

    config: dict[str, object] = {
        "app": "oaps.server:app",
        "host": host,
        "port": effective_port,
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

    print(f"Starting OAPS API server on {host}:{effective_port}")
    uvicorn.run(**config)  # pyright: ignore[reportArgumentType]


if __name__ == "__main__":
    app()
