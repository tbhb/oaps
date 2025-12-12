"""Property-based tests for OapsRepository invariants.

This module uses Hypothesis to test key invariants of the OapsRepository class:
- Path validation: paths inside .oaps/ are valid, paths outside are invalid
- Traversal rejection: paths with .. never escape .oaps/
- Commit idempotence: committing when clean is a no-op
- Status consistency: status reflects actual file state
- Discard completeness: after discard, has_changes() is False
- Stateful testing: operation sequences maintain invariants
"""

import tempfile
from pathlib import Path

from hypothesis import assume, given, settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

from oaps.exceptions import OapsRepositoryPathViolationError
from oaps.repository import OapsRepository

# =============================================================================
# Strategies
# =============================================================================

# Safe ASCII filename characters (lowercase alphanumeric, hyphen, underscore)
# Restricting to lowercase avoids case-sensitivity issues on macOS
_SAFE_FILENAME_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789-_"

# Valid filenames (ASCII only, no reserved names)
safe_filename = st.text(
    alphabet=_SAFE_FILENAME_ALPHABET, min_size=1, max_size=30
).filter(lambda x: x not in {".", "..", ".git"})

# Relative path components (directories and filenames)
path_component = safe_filename

# Valid relative paths within repository (1-3 components)
valid_relative_path = st.lists(path_component, min_size=1, max_size=3).map(
    lambda parts: "/".join(parts)
)

# Safe ASCII file content (printable characters)
_SAFE_CONTENT_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    " \n\t.,!?-_:;()[]{}'\""
)
safe_content = st.text(alphabet=_SAFE_CONTENT_ALPHABET, min_size=0, max_size=200)

# Traversal attack patterns
traversal_patterns = st.sampled_from(
    [
        "../",
        "/../",
        "..\\",
        "/..\\",
        "./../",
        "foo/../../../",
        "a/b/c/../../../../",
        "%2e%2e/",
        "..%2f",
        "....//",
    ]
)


# =============================================================================
# Fixture Helpers
# =============================================================================


def _run_git(cwd: Path, *args: str) -> None:
    """Run a git command in the given directory."""
    import subprocess

    result = subprocess.run(  # noqa: S603 - Safe: controlled git args
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr}"
        raise RuntimeError(msg)


def _init_git_repo(oaps_dir: Path) -> None:
    """Initialize a git repository with an initial commit using system git.

    This avoids dulwich API deprecation warnings by using the system git command.
    """
    _run_git(oaps_dir, "init")
    _run_git(oaps_dir, "config", "user.name", "Test User")
    _run_git(oaps_dir, "config", "user.email", "test@example.com")
    _run_git(oaps_dir, "config", "commit.gpgsign", "false")

    # Create initial commit
    readme = oaps_dir / "README.md"
    readme.write_text("# OAPS")
    _run_git(oaps_dir, "add", "README.md")
    _run_git(oaps_dir, "commit", "-m", "Initial commit")


def create_oaps_repo() -> tuple[OapsRepository, Path, tempfile.TemporaryDirectory[str]]:
    """Create a fresh OapsRepository with a temporary directory.

    Returns:
        Tuple of (OapsRepository, project_dir, TemporaryDirectory).
        The TemporaryDirectory must be kept alive for cleanup.
    """
    tmpdir = tempfile.TemporaryDirectory()
    project_dir = Path(tmpdir.name)
    oaps_dir = project_dir / ".oaps"
    oaps_dir.mkdir()

    # Initialize git repository with initial commit using system git
    _init_git_repo(oaps_dir)

    oaps_repo = OapsRepository(working_dir=project_dir)
    return oaps_repo, project_dir, tmpdir


# =============================================================================
# Path Validation Properties
# =============================================================================


