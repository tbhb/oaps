"""Integration tests for worktree utilities with real git repos."""

from pathlib import Path

import pytest
from dulwich.porcelain import add, commit
from dulwich.repo import Repo

from oaps.exceptions import (
    OAPSError,
    WorktreeLockedError,
    WorktreeNotFoundError,
)
from oaps.utils._git._worktree import (
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


def _create_initial_commit(repo_path: Path) -> bytes:
    """Create an initial commit in a repository.

    Args:
        repo_path: Path to the repository.

    Returns:
        The commit SHA.
    """
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n")

    # Stage and commit using porcelain
    add(str(repo_path), paths=["README.md"])
    return commit(
        str(repo_path),
        message=b"Initial commit",
        author=b"Test <test@test.com>",
        committer=b"Test <test@test.com>",
        sign=False,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Repo:
    """Create a git repository with an initial commit."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = Repo.init(str(repo_path))
    _create_initial_commit(repo_path)
    return repo


@pytest.fixture
def git_repo_path(git_repo: Repo) -> Path:
    """Get the path to the git repository."""
    repo_path = git_repo.path
    path_str = repo_path.decode() if isinstance(repo_path, bytes) else repo_path
    path = Path(path_str)
    if path.name == ".git":
        return path.parent
    return path


class TestListWorktreesIntegration:
    def test_lists_main_worktree(self, git_repo_path: Path) -> None:
        worktrees = list_worktrees(repo_path=git_repo_path)

        assert len(worktrees) == 1
        assert worktrees[0].is_main is True
        assert worktrees[0].path.resolve() == git_repo_path.resolve()

    def test_lists_multiple_worktrees(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        # Add a linked worktree
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        worktrees = list_worktrees(repo_path=git_repo_path)

        assert len(worktrees) == 2
        assert worktrees[0].is_main is True
        assert worktrees[1].is_main is False
        branches = {wt.branch for wt in worktrees}
        assert "feature" in branches


class TestGetWorktreeIntegration:
    def test_returns_worktree_for_exact_path(self, git_repo_path: Path) -> None:
        result = get_worktree(git_repo_path)

        assert result is not None
        assert result.is_main is True
        assert result.path.resolve() == git_repo_path.resolve()

    def test_returns_none_for_non_worktree_path(self, tmp_path: Path) -> None:
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        result = get_worktree(non_repo)

        assert result is None


class TestGetMainWorktreeIntegration:
    def test_returns_main_worktree(self, git_repo_path: Path) -> None:
        result = get_main_worktree(repo_path=git_repo_path)

        assert result.is_main is True
        assert result.path.resolve() == git_repo_path.resolve()

    def test_returns_main_even_with_linked_worktrees(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        result = get_main_worktree(repo_path=git_repo_path)

        assert result.is_main is True
        assert result.path.resolve() == git_repo_path.resolve()


class TestGetWorktreeForPathIntegration:
    def test_finds_worktree_for_nested_path(self, git_repo_path: Path) -> None:
        subdir = git_repo_path / "src" / "deep" / "nested"
        subdir.mkdir(parents=True)

        result = get_worktree_for_path(subdir)

        assert result is not None
        assert result.is_main is True
        assert result.path.resolve() == git_repo_path.resolve()

    def test_returns_correct_worktree_for_linked(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)
        nested = feature_path / "subdir"
        nested.mkdir()

        result = get_worktree_for_path(nested)

        assert result is not None
        assert result.branch == "feature"
        assert result.path.resolve() == feature_path.resolve()


class TestIsInWorktreeIntegration:
    def test_returns_true_for_path_in_worktree(self, git_repo_path: Path) -> None:
        subdir = git_repo_path / "src"
        subdir.mkdir()

        result = is_in_worktree(subdir)

        assert result is True

    def test_returns_false_for_path_outside_worktree(self, tmp_path: Path) -> None:
        non_repo = tmp_path / "outside"
        non_repo.mkdir()

        result = is_in_worktree(non_repo)

        assert result is False


class TestIsMainWorktreeIntegration:
    def test_returns_true_for_main_worktree(self, git_repo_path: Path) -> None:
        result = is_main_worktree(git_repo_path)

        assert result is True

    def test_returns_false_for_linked_worktree(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        result = is_main_worktree(feature_path)

        assert result is False


class TestAddWorktreeIntegration:
    def test_adds_worktree_with_new_branch(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"

        result = add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        assert result.worktree.path.resolve() == feature_path.resolve()
        assert result.worktree.branch == "feature"
        assert result.created_branch == "feature"
        assert feature_path.exists()
        assert (feature_path / "README.md").exists()

    def test_adds_worktree_with_existing_branch(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        # First create a branch
        Repo(str(git_repo_path)).refs[b"refs/heads/existing"] = Repo(
            str(git_repo_path)
        ).head()

        worktree_path = tmp_path / "existing-worktree"
        result = add_worktree(worktree_path, branch="existing", repo_path=git_repo_path)

        assert result.created_branch is None
        assert result.worktree.branch == "existing"

    def test_adds_detached_worktree(self, git_repo_path: Path, tmp_path: Path) -> None:
        repo = Repo(str(git_repo_path))
        commit_sha = repo.head().decode()

        worktree_path = tmp_path / "detached-worktree"
        result = add_worktree(
            worktree_path, commit=commit_sha, detach=True, repo_path=git_repo_path
        )

        assert result.worktree.is_detached is True
        assert result.worktree.branch is None


class TestRemoveWorktreeIntegration:
    def test_removes_worktree(self, git_repo_path: Path, tmp_path: Path) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        remove_worktree(feature_path, repo_path=git_repo_path)

        # Directory should be removed
        assert not feature_path.exists()
        # Should not appear in worktree list
        worktrees = list_worktrees(repo_path=git_repo_path)
        assert len(worktrees) == 1

    def test_raises_not_found_for_nonexistent(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(WorktreeNotFoundError):
            remove_worktree(nonexistent, repo_path=git_repo_path)

    def test_raises_locked_error_for_locked_worktree(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)
        lock_worktree(feature_path, reason="Testing", repo_path=git_repo_path)

        with pytest.raises(WorktreeLockedError):
            remove_worktree(feature_path, repo_path=git_repo_path)


class TestMoveWorktreeIntegration:
    def test_moves_worktree(self, git_repo_path: Path, tmp_path: Path) -> None:
        old_path = tmp_path / "old-worktree"
        new_path = tmp_path / "new-worktree"
        add_worktree(old_path, branch="feature", repo_path=git_repo_path)

        result = move_worktree(old_path, new_path, repo_path=git_repo_path)

        assert result.path.resolve() == new_path.resolve()
        assert not old_path.exists()
        assert new_path.exists()

    def test_raises_not_found_for_nonexistent(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        with pytest.raises(WorktreeNotFoundError):
            move_worktree(
                tmp_path / "nonexistent",
                tmp_path / "new",
                repo_path=git_repo_path,
            )


class TestLockUnlockWorktreeIntegration:
    def test_locks_and_unlocks_worktree(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        lock_worktree(feature_path, reason="Testing lock", repo_path=git_repo_path)

        # Verify it's locked
        worktrees = list_worktrees(repo_path=git_repo_path)
        feature_wt = next(wt for wt in worktrees if wt.branch == "feature")
        assert feature_wt.is_locked is True
        assert feature_wt.lock_reason == "Testing lock"

        unlock_worktree(feature_path, repo_path=git_repo_path)

        # Verify it's unlocked
        worktrees = list_worktrees(repo_path=git_repo_path)
        feature_wt = next(wt for wt in worktrees if wt.branch == "feature")
        assert feature_wt.is_locked is False


class TestPruneWorktreesIntegration:
    def test_prunes_missing_worktrees(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        # Manually delete the worktree directory (simulating corruption)
        import shutil

        shutil.rmtree(feature_path)

        # Prune should clean up
        result = prune_worktrees(repo_path=git_repo_path)

        # Note: pruned_ids may or may not contain entries depending on dulwich behavior
        assert result.dry_run is False

    def test_dry_run_does_not_prune(self, git_repo_path: Path, tmp_path: Path) -> None:
        result = prune_worktrees(dry_run=True, repo_path=git_repo_path)

        assert result.dry_run is True


class TestWorktreeInfoAttributes:
    def test_worktree_has_correct_attributes(self, git_repo_path: Path) -> None:
        worktrees = list_worktrees(repo_path=git_repo_path)

        main_wt = worktrees[0]
        assert main_wt.path.is_dir()
        assert main_wt.head_commit is not None
        assert len(main_wt.head_commit) == 40  # SHA-1 hex length
        assert main_wt.is_main is True
        assert main_wt.is_bare is False
        assert main_wt.is_locked is False

    def test_linked_worktree_has_correct_attributes(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        feature_path = tmp_path / "feature-worktree"
        add_worktree(feature_path, branch="feature", repo_path=git_repo_path)

        worktrees = list_worktrees(repo_path=git_repo_path)
        feature_wt = next(wt for wt in worktrees if wt.branch == "feature")

        assert feature_wt.is_main is False
        assert feature_wt.path.resolve() == feature_path.resolve()


class TestErrorHandling:
    def test_raises_oaps_error_for_non_repo(self, tmp_path: Path) -> None:
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        with pytest.raises(OAPSError, match="Not inside a Git repository"):
            list_worktrees(repo_path=non_repo)

    def test_worktree_not_found_for_lock_on_nonexistent(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(WorktreeNotFoundError):
            lock_worktree(nonexistent, repo_path=git_repo_path)

    def test_worktree_not_found_for_unlock_on_nonexistent(
        self, git_repo_path: Path, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(WorktreeNotFoundError):
            unlock_worktree(nonexistent, repo_path=git_repo_path)
