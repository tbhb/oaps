# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Config command app for managing OAPS configuration."""

# Import command modules to register commands with the app
# This must be done after app is imported but before it's used
from oaps.cli._commands._context import CLIContext, OutputFormat
from oaps.cli._commands._shared import ExitCode

from . import _read as _read, _validate as _validate, _write as _write
from ._app import app
from ._formatters import (
    format_json,
    format_plain,
    format_table,
    format_toml,
    format_yaml,
)

__all__ = [
    "CLIContext",
    "ExitCode",
    "OutputFormat",
    "app",
    "format_json",
    "format_plain",
    "format_table",
    "format_toml",
    "format_yaml",
]