class TestPathValidationProperties:
    """Properties for path validation behavior."""

    @given(filename=safe_filename)
    @settings(max_examples=50, deadline=None)
    def test_path_inside_oaps_always_valid(self, filename: str) -> None:
        """Property: any valid filename inside .oaps/ should be valid."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            path = repo.root / filename
            assert repo.validate_path(path) is True
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(rel_path=valid_relative_path)
    @settings(max_examples=50, deadline=None)
    def test_nested_path_inside_oaps_always_valid(self, rel_path: str) -> None:
        """Property: any valid nested path inside .oaps/ should be valid."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            path = repo.root / rel_path
            assert repo.validate_path(path) is True
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename)
    @settings(max_examples=50, deadline=None)
    def test_path_outside_oaps_always_invalid(self, filename: str) -> None:
        """Property: any path outside .oaps/ should be invalid."""
        repo, project_dir, tmpdir = create_oaps_repo()
        try:
            # Path in project root (not .oaps/)
            path = project_dir / filename
            assert repo.validate_path(path) is False
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename)
    @settings(max_examples=30, deadline=None)
    def test_sibling_directory_always_invalid(self, filename: str) -> None:
        """Property: paths in sibling directories are always invalid."""
        repo, project_dir, tmpdir = create_oaps_repo()
        try:
            # Create sibling directory
            sibling = project_dir / "other_dir"
            sibling.mkdir(exist_ok=True)
            path = sibling / filename
            assert repo.validate_path(path) is False
        finally:
            repo.close()
            tmpdir.cleanup()


# =============================================================================
# Traversal Rejection Properties
# =============================================================================


