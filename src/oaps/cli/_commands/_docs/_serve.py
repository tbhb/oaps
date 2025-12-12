import socket
from typing import cast

from cyclopts import App
from zensical import serve

from oaps.utils import get_oaps_dir


def find_open_port() -> int:
    """Find an available port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        addr: tuple[str, int] = cast("tuple[str, int]", s.getsockname())
        return addr[1]


serve_cmd = App(name="serve", help="Serve internal docs")


@serve_cmd.default
def _serve_cmd() -> None:  # pyright: ignore[reportUnusedFunction]
    port = find_open_port()
    config_path = get_oaps_dir() / "mkdocs.yml"
    serve(
        config_file=str(config_path.absolute()),
        options={"dev_addr": f"localhost:{port}", "open": True},  # pyright: ignore[reportCallIssue]
    )
