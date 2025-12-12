"""Integration tests for ProjectRepository extended operations.

These tests verify ProjectRepository's extended operations (diff, log, blame,
search, file history) using real Git repositories.
"""

import subprocess
from pathlib import Path

import pytest

from oaps.exceptions import OapsRepositoryPathViolationError
from oaps.repository import BlameLine, DiffStats, ProjectRepository


def _run_git(cwd: Path, *args: str) -> None:
    """Run a git command in the given directory."""
    result = subprocess.run(  # noqa: S603 - Safe: running git with controlled args
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr}"
        raise RuntimeError(msg)


@pytest.fixture
def project_with_history(tmp_path: Path) -> Path:
    """Create a git repository with multiple commits for testing.

    Creates:
    - Initial commit with README.md
    - Second commit adding src/main.py
    - Third commit modifying both files
    """
    # Initialize git repo
    _run_git(tmp_path, "init")
    _run_git(tmp_path, "config", "user.name", "Test User")
    _run_git(tmp_path, "config", "user.email", "test@example.com")
    # Disable GPG signing to avoid signature issues
    _run_git(tmp_path, "config", "commit.gpgsign", "false")

    # First commit: README.md
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n\nInitial version.\n")
    _run_git(tmp_path, "add", "README.md")
    _run_git(tmp_path, "commit", "-m", "Initial commit with README")

    # Second commit: add src/main.py
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_py = src_dir / "main.py"
    main_py.write_text('def main():\n    print("Hello")\n')
    _run_git(tmp_path, "add", "src/main.py")
    _run_git(tmp_path, "commit", "-m", "Add main.py entry point")

    # Third commit: modify both files
    readme.write_text("# Test Project\n\nUpdated version.\n\nMore content.\n")
    main_content = """\
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""
    main_py.write_text(main_content)
    _run_git(tmp_path, "add", "README.md", "src/main.py")
    _run_git(tmp_path, "commit", "-m", "Update README and main.py")

    return tmp_path


class TestDiffOperations:
    def test_get_diff_shows_unstaged_changes(self, project_with_history: Path) -> None:
        main_py = project_with_history / "src" / "main.py"
        main_py.write_text('def main():\n    print("Modified!")\n')

        with ProjectRepository(worktree_dir=project_with_history) as repo:
            diff = repo.get_diff(staged=False)

        assert "Modified!" in diff
        assert "src/main.py" in diff

    def test_get_diff_staged_shows_staged_changes(
        self, project_with_history: Path
    ) -> None:
        main_py = project_with_history / "src" / "main.py"
        main_py.write_text('def main():\n    print("Staged change")\n')
        _run_git(project_with_history, "add", "src/main.py")

        with ProjectRepository(worktree_dir=project_with_history) as repo:
            diff = repo.get_diff(staged=True)

        assert "Staged change" in diff
        assert "src/main.py" in diff

    def test_get_diff_stats_counts_lines(self, project_with_history: Path) -> None:
        main_py = project_with_history / "src" / "main.py"
        # Add 3 new lines
        new_content = """\
def main():
    print("Hello, World!")
    print("Line 2")
    print("Line 3")
    print("Line 4")
