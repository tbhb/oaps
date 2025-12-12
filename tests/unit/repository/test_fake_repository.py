"""Consumer tests for FakeRepository."""

from datetime import UTC, datetime
from pathlib import Path

from oaps.repository import BlameLine, CommitInfo, FakeRepository, RepositoryProtocol

# =============================================================================
# Protocol Conformance Tests
# =============================================================================


class TestFakeRepositoryProtocolConformance:
    def test_isinstance_repository_protocol_returns_true(self) -> None:
        assert isinstance(FakeRepository(), RepositoryProtocol) is True

    def test_has_root_property(self) -> None:
        repo = FakeRepository()
        assert isinstance(repo.root, Path)
        assert repo.root == Path("/fake/project")


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestFakeRepositoryContextManager:
    def test_enter_returns_self(self) -> None:
        repo = FakeRepository()
        with repo as ctx:
            assert ctx is repo

    def test_works_as_context_manager(self) -> None:
        with FakeRepository() as repo:
            _ = repo.has_changes()

    def test_close_is_noop(self) -> None:
        repo = FakeRepository()
        repo.close()


# =============================================================================
# has_changes Tests
# =============================================================================


class TestFakeRepositoryHasChanges:
    def test_returns_false_when_no_changes(self) -> None:
        repo = FakeRepository()
        assert repo.has_changes() is False

    def test_returns_true_when_staged_not_empty(self) -> None:
        repo = FakeRepository()
        repo.staged.add(Path("/fake/project/file.py"))
        assert repo.has_changes() is True

    def test_returns_true_when_modified_not_empty(self) -> None:
        repo = FakeRepository()
        repo.modified.add(Path("/fake/project/file.py"))
        assert repo.has_changes() is True

    def test_returns_true_when_untracked_not_empty(self) -> None:
        repo = FakeRepository()
        repo.untracked.add(Path("/fake/project/file.py"))
        assert repo.has_changes() is True


# =============================================================================
# commit Tests
# =============================================================================


