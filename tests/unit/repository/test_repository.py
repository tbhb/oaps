"""Unit tests for OapsRepository class."""

from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from oaps.exceptions import OapsRepositoryNotInitializedError
from oaps.repository import OapsRepository, OapsRepoStatus

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def oaps_dir(tmp_path: Path) -> Path:
    """Create a mock .oaps directory structure."""
    oaps_path = tmp_path / ".oaps"
    oaps_path.mkdir()
    (oaps_path / ".git").mkdir()
    return oaps_path


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> MagicMock:
    """Create a mock dulwich Repo."""
    mock = MagicMock()
    mocker.patch("oaps.repository._base.Repo", return_value=mock)
    return mock


@pytest.fixture
def empty_status(mocker: MockerFixture) -> MagicMock:
    """Create a mock GitStatus with no changes."""
    mock_status = MagicMock()
    mock_status.staged = {"add": [], "delete": [], "modify": []}
    mock_status.unstaged = []
    mock_status.untracked = []
    mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
    return mock_status


class TestOapsRepoStatus:
    def test_frozen_dataclass_is_immutable(self) -> None:
        status = OapsRepoStatus(
            staged=frozenset(),
            modified=frozenset(),
            untracked=frozenset(),
        )
        with pytest.raises(AttributeError):
            status.staged = frozenset([Path("/test")])  # pyright: ignore[reportAttributeAccessIssue]

    def test_contains_path_objects(self) -> None:
        path = Path("/some/path")
        status = OapsRepoStatus(
            staged=frozenset([path]),
            modified=frozenset(),
            untracked=frozenset(),
        )
        assert path in status.staged

    def test_empty_status(self) -> None:
        status = OapsRepoStatus(
            staged=frozenset(),
            modified=frozenset(),
            untracked=frozenset(),
        )
        assert len(status.staged) == 0
        assert len(status.modified) == 0
        assert len(status.untracked) == 0


class TestOapsRepositoryInit:
    def test_raises_error_when_oaps_git_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(OapsRepositoryNotInitializedError) as exc_info:
            OapsRepository(working_dir=tmp_path)

        assert ".oaps/.git not found" in str(exc_info.value)
        assert exc_info.value.path == (tmp_path / ".oaps").resolve()

    def test_raises_error_when_oaps_dir_missing(self, tmp_path: Path) -> None:
        with pytest.raises(OapsRepositoryNotInitializedError):
            OapsRepository(working_dir=tmp_path)

    def test_initializes_with_valid_oaps_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        assert repo.root == oaps_dir.resolve()

    def test_uses_cwd_when_working_dir_none(self, mocker: MockerFixture) -> None:
        mock_cwd = Path("/mock/cwd")
        mocker.patch.object(Path, "cwd", return_value=mock_cwd)
        mock_exists = mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("oaps.repository._base.Repo")

        OapsRepository(working_dir=None)

        mock_exists.assert_called()

    def test_resolves_symlinks(self, tmp_path: Path, mocker: MockerFixture) -> None:
        real_oaps = tmp_path / "real_oaps"
        real_oaps.mkdir()
        (real_oaps / ".git").mkdir()

        symlink_project = tmp_path / "project"
        symlink_project.mkdir()
        oaps_symlink = symlink_project / ".oaps"
        oaps_symlink.symlink_to(real_oaps)

        mocker.patch("oaps.repository._base.Repo", return_value=MagicMock())

        repo = OapsRepository(working_dir=symlink_project)

        assert repo.root == real_oaps.resolve()


