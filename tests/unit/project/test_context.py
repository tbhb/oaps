"""Unit tests for project context module."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from oaps.project import (
    ProjectCommitInfo,
    ProjectContext,
    ProjectDiffStats,
    get_project_context,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a mock project directory with .git."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def mock_project_repo(mocker: MockerFixture) -> MagicMock:
    """Create a mock ProjectRepository."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)
    mocker.patch("oaps.project._context.ProjectRepository", return_value=mock)
    return mock


class TestProjectDiffStats:
    def test_is_frozen_dataclass(self) -> None:
        stats = ProjectDiffStats(
            total_additions=10,
            total_deletions=5,
            files_changed=3,
        )

        with pytest.raises(FrozenInstanceError):
            stats.total_additions = 20  # pyright: ignore[reportAttributeAccessIssue]

    def test_has_slots(self) -> None:
        assert hasattr(ProjectDiffStats, "__slots__")

    def test_fields_correctly_set(self) -> None:
        stats = ProjectDiffStats(
            total_additions=10,
            total_deletions=5,
            files_changed=3,
        )

        assert stats.total_additions == 10
        assert stats.total_deletions == 5
        assert stats.files_changed == 3


class TestProjectCommitInfo:
    def test_is_frozen_dataclass(self) -> None:
        commit = ProjectCommitInfo(
            sha="a" * 40,
            message="Test commit",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp="2024-01-15T10:30:00+00:00",
            files_changed=3,
            parent_shas=("b" * 40,),
        )

        with pytest.raises(FrozenInstanceError):
            commit.sha = "c" * 40  # pyright: ignore[reportAttributeAccessIssue]

    def test_has_slots(self) -> None:
        assert hasattr(ProjectCommitInfo, "__slots__")

    def test_timestamp_is_iso_string(self) -> None:
        commit = ProjectCommitInfo(
            sha="a" * 40,
            message="Test commit",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp="2024-01-15T10:30:00+00:00",
            files_changed=3,
            parent_shas=(),
        )

        # Verify it's a string that can be parsed as ISO format
        assert isinstance(commit.timestamp, str)
        parsed = datetime.fromisoformat(commit.timestamp)
        assert isinstance(parsed, datetime)

    def test_parent_shas_is_tuple(self) -> None:
        commit = ProjectCommitInfo(
            sha="a" * 40,
            message="Test commit",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp="2024-01-15T10:30:00+00:00",
            files_changed=3,
            parent_shas=("b" * 40, "c" * 40),
        )

        assert isinstance(commit.parent_shas, tuple)
        assert len(commit.parent_shas) == 2


class TestProjectContext:
    def test_is_frozen_dataclass(self) -> None:
        context = ProjectContext(
            has_changes=True,
            uncommitted_count=5,
            staged_count=2,
            modified_count=3,
            untracked_count=1,
            diff_stats=None,
            recent_commits=(),
        )

        with pytest.raises(FrozenInstanceError):
            context.has_changes = False  # pyright: ignore[reportAttributeAccessIssue]

    def test_has_slots(self) -> None:
        assert hasattr(ProjectContext, "__slots__")

    def test_all_fields_set_correctly(self) -> None:
        diff_stats = ProjectDiffStats(
            total_additions=10,
            total_deletions=5,
            files_changed=3,
        )
        commit = ProjectCommitInfo(
            sha="a" * 40,
            message="Test commit",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp="2024-01-15T10:30:00+00:00",
            files_changed=3,
            parent_shas=(),
        )

        context = ProjectContext(
            has_changes=True,
            uncommitted_count=5,
            staged_count=2,
            modified_count=3,
            untracked_count=1,
            diff_stats=diff_stats,
            recent_commits=(commit,),
        )

        assert context.has_changes is True
        assert context.uncommitted_count == 5
        assert context.staged_count == 2
        assert context.modified_count == 3
        assert context.untracked_count == 1
        assert context.diff_stats == diff_stats
        assert len(context.recent_commits) == 1

    def test_diff_stats_can_be_none(self) -> None:
        context = ProjectContext(
            has_changes=True,
            uncommitted_count=5,
            staged_count=2,
            modified_count=3,
            untracked_count=1,
            diff_stats=None,
            recent_commits=(),
        )

        assert context.diff_stats is None

    def test_recent_commits_is_tuple(self) -> None:
        context = ProjectContext(
            has_changes=False,
            uncommitted_count=0,
            staged_count=0,
            modified_count=0,
            untracked_count=0,
            diff_stats=None,
            recent_commits=(),
        )

        assert isinstance(context.recent_commits, tuple)


