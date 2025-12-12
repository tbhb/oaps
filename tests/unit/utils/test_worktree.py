"""Unit tests for worktree utilities with mocked dulwich."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from oaps.exceptions import (
    OAPSError,
    WorktreeDirtyError,
    WorktreeError,
    WorktreeLockedError,
    WorktreeNotFoundError,
)
from oaps.utils._git._common import resolve_repo, strip_refs_heads
from oaps.utils._git._worktree import (
    WorktreeAddResult,
    WorktreeInfo,
    WorktreePruneResult,
    _convert_worktree_info,
    add_worktree,
    get_main_worktree,
    get_worktree,
    get_worktree_for_path,
    is_in_worktree,
    is_main_worktree,
    list_worktrees,
    lock_worktree,
    move_worktree,
    prune_worktrees,
    remove_worktree,
    unlock_worktree,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestStripRefsHeads:
    def test_strips_prefix_from_bytes(self) -> None:
        result = strip_refs_heads(b"refs/heads/main")
        assert result == "main"

    def test_strips_prefix_from_str(self) -> None:
        result = strip_refs_heads("refs/heads/feature/test")
        assert result == "feature/test"

    def test_returns_as_is_without_prefix(self) -> None:
        result = strip_refs_heads("main")
        assert result == "main"

    def test_returns_none_for_none_input(self) -> None:
        result = strip_refs_heads(None)
        assert result is None

    def test_handles_bytes_without_prefix(self) -> None:
        result = strip_refs_heads(b"main")
        assert result == "main"


class TestConvertWorktreeInfo:
    def test_converts_basic_worktree_info(self) -> None:
        dulwich_info = MagicMock()
        dulwich_info.path = "/path/to/worktree"
        dulwich_info.head = b"abc123def456"
        dulwich_info.branch = b"refs/heads/main"
        dulwich_info.bare = False
        dulwich_info.detached = False
        dulwich_info.locked = False
        dulwich_info.prunable = False
        dulwich_info.lock_reason = None

        result = _convert_worktree_info(dulwich_info, is_main=True)

        assert isinstance(result, WorktreeInfo)
        assert result.path == Path("/path/to/worktree")
        assert result.head_commit == "abc123def456"
        assert result.branch == "main"
        assert result.is_main is True
        assert result.is_bare is False
        assert result.is_detached is False
        assert result.is_locked is False
        assert result.is_prunable is False
        assert result.lock_reason is None

    def test_converts_locked_worktree(self) -> None:
        dulwich_info = MagicMock()
        dulwich_info.path = "/path/to/locked"
        dulwich_info.head = b"abc123"
        dulwich_info.branch = b"refs/heads/feature"
        dulwich_info.bare = False
        dulwich_info.detached = False
        dulwich_info.locked = True
        dulwich_info.prunable = False
        dulwich_info.lock_reason = "Work in progress"

        result = _convert_worktree_info(dulwich_info, is_main=False)

        assert result.is_locked is True
        assert result.lock_reason == "Work in progress"

    def test_converts_detached_head(self) -> None:
        dulwich_info = MagicMock()
        dulwich_info.path = "/path/to/detached"
        dulwich_info.head = b"abc123"
        dulwich_info.branch = None
        dulwich_info.bare = False
        dulwich_info.detached = True
        dulwich_info.locked = False
        dulwich_info.prunable = True
        dulwich_info.lock_reason = None

        result = _convert_worktree_info(dulwich_info, is_main=False)

        assert result.branch is None
        assert result.is_detached is True
        assert result.is_prunable is True

    def test_converts_bare_repository(self) -> None:
        dulwich_info = MagicMock()
        dulwich_info.path = "/path/to/bare.git"
        dulwich_info.head = None
        dulwich_info.branch = None
        dulwich_info.bare = True
        dulwich_info.detached = False
        dulwich_info.locked = False
        dulwich_info.prunable = False
        dulwich_info.lock_reason = None

        result = _convert_worktree_info(dulwich_info, is_main=True)

        assert result.head_commit is None
        assert result.is_bare is True

    def test_handles_none_head_commit(self) -> None:
        dulwich_info = MagicMock()
        dulwich_info.path = "/path/to/worktree"
        dulwich_info.head = None
        dulwich_info.branch = b"refs/heads/main"
        dulwich_info.bare = False
        dulwich_info.detached = False
        dulwich_info.locked = False
        dulwich_info.prunable = False
        dulwich_info.lock_reason = None

        result = _convert_worktree_info(dulwich_info)

        assert result.head_commit is None


class TestResolveRepo:
    def test_discovers_repo_when_path_none(self, mocker: MockerFixture) -> None:
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._common.Repo.discover", return_value=mock_repo)

        result = resolve_repo(None)

        assert result is mock_repo

    def test_opens_repo_at_path(self, mocker: MockerFixture) -> None:
        mock_repo = MagicMock()
        mock_repo_class = mocker.patch(
            "oaps.utils._git._common.Repo", return_value=mock_repo
        )

        result = resolve_repo(Path("/some/path"))

        mock_repo_class.assert_called_once_with("/some/path")
        assert result is mock_repo

    def test_raises_oaps_error_when_not_git_repo(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._common.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        with pytest.raises(OAPSError, match="Not inside a Git repository"):
            resolve_repo(None)


class TestListWorktrees:
    def test_lists_all_worktrees(self, mocker: MockerFixture) -> None:
        mock_wt1 = MagicMock()
        mock_wt1.path = "/path/main"
        mock_wt1.head = b"abc123"
        mock_wt1.branch = b"refs/heads/main"
        mock_wt1.bare = False
        mock_wt1.detached = False
        mock_wt1.locked = False
        mock_wt1.prunable = False
        mock_wt1.lock_reason = None

        mock_wt2 = MagicMock()
        mock_wt2.path = "/path/feature"
        mock_wt2.head = b"def456"
        mock_wt2.branch = b"refs/heads/feature"
        mock_wt2.bare = False
        mock_wt2.detached = False
        mock_wt2.locked = False
        mock_wt2.prunable = False
        mock_wt2.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt1, mock_wt2]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        result = list_worktrees()

        assert len(result) == 2
        assert result[0].is_main is True
        assert result[0].branch == "main"
        assert result[1].is_main is False
        assert result[1].branch == "feature"

    def test_passes_repo_path_to_resolve(self, mocker: MockerFixture) -> None:
        mock_resolve = mocker.patch("oaps.utils._git._worktree.resolve_repo")
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )

        list_worktrees(repo_path=Path("/custom/path"))

        mock_resolve.assert_called_once_with(Path("/custom/path"))


class TestGetWorktree:
    def test_returns_worktree_info_when_found(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/worktree"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/main"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)

        mocker.patch.object(Path, "resolve", return_value=Path("/path/to/worktree"))

        result = get_worktree(Path("/path/to/worktree"))

        assert result is not None
        assert result.branch == "main"

    def test_returns_none_when_not_git_repo(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        result = get_worktree(Path("/not/a/repo"))

        assert result is None

    def test_returns_none_when_path_not_worktree(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/other/path"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/main"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)

        result = get_worktree(Path("/different/path"))

        assert result is None

    def test_uses_cwd_when_path_none(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )
        mock_cwd = mocker.patch.object(Path, "cwd", return_value=Path("/current/dir"))

        get_worktree(None)

        mock_cwd.assert_called_once()


class TestGetMainWorktree:
    def test_returns_first_worktree(self, mocker: MockerFixture) -> None:
        mock_wt1 = MagicMock()
        mock_wt1.path = "/path/main"
        mock_wt1.head = b"abc123"
        mock_wt1.branch = b"refs/heads/main"
        mock_wt1.bare = False
        mock_wt1.detached = False
        mock_wt1.locked = False
        mock_wt1.prunable = False
        mock_wt1.lock_reason = None

        mock_wt2 = MagicMock()
        mock_wt2.path = "/path/feature"
        mock_wt2.head = b"def456"
        mock_wt2.branch = b"refs/heads/feature"
        mock_wt2.bare = False
        mock_wt2.detached = False
        mock_wt2.locked = False
        mock_wt2.prunable = False
        mock_wt2.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt1, mock_wt2]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        result = get_main_worktree()

        assert result.is_main is True
        assert result.branch == "main"

    def test_raises_worktree_error_when_no_worktrees(
        self, mocker: MockerFixture
    ) -> None:
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeError, match="No worktrees found"):
            get_main_worktree()


class TestGetWorktreeForPath:
    def test_returns_worktree_containing_path(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/worktree"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/main"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        result = get_worktree_for_path(Path("/path/to/worktree/subdir/file.txt"))

        assert result is not None
        assert result.branch == "main"

    def test_returns_none_when_not_in_worktree(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        result = get_worktree_for_path(Path("/outside/git"))

        assert result is None


class TestIsInWorktree:
    def test_returns_true_when_in_worktree(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/worktree"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/main"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        result = is_in_worktree(Path("/path/to/worktree/subdir"))

        assert result is True

    def test_returns_false_when_outside_worktree(self, mocker: MockerFixture) -> None:
        from dulwich.errors import NotGitRepository

        mocker.patch(
            "oaps.utils._git._worktree.Repo.discover",
            side_effect=NotGitRepository("not a repo"),
        )

        result = is_in_worktree(Path("/outside"))

        assert result is False


class TestIsMainWorktree:
    def test_returns_true_when_in_main_worktree(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/main"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/main"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        result = is_main_worktree(Path("/path/to/main/subdir"))

        assert result is True

    def test_returns_false_when_in_linked_worktree(self, mocker: MockerFixture) -> None:
        mock_wt1 = MagicMock()
        mock_wt1.path = "/path/main"
        mock_wt1.head = b"abc123"
        mock_wt1.branch = b"refs/heads/main"
        mock_wt1.bare = False
        mock_wt1.detached = False
        mock_wt1.locked = False
        mock_wt1.prunable = False
        mock_wt1.lock_reason = None

        mock_wt2 = MagicMock()
        mock_wt2.path = "/path/feature"
        mock_wt2.head = b"def456"
        mock_wt2.branch = b"refs/heads/feature"
        mock_wt2.bare = False
        mock_wt2.detached = False
        mock_wt2.locked = False
        mock_wt2.prunable = False
        mock_wt2.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt1, mock_wt2]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mocker.patch("oaps.utils._git._worktree.Repo.discover", return_value=mock_repo)
        mocker.patch("oaps.utils._git._worktree.get_main_repo", return_value=mock_repo)

        result = is_main_worktree(Path("/path/feature/file.txt"))

        assert result is False


class TestAddWorktree:
    def test_adds_worktree_successfully(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/new"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/new-branch"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mock_repo.refs = {}
        mocker.patch("oaps.utils._git._worktree.resolve_repo", return_value=mock_repo)

        result = add_worktree(Path("/path/to/new"), branch="new-branch")

        assert isinstance(result, WorktreeAddResult)
        assert result.worktree.branch == "new-branch"
        assert result.created_branch == "new-branch"
        mock_container.add.assert_called_once()

    def test_does_not_create_branch_when_exists(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/new"
        mock_wt.head = b"abc123"
        mock_wt.branch = b"refs/heads/existing"
        mock_wt.bare = False
        mock_wt.detached = False
        mock_wt.locked = False
        mock_wt.prunable = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mock_repo.refs = {b"refs/heads/existing": b"abc123"}
        mocker.patch("oaps.utils._git._worktree.resolve_repo", return_value=mock_repo)

        result = add_worktree(Path("/path/to/new"), branch="existing")

        assert result.created_branch is None

    def test_raises_worktree_error_on_failure(self, mocker: MockerFixture) -> None:
        mock_container = MagicMock()
        mock_container.add.side_effect = RuntimeError("Failed to create")
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mock_repo = MagicMock()
        mock_repo.refs = {}
        mocker.patch("oaps.utils._git._worktree.resolve_repo", return_value=mock_repo)

        with pytest.raises(WorktreeError, match="Failed to add worktree"):
            add_worktree(Path("/path/to/new"))


class TestRemoveWorktree:
    def test_removes_worktree_successfully(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/remove"
        mock_wt.locked = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        remove_worktree(Path("/path/to/remove"))

        mock_container.remove.assert_called_once_with("/path/to/remove", force=False)

    def test_raises_not_found_when_worktree_missing(
        self, mocker: MockerFixture
    ) -> None:
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeNotFoundError, match="No worktree found"):
            remove_worktree(Path("/nonexistent"))

    def test_raises_locked_error_when_locked(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/locked"
        mock_wt.locked = True
        mock_wt.lock_reason = "Work in progress"

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeLockedError, match=r"is locked.*Work in progress"):
            remove_worktree(Path("/path/to/locked"))

    def test_force_removes_locked_worktree(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/locked"
        mock_wt.locked = True
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        remove_worktree(Path("/path/to/locked"), force=True)

        mock_container.remove.assert_called_once_with("/path/to/locked", force=True)

    def test_raises_dirty_error_on_uncommitted_changes(
        self, mocker: MockerFixture
    ) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/dirty"
        mock_wt.locked = False
        mock_wt.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mock_container.remove.side_effect = RuntimeError("uncommitted changes exist")
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeDirtyError, match="uncommitted changes"):
            remove_worktree(Path("/path/to/dirty"))


class TestMoveWorktree:
    def test_moves_worktree_successfully(self, mocker: MockerFixture) -> None:
        mock_wt_old = MagicMock()
        mock_wt_old.path = "/old/path"
        mock_wt_old.locked = False
        mock_wt_old.lock_reason = None

        mock_wt_new = MagicMock()
        mock_wt_new.path = "/new/path"
        mock_wt_new.head = b"abc123"
        mock_wt_new.branch = b"refs/heads/main"
        mock_wt_new.bare = False
        mock_wt_new.detached = False
        mock_wt_new.locked = False
        mock_wt_new.prunable = False
        mock_wt_new.lock_reason = None

        mock_container = MagicMock()
        mock_container.list.side_effect = [[mock_wt_old], [mock_wt_new]]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        result = move_worktree(Path("/old/path"), Path("/new/path"))

        assert result.path == Path("/new/path")
        mock_container.move.assert_called_once()

    def test_raises_not_found_when_worktree_missing(
        self, mocker: MockerFixture
    ) -> None:
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeNotFoundError):
            move_worktree(Path("/nonexistent"), Path("/new"))

    def test_raises_locked_error_when_locked(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/locked/path"
        mock_wt.locked = True
        mock_wt.lock_reason = "Locked"

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeLockedError):
            move_worktree(Path("/locked/path"), Path("/new/path"))


class TestLockWorktree:
    def test_locks_worktree_successfully(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/worktree"

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        lock_worktree(Path("/path/to/worktree"), reason="Testing")

        mock_container.lock.assert_called_once_with(
            "/path/to/worktree", reason="Testing"
        )

    def test_raises_not_found_when_worktree_missing(
        self, mocker: MockerFixture
    ) -> None:
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeNotFoundError):
            lock_worktree(Path("/nonexistent"))


class TestUnlockWorktree:
    def test_unlocks_worktree_successfully(self, mocker: MockerFixture) -> None:
        mock_wt = MagicMock()
        mock_wt.path = "/path/to/worktree"

        mock_container = MagicMock()
        mock_container.list.return_value = [mock_wt]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        unlock_worktree(Path("/path/to/worktree"))

        mock_container.unlock.assert_called_once_with("/path/to/worktree")

    def test_raises_not_found_when_worktree_missing(
        self, mocker: MockerFixture
    ) -> None:
        mock_container = MagicMock()
        mock_container.list.return_value = []
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeNotFoundError):
            unlock_worktree(Path("/nonexistent"))


class TestPruneWorktrees:
    def test_prunes_worktrees_successfully(self, mocker: MockerFixture) -> None:
        mock_container = MagicMock()
        mock_container.prune.return_value = ["worktree1", "worktree2"]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        result = prune_worktrees()

        assert isinstance(result, WorktreePruneResult)
        assert result.pruned_ids == ("worktree1", "worktree2")
        assert result.dry_run is False

    def test_prunes_with_dry_run(self, mocker: MockerFixture) -> None:
        mock_container = MagicMock()
        mock_container.prune.return_value = ["worktree1"]
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        result = prune_worktrees(dry_run=True)

        assert result.dry_run is True
        mock_container.prune.assert_called_once_with(dry_run=True)

    def test_raises_error_on_failure(self, mocker: MockerFixture) -> None:
        mock_container = MagicMock()
        mock_container.prune.side_effect = RuntimeError("Prune failed")
        mocker.patch(
            "oaps.utils._git._worktree.WorkTreeContainer", return_value=mock_container
        )
        mocker.patch("oaps.utils._git._worktree.resolve_repo")

        with pytest.raises(WorktreeError, match="Failed to prune worktrees"):
            prune_worktrees()
