import math
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

import pendulum
import pytest
from pydantic import BaseModel, Field, ValidationError
from pydantic_extra_types.pendulum_dt import (
    Date as PendulumDate,
    DateTime as PendulumDateTime,
    Duration as PendulumDuration,
    Time as PendulumTime,
)

from oaps.utils.database import (
    connect,
    delete,
    fetch_all,
    fetch_one,
    insert,
    insert_all,
    update,
    upsert,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class Record(BaseModel):
    id: int | None = None
    name: str
    code: str


class ChildRecord(BaseModel):
    id: int | None = None
    parent_id: int
    label: str
    description: str | None = None


class ReservedWordsModel(BaseModel):
    """Model with SQL reserved words as field names."""

    id: int | None = None
    order: int
    select: str


class _TestError(Exception):
    """Test exception for connect tests."""


def _raise_test_error() -> None:
    raise _TestError


@pytest.fixture
def conn() -> "Iterator[sqlite3.Connection]":  # noqa: UP037
    with connect(":memory:") as connection:
        _ = connection.execute("""
            CREATE TABLE records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE
            )
        """)
        _ = connection.execute("""
            CREATE TABLE children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (parent_id) REFERENCES records(id)
            )
        """)
        _ = connection.execute("""
            CREATE TABLE "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                "order" INTEGER NOT NULL,
                "select" TEXT NOT NULL
            )
        """)
        connection.commit()
        yield connection


@pytest.fixture
def record() -> Record:
    return Record(name="first", code="A001")


@pytest.fixture
def inserted_record(conn: sqlite3.Connection, record: Record) -> Record:
    """Insert a record and return it with the assigned id."""
    row_id = insert(conn, "records", record, exclude={"id"})
    return Record(id=row_id, name=record.name, code=record.code)


class TestInsert:
    def test_returns_lastrowid(self, conn: sqlite3.Connection, record: Record) -> None:
        row_id = insert(conn, "records", record, exclude={"id"})

        assert row_id == 1

    def test_stores_data_correctly(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))
        assert result is not None
        assert result.name == inserted_record.name
        assert result.code == inserted_record.code

    def test_multiple_rows_increments_id(self, conn: sqlite3.Connection) -> None:
        record1 = Record(name="first", code="A001")
        record2 = Record(name="second", code="B002")

        id1 = insert(conn, "records", record1, exclude={"id"})
        id2 = insert(conn, "records", record2, exclude={"id"})

        assert id1 == 1
        assert id2 == 2

    def test_excludes_none_values(self, conn: sqlite3.Connection) -> None:
        child = ChildRecord(parent_id=1, label="test", description=None)

        _ = insert(conn, "children", child, exclude={"id"})

        result = fetch_one(
            conn, ChildRecord, "SELECT * FROM children WHERE id = ?", (1,)
        )
        assert result is not None
        assert result.label == "test"
        assert result.description is None

    def test_with_reserved_word_table_name(self, conn: sqlite3.Connection) -> None:
        model = ReservedWordsModel(order=1, select="test")

        row_id = insert(conn, "order", model, exclude={"id"})

        assert row_id == 1

    def test_with_reserved_word_column_names(self, conn: sqlite3.Connection) -> None:
        model = ReservedWordsModel(order=42, select="value")

        _ = insert(conn, "order", model, exclude={"id"})

        result = fetch_one(
            conn, ReservedWordsModel, 'SELECT * FROM "order" WHERE id = ?', (1,)
        )
        assert result is not None
        assert result.order == 42
        assert result.select == "value"

    def test_rejects_malicious_table_name(
        self, conn: sqlite3.Connection, record: Record
    ) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _ = insert(conn, "records; DROP TABLE records--", record, exclude={"id"})


