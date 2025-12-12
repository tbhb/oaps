"""Integration tests for the config command."""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from oaps.cli._commands._config._exit_codes import (
    EXIT_KEY_ERROR,
    EXIT_LOAD_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATE_ERRORS,
    EXIT_VALIDATION_ERROR,
)
from oaps.cli._commands._context import CLIContext


@pytest.fixture
def user_config_dir(tmp_path: Path) -> Path:
    """Create user config directory for testing."""
    user_dir = tmp_path / "user_config" / "oaps"
    user_dir.mkdir(parents=True)
    return user_dir


@pytest.fixture
def config_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    user_config_dir: Path,
) -> Generator[Path]:
    """Set up isolated environment for config commands.

    Creates:
        tmp_path/
            project/
                .oaps/
                    oaps.toml       # Project config
                    oaps.local.toml # Local config (created by some tests)
    """
    # Create project structure
    project_root = tmp_path / "project"
    project_root.mkdir()

    oaps_dir = project_root / ".oaps"
    oaps_dir.mkdir()

    # Create default project config
    project_config = oaps_dir / "oaps.toml"
    project_config.write_text("""[project]
name = "test-project"

[logging]
level = "debug"
""")

    # Patch path discovery functions
    def mock_find_project_root(start: Path | None = None) -> Path:  # noqa: ARG001
        return project_root

    monkeypatch.setattr(
        "oaps.config._discovery.find_project_root",
        mock_find_project_root,
    )

    def mock_get_user_config_path() -> Path:
        return user_config_dir / "config.toml"

    monkeypatch.setattr(
        "oaps.config._discovery.get_user_config_path",
        mock_get_user_config_path,
    )

    # Reset CLIContext after each test to avoid state leakage
    yield project_root

    CLIContext.reset()


