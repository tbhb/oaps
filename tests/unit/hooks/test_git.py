"""Tests for git context collection."""

from pathlib import Path
from unittest.mock import MagicMock

from oaps.utils import GitContext, get_git_context
from oaps.utils._git._common import (
    decode_bytes,
    discover_repo,
    get_main_worktree_dir,
    get_worktree_dir,
)
from oaps.utils._git._status import (
    _get_current_branch,
    _get_head_commit,
    _get_modified_files,
    _get_staged_files,
    _get_untracked_files,
    _is_detached,
    _is_dirty,
)


class TestDecodeBytes:
    def test_decode_bytes_from_bytes(self) -> None:
        result = decode_bytes(b"test")
        assert result == "test"

    def test_decode_bytes_from_str(self) -> None:
        result = decode_bytes("test")
        assert result == "test"

    def test_decode_bytes_unicode(self) -> None:
        result = decode_bytes(b"\xc3\xa9")  # UTF-8 encoded 'e'
        assert result == "\xe9"


class TestDiscoverRepo:
    def test_discover_repo_in_git_directory(self, oaps_project: MagicMock) -> None:
        # oaps_project fixture creates a git repo
        repo = discover_repo(oaps_project.root)
        assert repo is not None

    def test_discover_repo_not_git_directory(self, tmp_path: Path) -> None:
        repo = discover_repo(tmp_path)
        assert repo is None

    def test_discover_repo_none_cwd(self) -> None:
        # This test relies on the current directory
        # If we're in a git repo, it should find it
        repo = discover_repo(None)
        # We're running from inside the oaps repo, so should find it
        assert repo is not None


class TestGetWorktreeDir:
    def test_get_worktree_dir_from_dotgit(self, oaps_project: MagicMock) -> None:
        from dulwich.repo import Repo

        repo = Repo(str(oaps_project.root))
        worktree_dir = get_worktree_dir(repo)
        assert worktree_dir == oaps_project.root

    def test_get_worktree_dir_handles_bytes_path(self, tmp_path: Path) -> None:
        # Use a mock to test bytes path handling
        repo = MagicMock()
        test_repo_path = tmp_path / "test_repo"
        repo.path = str(test_repo_path / ".git").encode()
        worktree_dir = get_worktree_dir(repo)
        assert worktree_dir == test_repo_path


class TestGetMainWorktreeDir:
    def test_get_main_worktree_dir(self, oaps_project: MagicMock) -> None:
        from dulwich.repo import Repo

        repo = Repo(str(oaps_project.root))
        main_dir = get_main_worktree_dir(repo)
        assert main_dir == oaps_project.root


class TestGetStagedFiles:
    def test_get_staged_files_empty(self) -> None:
        status = MagicMock()
        status.staged = {"add": [], "delete": [], "modify": []}
        result = _get_staged_files(status)
        assert result == frozenset()

    def test_get_staged_files_with_added_files(self) -> None:
        status = MagicMock()
        status.staged = {
            "add": [b"new_file.py", b"another.py"],
            "delete": [],
            "modify": [],
        }
        result = _get_staged_files(status)
        assert result == frozenset({"new_file.py", "another.py"})

    def test_get_staged_files_with_all_types(self) -> None:
        status = MagicMock()
        status.staged = {
            "add": [b"new.py"],
            "delete": [b"old.py"],
            "modify": [b"changed.py"],
        }
        result = _get_staged_files(status)
        assert result == frozenset({"new.py", "old.py", "changed.py"})


class TestGetModifiedFiles:
    def test_get_modified_files_empty(self) -> None:
        status = MagicMock()
        status.unstaged = []
        result = _get_modified_files(status)
        assert result == frozenset()

    def test_get_modified_files_with_files(self) -> None:
        status = MagicMock()
        status.unstaged = [b"modified.py", b"another.py"]
        result = _get_modified_files(status)
        assert result == frozenset({"modified.py", "another.py"})


