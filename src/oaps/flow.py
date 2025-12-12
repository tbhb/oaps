"""Flow discovery, loading, and rendering for templated workflows."""

# ruff: noqa: PLC0415
# pyright: reportAny=false

import importlib.util
import sys
from dataclasses import dataclass
from os import getenv
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from jinja2 import Environment, FileSystemLoader, select_autoescape

from oaps.templating import parse_frontmatter

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from oaps.project import ProjectContext


class FlowContext(TypedDict):
    """Context for rendering flow templates.

    Attributes:
        flow: The dict returned by workflow.py:parse() or default argument handling.
        tool_versions: Detected tool versions from the environment.
        session_id: The Claude session ID from CLAUDE_SESSION_ID env var.
        session_state: Snapshot of session state key-value pairs.
        project: Project git context with changes, commits, etc.
    """

    flow: dict[str, object]
    tool_versions: dict[str, str | None]
    session_id: NotRequired[str | None]
    session_state: NotRequired[dict[str, object] | None]
    project: NotRequired[ProjectContext | None]


@dataclass(slots=True, frozen=True)
class FlowInfo:
    """Information about a discovered flow.

    Attributes:
        namespace: The flow namespace (e.g., 'dev').
        workflow: The workflow directory name (e.g., 'general').
        description: Human-readable description from WORKFLOW.md frontmatter.
        default: Whether this is the default workflow for its namespace.
        path: Path to the flow directory.
    """

    namespace: str
    workflow: str
    description: str
    default: bool
    path: Path

    @property
    def spec(self) -> str:
        """Return the flow spec string (namespace:workflow)."""
        return f"{self.namespace}:{self.workflow}"


def _get_flow_search_paths() -> list[Path]:
    """Get the paths to search for flows.

    Returns:
        List of paths to search, in priority order (project first, then plugin).
    """
    import subprocess

    from oaps.utils._claude_plugin import get_claude_plugin_dir
    from oaps.utils._paths import get_oaps_dir, get_worktree_root

    paths: list[Path] = []

    # Project flows first (.oaps/flows/)
    project_flows = get_oaps_dir() / "flows"
    if project_flows.is_dir():
        paths.append(project_flows)

    # Plugin flows from Claude plugin install location
    plugin_dir = get_claude_plugin_dir()
    if plugin_dir is not None:
        plugin_flows = plugin_dir / "flows"
        if plugin_flows.is_dir():
            paths.append(plugin_flows)

    # Fall back to repo's flows/ directory (for development)
    try:
        repo_flows = get_worktree_root() / "flows"
        if repo_flows.is_dir() and repo_flows not in paths:
            paths.append(repo_flows)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return paths


@dataclass(slots=True, frozen=True)
class FlowConfig:
    """Configuration parsed from WORKFLOW.md frontmatter.

    Attributes:
        description: Human-readable description of the workflow.
        default: Whether this is the default workflow for its namespace.
    """

    description: str
    default: bool


def load_flow_config(flow_dir: Path) -> FlowConfig:
    """Parse WORKFLOW.md frontmatter to get flow metadata.

    Args:
        flow_dir: Path to the flow directory.

    Returns:
        FlowConfig with description and default fields.
    """
    workflow_md = flow_dir / "WORKFLOW.md"
    if not workflow_md.is_file():
        return FlowConfig(description="", default=False)

    content = workflow_md.read_text(encoding="utf-8")
    frontmatter, _ = parse_frontmatter(content)

    description = str(frontmatter.get("description", "")) if frontmatter else ""
    default = bool(frontmatter.get("default", False)) if frontmatter else False

    return FlowConfig(description=description, default=default)


