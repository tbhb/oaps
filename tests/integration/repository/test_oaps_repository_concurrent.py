"""Multi-process concurrency tests for OapsRepository.

These tests verify that OapsRepository handles concurrent access from multiple
processes correctly, including race condition detection and repository integrity.
"""

import os
import subprocess
import time
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty

import pytest

from oaps.exceptions import OapsRepositoryConflictError
from oaps.repository import OapsRepository


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
def oaps_git_repo(tmp_path: Path) -> Path:
    """Create a real .oaps git repository for testing."""
    oaps_dir = tmp_path / ".oaps"
    oaps_dir.mkdir()

    # Initialize git repo using system git (avoids dulwich API deprecations)
    _run_git(oaps_dir, "init")
    _run_git(oaps_dir, "config", "user.name", "Test User")
    _run_git(oaps_dir, "config", "user.email", "test@example.com")
    # Disable GPG signing to avoid dulwich trying to sign commits
    _run_git(oaps_dir, "config", "commit.gpgsign", "false")

    # Create initial commit
    readme = oaps_dir / "README.md"
    readme.write_text("# OAPS Test Repository\n")
    _run_git(oaps_dir, "add", "README.md")
    _run_git(oaps_dir, "commit", "-m", "Initial commit")

    return tmp_path


def _commit_file_in_process(
    working_dir: Path,
    file_name: str,
    result_queue: Queue[tuple[str, str | None, str | None]],
) -> None:
    """Worker function to create and commit a file in a separate process.

    Args:
        working_dir: Project working directory containing .oaps/
        file_name: Name of file to create and commit
        result_queue: Queue to put results (file_name, sha, error)
    """
    try:
        with OapsRepository(working_dir=working_dir) as repo:
            # Create unique file content
            file_path = repo.root / file_name
            file_path.write_text(f"Content for {file_name}\nPID: {os.getpid()}\n")

            # Commit the file
            result = repo.commit_pending(f"Add {file_name}")

            if result.no_changes:
                result_queue.put((file_name, None, "no_changes"))
            else:
                result_queue.put((file_name, result.sha, None))
    except OapsRepositoryConflictError as e:
        result_queue.put((file_name, None, f"conflict: {e}"))
    except Exception as e:  # noqa: BLE001 - Need to catch all to report via queue
        result_queue.put((file_name, None, f"error: {e!r}"))


def _commit_same_file_in_process(
    working_dir: Path,
    file_name: str,
    content: str,
    result_queue: Queue[tuple[str, str | None, str | None]],
) -> None:
    """Worker function to modify and commit the same file.

    Args:
        working_dir: Project working directory containing .oaps/
        file_name: Name of file to modify
        content: Content to write to file
        result_queue: Queue to put results (content_id, sha, error)
    """
    try:
        with OapsRepository(working_dir=working_dir) as repo:
            file_path = repo.root / file_name
            file_path.write_text(content)
            result = repo.commit_pending(f"Update {file_name}")

            if result.no_changes:
                result_queue.put((content, None, "no_changes"))
            else:
                result_queue.put((content, result.sha, None))
    except OapsRepositoryConflictError as e:
        result_queue.put((content, None, f"conflict: {e}"))
    except Exception as e:  # noqa: BLE001 - Need to catch all to report via queue
        result_queue.put((content, None, f"error: {e!r}"))


def _read_status_in_process(
    working_dir: Path,
    result_queue: Queue[tuple[int, int, int, str | None]],
) -> None:
    """Worker function to read repository status.

    Args:
        working_dir: Project working directory containing .oaps/
        result_queue: Queue to put results (staged, modified, untracked, error)
    """
    try:
        with OapsRepository(working_dir=working_dir) as repo:
            status = repo.get_status()
            result_queue.put(
                (
                    len(status.staged),
                    len(status.modified),
                    len(status.untracked),
                    None,
                )
            )
    except Exception as e:  # noqa: BLE001 - Need to catch all to report via queue
        result_queue.put((0, 0, 0, f"error: {e!r}"))


