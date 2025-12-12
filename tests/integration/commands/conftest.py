from collections.abc import Callable

import pytest
from rich.console import Console

from oaps.cli import create_app


@pytest.fixture
def oaps_cli(console: Console) -> Callable[..., None]:
    """Create CLI app for testing.

    Returns a callable that runs the CLI and suppresses SystemExit.
    Use oaps_cli_with_exit_code when you need to check the exit code.
    """

    app = create_app(console=console, error_console=console)

    def _run(*args: str) -> None:
        """Run CLI app and suppress SystemExit from cyclopts."""

        try:
            app(args)
        except SystemExit:
            pass

    return _run


@pytest.fixture
def oaps_cli_with_exit_code(console: Console) -> Callable[..., int]:
    """Create CLI app for testing that returns the exit code.

    Use this fixture when tests need to verify the exit code.
    """

    app = create_app(console=console, error_console=console)

    def _run(*args: str) -> int:
        """Run CLI app and return exit code (0 if no SystemExit)."""

        try:
            app(args)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        else:
            return 0

    return _run
