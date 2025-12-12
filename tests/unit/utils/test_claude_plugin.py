import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from oaps.utils._claude_plugin import (
    _get_claude_plugin_marketplaces,
    get_claude_plugin_agents_dir,
    get_claude_plugin_commands_dir,
    get_claude_plugin_dir,
    get_claude_plugin_skill_dir,
    get_claude_plugin_skills_dir,
)

if TYPE_CHECKING:
    import pytest
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestGetClaudePluginMarketplaces:
    def test_returns_none_when_file_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert _get_claude_plugin_marketplaces() is None

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
        assert _get_claude_plugin_marketplaces() is None

    def test_returns_none_when_json_is_not_dict(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json", contents=json.dumps(["array"])
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert _get_claude_plugin_marketplaces() is None

    def test_returns_dict_when_valid_json(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        expected_data = {"oaps": {"installLocation": "/some/path"}}
        fs.create_file(
            plugins_dir / "known_marketplaces.json", contents=json.dumps(expected_data)
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        result = _get_claude_plugin_marketplaces()
        assert result == expected_data


class TestGetClaudePluginDir:
    def test_returns_none_when_marketplaces_file_missing(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_dir() is None

    def test_returns_none_when_marketplaces_not_dict(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json", contents=json.dumps(["array"])
        )
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

    def test_returns_none_when_oaps_entry_not_dict(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": "not a dict"}),
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

    def test_returns_none_when_install_location_not_string(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": 123}}),
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


class TestGetClaudePluginAgentsDir:
    def test_returns_none_when_plugin_dir_not_found(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_agents_dir() is None

    def test_returns_agents_dir_when_plugin_found(
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
        result = get_claude_plugin_agents_dir()
        assert result == oaps_dir / "agents"


class TestGetClaudePluginCommandsDir:
    def test_returns_none_when_plugin_dir_not_found(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_commands_dir() is None

    def test_returns_commands_dir_when_plugin_found(
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
        result = get_claude_plugin_commands_dir()
        assert result == oaps_dir / "commands"


class TestGetClaudePluginSkillsDir:
    def test_returns_none_when_plugin_dir_not_found(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        assert get_claude_plugin_skills_dir() is None

    def test_returns_skills_dir_when_plugin_found(
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
        result = get_claude_plugin_skills_dir()
        assert result == oaps_dir / "skills"


class TestGetClaudePluginSkillDir:
    def test_returns_none_when_plugin_skills_dir_not_found_and_not_in_git(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )

        def mock_get_worktree_root() -> Path:
            raise subprocess.CalledProcessError(128, ["git"])

        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", mock_get_worktree_root
        )
        assert get_claude_plugin_skill_dir("test-skill") is None

    def test_returns_plugin_skill_when_found_in_plugin(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        oaps_dir = Path("/fake/oaps-plugin")
        skill_dir = oaps_dir / "skills" / "test-skill"
        fs.create_dir(skill_dir)
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(oaps_dir)}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result == skill_dir

    def test_returns_none_when_skill_not_in_plugin_and_not_in_repo(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        oaps_dir = Path("/fake/oaps-plugin")
        fs.create_dir(oaps_dir / "skills")
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(oaps_dir)}}),
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )

        def mock_get_worktree_root() -> Path:
            raise subprocess.CalledProcessError(128, ["git"])

        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", mock_get_worktree_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result is None

    def test_returns_repo_skill_when_not_in_plugin_but_in_repo(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        oaps_dir = Path("/fake/oaps-plugin")
        fs.create_dir(oaps_dir / "skills")
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(oaps_dir)}}),
        )
        repo_root = Path("/fake/repo")
        skill_dir = repo_root / "skills" / "test-skill"
        fs.create_dir(skill_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", lambda: repo_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result == skill_dir

    def test_returns_plugin_skill_when_in_both_plugin_and_repo(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        plugins_dir = claude_dir / "plugins"
        oaps_dir = Path("/fake/oaps-plugin")
        plugin_skill_dir = oaps_dir / "skills" / "test-skill"
        fs.create_dir(plugin_skill_dir)
        fs.create_file(
            plugins_dir / "known_marketplaces.json",
            contents=json.dumps({"oaps": {"installLocation": str(oaps_dir)}}),
        )
        repo_root = Path("/fake/repo")
        repo_skill_dir = repo_root / "skills" / "test-skill"
        fs.create_dir(repo_skill_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", lambda: repo_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result == plugin_skill_dir

    def test_returns_repo_skill_when_plugin_dir_none(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        repo_root = Path("/fake/repo")
        skill_dir = repo_root / "skills" / "test-skill"
        fs.create_dir(skill_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", lambda: repo_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result == skill_dir

    def test_returns_none_when_git_raises_file_not_found_error(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )

        def mock_get_worktree_root() -> Path:
            raise FileNotFoundError

        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", mock_get_worktree_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result is None

    def test_returns_none_when_repo_skill_dir_not_directory(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        claude_dir = Path("/fake/.claude")
        fs.create_dir(claude_dir)
        repo_root = Path("/fake/repo")
        fs.create_dir(repo_root / "skills")
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_claude_config_dir", lambda: claude_dir
        )
        monkeypatch.setattr(
            "oaps.utils._claude_plugin.get_worktree_root", lambda: repo_root
        )
        result = get_claude_plugin_skill_dir("test-skill")
        assert result is None
