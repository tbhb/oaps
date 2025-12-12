"""Cyclopts App definition for project commands."""

from cyclopts import App

app = App(
    name="project",
    help="Manage project state and Git operations",
    help_on_error=True,
)
