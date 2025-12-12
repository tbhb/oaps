# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnusedImport=false
# ruff: noqa: D415
"""Commands for specification creation and management."""

from oaps.cli._commands._context import CLIContext, OutputFormat

# Import ExitCode from shared module
from oaps.cli._commands._shared import ExitCode

# Import porcelain commands to register them with the app
# Import requirement commands to register them with the req_app
# Import test commands to register them with the test_app
# Import history commands to register them with the history_app
from . import (
    _history_commands,  # noqa: F401
    _porcelain,  # noqa: F401
    _req_commands,  # noqa: F401
    _test_commands,  # noqa: F401
)

# Import app from _app module
from ._app import app

# Import and re-export error handling
from ._errors import exit_code_for_exception

# Import and re-export helper functions
from ._helpers import (
    get_requirement_manager,
    get_test_manager,
    parse_qualified_id,
    requirement_to_dict,
    sync_result_to_dict,
    test_to_dict,
)

# Import and re-export output formatters
from ._output import (
    SpecData,
    format_ids,
    format_json,
    format_requirement_info,
    format_requirement_table,
    format_spec_info,
    format_spec_table,
    format_sync_result,
    format_table,
    format_test_info,
    format_test_table,
    format_validation_table,
    format_yaml,
)

# Legacy EXIT_* constants - deprecated, use ExitCode instead
EXIT_SUCCESS: int = ExitCode.SUCCESS
EXIT_NOT_FOUND: int = ExitCode.NOT_FOUND
EXIT_VALIDATION_ERROR: int = ExitCode.VALIDATION_ERROR
EXIT_CANCELLED: int = ExitCode.NOT_FOUND  # Maps to NOT_FOUND for cancellation
EXIT_IO_ERROR: int = ExitCode.IO_ERROR
EXIT_INTERNAL_ERROR: int = ExitCode.INTERNAL_ERROR

__all__ = [
    "EXIT_CANCELLED",
    "EXIT_INTERNAL_ERROR",
    "EXIT_IO_ERROR",
    "EXIT_NOT_FOUND",
    "EXIT_SUCCESS",
    "EXIT_VALIDATION_ERROR",
    "CLIContext",
    "ExitCode",
    "OutputFormat",
    "SpecData",
    "app",
    "exit_code_for_exception",
    "format_ids",
    "format_json",
    "format_requirement_info",
    "format_requirement_table",
    "format_spec_info",
    "format_spec_table",
    "format_sync_result",
    "format_table",
    "format_test_info",
    "format_test_table",
    "format_validation_table",
    "format_yaml",
    "get_requirement_manager",
    "get_test_manager",
    "parse_qualified_id",
    "requirement_to_dict",
    "sync_result_to_dict",
    "test_to_dict",
]


@app.command(name="list-templates")
def _list_templates() -> None:
    """List available specification templates"""
    from oaps.templating import discover_skill_templates

    templates = discover_skill_templates("spec-writing")

    if not templates:
        print("No templates found.")
        print("Check that the spec-writing skill is installed.")
        return

    print("## Available specification templates\n")
    for name, info in sorted(templates.items()):
        source_label = f" ({info.source})" if info.source == "override" else ""
        print(f"- **{name}**{source_label}: {info.description}")


if __name__ == "__main__":
    app()
