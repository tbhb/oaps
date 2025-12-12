import time

import pendulum
import pytest

from oaps.utils._state_store import (
    MockStateStore,
    StateEntry,
)


class TestStateEntry:
    def test_stores_all_value_types(self) -> None:
        now_str = pendulum.now("UTC").to_iso8601_string()

        string_entry = StateEntry(
            key="str",
            value="hello",
            created_at=now_str,
            created_by=None,
            updated_at=now_str,
            updated_by=None,
        )
        assert string_entry.value == "hello"

        int_entry = StateEntry(
            key="int",
            value=42,
            created_at=now_str,
            created_by=None,
            updated_at=now_str,
            updated_by=None,
        )
        assert int_entry.value == 42

        float_entry = StateEntry(
            key="float",
            value=3.14,
            created_at=now_str,
            created_by=None,
            updated_at=now_str,
            updated_by=None,
        )
        assert float_entry.value == 3.14

        bytes_entry = StateEntry(
            key="bytes",
            value=b"\x00\x01",
            created_at=now_str,
            created_by=None,
            updated_at=now_str,
            updated_by=None,
        )
        assert bytes_entry.value == b"\x00\x01"

        none_entry = StateEntry(
            key="none",
            value=None,
            created_at=now_str,
            created_by=None,
            updated_at=now_str,
            updated_by=None,
        )
        assert none_entry.value is None


class TestMockStateStore:
    @pytest.fixture
    def store(self) -> MockStateStore:
        return MockStateStore()

    def test_starts_empty(self, store: MockStateStore) -> None:
        assert len(store) == 0
        assert list(store) == []

    def test_set_and_get_value(self, store: MockStateStore) -> None:
        store.set("key1", "value1")

        assert store["key1"] == "value1"

    def test_get_missing_key_raises_keyerror(self, store: MockStateStore) -> None:
        with pytest.raises(KeyError):
            _ = store["nonexistent"]

    def test_contains(self, store: MockStateStore) -> None:
        store.set("exists", "value")

        assert "exists" in store
        assert "missing" not in store

    def test_len(self, store: MockStateStore) -> None:
        assert len(store) == 0

        store.set("a", 1)
        assert len(store) == 1

        store.set("b", 2)
        assert len(store) == 2

        store.set("a", 100)  # Update existing
        assert len(store) == 2

    def test_iter_keys(self, store: MockStateStore) -> None:
        store.set("c", 3)
        store.set("a", 1)
        store.set("b", 2)

        keys = list(store)
        assert set(keys) == {"a", "b", "c"}

    def test_get_entry_returns_full_entry(self, store: MockStateStore) -> None:
        store.set("key", "value", author="test_user")

        entry = store.get_entry("key")

        assert entry is not None
        assert entry.key == "key"
        assert entry.value == "value"
        assert entry.created_by == "test_user"
        assert entry.updated_by == "test_user"
        assert isinstance(entry.created_at, str)
        assert isinstance(entry.updated_at, str)

    def test_get_entry_missing_returns_none(self, store: MockStateStore) -> None:
        assert store.get_entry("missing") is None

    def test_set_preserves_created_metadata_on_update(
        self, store: MockStateStore
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

    def test_delete_existing_key(self, store: MockStateStore) -> None:
        store.set("key", "value")

        result = store.delete("key")

        assert result is True
        assert "key" not in store

    def test_delete_missing_key(self, store: MockStateStore) -> None:
        result = store.delete("nonexistent")

        assert result is False

    def test_clear_removes_all_entries(self, store: MockStateStore) -> None:
        store.set("a", 1)
        store.set("b", 2)
        store.set("c", 3)

        store.clear()

        assert len(store) == 0
        assert list(store) == []

    def test_stores_string_values(self, store: MockStateStore) -> None:
        store.set("key", "hello world")
        assert store["key"] == "hello world"

    def test_stores_int_values(self, store: MockStateStore) -> None:
        store.set("key", 42)
        assert store["key"] == 42

    def test_stores_float_values(self, store: MockStateStore) -> None:
        store.set("key", 3.14159)
        assert store["key"] == 3.14159

    def test_stores_bytes_values(self, store: MockStateStore) -> None:
        store.set("key", b"\x00\x01\x02\xff")
        assert store["key"] == b"\x00\x01\x02\xff"

    def test_stores_none_values(self, store: MockStateStore) -> None:
        store.set("key", None)
        assert store["key"] is None
        assert "key" in store

    def test_author_none_by_default(self, store: MockStateStore) -> None:
        store.set("key", "value")
        entry = store.get_entry("key")

        assert entry is not None
        assert entry.created_by is None
        assert entry.updated_by is None
