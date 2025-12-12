# pyright: reportExplicitAny=false
"""Unit tests for the shared CLI utilities module."""

from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from oaps.cli._commands._shared import (
    ExitCode,
    exit_with_error,
    exit_with_success,
    format_json,
    format_table,
    format_yaml,
    get_error_console,
)


class TestExitCode:
    def test_exit_code_values_are_unique(self) -> None:
        values = [code.value for code in ExitCode]
        assert len(values) == len(set(values))

    def test_exit_code_is_int_subclass(self) -> None:
        assert issubclass(ExitCode, int)
        assert isinstance(ExitCode.SUCCESS, int)
        assert ExitCode.SUCCESS == 0
        assert ExitCode.LOAD_ERROR == 1
        assert ExitCode.VALIDATION_ERROR == 2
        assert ExitCode.NOT_FOUND == 3
        assert ExitCode.IO_ERROR == 4
        assert ExitCode.INTERNAL_ERROR == 5

    def test_exit_code_usable_with_system_exit(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            raise SystemExit(ExitCode.NOT_FOUND)
        assert exc_info.value.code == 3


class TestFormatJson:
    def test_format_empty_dict(self) -> None:
        result = format_json({})
        assert result == "{}"

    def test_format_nested_dict(self) -> None:
        data: dict[str, Any] = {"key": {"nested": "value", "number": 42}}
        result = format_json(data)
        assert '"key"' in result
        assert '"nested"' in result
        assert '"value"' in result
        assert "42" in result
        # Verify indentation
        assert "\n" in result

    def test_format_with_unicode(self) -> None:
        data: dict[str, Any] = {"greeting": "Hello, 世界!", "emoji": "🚀"}
        result = format_json(data)
        assert "Hello, 世界!" in result
        assert "🚀" in result

    def test_format_without_indent(self) -> None:
        data: dict[str, Any] = {"key": "value", "nested": {"inner": "data"}}
        result = format_json(data, indent=False)
        # Without indent, output should be compact (no newlines except possibly at end)
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_format_with_list_values(self) -> None:
        data: dict[str, Any] = {"items": ["a", "b", "c"], "numbers": [1, 2, 3]}
        result = format_json(data)
        assert '"items"' in result
        assert '"a"' in result
        assert '"b"' in result
        assert '"c"' in result
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestFormatYaml:
    def test_format_empty_dict(self) -> None:
        result = format_yaml({})
        assert result == "{}\n"

    def test_format_nested_dict(self) -> None:
        data: dict[str, Any] = {"key": {"nested": "value", "number": 42}}
        result = format_yaml(data)
        assert "key:" in result
        assert "nested: value" in result
        assert "number: 42" in result

    def test_format_with_unicode(self) -> None:
        data: dict[str, Any] = {"greeting": "Hello, 世界!", "emoji": "🚀"}
        result = format_yaml(data)
        assert "Hello, 世界!" in result
        assert "🚀" in result


class TestFormatTable:
    def test_format_simple_table(self) -> None:
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "25"]]
        result = format_table(headers, rows)
        assert "| Name" in result
        assert "| Age" in result
        assert "Alice" in result
        assert "30" in result
        assert "Bob" in result
        assert "25" in result
        # Verify table structure (separator row)
        assert "---" in result

    def test_format_empty_rows(self) -> None:
        headers = ["Column1", "Column2"]
        rows: list[list[str]] = []
        result = format_table(headers, rows)
        assert "| Column1" in result
        assert "| Column2" in result
        # Table should have headers even with no data rows

    def test_format_with_unicode(self) -> None:
        headers = ["名前", "年齢"]
        rows = [["太郎", "25"], ["花子", "30"]]
        result = format_table(headers, rows)
        assert "名前" in result
        assert "年齢" in result
        assert "太郎" in result
        assert "花子" in result


class TestGetErrorConsole:
    def test_returns_console_with_stderr(self) -> None:
        console = get_error_console()
        assert isinstance(console, Console)
        assert console.stderr is True


class TestExitWithError:
    def test_prints_error_message(self) -> None:
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=False)

        with pytest.raises(SystemExit):
            exit_with_error("Something went wrong", console=console)

        output = string_io.getvalue()
        assert "Error:" in output
        assert "Something went wrong" in output

    def test_raises_system_exit_with_code(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            exit_with_error("Test error", ExitCode.NOT_FOUND)
        assert exc_info.value.code == ExitCode.NOT_FOUND

    def test_uses_provided_console(self) -> None:
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=False)

        with pytest.raises(SystemExit) as exc_info:
            exit_with_error("Custom error message", ExitCode.IO_ERROR, console=console)

        assert exc_info.value.code == ExitCode.IO_ERROR
        output = string_io.getvalue()
        assert "Error:" in output
        assert "Custom error message" in output

    def test_defaults_to_internal_error(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            exit_with_error("Generic error")
        assert exc_info.value.code == ExitCode.INTERNAL_ERROR


class TestExitWithSuccess:
    def test_raises_system_exit_with_success_code(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            exit_with_success()
        assert exc_info.value.code == ExitCode.SUCCESS

    def test_prints_message_when_provided(self) -> None:
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=False)

        with pytest.raises(SystemExit):
            exit_with_success("Operation completed", console=console)

        output = string_io.getvalue()
        assert "Operation completed" in output

    def test_no_output_when_no_message(self) -> None:
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=False)

        with pytest.raises(SystemExit):
            exit_with_success(console=console)

        output = string_io.getvalue()
        assert output == ""

    def test_uses_provided_console(self) -> None:
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=False)

        with pytest.raises(SystemExit) as exc_info:
            exit_with_success("Custom message", console=console)

        assert exc_info.value.code == ExitCode.SUCCESS
        output = string_io.getvalue()
        assert "Custom message" in output
