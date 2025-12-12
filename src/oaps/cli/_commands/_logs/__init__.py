# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Log viewing and analysis commands for OAPS CLI."""

# Import command modules to register decorators
# Re-export exit codes from shared
from oaps.cli._commands._shared import ExitCode

from . import _query as _query

# Re-export app
from ._app import app

# Re-export source utilities
from ._sources import (
    LogSource,
    list_sessions,
    load_logs,
    resolve_source,
)

__all__ = [
    "ExitCode",
    "LogSource",
    "app",
    "list_sessions",
    "load_logs",
    "resolve_source",
]