class TestConfigShow:
    def test_show_default_format_is_toml(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # TOML format should have section headers with brackets
        assert "[project]" in captured.out
        assert "[logging]" in captured.out
        assert 'name = "test-project"' in captured.out

    def test_show_json_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # JSON format should have curly braces and colons
        assert '"project"' in captured.out
        assert '"name"' in captured.out
        assert '"test-project"' in captured.out

    def test_show_section_filters_output(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show", "--section", "logging")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "[logging]" in captured.out
        assert 'level = "debug"' in captured.out
        # Should not include other sections
        assert "[project]" not in captured.out

    def test_show_section_not_found(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "show", "--section", "nonexistent"
        )

        assert exit_code == EXIT_LOAD_ERROR
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_show_sources_adds_annotations(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show", "--show-sources")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Source annotations should be in comments
        assert "# source:" in captured.out

    def test_show_sources_not_supported_with_json(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "show", "--format", "json", "--show-sources"
        )

        assert exit_code == EXIT_LOAD_ERROR
        captured = capsys.readouterr()
        assert "not supported with JSON" in captured.out

    def test_show_source_filters_to_single_source(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "show", "--source", "project")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "test-project" in captured.out


class TestConfigGet:
    def test_get_existing_key(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "get", "project.name")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "test-project" in captured.out

    def test_get_missing_key_exits_with_error(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "get", "nonexistent.key")

        assert exit_code == EXIT_KEY_ERROR
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_get_with_default_returns_default(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "get", "nonexistent.key", "--default", "fallback"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "fallback" in captured.out

    def test_get_nested_key(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "get", "logging.level")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "debug" in captured.out

    def test_get_json_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "get", "project.name", "--format", "json"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # JSON format for string should be quoted
        assert '"test-project"' in captured.out


class TestConfigSet:
    def test_set_creates_local_config_by_default(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "set", "project.version", "1.0.0")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Set project.version" in captured.out

        # Verify local config was created
        local_config = config_env / ".oaps" / "oaps.local.toml"
        assert local_config.exists()
        content = local_config.read_text()
        assert "version" in content

    def test_set_project_file(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "set", "project.version", "2.0.0", "--file", "project"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Set project.version" in captured.out
        assert "oaps.toml" in captured.out

        # Verify project config was modified
        project_config = config_env / ".oaps" / "oaps.toml"
        content = project_config.read_text()
        assert "version" in content

    def test_set_type_bool(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "set", "logging.structured", "true", "--type", "bool"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Set logging.structured" in captured.out
        assert "True" in captured.out

    def test_set_type_int(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "set", "project.timeout", "30", "--type", "int"
        )

        assert exit_code == EXIT_SUCCESS

    def test_set_auto_infers_bool(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "set", "logging.structured", "false"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Auto-inference should detect boolean
        assert "False" in captured.out

    def test_set_auto_infers_int(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "set", "project.port", "8080")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Auto-inference should detect integer (no quotes around value)
        assert "8080" in captured.out

    def test_set_validation_error_for_invalid_value(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "set", "logging.level", "12345", "--type", "int"
        )

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Invalid" in captured.out or "error" in captured.out.lower()


class TestConfigListSources:
    def test_list_sources_default_table_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "list-sources")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Table format should have headers
        assert "Source" in captured.out
        assert "Path" in captured.out
        assert "Exists" in captured.out
        # Should show project source
        assert "project" in captured.out

    def test_list_sources_all_includes_nonexistent(
        self,
        config_env: Path,
        user_config_dir: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "list-sources", "--all")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Should include user source even if it doesn't exist
        assert "user" in captured.out
        # Table should show non-existent sources
        assert "no" in captured.out

    def test_list_sources_json_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "list-sources", "--format", "json"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"sources"' in captured.out
        assert '"name"' in captured.out
        assert '"path"' in captured.out

    def test_list_sources_plain_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "config", "list-sources", "--format", "plain"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Plain format shows "source: path"
        assert "project:" in captured.out


class TestConfigValidate:
    def test_validate_valid_config(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "validate")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Validating config files" in captured.out
        assert "OK" in captured.out

    def test_validate_invalid_config(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create invalid config with wrong type
        project_config = config_env / ".oaps" / "oaps.toml"
        project_config.write_text("""[logging]
level = 12345
""")

        exit_code = oaps_cli_with_exit_code("config", "validate")

        assert exit_code == EXIT_VALIDATE_ERRORS
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_validate_strict_rejects_unknown_keys(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create config with unknown key (warning in normal mode, error in strict)
        project_config = config_env / ".oaps" / "oaps.toml"
        project_config.write_text("""[project]
name = "test"
unknown_key = "value"
""")

        exit_code = oaps_cli_with_exit_code("config", "validate", "--strict")

        # In strict mode, unknown keys are validation errors (exit code 1)
        assert exit_code == EXIT_VALIDATE_ERRORS
        captured = capsys.readouterr()
        # Should show unknown key error
        assert "unknown" in captured.out.lower() or "extra" in captured.out.lower()

    def test_validate_non_strict_shows_warnings_for_unknown_keys(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create config with unknown key (warning in normal mode)
        project_config = config_env / ".oaps" / "oaps.toml"
        project_config.write_text("""[project]
name = "test"
unknown_key = "value"
""")

        exit_code = oaps_cli_with_exit_code("config", "validate")

        # In non-strict mode, unknown keys are warnings (exit code 0)
        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Should show warning about unknown key
        assert "WARNING" in captured.out or "warning" in captured.out

    def test_validate_json_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "validate", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"files"' in captured.out
        assert '"summary"' in captured.out

    def test_validate_specific_file(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "validate", "--file", "project")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "project" in captured.out


class TestConfigSchema:
    def test_schema_stdout(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "schema")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # JSON schema should contain common schema keywords
        assert '"$schema"' in captured.out or '"type"' in captured.out
        assert '"properties"' in captured.out

    def test_schema_to_file(
        self,
        config_env: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        output_path = tmp_path / "schema.json"

        exit_code = oaps_cli_with_exit_code(
            "config", "schema", "--output", str(output_path)
        )

        assert exit_code == EXIT_SUCCESS
        assert output_path.exists()
        content = output_path.read_text()
        assert '"properties"' in content

        # Should print confirmation message
        captured = capsys.readouterr()
        assert "Schema written to" in captured.out

    def test_schema_yaml_format(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("config", "schema", "--format", "yaml")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # YAML format uses colons without quotes for keys
        assert "properties:" in captured.out


class TestConfigEdit:
    def test_edit_creates_file_with_create_flag(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Mock editor to avoid actually launching an editor
        def mock_find_editor() -> tuple[list[str], str | None]:
            return ["true"], None  # 'true' command does nothing and exits 0

        monkeypatch.setattr(
            "oaps.cli._commands._config._write._find_editor",
            mock_find_editor,
        )

        # Remove local config if it exists
        local_config = config_env / ".oaps" / "oaps.local.toml"
        local_config.unlink(missing_ok=True)

        exit_code = oaps_cli_with_exit_code("config", "edit", "--create")

        assert exit_code == EXIT_SUCCESS
        assert local_config.exists()
        captured = capsys.readouterr()
        assert "Created" in captured.out

    def test_edit_without_create_fails_for_nonexistent(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Remove local config if it exists
        local_config = config_env / ".oaps" / "oaps.local.toml"
        local_config.unlink(missing_ok=True)

        exit_code = oaps_cli_with_exit_code("config", "edit")

        assert exit_code == EXIT_LOAD_ERROR
        captured = capsys.readouterr()
        assert "not found" in captured.out
        assert "--create" in captured.out

    def test_edit_existing_file(
        self,
        config_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Mock editor
        def mock_find_editor() -> tuple[list[str], str | None]:
            return ["true"], None

        monkeypatch.setattr(
            "oaps.cli._commands._config._write._find_editor",
            mock_find_editor,
        )

        # Edit the existing project config
        exit_code = oaps_cli_with_exit_code("config", "edit", "--file", "project")

        assert exit_code == EXIT_SUCCESS