class TestTraversalRejectionProperties:
    """Properties for path traversal attack rejection."""

    @given(attack=traversal_patterns, suffix=safe_filename)
    @settings(max_examples=50, deadline=None)
    def test_traversal_attacks_always_rejected(self, attack: str, suffix: str) -> None:
        """Property: paths with .. that escape .oaps/ should always be invalid."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Build path that attempts to escape
            attack_path = repo.root / attack / suffix

            # If the resolved path is outside .oaps/, it should be invalid
            try:
                resolved = attack_path.resolve()
                if not resolved.is_relative_to(repo.root):
                    assert repo.validate_path(attack_path) is False
            except (OSError, ValueError):
                # Invalid path - that's fine, it would fail anyway
                pass
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(depth=st.integers(min_value=1, max_value=5))
    @settings(max_examples=30, deadline=None)
    def test_deep_traversal_always_rejected(self, depth: int) -> None:
        """Property: escaping via multiple .. components always fails."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Build path with multiple .. to escape
            traversal = "/".join([".."] * (depth + 2))  # +2 to ensure escape
            attack_path = repo.root / "subdir" / traversal / "target.txt"

            try:
                resolved = attack_path.resolve()
                if not resolved.is_relative_to(repo.root):
                    assert repo.validate_path(attack_path) is False
            except (OSError, ValueError):
                pass
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(prefix=valid_relative_path)
    @settings(max_examples=30, deadline=None)
    def test_traversal_from_nested_path_rejected(self, prefix: str) -> None:
        """Property: .. escapes from nested paths are always rejected."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Count depth and add enough .. to escape
            depth = prefix.count("/") + 1
            traversal = "/".join([".."] * (depth + 2))
            attack_path = repo.root / prefix / traversal / "escape.txt"

            try:
                resolved = attack_path.resolve()
                if not resolved.is_relative_to(repo.root):
                    assert repo.validate_path(attack_path) is False
            except (OSError, ValueError):
                pass
        finally:
            repo.close()
            tmpdir.cleanup()


# =============================================================================
# Commit Idempotence Properties
# =============================================================================


class TestCommitIdempotenceProperties:
    """Properties for commit operation idempotence."""

    @given(st.data())
    @settings(max_examples=20, deadline=None)
    def test_commit_on_clean_repo_is_noop(self, data: st.DataObject) -> None:
        """Property: committing when repo is clean returns no_changes=True."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Repo should be clean after initial commit
            assert repo.has_changes() is False

            # Commit should be a no-op
            result = repo.commit_pending("No changes commit")

            assert result.no_changes is True
            assert result.sha is None
            assert result.files == frozenset()
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(count=st.integers(min_value=1, max_value=3))
    @settings(max_examples=15, deadline=None)
    def test_multiple_commits_on_clean_all_noop(self, count: int) -> None:
        """Property: multiple commits on clean repo all return no_changes."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            for i in range(count):
                result = repo.commit_pending(f"Attempt {i}")
                assert result.no_changes is True
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename, content=safe_content)
    @settings(max_examples=20, deadline=None)
    def test_commit_after_change_not_noop(self, filename: str, content: str) -> None:
        """Property: commit after making changes is not a no-op."""
        # Skip problematic filenames
        assume(filename not in {".", "..", ".git"})
        assume(not filename.startswith("."))

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Create new file
            new_file = repo.root / filename
            new_file.write_text(content)

            # Verify there are changes
            assert repo.has_changes() is True

            # Commit should succeed
            result = repo.commit_pending("Add file")

            assert result.no_changes is False
            assert result.sha is not None
            assert len(result.files) >= 1
        finally:
            repo.close()
            tmpdir.cleanup()


# =============================================================================
# Status Consistency Properties
# =============================================================================


class TestStatusConsistencyProperties:
    """Properties for status consistency with filesystem state."""

    @given(filename=safe_filename, content=safe_content)
    @settings(max_examples=30, deadline=None)
    def test_new_file_appears_in_untracked(self, filename: str, content: str) -> None:
        """Property: new untracked files appear in status.untracked."""
        assume(filename not in {".", "..", ".git", "README.md"})
        assume(not filename.startswith("."))

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Create new untracked file
            new_file = repo.root / filename
            new_file.write_text(content)

            status = repo.get_status()

            # New file should be in untracked
            assert new_file in status.untracked
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(content=safe_content)
    @settings(max_examples=30, deadline=None)
    def test_modified_tracked_file_appears_in_modified(self, content: str) -> None:
        """Property: modified tracked files appear in status.modified."""
        assume(content != "# OAPS")  # Don't use original content

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Modify tracked file (README.md from initial commit)
            readme = repo.root / "README.md"
            readme.write_text(content)

            status = repo.get_status()

            # Modified file should be in modified (not untracked)
            assert readme in status.modified
            assert readme not in status.untracked
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename)
    @settings(max_examples=30, deadline=None)
    def test_status_sets_are_disjoint(self, filename: str) -> None:
        """Property: staged, modified, untracked sets are always disjoint."""
        assume(filename not in {".", "..", ".git", "README.md"})
        assume(not filename.startswith("."))

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Create a new file
            new_file = repo.root / filename
            new_file.write_text("content")

            status = repo.get_status()

            # Sets should be disjoint
            staged_set = set(status.staged)
            modified_set = set(status.modified)
            untracked_set = set(status.untracked)

            assert staged_set.isdisjoint(modified_set)
            assert staged_set.isdisjoint(untracked_set)
            assert modified_set.isdisjoint(untracked_set)
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename, content=safe_content)
    @settings(max_examples=20, deadline=None)
    def test_has_changes_consistent_with_status(
        self, filename: str, content: str
    ) -> None:
        """Property: has_changes() returns True iff status has any files."""
        assume(filename not in {".", "..", ".git", "README.md"})
        assume(not filename.startswith("."))

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Initially clean
            assert repo.has_changes() is False
            status = repo.get_status()
            assert not status.staged
            assert not status.modified
            assert not status.untracked

            # Create file
            new_file = repo.root / filename
            new_file.write_text(content)

            # Now should have changes
            assert repo.has_changes() is True
            status = repo.get_status()
            assert status.staged or status.modified or status.untracked
        finally:
            repo.close()
            tmpdir.cleanup()


# =============================================================================
# Discard Completeness Properties
# =============================================================================


class TestDiscardCompletenessProperties:
    """Properties for discard operation completeness."""

    @given(content=safe_content)
    @settings(max_examples=20, deadline=None)
    def test_discard_modified_clears_changes(self, content: str) -> None:
        """Property: after discarding modified file, has_changes() is False."""
        assume(content != "# OAPS")

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Modify tracked file
            readme = repo.root / "README.md"
            readme.write_text(content)

            assert repo.has_changes() is True

            # Discard changes
            result = repo.discard_changes()

            # Should have discarded
            assert result.no_changes is False
            # File should be restored
            assert readme in result.restored
            # Should be clean now
            assert repo.has_changes() is False
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(filename=safe_filename, content=safe_content)
    @settings(max_examples=15, deadline=None)
    def test_discard_specific_file_only_affects_that_file(
        self, filename: str, content: str
    ) -> None:
        """Property: discarding specific file leaves other changes intact."""
        assume(filename not in {".", "..", ".git", "README.md"})
        assume(not filename.startswith("."))
        assume(content != "# OAPS")

        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Modify README and create new file
            readme = repo.root / "README.md"
            readme.write_text(content)

            new_file = repo.root / filename
            new_file.write_text("new file content")

            # Both should show as changes
            assert repo.has_changes() is True
            status = repo.get_status()
            assert readme in status.modified
            assert new_file in status.untracked

            # Discard only the modified file
            result = repo.discard_changes(paths=[readme])

            # README should be restored
            assert readme in result.restored

            # New file should still be untracked
            new_status = repo.get_status()
            assert new_file in new_status.untracked
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(st.data())
    @settings(max_examples=10, deadline=None)
    def test_discard_on_clean_repo_is_noop(self, data: st.DataObject) -> None:
        """Property: discarding on clean repo returns no_changes=True."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            assert repo.has_changes() is False

            result = repo.discard_changes()

            assert result.no_changes is True
            assert result.unstaged == frozenset()
            assert result.restored == frozenset()
        finally:
            repo.close()
            tmpdir.cleanup()