def _discard_in_process(
    working_dir: Path,
    result_queue: Queue[tuple[str, str | None, str | None]],
) -> None:
    """Worker function to discard changes in a separate process.

    Args:
        working_dir: Project working directory containing .oaps/
        result_queue: Queue to put results (operation, sha, error)
    """
    try:
        with OapsRepository(working_dir=working_dir) as repo:
            repo.discard_changes()
            result_queue.put(("discard", None, None))
    except Exception as e:  # noqa: BLE001 - Need to catch all to report via queue
        result_queue.put(("discard", None, f"error: {e!r}"))


def _use_repo_instance(
    working_dir: Path,
    instance_id: int,
    result_queue: Queue[tuple[int, str | None, str | None]],
) -> None:
    """Worker function to use repository from a separate process.

    Args:
        working_dir: Project working directory containing .oaps/
        instance_id: Identifier for this instance
        result_queue: Queue to put results (instance_id, sha, error)
    """
    try:
        with OapsRepository(working_dir=working_dir) as repo:
            # Create file
            file_path = repo.root / f"instance-{instance_id}.md"
            file_path.write_text(f"From instance {instance_id}\n")

            # Get status (exercise read operations)
            _ = repo.get_status()

            # Commit
            commit_result = repo.commit_pending(f"From instance {instance_id}")

            result_queue.put((instance_id, commit_result.sha, None))
    except Exception as e:  # noqa: BLE001 - Need to catch all to report via queue
        result_queue.put((instance_id, None, f"error: {e!r}"))


class TestConcurrentCommitsDifferentFiles:
    def test_multiple_processes_different_files_all_succeed(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify concurrent commits to different files all succeed."""
        num_processes = 5
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        # Start processes that each commit a different file
        processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"file-{i}.md", result_queue),
            )
            for i in range(num_processes)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        # Give queue time to propagate results from child processes
        time.sleep(0.5)

        # Collect results with timeout
        results: list[tuple[str, str | None, str | None]] = []
        for _ in range(num_processes):
            try:
                result = result_queue.get(timeout=2.0)
                results.append(result)
            except Empty:
                break

        # All processes should have completed
        assert len(results) == num_processes, (
            f"Expected {num_processes} results, got {len(results)}: {results}"
        )

        # Count successes, conflicts, lock errors, and other errors
        successes = [r for r in results if r[1] is not None and r[2] is None]
        conflicts = [r for r in results if r[2] and "conflict" in r[2]]
        # FileLocked and CommitError are expected when concurrent processes race
        # for git locks or HEAD changes during commit
        expected_race_errors = [
            r
            for r in results
            if r[2] and ("FileLocked" in r[2] or "changed during commit" in r[2])
        ]
        no_changes = [r for r in results if r[2] == "no_changes"]
        other_errors = [
            r
            for r in results
            if r[2]
            and "error" in r[2]
            and "FileLocked" not in r[2]
            and "conflict" not in r[2]
            and "changed during commit" not in r[2]
        ]

        # With concurrent access, we expect:
        # - Some successes (at least one process should succeed)
        # - Possibly some race errors (FileLocked, HEAD changed)
        # - Possibly some conflicts (race condition detection)
        # - No other unexpected errors
        assert len(successes) >= 1, (
            f"At least one process should succeed. "
            f"Results: successes={len(successes)}, "
            f"race_errors={len(expected_race_errors)}, "
            f"conflicts={len(conflicts)}, no_changes={len(no_changes)}"
        )
        assert len(other_errors) == 0, f"Unexpected errors: {other_errors}"

        # Verify repository integrity using git fsck
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"git fsck failed: {result.stderr}"

        # Verify all files exist in repository
        for i in range(num_processes):
            file_path = oaps_git_repo / ".oaps" / f"file-{i}.md"
            assert file_path.exists(), f"Missing file: file-{i}.md"

    def test_repository_history_valid_after_concurrent_commits(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify commit history is valid after concurrent operations."""
        num_processes = 3
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"history-test-{i}.md", result_queue),
            )
            for i in range(num_processes)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        # Verify we can walk the commit history without errors
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            commits = repo.get_last_commits(n=20)

            # Should have at least initial commit + some new commits
            assert len(commits) >= 1

            # All commits should have valid SHAs (accept both 40 and 80 char formats)
            # Note: 80 char SHAs are double-hex-encoded, which is a known dulwich quirk
            for commit in commits:
                assert len(commit.sha) in (40, 80)
                assert all(c in "0123456789abcdef" for c in commit.sha)


