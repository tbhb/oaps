# pyright: reportAny=false, reportUnknownArgumentType=false
"""Tests for hook rule loading and merging."""

from pathlib import Path
from typing import TYPE_CHECKING, Literal
from unittest.mock import MagicMock

import pytest

from oaps.config import HookRuleConfiguration
from oaps.config._hooks_loader import (
    _get_dropin_dir,
    discover_drop_in_files,
    load_all_hook_rules,
    load_drop_in_rules,
    merge_hook_rules,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem

EventType = Literal[
    "all",
    "pre_tool_use",
    "post_tool_use",
    "permission_request",
    "user_prompt_submit",
    "notification",
    "session_start",
    "session_end",
    "stop",
    "subagent_stop",
    "pre_compact",
]

ResultType = Literal["block", "ok", "warn"]


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


def make_rule(
    rule_id: str,
    *,
    condition: str = "true",
    events: set[EventType] | None = None,
    result: ResultType = "ok",
    enabled: bool = True,
    source_file: Path | None = None,
) -> HookRuleConfiguration:
    """Create a test rule configuration."""
    return HookRuleConfiguration(
        id=rule_id,
        condition=condition,
        events=events or {"pre_tool_use"},
        result=result,
        enabled=enabled,
        source_file=source_file,
    )


class TestDiscoverDropInFiles:
    def test_finds_toml_files_in_directory(self, fs: FakeFilesystem) -> None:
        directory = Path("/project/.oaps/hooks.d")
        fs.create_file(directory / "00-base.toml", contents="")
        fs.create_file(directory / "50-project.toml", contents="")
        fs.create_file(directory / "99-local.toml", contents="")

        result = discover_drop_in_files(directory)

        assert len(result) == 3
        assert result[0].name == "00-base.toml"
        assert result[1].name == "50-project.toml"
        assert result[2].name == "99-local.toml"

    def test_sorts_lexicographically(self, fs: FakeFilesystem) -> None:
        directory = Path("/project/.oaps/hooks.d")
        # Create in non-sorted order
        fs.create_file(directory / "zzz.toml", contents="")
        fs.create_file(directory / "aaa.toml", contents="")
        fs.create_file(directory / "mmm.toml", contents="")

        result = discover_drop_in_files(directory)

        assert [p.name for p in result] == ["aaa.toml", "mmm.toml", "zzz.toml"]

    def test_returns_empty_list_if_directory_missing(self, fs: FakeFilesystem) -> None:
        result = discover_drop_in_files(Path("/nonexistent"))

        assert result == []

    def test_returns_empty_list_if_no_toml_files(self, fs: FakeFilesystem) -> None:
        directory = Path("/project/.oaps/hooks.d")
        fs.create_dir(directory)
        fs.create_file(directory / "readme.md", contents="")

        result = discover_drop_in_files(directory)

        assert result == []

    def test_ignores_non_toml_files(self, fs: FakeFilesystem) -> None:
        directory = Path("/project/.oaps/hooks.d")
        fs.create_file(directory / "rules.toml", contents="")
        fs.create_file(directory / "readme.txt", contents="")
        fs.create_file(directory / "config.json", contents="")

        result = discover_drop_in_files(directory)

        assert len(result) == 1
        assert result[0].name == "rules.toml"


class TestLoadDropInRules:
    def test_loads_rules_from_toml_files(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        content = """
[[rules]]
id = "test-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
"""
        fs.create_file(directory / "00-test.toml", contents=content)

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 1
        assert result[0].id == "test-rule"
        assert result[0].source_file == directory / "00-test.toml"

    def test_loads_multiple_rules_from_file(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        content = """
[[rules]]
id = "rule-1"
condition = "true"
events = ["pre_tool_use"]
result = "ok"

[[rules]]
id = "rule-2"
condition = "false"
events = ["post_tool_use"]
result = "block"
"""
        fs.create_file(directory / "00-test.toml", contents=content)

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 2
        assert result[0].id == "rule-1"
        assert result[1].id == "rule-2"

    def test_loads_rules_from_multiple_files_in_order(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        fs.create_file(
            directory / "00-first.toml",
            contents="""
[[rules]]
id = "first-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        fs.create_file(
            directory / "50-second.toml",
            contents="""
[[rules]]
id = "second-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 2
        assert result[0].id == "first-rule"
        assert result[1].id == "second-rule"

    def test_skips_invalid_toml_files(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        fs.create_file(directory / "00-invalid.toml", contents="[invalid syntax")
        fs.create_file(
            directory / "50-valid.toml",
            contents="""
[[rules]]
id = "valid-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 1
        assert result[0].id == "valid-rule"
        mock_logger.warning.assert_called()

    def test_warns_on_non_rules_sections(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        content = """
[settings]
debug = true

[[rules]]
id = "test-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
"""
        fs.create_file(directory / "00-test.toml", contents=content)

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 1
        mock_logger.warning.assert_called()

    def test_returns_empty_list_for_missing_directory(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        result = load_drop_in_rules(Path("/nonexistent"), mock_logger)

        assert result == []

    def test_skips_invalid_rules(
        self, fs: FakeFilesystem, mock_logger: MagicMock
    ) -> None:
        directory = Path("/project/.oaps/hooks.d")
        # Missing required 'events' field
        content = """
[[rules]]
id = "invalid-rule"
condition = "true"
result = "ok"

[[rules]]
id = "valid-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
"""
        fs.create_file(directory / "00-test.toml", contents=content)

        result = load_drop_in_rules(directory, mock_logger)

        assert len(result) == 1
        assert result[0].id == "valid-rule"
        mock_logger.warning.assert_called()


class TestMergeHookRules:
    def test_merges_empty_lists(self) -> None:
        result = merge_hook_rules([], [])

        assert result == []

    def test_returns_single_list_unchanged(self) -> None:
        rules = [make_rule("rule-1"), make_rule("rule-2")]

        result = merge_hook_rules(rules)

        assert len(result) == 2
        assert result[0].id == "rule-1"
        assert result[1].id == "rule-2"

    def test_combines_rules_from_multiple_lists(self) -> None:
        list1 = [make_rule("rule-a")]
        list2 = [make_rule("rule-b")]

        result = merge_hook_rules(list1, list2)

        assert len(result) == 2
        ids = {r.id for r in result}
        assert ids == {"rule-a", "rule-b"}

    def test_later_rules_override_earlier_by_id(self) -> None:
        # Lower precedence
        list1 = [make_rule("shared-id", condition="first")]
        # Higher precedence
        list2 = [make_rule("shared-id", condition="second")]

        result = merge_hook_rules(list1, list2)

        assert len(result) == 1
        assert result[0].id == "shared-id"
        assert result[0].condition == "second"

    def test_preserves_first_seen_order(self) -> None:
        list1 = [make_rule("rule-a"), make_rule("rule-b")]
        list2 = [make_rule("rule-c"), make_rule("rule-b", condition="override")]

        result = merge_hook_rules(list1, list2)

        assert len(result) == 3
        # rule-a, rule-b (first seen), rule-c
        assert result[0].id == "rule-a"
        assert result[1].id == "rule-b"
        assert result[1].condition == "override"  # But with updated content
        assert result[2].id == "rule-c"

    def test_handles_many_lists(self) -> None:
        lists = [[make_rule(f"rule-{i}")] for i in range(10)]

        result = merge_hook_rules(*lists)

        assert len(result) == 10


class TestGetDropinDir:
    def test_returns_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)
        project_root = Path("/project")

        result = _get_dropin_dir(project_root)

        assert result == Path("/project/.oaps/hooks.d")

    def test_respects_absolute_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OAPS_HOOKS__DROPIN_DIR", "/custom/hooks")
        project_root = Path("/project")

        result = _get_dropin_dir(project_root)

        assert result == Path("/custom/hooks")

    def test_respects_relative_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OAPS_HOOKS__DROPIN_DIR", "custom/hooks")
        project_root = Path("/project")

        result = _get_dropin_dir(project_root)

        assert result == Path("/project/custom/hooks")

    def test_ignores_empty_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OAPS_HOOKS__DROPIN_DIR", "")
        project_root = Path("/project")

        result = _get_dropin_dir(project_root)

        assert result == Path("/project/.oaps/hooks.d")

    def test_strips_whitespace_from_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OAPS_HOOKS__DROPIN_DIR", "  /custom/hooks  ")
        project_root = Path("/project")

        result = _get_dropin_dir(project_root)

        assert result == Path("/custom/hooks")


class TestLoadAllHookRules:
    def test_loads_from_project_dropin(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        project_root = Path("/project")
        # Create .oaps dir so find_project_root works
        fs.create_dir(project_root / ".oaps")
        dropin_dir = project_root / ".oaps" / "hooks.d"
        fs.create_file(
            dropin_dir / "00-test.toml",
            contents="""
[[rules]]
id = "test-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(project_root, mock_logger)

        assert len(result) == 1
        assert result[0].id == "test-rule"

    def test_loads_from_project_hooks_toml(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        project_root = Path("/project")
        fs.create_dir(project_root / ".oaps")
        fs.create_file(
            project_root / ".oaps" / "hooks.toml",
            contents="""
[[hooks.rules]]
id = "external-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(project_root, mock_logger)

        assert len(result) == 1
        assert result[0].id == "external-rule"

    def test_loads_from_project_inline(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        project_root = Path("/project")
        fs.create_dir(project_root / ".oaps")
        fs.create_file(
            project_root / ".oaps" / "oaps.toml",
            contents="""
[[hooks.rules]]
id = "inline-rule"
condition = "true"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(project_root, mock_logger)

        assert len(result) == 1
        assert result[0].id == "inline-rule"

    def test_merges_with_precedence(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        project_root = Path("/project")
        fs.create_dir(project_root / ".oaps")

        # External hooks file (lower precedence)
        fs.create_file(
            project_root / ".oaps" / "hooks.toml",
            contents="""
[[hooks.rules]]
id = "shared-rule"
condition = "external"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        # Inline rules (higher precedence)
        fs.create_file(
            project_root / ".oaps" / "oaps.toml",
            contents="""
[[hooks.rules]]
id = "shared-rule"
condition = "inline"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(project_root, mock_logger)

        assert len(result) == 1
        assert result[0].id == "shared-rule"
        assert result[0].condition == "inline"  # Higher precedence wins

    def test_dropin_overrides_external(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        project_root = Path("/project")
        fs.create_dir(project_root / ".oaps")

        # External hooks file (lower precedence)
        fs.create_file(
            project_root / ".oaps" / "hooks.toml",
            contents="""
[[hooks.rules]]
id = "shared-rule"
condition = "external"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        # Drop-in (higher precedence than external)
        dropin_dir = project_root / ".oaps" / "hooks.d"
        fs.create_file(
            dropin_dir / "00-test.toml",
            contents="""
[[rules]]
id = "shared-rule"
condition = "dropin"
events = ["pre_tool_use"]
result = "ok"
""",
        )
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(project_root, mock_logger)

        assert len(result) == 1
        assert result[0].condition == "dropin"  # Drop-in wins over external

    def test_returns_empty_list_without_project_root(
        self,
        fs: FakeFilesystem,
        monkeypatch: pytest.MonkeyPatch,
        mock_logger: MagicMock,
    ) -> None:
        # No .oaps directory anywhere
        fs.create_dir("/some/path")
        monkeypatch.chdir("/some/path")
        monkeypatch.delenv("OAPS_HOOKS__DROPIN_DIR", raising=False)

        result = load_all_hook_rules(None, mock_logger)

        assert result == []
