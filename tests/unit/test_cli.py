import importlib
import sys
from typing import TYPE_CHECKING, cast

import pytest
from cyclopts import App

from oaps.cli._commands import register_commands

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestCommandRegistration:
    def test_register_commands_registers_subcommands(
        self, mocker: MockerFixture
    ) -> None:
        mock_app = mocker.MagicMock(spec=App)
        register_commands(mock_app)

        assert cast("int", mock_app.command.call_count) >= 5  # pyright: ignore[reportAny]


class TestImportErrorHandling:
    def test_handles_import_error_gracefully(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Import first to ensure it's in sys.modules
        import oaps.cli  # pyright: ignore[reportUnusedImport]

        original_modules = sys.modules.copy()

        try:
            if "oaps.cli" in sys.modules:
                del sys.modules["oaps.cli"]
            if "oaps.cli._commands" in sys.modules:
                del sys.modules["oaps.cli._commands"]

            mocker.patch.dict("sys.modules", {"oaps.cli._commands": None})
            with pytest.raises(SystemExit) as exc_info:
                import oaps.cli  # noqa: F401  # pyright: ignore[reportUnusedImport,reportShadowedImports]

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "Failed to import commands" in captured.out
            assert "Traceback" in captured.err or "ModuleNotFoundError" in captured.err
        finally:
            sys.modules.update(original_modules)
            if "oaps.cli" in sys.modules:
                importlib.reload(sys.modules["oaps.cli"])