class TestFakeRepositoryCommit:
    def test_returns_no_changes_when_nothing_staged(self) -> None:
        repo = FakeRepository()
        result = repo.commit("Test commit")
        assert result.no_changes is True
        assert result.sha is None
        assert result.files == frozenset()

    def test_commits_staged_files_and_returns_result(self) -> None:
        repo = FakeRepository()
        file_path = Path("/fake/project/file.py")
        repo.staged.add(file_path)

        result = repo.commit("Test commit")

        assert result.no_changes is False
        assert result.sha is not None
        assert file_path in result.files

    def test_clears_staged_after_commit(self) -> None:
        repo = FakeRepository()
        file_path = Path("/fake/project/file.py")
        repo.staged.add(file_path)

        repo.commit("Test commit")

        assert len(repo.staged) == 0

    def test_generates_sequential_sha(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        result1 = repo.commit("First commit")

        repo.staged.add(Path("/fake/project/file2.py"))
        result2 = repo.commit("Second commit")

        assert result1.sha == "fake00000001"
        assert result2.sha == "fake00000002"

    def test_adds_commit_to_history(self) -> None:
        repo = FakeRepository()
        file_path = Path("/fake/project/file.py")
        repo.staged.add(file_path)

        repo.commit("Test commit message")

        assert len(repo.commits) == 1
        assert repo.commits[0].message == "Test commit message"
        assert repo.commits[0].sha == "fake00000001"

    def test_commit_has_correct_parent(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("First commit")

        repo.staged.add(Path("/fake/project/file2.py"))
        repo.commit("Second commit")

        assert repo.commits[0].parent_shas == ("fake00000001",)
        assert repo.commits[1].parent_shas == ()


# =============================================================================
# get_log Tests
# =============================================================================


class TestFakeRepositoryGetLog:
    def test_returns_empty_list_when_no_commits(self) -> None:
        repo = FakeRepository()
        assert repo.get_log() == []

    def test_returns_commits_in_reverse_chronological_order(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("First commit")
        repo.staged.add(Path("/fake/project/file2.py"))
        repo.commit("Second commit")
        repo.staged.add(Path("/fake/project/file3.py"))
        repo.commit("Third commit")

        log = repo.get_log()

        assert len(log) == 3
        assert log[0].message == "Third commit"
        assert log[1].message == "Second commit"
        assert log[2].message == "First commit"

    def test_respects_n_limit(self) -> None:
        repo = FakeRepository()

        for i in range(5):
            repo.staged.add(Path(f"/fake/project/file{i}.py"))
            repo.commit(f"Commit {i}")

        log = repo.get_log(n=2)

        assert len(log) == 2
        assert log[0].message == "Commit 4"
        assert log[1].message == "Commit 3"

    def test_filters_by_grep_case_insensitive(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("Add feature X")
        repo.staged.add(Path("/fake/project/file2.py"))
        repo.commit("Fix bug in feature Y")
        repo.staged.add(Path("/fake/project/file3.py"))
        repo.commit("Update documentation")

        log = repo.get_log(grep="FEATURE")

        assert len(log) == 2
        assert log[0].message == "Fix bug in feature Y"
        assert log[1].message == "Add feature X"

    def test_filters_by_author_name(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("Test commit")

        log_match = repo.get_log(author="Fake")
        log_no_match = repo.get_log(author="Unknown")

        assert len(log_match) == 1
        assert len(log_no_match) == 0

    def test_filters_by_author_email(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("Test commit")

        log_match = repo.get_log(author="fake@example.com")
        log_no_match = repo.get_log(author="other@example.com")

        assert len(log_match) == 1
        assert len(log_no_match) == 0

    def test_combines_grep_and_author_filters(self) -> None:
        repo = FakeRepository()

        repo.staged.add(Path("/fake/project/file1.py"))
        repo.commit("Add feature")
        repo.staged.add(Path("/fake/project/file2.py"))
        repo.commit("Fix bug")

        log = repo.get_log(grep="feature", author="Fake")

        assert len(log) == 1
        assert log[0].message == "Add feature"


# =============================================================================
# Helper Methods Tests
# =============================================================================


class TestFakeRepositoryHelperMethods:
    def test_set_diff_configures_get_diff_return(self) -> None:
        repo = FakeRepository()
        diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"

        repo.set_diff(diff_content)

        assert repo.get_diff() == diff_content

    def test_set_blame_configures_get_blame_for_path(self) -> None:
        repo = FakeRepository()
        file_path = Path("/fake/project/file.py")
        blame_lines = [
            BlameLine(
                line_no=1,
                content="print('hello')",
                sha="abc123" * 7 + "ab",
                author_name="Test Author",
                author_email="test@example.com",
                timestamp=datetime.now(UTC),
            )
        ]

        repo.set_blame(file_path, blame_lines)

        result = repo.get_blame(file_path)
        assert len(result) == 1
        assert result[0].content == "print('hello')"

    def test_get_blame_returns_empty_for_unconfigured_path(self) -> None:
        repo = FakeRepository()
        result = repo.get_blame(Path("/fake/project/unknown.py"))
        assert result == []

    def test_set_file_at_commit_configures_get_file_at_commit(self) -> None:
        repo = FakeRepository()
        file_path = Path("/fake/project/file.py")
        commit_sha = "fake00000001"
        content = b"original content"

        repo.set_file_at_commit(file_path, commit_sha, content)

        result = repo.get_file_at_commit(file_path, commit_sha)
        assert result == content

    def test_get_file_at_commit_returns_none_for_unconfigured(self) -> None:
        repo = FakeRepository()
        result = repo.get_file_at_commit(Path("/fake/project/file.py"), "fake00000001")
        assert result is None


# =============================================================================
# Consumer Pattern Tests
# =============================================================================


class TestFakeRepositoryConsumerPattern:
    def test_injection_via_protocol_type_hint(self) -> None:
        def save_changes(repo: RepositoryProtocol, message: str) -> str | None:
            if repo.has_changes():
                staged = repo.stage(repo.get_uncommitted_files())
                if staged:
                    result = repo.commit(message, staged_paths=staged)
                    return result.sha
            return None

        fake_repo = FakeRepository()
        fake_repo.modified.add(Path("/fake/project/src/main.py"))

        sha = save_changes(fake_repo, "Auto-save")

        assert sha is not None
        assert sha.startswith("fake")

    def test_setup_for_specific_test_scenario(self) -> None:
        repo = FakeRepository()

        repo.commits.append(
            CommitInfo(
                sha="existing00001",
                message="Initial commit",
                author_name="Original Author",
                author_email="original@example.com",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                files_changed=3,
                parent_shas=(),
            )
        )

        repo.modified.add(Path("/fake/project/src/feature.py"))
        repo.untracked.add(Path("/fake/project/tests/test_feature.py"))

        diff_content = """\
diff --git a/src/feature.py b/src/feature.py
--- a/src/feature.py
+++ b/src/feature.py
@@ -1 +1,2 @@
 existing
+new line
"""
        repo.set_diff(diff_content)

        assert repo.has_changes() is True
        assert len(repo.get_uncommitted_files()) == 2
        assert repo.get_diff() != ""
        assert len(repo.get_log()) == 1
        assert repo.get_log()[0].author_name == "Original Author"
