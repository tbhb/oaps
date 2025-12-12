"""SQLite database utilities for Pydantic models.

This module provides simple CRUD operations for SQLite databases using Pydantic
models for serialization/deserialization.

Note:
    Fields with ``None`` values are excluded from INSERT/UPDATE operations via
    ``exclude_none=True``. This means you cannot explicitly set a column to NULL
    using these utilities. If you need explicit NULLs, use raw SQL or modify the
    model to use a sentinel value.

    Return values of 0 from ``insert`` and ``upsert`` indicate "no meaningful row
    id" (e.g., INSERT OR IGNORE that didn't insert, or tables without ROWID),
    not "row id is zero."
"""

import re
import sqlite3
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

# Valid SQL identifier pattern (alphanumeric and underscores, not starting with digit)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# SQLite-compatible value types
type SQLValue = str | int | float | bytes | None

# SQLite transaction isolation levels
type IsolationLevel = Literal["DEFERRED", "EXCLUSIVE", "IMMEDIATE"] | None


@contextmanager
def connect(  # noqa: PLR0913
    path: str | bytes,
    *,
    timeout: float = 30.0,
    detect_types: int = 0,
    isolation_level: IsolationLevel = "IMMEDIATE",
    check_same_thread: bool = True,
    factory: type[sqlite3.Connection] = sqlite3.Connection,
    cached_statements: int = 128,
    uri: bool = False,
    autocommit: bool = False,
    wal_mode: bool = True,
) -> Iterator[sqlite3.Connection]:
    """Context manager for SQLite connections with automatic transaction handling.

    Opens a connection, yields it for use, and handles cleanup. On successful
    completion, commits the transaction. On any exception, rolls back and re-raises.
    The connection is always closed on exit.

    Args:
        path: Database file path, or ``:memory:`` for in-memory database.
        timeout: Seconds to wait for lock before raising OperationalError.
        detect_types: Control type detection for datetime/date columns.
        isolation_level: Transaction isolation level (DEFERRED, IMMEDIATE, EXCLUSIVE).
        check_same_thread: If True, only the creating thread may use the connection.
        factory: Custom connection class (must subclass sqlite3.Connection).
        cached_statements: Number of statements to cache.
        uri: If True, interpret path as a URI.
        autocommit: If True, disable implicit transaction management.
        wal_mode: If True, enable WAL journal mode for better concurrency.

    Yields:
        SQLite connection with row_factory set to sqlite3.Row.

    Raises:
        sqlite3.OperationalError: If the database cannot be opened.
        Any exception raised within the context block (after rollback).

    Examples:
        >>> with connect(":memory:") as conn:
        ...     conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, name TEXT)")
        ...     conn.execute("INSERT INTO records (name) VALUES (?)", ("first",))
        >>> # Transaction is committed automatically on successful exit

        >>> with connect(":memory:") as conn:
        ...     conn.execute("CREATE TABLE t (x INT)")
        ...     raise ValueError("oops")  # Transaction is rolled back
        Traceback (most recent call last):
            ...
        ValueError: oops
    """
    conn = sqlite3.connect(
        path,
        timeout=timeout,
        detect_types=detect_types,
        isolation_level=isolation_level,
        check_same_thread=check_same_thread,
        factory=factory,
        cached_statements=cached_statements,
        uri=uri,
        autocommit=autocommit,
    )
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency (skip for :memory: databases)
    if wal_mode and str(path) != ":memory:" and not str(path).startswith("file:"):
        with suppress(sqlite3.OperationalError):
            _ = conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout for handling concurrent access
        _ = conn.execute("PRAGMA busy_timeout=10000")

    try:
        yield conn
        conn.commit()
    except BaseException:
        with suppress(Exception):
            conn.rollback()
        raise
    finally:
        conn.close()


def create_database(path: str | Path, schema: str | None = None) -> None:
    """Create an empty SQLite database, optionally with a schema.

    Creates the database file and any parent directories if they don't exist.
    If a schema is provided, executes it as DDL statements.

    Args:
        path: Path to the database file. Use ``:memory:`` for in-memory database.
        schema: Optional DDL statements to execute (e.g., CREATE TABLE statements).

    Raises:
        sqlite3.OperationalError: If the database cannot be created.
        sqlite3.DatabaseError: If the schema contains invalid SQL.

    Examples:
        >>> create_database("app.db")
        >>> # Creates an empty database file

        >>> schema = '''
        ...     CREATE TABLE users (
        ...         id INTEGER PRIMARY KEY,
        ...         name TEXT NOT NULL
        ...     );
        ...     CREATE TABLE posts (
        ...         id INTEGER PRIMARY KEY,
        ...         user_id INTEGER REFERENCES users(id),
        ...         content TEXT
        ...     );
        ... '''
        >>> create_database("app.db", schema=schema)
        >>> # Creates database with tables
    """
    path_obj = Path(path) if not isinstance(path, Path) else path

    # Create parent directories if needed (skip for :memory: or URI paths)
    if str(path) != ":memory:" and not str(path).startswith("file:"):
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    with connect(str(path)) as conn:
        if schema:
            _ = conn.executescript(schema)


