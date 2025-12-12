# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Hook management commands for OAPS CLI."""

# Import command modules to register decorators
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

# Re-export exit codes
from ._exit_codes import (
    EXIT_INPUT_ERROR,
    EXIT_LOAD_ERROR,
    EXIT_NOT_FOUND,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
)

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
    "EXIT_INPUT_ERROR",
    "EXIT_LOAD_ERROR",
    "EXIT_NOT_FOUND",
    "EXIT_SUCCESS",
    "EXIT_VALIDATION_ERROR",
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
