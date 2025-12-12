import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.utils._claude_plugin import get_claude_plugin_dir
from oaps.utils._paths import (
    get_claude_config_dir,
    get_oaps_dir,
    get_oaps_overrides_dir,
    get_oaps_skill_overrides_dir,
    get_plans_dir,
    get_project_skill_dir,
    get_project_skills_dir,
    get_templates_dir,
    get_worktree_root,
    is_oaps_shared,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest_mock import MockerFixture


class TestGetClaudeConfigDir:
    def test_returns_path_to_claude_directory(self) -> None:
        path = get_claude_config_dir()
        assert path == Path.home() / ".claude"


class TestGetClaudePluginDir:
    def test_returns_none_when_known_marketplaces_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None

    def test_returns_none_when_oaps_entry_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"other-plugin": {"installLocation": "/some/path"}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None

    def test_returns_none_when_install_location_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"source": {"source": "directory"}}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None

    def test_returns_none_when_install_location_not_directory(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        nonexistent_path = Path("/fake/nonexistent")
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(nonexistent_path)}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None

    def test_returns_path_when_oaps_plugin_installed(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        oaps_dir = Path("/fake/oaps-plugin")
        fs.create_dir(oaps_dir)
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(oaps_dir)}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() == oaps_dir

    def test_returns_none_when_json_invalid(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json", contents="not valid json"
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None


class TestGetWorktreeRoot:
    def test_returns_git_worktree_root(self, mocker: MockerFixture) -> None:
        # Mock dulwich Repo.discover() which returns a Repo with .path attribute
        mock_repo = mocker.MagicMock()
        mock_repo.path = b"/fake/repo/.git"
        mocker.patch("dulwich.repo.Repo.discover", return_value=mock_repo)

        result = get_worktree_root()

        # The function returns repo.path decoded (which includes .git)
        assert result == Path("/fake/repo/.git")


class TestGetOapsDir:
    def test_returns_oaps_directory_in_worktree(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_worktree_root", lambda: Path("/fake/repo")
        )

        result = get_oaps_dir()

        assert result == Path("/fake/repo/.oaps")


class TestGetOapsOverridesDir:
    def test_returns_overrides_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_dir", lambda: Path("/fake/repo/.oaps")
        )

        result = get_oaps_overrides_dir()

        assert result == Path("/fake/repo/.oaps/overrides")


class TestGetOapsSkillOverridesDir:
    def test_returns_path_when_directory_exists(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = Path("/fake/repo/.oaps/overrides/skills/test-skill")
        fs.create_dir(skill_dir)
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_overrides_dir",
            lambda: Path("/fake/repo/.oaps/overrides"),
        )

        result = get_oaps_skill_overrides_dir("test-skill")

        assert result == skill_dir

    def test_returns_none_when_directory_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_overrides_dir",
            lambda: Path("/fake/repo/.oaps/overrides"),
        )

        result = get_oaps_skill_overrides_dir("nonexistent-skill")

        assert result is None


class TestIsOapsShared:
    def test_returns_true_when_oaps_is_symlink(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target_dir = Path("/fake/shared/.oaps")
        link_path = Path("/fake/repo/.oaps")
        fs.create_dir(target_dir)
        fs.create_symlink(link_path, target_dir)
        monkeypatch.setattr("oaps.utils._paths.get_oaps_dir", lambda: link_path)

        result = is_oaps_shared()

        assert result is True

    def test_returns_false_when_oaps_is_regular_directory(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        oaps_dir = Path("/fake/repo/.oaps")
        fs.create_dir(oaps_dir)
        monkeypatch.setattr("oaps.utils._paths.get_oaps_dir", lambda: oaps_dir)

        result = is_oaps_shared()

        assert result is False


class TestGetTemplatesDir:
    def test_returns_templates_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_package_dir", lambda: Path("/fake/package/oaps")
        )

        result = get_templates_dir()

        assert result == Path("/fake/package/oaps/templates")


class TestGetProjectSkillDir:
    def test_returns_path_when_skill_exists(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = Path("/fake/repo/.oaps/claude/skills/my-skill")
        fs.create_dir(skill_dir)
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_dir", lambda: Path("/fake/repo/.oaps")
        )

        result = get_project_skill_dir("my-skill")

        assert result == skill_dir

    def test_returns_none_when_skill_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_dir", lambda: Path("/fake/repo/.oaps")
        )

        result = get_project_skill_dir("nonexistent-skill")

        assert result is None


class TestGetProjectSkillsDir:
    def test_returns_project_skills_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_dir", lambda: Path("/fake/repo/.oaps")
        )

        result = get_project_skills_dir()

        assert result == Path("/fake/repo/.oaps/claude/skills")


class TestGetPlansDir:
    def test_returns_plans_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oaps.utils._paths.get_oaps_dir", lambda: Path("/fake/repo/.oaps")
        )

        result = get_plans_dir()

        assert result == Path("/fake/repo/.oaps/plans")
