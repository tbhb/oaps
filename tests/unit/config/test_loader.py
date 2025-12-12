# pyright: reportAny=false, reportUnknownArgumentType=false
import copy
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.config._loader import (
    _parse_env_value,
    deep_merge,
    parse_env_vars,
    read_toml_file,
    set_nested_key,
)
from oaps.exceptions import ConfigLoadError

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestReadTomlFile:
    def test_parses_valid_toml(self, fs: FakeFilesystem) -> None:
        content = """
[section]
key = "value"
number = 42
"""
        path = Path("/test/config.toml")
        fs.create_file(path, contents=content)

        result = read_toml_file(path)

        assert result == {"section": {"key": "value", "number": 42}}

    def test_raises_file_not_found_for_missing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/missing.toml")

        with pytest.raises(FileNotFoundError):
            read_toml_file(path)

    def test_raises_config_load_error_for_invalid_toml(
        self, fs: FakeFilesystem
    ) -> None:
        content = """
[section
key = "unclosed bracket"
"""
        path = Path("/test/invalid.toml")
        fs.create_file(path, contents=content)

        with pytest.raises(ConfigLoadError) as exc_info:
            read_toml_file(path)

        error = exc_info.value
        assert error.path == path
        assert error.line is not None
        assert error.column is not None

    def test_config_load_error_includes_line_and_column(
        self, fs: FakeFilesystem
    ) -> None:
        content = """[valid]
key = "value"

[invalid section
"""
        path = Path("/test/syntax_error.toml")
        fs.create_file(path, contents=content)

        with pytest.raises(ConfigLoadError) as exc_info:
            read_toml_file(path)

        error = exc_info.value
        assert error.line == 4
        assert error.column is not None

    def test_config_load_error_chains_original_exception(
        self, fs: FakeFilesystem
    ) -> None:
        content = "[bad"
        path = Path("/test/bad.toml")
        fs.create_file(path, contents=content)

        with pytest.raises(ConfigLoadError) as exc_info:
            read_toml_file(path)

        assert exc_info.value.__cause__ is not None
        assert "TOMLDecodeError" in type(exc_info.value.__cause__).__name__

    def test_parses_complex_toml_structure(self, fs: FakeFilesystem) -> None:
        content = """
name = "test-project"
version = "1.0.0"

[database]
host = "localhost"
port = 5432
enabled = true

[database.connection]
timeout = 30
retries = 3

[[servers]]
name = "alpha"
ip = "10.0.0.1"

[[servers]]
name = "beta"
ip = "10.0.0.2"
"""
        path = Path("/test/complex.toml")
        fs.create_file(path, contents=content)

        result = read_toml_file(path)

        assert result["name"] == "test-project"
        assert result["version"] == "1.0.0"
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["database"]["enabled"] is True
        assert result["database"]["connection"]["timeout"] == 30
        servers = result["servers"]
        assert isinstance(servers, list)
        assert len(servers) == 2
        assert servers[0]["name"] == "alpha"

    def test_parses_empty_toml_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/empty.toml")
        fs.create_file(path, contents="")

        result = read_toml_file(path)

        assert result == {}


