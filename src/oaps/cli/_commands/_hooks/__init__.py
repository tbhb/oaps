# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Hook management commands for OAPS CLI."""

# Import command modules to register decorators
# Re-export ExitCode from shared module
from oaps.cli._commands._shared import ExitCode

from . import (
    _candidates as _candidates,
    _debug as _debug,
    _errors as _errors,
    _list as _list,
    _stats as _stats,
    _status as _status,
    _test as _test,
    _validate as _validate,
)

# Re-export app
from ._app import app

# Re-export formatters
from ._formatters import (
    format_match_result,
    format_rule_detail,
    format_rule_json,
    format_rule_table,
    format_rule_yaml,
    format_source_table,
    format_validation_issues,
    rule_to_dict,
)

__all__ = [
    "ExitCode",
    "app",
    "format_match_result",
    "format_rule_detail",
    "format_rule_json",
    "format_rule_table",
    "format_rule_yaml",
    "format_source_table",
    "format_validation_issues",
    "rule_to_dict",
]
