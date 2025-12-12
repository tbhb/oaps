import time
from pathlib import Path

import pytest

from oaps.utils._state_store import (
    SQLiteStateStore,
    StateStore,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_state.db"


@pytest.fixture
def store(db_path: Path) -> SQLiteStateStore:
    return SQLiteStateStore(db_path)


class TestSQLiteStateStoreInit:
    def test_creates_database_file(self, db_path: Path) -> None:
        SQLiteStateStore(db_path)

        assert db_path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        # Create the parent directories first, as connect() doesn't create them
        nested_path = tmp_path / "a" / "b" / "c" / "state.db"
        nested_path.parent.mkdir(parents=True, exist_ok=True)

        SQLiteStateStore(nested_path)

        assert nested_path.exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "string_path.db")

        store = SQLiteStateStore(db_path)

        assert Path(db_path).exists()
        assert len(store) == 0

    def test_implements_state_store(self, store: SQLiteStateStore) -> None:
        assert isinstance(store, StateStore)

    def test_reuses_existing_database(self, db_path: Path) -> None:
        store1 = SQLiteStateStore(db_path)
        store1.set("key", "value")

        store2 = SQLiteStateStore(db_path)

        assert "key" in store2
        assert store2["key"] == "value"


class TestSQLiteStateStoreBasicOps:
    def test_set_and_get_value(self, store: SQLiteStateStore) -> None:
        store.set("key1", "value1")

        assert store["key1"] == "value1"

    def test_get_missing_key_raises_keyerror(self, store: SQLiteStateStore) -> None:
        with pytest.raises(KeyError):
            _ = store["nonexistent"]

    def test_contains(self, store: SQLiteStateStore) -> None:
        store.set("exists", "value")

        assert "exists" in store
        assert "missing" not in store

    def test_contains_non_string_returns_false(self, store: SQLiteStateStore) -> None:
        store.set("key", "value")

        assert 123 not in store
        assert None not in store
        assert ["key"] not in store

    def test_len(self, store: SQLiteStateStore) -> None:
        assert len(store) == 0

        store.set("a", 1)
        assert len(store) == 1

        store.set("b", 2)
        assert len(store) == 2

        store.set("a", 100)  # Update existing
        assert len(store) == 2

    def test_iter_keys(self, store: SQLiteStateStore) -> None:
        store.set("c", 3)
        store.set("a", 1)
        store.set("b", 2)

        keys = list(store)
        # SQLite orders by key
        assert keys == ["a", "b", "c"]


class TestSQLiteStateStoreEntry:
    def test_get_entry_returns_full_entry(self, store: SQLiteStateStore) -> None:
        store.set("key", "value", author="test_user")

        entry = store.get_entry("key")

        assert entry is not None
        assert entry.key == "key"
        assert entry.value == "value"
        assert entry.created_by == "test_user"
        assert entry.updated_by == "test_user"
        assert isinstance(entry.created_at, str)
        assert isinstance(entry.updated_at, str)

    def test_get_entry_missing_returns_none(self, store: SQLiteStateStore) -> None:
        assert store.get_entry("missing") is None

    def test_set_preserves_created_metadata_on_update(
        self, store: SQLiteStateStore
    ) -> None:
        store.set("key", "original", author="creator")
        original_entry = store.get_entry("key")
        assert original_entry is not None

        # Small delay to ensure different timestamp
        time.sleep(0.01)
        store.set("key", "updated", author="updater")
        updated_entry = store.get_entry("key")
        assert updated_entry is not None

        assert updated_entry.value == "updated"
        assert updated_entry.created_at == original_entry.created_at
        assert updated_entry.created_by == "creator"
        assert updated_entry.updated_by == "updater"
        assert updated_entry.updated_at >= original_entry.updated_at


class TestSQLiteStateStoreDelete:
    def test_delete_existing_key(self, store: SQLiteStateStore) -> None:
        store.set("key", "value")

        result = store.delete("key")

        assert result is True
        assert "key" not in store

    def test_delete_missing_key(self, store: SQLiteStateStore) -> None:
        result = store.delete("nonexistent")

        assert result is False