class TestDeepMerge:
    def test_merges_nested_dictionaries(self) -> None:
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3}}

        result = deep_merge(base, override)

        assert result == {"a": {"x": 1, "y": 3}}

    def test_replaces_arrays_entirely(self) -> None:
        base = {"tags": ["a", "b"]}
        override = {"tags": ["x"]}

        result = deep_merge(base, override)

        assert result == {"tags": ["x"]}

    def test_replaces_scalars(self) -> None:
        base = {"level": "info"}
        override = {"level": "debug"}

        result = deep_merge(base, override)

        assert result == {"level": "debug"}

    def test_preserves_base_keys_not_in_override(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"a": 10}

        result = deep_merge(base, override)

        assert result == {"a": 10, "b": 2}

    def test_adds_new_keys_from_override(self) -> None:
        base = {"a": 1}
        override = {"b": 2}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 2}

    def test_deeply_nested_merge(self) -> None:
        base = {"outer": {"inner": {"key1": "value1", "key2": "value2"}}}
        override = {"outer": {"inner": {"key2": "override", "key3": "new"}}}

        result = deep_merge(base, override)

        assert result == {
            "outer": {"inner": {"key1": "value1", "key2": "override", "key3": "new"}}
        }

    def test_does_not_mutate_base(self) -> None:
        base = {"a": {"x": 1}}
        base_copy = copy.deepcopy(base)
        override = {"a": {"y": 2}}

        deep_merge(base, override)

        assert base == base_copy

    def test_does_not_mutate_override(self) -> None:
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        override_copy = copy.deepcopy(override)

        deep_merge(base, override)

        assert override == override_copy

    def test_empty_base(self) -> None:
        base: dict[str, object] = {}
        override = {"a": 1, "b": {"c": 2}}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": {"c": 2}}

    def test_empty_override(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        override: dict[str, object] = {}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": {"c": 2}}

    def test_both_empty(self) -> None:
        result = deep_merge({}, {})

        assert result == {}

    def test_override_dict_replaces_scalar(self) -> None:
        base = {"a": "scalar"}
        override = {"a": {"nested": "dict"}}

        result = deep_merge(base, override)

        assert result == {"a": {"nested": "dict"}}

    def test_override_scalar_replaces_dict(self) -> None:
        base = {"a": {"nested": "dict"}}
        override = {"a": "scalar"}

        result = deep_merge(base, override)

        assert result == {"a": "scalar"}

    def test_override_list_replaces_dict(self) -> None:
        base = {"a": {"nested": "dict"}}
        override = {"a": [1, 2, 3]}

        result = deep_merge(base, override)

        assert result == {"a": [1, 2, 3]}

    def test_empty_list_in_override_replaces_base_list(self) -> None:
        base = {"tags": ["a", "b", "c"]}
        override = {"tags": []}

        result = deep_merge(base, override)

        assert result == {"tags": []}

    def test_none_value_in_override(self) -> None:
        base = {"a": "value"}
        override = {"a": None}

        result = deep_merge(base, override)

        assert result == {"a": None}

    def test_complex_realistic_config(self) -> None:
        base = {
            "logging": {"level": "info", "format": "json", "file": "/var/log/app.log"},
            "project": {"name": "my-project", "version": "1.0.0"},
            "features": ["auth", "api", "ui"],
        }
        override = {
            "logging": {"level": "debug"},
            "features": ["auth"],
        }

        result = deep_merge(base, override)

        assert result == {
            "logging": {
                "level": "debug",
                "format": "json",
                "file": "/var/log/app.log",
            },
            "project": {"name": "my-project", "version": "1.0.0"},
            "features": ["auth"],
        }

    def test_lists_with_dicts_are_replaced_not_merged(self) -> None:
        base = {"servers": [{"name": "a", "port": 80}]}
        override = {"servers": [{"name": "b"}]}

        result = deep_merge(base, override)

        assert result == {"servers": [{"name": "b"}]}

    def test_returned_dict_is_independent(self) -> None:
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}

        result = deep_merge(base, override)
        result["a"]["b"] = 999

        assert base["a"]["b"] == 1

    def test_returned_list_is_independent(self) -> None:
        base = {"tags": ["a"]}
        override = {"tags": ["x", "y"]}

        result = deep_merge(base, override)
        result["tags"].append("z")

        assert override["tags"] == ["x", "y"]