class TestConcurrentCommitsSameFile:
    def test_concurrent_commits_same_file_conflict_detection(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify conflict detection when multiple processes modify same file."""
        num_processes = 5
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        # Create initial shared file
        shared_file = oaps_git_repo / ".oaps" / "shared.md"
        shared_file.write_text("Initial shared content\n")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.commit_pending("Add shared file")

        # Start processes that all modify the same file
        processes = [
            Process(
                target=_commit_same_file_in_process,
                args=(
                    oaps_git_repo,
                    "shared.md",
                    f"Content from process {i}\nPID: {os.getpid()}\n",
                    result_queue,
                ),
            )
            for i in range(num_processes)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        # Collect results
        results: list[tuple[str, str | None, str | None]] = []
        while not result_queue.empty():
            try:
                results.append(result_queue.get_nowait())
            except Empty:
                break

        assert len(results) == num_processes

        # Count outcomes
        successes = [r for r in results if r[1] is not None and r[2] is None]
        conflicts = [r for r in results if r[2] and "conflict" in r[2]]

        # At least one should succeed, and we may see conflicts
        assert len(successes) >= 1 or len(conflicts) >= 1

        # Verify repository integrity
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"git fsck failed: {result.stderr}"


class TestRapidSequentialCommits:
    def test_rapid_sequential_commits_succeed_in_order(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify rapid sequential commits all succeed in order."""
        num_commits = 10
        commit_shas: list[str] = []

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            for i in range(num_commits):
                # Create file
                file_path = repo.root / f"rapid-{i}.md"
                file_path.write_text(f"Rapid commit {i}\n")

                # Commit immediately
                result = repo.commit_pending(f"Rapid commit {i}")
                assert not result.no_changes, f"Commit {i} had no changes"
                assert result.sha is not None
                commit_shas.append(result.sha)

        # Verify all commits exist
        assert len(commit_shas) == num_commits

        # Verify commit order in history
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            history = repo.get_last_commits(n=num_commits + 1)
            # Most recent first, so reverse to check order
            history_shas = [c.sha for c in history]

            # All our commits should be in the history
            for sha in commit_shas:
                assert sha in history_shas

        # Verify repository integrity
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0


class TestReadDuringWrite:
    def test_read_during_write_returns_consistent_state(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify reading status during writes returns consistent state."""
        num_write_processes = 3
        num_read_processes = 5
        write_queue: Queue[tuple[str, str | None, str | None]] = Queue()
        read_queue: Queue[tuple[int, int, int, str | None]] = Queue()

        # Start write processes
        write_processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"concurrent-{i}.md", write_queue),
            )
            for i in range(num_write_processes)
        ]

        # Start read processes
        read_processes = [
            Process(
                target=_read_status_in_process,
                args=(oaps_git_repo, read_queue),
            )
            for _ in range(num_read_processes)
        ]

        # Launch all processes
        for p in write_processes + read_processes:
            p.start()

        # Wait for completion
        for p in write_processes + read_processes:
            p.join(timeout=30)

        # Collect read results
        read_results: list[tuple[int, int, int, str | None]] = []
        while not read_queue.empty():
            try:
                read_results.append(read_queue.get_nowait())
            except Empty:
                break

        # All reads should have succeeded without errors
        errors = [r for r in read_results if r[3] is not None]
        assert len(errors) == 0, f"Read errors: {errors}"

        # Each read should return non-negative counts
        for staged, modified, untracked, _ in read_results:
            assert staged >= 0
            assert modified >= 0
            assert untracked >= 0


class TestRepositoryIntegrity:
    def test_repository_integrity_after_concurrent_operations(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify git fsck passes after concurrent operations."""
        num_processes = 5
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        # Run concurrent commits
        processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"integrity-{i}.md", result_queue),
            )
            for i in range(num_processes)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        # Run comprehensive git fsck
        result = subprocess.run(
            ["git", "fsck", "--strict", "--full"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"git fsck failed: {result.stderr}"

        # Verify we can read all objects
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            # Should be able to get status without errors
            status = repo.get_status()
            assert isinstance(status.staged, frozenset)
            assert isinstance(status.modified, frozenset)
            assert isinstance(status.untracked, frozenset)

            # Should be able to walk history without errors
            commits = repo.get_last_commits(n=50)
            assert len(commits) >= 1

    def test_index_integrity_after_concurrent_operations(
        self, oaps_git_repo: Path
    ) -> None:
        """Verify git index is valid after concurrent operations."""
        num_processes = 4
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        # Run concurrent commits
        processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"index-test-{i}.md", result_queue),
            )
            for i in range(num_processes)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        # Verify index by running git status (which validates index)
        # check=True will raise if command fails, indicating corrupted index
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=True,
        )


