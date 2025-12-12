# pyright: reportAny=false
"""Unit tests for worktree repository factory functions."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from oaps.exceptions import WorktreeNotFoundError
from oaps.repository import OapsRepository, ProjectRepository
from oaps.utils._git._worktree import (
    get_oaps_repository_for_worktree,
    get_project_repository_for_worktree,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _create_mock_worktree(path: Path = Path("/path/to/worktree")) -> MagicMock:
    """Create a mock WorkTree object with standard attributes."""
    mock_wt = MagicMock()
    mock_wt.path = path
    mock_wt.head = b"abc123"
    mock_wt.branch = b"refs/heads/main"
    mock_wt.bare = False
    mock_wt.detached = False
    mock_wt.locked = False
    mock_wt.prunable = False
    mock_wt.lock_reason = None
    return mock_wt


class TestGetProjectRepositoryForWorktree:
    def test_returns_project_repository_for_valid_worktree(
        self, mocker: MockerFixture
    ) -> None:
        mock_wt = _create_mock_worktree(Path("/path/to/worktree"))

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        mock_project_repo = MagicMock(spec=ProjectRepository)
        mock_project_repo_class = mocker.patch(
            "oaps.repository.ProjectRepository",
            return_value=mock_project_repo,
        )

        result = get_project_repository_for_worktree(
            Path("/path/to/worktree/subdir/file.txt")
        )

        assert result is mock_project_repo
        mock_project_repo_class.assert_called_once_with(
            worktree_dir=Path("/path/to/worktree")
        )

    def test_uses_cwd_when_path_is_none(self, mocker: MockerFixture) -> None:
        mock_wt = _create_mock_worktree(Path("/current/dir"))

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        mocker.patch.object(Path, "cwd", return_value=Path("/current/dir"))

        mock_project_repo = MagicMock(spec=ProjectRepository)
        mocker.patch(
            "oaps.repository.ProjectRepository",
            return_value=mock_project_repo,
        )

        result = get_project_repository_for_worktree(None)

        assert result is mock_project_repo

    def test_raises_worktree_not_found_when_no_worktree(
        self, mocker: MockerFixture
    ) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        with pytest.raises(WorktreeNotFoundError, match="No worktree found"):
            get_project_repository_for_worktree(Path("/not/a/worktree"))


class TestGetOapsRepositoryForWorktree:
    def test_returns_oaps_repository_for_valid_worktree(
        self, mocker: MockerFixture
    ) -> None:
        mock_wt = _create_mock_worktree(Path("/path/to/worktree"))

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        mock_oaps_repo = MagicMock(spec=OapsRepository)
        mock_oaps_repo_class = mocker.patch(
            "oaps.repository.OapsRepository",
            return_value=mock_oaps_repo,
        )

        result = get_oaps_repository_for_worktree(
            Path("/path/to/worktree/subdir/file.txt")
        )

        assert result is mock_oaps_repo
        # OapsRepository expects working_dir to be the parent of .oaps/
        mock_oaps_repo_class.assert_called_once_with(
            working_dir=Path("/path/to/worktree")
        )

    def test_uses_cwd_when_path_is_none(self, mocker: MockerFixture) -> None:
        mock_wt = _create_mock_worktree(Path("/current/dir"))

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        mocker.patch.object(Path, "cwd", return_value=Path("/current/dir"))

        mock_oaps_repo = MagicMock(spec=OapsRepository)
        mocker.patch(
            "oaps.repository.OapsRepository",
            return_value=mock_oaps_repo,
        )

        result = get_oaps_repository_for_worktree(None)

        assert result is mock_oaps_repo

    def test_raises_worktree_not_found_when_no_worktree(
        self, mocker: MockerFixture
    ) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        with pytest.raises(WorktreeNotFoundError, match="No worktree found"):
            get_oaps_repository_for_worktree(Path("/not/a/worktree"))

    def test_resolves_symlinked_oaps_directory(self, mocker: MockerFixture) -> None:
        mock_wt = _create_mock_worktree(Path("/path/to/worktree"))

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        # Simulate symlink resolution: .oaps symlink points to /shared/oaps
        # So (worktree.path / ".oaps").resolve() returns /shared/oaps
        # And .parent is /shared
        mock_oaps_path = MagicMock(spec=Path)
        mock_oaps_path.resolve.return_value = Path("/shared/oaps")
        mocker.patch.object(Path, "__truediv__", return_value=mock_oaps_path)

        mock_oaps_repo = MagicMock(spec=OapsRepository)
        mock_oaps_repo_class = mocker.patch(
            "oaps.repository.OapsRepository",
            return_value=mock_oaps_repo,
        )

        result = get_oaps_repository_for_worktree(Path("/path/to/worktree"))

        assert result is mock_oaps_repo
        # The resolved path's parent (/shared) should be passed as working_dir
        mock_oaps_repo_class.assert_called_once_with(working_dir=Path("/shared"))
