# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Log viewing and analysis commands for OAPS CLI."""

# Import command modules to register decorators
from . import _query as _query

# Re-export app
from ._app import app

# Re-export exit codes
from ._exit_codes import (
    EXIT_FILTER_ERROR,
    EXIT_LOAD_ERROR,
    EXIT_SOURCE_NOT_FOUND,
    EXIT_SUCCESS,
)

# Re-export source utilities
from ._sources import (
    LogSource,
    list_sessions,
    load_logs,
    resolve_source,
)

__all__ = [
    "EXIT_FILTER_ERROR",
    "EXIT_LOAD_ERROR",
    "EXIT_SOURCE_NOT_FOUND",
    "EXIT_SUCCESS",
    "LogSource",
    "app",
    "list_sessions",
    "load_logs",
    "resolve_source",
]