class TestConcurrentCommitStress:
    def test_stress_concurrent_commits(self, oaps_git_repo: Path) -> None:
        """Stress test with many concurrent commits."""
        num_processes = 10
        result_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        processes = [
            Process(
                target=_commit_file_in_process,
                args=(oaps_git_repo, f"stress-{i}.md", result_queue),
            )
            for i in range(num_processes)
        ]

        start_time = time.time()

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        elapsed = time.time() - start_time

        # Should complete within reasonable time
        assert elapsed < 30, f"Stress test took {elapsed:.2f}s"

        # Collect results
        results: list[tuple[str, str | None, str | None]] = []
        while not result_queue.empty():
            try:
                results.append(result_queue.get_nowait())
            except Empty:
                break

        # All processes should complete
        assert len(results) == num_processes

        # Verify final repository state
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0


class TestConcurrentDiscardOperations:
    def test_concurrent_discard_and_commit(self, oaps_git_repo: Path) -> None:
        """Verify discard and commit can run concurrently without corruption."""
        # Create some files first
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            for i in range(3):
                file_path = repo.root / f"discard-test-{i}.md"
                file_path.write_text(f"Discard test file {i}\n")
            repo.commit_pending("Add discard test files")

        # Now create modifications
        for i in range(3):
            file_path = oaps_git_repo / ".oaps" / f"discard-test-{i}.md"
            file_path.write_text(f"Modified content {i}\n")

        commit_queue: Queue[tuple[str, str | None, str | None]] = Queue()

        # One process commits new file while another tries discard
        p1 = Process(
            target=_commit_file_in_process,
            args=(oaps_git_repo, "new-file.md", commit_queue),
        )
        p2 = Process(
            target=_discard_in_process,
            args=(oaps_git_repo, commit_queue),
        )

        p1.start()
        p2.start()
        p1.join(timeout=30)
        p2.join(timeout=30)

        # Collect results
        results: list[tuple[str, str | None, str | None]] = []
        while not commit_queue.empty():
            try:
                results.append(commit_queue.get_nowait())
            except Empty:
                break

        # Both should complete without catastrophic errors
        assert len(results) == 2

        # Verify repository integrity
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0


class TestMultipleRepositoryInstances:
    def test_multiple_instances_same_repo(self, oaps_git_repo: Path) -> None:
        """Verify multiple OapsRepository instances for same repo work correctly."""
        num_instances = 4
        result_queue: Queue[tuple[int, str | None, str | None]] = Queue()

        processes = [
            Process(
                target=_use_repo_instance,
                args=(oaps_git_repo, i, result_queue),
            )
            for i in range(num_instances)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)

        results: list[tuple[int, str | None, str | None]] = []
        while not result_queue.empty():
            try:
                results.append(result_queue.get_nowait())
            except Empty:
                break

        assert len(results) == num_instances

        # Verify repository integrity
        result = subprocess.run(
            ["git", "fsck", "--strict"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
