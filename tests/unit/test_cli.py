from typing import TYPE_CHECKING, cast

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
