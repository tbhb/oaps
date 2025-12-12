"""Integration tests for the session command."""

from collections.abc import Callable
from pathlib import Path

import pytest

from oaps.utils import SQLiteStateStore


@pytest.fixture
def session_store(tmp_path: Path) -> SQLiteStateStore:
    """Create a session store for testing with session scoping."""
    db_path = tmp_path / ".oaps" / "state.db"
    db_path.parent.mkdir(parents=True)
    return SQLiteStateStore(db_path, session_id="test-session")


@pytest.fixture
def session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_store: SQLiteStateStore,  # noqa: ARG001 - Creates store before fixture runs
) -> str:
    """Set up environment for session commands."""
    session_id = "test-session"
    monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)

    # Patch at oaps.utils where the function is actually imported from
    def mock_state_file() -> Path:
        return tmp_path / ".oaps" / "state.db"

    monkeypatch.setattr("oaps.utils.get_oaps_state_file", mock_state_file)

    return session_id


class TestSessionGet:
    def test_get_existing_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("test-key", "test-value")

        exit_code = oaps_cli_with_exit_code("session", "get", "test-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "test-value" in captured.out

    def test_get_missing_key_exits_with_error(
        self,
        session_env: str,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "get", "nonexistent")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_get_verbose_shows_metadata(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("meta-key", "meta-value", author="test-author")

        exit_code = oaps_cli_with_exit_code("session", "get", "meta-key", "--verbose")

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
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("null-key", None)

        exit_code = oaps_cli_with_exit_code("session", "get", "null-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "null" in captured.out

    def test_get_integer_value(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("int-key", 42)

        exit_code = oaps_cli_with_exit_code("session", "get", "int-key")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "42" in captured.out


class TestSessionSet:
    def test_set_new_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "set", "new-key", "new-value")

        assert exit_code == 0
        assert session_store["new-key"] == "new-value"
        captured = capsys.readouterr()
        assert "Set 'new-key'" in captured.out

    def test_set_with_author(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "session", "set", "authored-key", "value", "--author", "test-user"
        )

        assert exit_code == 0
        entry = session_store.get_entry("authored-key")
        assert entry is not None
        assert entry.created_by == "test-user"

    def test_set_updates_existing_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("existing", "old-value")

        exit_code = oaps_cli_with_exit_code("session", "set", "existing", "new-value")

        assert exit_code == 0
        assert session_store["existing"] == "new-value"

    def test_set_detects_integer(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "set", "counter", "42")

        assert exit_code == 0
        assert session_store["counter"] == 42
        assert isinstance(session_store["counter"], int)

    def test_set_detects_negative_integer(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "set", "negative", "-5")

        assert exit_code == 0
        assert session_store["negative"] == -5
        assert isinstance(session_store["negative"], int)

    def test_set_detects_float(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "set", "pi", "3.14")

        assert exit_code == 0
        assert session_store["pi"] == 3.14
        assert isinstance(session_store["pi"], float)

    def test_set_keeps_whole_float_as_float(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "set", "whole", "3.0")

        assert exit_code == 0
        assert session_store["whole"] == 3.0
        assert isinstance(session_store["whole"], float)

    def test_set_string_flag_forces_string(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "session", "set", "str-num", "42", "--string"
        )

        assert exit_code == 0
        assert session_store["str-num"] == "42"
        assert isinstance(session_store["str-num"], str)

    def test_set_integer_then_increment_works(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        oaps_cli_with_exit_code("session", "set", "counter", "10")
        exit_code = oaps_cli_with_exit_code("session", "increment", "counter")

        assert exit_code == 0
        assert session_store["counter"] == 11


class TestSessionDelete:
    def test_delete_existing_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("delete-me", "value")

        exit_code = oaps_cli_with_exit_code("session", "delete", "delete-me")

        assert exit_code == 0
        assert "delete-me" not in session_store
        captured = capsys.readouterr()
        assert "Deleted" in captured.out

    def test_delete_missing_key_exits_with_error(
        self,
        session_env: str,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "delete", "nonexistent")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestSessionClear:
    def test_clear_requires_force(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("keep-me", "value")

        exit_code = oaps_cli_with_exit_code("session", "clear")

        assert exit_code == 1
        assert "keep-me" in session_store
        captured = capsys.readouterr()
        assert "--force" in captured.out

    def test_clear_with_force(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("a", 1)
        session_store.set("b", 2)

        exit_code = oaps_cli_with_exit_code("session", "clear", "--force")

        assert exit_code == 0
        assert len(session_store) == 0
        captured = capsys.readouterr()
        assert "Cleared 2 entries" in captured.out

    def test_clear_empty_store(
        self,
        session_env: str,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "clear")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "already empty" in captured.out


class TestSessionIncrement:
    def test_increment_new_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "increment", "counter")

        assert exit_code == 0
        assert session_store["counter"] == 1
        captured = capsys.readouterr()
        assert "counter = 1" in captured.out

    def test_increment_existing_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("counter", 10)

        exit_code = oaps_cli_with_exit_code("session", "increment", "counter")

        assert exit_code == 0
        assert session_store["counter"] == 11
        captured = capsys.readouterr()
        assert "counter = 11" in captured.out

    def test_increment_with_amount(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("counter", 5)

        exit_code = oaps_cli_with_exit_code(
            "session", "increment", "counter", "--amount", "10"
        )

        assert exit_code == 0
        assert session_store["counter"] == 15
        captured = capsys.readouterr()
        assert "counter = 15" in captured.out

    def test_increment_non_integer_fails(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("not-int", "string-value")

        exit_code = oaps_cli_with_exit_code("session", "increment", "not-int")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not an integer" in captured.out


class TestSessionDecrement:
    def test_decrement_new_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "decrement", "counter")

        assert exit_code == 0
        assert session_store["counter"] == -1
        captured = capsys.readouterr()
        assert "counter = -1" in captured.out

    def test_decrement_existing_key(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("counter", 10)

        exit_code = oaps_cli_with_exit_code("session", "decrement", "counter")

        assert exit_code == 0
        assert session_store["counter"] == 9
        captured = capsys.readouterr()
        assert "counter = 9" in captured.out

    def test_decrement_with_amount(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("counter", 20)

        exit_code = oaps_cli_with_exit_code(
            "session", "decrement", "counter", "--amount", "5"
        )

        assert exit_code == 0
        assert session_store["counter"] == 15
        captured = capsys.readouterr()
        assert "counter = 15" in captured.out

    def test_decrement_non_integer_fails(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("not-int", "string-value")

        exit_code = oaps_cli_with_exit_code("session", "decrement", "not-int")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not an integer" in captured.out


class TestSessionState:
    def test_state_empty_store(
        self,
        session_env: str,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("session", "state")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "empty" in captured.out

    def test_state_shows_keys_and_values(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("key1", "value1")
        session_store.set("key2", 42)

        exit_code = oaps_cli_with_exit_code("session", "state")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "key1: value1" in captured.out
        assert "key2: 42" in captured.out

    def test_state_verbose_shows_metadata(
        self,
        session_env: str,
        session_store: SQLiteStateStore,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        session_store.set("key1", "value1", author="author1")
        session_store.set("key2", "value2", author="author2")

        exit_code = oaps_cli_with_exit_code("session", "state", "--verbose")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "key: key1" in captured.out
        assert "value: value1" in captured.out
        assert "created_by: author1" in captured.out
        assert "---" in captured.out  # Separator between entries


class TestSessionNoSessionId:
    def test_fails_without_session_id(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Clear CLAUDE_SESSION_ID
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)

        exit_code = oaps_cli_with_exit_code("session", "get", "key")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No session ID" in captured.out

    def test_explicit_session_id_overrides_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Set up paths
        def mock_state_file() -> Path:
            return tmp_path / ".oaps" / "state.db"

        monkeypatch.setattr("oaps.utils.get_oaps_state_file", mock_state_file)

        mock_state_file().parent.mkdir(parents=True)

        # Set a session ID in env
        monkeypatch.setenv("CLAUDE_SESSION_ID", "env-session")

        # Create store with explicit session ID and add data
        explicit_store = SQLiteStateStore(
            mock_state_file(), session_id="explicit-session"
        )
        explicit_store.set("explicit-key", "explicit-value")

        # Get with explicit session ID should find the key
        exit_code = oaps_cli_with_exit_code(
            "session", "get", "explicit-key", "--session-id", "explicit-session"
        )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "explicit-value" in captured.out
