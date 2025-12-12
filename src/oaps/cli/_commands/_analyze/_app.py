"""Cyclopts App definition for analyze commands."""

from cyclopts import App

app = App(
    name="analyze", help="Analyze Claude Code usage and sessions", help_on_error=True
)
