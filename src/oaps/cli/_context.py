# pyright: reportUnusedCallResult=false
# ruff: noqa: TC003  # Path needed at runtime for dataclass field; TRY300 pattern valid here
"""CLI context for global state management.

This module provides thread-safe context management for CLI options and
loaded configuration. The CLIContext is set once at CLI startup and
made available to all commands via contextvars.
"""

import contextvars
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from oaps.config import Config

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from oaps.utils import GitContext


class OutputFormat(StrEnum):
    """Supported output formats for commands."""

    TOML = "toml"
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    PLAIN = "plain"
    TEXT = "text"


# Thread-safe context variable for CLIContext
_current_cli_context: contextvars.ContextVar[CLIContext | None] = (
    contextvars.ContextVar("cli_context", default=None)
)


@dataclass(frozen=True, slots=True)
class CLIContext:
    """Global CLI context with configuration and options.

    This class provides thread-safe context management for passing global CLI
    options and configuration through the command hierarchy without explicit
    parameter threading. Uses contextvars for proper async/thread safety.

    Attributes:
        config: Loaded configuration object.
        verbose: Enable verbose output with additional details.
        quiet: Suppress non-essential output.
        no_color: Disable colored output.
        project_root: Resolved project root path.
        config_error: Error message if config loading failed.
        logger: Structured logger for CLI commands (writes to file only).
        git: Git repository context, or None if not in a git repository.
    """

    config: Config = field(repr=False)
    verbose: bool = False
    quiet: bool = False
    no_color: bool = False
    project_root: Path | None = None
    config_error: str | None = None
    logger: FilteringBoundLogger | None = field(default=None, repr=False)
    git: GitContext | None = None

    @classmethod
    def get_current(cls) -> CLIContext:
        """Get current active CLIContext, or create a default if not set.

        Returns:
            The currently active CLIContext, or a default instance if none is set.
        """
        ctx = _current_cli_context.get()
        if ctx is not None:
            return ctx

        # Create default context with empty config

        default_config = Config.from_dict({})
        return cls(config=default_config)

    @classmethod
    def set_current(cls, ctx: CLIContext) -> None:
        """Set the current active CLIContext.

        Args:
            ctx: The CLIContext to set as current.
        """
        _current_cli_context.set(ctx)

    @classmethod
    def reset(cls) -> None:
        """Reset to default context.

        This is primarily useful for testing to ensure a clean state between tests.
        """
        _current_cli_context.set(None)
