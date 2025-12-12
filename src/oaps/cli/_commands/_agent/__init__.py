# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# ruff: noqa: D415, FBT002
"""Commands for agent management and and contextualization."""

from typing import Annotated

from cyclopts import App, Parameter

app = App(name="agent", help="Manage and contextualize subagents", help_on_error=True)


@app.command(name="create")
def _create(
    agent_name: str,
    /,
    plugin: Annotated[
        bool, Parameter(help="Create a plugin agent (in agents/)")
    ] = False,
    project: Annotated[
        bool, Parameter(help="Create a project agent (in .oaps/claude/agents/)")
    ] = False,
) -> None:
    """Create a new agent

    Args:
        agent_name: Name of the agent to create
        plugin: Whether to create a plugin agent
        project: Whether to create a project agent
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"Creating {target} agent: {agent_name}")
    print("(Not yet implemented)")


@app.command(name="save")
def _save(
    agent_name: str,
    /,
    message: Annotated[str, Parameter(help="Commit message for saving the agent")],
    validate: Annotated[
        bool, Parameter(help="Whether to validate before saving")
    ] = True,
) -> None:
    """Save a project agent

    Args:
        agent_name: Name of the agent to save
        message: Commit message for saving the agent
        validate: Whether to validate before saving
    """
    print(f"Saving project agent: {agent_name}")
    print(f"Message: {message}")
    print(f"Validate: {validate}")
    print("(Not yet implemented)")


@app.command(name="validate")
def _validate(
    agent_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Validate a plugin agent")] = False,
    project: Annotated[bool, Parameter(help="Validate a project agent")] = False,
) -> None:
    """Validate an agent

    Args:
        agent_name: Name of the agent to validate
        plugin: Whether to validate a plugin agent
        project: Whether to validate a project agent
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"Validating {target} agent: {agent_name}")
    print("(Not yet implemented)")


@app.command(name="orient")
def _orient(
    agent_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Orient for a plugin agent")] = False,
    project: Annotated[bool, Parameter(help="Orient for a project agent")] = False,
) -> None:
    """Provide static context for a agent

    Outputs:
    - Environment summary (tool versions)
    - Available references with descriptions
    - Instructions to load specific context

    Args:
        agent_name: Name of the agent to provide context for
        plugin: Whether to provide context for a plugin agent
        project: Whether to provide context for a project agent
    """
    from oaps.context import AgentContext
    from oaps.utils import detect_tooling

    # Default to project when neither or both flags specified
    _target = "plugin" if plugin and not project else "project"
    _ = _target  # Will be used when resolution is implemented

    # Detect environment
    tools = detect_tooling()

    # Build template context
    _template_context = AgentContext(tool_versions=tools)

    # Build output
    output_parts: list[str] = []

    # Header section
    output_parts.append(f"## {agent_name} agent context\n")

    # Environment section
    output_parts.append("### Environment\n")
    for tool_name, version in tools.items():
        if version:
            output_parts.append(f"- {tool_name}: {version}")
    output_parts.append("")

    print("\n".join(output_parts))


@app.command(name="context")
def _context(
    agent_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Load context for a plugin agent")] = False,
    project: Annotated[
        bool, Parameter(help="Load context for a project agent")
    ] = False,
) -> None:
    """Provide dynamic context for a command

    Args:
        agent_name: Name of the agent to provide context for
        plugin: Whether to provide context for a plugin agent
        project: Whether to provide context for a project agent
    """
    # Default to project when neither or both flags specified
    target = "plugin" if plugin and not project else "project"
    print(f"Context for {target} agent: {agent_name}")


if __name__ == "__main__":
    app()