class TestOapsRepositoryContextManager:
    def test_context_manager_calls_close(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        with OapsRepository(working_dir=tmp_path) as repo:
            assert repo.root == oaps_dir.resolve()

        mock_repo.close.assert_called_once()

    def test_context_manager_closes_on_exception(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        with (
            pytest.raises(ValueError, match="test error"),
            OapsRepository(working_dir=tmp_path),
        ):
            msg = "test error"
            raise ValueError(msg)

        mock_repo.close.assert_called_once()

    def test_close_releases_resources(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        repo.close()
        mock_repo.close.assert_called_once()


class TestOapsRepositoryRoot:
    def test_returns_resolved_path(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        assert repo.root == oaps_dir.resolve()
        assert repo.root.is_absolute()


class TestOapsRepositoryHasChanges:
    def test_returns_false_when_no_changes(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        assert repo.has_changes() is False

    def test_returns_true_when_staged_files_exist(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"new_file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        assert repo.has_changes() is True

    def test_returns_true_when_modified_files_exist(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        assert repo.has_changes() is True

    def test_returns_true_when_untracked_files_exist(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = [b"untracked.txt"]
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        assert repo.has_changes() is True


class TestOapsRepositoryGetUncommittedFiles:
    def test_returns_empty_set_when_no_changes(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_uncommitted_files()
        assert result == set()

    def test_returns_union_of_all_changes(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"added.txt"], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = [b"untracked.txt"]
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_uncommitted_files()

        expected = {
            oaps_dir.resolve() / "added.txt",
            oaps_dir.resolve() / "modified.txt",
            oaps_dir.resolve() / "untracked.txt",
        }
        assert result == expected


class TestOapsRepositoryGetStatus:
    def test_returns_status_with_staged_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {
            "add": [b"new.txt"],
            "delete": [b"removed.txt"],
            "modify": [b"changed.txt"],
        }
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        status = repo.get_status()

        assert isinstance(status, OapsRepoStatus)
        assert oaps_dir.resolve() / "new.txt" in status.staged
        assert oaps_dir.resolve() / "removed.txt" in status.staged
        assert oaps_dir.resolve() / "changed.txt" in status.staged

    def test_returns_status_with_modified_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified1.txt", b"modified2.txt"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        status = repo.get_status()

        assert len(status.modified) == 2
        assert oaps_dir.resolve() / "modified1.txt" in status.modified

    def test_returns_status_with_untracked_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = [b"new_file.txt"]
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        status = repo.get_status()

        assert len(status.untracked) == 1
        assert oaps_dir.resolve() / "new_file.txt" in status.untracked

    def test_handles_nested_paths(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {
            "add": [b"subdir/nested/file.txt"],
            "delete": [],
            "modify": [],
        }
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)
        status = repo.get_status()

        assert oaps_dir.resolve() / "subdir/nested/file.txt" in status.staged


class TestOapsRepositoryValidatePath:
    def test_returns_true_for_path_inside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        assert repo.validate_path(oaps_dir / "some_file.txt") is True
        assert repo.validate_path(oaps_dir / "subdir" / "nested.txt") is True

    def test_returns_false_for_path_outside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        assert repo.validate_path(tmp_path / "outside.txt") is False
        assert repo.validate_path(Path("/some/other/path")) is False

    def test_resolves_path_before_validation(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        # Using .. to stay within repo should resolve correctly
        path_with_dots = oaps_dir / "subdir" / ".." / "file.txt"
        assert repo.validate_path(path_with_dots) is True

    def test_returns_false_for_parent_traversal_escape(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        # Path that tries to escape using parent traversal
        escape_path = oaps_dir / ".." / "outside.txt"
        assert repo.validate_path(escape_path) is False

    def test_returns_false_for_symlink_pointing_outside(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        # Create a file outside .oaps/
        external_file = tmp_path / "external.txt"
        external_file.touch()

        # Create a symlink inside .oaps/ that points outside
        symlink_inside = oaps_dir / "escape_link"
        symlink_inside.symlink_to(external_file)

        repo = OapsRepository(working_dir=tmp_path)

        # The symlink resolves to outside .oaps/, should return False
        assert repo.validate_path(symlink_inside) is False

    def test_returns_true_for_symlink_pointing_inside(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        # Create a file inside .oaps/
        internal_file = oaps_dir / "internal.txt"
        internal_file.touch()

        # Create a symlink inside .oaps/ that points to another file inside
        symlink_inside = oaps_dir / "internal_link"
        symlink_inside.symlink_to(internal_file)

        repo = OapsRepository(working_dir=tmp_path)

        # The symlink resolves to inside .oaps/, should return True
        assert repo.validate_path(symlink_inside) is True


class TestOapsRepositoryPublicExports:
    def test_exports_available_from_package(self) -> None:
        from oaps.repository import CommitResult, OapsRepository, OapsRepoStatus

        assert OapsRepoStatus is not None
        assert OapsRepository is not None
        assert CommitResult is not None


# =============================================================================
# CommitResult Tests
# =============================================================================


class TestCommitResult:
    def test_frozen_dataclass_is_immutable(self) -> None:
        from oaps.repository import CommitResult

        result = CommitResult(sha="abc123", files=frozenset(), no_changes=False)
        with pytest.raises(AttributeError):
            result.sha = "def456"  # pyright: ignore[reportAttributeAccessIssue]

    def test_no_changes_result(self) -> None:
        from oaps.repository import CommitResult

        result = CommitResult(sha=None, files=frozenset(), no_changes=True)
        assert result.sha is None
        assert result.files == frozenset()
        assert result.no_changes is True

    def test_successful_commit_result(self) -> None:
        from oaps.repository import CommitResult

        files = frozenset([Path("/test/file.txt")])
        result = CommitResult(sha="abc123def456", files=files, no_changes=False)
        assert result.sha == "abc123def456"
        assert result.files == files
        assert result.no_changes is False


# =============================================================================
# Private Helper Method Tests
# =============================================================================


class TestGetHeadSha:
    def test_returns_sha_hex_string(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        mock_repo.head.return_value = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._get_head_sha()

        assert result == "abcdef1234567890" * 2 + "abcdef12"

    def test_returns_none_when_no_commits(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        mock_repo.head.side_effect = KeyError("HEAD")
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._get_head_sha()

        assert result is None


class TestFormatAuthorLine:
    def test_uses_git_config_when_available(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.utils._author import AuthorInfo

        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=AuthorInfo(name="Test User", email="test@example.com"),
        )
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_author_line()

        assert result == b"Test User <test@example.com>"

    def test_uses_default_when_git_config_unavailable(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.utils._author import AuthorInfo

        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=AuthorInfo(name=None, email=None),
        )
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_author_line()

        assert result == b"OAPS <oaps@localhost>"

    def test_uses_partial_defaults(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.utils._author import AuthorInfo

        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=AuthorInfo(name="Test User", email=None),
        )
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_author_line()

        assert result == b"Test User <oaps@localhost>"


class TestFormatOapsCoauthor:
    def test_returns_coauthor_trailer(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_oaps_coauthor()

        assert result == "Co-authored-by: OAPS <oaps@localhost>"


class TestFormatSessionTrailer:
    def test_returns_session_trailer(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_session_trailer("session-abc-123")

        assert result == "OAPS-Session: session-abc-123"


class TestBuildCommitMessage:
    def test_builds_message_without_session(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._build_commit_message("Test commit", session_id=None)

        expected = b"Test commit\n\nCo-authored-by: OAPS <oaps@localhost>"
        assert result == expected

    def test_builds_message_with_session(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._build_commit_message("Test commit", session_id="session-123")

        expected = (
            b"Test commit\n\n"
            b"Co-authored-by: OAPS <oaps@localhost>\n"
            b"OAPS-Session: session-123"
        )
        assert result == expected


class TestFormatCheckpointSubject:
    def test_formats_checkpoint_subject(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._format_checkpoint_subject("spec", "created specification")

        assert result == "oaps(spec): created specification"


class TestToRelativePath:
    def test_converts_path_inside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._to_relative_path(oaps_dir / "some" / "file.txt")

        assert result == "some/file.txt"

    def test_raises_for_path_outside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        from oaps.exceptions import OapsRepositoryPathViolationError

        repo = OapsRepository(working_dir=tmp_path)

        with pytest.raises(OapsRepositoryPathViolationError) as exc_info:
            repo._to_relative_path(tmp_path / "outside.txt")

        assert exc_info.value.path == tmp_path / "outside.txt"
        assert exc_info.value.oaps_root == oaps_dir.resolve()


class TestStageFiles:
    def test_stages_valid_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_add = mocker.patch("oaps.repository._base.porcelain.add")
        repo = OapsRepository(working_dir=tmp_path)
        files = [oaps_dir / "file1.txt", oaps_dir / "file2.txt"]

        result = repo.stage(files)

        assert result == frozenset(files)
        mock_add.assert_called_once()

    def test_raises_for_files_outside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        from oaps.exceptions import OapsRepositoryPathViolationError

        repo = OapsRepository(working_dir=tmp_path)
        files = [oaps_dir / "valid.txt", tmp_path / "outside.txt"]

        with pytest.raises(OapsRepositoryPathViolationError):
            repo.stage(files)

    def test_returns_empty_for_empty_input(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_add = mocker.patch("oaps.repository._base.porcelain.add")
        repo = OapsRepository(working_dir=tmp_path)

        result = repo.stage([])

        assert result == frozenset()
        mock_add.assert_not_called()


class TestStagePending:
    def test_stages_uncommitted_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = [b"new.txt"]
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mock_add = mocker.patch("oaps.repository._base.porcelain.add")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._stage_pending()

        assert len(result) == 2
        mock_add.assert_called_once()

    def test_returns_empty_when_no_changes(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_add = mocker.patch("oaps.repository._base.porcelain.add")
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._stage_pending()

        assert result == frozenset()
        mock_add.assert_not_called()


class TestPerformCommit:
    def test_commits_with_race_detection(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock the commit object with expected parent
        mock_commit = MagicMock()
        mock_commit.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        staged_files = frozenset([oaps_dir / "file.txt"])
        result = repo._perform_commit(b"Test message", staged_files)

        assert result.sha == commit_sha.hex()
        assert result.files == staged_files
        assert result.no_changes is False

    def test_returns_no_changes_when_nothing_staged(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo._perform_commit(b"Test message", frozenset())

        assert result.sha is None
        assert result.no_changes is True

    def test_raises_on_race_condition(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.exceptions import OapsRepositoryConflictError

        head_before = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        different_parent = bytes.fromhex("9999999999999999" * 2 + "99999999")
        mock_repo.head.return_value = head_before
        # Mock commit with wrong parent (indicates race condition)
        mock_commit = MagicMock()
        mock_commit.parents = [different_parent]
        mock_repo.__getitem__.return_value = mock_commit
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)

        with pytest.raises(OapsRepositoryConflictError) as exc_info:
            repo._perform_commit(b"Test message", frozenset([oaps_dir / "file.txt"]))

        assert "Concurrent modification detected" in str(exc_info.value)
        assert "expected parent" in str(exc_info.value)


# =============================================================================
# Public Commit Method Tests
# =============================================================================


class TestCommitPending:
    def test_commits_all_pending_changes(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock commit object with expected parent
        mock_commit = MagicMock()
        mock_commit.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit

        # First status call for _stage_pending shows uncommitted files
        # Second status call for _perform_commit shows staged files
        mock_status_uncommitted = MagicMock()
        mock_status_uncommitted.staged = {"add": [], "delete": [], "modify": []}
        mock_status_uncommitted.unstaged = [b"modified.txt"]
        mock_status_uncommitted.untracked = []

        mock_status_staged = MagicMock()
        mock_status_staged.staged = {
            "add": [b"modified.txt"],
            "delete": [],
            "modify": [],
        }
        mock_status_staged.unstaged = []
        mock_status_staged.untracked = []

        mocker.patch(
            "oaps.repository._base.porcelain.status",
            side_effect=[mock_status_uncommitted, mock_status_staged],
        )
        mocker.patch("oaps.repository._base.porcelain.add")
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.commit_pending("Test commit")

        assert result.sha == commit_sha.hex()
        assert result.no_changes is False

    def test_returns_no_changes_when_nothing_pending(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo.commit_pending("Test commit")

        assert result.sha is None
        assert result.no_changes is True

    def test_includes_session_id_in_message(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock commit object with expected parent
        mock_commit_obj = MagicMock()
        mock_commit_obj.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit_obj

        mock_status_uncommitted = MagicMock()
        mock_status_uncommitted.staged = {"add": [], "delete": [], "modify": []}
        mock_status_uncommitted.unstaged = [b"modified.txt"]
        mock_status_uncommitted.untracked = []

        mock_status_staged = MagicMock()
        mock_status_staged.staged = {
            "add": [b"modified.txt"],
            "delete": [],
            "modify": [],
        }
        mock_status_staged.unstaged = []
        mock_status_staged.untracked = []

        mocker.patch(
            "oaps.repository._base.porcelain.status",
            side_effect=[mock_status_uncommitted, mock_status_staged],
        )
        mocker.patch("oaps.repository._base.porcelain.add")
        mock_commit = mocker.patch(
            "oaps.repository._base.porcelain.commit", return_value=commit_sha
        )
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        repo.commit_pending("Test commit", session_id="session-123")

        # Check that session trailer is in the commit message
        call_args = mock_commit.call_args
        message = call_args.kwargs["message"]
        assert b"OAPS-Session: session-123" in message


class TestCommitFiles:
    def test_commits_specific_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock commit object with expected parent
        mock_commit = MagicMock()
        mock_commit.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit

        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []

        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch("oaps.repository._base.porcelain.add")
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        files = [oaps_dir / "file.txt"]
        result = repo.commit_files(files, "Test commit")

        assert result.sha == commit_sha.hex()
        assert result.no_changes is False

    def test_raises_for_files_outside_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        from oaps.exceptions import OapsRepositoryPathViolationError

        repo = OapsRepository(working_dir=tmp_path)
        files = [tmp_path / "outside.txt"]

        with pytest.raises(OapsRepositoryPathViolationError):
            repo.commit_files(files, "Test commit")

    def test_returns_no_changes_for_empty_file_list(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("oaps.repository._base.porcelain.add")
        repo = OapsRepository(working_dir=tmp_path)

        result = repo.commit_files([], "Test commit")

        assert result.sha is None
        assert result.no_changes is True


class TestCheckpoint:
    def test_creates_checkpoint_with_formatted_message(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock commit object with expected parent
        mock_commit_obj = MagicMock()
        mock_commit_obj.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit_obj

        mock_status_uncommitted = MagicMock()
        mock_status_uncommitted.staged = {"add": [], "delete": [], "modify": []}
        mock_status_uncommitted.unstaged = [b"spec.md"]
        mock_status_uncommitted.untracked = []

        mock_status_staged = MagicMock()
        mock_status_staged.staged = {"add": [b"spec.md"], "delete": [], "modify": []}
        mock_status_staged.unstaged = []
        mock_status_staged.untracked = []

        mocker.patch(
            "oaps.repository._base.porcelain.status",
            side_effect=[mock_status_uncommitted, mock_status_staged],
        )
        mocker.patch("oaps.repository._base.porcelain.add")
        mock_commit = mocker.patch(
            "oaps.repository._base.porcelain.commit", return_value=commit_sha
        )
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.checkpoint("spec", "created specification")

        assert result.sha == commit_sha.hex()
        # Check that the formatted subject is in the commit message
        call_args = mock_commit.call_args
        message = call_args.kwargs["message"]
        assert b"oaps(spec): created specification" in message

    def test_includes_session_id(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        # Mock commit object with expected parent
        mock_commit_obj = MagicMock()
        mock_commit_obj.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit_obj

        mock_status_uncommitted = MagicMock()
        mock_status_uncommitted.staged = {"add": [], "delete": [], "modify": []}
        mock_status_uncommitted.unstaged = [b"spec.md"]
        mock_status_uncommitted.untracked = []

        mock_status_staged = MagicMock()
        mock_status_staged.staged = {"add": [b"spec.md"], "delete": [], "modify": []}
        mock_status_staged.unstaged = []
        mock_status_staged.untracked = []

        mocker.patch(
            "oaps.repository._base.porcelain.status",
            side_effect=[mock_status_uncommitted, mock_status_staged],
        )
        mocker.patch("oaps.repository._base.porcelain.add")
        mock_commit = mocker.patch(
            "oaps.repository._base.porcelain.commit", return_value=commit_sha
        )
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        repo.checkpoint("spec", "created specification", session_id="session-xyz")

        call_args = mock_commit.call_args
        message = call_args.kwargs["message"]
        assert b"OAPS-Session: session-xyz" in message

    def test_returns_no_changes_when_nothing_to_commit(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)

        result = repo.checkpoint("spec", "no changes")

        assert result.sha is None
        assert result.no_changes is True


# =============================================================================
# CommitInfo Tests
# =============================================================================


class TestCommitInfo:
    def test_frozen_dataclass_is_immutable(self) -> None:
        from datetime import datetime

        from oaps.repository import CommitInfo

        timestamp = datetime.now(tz=UTC)
        info = CommitInfo(
            sha="abc123def456" * 3 + "abcd",
            message="Test commit",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=timestamp,
            files_changed=3,
            parent_shas=("parent1",),
        )
        with pytest.raises(AttributeError):
            info.sha = "new_sha"  # pyright: ignore[reportAttributeAccessIssue]

    def test_initial_commit_has_empty_parent_shas(self) -> None:
        from datetime import datetime

        from oaps.repository import CommitInfo

        timestamp = datetime.now(tz=UTC)
        info = CommitInfo(
            sha="abc123def456" * 3 + "abcd",
            message="Initial commit",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=timestamp,
            files_changed=1,
            parent_shas=(),
        )
        assert info.parent_shas == ()

    def test_commit_with_multiple_parents(self) -> None:
        from datetime import datetime

        from oaps.repository import CommitInfo

        timestamp = datetime.now(tz=UTC)
        info = CommitInfo(
            sha="abc123def456" * 3 + "abcd",
            message="Merge commit",
            author_name="Test User",
            author_email="test@example.com",
            timestamp=timestamp,
            files_changed=5,
            parent_shas=("parent1", "parent2"),
        )
        assert len(info.parent_shas) == 2


# =============================================================================
# DiscardResult Tests
# =============================================================================


class TestDiscardResult:
    def test_frozen_dataclass_is_immutable(self) -> None:
        from oaps.repository import DiscardResult

        result = DiscardResult(
            unstaged=frozenset(),
            restored=frozenset(),
            no_changes=True,
        )
        with pytest.raises(AttributeError):
            result.no_changes = False  # pyright: ignore[reportAttributeAccessIssue]

    def test_no_changes_result(self) -> None:
        from oaps.repository import DiscardResult

        result = DiscardResult(
            unstaged=frozenset(),
            restored=frozenset(),
            no_changes=True,
        )
        assert result.unstaged == frozenset()
        assert result.restored == frozenset()
        assert result.no_changes is True

    def test_with_unstaged_and_restored_files(self) -> None:
        from oaps.repository import DiscardResult

        unstaged = frozenset([Path("/test/staged.txt")])
        restored = frozenset([Path("/test/staged.txt"), Path("/test/modified.txt")])
        result = DiscardResult(
            unstaged=unstaged,
            restored=restored,
            no_changes=False,
        )
        assert result.unstaged == unstaged
        assert result.restored == restored
        assert result.no_changes is False


# =============================================================================
# Private Helper Method Tests for Undo/Recovery
# =============================================================================


class TestGetHeadTree:
    def test_returns_tree_sha(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_repo.__getitem__.return_value = mock_commit

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._get_head_tree()

        assert result == tree_sha

    def test_returns_none_when_no_commits(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        mock_repo.head.side_effect = KeyError("HEAD")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._get_head_tree()

        assert result is None


class TestParseAuthorLine:
    def test_parses_standard_author_format(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        author = b"Test User <test@example.com>"
        author_time = 1700000000
        author_tz = -18000  # UTC-5

        name, email, timestamp = repo._parse_author_line(author, author_time, author_tz)

        assert name == "Test User"
        assert email == "test@example.com"
        assert timestamp.year == 2023

    def test_handles_author_without_email_brackets(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        author = b"Just A Name"
        author_time = 1700000000
        author_tz = 0

        name, email, _timestamp = repo._parse_author_line(
            author, author_time, author_tz
        )

        assert name == "Just A Name"
        assert email == ""

    def test_handles_timezone_offset(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        author = b"Test User <test@example.com>"
        author_time = 1700000000
        author_tz = 3600  # UTC+1

        _, _, timestamp = repo._parse_author_line(author, author_time, author_tz)

        # Timestamp should have timezone info
        assert timestamp.tzinfo is not None
        assert timestamp.tzinfo != UTC or author_tz == 0


class TestCountFilesChanged:
    def test_counts_files_in_non_initial_commit(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        commit_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        parent_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        tree_sha = bytes.fromhex("aaaaaaaaaaaaaaaa" * 2 + "aaaaaaaa")
        parent_tree_sha = bytes.fromhex("bbbbbbbbbbbbbbbb" * 2 + "bbbbbbbb")

        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_commit.parents = [parent_sha]

        mock_parent_commit = MagicMock()
        mock_parent_commit.tree = parent_tree_sha

        def getitem(sha: bytes) -> MagicMock:
            if sha == commit_sha:
                return mock_commit
            if sha == parent_sha:
                return mock_parent_commit
            return MagicMock()

        mock_repo.__getitem__.side_effect = getitem

        # Mock tree_changes to return 2 changes
        mock_tree_changes = mocker.patch(
            "oaps.repository._base.tree_changes",
            return_value=[MagicMock(), MagicMock()],
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._count_files_changed(commit_sha)

        assert result == 2
        mock_tree_changes.assert_called_once()


# =============================================================================
# Public Change Management Method Tests
# =============================================================================


class TestDiscardChanges:
    def test_returns_no_changes_for_empty_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        mock_repo.head.side_effect = KeyError("HEAD")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.discard_changes()

        assert result.no_changes is True
        assert result.unstaged == frozenset()
        assert result.restored == frozenset()

    def test_returns_no_changes_when_nothing_to_discard(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_repo.__getitem__.return_value = mock_commit

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.discard_changes()

        assert result.no_changes is True

    def test_raises_for_path_outside_repo(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.exceptions import OapsRepositoryPathViolationError

        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_repo.__getitem__.return_value = mock_commit

        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        repo = OapsRepository(working_dir=tmp_path)

        with pytest.raises(OapsRepositoryPathViolationError):
            repo.discard_changes(paths=[tmp_path / "outside.txt"])

    def test_discards_specific_paths(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_repo.__getitem__.return_value = mock_commit

        # Status shows staged file
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        # Mock index and tree operations
        mock_index = MagicMock()
        mock_index.__contains__ = MagicMock(return_value=True)
        mock_repo.open_index.return_value = mock_index

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            side_effect=KeyError("not in tree"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.discard_changes(paths=[oaps_dir / "file.txt"])

        # Should identify the file as staged
        assert oaps_dir.resolve() / "file.txt" in result.unstaged
        assert result.no_changes is False


class TestGetLastCommits:
    def test_returns_empty_list_for_empty_repo(
        self, tmp_path: Path, oaps_dir: Path, mock_repo: MagicMock
    ) -> None:
        mock_repo.head.side_effect = KeyError("HEAD")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_last_commits()

        assert result == []

    def test_returns_commits_in_reverse_chronological_order(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        mock_repo.head.return_value = head_sha

        # Create mock commit
        mock_commit = MagicMock()
        mock_commit.id = head_sha
        mock_commit.author = b"Test User <test@example.com>"
        mock_commit.author_time = 1700000000
        mock_commit.author_timezone = 0
        mock_commit.message = b"Test commit message"
        mock_commit.parents = []
        mock_commit.tree = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

        # Mock walker entry
        mock_entry = MagicMock()
        mock_entry.commit = mock_commit

        mock_repo.get_walker.return_value = [mock_entry]

        # Mock _count_files_changed
        mocker.patch.object(OapsRepository, "_count_files_changed", return_value=1)

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_last_commits(n=1)

        assert len(result) == 1
        assert result[0].sha == head_sha.hex()
        assert result[0].author_name == "Test User"
        assert result[0].author_email == "test@example.com"
        assert result[0].message == "Test commit message"
        assert result[0].parent_shas == ()

    def test_respects_n_parameter(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        mock_repo.head.return_value = head_sha

        # Create 3 mock commits
        commits_data = []
        for i in range(3):
            mock_commit = MagicMock()
            mock_commit.id = bytes.fromhex(f"{i}bcdef1234567890" * 2 + f"{i}bcdef12")
            mock_commit.author = b"Test User <test@example.com>"
            mock_commit.author_time = 1700000000 - i * 3600
            mock_commit.author_timezone = 0
            mock_commit.message = f"Commit {i}".encode()
            mock_commit.parents = []
            mock_commit.tree = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

            mock_entry = MagicMock()
            mock_entry.commit = mock_commit
            commits_data.append(mock_entry)

        mock_repo.get_walker.return_value = commits_data[:2]

        mocker.patch.object(OapsRepository, "_count_files_changed", return_value=1)

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_last_commits(n=2)

        assert len(result) == 2
        mock_repo.get_walker.assert_called_once_with(include=[head_sha], max_entries=2)

    def test_returns_empty_list_for_n_zero(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        mock_repo.head.return_value = head_sha
        mock_repo.get_walker.return_value = []

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.get_last_commits(n=0)

        assert result == []


class TestPublicExportsIncludeNewTypes:
    def test_exports_commit_info_and_discard_result(self) -> None:
        from oaps.repository import CommitInfo, DiscardResult

        assert CommitInfo is not None
        assert DiscardResult is not None


# =============================================================================
# BaseRepository.commit() Tests
# =============================================================================


class TestBaseRepositoryCommit:
    def test_commit_with_none_staged_paths_gets_current_staged(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        mock_repo.head.return_value = head_sha
        mock_commit_obj = MagicMock()
        mock_commit_obj.parents = [head_sha]
        mock_repo.__getitem__.return_value = mock_commit_obj

        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.commit("Test commit", staged_paths=None)

        assert result.sha == commit_sha.hex()
        assert result.no_changes is False

    def test_commit_returns_no_changes_when_nothing_staged(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        empty_status: MagicMock,
    ) -> None:
        repo = OapsRepository(working_dir=tmp_path)
        result = repo.commit("Test commit", staged_paths=None)

        assert result.sha is None
        assert result.no_changes is True


# =============================================================================
# Race Condition Tests for Initial Commit
# =============================================================================


class TestPerformCommitInitialCommitRaceCondition:
    def test_raises_on_initial_commit_race_condition(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from oaps.exceptions import OapsRepositoryConflictError

        commit_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        # HEAD doesn't exist initially (empty repo)
        mock_repo.head.side_effect = KeyError("HEAD")
        # But commit ends up with a parent (race condition - another process
        # committed first)
        unexpected_parent = bytes.fromhex("9999999999999999" * 2 + "99999999")
        mock_commit = MagicMock()
        mock_commit.parents = [unexpected_parent]
        mock_repo.__getitem__.return_value = mock_commit

        mock_status = MagicMock()
        mock_status.staged = {"add": [b"file.txt"], "delete": [], "modify": []}
        mock_status.unstaged = []
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)
        mocker.patch("oaps.repository._base.porcelain.commit", return_value=commit_sha)
        mocker.patch(
            "oaps.repository._base.get_author_info",
            return_value=MagicMock(name="Test", email="test@test.com"),
        )

        repo = OapsRepository(working_dir=tmp_path)

        with pytest.raises(OapsRepositoryConflictError) as exc_info:
            repo._perform_commit(b"Test message", frozenset([oaps_dir / "file.txt"]))

        assert "expected no parent for initial commit" in str(exc_info.value)


# =============================================================================
# Initial Commit File Count Tests
# =============================================================================


class TestCountFilesChangedInitialCommit:
    def test_counts_files_in_initial_commit_flat_tree(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        commit_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_commit.parents = []  # Initial commit

        # Create mock tree with 3 blob files (no subdirectories)
        mock_tree = MagicMock()
        mock_tree.items.return_value = [
            (b"file1.txt", 0o100644, bytes.fromhex("a" * 40)),  # Blob
            (b"file2.txt", 0o100644, bytes.fromhex("b" * 40)),  # Blob
            (b"file3.txt", 0o100644, bytes.fromhex("c" * 40)),  # Blob
        ]

        def getitem(sha: bytes) -> MagicMock:
            if sha == commit_sha:
                return mock_commit
            if sha == tree_sha:
                return mock_tree
            return MagicMock()

        mock_repo.__getitem__.side_effect = getitem

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._count_files_changed(commit_sha)

        assert result == 3

    def test_counts_files_in_initial_commit_nested_tree(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        commit_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        subtree_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")

        mock_commit = MagicMock()
        mock_commit.tree = tree_sha
        mock_commit.parents = []  # Initial commit

        # Create mock tree with 1 blob and 1 subdirectory
        mock_tree = MagicMock()
        mock_tree.items.return_value = [
            (b"file1.txt", 0o100644, bytes.fromhex("a" * 40)),  # Blob
            (b"subdir", 0o040000, subtree_sha),  # Tree (directory)
        ]

        # Create mock subtree with 2 blobs
        mock_subtree = MagicMock()
        mock_subtree.items.return_value = [
            (b"nested1.txt", 0o100644, bytes.fromhex("d" * 40)),  # Blob
            (b"nested2.txt", 0o100644, bytes.fromhex("e" * 40)),  # Blob
        ]

        def getitem(sha: bytes) -> MagicMock:
            if sha == commit_sha:
                return mock_commit
            if sha == tree_sha:
                return mock_tree
            if sha == subtree_sha:
                return mock_subtree
            return MagicMock()

        mock_repo.__getitem__.side_effect = getitem

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._count_files_changed(commit_sha)

        # 1 file in root + 2 files in subdir = 3 total
        assert result == 3


# =============================================================================
# Discard Changes File Restoration Tests
# =============================================================================


class TestDiscardChangesFullRestoration:
    def test_restores_modified_files_from_head(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from dulwich.objects import Blob

        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        blob_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")
        mock_repo.head.return_value = head_sha

        mock_commit = MagicMock()
        mock_commit.tree = tree_sha

        # Create real Blob for testing
        mock_blob = MagicMock(spec=Blob)
        mock_blob.data = b"original content"

        def getitem(sha: bytes) -> MagicMock:
            if sha == head_sha:
                return mock_commit
            if sha == bytes.fromhex(head_sha.hex()):
                return mock_commit
            if sha == blob_sha:
                return mock_blob
            return mock_commit

        mock_repo.__getitem__.side_effect = getitem

        # Status shows modified file
        mock_status = MagicMock()
        mock_status.staged = {"add": [], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        # Mock index operations
        mock_index = MagicMock()
        mock_index.__contains__ = MagicMock(return_value=False)
        mock_repo.open_index.return_value = mock_index

        # Mock tree lookup to return blob info
        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )

        # Create the file in the filesystem for stat() to work
        modified_file = oaps_dir / "modified.txt"
        modified_file.write_text("modified content")

        # Mock build_file_from_blob
        mock_build = mocker.patch("oaps.repository._base.build_file_from_blob")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.discard_changes()

        assert result.no_changes is False
        assert oaps_dir.resolve() / "modified.txt" in result.restored
        mock_build.assert_called_once()

    def test_discard_all_changes_restores_staged_and_modified(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from dulwich.objects import Blob

        head_sha = bytes.fromhex("abcdef1234567890" * 2 + "abcdef12")
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        blob_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")
        mock_repo.head.return_value = head_sha

        mock_commit = MagicMock()
        mock_commit.tree = tree_sha

        mock_blob = MagicMock(spec=Blob)
        mock_blob.data = b"content"

        def getitem(sha: bytes) -> MagicMock:
            if sha == head_sha:
                return mock_commit
            if sha == bytes.fromhex(head_sha.hex()):
                return mock_commit
            if sha == blob_sha:
                return mock_blob
            return mock_commit

        mock_repo.__getitem__.side_effect = getitem

        # Status shows both staged and modified files
        mock_status = MagicMock()
        mock_status.staged = {"add": [b"staged.txt"], "delete": [], "modify": []}
        mock_status.unstaged = [b"modified.txt"]
        mock_status.untracked = []
        mocker.patch("oaps.repository._base.porcelain.status", return_value=mock_status)

        # Mock index
        mock_index = MagicMock()
        mock_index.__contains__ = MagicMock(return_value=True)
        mock_repo.open_index.return_value = mock_index

        # Mock tree lookup
        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )

        # Create files
        staged_file = oaps_dir / "staged.txt"
        staged_file.write_text("staged content")
        modified_file = oaps_dir / "modified.txt"
        modified_file.write_text("modified content")

        # Mock build_file_from_blob
        mocker.patch("oaps.repository._base.build_file_from_blob")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo.discard_changes()

        assert result.no_changes is False
        assert oaps_dir.resolve() / "staged.txt" in result.unstaged
        assert len(result.restored) == 2


# =============================================================================
# _restore_file_from_tree Tests
# =============================================================================


class TestRestoreFileFromTree:
    def test_restore_creates_parent_directories(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        from dulwich.objects import Blob

        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        blob_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")

        mock_blob = MagicMock(spec=Blob)
        mock_blob.data = b"file content"

        mock_repo.__getitem__.return_value = mock_blob

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )
        mock_build = mocker.patch("oaps.repository._base.build_file_from_blob")

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._restore_file_from_tree(tree_sha, "deep/nested/file.txt")

        assert result is True
        mock_build.assert_called_once()
        # Verify parent directory was created
        assert (oaps_dir / "deep" / "nested").exists()

    def test_restore_returns_false_when_file_not_in_tree(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            side_effect=KeyError("not in tree"),
        )

        repo = OapsRepository(working_dir=tmp_path)
        result = repo._restore_file_from_tree(tree_sha, "nonexistent.txt")

        assert result is False


# =============================================================================
# _update_index_from_tree Tests
# =============================================================================


class TestUpdateIndexFromTree:
    def test_updates_index_for_existing_files(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        blob_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")

        mock_blob = MagicMock()
        mock_blob.data = b"file content"
        mock_repo.__getitem__.return_value = mock_blob

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )

        # Create the file so stat() works
        test_file = oaps_dir / "existing.txt"
        test_file.write_text("content")

        mock_index = MagicMock()
        mock_repo.open_index.return_value = mock_index

        repo = OapsRepository(working_dir=tmp_path)
        repo._update_index_from_tree(tree_sha, ["existing.txt"])

        # Verify index entry was set
        mock_index.__setitem__.assert_called_once()
        mock_index.write.assert_called_once()

    def test_removes_from_index_when_file_not_in_tree(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            side_effect=KeyError("not in tree"),
        )

        mock_index = MagicMock()
        mock_index.__contains__ = MagicMock(return_value=True)
        mock_repo.open_index.return_value = mock_index

        repo = OapsRepository(working_dir=tmp_path)
        repo._update_index_from_tree(tree_sha, ["new_file.txt"])

        # Verify file was removed from index
        mock_index.__delitem__.assert_called_once()
        mock_index.write.assert_called_once()

    def test_does_not_update_index_for_nonexistent_file(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")
        blob_sha = bytes.fromhex("aaaa567890abcdef" * 2 + "aaaa5678")

        mock_blob = MagicMock()
        mock_blob.data = b"file content"
        mock_repo.__getitem__.return_value = mock_blob

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            return_value=(0o100644, blob_sha),
        )

        # Don't create the file - it doesn't exist

        mock_index = MagicMock()
        mock_repo.open_index.return_value = mock_index

        repo = OapsRepository(working_dir=tmp_path)
        repo._update_index_from_tree(tree_sha, ["nonexistent.txt"])

        # Verify index entry was NOT set (file doesn't exist)
        mock_index.__setitem__.assert_not_called()
        mock_index.write.assert_called_once()

    def test_skips_index_removal_for_files_not_in_index(
        self,
        tmp_path: Path,
        oaps_dir: Path,
        mock_repo: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        tree_sha = bytes.fromhex("1234567890abcdef" * 2 + "12345678")

        mocker.patch(
            "oaps.repository._base.tree_lookup_path",
            side_effect=KeyError("not in tree"),
        )

        mock_index = MagicMock()
        mock_index.__contains__ = MagicMock(return_value=False)  # Not in index
        mock_repo.open_index.return_value = mock_index

        repo = OapsRepository(working_dir=tmp_path)
        repo._update_index_from_tree(tree_sha, ["not_in_index.txt"])

        # Verify file was NOT removed (wasn't in index)
        mock_index.__delitem__.assert_not_called()
        mock_index.write.assert_called_once()
