# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# ruff: noqa: D415, FBT002
"""Commands for slash command management and and contextualization."""

from typing import Annotated

from cyclopts import Parameter

# Import command modules to register decorators
from . import _usage as _usage

# Re-export app
from ._app import app as app


@app.command(name="create")
def _create(
    command_name: str,
    /,
    plugin: Annotated[
        bool, Parameter(help="Create a plugin command (in commands/)")
    ] = False,
    project: Annotated[
        bool, Parameter(help="Create a project command (in .oaps/claude/commands/)")
    ] = False,
) -> None:
    """Create a new command

    Args:
        command_name: Name of the command to create
        plugin: Whether to create a plugin command
        project: Whether to create a project command
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"Creating {target} command: {command_name}")
    print("(Not yet implemented)")


@app.command(name="save")
def _save(
    command_name: str,
    /,
    message: Annotated[str, Parameter(help="Commit message for saving the command")],
    validate: Annotated[
        bool, Parameter(help="Whether to validate before saving")
    ] = True,
) -> None:
    """Save a project command

    Args:
        command_name: Name of the command to save
        message: Commit message for saving the command
        validate: Whether to validate before saving
    """
    print(f"Saving project command: {command_name}")
    print(f"Message: {message}")
    print(f"Validate: {validate}")
    print("(Not yet implemented)")


@app.command(name="validate")
def _validate(
    command_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Validate a plugin command")] = False,
    project: Annotated[bool, Parameter(help="Validate a project command")] = False,
) -> None:
    """Validate a command

    Args:
        command_name: Name of the command to validate
        plugin: Whether to validate a plugin command
        project: Whether to validate a project command
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"Validating {target} command: {command_name}")
    print("(Not yet implemented)")


@app.command(name="orient")
def _orient(
    command_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Orient for a plugin command")] = False,
    project: Annotated[bool, Parameter(help="Orient for a project command")] = False,
) -> None:
    """Provide static context for a command

    Outputs:
    - Environment summary (tool versions)
    - Available references with descriptions
    - Instructions to load specific context

    Args:
        command_name: Name of the command to provide context for
        plugin: Whether to provide context for a plugin command
        project: Whether to provide context for a project command
    """
    from oaps.context import CommandContext
    from oaps.utils import detect_tooling

    # Default to project when neither or both flags specified
    _target = "plugin" if plugin and not project else "project"
    _ = _target  # Will be used when resolution is implemented

    # Detect environment
    tools = detect_tooling()

    # Build template context
    _template_context = CommandContext(tool_versions=tools)

    # Build output
    output_parts: list[str] = []

    # Header section
    output_parts.append(f"## {command_name} command context\n")

    # Environment section
    output_parts.append("### Environment\n")
    for tool_name, version in tools.items():
        if version:
            output_parts.append(f"- {tool_name}: {version}")
    output_parts.append("")

    print("\n".join(output_parts))


@app.command(name="context")
def _context(
    command_name: str,
    /,
    plugin: Annotated[
        bool, Parameter(help="Load context for a plugin command")
    ] = False,
    project: Annotated[
        bool, Parameter(help="Load context for a project command")
    ] = False,
) -> None:
    """Provide dynamic context for a command

    Args:
        command_name: Name of the command to provide context for
        plugin: Whether to provide context for a plugin command
        project: Whether to provide context for a project command
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"# Context for {target} command: {command_name}")


if __name__ == "__main__":
    app()
