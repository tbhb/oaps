# pyright: reportAny=false, reportUnknownArgumentType=false
"""Unit tests for config validation."""

from pathlib import Path
from typing import Any

from oaps.config import (
    ConfigSource,
    ConfigSourceName,
    ValidationIssue,
    validate_config,
    validate_source,
)


class TestValidationIssue:
    def test_stores_all_attributes(self) -> None:
        issue = ValidationIssue(
            key="logging.level",
            message="Input should be 'debug', 'info', 'warning' or 'error'",
            expected="'debug', 'info', 'warning' or 'error'",
            actual="invalid",
            source="local",
            severity="error",
        )

        assert issue.key == "logging.level"
        assert issue.message == "Input should be 'debug', 'info', 'warning' or 'error'"
        assert issue.expected == "'debug', 'info', 'warning' or 'error'"
        assert issue.actual == "invalid"
        assert issue.source == "local"
        assert issue.severity == "error"

    def test_allows_none_for_optional_fields(self) -> None:
        issue = ValidationIssue(
            key="logging.level",
            message="Invalid value",
            expected=None,
            actual="invalid",
            source=None,
            severity="error",
        )

        assert issue.expected is None
        assert issue.source is None


class TestValidateConfig:
    def test_valid_config_returns_empty_list(self) -> None:
        config = {
            "logging": {"level": "debug", "format": "json", "file": ""},
            "project": {"name": "test", "version": "1.0.0"},
        }

        result = validate_config(config)

        assert result == []

    def test_minimal_config_returns_empty_list(self) -> None:
        result = validate_config({})

        assert result == []

    def test_partial_config_uses_defaults(self) -> None:
        config = {"logging": {"level": "warning"}}

        result = validate_config(config)

        assert result == []

    def test_invalid_log_level_returns_issue(self) -> None:
        config = {"logging": {"level": "invalid"}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "logging.level"
        assert "invalid" in issue.actual
        assert issue.severity == "error"
        assert issue.source is None

    def test_invalid_log_format_returns_issue(self) -> None:
        config = {"logging": {"format": "xml"}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "logging.format"
        assert issue.actual == "xml"
        assert issue.severity == "error"

    def test_wrong_type_for_log_level_returns_issue(self) -> None:
        config = {"logging": {"level": 123}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "logging.level"
        assert issue.actual == 123
        assert issue.severity == "error"

    def test_wrong_type_for_file_returns_issue(self) -> None:
        config = {"logging": {"file": ["list", "not", "string"]}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "logging.file"
        assert issue.severity == "error"

    def test_wrong_type_for_project_name_returns_issue(self) -> None:
        config = {"project": {"name": 123}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "project.name"
        assert issue.actual == 123

    def test_multiple_errors_returns_multiple_issues(self) -> None:
        config = {"logging": {"level": "bad", "format": "bad"}}

        result = validate_config(config)

        assert len(result) == 2
        keys = {issue.key for issue in result}
        assert keys == {"logging.level", "logging.format"}

    def test_unknown_section_ignored_in_lenient_mode(self) -> None:
        config = {
            "logging": {"level": "info"},
            "unknown": {"foo": "bar"},
        }

        result = validate_config(config, strict=False)

        assert result == []

    def test_unknown_key_in_section_ignored_in_lenient_mode(self) -> None:
        config = {"logging": {"level": "info", "unknown_key": "value"}}

        result = validate_config(config, strict=False)

        assert result == []

    def test_unknown_section_errors_in_strict_mode(self) -> None:
        config = {
            "logging": {"level": "info"},
            "unknown": {"foo": "bar"},
        }

        result = validate_config(config, strict=True)

        assert len(result) == 1
        assert result[0].key == "unknown"
        assert result[0].severity == "error"

    def test_unknown_key_in_section_errors_in_strict_mode(self) -> None:
        config = {"logging": {"level": "info", "unknown_key": "value"}}

        result = validate_config(config, strict=True)

        assert len(result) == 1
        assert result[0].key == "logging.unknown_key"
        assert result[0].severity == "error"


class TestValidateSource:
    def _make_source(
        self,
        name: ConfigSourceName,
        values: dict[str, Any],
        *,
        exists: bool = True,
        path: Path | None = None,
    ) -> ConfigSource:
        return ConfigSource(name=name, path=path, exists=exists, values=values)

    def test_valid_source_returns_empty_list(self) -> None:
        source = self._make_source(
            ConfigSourceName.PROJECT,
            {"logging": {"level": "debug"}},
        )

        result = validate_source(source)

        assert result == []

    def test_empty_source_returns_empty_list(self) -> None:
        source = self._make_source(ConfigSourceName.LOCAL, {})

        result = validate_source(source)

        assert result == []

    def test_nonexistent_source_returns_empty_list(self) -> None:
        source = self._make_source(
            ConfigSourceName.USER,
            {"logging": {"level": "invalid"}},
            exists=False,
        )

        result = validate_source(source)

        assert result == []

    def test_source_name_included_in_issues(self) -> None:
        source = self._make_source(
            ConfigSourceName.LOCAL,
            {"logging": {"level": "bad"}},
        )

        result = validate_source(source)

        assert len(result) == 1
        assert result[0].source == "local"

    def test_project_source_name_included(self) -> None:
        source = self._make_source(
            ConfigSourceName.PROJECT,
            {"logging": {"format": "invalid"}},
        )

        result = validate_source(source)

        assert len(result) == 1
        assert result[0].source == "project"

    def test_env_source_name_included(self) -> None:
        source = self._make_source(
            ConfigSourceName.ENV,
            {"project": {"name": 123}},
        )

        result = validate_source(source)

        assert len(result) == 1
        assert result[0].source == "env"

    def test_unknown_sections_ignored_in_source(self) -> None:
        source = self._make_source(
            ConfigSourceName.PROJECT,
            {
                "logging": {"level": "info"},
                "custom": {"key": "value"},
            },
        )

        result = validate_source(source)

        assert result == []

    def test_multiple_issues_all_have_source(self) -> None:
        source = self._make_source(
            ConfigSourceName.WORKTREE,
            {"logging": {"level": "x", "format": "y"}},
        )

        result = validate_source(source)

        assert len(result) == 2
        assert all(issue.source == "worktree" for issue in result)


class TestPydanticErrorExtraction:
    def test_enum_error_has_expected_values(self) -> None:
        config = {"logging": {"level": "invalid"}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        # Pydantic includes expected values in message or ctx
        assert issue.expected is not None or "debug" in issue.message.lower()

    def test_type_error_for_string_field(self) -> None:
        config = {"logging": {"file": {"nested": "dict"}}}

        result = validate_config(config)

        assert len(result) == 1
        issue = result[0]
        assert issue.key == "logging.file"
        assert "string" in issue.message.lower()

    def test_error_preserves_actual_value(self) -> None:
        config = {"project": {"version": ["1", "0", "0"]}}

        result = validate_config(config)

        assert len(result) == 1
        assert result[0].actual == ["1", "0", "0"]

    def test_nested_error_has_full_path(self) -> None:
        config = {"logging": {"level": "bad"}}

        result = validate_config(config)

        assert len(result) == 1
        assert result[0].key == "logging.level"
