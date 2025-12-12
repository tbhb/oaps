"""Integration tests for the project command."""

from collections.abc import Callable
from pathlib import Path

import pytest

from oaps.utils import SQLiteStateStore


@pytest.fixture
def project_store(tmp_path: Path) -> SQLiteStateStore:
    """Create a project store for testing with project scope (session_id=None)."""
    db_path = tmp_path / ".oaps" / "state.db"
    db_path.parent.mkdir(parents=True)
    return SQLiteStateStore(db_path, session_id=None)


@pytest.fixture
def project_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    project_store: SQLiteStateStore,  # noqa: ARG001 - Creates store before fixture runs
) -> Path:
    """Set up environment for project commands."""

    # Patch at multiple locations to ensure the function is mocked everywhere
    def mock_state_file() -> Path:
        return tmp_path / ".oaps" / "state.db"

    monkeypatch.setattr("oaps.utils.get_oaps_state_file", mock_state_file)
    monkeypatch.setattr("oaps.utils._paths.get_oaps_state_file", mock_state_file)

    return tmp_path


class TestProjectGet:
    def test_get_existing_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("test-key", "test-value")

        exit_code = oaps_cli_with_exit_code("project", "get", "test-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "test-value" in captured.out

    def test_get_missing_key_exits_with_error(
        self,
        project_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "get", "nonexistent")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_get_verbose_shows_metadata(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("meta-key", "meta-value", author="test-author")

        exit_code = oaps_cli_with_exit_code("project", "get", "meta-key", "--verbose")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "key: meta-key" in captured.out
        assert "value: meta-value" in captured.out
        assert "created_at:" in captured.out
        assert "created_by: test-author" in captured.out
        assert "updated_at:" in captured.out
        assert "updated_by: test-author" in captured.out

    def test_get_null_value(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("null-key", None)

        exit_code = oaps_cli_with_exit_code("project", "get", "null-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "null" in captured.out

    def test_get_integer_value(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("int-key", 42)

        exit_code = oaps_cli_with_exit_code("project", "get", "int-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "42" in captured.out


class TestProjectSet:
    def test_set_new_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "set", "new-key", "new-value")

        assert exit_code == 0
        assert project_store["new-key"] == "new-value"
        captured = capsys.readouterr()
        assert "Set 'new-key'" in captured.out

    def test_set_with_author(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "project", "set", "authored-key", "value", "--author", "test-user"
        )

        assert exit_code == 0
        entry = project_store.get_entry("authored-key")
        assert entry is not None
        assert entry.created_by == "test-user"

    def test_set_updates_existing_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("existing", "old-value")

        exit_code = oaps_cli_with_exit_code("project", "set", "existing", "new-value")

        assert exit_code == 0
        assert project_store["existing"] == "new-value"

    def test_set_detects_integer(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "set", "counter", "42")

        assert exit_code == 0
        assert project_store["counter"] == 42
        assert isinstance(project_store["counter"], int)

    def test_set_detects_negative_integer(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "set", "negative", "-5")

        assert exit_code == 0
        assert project_store["negative"] == -5
        assert isinstance(project_store["negative"], int)

    def test_set_detects_float(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "set", "pi", "3.14")

        assert exit_code == 0
        assert project_store["pi"] == 3.14
        assert isinstance(project_store["pi"], float)

    def test_set_keeps_whole_float_as_float(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "set", "whole", "3.0")

        assert exit_code == 0
        assert project_store["whole"] == 3.0
        assert isinstance(project_store["whole"], float)

    def test_set_string_flag_forces_string(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "project", "set", "str-num", "42", "--string"
        )

        assert exit_code == 0
        assert project_store["str-num"] == "42"
        assert isinstance(project_store["str-num"], str)

    def test_set_integer_then_increment_works(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        oaps_cli_with_exit_code("project", "set", "counter", "10")
        exit_code = oaps_cli_with_exit_code("project", "increment", "counter")

        assert exit_code == 0
        assert project_store["counter"] == 11


class TestProjectDelete:
    def test_delete_existing_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("delete-me", "value")

        exit_code = oaps_cli_with_exit_code("project", "delete", "delete-me")

        assert exit_code == 0
        assert "delete-me" not in project_store
        captured = capsys.readouterr()
        assert "Deleted" in captured.out

    def test_delete_missing_key_exits_with_error(
        self,
        project_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "delete", "nonexistent")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestProjectClear:
    def test_clear_requires_force(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("keep-me", "value")

        exit_code = oaps_cli_with_exit_code("project", "clear")

        assert exit_code == 1
        assert "keep-me" in project_store
        captured = capsys.readouterr()
        assert "--force" in captured.out

    def test_clear_with_force(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("a", 1)
        project_store.set("b", 2)

        exit_code = oaps_cli_with_exit_code("project", "clear", "--force")

        assert exit_code == 0
        assert len(project_store) == 0
        captured = capsys.readouterr()
        assert "Cleared 2 entries" in captured.out

    def test_clear_empty_store(
        self,
        project_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "clear")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "already empty" in captured.out


class TestProjectIncrement:
    def test_increment_new_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "increment", "counter")

        assert exit_code == 0
        assert project_store["counter"] == 1
        captured = capsys.readouterr()
        assert "counter = 1" in captured.out

    def test_increment_existing_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("counter", 10)

        exit_code = oaps_cli_with_exit_code("project", "increment", "counter")

        assert exit_code == 0
        assert project_store["counter"] == 11
        captured = capsys.readouterr()
        assert "counter = 11" in captured.out

    def test_increment_with_amount(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("counter", 5)

        exit_code = oaps_cli_with_exit_code(
            "project", "increment", "counter", "--amount", "10"
        )

        assert exit_code == 0
        assert project_store["counter"] == 15
        captured = capsys.readouterr()
        assert "counter = 15" in captured.out

    def test_increment_non_integer_fails(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("not-int", "string-value")

        exit_code = oaps_cli_with_exit_code("project", "increment", "not-int")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not an integer" in captured.out


class TestProjectDecrement:
    def test_decrement_new_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "decrement", "counter")

        assert exit_code == 0
        assert project_store["counter"] == -1
        captured = capsys.readouterr()
        assert "counter = -1" in captured.out

    def test_decrement_existing_key(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("counter", 10)

        exit_code = oaps_cli_with_exit_code("project", "decrement", "counter")

        assert exit_code == 0
        assert project_store["counter"] == 9
        captured = capsys.readouterr()
        assert "counter = 9" in captured.out

    def test_decrement_with_amount(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("counter", 20)

        exit_code = oaps_cli_with_exit_code(
            "project", "decrement", "counter", "--amount", "5"
        )

        assert exit_code == 0
        assert project_store["counter"] == 15
        captured = capsys.readouterr()
        assert "counter = 15" in captured.out

    def test_decrement_non_integer_fails(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("not-int", "string-value")

        exit_code = oaps_cli_with_exit_code("project", "decrement", "not-int")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not an integer" in captured.out


class TestProjectState:
    def test_state_empty_store(
        self,
        project_env: Path,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("project", "state")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "empty" in captured.out

    def test_state_shows_keys_and_values(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("key1", "value1")
        project_store.set("key2", 42)

        exit_code = oaps_cli_with_exit_code("project", "state")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "key1: value1" in captured.out
        assert "key2: 42" in captured.out

    def test_state_verbose_shows_metadata(
        self,
        project_env: Path,
        project_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        project_store.set("key1", "value1", author="author1")
        project_store.set("key2", "value2", author="author2")

        exit_code = oaps_cli_with_exit_code("project", "state", "--verbose")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "key: key1" in captured.out
        assert "value: value1" in captured.out
        assert "created_by: author1" in captured.out
        assert "---" in captured.out  # Separator between entries
