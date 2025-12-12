from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.context import (
    extract_string_dict,
    extract_string_list,
    get_skill_dir,
    get_skill_override_dir,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest_mock import MockerFixture


class TestExtractStringList:
    def test_returns_list_of_strings(self) -> None:
        frontmatter = {"items": ["a", "b", "c"]}
        result = extract_string_list(frontmatter, "items")
        assert result == ["a", "b", "c"]

    def test_converts_non_strings_to_strings(self) -> None:
        frontmatter = {"items": [1, 2, 3]}
        result = extract_string_list(frontmatter, "items")
        assert result == ["1", "2", "3"]

    def test_returns_empty_list_when_key_missing(self) -> None:
        frontmatter: dict[str, object] = {}
        result = extract_string_list(frontmatter, "items")
        assert result == []

    def test_returns_empty_list_when_not_list(self) -> None:
        frontmatter = {"items": "not a list"}
        result = extract_string_list(frontmatter, "items")
        assert result == []


class TestExtractStringDict:
    def test_returns_dict_of_strings(self) -> None:
        frontmatter = {"commands": {"cmd1": "desc1", "cmd2": "desc2"}}
        result = extract_string_dict(frontmatter, "commands")
        assert result == {"cmd1": "desc1", "cmd2": "desc2"}

    def test_converts_values_to_strings(self) -> None:
        frontmatter = {"data": {"key": 123}}
        result = extract_string_dict(frontmatter, "data")
        assert result == {"key": "123"}

    def test_returns_empty_dict_when_key_missing(self) -> None:
        frontmatter: dict[str, object] = {}
        result = extract_string_dict(frontmatter, "commands")
        assert result == {}

    def test_returns_empty_dict_when_not_dict(self) -> None:
        frontmatter = {"commands": ["not", "a", "dict"]}
        result = extract_string_dict(frontmatter, "commands")
        assert result == {}


class TestGetSkillDir:
    def test_raises_when_both_plugin_and_project(self) -> None:
        with pytest.raises(ValueError, match="Cannot specify both plugin and project"):
            get_skill_dir("test-skill", plugin=True, project=True)

    def test_defaults_to_project_when_neither_specified(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_dir = Path("/test/.oaps")
        skill_dir = oaps_dir / "claude" / "skills" / "test-skill"
        fs.create_dir(skill_dir)
        mocker.patch("oaps.utils._paths.get_oaps_dir", return_value=oaps_dir)
        result = get_skill_dir("test-skill", plugin=False, project=False)
        assert result == skill_dir

    def test_project_returns_path_when_exists(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_dir = Path("/test/.oaps")
        skill_dir = oaps_dir / "claude" / "skills" / "test-skill"
        fs.create_dir(skill_dir)
        mocker.patch("oaps.utils._paths.get_oaps_dir", return_value=oaps_dir)
        result = get_skill_dir("test-skill", project=True)
        assert result == skill_dir

    def test_project_returns_none_when_not_exists(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_dir = Path("/test/.oaps")
        fs.create_dir(oaps_dir)
        mocker.patch("oaps.utils._paths.get_oaps_dir", return_value=oaps_dir)
        result = get_skill_dir("nonexistent-skill", project=True)
        assert result is None

    def test_plugin_calls_get_claude_plugin_skill_dir(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        plugin_skill_dir = Path("/plugin/skills/test-skill")
        fs.create_dir(plugin_skill_dir)

        def mock_get_claude_plugin_skill_dir(skill_name: str) -> Path | None:
            if skill_name == "test-skill":
                return plugin_skill_dir
            return None

        mocker.patch(
            "oaps.utils._claude_plugin.get_claude_plugin_skill_dir",
            side_effect=mock_get_claude_plugin_skill_dir,
        )
        result = get_skill_dir("test-skill", plugin=True, project=False)
        assert result == plugin_skill_dir


class TestGetSkillOverrideDir:
    def test_returns_override_dir_from_get_oaps_skill_overrides_dir(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        override_dir = Path("/test/.oaps/overrides/skills/test-skill")
        fs.create_dir(override_dir)

        def mock_get_oaps_skill_overrides_dir(skill_name: str) -> Path | None:
            if skill_name == "test-skill":
                return override_dir
            return None

        mocker.patch(
            "oaps.utils._paths.get_oaps_skill_overrides_dir",
            side_effect=mock_get_oaps_skill_overrides_dir,
        )
        result = get_skill_override_dir("test-skill")
        assert result == override_dir
