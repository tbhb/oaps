# pyright: reportExplicitAny=false
"""Shared CLI utilities for commands.

This module provides common utilities used across CLI command implementations:
- Standardized exit codes
- Generic output formatters (JSON, YAML, table)
- Console utilities for error handling
"""

from enum import IntEnum
from typing import TYPE_CHECKING, Any, Never

if TYPE_CHECKING:
    from rich.console import Console

# Type alias for formattable data - uses Any to match library signatures
FormattableData = dict[str, Any]

__all__ = [
    "ExitCode",
    "FormattableData",
    "exit_with_error",
    "exit_with_success",
    "format_json",
    "format_table",
    "format_yaml",
    "get_error_console",
]


class ExitCode(IntEnum):
    """Standard exit codes for OAPS CLI commands."""

    SUCCESS = 0
    LOAD_ERROR = 1
    VALIDATION_ERROR = 2
    NOT_FOUND = 3
    IO_ERROR = 4
    INTERNAL_ERROR = 5


def format_json(data: FormattableData, *, indent: bool = True) -> str:
    """Format data as JSON.

    Args:
        data: Dictionary to format as JSON.
        indent: Whether to pretty-print with indentation.

    Returns:
        JSON-formatted string representation.
    """
    import orjson

    options = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(data, option=options).decode("utf-8")


def format_yaml(data: FormattableData) -> str:
    """Format data as YAML.

    Args:
        data: Dictionary to format as YAML.

    Returns:
        YAML-formatted string representation.
    """
    import yaml

    return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a Markdown table.

    Args:
        headers: Column headers for the table.
        rows: List of rows, where each row is a list of cell values.

    Returns:
        Markdown table string representation.
    """
    from pytablewriter import MarkdownTableWriter

    writer = MarkdownTableWriter(
        headers=headers,
        value_matrix=rows,
        margin=1,
    )
    return writer.dumps()


def get_error_console() -> Console:
    """Get a Rich console configured for error output to stderr.

    Returns:
        Console instance writing to stderr.
    """
    from rich.console import Console

    return Console(stderr=True)


def exit_with_error(
    message: str,
    code: ExitCode = ExitCode.INTERNAL_ERROR,
    *,
    console: Console | None = None,
) -> Never:
    """Print an error message and exit with the specified code.

    Args:
        message: The error message to display.
        code: The exit code to use (defaults to INTERNAL_ERROR).
        console: Optional Rich console for output. If not provided,
            a new stderr console will be created.

    Raises:
        SystemExit: Always raised with the specified exit code.
    """
    if console is None:
        console = get_error_console()

    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(code)


def exit_with_success(
    message: str | None = None,
    *,
    console: Console | None = None,
) -> Never:
    """Print an optional success message and exit with SUCCESS code.

    Args:
        message: Optional success message to display.
        console: Optional Rich console for output. If not provided and a message
            is given, a new stderr console will be created.

    Raises:
        SystemExit: Always raised with ExitCode.SUCCESS (0).
    """
    if message is not None:
        if console is None:
            console = get_error_console()
        console.print(message)
    raise SystemExit(ExitCode.SUCCESS)