class TestInsertAll:
    def test_returns_row_count(self, conn: sqlite3.Connection) -> None:
        records = [
            Record(name="first", code="A001"),
            Record(name="second", code="B002"),
            Record(name="third", code="C003"),
        ]

        count = insert_all(conn, "records", records, exclude={"id"})

        assert count == 3

    def test_stores_data_correctly(self, conn: sqlite3.Connection) -> None:
        records = [
            Record(name="first", code="A001"),
            Record(name="second", code="B002"),
        ]

        _ = insert_all(conn, "records", records, exclude={"id"})

        results = fetch_all(conn, Record, "SELECT * FROM records ORDER BY id")
        assert len(results) == 2
        assert results[0].name == "first"
        assert results[0].code == "A001"
        assert results[1].name == "second"
        assert results[1].code == "B002"

    def test_empty_list_returns_zero(self, conn: sqlite3.Connection) -> None:
        count = insert_all(conn, "records", [], exclude={"id"})

        assert count == 0
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert results == []

    def test_single_item_list(self, conn: sqlite3.Connection) -> None:
        records = [Record(name="only", code="X001")]

        count = insert_all(conn, "records", records, exclude={"id"})

        assert count == 1
        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))
        assert result is not None
        assert result.name == "only"

    def test_excludes_none_values(self, conn: sqlite3.Connection) -> None:
        children = [
            ChildRecord(parent_id=1, label="child1", description=None),
            ChildRecord(parent_id=1, label="child2", description=None),
        ]

        count = insert_all(conn, "children", children, exclude={"id"})

        assert count == 2
        results = fetch_all(conn, ChildRecord, "SELECT * FROM children ORDER BY id")
        assert len(results) == 2
        assert results[0].description is None
        assert results[1].description is None

    def test_with_reserved_word_table_name(self, conn: sqlite3.Connection) -> None:
        models = [
            ReservedWordsModel(order=1, select="first"),
            ReservedWordsModel(order=2, select="second"),
        ]

        count = insert_all(conn, "order", models, exclude={"id"})

        assert count == 2

    def test_with_reserved_word_column_names(self, conn: sqlite3.Connection) -> None:
        models = [
            ReservedWordsModel(order=10, select="value1"),
            ReservedWordsModel(order=20, select="value2"),
        ]

        _ = insert_all(conn, "order", models, exclude={"id"})

        results = fetch_all(
            conn, ReservedWordsModel, 'SELECT * FROM "order" ORDER BY id'
        )
        assert len(results) == 2
        assert results[0].order == 10
        assert results[0].select == "value1"
        assert results[1].order == 20
        assert results[1].select == "value2"

    def test_rejects_malicious_table_name(self, conn: sqlite3.Connection) -> None:
        records = [Record(name="first", code="A001")]

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _ = insert_all(
                conn, "records; DROP TABLE records--", records, exclude={"id"}
            )

    def test_with_commit_false(self, conn: sqlite3.Connection) -> None:
        records = [
            Record(name="first", code="A001"),
            Record(name="second", code="B002"),
        ]

        _ = insert_all(conn, "records", records, exclude={"id"}, commit=False)

        # Data visible in same transaction
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 2

        # Rollback undoes uncommitted changes
        conn.rollback()
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 0

    def test_batching_with_manual_commit(self, conn: sqlite3.Connection) -> None:
        batch1 = [Record(name="a", code="A001"), Record(name="b", code="B002")]
        batch2 = [Record(name="c", code="C003"), Record(name="d", code="D004")]

        _ = insert_all(conn, "records", batch1, exclude={"id"}, commit=False)
        _ = insert_all(conn, "records", batch2, exclude={"id"}, commit=False)
        conn.commit()

        # Rollback has no effect after commit
        conn.rollback()
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 4


