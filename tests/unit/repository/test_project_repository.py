"""Unit tests for ProjectRepository class."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from oaps.exceptions import (
    OapsRepositoryPathViolationError,
    ProjectRepositoryNotInitializedError,
)
from oaps.repository import BlameLine, ProjectRepository, ProjectRepoStatus

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a mock project directory with .git."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def project_with_oaps(tmp_path: Path) -> Path:
    """Create a mock project directory with .git and .oaps."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".oaps").mkdir()
    return tmp_path


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> MagicMock:
    """Create a mock dulwich Repo."""
    mock = MagicMock()
    mocker.patch("oaps.repository._base.Repo", return_value=mock)
    return mock


@pytest.fixture
def empty_status(mocker: MockerFixture) -> MagicMock:
    """Create a mock GitStatus with no changes."""
    mock_status = MagicMock()
    mock_status.staged = {"add": [], "delete": [], "modify": []}
    mock_status.unstaged = []
    mock_status.untracked = []
    mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
    return mock_status


class TestProjectRepositoryInit:
    def test_raises_error_when_not_in_git_repo(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectRepositoryNotInitializedError) as exc_info:
            ProjectRepository(worktree_dir=tmp_path)

        assert "Not inside a Git repository" in str(exc_info.value)
        assert exc_info.value.path == tmp_path

    def test_discovers_root_from_project_directory(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        assert repo.root == project_dir.resolve()

    def test_discovers_root_from_subdirectory(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        subdir = project_dir / "src" / "deep" / "nested"
        subdir.mkdir(parents=True)

        repo = ProjectRepository(worktree_dir=subdir)
        assert repo.root == project_dir.resolve()

    def test_discovers_root_with_git_file_worktree(
        self, tmp_path: Path, mock_repo: MagicMock
    ) -> None:
        # Git worktrees use a .git file pointing to the main repo, not a directory
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /path/to/main/repo/.git/worktrees/feature")

        repo = ProjectRepository(worktree_dir=tmp_path)
        assert repo.root == tmp_path.resolve()

    def test_uses_cwd_when_worktree_dir_none(self, mocker: MockerFixture) -> None:
        mock_cwd = Path("/mock/cwd")
        mocker.patch.object(Path, "cwd", return_value=mock_cwd)
        mock_exists = mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("oaps.repository._base.Repo")

        ProjectRepository(worktree_dir=None)

        mock_exists.assert_called()


class TestProjectRepositoryValidatePath:
    def test_validate_path_returns_true_for_project_path(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        assert repo.validate_path(project_dir / "some_file.txt") is True
        assert repo.validate_path(project_dir / "subdir" / "nested.txt") is True

    def test_validate_path_returns_false_for_path_outside_project(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        assert repo.validate_path(project_dir.parent / "outside.txt") is False
        assert repo.validate_path(Path("/some/other/path")) is False

    def test_validate_path_returns_false_for_oaps_path(
        self, project_with_oaps: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_with_oaps)

        # .oaps/ directory itself
        assert repo.validate_path(project_with_oaps / ".oaps") is False
        # Files inside .oaps/
        assert repo.validate_path(project_with_oaps / ".oaps" / "config.toml") is False
        assert (
            repo.validate_path(
                project_with_oaps / ".oaps" / "docs" / "specs" / "SPEC-0001.md"
            )
            is False
        )

    def test_validate_path_returns_false_for_oaps_path_even_when_dir_does_not_exist(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        # .oaps doesn't exist in project_dir (only .git does)
        repo = ProjectRepository(worktree_dir=project_dir)

        # Paths inside .oaps/ should be rejected even if .oaps/ doesn't exist yet
        # This prevents accidental creation of .oaps/ files through ProjectRepository
        assert repo.validate_path(project_dir / ".oaps" / "config.toml") is False
        assert repo.validate_path(project_dir / ".oaps") is False

        # Regular project paths should still work
        assert repo.validate_path(project_dir / "src" / "main.py") is True

    def test_resolves_path_before_validation(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Using .. to stay within project should resolve correctly
        path_with_dots = project_dir / "subdir" / ".." / "file.txt"
        assert repo.validate_path(path_with_dots) is True

    def test_returns_false_for_parent_traversal_escape(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Path that tries to escape using parent traversal
        escape_path = project_dir / ".." / "outside.txt"
        assert repo.validate_path(escape_path) is False

    def test_returns_false_for_symlink_pointing_outside(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        # Create a file outside project
        external_file = project_dir.parent / "external.txt"
        external_file.touch()

        # Create a symlink inside project that points outside
        symlink_inside = project_dir / "escape_link"
        symlink_inside.symlink_to(external_file)

        repo = ProjectRepository(worktree_dir=project_dir)

        # The symlink resolves to outside project, should return False
        assert repo.validate_path(symlink_inside) is False

    def test_returns_true_for_symlink_pointing_inside(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        # Create a file inside project
        internal_file = project_dir / "internal.txt"
        internal_file.touch()

        # Create a symlink inside project that points to another file inside
        symlink_inside = project_dir / "internal_link"
        symlink_inside.symlink_to(internal_file)

        repo = ProjectRepository(worktree_dir=project_dir)

        # The symlink resolves to inside project, should return True
        assert repo.validate_path(symlink_inside) is True


class TestProjectRepositoryGetStatus:
    def test_get_status_returns_project_repo_status(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"new.txt"], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = [b"untracked.txt"]
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = ProjectRepository(worktree_dir=project_dir)
        status = repo.get_status()

        assert isinstance(status, ProjectRepoStatus)
        assert project_dir.resolve() / "new.txt" in status.staged
        assert project_dir.resolve() / "modified.txt" in status.modified
        assert project_dir.resolve() / "untracked.txt" in status.untracked

    def test_get_status_returns_empty_when_no_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        status = repo.get_status()

        assert status.staged == frozenset()
        assert status.modified == frozenset()
        assert status.untracked == frozenset()


class TestProjectRepositoryContextManager:
    def test_context_manager_protocol(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        with ProjectRepository(worktree_dir=project_dir) as repo:
            assert repo.root == project_dir.resolve()

        mock_repo.close.assert_called_once()

    def test_context_manager_closes_on_exception(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        with (
            pytest.raises(ValueError, match="test error"),
            ProjectRepository(worktree_dir=project_dir),
        ):
            msg = "test error"
            raise ValueError(msg)

        mock_repo.close.assert_called_once()

    def test_close_releases_resources(
        self, project_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        repo.close()
        mock_repo.close.assert_called_once()


class TestProjectRepositoryHasChanges:
    def test_returns_false_when_no_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        assert repo.has_changes() is False

    def test_returns_true_when_staged_files_exist(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"new_file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = ProjectRepository(worktree_dir=project_dir)
        assert repo.has_changes() is True


class TestProjectRepositoryCommitOperations:
    def test_commit_creates_commit(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Mock status to show a staged file
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"new_file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        # Mock commit to return a SHA
        commit_sha = bytes.fromhex("a" * 40)
        mock_porcelain_commit = mocker.patch(
            "oaps.repository._base.porcelain.commit", return_value=commit_sha
        )

        # Mock repo head and commit object for race detection
        mock_repo.head.return_value = bytes.fromhex("b" * 40)
        mock_commit_obj = MagicMock()
        mock_commit_obj.parents = [bytes.fromhex("b" * 40)]
        mock_repo.__getitem__.return_value = mock_commit_obj

        repo = ProjectRepository(worktree_dir=project_dir)
        result = repo.commit("Test commit message")

        assert result.sha == "a" * 40
        assert result.no_changes is False
        assert project_dir.resolve() / "new_file.txt" in result.files
        mock_porcelain_commit.assert_called_once()

    def test_commit_no_changes_returns_no_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        result = repo.commit("Test commit message")

        assert result.no_changes is True
        assert result.sha is None
        assert result.files == frozenset()

    def test_rejects_commit_of_oaps_files(
        self,
        project_with_oaps: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Create a file inside .oaps/ directory
        oaps_file = project_with_oaps / ".oaps" / "test_file.txt"
        oaps_file.write_text("test content")

        repo = ProjectRepository(worktree_dir=project_with_oaps)

        # Attempting to stage a file in .oaps/ should raise an exception
        with pytest.raises(OapsRepositoryPathViolationError) as exc_info:
            repo.stage([oaps_file])

        assert exc_info.value.path == oaps_file
        assert "outside repository scope" in str(exc_info.value)


class TestProjectRepositoryCustomOapsDirName:
    def test_uses_custom_oaps_dir_name_for_exclusion(
        self, tmp_path: Path, mock_repo: MagicMock
    ) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".custom-oaps").mkdir()

        repo = ProjectRepository(worktree_dir=tmp_path, oaps_dir_name=".custom-oaps")

        # Regular project files are valid
        assert repo.validate_path(tmp_path / "src" / "main.py") is True

        # Custom oaps dir is excluded
        assert repo.validate_path(tmp_path / ".custom-oaps" / "config.toml") is False

        # Default .oaps would be valid since we're using custom name
        assert repo.validate_path(tmp_path / ".oaps" / "config.toml") is True


class TestProjectRepositoryPublicExports:
    def test_exports_available_from_package(self) -> None:
        from oaps.repository import ProjectRepository, ProjectRepoStatus

        assert ProjectRepoStatus is not None
        assert ProjectRepository is not None


class TestProjectRepositoryGetDiff:
    def test_get_diff_returns_empty_string_when_no_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Mock porcelain.status to return no changes
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch(
            "oaps.repository._project.porcelain.status", return_value=mock_status
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        diff = repo.get_diff(staged=False)

        assert diff == ""

    def test_get_diff_staged_returns_empty_when_no_staged_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Mock tree_changes to return no changes
        mocker.patch(
            "oaps.repository._project.tree_changes",
            return_value=iter([]),
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        # Mock internal methods to avoid dulwich calls
        mocker.patch.object(repo, "_get_head_tree", return_value=b"fake_tree")
        mocker.patch.object(repo, "_get_index_tree_sha", return_value=b"fake_index")

        diff = repo.get_diff(staged=True)

        assert diff == ""

    def test_get_diff_filters_oaps_paths(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Create .oaps dir for the filter check
        (project_dir / ".oaps").mkdir()

        # Mock status with only .oaps files
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b".oaps/config.toml", b".oaps/docs/specs/test.md"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch(
            "oaps.repository._project.porcelain.status", return_value=mock_status
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        diff = repo.get_diff(staged=False)

        # Should be empty because all files are in .oaps/
        assert diff == ""


class TestProjectRepositoryGetDiffStats:
    def test_get_diff_stats_returns_empty_when_no_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch(
            "oaps.repository._project.porcelain.status", return_value=mock_status
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        stats = repo.get_diff_stats(staged=False)

        assert stats.files_changed == 0
        assert stats.total_additions == 0
        assert stats.total_deletions == 0
        assert stats.files == ()

    def test_get_diff_stats_staged_returns_empty_when_no_staged_changes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "oaps.repository._project.tree_changes",
            return_value=iter([]),
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_tree", return_value=b"fake_tree")
        mocker.patch.object(repo, "_get_index_tree_sha", return_value=b"fake_index")

        stats = repo.get_diff_stats(staged=True)

        assert stats.files_changed == 0
        assert stats.total_additions == 0
        assert stats.total_deletions == 0

    def test_get_diff_stats_filters_oaps_paths(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        (project_dir / ".oaps").mkdir()

        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b".oaps/config.toml"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch(
            "oaps.repository._project.porcelain.status", return_value=mock_status
        )

        repo = ProjectRepository(worktree_dir=project_dir)
        stats = repo.get_diff_stats(staged=False)

        assert stats.files_changed == 0

    def test_diff_stats_exports_available_from_package(self) -> None:
        from oaps.repository import DiffStats, FileDiffStats

        assert DiffStats is not None
        assert FileDiffStats is not None


class TestProjectRepositoryIsOapsPath:
    def test_is_oaps_path_detects_oaps_directory(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        assert repo._is_oaps_path(".oaps") is True
        assert repo._is_oaps_path(".oaps/config.toml") is True
        assert repo._is_oaps_path(".oaps/docs/specs/test.md") is True

    def test_is_oaps_path_allows_non_oaps_paths(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        assert repo._is_oaps_path("src/main.py") is False
        assert repo._is_oaps_path("README.md") is False
        assert repo._is_oaps_path(".oaps-like/file.txt") is False

    def test_is_oaps_path_respects_custom_dir_name(
        self,
        tmp_path: Path,
        mock_repo: MagicMock,
    ) -> None:
        (tmp_path / ".git").mkdir()
        repo = ProjectRepository(worktree_dir=tmp_path, oaps_dir_name=".custom")

        assert repo._is_oaps_path(".custom") is True
        assert repo._is_oaps_path(".custom/file.txt") is True
        assert repo._is_oaps_path(".oaps/file.txt") is False


class TestProjectRepositoryComputeLineStats:
    def test_compute_line_stats_counts_additions(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        old_content = b"line1\nline2\n"
        new_content = b"line1\nline2\nline3\nline4\n"

        additions, deletions = repo._compute_line_stats(old_content, new_content)

        assert additions == 2
        assert deletions == 0

    def test_compute_line_stats_counts_deletions(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        old_content = b"line1\nline2\nline3\nline4\n"
        new_content = b"line1\nline2\n"

        additions, deletions = repo._compute_line_stats(old_content, new_content)

        assert additions == 0
        assert deletions == 2

    def test_compute_line_stats_counts_replacements(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        old_content = b"line1\noriginal\nline3\n"
        new_content = b"line1\nreplacement\nline3\n"

        additions, deletions = repo._compute_line_stats(old_content, new_content)

        # Replacement counts as 1 deletion + 1 addition
        assert additions == 1
        assert deletions == 1

    def test_compute_line_stats_handles_empty_content(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # New file (old is empty)
        additions, deletions = repo._compute_line_stats(b"", b"line1\nline2\n")
        assert additions == 2
        assert deletions == 0

        # Deleted file (new is empty)
        additions, deletions = repo._compute_line_stats(b"line1\nline2\n", b"")
        assert additions == 0
        assert deletions == 2


class TestProjectRepositoryGetLog:
    def test_get_log_returns_empty_list_when_no_commits(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Mock _get_head_sha to return None (no commits)
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value=None)

        result = repo.get_log()

        assert result == []

    def test_get_log_respects_n_limit(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create mock walker that yields 5 entries
        mock_entries = []
        for i in range(5):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = b"Test <test@example.com>"
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        # Request only 3 commits
        result = repo.get_log(n=3)

        assert len(result) == 3

    def test_get_log_filters_by_grep_case_insensitive(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create mock entries with different messages
        mock_entries = []
        messages = [b"Fix bug in parser", b"Add new feature", b"BUGFIX for login"]
        for i, msg in enumerate(messages):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = b"Test <test@example.com>"
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = msg
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        # Search for "bug" (case-insensitive)
        result = repo.get_log(grep="bug")

        assert len(result) == 2
        assert "Fix bug" in result[0].message
        assert "BUGFIX" in result[1].message

    def test_get_log_filters_by_author_name(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create mock entries with different authors
        mock_entries = []
        authors = [
            b"Alice Smith <alice@example.com>",
            b"Bob Jones <bob@example.com>",
            b"ALICE Walker <alice.w@example.com>",
        ]
        for i, author in enumerate(authors):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = author
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        # Search for "alice" (case-insensitive)
        result = repo.get_log(author="alice")

        assert len(result) == 2

    def test_get_log_filters_by_author_email(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_entries = []
        authors = [
            b"User One <user@company.com>",
            b"User Two <user@example.com>",
            b"User Three <admin@company.com>",
        ]
        for i, author in enumerate(authors):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = author
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        # Search by email domain
        result = repo.get_log(author="company.com")

        assert len(result) == 2

    def test_get_log_combines_filters_with_and_logic(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create commits: only one matches both grep AND author
        mock_entries = []
        data = [
            (b"Alice <alice@example.com>", b"Fix bug in parser"),
            (b"Bob <bob@example.com>", b"Fix another bug"),
            (b"Alice <alice@example.com>", b"Add feature"),
        ]
        for i, (author, msg) in enumerate(data):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = author
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = msg
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        # Both grep="bug" AND author="alice"
        result = repo.get_log(grep="bug", author="alice")

        assert len(result) == 1
        assert "Fix bug" in result[0].message
        assert result[0].author_name == "Alice"

    def test_get_log_returns_commit_info_with_all_fields(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from datetime import datetime

        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        entry = MagicMock()
        entry.commit.id = bytes.fromhex("abc123" + "0" * 34)
        entry.commit.author = b"Test Author <test@example.com>"
        entry.commit.author_time = 1700000000
        entry.commit.author_timezone = 0
        entry.commit.message = b"Test commit message\n\nWith body"
        entry.commit.parents = [bytes.fromhex("def456" + "0" * 34)]

        mock_repo.get_walker.return_value = iter([entry])
        mocker.patch.object(repo, "_count_files_changed", return_value=3)

        result = repo.get_log(n=1)

        assert len(result) == 1
        commit = result[0]
        assert commit.sha == "abc123" + "0" * 34
        assert commit.message == "Test commit message\n\nWith body"
        assert commit.author_name == "Test Author"
        assert commit.author_email == "test@example.com"
        assert isinstance(commit.timestamp, datetime)
        assert commit.files_changed == 3
        assert commit.parent_shas == ("def456" + "0" * 34,)

    def test_get_log_path_outside_repo_returns_empty(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Path completely outside repo
        external_path = Path("/some/other/path/file.txt")
        result = repo.get_log(path=external_path)

        assert result == []
        # Verify walker was not called (early return optimization)
        mock_repo.get_walker.assert_not_called()

    def test_get_log_path_filtering_passes_to_walker(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Empty walker result
        mock_repo.get_walker.return_value = iter([])

        # Call with path filter
        target_path = project_dir / "src" / "main.py"
        repo.get_log(path=target_path)

        # Verify walker was called with paths parameter
        call_kwargs = mock_repo.get_walker.call_args.kwargs
        assert "paths" in call_kwargs
        assert call_kwargs["paths"] == [b"src/main.py"]

    def test_get_log_uses_overscan_when_filtering(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_repo.get_walker.return_value = iter([])

        # Call with n=5 and grep filter
        repo.get_log(n=5, grep="test")

        # Verify walker was called with 10x max_entries for overscan
        call_kwargs = mock_repo.get_walker.call_args.kwargs
        assert call_kwargs["max_entries"] == 50  # 5 * 10

    def test_get_log_no_overscan_without_filters(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_repo.get_walker.return_value = iter([])

        # Call with n=5, no filters
        repo.get_log(n=5)

        # Verify walker was called with exact max_entries (no overscan)
        call_kwargs = mock_repo.get_walker.call_args.kwargs
        assert call_kwargs["max_entries"] == 5


class TestProjectRepositoryGetBlame:
    # =========================================================================
    # Path Validation Tests
    # =========================================================================

    def test_get_blame_raises_file_not_found_for_nonexistent_file(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        nonexistent = project_dir / "nonexistent.py"

        with pytest.raises(FileNotFoundError, match="File not found"):
            repo.get_blame(nonexistent)

    def test_get_blame_raises_path_violation_for_oaps_path(
        self,
        project_with_oaps: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_with_oaps)
        oaps_file = project_with_oaps / ".oaps" / "config.toml"
        oaps_file.parent.mkdir(parents=True, exist_ok=True)
        oaps_file.touch()

        with pytest.raises(OapsRepositoryPathViolationError) as exc_info:
            repo.get_blame(oaps_file)

        assert exc_info.value.path == oaps_file
        assert "outside repository scope or in .oaps" in str(exc_info.value)

    def test_get_blame_raises_file_not_found_for_directory(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        subdir = project_dir / "subdir"
        subdir.mkdir()

        with pytest.raises(FileNotFoundError, match="Not a file"):
            repo.get_blame(subdir)

    def test_get_blame_accepts_relative_path(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()

        # Mock subprocess to return empty (untracked file)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="")

        relative_path = Path("src/main.py")
        result = repo.get_blame(relative_path)

        assert result == []
        mock_run.assert_called_once()

    def test_get_blame_accepts_absolute_path(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "main.py"
        test_file.touch()

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="")

        result = repo.get_blame(test_file)

        assert result == []

    # =========================================================================
    # Subprocess Execution Tests
    # =========================================================================

    def test_get_blame_returns_empty_list_for_untracked_file(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "untracked.py"
        test_file.write_text("print('hello')")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: no such path 'untracked.py' in HEAD",
        )

        result = repo.get_blame(test_file)

        assert result == []
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "blame", "--porcelain", "--", "untracked.py"]
        assert call_args[1]["cwd"] == str(project_dir.resolve())

    def test_get_blame_returns_empty_list_for_empty_file(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        empty_file = project_dir / "empty.py"
        empty_file.touch()

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = repo.get_blame(empty_file)

        assert result == []

    # =========================================================================
    # Parsing Tests
    # =========================================================================

    def test_get_blame_parses_porcelain_output_correctly(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "test.py"
        test_file.touch()

        porcelain_output = """\
abc1234567890abc1234567890abc1234567890ab 1 1 1
author Test Author
author-mail <test@example.com>
author-time 1700000000
author-tz +0000
committer Test Author
committer-mail <test@example.com>
committer-time 1700000000
committer-tz +0000
summary Initial commit
filename test.py
\tprint('hello world')
"""

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout=porcelain_output)

        result = repo.get_blame(test_file)

        assert len(result) == 1
        blame_line = result[0]
        assert blame_line.line_no == 1
        assert blame_line.content == "print('hello world')"
        assert blame_line.sha == "abc1234567890abc1234567890abc1234567890ab"
        assert blame_line.author_name == "Test Author"
        assert blame_line.author_email == "test@example.com"
        assert isinstance(blame_line.timestamp, datetime)

    def test_get_blame_caches_repeated_commit_info(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "test.py"
        test_file.touch()

        # Porcelain output with same SHA appearing multiple times
        # First occurrence has full metadata, subsequent ones only header
        porcelain_output = """\
abc1234567890abc1234567890abc1234567890ab 1 1 3
author Test Author
author-mail <test@example.com>
author-time 1700000000
author-tz +0000
committer Test Author
committer-mail <test@example.com>
committer-time 1700000000
committer-tz +0000
summary Initial commit
filename test.py
\tline one
abc1234567890abc1234567890abc1234567890ab 2 2
\tline two
abc1234567890abc1234567890abc1234567890ab 3 3
\tline three
"""

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout=porcelain_output)

        result = repo.get_blame(test_file)

        assert len(result) == 3

        # All lines should have the same author info from cache
        for i, blame_line in enumerate(result, start=1):
            assert blame_line.line_no == i
            assert blame_line.sha == "abc1234567890abc1234567890abc1234567890ab"
            assert blame_line.author_name == "Test Author"
            assert blame_line.author_email == "test@example.com"

        assert result[0].content == "line one"
        assert result[1].content == "line two"
        assert result[2].content == "line three"

    def test_get_blame_handles_multiple_authors(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        test_file = project_dir / "test.py"
        test_file.touch()

        # Different commits for different lines
        porcelain_output = """\
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 1 1
author Alice Author
author-mail <alice@example.com>
author-time 1700000000
author-tz +0000
committer Alice Author
committer-mail <alice@example.com>
committer-time 1700000000
committer-tz +0000
summary Alice's commit
filename test.py
\tdef hello():
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 2 2 1
author Bob Builder
author-mail <bob@example.com>
author-time 1700001000
author-tz -0500
committer Bob Builder
committer-mail <bob@example.com>
committer-time 1700001000
committer-tz -0500
summary Bob's commit
filename test.py
\t    print('hi')
"""

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout=porcelain_output)

        result = repo.get_blame(test_file)

        assert len(result) == 2

        assert result[0].line_no == 1
        assert result[0].author_name == "Alice Author"
        assert result[0].author_email == "alice@example.com"
        assert result[0].sha == "a" * 40

        assert result[1].line_no == 2
        assert result[1].author_name == "Bob Builder"
        assert result[1].author_email == "bob@example.com"
        assert result[1].sha == "b" * 40

    # =========================================================================
    # Timestamp Parsing Tests
    # =========================================================================

    def test_parse_blame_timestamp_positive_offset(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # +0100 = UTC + 1 hour
        result = repo._parse_blame_timestamp(1700000000, "+0100")

        expected_tz = timezone(timedelta(hours=1))
        expected = datetime.fromtimestamp(1700000000, tz=expected_tz)
        assert result == expected

    def test_parse_blame_timestamp_negative_offset(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # -0500 = UTC - 5 hours
        result = repo._parse_blame_timestamp(1700000000, "-0500")

        expected_tz = timezone(timedelta(hours=-5))
        expected = datetime.fromtimestamp(1700000000, tz=expected_tz)
        assert result == expected

    def test_parse_blame_timestamp_utc(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        result = repo._parse_blame_timestamp(1700000000, "+0000")

        expected = datetime.fromtimestamp(1700000000, tz=UTC)
        assert result == expected

    def test_parse_blame_timestamp_invalid_fallback_to_utc(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Invalid timezone strings should fall back to UTC
        invalid_cases = ["", "invalid", "+00", "ABC", None]

        for invalid_tz in invalid_cases:
            # Handle None case
            tz_str = invalid_tz if invalid_tz is not None else ""
            result = repo._parse_blame_timestamp(1700000000, tz_str)
            expected = datetime.fromtimestamp(1700000000, tz=UTC)
            assert result == expected, f"Failed for timezone: {invalid_tz!r}"

    def test_parse_blame_timestamp_with_minutes_offset(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # +0530 = UTC + 5 hours 30 minutes (India Standard Time)
        result = repo._parse_blame_timestamp(1700000000, "+0530")

        expected_tz = timezone(timedelta(hours=5, minutes=30))
        expected = datetime.fromtimestamp(1700000000, tz=expected_tz)
        assert result == expected


class TestBlameLineModel:
    def test_blame_line_is_frozen_dataclass(self) -> None:
        blame = BlameLine(
            line_no=1,
            content="test content",
            sha="a" * 40,
            author_name="Test Author",
            author_email="test@example.com",
            timestamp=datetime.now(tz=UTC),
        )

        with pytest.raises(FrozenInstanceError):
            blame.line_no = 2  # pyright: ignore[reportAttributeAccessIssue]

    def test_blame_line_exported_from_package(self) -> None:
        from oaps.repository import BlameLine

        assert BlameLine is not None

        # Verify it has expected attributes
        blame = BlameLine(
            line_no=1,
            content="content",
            sha="a" * 40,
            author_name="Author",
            author_email="author@example.com",
            timestamp=datetime.now(tz=UTC),
        )

        assert hasattr(blame, "line_no")
        assert hasattr(blame, "content")
        assert hasattr(blame, "sha")
        assert hasattr(blame, "author_name")
        assert hasattr(blame, "author_email")
        assert hasattr(blame, "timestamp")

    def test_blame_line_equality(self) -> None:
        ts = datetime.now(tz=UTC)
        blame1 = BlameLine(
            line_no=1,
            content="test",
            sha="a" * 40,
            author_name="Author",
            author_email="author@example.com",
            timestamp=ts,
        )
        blame2 = BlameLine(
            line_no=1,
            content="test",
            sha="a" * 40,
            author_name="Author",
            author_email="author@example.com",
            timestamp=ts,
        )

        assert blame1 == blame2

    def test_blame_line_uses_slots(self) -> None:
        assert hasattr(BlameLine, "__slots__")


class TestProjectRepositorySearchCommits:
    def test_search_commits_returns_empty_list_when_no_commits(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value=None)

        result = repo.search_commits()

        assert result == []

    def test_search_commits_returns_all_when_no_filters(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create mock entries
        mock_entries = []
        for i in range(5):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = b"Test <test@example.com>"
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        result = repo.search_commits(max_entries=10)

        assert len(result) == 5  # All commits returned

    def test_search_commits_respects_max_entries(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        # Create 10 mock entries
        mock_entries = []
        for i in range(10):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = b"Test <test@example.com>"
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        result = repo.search_commits(max_entries=3)

        assert len(result) == 3

    def test_search_commits_filters_by_grep(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_entries = []
        messages = [b"Fix bug in parser", b"Add feature", b"BUGFIX for login"]
        for i, msg in enumerate(messages):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = b"Test <test@example.com>"
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = msg
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        result = repo.search_commits(grep="bug")

        assert len(result) == 2
        assert "Fix bug" in result[0].message
        assert "BUGFIX" in result[1].message

    def test_search_commits_filters_by_author(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_entries = []
        authors = [
            b"Alice <alice@example.com>",
            b"Bob <bob@example.com>",
            b"ALICE Walker <alice.w@example.com>",
        ]
        for i, author in enumerate(authors):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = author
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = f"Commit {i}".encode()
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        result = repo.search_commits(author="alice")

        assert len(result) == 2

    def test_search_commits_combines_filters_with_and_logic(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)

        mock_entries = []
        data = [
            (b"Alice <alice@example.com>", b"Fix bug in parser"),
            (b"Bob <bob@example.com>", b"Fix another bug"),
            (b"Alice <alice@example.com>", b"Add feature"),
        ]
        for i, (author, msg) in enumerate(data):
            entry = MagicMock()
            entry.commit.id = bytes.fromhex(f"{i:040x}")
            entry.commit.author = author
            entry.commit.author_time = 1700000000 + i
            entry.commit.author_timezone = 0
            entry.commit.message = msg
            entry.commit.parents = []
            mock_entries.append(entry)

        mock_repo.get_walker.return_value = iter(mock_entries)
        mocker.patch.object(repo, "_count_files_changed", return_value=1)

        result = repo.search_commits(grep="bug", author="alice")

        assert len(result) == 1
        assert "Fix bug" in result[0].message

    def test_search_commits_uses_overscan_when_filtering(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)
        mock_repo.get_walker.return_value = iter([])

        repo.search_commits(max_entries=100, grep="test")

        call_kwargs = mock_repo.get_walker.call_args.kwargs
        # 100 * 10 (overscan multiplier) = 1000
        assert call_kwargs["max_entries"] == 1000

    def test_search_commits_no_overscan_without_filters(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        mocker.patch.object(repo, "_get_head_sha", return_value="a" * 40)
        mock_repo.get_walker.return_value = iter([])

        repo.search_commits(max_entries=100)

        call_kwargs = mock_repo.get_walker.call_args.kwargs
        assert call_kwargs["max_entries"] == 100


class TestProjectRepositoryGetFileAtCommit:
    def test_get_file_at_commit_returns_content(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Mock SHA resolution
        sha_bytes = bytes.fromhex("a" * 40)
        mocker.patch.object(repo, "_resolve_abbreviated_sha", return_value=sha_bytes)

        # Mock commit with tree
        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha_bytes_here"
        mock_repo.__getitem__.return_value = mock_commit

        # Mock tree_lookup_path to return blob sha
        blob_sha = b"blob_sha_bytes_here"
        mocker.patch(
            "oaps.repository._project.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )

        # Mock blob content
        mock_blob = MagicMock()
        mock_blob.data = b"file content here"

        def get_item(key: bytes) -> MagicMock:
            if key == sha_bytes:
                return mock_commit
            if key == blob_sha:
                return mock_blob
            return MagicMock(tree=b"tree")

        mock_repo.__getitem__.side_effect = get_item

        result = repo.get_file_at_commit(Path("src/main.py"), "a" * 40)

        assert result == b"file content here"

    def test_get_file_at_commit_returns_none_for_missing_file(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        sha_bytes = bytes.fromhex("a" * 40)
        mocker.patch.object(repo, "_resolve_abbreviated_sha", return_value=sha_bytes)

        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha_bytes_here"
        mock_repo.__getitem__.return_value = mock_commit

        # Mock tree_lookup_path to raise KeyError (file not found)
        mocker.patch(
            "oaps.repository._project.tree_lookup_path",
            side_effect=KeyError("path not found"),
        )

        result = repo.get_file_at_commit(Path("nonexistent.py"), "a" * 40)

        assert result is None

    def test_get_file_at_commit_accepts_relative_path(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        sha_bytes = bytes.fromhex("a" * 40)
        mocker.patch.object(repo, "_resolve_abbreviated_sha", return_value=sha_bytes)

        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha"
        mock_repo.__getitem__.return_value = mock_commit

        mock_lookup = mocker.patch(
            "oaps.repository._project.tree_lookup_path",
            side_effect=KeyError("not found"),
        )

        repo.get_file_at_commit(Path("src/main.py"), "a" * 40)

        # Verify the path was passed as bytes
        mock_lookup.assert_called_once()
        call_args = mock_lookup.call_args
        assert call_args[0][2] == b"src/main.py"

    def test_get_file_at_commit_accepts_absolute_path(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        sha_bytes = bytes.fromhex("a" * 40)
        mocker.patch.object(repo, "_resolve_abbreviated_sha", return_value=sha_bytes)

        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha"
        mock_repo.__getitem__.return_value = mock_commit

        mock_lookup = mocker.patch(
            "oaps.repository._project.tree_lookup_path",
            side_effect=KeyError("not found"),
        )

        # Use absolute path
        abs_path = project_dir / "src" / "main.py"
        repo.get_file_at_commit(abs_path.resolve(), "a" * 40)

        # Verify the path was converted to relative
        mock_lookup.assert_called_once()
        call_args = mock_lookup.call_args
        assert call_args[0][2] == b"src/main.py"

    def test_get_file_at_commit_rejects_oaps_path(
        self,
        project_with_oaps: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_with_oaps)

        with pytest.raises(OapsRepositoryPathViolationError) as exc_info:
            repo.get_file_at_commit(Path(".oaps/config.toml"), "a" * 40)

        assert "Cannot access files in .oaps/" in str(exc_info.value)

    def test_get_file_at_commit_rejects_path_outside_repo(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        with pytest.raises(OapsRepositoryPathViolationError) as exc_info:
            repo.get_file_at_commit(Path("/some/other/path/file.txt"), "a" * 40)

        assert "outside repository" in str(exc_info.value)


class TestProjectRepositoryResolveAbbreviatedSha:
    def test_resolve_full_sha_returns_bytes(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)
        full_sha = "a" * 40

        result = repo._resolve_abbreviated_sha(full_sha)

        assert result == bytes.fromhex(full_sha)

    def test_resolve_abbreviated_sha_finds_match(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Set up mock object store to return one matching commit
        full_sha_bytes = bytes.fromhex("abcd" + "0" * 36)
        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha"
        mock_commit.parents = []

        mock_repo.object_store.__iter__ = MagicMock(return_value=iter([full_sha_bytes]))
        mock_repo.__getitem__.return_value = mock_commit

        result = repo._resolve_abbreviated_sha("abcd")

        assert result == full_sha_bytes

    def test_resolve_raises_for_too_short_sha(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        with pytest.raises(KeyError, match="SHA too short"):
            repo._resolve_abbreviated_sha("abc")  # Only 3 chars, minimum is 4

    def test_resolve_raises_for_not_found_sha(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Empty object store
        mock_repo.object_store.__iter__ = MagicMock(return_value=iter([]))

        with pytest.raises(KeyError, match="Commit not found"):
            repo._resolve_abbreviated_sha("abcd1234")

    def test_resolve_raises_for_ambiguous_sha(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        # Two matching commits
        sha1 = bytes.fromhex("abcd" + "1" * 36)
        sha2 = bytes.fromhex("abcd" + "2" * 36)

        mock_commit = MagicMock()
        mock_commit.tree = b"tree_sha"
        mock_commit.parents = []

        mock_repo.object_store.__iter__ = MagicMock(return_value=iter([sha1, sha2]))
        mock_repo.__getitem__.return_value = mock_commit

        with pytest.raises(KeyError, match="Ambiguous SHA prefix"):
            repo._resolve_abbreviated_sha("abcd")

    def test_resolve_raises_for_invalid_hex(
        self,
        project_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        repo = ProjectRepository(worktree_dir=project_dir)

        with pytest.raises(KeyError, match="Invalid SHA format"):
            repo._resolve_abbreviated_sha("z" * 40)  # Invalid hex characters