# =============================================================================
# Stateful Machine Test
# =============================================================================


class OapsRepositoryStateMachine(RuleBasedStateMachine):
    """Stateful test for OapsRepository operations.

    Tests that sequences of operations maintain repository invariants.
    """

    def __init__(self) -> None:
        super().__init__()
        self._repo: OapsRepository | None = None
        self._project_dir: Path | None = None
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self._created_files: set[str] = set()
        self._pending_changes: bool = False

    @initialize()
    def init_repo(self) -> None:
        """Initialize repository state."""
        self._tmpdir = tempfile.TemporaryDirectory()
        self._project_dir = Path(self._tmpdir.name)
        oaps_dir = self._project_dir / ".oaps"
        oaps_dir.mkdir()

        # Initialize git repository with initial commit using system git
        _init_git_repo(oaps_dir)

        self._repo = OapsRepository(working_dir=self._project_dir)
        self._created_files = set()
        self._pending_changes = False

    def teardown(self) -> None:
        """Cleanup after tests."""
        if self._repo is not None:
            self._repo.close()
        if self._tmpdir is not None:
            self._tmpdir.cleanup()

    @rule(filename=safe_filename, content=safe_content)
    def create_file(self, filename: str, content: str) -> None:
        """Create a file and verify it appears in status."""
        assume(filename not in {".", "..", ".git", "README.md"})
        assume(not filename.startswith("."))
        assume(filename not in self._created_files)
        assert self._repo is not None  # For type narrowing

        new_file = self._repo.root / filename
        new_file.write_text(content)
        self._created_files.add(filename)
        self._pending_changes = True

        # Verify file appears in status
        status = self._repo.get_status()
        assert new_file in status.untracked or new_file in status.staged

    @rule()
    @precondition(lambda self: self._pending_changes)
    def commit_pending(self) -> None:
        """Commit pending changes and verify clean state."""
        assert self._repo is not None  # For type narrowing

        result = self._repo.commit_pending("Commit changes")

        if result.no_changes:
            # No changes - that's valid if everything was already committed
            pass
        else:
            # Changes were committed
            assert result.sha is not None
            assert len(result.files) > 0

        # After commit, check if still has changes
        self._pending_changes = self._repo.has_changes()

    @rule()
    @precondition(lambda self: self._pending_changes)
    def discard_changes(self) -> None:
        """Discard tracked changes and verify state."""
        assert self._repo is not None  # For type narrowing

        # Only discard tracked files (modified), not untracked
        status = self._repo.get_status()
        if not status.modified and not status.staged:
            # Only untracked files - discard won't affect them
            return

        result = self._repo.discard_changes()

        # If we had tracked changes, they should be discarded
        if not result.no_changes:
            # Check that modified files are no longer modified
            new_status = self._repo.get_status()
            for path in result.restored:
                assert path not in new_status.modified

    @rule(content=safe_content)
    def modify_readme(self, content: str) -> None:
        """Modify the tracked README file and update pending changes state.

        Note: We don't assert that the file appears in modified because
        if the content matches what's already committed, git won't show
        it as modified. We just update our tracking of pending changes.
        """
        # Skip empty content to avoid edge cases
        assume(content.strip())
        assert self._repo is not None  # For type narrowing

        readme = self._repo.root / "README.md"
        readme.write_text(content)

        # Update pending changes based on actual status
        self._pending_changes = self._repo.has_changes()

    @invariant()
    def status_sets_are_disjoint(self) -> None:
        """Invariant: staged, modified, untracked are always disjoint."""
        if self._repo is None:
            return

        status = self._repo.get_status()
        staged = set(status.staged)
        modified = set(status.modified)
        untracked = set(status.untracked)

        assert staged.isdisjoint(modified), "staged and modified should be disjoint"
        assert staged.isdisjoint(untracked), "staged and untracked should be disjoint"
        assert modified.isdisjoint(untracked), (
            "modified and untracked should be disjoint"
        )

    @invariant()
    def has_changes_consistent_with_status(self) -> None:
        """Invariant: has_changes() is consistent with status contents."""
        if self._repo is None:
            return

        has_changes = self._repo.has_changes()
        status = self._repo.get_status()
        has_status_changes = bool(status.staged or status.modified or status.untracked)

        assert has_changes == has_status_changes, (
            f"has_changes()={has_changes} but status has "
            f"staged={len(status.staged)}, "
            f"modified={len(status.modified)}, "
            f"untracked={len(status.untracked)}"
        )

    @invariant()
    def all_paths_are_valid(self) -> None:
        """Invariant: all status paths are within repository scope."""
        if self._repo is None:
            return

        status = self._repo.get_status()
        all_paths = set(status.staged) | set(status.modified) | set(status.untracked)

        for path in all_paths:
            assert self._repo.validate_path(path), f"Path {path} should be valid"