class TestParseEnvValue:
    def test_parses_true_lowercase(self) -> None:
        assert _parse_env_value("true") is True

    def test_parses_true_uppercase(self) -> None:
        assert _parse_env_value("True") is True

    def test_parses_true_mixed_case(self) -> None:
        assert _parse_env_value("TRUE") is True

    def test_parses_false_lowercase(self) -> None:
        assert _parse_env_value("false") is False

    def test_parses_false_uppercase(self) -> None:
        assert _parse_env_value("False") is False

    def test_parses_false_mixed_case(self) -> None:
        assert _parse_env_value("FALSE") is False

    def test_parses_1_as_true(self) -> None:
        assert _parse_env_value("1") is True

    def test_parses_0_as_false(self) -> None:
        assert _parse_env_value("0") is False

    def test_parses_integer(self) -> None:
        assert _parse_env_value("42") == 42

    def test_parses_negative_integer(self) -> None:
        assert _parse_env_value("-17") == -17

    def test_parses_large_integer(self) -> None:
        assert _parse_env_value("9999999999") == 9999999999

    def test_parses_float(self) -> None:
        assert _parse_env_value("3.14") == 3.14

    def test_parses_negative_float(self) -> None:
        assert _parse_env_value("-2.5") == -2.5

    def test_parses_float_with_leading_zero(self) -> None:
        assert _parse_env_value("0.5") == 0.5

    def test_parses_json_array(self) -> None:
        assert _parse_env_value('["a", "b", "c"]') == ["a", "b", "c"]

    def test_parses_json_array_with_numbers(self) -> None:
        assert _parse_env_value("[1, 2, 3]") == [1, 2, 3]

    def test_parses_json_array_mixed_types(self) -> None:
        assert _parse_env_value('["a", 1, true]') == ["a", 1, True]

    def test_parses_empty_json_array(self) -> None:
        assert _parse_env_value("[]") == []

    def test_parses_json_object(self) -> None:
        assert _parse_env_value('{"key": "value"}') == {"key": "value"}

    def test_parses_json_object_with_numbers(self) -> None:
        assert _parse_env_value('{"port": 8080}') == {"port": 8080}

    def test_parses_nested_json_object(self) -> None:
        result = _parse_env_value('{"outer": {"inner": "value"}}')
        assert result == {"outer": {"inner": "value"}}

    def test_parses_empty_json_object(self) -> None:
        assert _parse_env_value("{}") == {}

    def test_returns_string_for_plain_text(self) -> None:
        assert _parse_env_value("hello") == "hello"

    def test_returns_string_for_empty_string(self) -> None:
        assert _parse_env_value("") == ""

    def test_returns_string_for_path(self) -> None:
        assert _parse_env_value("/var/log/app.log") == "/var/log/app.log"

    def test_returns_string_for_url(self) -> None:
        result = _parse_env_value("https://example.com")
        assert result == "https://example.com"

    def test_returns_string_for_invalid_json_array(self) -> None:
        assert _parse_env_value("[invalid json") == "[invalid json"

    def test_returns_string_for_invalid_json_object(self) -> None:
        assert _parse_env_value("{invalid json}") == "{invalid json}"

    def test_returns_string_for_partial_number(self) -> None:
        assert _parse_env_value("12abc") == "12abc"

    def test_integer_not_parsed_as_float(self) -> None:
        result = _parse_env_value("42")
        assert result == 42
        assert isinstance(result, int)
        assert not isinstance(result, float)

    def test_string_with_dots_not_parsed_as_float(self) -> None:
        result = _parse_env_value("v1.2.3")
        assert result == "v1.2.3"
        assert isinstance(result, str)


class TestSetNestedKey:
    def test_sets_simple_key(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "key", "value")
        assert d == {"key": "value"}

    def test_sets_nested_key(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "logging.level", "debug")
        assert d == {"logging": {"level": "debug"}}

    def test_sets_deeply_nested_key(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "a.b.c.d", "value")
        assert d == {"a": {"b": {"c": {"d": "value"}}}}

    def test_preserves_existing_siblings(self) -> None:
        d: dict[str, object] = {"logging": {"format": "json"}}
        set_nested_key(d, "logging.level", "debug")
        assert d == {"logging": {"format": "json", "level": "debug"}}

    def test_overwrites_existing_value(self) -> None:
        d: dict[str, object] = {"key": "old"}
        set_nested_key(d, "key", "new")
        assert d == {"key": "new"}

    def test_overwrites_nested_existing_value(self) -> None:
        d: dict[str, object] = {"logging": {"level": "info"}}
        set_nested_key(d, "logging.level", "debug")
        assert d == {"logging": {"level": "debug"}}

    def test_overwrites_scalar_with_nested_structure(self) -> None:
        d: dict[str, object] = {"a": "scalar"}
        set_nested_key(d, "a.b", "value")
        assert d == {"a": {"b": "value"}}

    def test_sets_integer_value(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "port", 8080)
        assert d == {"port": 8080}

    def test_sets_boolean_value(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "enabled", True)
        assert d == {"enabled": True}

    def test_sets_list_value(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "tags", ["a", "b"])
        assert d == {"tags": ["a", "b"]}

    def test_sets_dict_value(self) -> None:
        d: dict[str, object] = {}
        set_nested_key(d, "config", {"nested": "dict"})
        assert d == {"config": {"nested": "dict"}}

    def test_empty_key_path_sets_empty_key(self) -> None:
        d: dict[str, object] = {"existing": "value"}
        set_nested_key(d, "", "new")
        assert d == {"existing": "value", "": "new"}