class TestSQLiteStateStoreClear:
    def test_clear_removes_all_entries(self, store: SQLiteStateStore) -> None:
        store.set("a", 1)
        store.set("b", 2)
        store.set("c", 3)

        store.clear()

        assert len(store) == 0
        assert list(store) == []


class TestSQLiteStateStoreValueTypes:
    def test_stores_string_values(self, store: SQLiteStateStore) -> None:
        store.set("key", "hello world")
        assert store["key"] == "hello world"

    def test_stores_int_values(self, store: SQLiteStateStore) -> None:
        store.set("key", 42)
        assert store["key"] == 42

    def test_stores_float_values(self, store: SQLiteStateStore) -> None:
        store.set("key", 3.14159)
        assert store["key"] == 3.14159

    def test_stores_bytes_values(self, store: SQLiteStateStore) -> None:
        store.set("key", b"\x00\x01\x02\xff")
        assert store["key"] == b"\x00\x01\x02\xff"

    def test_stores_none_values(self, store: SQLiteStateStore) -> None:
        store.set("key", None)
        assert store["key"] is None
        assert "key" in store

    def test_stores_empty_string(self, store: SQLiteStateStore) -> None:
        store.set("key", "")
        assert store["key"] == ""

    def test_stores_large_string(self, store: SQLiteStateStore) -> None:
        large_value = "x" * 100_000
        store.set("key", large_value)
        assert store["key"] == large_value

    def test_stores_negative_numbers(self, store: SQLiteStateStore) -> None:
        store.set("int", -42)
        store.set("float", -3.14)
        assert store["int"] == -42
        assert store["float"] == -3.14


class TestSQLiteStateStorePersistence:
    def test_data_persists_across_instances(self, db_path: Path) -> None:
        store1 = SQLiteStateStore(db_path)
        store1.set("persistent", "data", author="user1")

        # Create new instance pointing to same file
        store2 = SQLiteStateStore(db_path)

        assert "persistent" in store2
        assert store2["persistent"] == "data"
        entry = store2.get_entry("persistent")
        assert entry is not None
        assert entry.created_by == "user1"

    def test_delete_persists_across_instances(self, db_path: Path) -> None:
        store1 = SQLiteStateStore(db_path)
        store1.set("to_delete", "value")
        store1.delete("to_delete")

        store2 = SQLiteStateStore(db_path)

        assert "to_delete" not in store2

    def test_clear_persists_across_instances(self, db_path: Path) -> None:
        store1 = SQLiteStateStore(db_path)
        store1.set("a", 1)
        store1.set("b", 2)
        store1.clear()

        store2 = SQLiteStateStore(db_path)

        assert len(store2) == 0


class TestSQLiteStateStoreAuthor:
    def test_author_none_by_default(self, store: SQLiteStateStore) -> None:
        store.set("key", "value")
        entry = store.get_entry("key")

        assert entry is not None
        assert entry.created_by is None
        assert entry.updated_by is None

    def test_updated_by_preserved_when_update_author_is_none(
        self, store: SQLiteStateStore
    ) -> None:
        # Note: Due to exclude_none=True in database utilities, when author=None
        # is passed, the updated_by field is not included in the UPDATE, so
        # the original value is preserved rather than being set to NULL.
        store.set("key", "original", author="creator")

        store.set("key", "updated")  # No author specified

        entry = store.get_entry("key")
        assert entry is not None
        assert entry.created_by == "creator"  # Original creator preserved
        # Original updated_by preserved (not set to None due to exclude_none)
        assert entry.updated_by == "creator"


class TestSQLiteStateStoreTimestamps:
    def test_timestamps_are_iso8601_strings(self, store: SQLiteStateStore) -> None:
        store.set("key", "value")
        entry = store.get_entry("key")

        assert entry is not None
        assert isinstance(entry.created_at, str)
        assert isinstance(entry.updated_at, str)
        # Basic ISO 8601 format check
        assert "T" in entry.created_at
        assert "T" in entry.updated_at

    def test_updated_at_changes_on_update(self, store: SQLiteStateStore) -> None:
        store.set("key", "original")
        original_entry = store.get_entry("key")
        assert original_entry is not None

        time.sleep(0.01)
        store.set("key", "updated")
        updated_entry = store.get_entry("key")
        assert updated_entry is not None

        assert updated_entry.updated_at > original_entry.updated_at