"""
        main_py.write_text(new_content)

        with ProjectRepository(worktree_dir=project_with_history) as repo:
            stats = repo.get_diff_stats(staged=False)

        assert isinstance(stats, DiffStats)
        assert stats.files_changed >= 1
        assert stats.total_additions >= 3

    def test_get_diff_empty_when_no_changes(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            diff = repo.get_diff(staged=False)

        assert diff == ""


class TestLogOperations:
    def test_get_log_returns_commits(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            commits = repo.get_log(n=10)

        assert len(commits) == 3
        # Commits are in reverse chronological order (newest first)
        assert "Update README and main.py" in commits[0].message
        assert "Add main.py entry point" in commits[1].message
        assert "Initial commit with README" in commits[2].message

    def test_get_log_filters_by_path(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            commits = repo.get_log(n=10, path=Path("src/main.py"))

        # Only 2 commits affect src/main.py (add and update)
        assert len(commits) == 2
        for commit in commits:
            assert "main.py" in commit.message or "Update" in commit.message

    def test_get_log_filters_by_grep(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            commits = repo.get_log(n=10, grep="Initial")

        assert len(commits) == 1
        assert "Initial commit" in commits[0].message

    def test_get_log_filters_by_author(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            commits = repo.get_log(n=10, author="Test User")

        assert len(commits) == 3
        for commit in commits:
            assert commit.author_name == "Test User"


class TestSearchCommits:
    def test_search_commits_finds_matches(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            results = repo.search_commits(grep="main.py")

        assert len(results) >= 1
        for result in results:
            assert "main.py" in result.message.lower()

    def test_search_commits_by_author(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            results = repo.search_commits(author="test@example.com")

        assert len(results) == 3
        for result in results:
            assert result.author_email == "test@example.com"

    def test_search_commits_empty_results(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            results = repo.search_commits(grep="nonexistent-pattern-xyz123")

        assert results == []


class TestBlameOperations:
    def test_get_blame_returns_blame_lines(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            blame = repo.get_blame(Path("src/main.py"))

        assert len(blame) >= 1
        for line in blame:
            assert isinstance(line, BlameLine)
            assert len(line.sha) == 40
            assert line.author_name == "Test User"
            assert line.author_email == "test@example.com"
            assert line.line_no >= 1

    def test_get_blame_empty_file(self, project_with_history: Path) -> None:
        # Create and commit an empty file
        empty_file = project_with_history / "empty.txt"
        empty_file.write_text("")
        _run_git(project_with_history, "add", "empty.txt")
        _run_git(project_with_history, "commit", "-m", "Add empty file")

        with ProjectRepository(worktree_dir=project_with_history) as repo:
            blame = repo.get_blame(Path("empty.txt"))

        assert blame == []

    def test_get_blame_rejects_oaps_path(self, project_with_history: Path) -> None:
        # Create .oaps directory with a file
        oaps_dir = project_with_history / ".oaps"
        oaps_dir.mkdir()
        oaps_file = oaps_dir / "config.toml"
        oaps_file.write_text("[settings]\nkey = 'value'\n")

        with (
            ProjectRepository(worktree_dir=project_with_history) as repo,
            pytest.raises(OapsRepositoryPathViolationError),
        ):
            repo.get_blame(Path(".oaps/config.toml"))


class TestFileHistory:
    def test_get_file_at_commit(self, project_with_history: Path) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            # Get the initial commit SHA
            commits = repo.get_log(n=10)
            initial_commit = commits[-1]  # Oldest commit

            # Get README content at initial commit
            content = repo.get_file_at_commit(Path("README.md"), initial_commit.sha)

        assert content is not None
        assert b"Initial version" in content

    def test_get_file_at_commit_returns_none_for_missing(
        self, project_with_history: Path
    ) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            # Get the initial commit SHA (before src/main.py existed)
            commits = repo.get_log(n=10)
            initial_commit = commits[-1]  # Oldest commit

            # src/main.py didn't exist in the initial commit
            content = repo.get_file_at_commit(Path("src/main.py"), initial_commit.sha)

        assert content is None

    def test_get_file_at_commit_abbreviated_sha(
        self, project_with_history: Path
    ) -> None:
        with ProjectRepository(worktree_dir=project_with_history) as repo:
            # Get full SHA and use abbreviated version
            commits = repo.get_log(n=10)
            full_sha = commits[0].sha
            abbreviated_sha = full_sha[:8]  # Use first 8 characters

            content = repo.get_file_at_commit(Path("README.md"), abbreviated_sha)

        assert content is not None
        # The latest version has "Updated version" and "More content"
        assert b"Updated version" in content
        assert b"More content" in content