class TestGetProjectContext:
    def test_returns_none_for_non_git_directory(self, tmp_path: Path) -> None:
        result = get_project_context(cwd=tmp_path)

        assert result is None

    def test_returns_project_context_for_git_repo(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        # Setup mock status
        mock_status = MagicMock()
        mock_status.staged = frozenset([project_dir / "staged.txt"])
        mock_status.modified = frozenset([project_dir / "modified.txt"])
        mock_status.untracked = frozenset([project_dir / "untracked.txt"])
        mock_project_repo.get_status.return_value = mock_status

        # Setup mock log
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=project_dir)

        assert result is not None
        assert isinstance(result, ProjectContext)
        assert result.staged_count == 1
        assert result.modified_count == 1
        assert result.untracked_count == 1
        assert result.uncommitted_count == 2
        assert result.has_changes is True

    def test_calculates_uncommitted_count_correctly(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset([Path("a.txt"), Path("b.txt")])
        mock_status.modified = frozenset([Path("c.txt"), Path("d.txt"), Path("e.txt")])
        mock_status.untracked = frozenset([Path("f.txt")])
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=project_dir)

        assert result is not None
        assert result.staged_count == 2
        assert result.modified_count == 3
        assert result.uncommitted_count == 5  # staged + modified

    def test_has_changes_false_when_no_staged_or_modified(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset([Path("untracked.txt")])
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=project_dir)

        assert result is not None
        assert result.has_changes is False
        assert result.untracked_count == 1

    def test_include_diff_stats_false_returns_none_stats(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset([Path("a.txt")])
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=project_dir, include_diff_stats=False)

        assert result is not None
        assert result.diff_stats is None
        mock_project_repo.get_diff_stats.assert_not_called()

    def test_include_diff_stats_true_gets_combined_stats(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset([Path("a.txt")])
        mock_status.modified = frozenset([Path("b.txt")])
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        # Mock staged diff stats
        mock_staged_stats = MagicMock()
        mock_staged_stats.total_additions = 10
        mock_staged_stats.total_deletions = 5
        mock_staged_stats.files_changed = 1

        # Mock unstaged diff stats
        mock_unstaged_stats = MagicMock()
        mock_unstaged_stats.total_additions = 20
        mock_unstaged_stats.total_deletions = 8
        mock_unstaged_stats.files_changed = 2

        mock_project_repo.get_diff_stats.side_effect = [
            mock_staged_stats,
            mock_unstaged_stats,
        ]

        result = get_project_context(cwd=project_dir, include_diff_stats=True)

        assert result is not None
        assert result.diff_stats is not None
        assert result.diff_stats.total_additions == 30  # 10 + 20
        assert result.diff_stats.total_deletions == 13  # 5 + 8
        assert result.diff_stats.files_changed == 3  # 1 + 2

    def test_include_diff_stats_skipped_when_no_changes(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=project_dir, include_diff_stats=True)

        assert result is not None
        assert result.diff_stats is None
        mock_project_repo.get_diff_stats.assert_not_called()

    def test_recent_commits_count_parameter(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        get_project_context(cwd=project_dir, recent_commits_count=10)

        mock_project_repo.get_log.assert_called_once_with(n=10)

    def test_converts_commits_to_project_commit_info(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        from oaps.repository._models import CommitInfo

        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status

        # Create a real CommitInfo
        commit_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        commit = CommitInfo(
            sha="a" * 40,
            message="Test commit\n\nWith body",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp=commit_time,
            files_changed=3,
            parent_shas=("b" * 40,),
        )
        mock_project_repo.get_log.return_value = [commit]

        result = get_project_context(cwd=project_dir)

        assert result is not None
        assert len(result.recent_commits) == 1

        project_commit = result.recent_commits[0]
        assert isinstance(project_commit, ProjectCommitInfo)
        assert project_commit.sha == "a" * 40
        assert project_commit.message == "Test commit\n\nWith body"
        assert project_commit.author_name == "Test Author"
        assert project_commit.author_email == "test@example.com"
        assert project_commit.timestamp == commit_time.isoformat()
        assert project_commit.files_changed == 3
        assert project_commit.parent_shas == ("b" * 40,)

    def test_accepts_string_cwd(
        self, project_dir: Path, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        result = get_project_context(cwd=str(project_dir))

        assert result is not None

    def test_uses_cwd_when_none(
        self, mocker: MockerFixture, mock_project_repo: MagicMock
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = frozenset()
        mock_status.modified = frozenset()
        mock_status.untracked = frozenset()
        mock_project_repo.get_status.return_value = mock_status
        mock_project_repo.get_log.return_value = []

        # Mock Path.cwd to return a controlled path
        mock_cwd = Path("/mock/cwd")
        mocker.patch.object(Path, "cwd", return_value=mock_cwd)

        # This should not raise even though /mock/cwd doesn't exist
        # because ProjectRepository is mocked
        result = get_project_context(cwd=None)

        assert result is not None

    def test_returns_none_on_generic_exception(
        self, project_dir: Path, mocker: MockerFixture
    ) -> None:
        # Mock ProjectRepository to raise a generic exception
        mock_repo = MagicMock()
        mock_repo.__enter__.side_effect = RuntimeError("Something went wrong")
        mocker.patch("oaps.project._context.ProjectRepository", return_value=mock_repo)

        result = get_project_context(cwd=project_dir)

        assert result is None


class TestCombineDiffStats:
    def test_combines_staged_and_unstaged_stats(self) -> None:
        from oaps.project._context import _combine_diff_stats
        from oaps.repository._models import DiffStats, FileDiffStats

        staged = DiffStats(
            files=(FileDiffStats(path="a.txt", additions=5, deletions=3),),
            total_additions=5,
            total_deletions=3,
            files_changed=1,
        )
        unstaged = DiffStats(
            files=(FileDiffStats(path="b.txt", additions=10, deletions=2),),
            total_additions=10,
            total_deletions=2,
            files_changed=1,
        )

        result = _combine_diff_stats(staged, unstaged)

        assert isinstance(result, ProjectDiffStats)
        assert result.total_additions == 15
        assert result.total_deletions == 5
        assert result.files_changed == 2


class TestConvertCommitInfo:
    def test_converts_repository_commit_info(self) -> None:
        from oaps.project._context import _convert_commit_info
        from oaps.repository._models import CommitInfo

        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        repo_commit = CommitInfo(
            sha="abc123" + "0" * 34,
            message="Test commit message",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp=timestamp,
            files_changed=5,
            parent_shas=("def456" + "0" * 34,),
        )

        result = _convert_commit_info(repo_commit)

        assert isinstance(result, ProjectCommitInfo)
        assert result.sha == "abc123" + "0" * 34
        assert result.message == "Test commit message"
        assert result.author_name == "Test Author"
        assert result.author_email == "test@example.com"
        assert result.timestamp == timestamp.isoformat()
        assert result.files_changed == 5
        assert result.parent_shas == ("def456" + "0" * 34,)

    def test_converts_datetime_to_iso_string(self) -> None:
        from oaps.project._context import _convert_commit_info
        from oaps.repository._models import CommitInfo

        # Use a timezone-aware datetime with UTC
        timestamp = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)

        repo_commit = CommitInfo(
            sha="a" * 40,
            message="Test",
            author_name="Author",
            author_email="author@test.com",
            timestamp=timestamp,
            files_changed=1,
            parent_shas=(),
        )

        result = _convert_commit_info(repo_commit)

        # Verify the timestamp is an ISO 8601 string
        assert isinstance(result.timestamp, str)
        assert result.timestamp == "2024-06-15T14:30:45+00:00"

        # Verify it can be parsed back
        parsed = datetime.fromisoformat(result.timestamp)
        assert parsed == timestamp


class TestPublicExports:
    def test_exports_available_from_package(self) -> None:
        from oaps.project import (
            ProjectCommitInfo,
            ProjectContext,
            ProjectDiffStats,
            get_project_context,
        )

        assert ProjectDiffStats is not None
        assert ProjectCommitInfo is not None
        assert ProjectContext is not None
        assert get_project_context is not None