def safe_identifier(name: str) -> str:
    """Validate and quote a SQL identifier.

    Validates that the identifier contains only safe characters (letters,
    digits, underscores), then quotes it to handle SQL reserved words.

    Args:
        name: The identifier to validate and quote.

    Returns:
        The quoted identifier (e.g., ``"users"``).

    Raises:
        ValueError: If the identifier contains invalid characters.

    Examples:
        >>> _safe_identifier("users")
        '"users"'
        >>> _safe_identifier("user_id")
        '"user_id"'
        >>> _safe_identifier("order")  # SQL reserved word
        '"order"'
        >>> _safe_identifier("123abc")
        Traceback (most recent call last):
            ...
        ValueError: Invalid SQL identifier: '123abc'
    """
    if not _IDENTIFIER_RE.match(name):
        msg = f"Invalid SQL identifier: {name!r}"
        raise ValueError(msg)
    return f'"{name}"'


def fetch_one[T: BaseModel](
    conn: sqlite3.Connection,
    model: type[T],
    sql: str,
    params: tuple[SQLValue, ...] = (),
) -> T | None:
    """Fetch a single row and return it as a Pydantic model.

    Args:
        conn: SQLite connection.
        model: Pydantic model class to deserialize into.
        sql: SQL query string.
        params: Query parameters.

    Returns:
        Model instance or None if no row found.

    Examples:
        >>> class Record(BaseModel):
        ...     id: int
        ...     name: str
        >>> record = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))
        >>> record.name if record else None
        'first'
        >>> fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (999,))
        >>> # Returns None when no row found
    """
    row = cast("sqlite3.Row | None", conn.execute(sql, params).fetchone())
    if row is None:
        return None
    return model.model_validate(dict(row))


def fetch_all[T: BaseModel](
    conn: sqlite3.Connection,
    model: type[T],
    sql: str,
    params: tuple[SQLValue, ...] = (),
) -> list[T]:
    """Fetch all rows and return them as Pydantic models.

    Args:
        conn: SQLite connection.
        model: Pydantic model class to deserialize into.
        sql: SQL query string.
        params: Query parameters.

    Returns:
        List of model instances (empty if no rows).

    Examples:
        >>> class Record(BaseModel):
        ...     id: int
        ...     name: str
        >>> records = fetch_all(conn, Record, "SELECT * FROM records ORDER BY id")
        >>> [r.name for r in records]
        ['first', 'second']
        >>> fetch_all(conn, Record, "SELECT * FROM records WHERE id > ?", (999,))
        []
    """
    rows = cast("list[sqlite3.Row]", conn.execute(sql, params).fetchall())
    return [model.model_validate(dict(row)) for row in rows]


def insert_all(
    conn: sqlite3.Connection,
    table: str,
    objs: Sequence[BaseModel],
    exclude: set[str] | None = None,
    *,
    commit: bool = True,
) -> int:
    """Insert multiple models into a table.

    Uses executemany for efficient batch insertion. The column set is
    determined from the model's field definitions, ensuring all non-excluded
    fields are included regardless of their values.

    Args:
        conn: SQLite connection.
        table: Table name.
        objs: List of Pydantic models to insert.
        exclude: Field names to exclude from the insert.
        commit: Whether to commit the transaction (default True).

    Returns:
        Number of rows inserted.

    Examples:
        >>> records = [
        ...     Record(name="first", code="A001"),
        ...     Record(name="second", code="B002"),
        ... ]
        >>> insert_all(conn, "records", records, exclude={"id"})
        2
    """
    if not objs:
        return 0

    safe_table = safe_identifier(table)
    exclude_set = exclude or set()
    columns = [k for k in type(objs[0]).model_fields if k not in exclude_set]
    cols_sql = ", ".join(safe_identifier(k) for k in columns)
    placeholders = ", ".join(f":{k}" for k in columns)
    all_data = [obj.model_dump(include=set(columns)) for obj in objs]

    cursor = conn.executemany(
        f"INSERT INTO {safe_table} ({cols_sql}) VALUES ({placeholders})",  # noqa: S608
        all_data,
    )
    if commit:
        conn.commit()
    return cursor.rowcount


def insert(
    conn: sqlite3.Connection,
    table: str,
    obj: BaseModel,
    exclude: set[str] | None = None,
    *,
    commit: bool = True,
) -> int:
    """Insert a model into a table.

    Args:
        conn: SQLite connection.
        table: Table name.
        obj: Pydantic model to insert.
        exclude: Field names to exclude from the insert.
        commit: Whether to commit the transaction (default True).

    Returns:
        The lastrowid of the inserted row, or 0 if not available.

    Examples:
        >>> class Record(BaseModel):
        ...     id: int | None = None
        ...     name: str
        ...     code: str
        >>> record = Record(name="first", code="A001")
        >>> insert(conn, "records", record, exclude={"id"})
        1
        >>> # Batch inserts without auto-commit
        >>> insert(conn, "records", record1, exclude={"id"}, commit=False)
        2
        >>> insert(conn, "records", record2, exclude={"id"}, commit=False)
        3
        >>> conn.commit()  # Commit both at once
    """
    table = safe_identifier(table)
    data = obj.model_dump(exclude=exclude or set(), exclude_none=True)
    cols = ", ".join(safe_identifier(k) for k in data)
    placeholders = ", ".join(f":{k}" for k in data)
    cursor = conn.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",  # noqa: S608
        data,
    )
    if commit:
        conn.commit()
    return cursor.lastrowid or 0


