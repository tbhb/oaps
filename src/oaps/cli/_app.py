"""The command-line interface for OAPS."""
# ruff: noqa: TC003  # Path needed at runtime for cyclopts parameter parsing

import sys
from pathlib import Path
from traceback import print_exc
from typing import Annotated

from cyclopts import App, Parameter
from rich.console import Console

try:
    from oaps.config import safe_load_config
    from oaps.utils import create_cli_logger

    from ._commands import register_commands
    from ._commands._context import CLIContext
except ImportError:
    print(  # noqa: T201
        "Failed to import commands. Exiting gracefully so that Claude Code does not crash."  # noqa: E501
    )
    print_exc()
    sys.exit(0)

app = App(
    name="oaps", help="An overengineered agentic project system.", help_on_error=True
)
register_commands(app)


def create_app(
    console: Console | None = None,
    error_console: Console | None = None,
    *,
    exit_on_error: bool = True,
) -> App:
    if console is None:
        console = Console()
    if error_console is None:
        error_console = Console(stderr=True)
    app = App(
        name="oaps",
        help="An overengineered agentic project system.",
        help_on_error=True,
        console=console,
        error_console=error_console,
        exit_on_error=exit_on_error,
    )

    @app.meta.default
    def _default(  # pyright: ignore[reportUnusedFunction]
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: Annotated[bool, Parameter(help="Enable verbose output")] = False,
        quiet: Annotated[bool, Parameter(help="Suppress non-essential output")] = False,
        no_color: Annotated[
            bool, Parameter(name="--no-color", help="Disable colored output")
        ] = False,
        config: Annotated[
            Path | None, Parameter(name="--config", help="Path to config file")
        ] = None,
        project_root: Annotated[
            Path | None, Parameter(name="--project-root", help="Path to project root")
        ] = None,
    ) -> None:
        """Launch OAPS CLI with global options.

        Args:
            tokens: Command tokens to pass to subcommands.
            verbose: Enable verbose output with additional details.
            quiet: Suppress non-essential output.
            no_color: Disable colored output.
            config: Explicit path to config file.
            project_root: Path to project root directory.
        """
        # Build CLI overrides from flags
        cli_overrides: dict[str, object] | None = None
        if verbose or quiet or no_color:
            cli_overrides = {}
            if verbose:
                cli_overrides["verbose"] = True
            if quiet:
                cli_overrides["quiet"] = True
            if no_color:
                cli_overrides["no_color"] = True

        # Load configuration
        loaded_config, config_error = safe_load_config(
            config_path=config,
            project_root=project_root,
            cli_overrides=cli_overrides,
        )

        # Create CLI logger from config settings
        cli_logger = create_cli_logger(
            level=loaded_config.logging.level.value,
            log_format=loaded_config.logging.format.value,  # type: ignore[arg-type]
            log_file=loaded_config.logging.file,
        )

        # Create and set CLI context
        ctx = CLIContext(
            config=loaded_config,
            verbose=verbose,
            quiet=quiet,
            no_color=no_color,
            project_root=project_root,
            config_error=config_error,
            logger=cli_logger,
        )
        CLIContext.set_current(ctx)

        try:
            app(tokens)
        finally:
            CLIContext.reset()

    register_commands(app)
    return app


@app.meta.default
def oaps_main(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    verbose: Annotated[bool, Parameter(help="Enable verbose output")] = False,
    quiet: Annotated[bool, Parameter(help="Suppress non-essential output")] = False,
    no_color: Annotated[
        bool, Parameter(name="--no-color", help="Disable colored output")
    ] = False,
    config: Annotated[
        Path | None, Parameter(name="--config", help="Path to config file")
    ] = None,
    project_root: Annotated[
        Path | None, Parameter(name="--project-root", help="Path to project root")
    ] = None,
) -> None:
    """Launch OAPS CLI with global options.

    Args:
        tokens: Command tokens to pass to subcommands.
        verbose: Enable verbose output with additional details.
        quiet: Suppress non-essential output.
        no_color: Disable colored output.
        config: Explicit path to config file.
        project_root: Path to project root directory.
    """
    # Build CLI overrides from flags
    cli_overrides: dict[str, object] | None = None
    if verbose or quiet or no_color:
        cli_overrides = {}
        if verbose:
            cli_overrides["verbose"] = True
        if quiet:
            cli_overrides["quiet"] = True
        if no_color:
            cli_overrides["no_color"] = True

    # Load configuration
    loaded_config, config_error = safe_load_config(
        config_path=config,
        project_root=project_root,
        cli_overrides=cli_overrides,
    )

    # Create CLI logger from config settings
    cli_logger = create_cli_logger(
        level=loaded_config.logging.level.value,
        log_format=loaded_config.logging.format.value,  # type: ignore[arg-type]
        log_file=loaded_config.logging.file,
    )

    # Create and set CLI context
    ctx = CLIContext(
        config=loaded_config,
        verbose=verbose,
        quiet=quiet,
        no_color=no_color,
        project_root=project_root,
        config_error=config_error,
        logger=cli_logger,
    )
    CLIContext.set_current(ctx)

    try:
        app(tokens)
    finally:
        CLIContext.reset()


def main() -> None:
    """Default entrypoint for the `oaps` CLI."""
    app = create_app()
    app()


if __name__ == "__main__":
    app()
