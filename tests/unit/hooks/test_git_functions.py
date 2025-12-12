"""Tests for git-related expression functions."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from oaps.enums import HookEventType
from oaps.hooks import PreToolUseInput, create_function_registry, evaluate_condition
from oaps.hooks._context import HookContext
from oaps.hooks._functions import (
    CurrentBranchFunction,
    GitFileInFunction,
    GitHasConflictsFunction,
    GitHasModifiedFunction,
    GitHasStagedFunction,
    GitHasUntrackedFunction,
    HasConflictsFunction,
    IsModifiedFunction,
    IsStagedFunction,
)
from oaps.utils import GitContext


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pre_tool_use_input(tmp_path: Path) -> PreToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PreToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd="/home/user/project",
        tool_name="Bash",
        tool_input={"command": "ls -la"},
        tool_use_id="tool-123",
    )


@pytest.fixture
def git_context(tmp_path: Path) -> GitContext:
    return GitContext(
        main_worktree_dir=tmp_path,
        worktree_dir=tmp_path,
        head_commit="abc123def456",
        is_detached=False,
        is_dirty=True,
        staged_files=frozenset({"src/main.py", "tests/test_main.py"}),
        modified_files=frozenset({"README.md", "docs/index.md"}),
        untracked_files=frozenset({"temp.txt", "output.log"}),
        conflict_files=frozenset(),
        branch="feature/test-branch",
        tag=None,
    )


@pytest.fixture
def git_context_with_conflicts(tmp_path: Path) -> GitContext:
    return GitContext(
        main_worktree_dir=tmp_path,
        worktree_dir=tmp_path,
        head_commit="abc123def456",
        is_detached=False,
        is_dirty=True,
        staged_files=frozenset(),
        modified_files=frozenset(),
        untracked_files=frozenset(),
        conflict_files=frozenset({"conflicted.py", "another_conflict.py"}),
        branch="feature/merge-branch",
        tag=None,
    )


@pytest.fixture
def context_with_git(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
    git_context: GitContext,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
        git=git_context,
    )


@pytest.fixture
def context_without_git(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
        git=None,
    )


class TestIsStagedFunction:
    def test_file_is_staged(self) -> None:
        func = IsStagedFunction(staged_files=frozenset({"file.py", "other.py"}))
        assert func("file.py") is True

    def test_file_not_staged(self) -> None:
        func = IsStagedFunction(staged_files=frozenset({"file.py"}))
        assert func("other.py") is False

    def test_empty_staged_files(self) -> None:
        func = IsStagedFunction(staged_files=frozenset())
        assert func("file.py") is False

    def test_invalid_path_type(self) -> None:
        func = IsStagedFunction(staged_files=frozenset({"file.py"}))
        assert func(123) is False
        assert func(None) is False


class TestIsModifiedFunction:
    def test_file_is_modified(self) -> None:
        func = IsModifiedFunction(modified_files=frozenset({"file.py", "other.py"}))
        assert func("file.py") is True

    def test_file_not_modified(self) -> None:
        func = IsModifiedFunction(modified_files=frozenset({"file.py"}))
        assert func("other.py") is False

    def test_invalid_path_type(self) -> None:
        func = IsModifiedFunction(modified_files=frozenset({"file.py"}))
        assert func(123) is False


class TestHasConflictsFunction:
    def test_has_conflicts(self) -> None:
        func = HasConflictsFunction(conflict_files=frozenset({"file.py"}))
        assert func() is True

    def test_no_conflicts(self) -> None:
        func = HasConflictsFunction(conflict_files=frozenset())
        assert func() is False


class TestCurrentBranchFunction:
    def test_returns_branch_name(self) -> None:
        func = CurrentBranchFunction(branch="main")
        assert func() == "main"

    def test_returns_none_when_detached(self) -> None:
        func = CurrentBranchFunction(branch=None)
        assert func() is None


class TestGitHasStagedFunction:
    def test_has_staged_no_pattern(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset({"file.py"}))
        assert func() is True

    def test_no_staged(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset())
        assert func() is False

    def test_has_staged_with_matching_pattern(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset({"src/main.py", "test.py"}))
        assert func("*.py") is True

    def test_has_staged_with_non_matching_pattern(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset({"src/main.py"}))
        assert func("*.js") is False

    def test_has_staged_invalid_pattern_type(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset({"file.py"}))
        assert func(123) is False


class TestGitHasModifiedFunction:
    def test_has_modified_no_pattern(self) -> None:
        func = GitHasModifiedFunction(modified_files=frozenset({"file.py"}))
        assert func() is True

    def test_no_modified(self) -> None:
        func = GitHasModifiedFunction(modified_files=frozenset())
        assert func() is False

    def test_has_modified_with_matching_pattern(self) -> None:
        func = GitHasModifiedFunction(modified_files=frozenset({"README.md"}))
        assert func("*.md") is True

    def test_has_modified_with_non_matching_pattern(self) -> None:
        func = GitHasModifiedFunction(modified_files=frozenset({"README.md"}))
        assert func("*.py") is False


class TestGitHasUntrackedFunction:
    def test_has_untracked_no_pattern(self) -> None:
        func = GitHasUntrackedFunction(untracked_files=frozenset({"file.txt"}))
        assert func() is True

    def test_no_untracked(self) -> None:
        func = GitHasUntrackedFunction(untracked_files=frozenset())
        assert func() is False

    def test_has_untracked_with_matching_pattern(self) -> None:
        func = GitHasUntrackedFunction(untracked_files=frozenset({"temp.log"}))
        assert func("*.log") is True


class TestGitHasConflictsFunction:
    def test_has_conflicts_no_pattern(self) -> None:
        func = GitHasConflictsFunction(conflict_files=frozenset({"file.py"}))
        assert func() is True

    def test_no_conflicts(self) -> None:
        func = GitHasConflictsFunction(conflict_files=frozenset())
        assert func() is False


class TestGitFileInFunction:
    def test_file_in_staged(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("src/main.py", "staged") is True

    def test_file_in_modified(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("README.md", "modified") is True

    def test_file_in_untracked(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("temp.txt", "untracked") is True

    def test_file_in_conflict(self, git_context_with_conflicts: GitContext) -> None:
        func = GitFileInFunction(git=git_context_with_conflicts)
        assert func("conflicted.py", "conflict") is True

    def test_file_not_in_set(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("nonexistent.py", "staged") is False

    def test_invalid_set_name(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("file.py", "invalid") is False

    def test_no_git_context(self) -> None:
        func = GitFileInFunction(git=None)
        assert func("file.py", "staged") is False

    def test_invalid_path_type(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func(123, "staged") is False

    def test_invalid_set_name_type(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("file.py", 123) is False


class TestCreateFunctionRegistryWithGit:
    def test_registry_includes_git_functions(
        self, git_context: GitContext, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), git=git_context)
        functions = registry.all_functions()

        assert "is_staged" in functions
        assert "is_modified" in functions
        assert "has_conflicts" in functions
        assert "current_branch" in functions
        assert "git_has_staged" in functions
        assert "git_has_modified" in functions
        assert "git_has_untracked" in functions
        assert "git_has_conflicts" in functions
        assert "git_file_in" in functions

    def test_registry_without_git_context(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path), git=None)
        functions = registry.all_functions()

        # Functions should still be registered but return safe defaults
        is_staged = functions["is_staged"]
        assert is_staged("file.py") is False

        has_conflicts = functions["has_conflicts"]
        assert has_conflicts() is False

        current_branch = functions["current_branch"]
        assert current_branch() is None


class TestGitFunctionsInExpressions:
    def test_is_staged_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition('is_staged("src/main.py")', context_with_git)
        assert result is True

    def test_is_staged_false_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition('is_staged("nonexistent.py")', context_with_git)
        assert result is False

    def test_is_modified_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition('is_modified("README.md")', context_with_git)
        assert result is True

    def test_has_conflicts_false(self, context_with_git: HookContext) -> None:
        result = evaluate_condition("has_conflicts()", context_with_git)
        assert result is False

    def test_current_branch_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition(
            'current_branch() == "feature/test-branch"', context_with_git
        )
        assert result is True

    def test_git_has_staged_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition("git_has_staged()", context_with_git)
        assert result is True

    def test_git_has_staged_with_pattern(self, context_with_git: HookContext) -> None:
        result = evaluate_condition('git_has_staged("*.py")', context_with_git)
        assert result is True

    def test_git_has_modified_in_expression(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition("git_has_modified()", context_with_git)
        assert result is True

    def test_git_has_untracked_in_expression(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition("git_has_untracked()", context_with_git)
        assert result is True

    def test_git_file_in_expression(self, context_with_git: HookContext) -> None:
        result = evaluate_condition(
            'git_file_in("src/main.py", "staged")', context_with_git
        )
        assert result is True

    def test_git_file_in_modified_expression(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition(
            'git_file_in("README.md", "modified")', context_with_git
        )
        assert result is True

    def test_git_functions_without_git_context(
        self, context_without_git: HookContext
    ) -> None:
        # All git functions should return safe defaults
        assert evaluate_condition('is_staged("file.py")', context_without_git) is False
        assert (
            evaluate_condition('is_modified("file.py")', context_without_git) is False
        )
        assert evaluate_condition("has_conflicts()", context_without_git) is False
        assert (
            evaluate_condition("current_branch() == null", context_without_git) is True
        )
        assert evaluate_condition("git_has_staged()", context_without_git) is False
        assert evaluate_condition("git_has_modified()", context_without_git) is False
        assert evaluate_condition("git_has_untracked()", context_without_git) is False


class TestAdaptContextWithGitFileSets:
    def test_adapt_context_includes_git_file_sets(
        self, context_with_git: HookContext
    ) -> None:
        from oaps.hooks._expression import adapt_context

        result = adapt_context(context_with_git)

        assert "git_staged_files" in result
        assert "git_modified_files" in result
        assert "git_untracked_files" in result
        assert "git_conflict_files" in result

        # Check the actual values
        staged_files = result["git_staged_files"]
        modified_files = result["git_modified_files"]
        untracked_files = result["git_untracked_files"]
        conflict_files = result["git_conflict_files"]
        assert isinstance(staged_files, list)
        assert isinstance(modified_files, list)
        assert isinstance(untracked_files, list)
        assert isinstance(conflict_files, list)
        assert "src/main.py" in staged_files
        assert "README.md" in modified_files
        assert "temp.txt" in untracked_files
        assert conflict_files == []

    def test_adapt_context_empty_git_file_sets_when_no_git(
        self, context_without_git: HookContext
    ) -> None:
        from oaps.hooks._expression import adapt_context

        result = adapt_context(context_without_git)

        assert result["git_staged_files"] == []
        assert result["git_modified_files"] == []
        assert result["git_untracked_files"] == []
        assert result["git_conflict_files"] == []