def discover_flows() -> dict[str, FlowInfo]:
    """Discover all available flows.

    Searches in both project (.oaps/flows/) and plugin (flows/) directories.
    Project flows take precedence over plugin flows with the same spec.

    Returns:
        Dict mapping flow spec (namespace:workflow) to FlowInfo.
    """
    flows: dict[str, FlowInfo] = {}

    # Search paths in reverse order so project flows override plugin flows
    for search_path in reversed(_get_flow_search_paths()):
        # Each subdirectory of search_path is a namespace
        for namespace_dir in search_path.iterdir():
            if not namespace_dir.is_dir():
                continue
            namespace = namespace_dir.name

            # Each subdirectory of namespace is a workflow
            for flow_dir in namespace_dir.iterdir():
                if not flow_dir.is_dir():
                    continue

                # Must have WORKFLOW.md to be a valid flow
                workflow_md = flow_dir / "WORKFLOW.md"
                if not workflow_md.is_file():
                    continue

                config = load_flow_config(flow_dir)
                workflow_name = flow_dir.name
                spec = f"{namespace}:{workflow_name}"

                flows[spec] = FlowInfo(
                    namespace=namespace,
                    workflow=workflow_name,
                    description=config.description,
                    default=config.default,
                    path=flow_dir,
                )

    return flows


def find_flow(namespace: str, workflow: str) -> Path | None:
    """Locate a specific flow directory.

    Args:
        namespace: The flow namespace (e.g., 'dev').
        workflow: The flow name (e.g., 'general').

    Returns:
        Path to the flow directory, or None if not found.
    """
    for search_path in _get_flow_search_paths():
        flow_dir = search_path / namespace / workflow
        workflow_md = flow_dir / "WORKFLOW.md"
        if workflow_md.is_file():
            return flow_dir

    return None


def find_default_flow(namespace: str) -> FlowInfo | None:
    """Find the default workflow for a namespace.

    Args:
        namespace: The flow namespace (e.g., 'dev').

    Returns:
        FlowInfo for the default workflow, or None if no default exists.
    """
    flows = discover_flows()
    for flow in flows.values():
        if flow.namespace == namespace and flow.default:
            return flow
    return None


def _load_workflow_module(flow_dir: Path) -> ModuleType:
    """Dynamically load workflow.py from a flow directory.

    Args:
        flow_dir: Path to the flow directory.

    Returns:
        The loaded module.

    Raises:
        FileNotFoundError: If workflow.py doesn't exist.
        ImportError: If the module cannot be loaded.
    """
    workflow_py = flow_dir / "workflow.py"
    if not workflow_py.is_file():
        msg = f"workflow.py not found in {flow_dir}"
        raise FileNotFoundError(msg)

    spec = importlib.util.spec_from_file_location("workflow", workflow_py)
    if spec is None or spec.loader is None:
        msg = f"Could not load workflow.py from {flow_dir}"
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow"] = module
    spec.loader.exec_module(module)

    return module


def execute_flow_parser(flow_dir: Path, args: list[str]) -> dict[str, object]:
    """Execute the parse() function from workflow.py, or use default handling.

    If workflow.py exists and has a parse() function, it is called with args.
    Otherwise, arguments are concatenated into a single prompt string.

    Args:
        flow_dir: Path to the flow directory.
        args: Arguments to pass to parse() or concatenate into a prompt.

    Returns:
        The dict returned by parse(), or {"prompt": " ".join(args)} if no workflow.py.

    Raises:
        AttributeError: If workflow.py exists but doesn't have a parse() function.
        TypeError: If parse() doesn't return a dict.
    """
    workflow_py = flow_dir / "workflow.py"
    if not workflow_py.is_file():
        # No workflow.py - use default argument handling
        return {"prompt": " ".join(args)}

    module = _load_workflow_module(flow_dir)

    if not hasattr(module, "parse"):
        msg = f"workflow.py in {flow_dir} must expose a parse() function"
        raise AttributeError(msg)

    parse_func = module.parse
    result: object = parse_func(args)

    if not isinstance(result, dict):
        msg = f"parse() in {flow_dir}/workflow.py must return a dict"
        raise TypeError(msg)

    return cast("dict[str, object]", result)


