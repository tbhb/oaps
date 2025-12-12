"""Generic state store implementations for persisting key-value data.

This module provides an abstract state store protocol and concrete implementations
for storing key-value data with metadata. Used for session state, project state, etc.
"""

from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import pendulum
from pydantic import BaseModel

from oaps.utils.database import (
    connect,
    fetch_all,
    fetch_one,
    safe_identifier,
    upsert,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

    from structlog.typing import FilteringBoundLogger

type StateStoreKey = str
type StateStoreValue = str | int | float | bytes | None

# Pre-computed safe identifiers for state store table/columns
_TABLE = safe_identifier("state_store")
_SESSION_ID_COL = safe_identifier("session_id")
_KEY_COL = safe_identifier("key")


class StateEntry(BaseModel):
    """An entry in the state store.

    Attributes:
        session_id: The session ID for this entry. Empty string indicates
            project scope (stored as empty string internally for SQLite
            ON CONFLICT compatibility).
        key: The unique identifier for this entry.
        value: The stored value.
        created_at: When this entry was first created (ISO 8601 string).
        created_by: Who created this entry (e.g., session ID, user).
        updated_at: When this entry was last modified (ISO 8601 string).
        updated_by: Who last modified this entry.
    """

    session_id: str = ""
    key: str
    value: str | int | float | bytes | None
    created_at: str
    created_by: str | None
    updated_at: str
    updated_by: str | None


@runtime_checkable
class StateStore(Protocol):
    """Protocol for state store implementations.

    State stores provide a key-value interface for persisting data.
    Implementations must support the full Mapping protocol plus set/delete operations.
    """

    def __getitem__(self, key: StateStoreKey) -> StateStoreValue:
        """Get the value for a key.

        Args:
            key: The key to look up.

        Returns:
            The stored value.

        Raises:
            KeyError: If the key does not exist.
        """
        ...

    def __iter__(self) -> Iterator[StateStoreKey]:
        """Iterate over all keys in the store.

        Returns:
            An iterator of keys.
        """
        ...

    def __len__(self) -> int:
        """Return the number of entries in the store.

        Returns:
            The count of stored entries.
        """
        ...

    def __contains__(self, key: object) -> bool:
        """Check if a key exists in the store.

        Args:
            key: The key to check.

        Returns:
            True if the key exists, False otherwise.
        """
        ...

    def get_entry(self, key: StateStoreKey) -> StateEntry | None:
        """Get the full entry for a key, including metadata.

        Args:
            key: The key to look up.

        Returns:
            The full entry with metadata, or None if not found.
        """
        ...

    def set(
        self,
        key: StateStoreKey,
        value: StateStoreValue,
        *,
        author: str | None = None,
    ) -> None:
        """Set a value in the store.

        If the key already exists, updates the value and updated_at/updated_by.
        If the key is new, sets created_at/created_by as well.

        Args:
            key: The key to set.
            value: The value to store.
            author: Who is making this change.
        """
        ...

    def delete(self, key: StateStoreKey) -> bool:
        """Delete a key from the store.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        ...

    def clear(self) -> None:
        """Remove all entries from the store."""
        ...

    def atomic_increment(
        self,
        key: StateStoreKey,
        amount: int = 1,
        *,
        author: str | None = None,
    ) -> int:
        """Atomically increment a counter, initializing to 0 if not exists.

        If the existing value is not numeric, treats it as 0.

        Args:
            key: The key to increment.
            amount: Amount to add (can be negative for decrement).
            author: Who is making this change.

        Returns:
            The new value after incrementing.
        """
        ...


class MockStateStore:
    """In-memory mock implementation of state store.

    Useful for testing and development. Data is not persisted.
    Can be used as a drop-in replacement for SQLiteStateStore in tests.
    """

    _entries: dict[tuple[str, StateStoreKey], StateEntry]
    _session_id: str | None
    _effective_session_id: str
    _logger: "FilteringBoundLogger | None"  # noqa: UP037

    def __init__(
        self,
        db_path: str
        | Path
        | None = None,  # Ignored - for SQLiteStateStore compatibility
        session_id: str | None = None,
        *,
        logger: "FilteringBoundLogger | None" = None,  # noqa: UP037
    ) -> None:
        """Initialize an empty in-memory store.

        Args:
            db_path: Ignored. Accepted for compatibility with SQLiteStateStore.
            session_id: The session ID for scoping (None for project scope).
            logger: Optional logger for debug-level operation logging.
                If None, no logging is performed.
        """
        # db_path is ignored - in-memory store doesn't persist
        _ = db_path
        self._entries = {}
        self._session_id = session_id
        # Use sentinel value for NULL - SQLite ON CONFLICT doesn't work with NULL
        self._effective_session_id = (
            session_id if session_id is not None else _PROJECT_SCOPE_SENTINEL
        )
        self._logger = logger

    @property
    def session_id(self) -> str | None:
        """Get the session ID for this store."""
        return self._session_id

    def __getitem__(self, key: StateStoreKey) -> StateStoreValue:
        """Get the value for a key.

        Args:
            key: The key to look up.

        Returns:
            The stored value.

        Raises:
            KeyError: If the key does not exist.
        """
        composite_key = (self._effective_session_id, key)
        try:
            value = self._entries[composite_key].value
        except KeyError:
            if self._logger:
                self._logger.debug("store_get", key=key, found=False)
            raise
        else:
            if self._logger:
                self._logger.debug("store_get", key=key, found=True, value=value)
            return value

    def __iter__(self) -> Iterator[StateStoreKey]:
        """Iterate over all keys in the store.

        Returns:
            An iterator of keys.
        """
        keys = [
            entry_key
            for (sid, entry_key) in self._entries
            if sid == self._effective_session_id
        ]
        if self._logger:
            self._logger.debug("store_iter", count=len(keys), keys=keys)
        return iter(keys)

    def __len__(self) -> int:
        """Return the number of entries in the store.

        Returns:
            The count of stored entries.
        """
        count = sum(1 for sid, _ in self._entries if sid == self._effective_session_id)
        if self._logger:
            self._logger.debug("store_len", count=count)
        return count

    def __contains__(self, key: object) -> bool:
        """Check if a key exists in the store.

        Args:
            key: The key to check.

        Returns:
            True if the key exists, False otherwise.
        """
        if not isinstance(key, str):
            if self._logger:
                self._logger.debug("store_contains", key=key, exists=False)
            return False
        composite_key = (self._effective_session_id, key)
        exists = composite_key in self._entries
        if self._logger:
            self._logger.debug("store_contains", key=key, exists=exists)
        return exists

    def get_entry(self, key: StateStoreKey) -> StateEntry | None:
        """Get the full entry for a key, including metadata.

        Args:
            key: The key to look up.

        Returns:
            The full entry with metadata, or None if not found.
        """
        composite_key = (self._effective_session_id, key)
        entry = self._entries.get(composite_key)
        if self._logger:
            if entry:
                self._logger.debug(
                    "store_get_entry",
                    key=key,
                    found=True,
                    value=entry.value,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                )
            else:
                self._logger.debug("store_get_entry", key=key, found=False)
        return entry

    def set(
        self,
        key: StateStoreKey,
        value: StateStoreValue,
        *,
        author: str | None = None,
    ) -> None:
        """Set a value in the store.

        If the key already exists, updates the value and updated_at/updated_by.
        If the key is new, sets created_at/created_by as well.

        Args:
            key: The key to set.
            value: The value to store.
            author: Who is making this change.
        """
        now_str = pendulum.now("UTC").to_iso8601_string()
        composite_key = (self._effective_session_id, key)
        existing = self._entries.get(composite_key)
        is_update = existing is not None

        if existing is not None:
            self._entries[composite_key] = StateEntry(
                session_id=self._effective_session_id,
                key=key,
                value=value,
                created_at=existing.created_at,
                created_by=existing.created_by,
                updated_at=now_str,
                updated_by=author,
            )
        else:
            self._entries[composite_key] = StateEntry(
                session_id=self._effective_session_id,
                key=key,
                value=value,
                created_at=now_str,
                created_by=author,
                updated_at=now_str,
                updated_by=author,
            )

        if self._logger:
            self._logger.debug(
                "store_set", key=key, value=value, author=author, is_update=is_update
            )

    def delete(self, key: StateStoreKey) -> bool:
        """Delete a key from the store.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        composite_key = (self._effective_session_id, key)
        deleted = composite_key in self._entries
        if deleted:
            del self._entries[composite_key]
        if self._logger:
            self._logger.debug("store_delete", key=key, deleted=deleted)
        return deleted

    def clear(self) -> None:
        """Remove all entries from the store."""
        keys_to_delete = [
            composite_key
            for composite_key in self._entries
            if composite_key[0] == self._effective_session_id
        ]
        count = len(keys_to_delete)
        for composite_key in keys_to_delete:
            del self._entries[composite_key]
        if self._logger:
            self._logger.debug("store_clear", cleared_count=count)

    def atomic_increment(
        self,
        key: StateStoreKey,
        amount: int = 1,
        *,
        author: str | None = None,
    ) -> int:
        """Atomically increment a counter, initializing to 0 if not exists."""
        now_str = pendulum.now("UTC").to_iso8601_string()
        composite_key = (self._effective_session_id, key)
        existing = self._entries.get(composite_key)

        if existing is not None:
            current_value = existing.value
            if isinstance(current_value, int):
                current_int = current_value
            elif isinstance(current_value, float):
                current_int = int(current_value)
            elif isinstance(current_value, str):
                # Match SQLite typeof() behavior: strings are not numeric
                current_int = 0
            else:
                current_int = 0

            new_value = current_int + amount
            self._entries[composite_key] = StateEntry(
                session_id=self._effective_session_id,
                key=key,
                value=new_value,
                created_at=existing.created_at,
                created_by=existing.created_by,
                updated_at=now_str,
                updated_by=author,
            )
        else:
            new_value = amount
            self._entries[composite_key] = StateEntry(
                session_id=self._effective_session_id,
                key=key,
                value=new_value,
                created_at=now_str,
                created_by=author,
                updated_at=now_str,
                updated_by=author,
            )

        if self._logger:
            self._logger.debug(
                "store_atomic_increment",
                key=key,
                amount=amount,
                new_value=new_value,
                author=author,
            )
        return new_value


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS state_store (
    session_id TEXT,
    key TEXT NOT NULL,
    value BLOB,
    created_at TEXT NOT NULL,
    created_by TEXT,
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    PRIMARY KEY (session_id, key)
);

CREATE INDEX IF NOT EXISTS idx_state_store_session_updated
ON state_store (session_id, updated_at);
"""

# Pre-computed SQL queries using safe identifiers
# S608 is safe: safe_identifier validates all table/column names
_SQL_SELECT_BY_KEY = (
    f"SELECT * FROM {_TABLE} WHERE {_SESSION_ID_COL} = ? AND {_KEY_COL} = ?"  # noqa: S608
)
_SQL_SELECT_ALL = (
    f"SELECT * FROM {_TABLE} WHERE {_SESSION_ID_COL} = ? ORDER BY {_KEY_COL}"  # noqa: S608
)
_SQL_COUNT = f"SELECT COUNT(*) FROM {_TABLE} WHERE {_SESSION_ID_COL} = ?"  # noqa: S608
_SQL_EXISTS = f"SELECT 1 FROM {_TABLE} WHERE {_SESSION_ID_COL} = ? AND {_KEY_COL} = ?"  # noqa: S608
_SQL_DELETE_ALL = f"DELETE FROM {_TABLE} WHERE {_SESSION_ID_COL} = ?"  # noqa: S608
_SQL_ATOMIC_INCREMENT = f"""
INSERT INTO {_TABLE}
    ({_SESSION_ID_COL}, {_KEY_COL}, "value",
     "created_at", "created_by", "updated_at", "updated_by")
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT ({_SESSION_ID_COL}, {_KEY_COL}) DO UPDATE SET
    "value" = COALESCE(
        CASE
            WHEN typeof({_TABLE}."value") IN ('integer', 'real')
            THEN CAST({_TABLE}."value" AS INTEGER)
            ELSE 0
        END, 0
    ) + excluded."value",
    "updated_at" = excluded."updated_at",
    "updated_by" = excluded."updated_by"
RETURNING "value"
"""  # noqa: S608


# Sentinel value for project scope - SQLite ON CONFLICT doesn't work with NULL
_PROJECT_SCOPE_SENTINEL = ""


class SQLiteStateStore:
    """SQLite-backed implementation of state store.

    Persists state data to a SQLite database file. Thread-safe for
    single-process access.
    """

    _db_path: str
    _session_id: str | None
    _effective_session_id: str  # Actual value used in SQL (sentinel for None)
    _logger: "FilteringBoundLogger | None"  # noqa: UP037

    def __init__(
        self,
        db_path: str | Path,
        session_id: str | None = None,
        *,
        logger: "FilteringBoundLogger | None" = None,  # noqa: UP037
    ) -> None:
        """Initialize a SQLite state store.

        Creates the database file and schema if they don't exist.

        Args:
            db_path: Path to the SQLite database file.
            session_id: The session ID for scoping (None for project scope).
            logger: Optional logger for debug-level operation logging.
                If None, no logging is performed.
        """
        self._db_path = str(db_path)
        self._session_id = session_id
        # Use sentinel value for NULL - SQLite ON CONFLICT doesn't work with NULL
        self._effective_session_id = (
            session_id if session_id is not None else _PROJECT_SCOPE_SENTINEL
        )
        self._logger = logger
        self._ensure_schema()

    @property
    def session_id(self) -> str | None:
        """Get the session ID for this store."""
        return self._session_id

    def _ensure_schema(self) -> None:
        """Create the database schema if it doesn't exist."""
        with connect(self._db_path) as conn:
            _ = conn.executescript(_SQLITE_SCHEMA)

    def __getitem__(self, key: StateStoreKey) -> StateStoreValue:
        """Get the value for a key.

        Args:
            key: The key to look up.

        Returns:
            The stored value.

        Raises:
            KeyError: If the key does not exist.
        """
        with connect(self._db_path) as conn:
            result = fetch_one(
                conn, StateEntry, _SQL_SELECT_BY_KEY, (self._effective_session_id, key)
            )
            if result is None:
                if self._logger:
                    self._logger.debug("store_get", key=key, found=False)
                raise KeyError(key)
            if self._logger:
                self._logger.debug("store_get", key=key, found=True, value=result.value)
            return result.value

    def __iter__(self) -> Iterator[StateStoreKey]:
        """Iterate over all keys in the store.

        Returns:
            An iterator of keys.
        """
        with connect(self._db_path) as conn:
            results = fetch_all(
                conn, StateEntry, _SQL_SELECT_ALL, (self._effective_session_id,)
            )
            keys = [entry.key for entry in results]
            if self._logger:
                self._logger.debug("store_iter", count=len(keys), keys=keys)
            return iter(keys)

    def __len__(self) -> int:
        """Return the number of entries in the store.

        Returns:
            The count of stored entries.
        """
        with connect(self._db_path) as conn:
            cursor = conn.execute(_SQL_COUNT, (self._effective_session_id,))
            row = cast("sqlite3.Row | None", cursor.fetchone())
            # Row indexing returns Any; COUNT(*) always returns an integer
            count = int(row[0]) if row else 0  # pyright: ignore[reportAny]
            if self._logger:
                self._logger.debug("store_len", count=count)
            return count

    def __contains__(self, key: object) -> bool:
        """Check if a key exists in the store.

        Args:
            key: The key to check.

        Returns:
            True if the key exists, False otherwise.
        """
        if not isinstance(key, str):
            if self._logger:
                self._logger.debug("store_contains", key=key, exists=False)
            return False
        with connect(self._db_path) as conn:
            cursor = conn.execute(_SQL_EXISTS, (self._effective_session_id, key))
            exists = cursor.fetchone() is not None
            if self._logger:
                self._logger.debug("store_contains", key=key, exists=exists)
            return exists

    def get_entry(self, key: StateStoreKey) -> StateEntry | None:
        """Get the full entry for a key, including metadata.

        Args:
            key: The key to look up.

        Returns:
            The full entry with metadata, or None if not found.
        """
        with connect(self._db_path) as conn:
            entry = fetch_one(
                conn, StateEntry, _SQL_SELECT_BY_KEY, (self._effective_session_id, key)
            )
            if self._logger:
                if entry:
                    self._logger.debug(
                        "store_get_entry",
                        key=key,
                        found=True,
                        value=entry.value,
                        created_at=entry.created_at,
                        updated_at=entry.updated_at,
                    )
                else:
                    self._logger.debug("store_get_entry", key=key, found=False)
            return entry

    def set(
        self,
        key: StateStoreKey,
        value: StateStoreValue,
        *,
        author: str | None = None,
    ) -> None:
        """Set a value in the store.

        If the key already exists, updates the value and updated_at/updated_by.
        If the key is new, sets created_at/created_by as well.

        Args:
            key: The key to set.
            value: The value to store.
            author: Who is making this change.
        """
        now_str = pendulum.now("UTC").to_iso8601_string()

        with connect(self._db_path) as conn:
            # Check if key exists to preserve created_at/created_by
            existing = fetch_one(
                conn, StateEntry, _SQL_SELECT_BY_KEY, (self._effective_session_id, key)
            )
            is_update = existing is not None

            if existing is not None:
                model = StateEntry(
                    session_id=self._effective_session_id,
                    key=key,
                    value=value,
                    created_at=existing.created_at,
                    created_by=existing.created_by,
                    updated_at=now_str,
                    updated_by=author,
                )
            else:
                model = StateEntry(
                    session_id=self._effective_session_id,
                    key=key,
                    value=value,
                    created_at=now_str,
                    created_by=author,
                    updated_at=now_str,
                    updated_by=author,
                )

            _ = upsert(
                conn,
                "state_store",
                model,
                conflict_columns=["session_id", "key"],
            )

            if self._logger:
                self._logger.debug(
                    "store_set",
                    key=key,
                    value=value,
                    author=author,
                    is_update=is_update,
                )

    def delete(self, key: StateStoreKey) -> bool:
        """Delete a key from the store.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        with connect(self._db_path) as conn:
            # Use raw SQL for composite key delete
            cursor = conn.execute(
                f"DELETE FROM {_TABLE} WHERE {_SESSION_ID_COL} = ? AND {_KEY_COL} = ?",  # noqa: S608
                (self._effective_session_id, key),
            )
            deleted = cursor.rowcount > 0
            if self._logger:
                self._logger.debug("store_delete", key=key, deleted=deleted)
            return deleted

    def clear(self) -> None:
        """Remove all entries from the store."""
        with connect(self._db_path) as conn:
            # Get count before clearing for logging
            count = 0
            if self._logger:
                cursor = conn.execute(_SQL_COUNT, (self._effective_session_id,))
                row = cast("sqlite3.Row | None", cursor.fetchone())
                count = int(row[0]) if row else 0  # pyright: ignore[reportAny]
            _ = conn.execute(_SQL_DELETE_ALL, (self._effective_session_id,))
            if self._logger:
                self._logger.debug("store_clear", cleared_count=count)

    def atomic_increment(
        self,
        key: StateStoreKey,
        amount: int = 1,
        *,
        author: str | None = None,
    ) -> int:
        """Atomically increment a counter, initializing to 0 if not exists.

        Uses a single SQL statement with INSERT...ON CONFLICT for atomicity.
        If the existing value is not numeric, treats it as 0.

        Args:
            key: The key to increment.
            amount: Amount to add (can be negative for decrement).
            author: Who is making this change.

        Returns:
            The new value after incrementing.
        """
        now_str = pendulum.now("UTC").to_iso8601_string()

        with connect(self._db_path) as conn:
            cursor = conn.execute(
                _SQL_ATOMIC_INCREMENT,
                (
                    self._effective_session_id,
                    key,
                    amount,  # Initial value if inserting
                    now_str,  # created_at
                    author,  # created_by
                    now_str,  # updated_at
                    author,  # updated_by
                ),
            )
            row = cast("sqlite3.Row | None", cursor.fetchone())
            # Row indexing returns Any; RETURNING value is always an integer
            new_value = int(row[0]) if row else amount  # pyright: ignore[reportAny]

            if self._logger:
                self._logger.debug(
                    "store_atomic_increment",
                    key=key,
                    amount=amount,
                    new_value=new_value,
                    author=author,
                )
            return new_value


def create_state_store(
    path: str | Path,
    session_id: str | None = None,
    *,
    logger: "FilteringBoundLogger | None" = None,  # noqa: UP037
) -> SQLiteStateStore:
    """Create an empty state store at the specified path.

    Creates a new SQLite database file with the state store schema.
    If the file already exists, it will be opened and the schema will
    be created if missing (existing data is preserved).

    Args:
        path: Path where the state store database should be created.
        session_id: The session ID for scoping (None for project scope).
        logger: Optional logger for debug-level operation logging.
            If None, no logging is performed.

    Returns:
        A SQLiteStateStore instance connected to the database.
    """
    return SQLiteStateStore(path, session_id=session_id, logger=logger)


def get_unified_db_path() -> Path:
    """Get the path to the unified state database.

    Returns:
        Path to the state database (.oaps/state.db).
    """
    from oaps.utils._paths import get_oaps_state_db  # noqa: PLC0415

    return get_oaps_state_db()


def create_project_store(
    *,
    logger: "FilteringBoundLogger | None" = None,  # noqa: UP037
) -> SQLiteStateStore:
    """Create a state store scoped to the project (session_id=None).

    Args:
        logger: Optional logger for debug-level operation logging.
            If None, no logging is performed.

    Returns:
        A SQLiteStateStore instance scoped to the project.
    """
    db_path = get_unified_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStateStore(db_path, session_id=None, logger=logger)


def create_session_store(
    session_id: str,
    *,
    logger: "FilteringBoundLogger | None" = None,  # noqa: UP037
) -> SQLiteStateStore:
    """Create a state store scoped to a specific session.

    Args:
        session_id: The session ID for scoping.
        logger: Optional logger for debug-level operation logging.
            If None, no logging is performed.

    Returns:
        A SQLiteStateStore instance scoped to the session.
    """
    db_path = get_unified_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStateStore(db_path, session_id=session_id, logger=logger)