# Create test case class for pytest discovery with limited examples and deadline
TestOapsRepositoryStateMachine = OapsRepositoryStateMachine.TestCase
TestOapsRepositoryStateMachine.settings = settings(
    max_examples=30,
    stateful_step_count=10,
    deadline=None,  # Disable deadline for I/O-bound tests
)


# =============================================================================
# Stage/Commit Path Validation Properties
# =============================================================================


class TestStagePathValidationProperties:
    """Properties for path validation during staging operations."""

    @given(filename=safe_filename)
    @settings(max_examples=30, deadline=None)
    def test_stage_path_outside_repo_raises(self, filename: str) -> None:
        """Property: staging path outside repo always raises PathViolationError."""
        repo, project_dir, tmpdir = create_oaps_repo()
        try:
            # Create file outside .oaps/
            external_file = project_dir / filename
            external_file.write_text("external content")

            # Staging should raise
            try:
                repo.stage([external_file])
                # If we get here, the test failed
                msg = f"Expected PathViolationError for {external_file}"
                raise AssertionError(msg)
            except OapsRepositoryPathViolationError:
                pass  # Expected
        finally:
            repo.close()
            tmpdir.cleanup()

    @given(attack=traversal_patterns, suffix=safe_filename)
    @settings(max_examples=30, deadline=None)
    def test_stage_traversal_path_raises(self, attack: str, suffix: str) -> None:
        """Property: staging path with traversal attack raises error."""
        repo, _project_dir, tmpdir = create_oaps_repo()
        try:
            # Build attack path
            attack_path = repo.root / attack / suffix

            # Check if this actually escapes
            try:
                resolved = attack_path.resolve()
                if not resolved.is_relative_to(repo.root):
                    # This escapes - should raise
                    try:
                        repo.stage([attack_path])
                        msg = f"Expected PathViolationError for {attack_path}"
                        raise AssertionError(msg)
                    except OapsRepositoryPathViolationError:
                        pass  # Expected
            except (OSError, ValueError):
                pass  # Invalid path, can't test
        finally:
            repo.close()
            tmpdir.cleanup()
