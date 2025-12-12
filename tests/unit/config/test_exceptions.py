# pyright: reportAny=false
"""Unit tests for configuration exceptions.

These tests verify that exception constructors correctly store context
attributes. We don't test Python built-in behaviors (inheritance, str()).
"""

from pathlib import Path

from oaps.exceptions import ConfigLoadError, ConfigValidationError


class TestConfigLoadError:
    def test_stores_path_context(self) -> None:
        error = ConfigLoadError(
            "Invalid syntax",
            path=Path("/project/.oaps/oaps.toml"),
        )

        assert error.path == Path("/project/.oaps/oaps.toml")

    def test_stores_line_and_column_context(self) -> None:
        error = ConfigLoadError(
            "Parse error",
            path=Path("/config/file.toml"),
            line=15,
            column=8,
        )

        assert error.line == 15
        assert error.column == 8

    def test_context_fields_default_to_none(self) -> None:
        error = ConfigLoadError("Simple error")

        assert error.path is None
        assert error.line is None
        assert error.column is None


class TestConfigValidationError:
    def test_stores_validation_context(self) -> None:
        error = ConfigValidationError(
            "Invalid enum value",
            key="logging.level",
            value="verbose",
            expected="debug | info | warning | error",
            source="project",
        )

        assert error.key == "logging.level"
        assert error.value == "verbose"
        assert error.expected == "debug | info | warning | error"
        assert error.source == "project"

    def test_source_defaults_to_none(self) -> None:
        error = ConfigValidationError(
            "Error",
            key="key",
            value="v",
            expected="e",
        )

        assert error.source is None

    def test_value_accepts_any_type(self) -> None:
        # Validation errors can occur for any type of invalid value
        int_error = ConfigValidationError("E", key="k", value=123, expected="str")
        list_error = ConfigValidationError("E", key="k", value=[1, 2], expected="str")
        none_error = ConfigValidationError("E", key="k", value=None, expected="str")

        assert int_error.value == 123
        assert list_error.value == [1, 2]
        assert none_error.value is None
