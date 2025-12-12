"""OAPS CLI commands."""
# pyright: reportUnusedCallResult=false

from typing import TYPE_CHECKING

from ._agent import app as agent_app
from ._analyze import app as analyze_app
from ._command import app as command_app
from ._config import app as config_app
from ._context import CLIContext, OutputFormat
from ._docs import app as docs_app
from ._flow import app as flow_app
from ._hooks import app as hooks_app
from ._idea import app as idea_app
from ._logs import app as logs_app
from ._project import app as project_app
from ._repo import app as repo_app
from ._session import app as session_app
from ._shared import (
    ExitCode,
    FormattableData,
    exit_with_error,
    exit_with_success,
    format_json,
    format_table,
    format_yaml,
    get_error_console,
)
from ._skill import app as skill_app
from ._spec import app as spec_app
from ._start import app as start_app

if TYPE_CHECKING:
    from cyclopts import App

__all__ = [
    "CLIContext",
    "ExitCode",
    "FormattableData",
    "OutputFormat",
    "agent_app",
    "analyze_app",
    "command_app",
    "config_app",
    "docs_app",
    "exit_with_error",
    "exit_with_success",
    "flow_app",
    "format_json",
    "format_table",
    "format_yaml",
    "get_error_console",
    "hooks_app",
    "idea_app",
    "logs_app",
    "project_app",
    "repo_app",
    "session_app",
    "skill_app",
    "spec_app",
    "start_app",
]


def register_commands(app: App) -> None:
    app.command(agent_app)
    app.command(analyze_app)
    app.command(command_app)
    app.command(config_app)
    app.command(docs_app)
    app.command(flow_app)
    app.command(hooks_app)
    app.command(idea_app)
    app.command(logs_app)
    app.command(project_app)
    app.command(repo_app)
    app.command(session_app)
    app.command(skill_app)
    app.command(spec_app)
    app.command(start_app)

    @app.command(name="--prefix")
    def _prefix() -> None:  # pyright: ignore[reportUnusedFunction]
        """Show OAPS' install path."""
        from oaps.utils import get_package_dir

        print(get_package_dir())