def _snapshot_session_state(session_id: str) -> dict[str, object] | None:
    """Snapshot all session state key-value pairs.

    Creates a plain dict copy of session state. Returns None if session
    store cannot be accessed.

    Args:
        session_id: The Claude session ID.

    Returns:
        Dict mapping state keys to values, or None if unavailable.
    """
    try:
        from oaps.utils import create_session_store

        store = create_session_store(session_id)
        result: dict[str, object] = {}
        for key in store:
            value = store[key]
            # Handle bytes values by decoding to string
            if isinstance(value, bytes):
                try:
                    result[key] = value.decode("utf-8")
                except UnicodeDecodeError:
                    result[key] = repr(value)
            else:
                result[key] = value
    except Exception:  # noqa: BLE001 - Graceful degradation
        return None
    else:
        return result


def build_flow_context(
    flow_data: dict[str, object],
    *,
    include_session: bool = True,
    include_project: bool = True,
) -> FlowContext:
    """Build complete flow context for template rendering.

    Assembles context from multiple sources with graceful degradation.

    Args:
        flow_data: Workflow-specific context from parse() function.
        include_session: Whether to include session context (requires
            CLAUDE_SESSION_ID env var).
        include_project: Whether to include project git context.

    Returns:
        FlowContext with all available context populated.
    """
    from oaps.utils import detect_tooling

    # Core context
    context: FlowContext = {
        "flow": flow_data,
        "tool_versions": detect_tooling(),
    }

    # Session context
    if include_session:
        session_id = getenv("CLAUDE_SESSION_ID")
        context["session_id"] = session_id
        if session_id:
            context["session_state"] = _snapshot_session_state(session_id)
        else:
            context["session_state"] = None

    # Project context
    if include_project:
        from oaps.project import get_project_context

        context["project"] = get_project_context()

    return context


def render_flow(flow_dir: Path, args: list[str]) -> str:
    """Render a flow's WORKFLOW.md template with context.

    Args:
        flow_dir: Path to the flow directory.
        args: Arguments to pass to the flow's parse() function.

    Returns:
        The rendered workflow content.
    """
    # Build context
    flow_data = execute_flow_parser(flow_dir, args)
    context = build_flow_context(flow_data)

    # Load and render WORKFLOW.md
    workflow_md = flow_dir / "WORKFLOW.md"
    content = workflow_md.read_text(encoding="utf-8")

    # Strip frontmatter if present
    frontmatter, body = parse_frontmatter(content)
    _ = frontmatter  # Currently unused but available for future metadata

    # Render the template
    env = Environment(
        autoescape=select_autoescape(),
        loader=FileSystemLoader(
            [
                flow_dir / "templates",
                flow_dir.parent / "_templates",
                flow_dir.parent.parent / "_templates",
            ],
        ),
    )
    return env.from_string(body).render(context)


def format_flow_not_found_error(spec: str, available_flows: dict[str, FlowInfo]) -> str:
    """Format a markdown error message when a flow is not found.

    Args:
        spec: The flow spec that was not found.
        available_flows: Dict of available flows.

    Returns:
        Formatted markdown error message.
    """
    lines = [
        "## Workflow Not Found",
        "",
        f"Could not find workflow `{spec}`.",
        "",
    ]

    if available_flows:
        lines.extend(
            [
                "### Available Workflows",
                "",
                "| Namespace | Workflow | Description |",
                "| --------- | -------- | ----------- |",
            ]
        )

        for flow in sorted(available_flows.values(), key=lambda f: f.spec):
            default_marker = " (default)" if flow.default else ""
            workflow_col = f"{flow.workflow}{default_marker}"
            lines.append(f"| {flow.namespace} | {workflow_col} | {flow.description} |")

        lines.append("")

    lines.extend(
        [
            "### Usage",
            "",
            "```",
            "/oaps:flow <namespace>:<workflow> [args...]",
            "```",
        ]
    )

    return "\n".join(lines)