class TestFetch:
    def test_one_returns_model(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))

        assert result is not None
        assert result == inserted_record

    def test_one_returns_none_when_not_found(self, conn: sqlite3.Connection) -> None:
        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (999,))

        assert result is None

    def test_all_returns_list_of_models(self, conn: sqlite3.Connection) -> None:
        _ = insert(conn, "records", Record(name="first", code="A001"), exclude={"id"})
        _ = insert(conn, "records", Record(name="second", code="B002"), exclude={"id"})

        results = fetch_all(conn, Record, "SELECT * FROM records ORDER BY id")

        assert len(results) == 2
        assert results[0].name == "first"
        assert results[1].name == "second"

    def test_all_returns_empty_list_when_no_results(
        self, conn: sqlite3.Connection
    ) -> None:
        results = fetch_all(conn, Record, "SELECT * FROM records")

        assert results == []

    def test_with_float_param(self, conn: sqlite3.Connection) -> None:
        class FloatModel(BaseModel):
            id: int | None = None
            value: float

        _ = conn.execute(
            "CREATE TABLE floats (id INTEGER PRIMARY KEY, value REAL NOT NULL)"
        )
        conn.commit()
        _ = insert(conn, "floats", FloatModel(value=3.14159), exclude={"id"})

        result = fetch_one(
            conn, FloatModel, "SELECT * FROM floats WHERE value > ?", (3.0,)
        )

        assert result is not None
        assert math.isclose(result.value, 3.14159, rel_tol=1e-9)

    def test_with_bytes_param(self, conn: sqlite3.Connection) -> None:
        class BinaryModel(BaseModel):
            id: int | None = None
            data: bytes

        _ = conn.execute(
            "CREATE TABLE binaries (id INTEGER PRIMARY KEY, data BLOB NOT NULL)"
        )
        conn.commit()
        test_bytes = b"\x00\x01\x02\xff"
        _ = insert(conn, "binaries", BinaryModel(data=test_bytes), exclude={"id"})

        result = fetch_one(
            conn, BinaryModel, "SELECT * FROM binaries WHERE data = ?", (test_bytes,)
        )

        assert result is not None
        assert result.data == test_bytes

    def test_validates_database_row(self, conn: sqlite3.Connection) -> None:
        _ = insert(conn, "records", Record(name="first", code="A001"), exclude={"id"})

        class StrictModel(BaseModel):
            id: int
            name: str
            code: str
            extra_field: str

        with pytest.raises(ValidationError) as exc_info:
            _ = fetch_one(conn, StrictModel, "SELECT * FROM records WHERE id = ?", (1,))

        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("extra_field",)
        assert errors[0]["type"] == "missing"