class TestParseEnvVars:
    # Use TEST_ prefix to avoid picking up actual OAPS_ environment variables
    TEST_PREFIX: str = "OAPS_TEST_"

    def test_parses_single_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_LEVEL", "debug")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"level": "debug"}

    def test_parses_nested_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_LOGGING__LEVEL", "debug")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"logging": {"level": "debug"}}

    def test_parses_deeply_nested_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OAPS_TEST_A__B__C", "value")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"a": {"b": {"c": "value"}}}

    def test_parses_multiple_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_LOGGING__LEVEL", "debug")
        monkeypatch.setenv("OAPS_TEST_LOGGING__FORMAT", "json")
        monkeypatch.setenv("OAPS_TEST_PROJECT__NAME", "test")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {
            "logging": {"level": "debug", "format": "json"},
            "project": {"name": "test"},
        }

    def test_converts_to_lowercase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_LOGGING__LEVEL", "debug")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert "logging" in result
        assert "LOGGING" not in result

    def test_ignores_non_prefixed_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_KEY", "value")
        monkeypatch.setenv("OTHER_KEY", "other")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"key": "value"}

    def test_custom_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MYAPP_KEY", "value")
        monkeypatch.setenv("OAPS_OTHER", "other")

        result = parse_env_vars(prefix="MYAPP_")

        assert result == {"key": "value"}

    def test_parses_integer_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_PORT", "8080")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"port": 8080}
        assert isinstance(result["port"], int)

    def test_parses_boolean_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_ENABLED", "true")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"enabled": True}
        assert result["enabled"] is True

    def test_parses_float_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_TIMEOUT", "1.5")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"timeout": 1.5}
        assert isinstance(result["timeout"], float)

    def test_parses_json_array_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_TAGS", '["a", "b", "c"]')

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"tags": ["a", "b", "c"]}

    def test_parses_json_object_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_OPTIONS", '{"key": "value"}')

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"options": {"key": "value"}}

    def test_returns_empty_dict_when_no_matching_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use a prefix that won't match any real environment variables
        result = parse_env_vars(prefix="NONEXISTENT_PREFIX_XYZ_")

        assert result == {}

    def test_ignores_prefix_only_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # This tests that OAPS_TEST_ by itself (with no key after) is ignored
        monkeypatch.setenv("OAPS_TEST_", "value")
        monkeypatch.setenv("OAPS_TEST_KEY", "real")

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {"key": "real"}

    def test_realistic_config_scenario(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_TEST_LOGGING__LEVEL", "debug")
        monkeypatch.setenv("OAPS_TEST_LOGGING__FORMAT", "json")
        monkeypatch.setenv("OAPS_TEST_PROJECT__NAME", "my-project")
        monkeypatch.setenv("OAPS_TEST_SERVER__PORT", "3000")
        monkeypatch.setenv("OAPS_TEST_SERVER__HOST", "localhost")
        monkeypatch.setenv("OAPS_TEST_FEATURES__AUTH__ENABLED", "true")
        monkeypatch.setenv(
            "OAPS_TEST_FEATURES__AUTH__PROVIDERS", '["google", "github"]'
        )

        result = parse_env_vars(prefix=self.TEST_PREFIX)

        assert result == {
            "logging": {"level": "debug", "format": "json"},
            "project": {"name": "my-project"},
            "server": {"port": 3000, "host": "localhost"},
            "features": {"auth": {"enabled": True, "providers": ["google", "github"]}},
        }

    def test_default_prefix_is_oaps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Verify the default prefix by testing with a unique key
        monkeypatch.setenv("OAPS_UNIQUE_TEST_KEY_12345", "test_value")

        result = parse_env_vars()

        assert result.get("unique_test_key_12345") == "test_value"
