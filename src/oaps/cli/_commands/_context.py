# pyright: reportUnusedCallResult=false
# ruff: noqa: TC003, TRY300  # Path needed at runtime for dataclass field; TRY300 pattern valid here
"""CLI context for global state management.

This module provides thread-safe context management for CLI options and
loaded configuration. The CLIContext is set once at CLI startup and
made available to all commands via contextvars.
"""

import contextvars
import os
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from oaps.config import Config
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
        from oaps.config import Config

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


def load_config_safely(
    *,
    config_path: Path | None = None,
    project_root: Path | None = None,
    cli_overrides: dict[str, object] | None = None,
) -> tuple[Config, str | None]:
    """Load configuration with error handling.

    Attempts to load configuration and handles errors based on the
    OAPS_STRICT_CONFIG environment variable:
    - If unset or "0": warn to stderr and return empty config
    - If "1": fail fast with sys.exit(1)

    When config_path is provided, the file must exist (explicit user request).

    Args:
        config_path: Explicit path to config file (--config flag).
        project_root: Project root directory override (--project-root flag).
        cli_overrides: CLI argument overrides to pass to Config.load().

    Returns:
        Tuple of (Config, error_message). On success, error_message is None.
        On failure (non-strict mode), returns empty Config with error message.
    """
    from oaps.config import Config
    from oaps.exceptions import ConfigError

    strict_mode = os.environ.get("OAPS_STRICT_CONFIG", "0") == "1"

    try:
        if config_path is not None:
            # Explicit path - must exist
            if not config_path.exists():
                error_msg = f"Config file not found: {config_path}"
                # Always fail for explicit path
                print(f"Error: {error_msg}", file=sys.stderr)
                sys.exit(1)
            return Config.from_file(config_path), None

        # Normal load with discovery
        config = Config.load(
            project_root=project_root,
            include_env=True,
            include_cli=cli_overrides is not None,
            cli_overrides=cli_overrides,
        )
        return config, None

    except ConfigError as e:
        error_msg = str(e)
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
        else:
            print(
                f"Warning: Failed to load config: {error_msg}",
                file=sys.stderr,
            )
            return Config.from_dict({}), error_msg

    except FileNotFoundError as e:
        error_msg = str(e)
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
        else:
            print(
                f"Warning: Config file not found: {error_msg}",
                file=sys.stderr,
            )
            return Config.from_dict({}), error_msg

    except OSError as e:
        error_msg = f"Failed to load config: {e}"
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Warning: {error_msg}", file=sys.stderr)
            return Config.from_dict({}), error_msg