class TestUpdate:
    def test_modifies_row(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        updated = Record(id=inserted_record.id, name="updated", code="X999")

        rowcount = update(conn, "records", updated)

        assert rowcount == 1
        result = fetch_one(
            conn, Record, "SELECT * FROM records WHERE id = ?", (inserted_record.id,)
        )
        assert result is not None
        assert result.name == "updated"
        assert result.code == "X999"

    def test_returns_zero_when_not_found(self, conn: sqlite3.Connection) -> None:
        nonexistent = Record(id=999, name="ghost", code="Z000")

        rowcount = update(conn, "records", nonexistent)

        assert rowcount == 0

    def test_with_custom_key_column(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        updated = Record(id=999, name="updated", code=inserted_record.code)

        rowcount = update(conn, "records", updated, key_column="code")

        assert rowcount == 1
        result = fetch_one(
            conn,
            Record,
            "SELECT * FROM records WHERE code = ?",
            (inserted_record.code,),
        )
        assert result is not None
        assert result.name == "updated"

    def test_exclude_parameter(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        updated = Record(
            id=inserted_record.id,
            name="updated",
            code="should_not_update",
        )

        rowcount = update(conn, "records", updated, exclude={"code"})

        assert rowcount == 1
        result = fetch_one(
            conn, Record, "SELECT * FROM records WHERE id = ?", (inserted_record.id,)
        )
        assert result is not None
        assert result.name == "updated"
        assert result.code == inserted_record.code  # Original code preserved

    def test_raises_attribute_error_for_missing_key_column(
        self, conn: sqlite3.Connection
    ) -> None:
        _ = conn.execute(
            "CREATE TABLE simple (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        conn.commit()

        class SimpleModel(BaseModel):
            name: str

        model = SimpleModel(name="test")

        with pytest.raises(AttributeError):
            _ = update(conn, "simple", model, key_column="id")

    def test_with_reserved_word_table_and_columns(
        self, conn: sqlite3.Connection
    ) -> None:
        model = ReservedWordsModel(order=1, select="initial")
        _ = insert(conn, "order", model, exclude={"id"})
        updated = ReservedWordsModel(id=1, order=99, select="updated")

        rowcount = update(conn, "order", updated)

        assert rowcount == 1
        result = fetch_one(
            conn, ReservedWordsModel, 'SELECT * FROM "order" WHERE id = ?', (1,)
        )
        assert result is not None
        assert result.order == 99
        assert result.select == "updated"

    def test_rejects_malicious_key_column(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        updated = Record(id=inserted_record.id, name="hacked", code="evil")

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _ = update(conn, "records", updated, key_column="id; DROP TABLE records--")


class TestDelete:
    def test_removes_row(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        assert inserted_record.id is not None
        rowcount = delete(conn, "records", "id", inserted_record.id)

        assert rowcount == 1
        result = fetch_one(
            conn, Record, "SELECT * FROM records WHERE id = ?", (inserted_record.id,)
        )
        assert result is None

    def test_returns_zero_when_not_found(self, conn: sqlite3.Connection) -> None:
        rowcount = delete(conn, "records", "id", 999)

        assert rowcount == 0

    def test_with_reserved_word_table(self, conn: sqlite3.Connection) -> None:
        model = ReservedWordsModel(order=1, select="test")
        _ = insert(conn, "order", model, exclude={"id"})

        rowcount = delete(conn, "order", "id", 1)

        assert rowcount == 1

    def test_rejects_malicious_table_name(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _ = delete(conn, "records'; DROP TABLE records--", "id", 1)


class TestUpsert:
    def test_inserts_new_row(self, conn: sqlite3.Connection, record: Record) -> None:
        row_id = upsert(
            conn, "records", record, conflict_columns=["code"], exclude={"id"}
        )

        assert row_id == 1
        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))
        assert result is not None
        assert result.name == "first"

    def test_updates_on_conflict(
        self, conn: sqlite3.Connection, inserted_record: Record
    ) -> None:
        updated = Record(name="updated", code=inserted_record.code)

        _ = upsert(conn, "records", updated, conflict_columns=["code"], exclude={"id"})

        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 1
        assert results[0].name == "updated"

    def test_does_nothing_when_all_columns_are_conflict(
        self, conn: sqlite3.Connection
    ) -> None:
        _ = conn.execute("CREATE TABLE singles (value TEXT PRIMARY KEY)")
        conn.commit()

        class SingleFieldModel(BaseModel):
            value: str

        model = SingleFieldModel(value="test")
        _ = upsert(conn, "singles", model, conflict_columns=["value"])
        _ = upsert(conn, "singles", model, conflict_columns=["value"])

        results = fetch_all(conn, SingleFieldModel, "SELECT * FROM singles")
        assert len(results) == 1
        assert results[0].value == "test"

    def test_rejects_malicious_conflict_column(
        self, conn: sqlite3.Connection, record: Record
    ) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _ = upsert(
                conn,
                "records",
                record,
                conflict_columns=["code; DROP TABLE records--"],
                exclude={"id"},
            )


class TestConnect:
    def test_commits_on_successful_exit(self) -> None:
        with connect(":memory:") as conn:
            _ = conn.execute("CREATE TABLE t (x INTEGER)")
            _ = conn.execute("INSERT INTO t (x) VALUES (42)")

    def test_rolls_back_on_exception(self) -> None:
        with pytest.raises(_TestError), connect(":memory:") as conn:
            _ = conn.execute("CREATE TABLE t (x INTEGER)")
            _ = conn.execute("INSERT INTO t (x) VALUES (42)")
            _raise_test_error()

    def test_closes_connection_on_exit(self) -> None:
        conn_ref: sqlite3.Connection | None = None
        with connect(":memory:") as conn:
            conn_ref = conn
            _ = conn.execute("CREATE TABLE t (x INTEGER)")

        assert conn_ref is not None
        with pytest.raises(
            sqlite3.ProgrammingError, match="Cannot operate on a closed"
        ):
            _ = conn_ref.execute("SELECT 1")

    def test_closes_connection_on_exception(self) -> None:
        conn_ref: sqlite3.Connection | None = None
        with pytest.raises(_TestError), connect(":memory:") as conn:
            conn_ref = conn
            _raise_test_error()

        assert conn_ref is not None
        with pytest.raises(
            sqlite3.ProgrammingError, match="Cannot operate on a closed"
        ):
            _ = conn_ref.execute("SELECT 1")

    def test_sets_row_factory(self) -> None:
        with connect(":memory:") as conn:
            _ = conn.execute("CREATE TABLE t (x INTEGER, y TEXT)")
            _ = conn.execute("INSERT INTO t (x, y) VALUES (1, 'hello')")

            row = cast("sqlite3.Row | None", conn.execute("SELECT * FROM t").fetchone())
            assert row is not None
            assert row["x"] == 1
            assert row["y"] == "hello"

    def test_propagates_exception_after_rollback(self) -> None:
        with pytest.raises(_TestError), connect(":memory:") as conn:
            _ = conn.execute("CREATE TABLE t (x INTEGER)")
            _raise_test_error()


class TestTransactions:
    def test_batching_with_commit_false(self, conn: sqlite3.Connection) -> None:
        record1 = Record(name="first", code="A001")
        record2 = Record(name="second", code="B002")

        _ = insert(conn, "records", record1, exclude={"id"}, commit=False)
        _ = insert(conn, "records", record2, exclude={"id"}, commit=False)

        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 2

        conn.rollback()
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 0

    def test_batching_commits_atomically(self, conn: sqlite3.Connection) -> None:
        record1 = Record(name="first", code="A001")
        record2 = Record(name="second", code="B002")

        _ = insert(conn, "records", record1, exclude={"id"}, commit=False)
        _ = insert(conn, "records", record2, exclude={"id"}, commit=False)
        conn.commit()

        conn.rollback()
        results = fetch_all(conn, Record, "SELECT * FROM records")
        assert len(results) == 2


class TestPydanticValidation:
    def test_coerces_compatible_types(self, conn: sqlite3.Connection) -> None:
        _ = insert(conn, "records", Record(name="first", code="A001"), exclude={"id"})

        result = fetch_one(conn, Record, "SELECT * FROM records WHERE id = ?", (1,))

        assert result is not None
        assert isinstance(result.id, int)
        assert result.id == 1

    def test_coerces_string_to_int_when_valid(self, conn: sqlite3.Connection) -> None:
        _ = conn.execute(
            "CREATE TABLE integers (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"
        )
        conn.commit()

        class IntModel(BaseModel):
            id: int
            value: int

        _ = conn.execute("INSERT INTO integers (value) VALUES (?)", ("42",))
        conn.commit()

        result = fetch_one(conn, IntModel, "SELECT * FROM integers WHERE id = ?", (1,))

        assert result is not None
        assert result.value == 42
        assert isinstance(result.value, int)

    def test_validates_nested_constraints(self, conn: sqlite3.Connection) -> None:
        class BoundedModel(BaseModel):
            id: int | None = None
            value: int = Field(ge=0, le=100)

        _ = conn.execute(
            "CREATE TABLE bounded (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"
        )
        conn.commit()

        model = BoundedModel(value=50)
        _ = insert(conn, "bounded", model, exclude={"id"})

        result = fetch_one(
            conn, BoundedModel, "SELECT * FROM bounded WHERE id = ?", (1,)
        )
        assert result is not None
        assert result.value == 50


class TestDatetimeSerialization:
    def test_from_iso_string(self, conn: sqlite3.Connection) -> None:
        class DateTimeModel(BaseModel):
            id: int | None = None
            name: str
            ts: datetime

        _ = conn.execute(
            "CREATE TABLE datetimes (id INTEGER PRIMARY KEY, name TEXT, ts TEXT)"
        )
        conn.commit()

        iso_str = "2024-06-15T12:30:45+00:00"
        _ = conn.execute(
            "INSERT INTO datetimes (name, ts) VALUES (?, ?)",
            ("test", iso_str),
        )
        conn.commit()

        result = fetch_one(
            conn, DateTimeModel, "SELECT * FROM datetimes WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.ts, datetime)
        assert result.ts.year == 2024
        assert result.ts.month == 6
        assert result.ts.day == 15
        assert result.ts.hour == 12
        assert result.ts.tzinfo is not None

    def test_naive_datetime(self, conn: sqlite3.Connection) -> None:
        class NaiveDateTimeModel(BaseModel):
            id: int | None = None
            ts: datetime

        _ = conn.execute("CREATE TABLE naive_ts (id INTEGER PRIMARY KEY, ts TEXT)")
        conn.commit()

        _ = conn.execute(
            "INSERT INTO naive_ts (ts) VALUES (?)", ("2024-01-01T00:00:00",)
        )
        conn.commit()

        result = fetch_one(
            conn, NaiveDateTimeModel, "SELECT * FROM naive_ts WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.ts, datetime)
        assert result.ts.tzinfo is None


class TestTimedeltaSerialization:
    def test_from_iso_duration(self, conn: sqlite3.Connection) -> None:
        class DurationModel(BaseModel):
            id: int | None = None
            name: str
            delta: timedelta

        _ = conn.execute(
            "CREATE TABLE durations (id INTEGER PRIMARY KEY, name TEXT, delta TEXT)"
        )
        conn.commit()

        _ = conn.execute(
            "INSERT INTO durations (name, delta) VALUES (?, ?)",
            ("test", "PT2H30M15S"),
        )
        conn.commit()

        result = fetch_one(
            conn, DurationModel, "SELECT * FROM durations WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.delta, timedelta)
        assert result.delta.total_seconds() == 2 * 3600 + 30 * 60 + 15

    @pytest.mark.parametrize(
        ("iso_duration", "expected"),
        [
            ("PT0S", timedelta(0)),  # zero duration
            ("P1D", timedelta(days=1)),  # 1 day
            ("P1DT5H", timedelta(days=1, hours=5)),  # 1 day, 5 hours
            ("PT1H30M", timedelta(hours=1, minutes=30)),  # 1.5 hours
            ("P7D", timedelta(weeks=1)),  # 1 week as days
        ],
    )
    def test_various_formats(
        self, conn: sqlite3.Connection, iso_duration: str, expected: timedelta
    ) -> None:
        class DeltaModel(BaseModel):
            id: int | None = None
            delta: timedelta

        _ = conn.execute("CREATE TABLE deltas (id INTEGER PRIMARY KEY, delta TEXT)")
        conn.commit()

        _ = conn.execute("INSERT INTO deltas (delta) VALUES (?)", (iso_duration,))
        conn.commit()

        result = fetch_one(conn, DeltaModel, "SELECT * FROM deltas WHERE id = ?", (1,))
        assert result is not None
        assert result.delta == expected


class TestUuidSerialization:
    def test_uuid7_from_string(self, conn: sqlite3.Connection) -> None:
        class UuidModel(BaseModel):
            id: int | None = None
            uid: uuid.UUID

        _ = conn.execute("CREATE TABLE uuids (id INTEGER PRIMARY KEY, uid TEXT)")
        conn.commit()

        test_uuid = uuid.uuid7()
        _ = conn.execute("INSERT INTO uuids (uid) VALUES (?)", (str(test_uuid),))
        conn.commit()

        result = fetch_one(conn, UuidModel, "SELECT * FROM uuids WHERE id = ?", (1,))
        assert result is not None
        assert result.uid == test_uuid
        assert isinstance(result.uid, uuid.UUID)
        assert result.uid.version == 7

    def test_multiple_versions(self, conn: sqlite3.Connection) -> None:
        class VersionedUuidModel(BaseModel):
            id: int | None = None
            uid: uuid.UUID
            version: int

        _ = conn.execute("""
            CREATE TABLE versioned_uuids
            (id INTEGER PRIMARY KEY, uid TEXT, version INT)
        """)
        conn.commit()

        uuid4 = uuid.uuid4()
        uuid7 = uuid.uuid7()

        _ = conn.execute(
            "INSERT INTO versioned_uuids (uid, version) VALUES (?, ?)", (str(uuid4), 4)
        )
        _ = conn.execute(
            "INSERT INTO versioned_uuids (uid, version) VALUES (?, ?)", (str(uuid7), 7)
        )
        conn.commit()

        results = fetch_all(
            conn, VersionedUuidModel, "SELECT * FROM versioned_uuids ORDER BY id"
        )
        assert len(results) == 2

        assert results[0].uid == uuid4
        assert results[0].uid.version == 4

        assert results[1].uid == uuid7
        assert results[1].uid.version == 7

    def test_from_string_coercion(self, conn: sqlite3.Connection) -> None:
        class UuidRecordModel(BaseModel):
            id: int | None = None
            uid: uuid.UUID

        _ = conn.execute("CREATE TABLE uuid_records (id INTEGER PRIMARY KEY, uid TEXT)")
        conn.commit()

        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        _ = conn.execute("INSERT INTO uuid_records (uid) VALUES (?)", (uuid_str,))
        conn.commit()

        result = fetch_one(
            conn, UuidRecordModel, "SELECT * FROM uuid_records WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.uid, uuid.UUID)
        assert str(result.uid) == uuid_str


class TestPendulumDatetimeSerialization:
    def test_basic_deserialization(self, conn: sqlite3.Connection) -> None:
        class PendulumDateTimeModel(BaseModel):
            id: int | None = None
            ts: PendulumDateTime

        _ = conn.execute(
            "CREATE TABLE pendulum_datetimes (id INTEGER PRIMARY KEY, ts TEXT)"
        )
        conn.commit()

        _ = conn.execute(
            "INSERT INTO pendulum_datetimes (ts) VALUES (?)",
            ("2024-06-15T14:30:00+02:00",),
        )
        conn.commit()

        result = fetch_one(
            conn,
            PendulumDateTimeModel,
            "SELECT * FROM pendulum_datetimes WHERE id = ?",
            (1,),
        )
        assert result is not None
        assert isinstance(result.ts, pendulum.DateTime)
        assert result.ts.year == 2024
        assert result.ts.month == 6
        assert result.ts.day == 15
        assert result.ts.hour == 14
        assert result.ts.minute == 30

    def test_timezone_handling(self, conn: sqlite3.Connection) -> None:
        class TzDateTimeModel(BaseModel):
            id: int | None = None
            ts: PendulumDateTime

        _ = conn.execute("CREATE TABLE tz_datetimes (id INTEGER PRIMARY KEY, ts TEXT)")
        conn.commit()

        _ = conn.execute(
            "INSERT INTO tz_datetimes (ts) VALUES (?)",
            ("2024-12-25T00:00:00Z",),
        )
        conn.commit()

        result = fetch_one(
            conn, TzDateTimeModel, "SELECT * FROM tz_datetimes WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.ts, pendulum.DateTime)
        assert result.ts.timezone is not None


class TestPendulumDateSerialization:
    def test_basic_deserialization(self, conn: sqlite3.Connection) -> None:
        class PendulumDateModel(BaseModel):
            id: int | None = None
            d: PendulumDate

        _ = conn.execute("CREATE TABLE pendulum_dates (id INTEGER PRIMARY KEY, d TEXT)")
        conn.commit()

        _ = conn.execute("INSERT INTO pendulum_dates (d) VALUES (?)", ("1990-05-20",))
        conn.commit()

        result = fetch_one(
            conn, PendulumDateModel, "SELECT * FROM pendulum_dates WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.d, pendulum.Date)
        assert result.d.year == 1990
        assert result.d.month == 5
        assert result.d.day == 20


class TestPendulumTimeSerialization:
    def test_basic_deserialization(self, conn: sqlite3.Connection) -> None:
        class PendulumTimeModel(BaseModel):
            id: int | None = None
            t: PendulumTime

        _ = conn.execute("CREATE TABLE pendulum_times (id INTEGER PRIMARY KEY, t TEXT)")
        conn.commit()

        _ = conn.execute("INSERT INTO pendulum_times (t) VALUES (?)", ("07:30:00",))
        conn.commit()

        result = fetch_one(
            conn, PendulumTimeModel, "SELECT * FROM pendulum_times WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.t, pendulum.Time)
        assert result.t.hour == 7
        assert result.t.minute == 30
        assert result.t.second == 0

    def test_with_microseconds(self, conn: sqlite3.Connection) -> None:
        class PreciseTimeModel(BaseModel):
            id: int | None = None
            t: PendulumTime

        _ = conn.execute("CREATE TABLE precise_times (id INTEGER PRIMARY KEY, t TEXT)")
        conn.commit()

        _ = conn.execute(
            "INSERT INTO precise_times (t) VALUES (?)", ("12:34:56.789012",)
        )
        conn.commit()

        result = fetch_one(
            conn, PreciseTimeModel, "SELECT * FROM precise_times WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.t, pendulum.Time)
        assert result.t.hour == 12
        assert result.t.minute == 34
        assert result.t.second == 56
        assert result.t.microsecond == 789012


class TestPendulumDurationSerialization:
    def test_basic_deserialization(self, conn: sqlite3.Connection) -> None:
        class PendulumDurationModel(BaseModel):
            id: int | None = None
            delta: PendulumDuration

        _ = conn.execute(
            "CREATE TABLE pendulum_durations (id INTEGER PRIMARY KEY, delta TEXT)"
        )
        conn.commit()

        _ = conn.execute(
            "INSERT INTO pendulum_durations (delta) VALUES (?)", ("PT1H30M",)
        )
        conn.commit()

        result = fetch_one(
            conn,
            PendulumDurationModel,
            "SELECT * FROM pendulum_durations WHERE id = ?",
            (1,),
        )
        assert result is not None
        assert isinstance(result.delta, pendulum.Duration)
        assert result.delta.in_minutes() == 90

    def test_with_days(self, conn: sqlite3.Connection) -> None:
        class LongDurationModel(BaseModel):
            id: int | None = None
            delta: PendulumDuration

        _ = conn.execute(
            "CREATE TABLE long_durations (id INTEGER PRIMARY KEY, delta TEXT)"
        )
        conn.commit()

        _ = conn.execute("INSERT INTO long_durations (delta) VALUES (?)", ("P30D",))
        conn.commit()

        result = fetch_one(
            conn, LongDurationModel, "SELECT * FROM long_durations WHERE id = ?", (1,)
        )
        assert result is not None
        assert isinstance(result.delta, pendulum.Duration)
        assert result.delta.in_days() == 30
