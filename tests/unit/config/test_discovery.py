# pyright: reportAny=false, reportUnknownArgumentType=false
from pathlib import Path
from typing import TYPE_CHECKING

from oaps.config import DEFAULT_CONFIG, ConfigSourceName
from oaps.config._discovery import (
    _file_exists,
    discover_sources,
    find_project_root,
    get_git_dir,
    get_user_config_path,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest_mock import MockerFixture


class TestFindProjectRoot:
    def test_finds_project_root_in_current_directory(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project/.oaps")

        result = find_project_root(Path("/project"))

        assert result == Path("/project")

    def test_finds_project_root_in_parent_directory(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project/.oaps")
        fs.create_dir("/project/subdir/deep")

        result = find_project_root(Path("/project/subdir/deep"))

        assert result == Path("/project")

    def test_returns_none_when_no_project_root_found(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/some/path")

        result = find_project_root(Path("/some/path"))

        assert result is None

    def test_uses_cwd_when_start_is_none(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/cwd/.oaps")
        fs.cwd = "/cwd"

        result = find_project_root(None)

        assert result == Path("/cwd")


class TestGetUserConfigPath:
    def test_returns_path_with_config_toml_filename(self) -> None:
        result = get_user_config_path()

        assert result.name == "config.toml"
        assert result.parent.name == "oaps"


class TestGetGitDir:
    def test_returns_git_dir_when_in_repository(self, mocker: MockerFixture) -> None:
        mock_repo = mocker.MagicMock()
        mock_repo.path = "/repo/.git"
        mock_discover = mocker.patch("dulwich.repo.Repo.discover")
        mock_discover.return_value = mock_repo

        result = get_git_dir(Path("/repo/subdir"))

        assert result == Path("/repo/.git")
        mock_discover.assert_called_once()

    def test_returns_none_when_not_in_repository(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mock_discover = mocker.patch("dulwich.repo.Repo.discover")
        mock_discover.side_effect = NotGitRepository("/path")

        result = get_git_dir(Path("/not/a/repo"))

        assert result is None

    def test_uses_cwd_when_path_is_none(self, mocker: MockerFixture) -> None:
        mock_repo = mocker.MagicMock()
        mock_repo.path = "/cwd/.git"
        mock_discover = mocker.patch("dulwich.repo.Repo.discover")
        mock_discover.return_value = mock_repo

        result = get_git_dir(None)

        assert result == Path("/cwd/.git")
        mock_discover.assert_called_once_with(".")


class TestFileExists:
    def test_returns_true_for_existing_file(self, fs: FakeFilesystem) -> None:
        fs.create_file("/test/file.txt")

        result = _file_exists(Path("/test/file.txt"))

        assert result is True

    def test_returns_false_for_missing_file(self, fs: FakeFilesystem) -> None:
        result = _file_exists(Path("/test/missing.txt"))

        assert result is False

    def test_returns_false_for_directory(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/test/dir")

        result = _file_exists(Path("/test/dir"))

        assert result is False


class TestDiscoverSources:
    def test_returns_sources_in_precedence_order_with_project(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        fs.create_file("/project/.oaps/oaps.toml")
        fs.create_file("/project/.oaps/oaps.local.toml")
        fs.create_dir("/project/.git")
        fs.create_file("/project/.git/oaps.toml")

        mocker.patch(
            "oaps.config._discovery.get_git_dir", return_value=Path("/project/.git")
        )

        sources = discover_sources(Path("/project"))

        source_names = [s.name for s in sources]
        assert source_names == [
            ConfigSourceName.ENV,
            ConfigSourceName.WORKTREE,
            ConfigSourceName.LOCAL,
            ConfigSourceName.PROJECT,
            ConfigSourceName.USER,
            ConfigSourceName.DEFAULT,
        ]

    def test_includes_cli_source_when_requested(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(
            Path("/project"),
            include_cli=True,
            cli_overrides={"logging": {"level": "debug"}},
        )

        assert sources[0].name == ConfigSourceName.CLI
        assert sources[0].exists is True
        assert sources[0].values == {"logging": {"level": "debug"}}

    def test_cli_source_exists_false_when_no_overrides(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(
            Path("/project"),
            include_cli=True,
            cli_overrides=None,
        )

        assert sources[0].name == ConfigSourceName.CLI
        assert sources[0].exists is False
        assert sources[0].values == {}

    def test_excludes_env_source_when_not_requested(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(Path("/project"), include_env=False)

        source_names = [s.name for s in sources]
        assert ConfigSourceName.ENV not in source_names

    def test_omits_project_sources_when_no_project_root(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        mocker.patch("oaps.config._discovery.find_project_root", return_value=None)

        sources = discover_sources(None)

        source_names = [s.name for s in sources]
        assert ConfigSourceName.WORKTREE not in source_names
        assert ConfigSourceName.LOCAL not in source_names
        assert ConfigSourceName.PROJECT not in source_names
        assert ConfigSourceName.USER in source_names
        assert ConfigSourceName.DEFAULT in source_names

    def test_marks_existing_files_correctly(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        fs.create_file("/project/.oaps/oaps.toml")
        # oaps.local.toml does NOT exist
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(Path("/project"))

        project_source = next(s for s in sources if s.name == ConfigSourceName.PROJECT)
        local_source = next(s for s in sources if s.name == ConfigSourceName.LOCAL)

        assert project_source.exists is True
        assert local_source.exists is False

    def test_default_source_has_default_config_values(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(Path("/project"))

        default_source = next(s for s in sources if s.name == ConfigSourceName.DEFAULT)

        assert default_source.exists is True
        assert default_source.path is None
        assert default_source.values == DEFAULT_CONFIG

    def test_file_sources_have_correct_paths(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch(
            "oaps.config._discovery.get_git_dir", return_value=Path("/project/.git")
        )

        sources = discover_sources(Path("/project"))

        worktree_source = next(
            s for s in sources if s.name == ConfigSourceName.WORKTREE
        )
        local_source = next(s for s in sources if s.name == ConfigSourceName.LOCAL)
        project_source = next(s for s in sources if s.name == ConfigSourceName.PROJECT)

        assert worktree_source.path == Path("/project/.git/oaps.toml")
        assert local_source.path == Path("/project/.oaps/oaps.local.toml")
        assert project_source.path == Path("/project/.oaps/oaps.toml")

    def test_worktree_source_omitted_when_not_in_git_repo(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(Path("/project"))

        source_names = [s.name for s in sources]
        assert ConfigSourceName.WORKTREE not in source_names

    def test_user_source_always_included(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        mocker.patch("oaps.config._discovery.find_project_root", return_value=None)

        sources = discover_sources(None)

        user_source = next(s for s in sources if s.name == ConfigSourceName.USER)

        assert user_source is not None
        assert user_source.path is not None

    def test_env_source_has_empty_values(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(Path("/project"))

        env_source = next(s for s in sources if s.name == ConfigSourceName.ENV)

        assert env_source.exists is True
        assert env_source.path is None
        assert env_source.values == {}

    def test_auto_detects_project_root_when_not_provided(
        self, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        fs.create_dir("/project/.oaps")
        fs.create_file("/project/.oaps/oaps.toml")
        fs.cwd = "/project/subdir"
        fs.create_dir("/project/subdir")
        mocker.patch("oaps.config._discovery.get_git_dir", return_value=None)

        sources = discover_sources(None)

        source_names = [s.name for s in sources]
        assert ConfigSourceName.PROJECT in source_names
        project_source = next(s for s in sources if s.name == ConfigSourceName.PROJECT)
        assert project_source.path == Path("/project/.oaps/oaps.toml")