class TestGetUntrackedFiles:
    def test_get_untracked_files_empty(self) -> None:
        status = MagicMock()
        status.untracked = []
        result = _get_untracked_files(status)
        assert result == frozenset()

    def test_get_untracked_files_with_files(self) -> None:
        status = MagicMock()
        status.untracked = [b"untracked.py", b"new_file.txt"]
        result = _get_untracked_files(status)
        assert result == frozenset({"untracked.py", "new_file.txt"})


class TestGetCurrentBranch:
    def test_get_current_branch_on_branch(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {b"HEAD": b"refs/heads/main"}
        branch = _get_current_branch(repo)
        assert branch == "main"

    def test_get_current_branch_on_feature_branch(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {b"HEAD": b"refs/heads/feature/test"}
        branch = _get_current_branch(repo)
        assert branch == "feature/test"

    def test_get_current_branch_detached_head(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {}
        branch = _get_current_branch(repo)
        assert branch is None


class TestIsDetached:
    def test_is_detached_when_on_branch(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {b"HEAD": b"refs/heads/main"}
        assert _is_detached(repo) is False

    def test_is_detached_when_detached(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {}
        assert _is_detached(repo) is True

    def test_is_detached_when_head_points_to_tag(self) -> None:
        repo = MagicMock()
        repo.refs.get_symrefs.return_value = {b"HEAD": b"refs/tags/v1.0"}
        assert _is_detached(repo) is True


class TestGetHeadCommit:
    def test_get_head_commit(self) -> None:
        repo = MagicMock()
        repo.head.return_value = b"abc123def456"
        commit = _get_head_commit(repo)
        assert commit == "abc123def456"


class TestIsDirty:
    def test_is_dirty_with_staged_files(self) -> None:
        assert _is_dirty(frozenset({"file.py"}), frozenset()) is True

    def test_is_dirty_with_modified_files(self) -> None:
        assert _is_dirty(frozenset(), frozenset({"file.py"})) is True

    def test_is_dirty_with_both(self) -> None:
        assert _is_dirty(frozenset({"a.py"}), frozenset({"b.py"})) is True

    def test_not_dirty_when_clean(self) -> None:
        assert _is_dirty(frozenset(), frozenset()) is False


class TestGetGitContext:
    def test_get_git_context_not_in_repo(self, tmp_path: Path) -> None:
        result = get_git_context(tmp_path)
        assert result is None

    def test_get_git_context_returns_none_on_error(self, tmp_path: Path) -> None:
        # Create a non-git directory
        result = get_git_context(tmp_path)
        assert result is None

    def test_get_git_context_with_none_cwd(self) -> None:
        # Should work with None cwd (uses current directory)
        result = get_git_context(None)
        # We're in the oaps repo, so should succeed
        assert result is not None

    def test_get_git_context_in_current_repo(self) -> None:
        # Test with the actual repo we're running in
        project_root = Path(__file__).parent.parent.parent.parent
        result = get_git_context(project_root)
        assert result is not None
        assert isinstance(result, GitContext)
        assert result.head_commit is not None
        # Current repo should have a branch
        assert result.branch is not None or result.is_detached is True

    def test_get_git_context_result_has_correct_structure(self) -> None:
        # Test with the actual repo
        project_root = Path(__file__).parent.parent.parent.parent
        result = get_git_context(project_root)
        assert result is not None

        # Check all expected attributes exist
        assert hasattr(result, "main_worktree_dir")
        assert hasattr(result, "worktree_dir")
        assert hasattr(result, "head_commit")
        assert hasattr(result, "is_detached")
        assert hasattr(result, "is_dirty")
        assert hasattr(result, "staged_files")
        assert hasattr(result, "modified_files")
        assert hasattr(result, "untracked_files")
        assert hasattr(result, "conflict_files")
        assert hasattr(result, "branch")
        assert hasattr(result, "tag")

        # Check types are correct
        assert isinstance(result.staged_files, frozenset)
        assert isinstance(result.modified_files, frozenset)
        assert isinstance(result.untracked_files, frozenset)
        assert isinstance(result.conflict_files, frozenset)

    def test_get_git_context_with_string_path(self) -> None:
        # Test with string path
        project_root = Path(__file__).parent.parent.parent.parent
        result = get_git_context(str(project_root))
        assert result is not None