def update(  # noqa: PLR0913
    conn: sqlite3.Connection,
    table: str,
    obj: BaseModel,
    key_column: str = "id",
    exclude: set[str] | None = None,
    *,
    commit: bool = True,
) -> int:
    """Update a row in a table.

    Args:
        conn: SQLite connection.
        table: Table name.
        obj: Pydantic model with updated values.
        key_column: Column name to use for the WHERE clause (default "id").
        exclude: Additional field names to exclude from the update.
        commit: Whether to commit the transaction (default True).

    Returns:
        Number of rows affected.

    Raises:
        AttributeError: If the model lacks the key_column attribute.

    Examples:
        >>> class Record(BaseModel):
        ...     id: int
        ...     name: str
        ...     code: str
        >>> record = Record(id=1, name="updated", code="A001")
        >>> update(conn, "records", record)
        1
        >>> # Update using a different key column
        >>> update(conn, "records", record, key_column="code")
        1
        >>> # Exclude fields from the update
        >>> update(conn, "records", record, exclude={"code"})
        1
    """
    safe_table = safe_identifier(table)
    safe_key_col = safe_identifier(key_column)
    exclude = (exclude or set()) | {key_column}
    data = obj.model_dump(exclude=exclude, exclude_none=True)
    key_value = cast("SQLValue", getattr(obj, key_column))

    sets = ", ".join(f"{safe_identifier(k)} = :{k}" for k in data)
    data[key_column] = key_value

    cursor = conn.execute(
        f"UPDATE {safe_table} SET {sets} WHERE {safe_key_col} = :{key_column}",  # noqa: S608
        data,
    )
    if commit:
        conn.commit()
    return cursor.rowcount


def delete(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key_value: str | int,
    *,
    commit: bool = True,
) -> int:
    """Delete a row from a table.

    Args:
        conn: SQLite connection.
        table: Table name.
        key_column: Column name to use for the WHERE clause.
        key_value: Value to match in the key column.
        commit: Whether to commit the transaction (default True).

    Returns:
        Number of rows affected.

    Examples:
        >>> delete(conn, "records", "id", 1)
        1
        >>> delete(conn, "records", "code", "A001")
        1
        >>> delete(conn, "records", "id", 999)  # No matching row
        0
    """
    table = safe_identifier(table)
    key_column = safe_identifier(key_column)
    cursor = conn.execute(
        f"DELETE FROM {table} WHERE {key_column} = ?",  # noqa: S608
        (key_value,),
    )
    if commit:
        conn.commit()
    return cursor.rowcount


def upsert(  # noqa: PLR0913
    conn: sqlite3.Connection,
    table: str,
    obj: BaseModel,
    conflict_columns: list[str],
    exclude: set[str] | None = None,
    *,
    commit: bool = True,
) -> int:
    """Insert or update on conflict.

    If a row with matching conflict_columns exists, updates the non-conflict
    columns. If all data columns are conflict columns, uses DO NOTHING.

    Args:
        conn: SQLite connection.
        table: Table name.
        obj: Pydantic model to upsert.
        conflict_columns: Columns to check for conflicts.
        exclude: Field names to exclude from the upsert.
        commit: Whether to commit the transaction (default True).

    Returns:
        The lastrowid of the upserted row, or 0 if not available.

    Examples:
        >>> class Record(BaseModel):
        ...     id: int | None = None
        ...     name: str
        ...     code: str
        >>> record = Record(name="first", code="A001")
        >>> upsert(conn, "records", record, conflict_columns=["code"], exclude={"id"})
        1
        >>> # Update name if code already exists
        >>> record2 = Record(name="updated", code="A001")
        >>> upsert(conn, "records", record2, conflict_columns=["code"], exclude={"id"})
        1
    """
    table = safe_identifier(table)
    safe_conflict_cols = [safe_identifier(col) for col in conflict_columns]
    data = obj.model_dump(exclude=exclude or set(), exclude_none=True)
    cols = ", ".join(safe_identifier(k) for k in data)
    placeholders = ", ".join(f":{k}" for k in data)
    conflict = ", ".join(safe_conflict_cols)
    updates = ", ".join(
        f"{safe_identifier(k)} = excluded.{safe_identifier(k)}"
        for k in data
        if k not in conflict_columns
    )

    if updates:
        sql = f"""INSERT INTO {table} ({cols}) VALUES ({placeholders})
            ON CONFLICT ({conflict}) DO UPDATE SET {updates}"""  # noqa: S608
    else:
        sql = f"""INSERT INTO {table} ({cols}) VALUES ({placeholders})
            ON CONFLICT ({conflict}) DO NOTHING"""  # noqa: S608

    cursor = conn.execute(sql, data)
    if commit:
        conn.commit()
    return cursor.lastrowid or 0
