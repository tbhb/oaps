"""Tests for OAPS expression function implementations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from oaps.hooks._functions import (
    EnvFunction,
    FileExistsFunction,
    GitFileInFunction,
    GitHasConflictsFunction,
    GitHasModifiedFunction,
    GitHasStagedFunction,
    GitHasUntrackedFunction,
    IsExecutableFunction,
    IsGitRepoFunction,
    IsModifiedFunction,
    IsPathUnderFunction,
    IsStagedFunction,
    MatchesGlobFunction,
    ProjectGetFunction,
    SessionGetFunction,
)
from oaps.project import Project
from oaps.session import Session
from oaps.utils import GitContext, MockStateStore


class TestIsPathUnderFunction:
    def test_path_under_base_returns_true(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        child = tmp_path / "subdir" / "file.txt"
        assert func(str(child), str(tmp_path)) is True

    def test_path_not_under_base_returns_false(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        other = Path("/some/other/path")
        assert func(str(other), str(tmp_path)) is False

    def test_same_path_returns_true(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        assert func(str(tmp_path), str(tmp_path)) is True

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        malicious = str(tmp_path / "subdir" / ".." / ".." / "etc" / "passwd")
        assert func(malicious, str(tmp_path / "subdir")) is False

    def test_relative_path_resolved(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        relative = str(subdir / "inner" / ".." / "file.txt")
        assert func(relative, str(tmp_path)) is True

    def test_nonexistent_path_handled(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        nonexistent = tmp_path / "does_not_exist" / "file.txt"
        assert func(str(nonexistent), str(tmp_path)) is True

    def test_invalid_path_type_returns_false(self) -> None:
        func = IsPathUnderFunction()
        assert func(123, "/base") is False
        assert func("/path", 456) is False
        assert func(None, "/base") is False
        assert func("/path", None) is False

    def test_empty_strings_handled(self) -> None:
        func = IsPathUnderFunction()
        # Empty strings resolve to cwd, which may or may not be under base
        result = func("", "")
        assert isinstance(result, bool)

    def test_oserror_returns_false(self) -> None:
        func = IsPathUnderFunction()
        with patch.object(Path, "resolve", side_effect=OSError("test error")):
            assert func("/some/path", "/base") is False

    def test_value_error_returns_false(self) -> None:
        func = IsPathUnderFunction()
        with patch.object(Path, "resolve", side_effect=ValueError("test error")):
            assert func("/some/path", "/base") is False


class TestFileExistsFunction:
    def test_existing_file_returns_true(self, tmp_path: Path) -> None:
        func = FileExistsFunction()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert func(str(test_file)) is True

    def test_nonexistent_file_returns_false(self) -> None:
        func = FileExistsFunction()
        assert func("/nonexistent/path/file.txt") is False

    def test_existing_directory_returns_true(self, tmp_path: Path) -> None:
        func = FileExistsFunction()
        assert func(str(tmp_path)) is True

    def test_invalid_path_type_returns_false(self) -> None:
        func = FileExistsFunction()
        assert func(123) is False
        assert func(None) is False
        assert func(["list"]) is False
        assert func({"dict": "value"}) is False

    def test_oserror_returns_false(self) -> None:
        func = FileExistsFunction()
        with patch.object(Path, "exists", side_effect=OSError("test error")):
            assert func("/some/path") is False


class TestIsExecutableFunction:
    def test_executable_file_returns_true(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        exec_file = tmp_path / "script.sh"
        exec_file.write_text("#!/bin/bash\necho hello")
        exec_file.chmod(0o755)
        assert func(str(exec_file)) is True

    def test_non_executable_file_returns_false(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        regular_file = tmp_path / "data.txt"
        regular_file.write_text("some data")
        regular_file.chmod(0o644)
        assert func(str(regular_file)) is False

    def test_nonexistent_file_returns_false(self) -> None:
        func = IsExecutableFunction()
        assert func("/nonexistent/file") is False

    def test_directory_returns_false(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        # Directory is not a file, so should return False
        assert func(str(tmp_path)) is False

    def test_invalid_path_type_returns_false(self) -> None:
        func = IsExecutableFunction()
        assert func(123) is False
        assert func(None) is False
        assert func(["list"]) is False

    def test_oserror_returns_false(self) -> None:
        func = IsExecutableFunction()
        with patch.object(Path, "is_file", side_effect=OSError("test error")):
            assert func("/some/path") is False


class TestMatchesGlobFunction:
    def test_exact_match(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "test.py") is True

    def test_wildcard_star(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "*.py") is True
        assert func("module.py", "*.py") is True

    def test_wildcard_star_no_match(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "*.js") is False

    def test_wildcard_question_mark(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "tes?.py") is True
        assert func("tess.py", "tes?.py") is True
        assert func("tests.py", "tes?.py") is False  # ? matches exactly one char

    def test_character_range(self) -> None:
        func = MatchesGlobFunction()
        assert func("test1.py", "test[0-9].py") is True
        assert func("testA.py", "test[0-9].py") is False

    def test_character_set(self) -> None:
        func = MatchesGlobFunction()
        assert func("testa.py", "test[abc].py") is True
        assert func("testd.py", "test[abc].py") is False

    def test_path_matching(self) -> None:
        func = MatchesGlobFunction()
        assert func("src/test.py", "src/*.py") is True
        # fnmatch's * matches any characters including /
        assert func("src/sub/test.py", "src/*.py") is True

    def test_star_matches_slashes_in_fnmatch(self) -> None:
        func = MatchesGlobFunction()
        # fnmatch's * matches any characters including /
        assert func("deep/nested/test.py", "*.py") is True

    def test_invalid_path_type_returns_false(self) -> None:
        func = MatchesGlobFunction()
        assert func(123, "*.py") is False
        assert func(None, "*.py") is False

    def test_invalid_pattern_type_returns_false(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", 123) is False
        assert func("test.py", None) is False

    def test_both_invalid_returns_false(self) -> None:
        func = MatchesGlobFunction()
        assert func(123, 456) is False


class TestEnvFunction:
    def test_existing_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        func = EnvFunction()
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert func("TEST_VAR") == "test_value"

    def test_nonexistent_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        func = EnvFunction()
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert func("NONEXISTENT_VAR") is None

    def test_empty_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        func = EnvFunction()
        monkeypatch.setenv("EMPTY_VAR", "")
        assert func("EMPTY_VAR") == ""

    def test_invalid_name_type(self) -> None:
        func = EnvFunction()
        assert func(123) is None
        assert func(None) is None
        assert func(["list"]) is None


class TestIsGitRepoFunction:
    def test_in_git_repo(self) -> None:
        # The project itself is a git repo
        project_root = Path(__file__).parent.parent.parent.parent
        func = IsGitRepoFunction(cwd=str(project_root))
        assert func() is True

    def test_not_in_git_repo(self, tmp_path: Path) -> None:
        func = IsGitRepoFunction(cwd=str(tmp_path))
        assert func() is False

    def test_subdirectory_of_git_repo(self) -> None:
        tests_dir = Path(__file__).parent
        func = IsGitRepoFunction(cwd=str(tests_dir))
        assert func() is True

    def test_git_directory_at_root(self, tmp_path: Path) -> None:
        # Create a .git directory to simulate a git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        func = IsGitRepoFunction(cwd=str(tmp_path))
        assert func() is True

    def test_git_directory_in_parent(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)
        func = IsGitRepoFunction(cwd=str(subdir))
        assert func() is True

    def test_oserror_returns_false(self, tmp_path: Path) -> None:
        func = IsGitRepoFunction(cwd=str(tmp_path))
        with patch.object(Path, "parents", side_effect=OSError("test error")):
            assert func() is False


class TestSessionGetFunction:
    @pytest.fixture
    def mock_session(self) -> Session:
        store = MockStateStore()
        store.set("test_key", "test_value", author="test")
        store.set("counter", 42, author="test")
        store.set("float_val", 3.14, author="test")
        store.set("bytes_val", b"binary", author="test")
        return Session(id="test-session", store=store)

    def test_existing_string_key(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("test_key") == "test_value"

    def test_existing_int_key(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("counter") == 42

    def test_existing_float_key(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("float_val") == 3.14

    def test_existing_bytes_key(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("bytes_val") == b"binary"

    def test_nonexistent_key(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("nonexistent") is None

    def test_invalid_key_type(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func(123) is None
        assert func(None) is None
        assert func(["list"]) is None


class TestProjectGetFunction:
    @pytest.fixture
    def mock_project(self) -> Project:
        store = MockStateStore()
        store.set("test_key", "test_value", author="test")
        store.set("counter", 42, author="test")
        store.set("float_val", 3.14, author="test")
        store.set("bytes_val", b"binary", author="test")
        return Project(store=store)

    def test_existing_string_key(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func("test_key") == "test_value"

    def test_existing_int_key(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func("counter") == 42

    def test_existing_float_key(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func("float_val") == 3.14

    def test_existing_bytes_key(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func("bytes_val") == b"binary"

    def test_nonexistent_key(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func("nonexistent") is None

    def test_invalid_key_type(self, mock_project: Project) -> None:
        func = ProjectGetFunction(project=mock_project)
        assert func(123) is None
        assert func(None) is None
        assert func(["list"]) is None

    def test_none_project_returns_none(self) -> None:
        func = ProjectGetFunction(project=None)
        assert func("any_key") is None

    def test_oserror_returns_none_and_logs_warning(
        self, mock_project: Project, caplog: pytest.LogCaptureFixture
    ) -> None:
        func = ProjectGetFunction(project=mock_project)
        with patch.object(Project, "get", side_effect=OSError("db error")):
            result = func("test_key")
        assert result is None
        assert "Error accessing project state for key 'test_key'" in caplog.text

    def test_sqlite_error_returns_none_and_logs_warning(
        self, mock_project: Project, caplog: pytest.LogCaptureFixture
    ) -> None:
        import sqlite3

        func = ProjectGetFunction(project=mock_project)
        with patch.object(Project, "get", side_effect=sqlite3.Error("sqlite error")):
            result = func("test_key")
        assert result is None
        assert "Error accessing project state for key 'test_key'" in caplog.text


class TestIsStagedFunction:
    def test_invalid_path_type_returns_false(self) -> None:
        func = IsStagedFunction(staged_files=frozenset({"file.py"}))
        assert func(123) is False
        assert func(None) is False
        assert func(["list"]) is False


class TestIsModifiedFunction:
    def test_invalid_path_type_returns_false(self) -> None:
        func = IsModifiedFunction(modified_files=frozenset({"file.py"}))
        assert func(123) is False
        assert func(None) is False


class TestGitHasStagedFunction:
    def test_pattern_matching_filters_files(self) -> None:
        files = frozenset({"src/main.py", "README.md"})
        func = GitHasStagedFunction(staged_files=files)
        assert func("*.py") is True
        assert func("*.md") is True
        assert func("*.js") is False

    def test_invalid_pattern_type_returns_false(self) -> None:
        func = GitHasStagedFunction(staged_files=frozenset({"file.py"}))
        assert func(123) is False
        assert func(["*.py"]) is False


class TestGitHasModifiedFunction:
    def test_pattern_matching_filters_files(self) -> None:
        files = frozenset({"README.md", "main.py"})
        func = GitHasModifiedFunction(modified_files=files)
        assert func("*.md") is True
        assert func("*.py") is True
        assert func("*.js") is False

    def test_invalid_pattern_type_returns_false(self) -> None:
        func = GitHasModifiedFunction(modified_files=frozenset({"file.py"}))
        assert func(123) is False


class TestGitHasUntrackedFunction:
    def test_pattern_matching_filters_files(self) -> None:
        files = frozenset({"temp.log", "data.csv"})
        func = GitHasUntrackedFunction(untracked_files=files)
        assert func("*.log") is True
        assert func("*.csv") is True
        assert func("*.txt") is False

    def test_invalid_pattern_type_returns_false(self) -> None:
        func = GitHasUntrackedFunction(untracked_files=frozenset({"file.txt"}))
        assert func(123) is False


class TestGitHasConflictsFunction:
    def test_pattern_matching_filters_files(self) -> None:
        files = frozenset({"merge.py", "config.yml"})
        func = GitHasConflictsFunction(conflict_files=files)
        assert func("*.py") is True
        assert func("*.yml") is True
        assert func("*.js") is False

    def test_invalid_pattern_type_returns_false(self) -> None:
        func = GitHasConflictsFunction(conflict_files=frozenset({"file.py"}))
        assert func(123) is False


class TestGitFileInFunction:
    @pytest.fixture
    def git_context(self, tmp_path: Path) -> GitContext:
        return GitContext(
            main_worktree_dir=tmp_path,
            worktree_dir=tmp_path,
            head_commit="abc123",
            is_detached=False,
            is_dirty=True,
            staged_files=frozenset({"staged.py"}),
            modified_files=frozenset({"modified.py"}),
            untracked_files=frozenset({"untracked.py"}),
            conflict_files=frozenset({"conflict.py"}),
            branch="main",
            tag=None,
        )

    def test_dispatches_to_correct_file_set(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        # Each set name maps to the correct file set
        assert func("staged.py", "staged") is True
        assert func("modified.py", "modified") is True
        assert func("untracked.py", "untracked") is True
        assert func("conflict.py", "conflict") is True
        # Files not in the specified set return False
        assert func("staged.py", "modified") is False

    def test_invalid_set_name_returns_false(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func("file.py", "invalid") is False

    def test_no_git_context_returns_false(self) -> None:
        func = GitFileInFunction(git=None)
        assert func("file.py", "staged") is False

    def test_invalid_types_return_false(self, git_context: GitContext) -> None:
        func = GitFileInFunction(git=git_context)
        assert func(123, "staged") is False
        assert func("file.py", 123) is False
