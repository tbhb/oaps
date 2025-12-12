"""Integration tests for the hooks command group."""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from oaps.cli._commands._context import CLIContext
from oaps.cli._commands._hooks._exit_codes import (
    EXIT_NOT_FOUND,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
)


@pytest.fixture
def hooks_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Path]:
    """Set up isolated environment for hooks commands.

    Creates:
        tmp_path/
            project/
                .oaps/
                    oaps.toml       # Project config with hooks
                    hooks.d/        # Drop-in directory
    """
    # Create project structure
    project_root = tmp_path / "project"
    project_root.mkdir()

    oaps_dir = project_root / ".oaps"
    oaps_dir.mkdir()

    # Create hooks drop-in directory
    hooks_d = oaps_dir / "hooks.d"
    hooks_d.mkdir()

    # Create a test rule in drop-in
    test_rule = hooks_d / "test-rules.toml"
    test_rule.write_text("""[[rules]]
id = "test-bash-warn"
events = ["pre_tool_use"]
condition = "tool_name == 'Bash'"
result = "warn"
priority = "medium"
description = "Warn on Bash usage"
enabled = true
terminal = false

[[rules.actions]]
type = "warn"
message = "Be careful with Bash commands!"

[[rules]]
id = "test-disabled-rule"
events = ["all"]
condition = "true"
result = "ok"
priority = "low"
description = "A disabled rule"
enabled = false
""")

    # Patch path discovery functions in all locations where they're imported
    def mock_find_project_root(start: Path | None = None) -> Path:  # noqa: ARG001
        return project_root

    # Patch in the discovery module (source)
    monkeypatch.setattr(
        "oaps.config._discovery.find_project_root",
        mock_find_project_root,
    )
    # Patch in oaps.config (where commands import from)
    monkeypatch.setattr(
        "oaps.config.find_project_root",
        mock_find_project_root,
    )
    # Patch in the hooks loader
    monkeypatch.setattr(
        "oaps.config._hooks_loader.find_project_root",
        mock_find_project_root,
    )
    # Patch in command modules (where they've already imported)
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._validate.find_project_root",
        mock_find_project_root,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._list.find_project_root",
        mock_find_project_root,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._test.find_project_root",
        mock_find_project_root,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._debug.find_project_root",
        mock_find_project_root,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._status.find_project_root",
        mock_find_project_root,
    )

    # Patch user config path
    user_config_dir = tmp_path / "user_config" / "oaps"
    user_config_dir.mkdir(parents=True)

    def mock_get_user_config_path() -> Path:
        return user_config_dir / "config.toml"

    monkeypatch.setattr(
        "oaps.config._discovery.get_user_config_path",
        mock_get_user_config_path,
    )
    monkeypatch.setattr(
        "oaps.config.get_user_config_path",
        mock_get_user_config_path,
    )
    monkeypatch.setattr(
        "oaps.config._hooks_loader.get_user_config_path",
        mock_get_user_config_path,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._hooks._status.get_user_config_path",
        mock_get_user_config_path,
    )

    # Patch builtin hooks dir to empty dir (isolate from package builtin hooks)
    builtin_hooks_dir = tmp_path / "empty_builtin_hooks"
    builtin_hooks_dir.mkdir()

    def mock_get_builtin_hooks_dir() -> Path:
        return builtin_hooks_dir

    monkeypatch.setattr(
        "oaps.config._hooks_loader._get_builtin_hooks_dir",
        mock_get_builtin_hooks_dir,
    )

    yield project_root

    CLIContext.reset()


class TestHooksValidate:
    def test_validate_success(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "validate")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Validation OK" in captured.out

    def test_validate_json_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "validate", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"valid": true' in captured.out

    def test_validate_invalid_expression(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create an invalid rule
        hooks_d = hooks_env / ".oaps" / "hooks.d"
        invalid_rule = hooks_d / "invalid.toml"
        invalid_rule.write_text("""[[rules]]
id = "invalid-expression"
events = ["pre_tool_use"]
condition = "this is not valid >>>"
result = "ok"
""")

        exit_code = oaps_cli_with_exit_code("hooks", "validate")

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "FAILED" in captured.out or "error" in captured.out.lower()


class TestHooksList:
    def test_list_table_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "list")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Table headers
        assert "ID" in captured.out
        assert "Priority" in captured.out
        # Rule content
        assert "test-bash-warn" in captured.out

    def test_list_json_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "list", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"rules"' in captured.out
        assert '"test-bash-warn"' in captured.out

    def test_list_filter_by_event(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "list", "--event", "pre_tool_use")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "test-bash-warn" in captured.out

    def test_list_enabled_only(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "list", "--enabled-only")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "test-bash-warn" in captured.out
        # Disabled rule should not appear
        assert "test-disabled-rule" not in captured.out

    def test_list_no_rules(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Remove all rules
        hooks_d = hooks_env / ".oaps" / "hooks.d"
        for f in hooks_d.glob("*.toml"):
            f.unlink()

        exit_code = oaps_cli_with_exit_code("hooks", "list")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "No hook rules configured" in captured.out


class TestHooksTest:
    def test_test_default_event(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "test")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Test Context" in captured.out
        assert "pre_tool_use" in captured.out

    def test_test_specific_event(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "hooks", "test", "--event", "user_prompt_submit"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "user_prompt_submit" in captured.out

    def test_test_specific_rule(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "test", "--rule", "test-bash-warn")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "test-bash-warn" in captured.out

    def test_test_rule_not_found(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "test", "--rule", "nonexistent")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_test_json_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "test", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"event"' in captured.out
        assert '"matched_rules"' in captured.out


class TestHooksDebug:
    def test_debug_rule(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "debug", "test-bash-warn")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "RULE DETAILS" in captured.out
        assert "test-bash-warn" in captured.out
        assert "EXPRESSION VALIDATION" in captured.out

    def test_debug_rule_not_found(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "debug", "nonexistent-rule")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_debug_with_event(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "hooks", "debug", "test-bash-warn", "--event", "pre_tool_use"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "EVENT MATCHING" in captured.out
        assert "CONDITION EVALUATION" in captured.out


class TestHooksStatus:
    def test_status_text_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "status")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "HOOK SYSTEM STATUS" in captured.out
        assert "Rules:" in captured.out
        assert "Total:" in captured.out

    def test_status_json_format(
        self,
        hooks_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("hooks", "status", "--format", "json")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert '"rules"' in captured.out
        assert '"total"' in captured.out
        assert '"by_priority"' in captured.out
