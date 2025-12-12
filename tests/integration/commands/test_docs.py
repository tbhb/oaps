"""Integration tests for the docs command.

Note: The docs serve command starts a server, which is not suitable for
automated testing. These tests verify the command is registered and help
text works.
"""

from collections.abc import Callable

import pytest

from oaps.cli._commands._docs import app as docs_app


class TestDocsApp:
    def test_help_shows_serve_command(
        self,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("docs", "--help")

        captured = capsys.readouterr()
        assert "serve" in captured.out

    def test_app_name_is_docs(self) -> None:
        # cyclopts returns name as a tuple
        assert docs_app.name == ("docs",)
