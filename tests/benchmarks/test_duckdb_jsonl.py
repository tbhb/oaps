"""Benchmark DuckDB performance for JSONL-based spec storage.

This benchmark tests the hypothesis that DuckDB can efficiently query
JSONL files directly, eliminating the need for a separate cache layer.

Test scenarios:
1. Generate 100 JSONL files, each with 100 requirements (10,000 total)
2. Benchmark loading single file with orjson
3. Benchmark loading all files with DuckDB glob pattern
4. Benchmark aggregation queries across all files
5. Benchmark point lookups by ID
"""

from __future__ import annotations

import random
import shutil
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import orjson
import polars as pl
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_benchmark.fixture import BenchmarkFixture

# Requirement schema fields based on src/oaps/spec/_models.py
REQUIREMENT_TYPES = ["functional", "quality", "security", "interface", "constraint"]
REQUIREMENT_STATUSES = [
    "proposed",
    "approved",
    "implementing",
    "implemented",
    "verified",
]
TAGS = ["api", "cli", "core", "ui", "database", "auth", "config", "hooks", "spec"]


def generate_requirement(spec_id: str, req_num: int) -> dict:
    """Generate a realistic requirement record."""
    req_type = random.choice(REQUIREMENT_TYPES)
    status = random.choice(REQUIREMENT_STATUSES)
    base_time = datetime(2025, 1, 1, tzinfo=UTC)

    return {
        "id": f"REQ-{spec_id}-{req_num:04d}",
        "spec_id": spec_id,
        "title": f"Requirement {req_num} for {spec_id}",
        "req_type": req_type,
        "status": status,
        "created": (base_time + timedelta(days=random.randint(0, 365))).isoformat(),
        "updated": (base_time + timedelta(days=random.randint(0, 365))).isoformat(),
        "author": random.choice(["alice", "bob", "carol", "dave", "eve"]),
        "description": f"This is a {req_type} requirement that describes functionality for {spec_id}. "
        * 3,
        "rationale": f"This requirement exists because of business need #{random.randint(1, 100)}.",
        "acceptance_criteria": [f"Criterion {i}" for i in range(random.randint(1, 5))],
        "verified_by": [f"TEST-{spec_id}-{i:04d}" for i in range(random.randint(0, 3))],
        "depends_on": [],
        "tags": random.sample(TAGS, k=random.randint(1, 4)),
        "source_section": f"docs/spec-{spec_id}.md#section-{req_num}",
    }


def generate_jsonl_file(path: Path, spec_id: str, num_requirements: int) -> None:
    """Generate a JSONL file with requirements."""
    with path.open("wb") as f:
        for i in range(num_requirements):
            req = generate_requirement(spec_id, i)
            f.write(orjson.dumps(req))
            f.write(b"\n")


@pytest.fixture(scope="module")
def jsonl_dir() -> Generator[Path, None, None]:
    """Create temp directory with 100 JSONL files, 100 requirements each."""
    tmpdir = Path(tempfile.mkdtemp(prefix="duckdb_bench_"))

    # Generate 100 specs, each with 100 requirements
    num_specs = 100
    reqs_per_spec = 100

    for i in range(num_specs):
        spec_id = f"SPEC-{i:04d}"
        spec_dir = tmpdir / spec_id
        spec_dir.mkdir()
        jsonl_path = spec_dir / "requirements.jsonl"
        generate_jsonl_file(jsonl_path, spec_id, reqs_per_spec)

    yield tmpdir

    # Cleanup
    shutil.rmtree(tmpdir)


@pytest.fixture(scope="module")
def duckdb_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create in-memory DuckDB connection."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestDuckDBJsonlBenchmarks:
    """Benchmark suite for DuckDB JSONL operations."""

    def test_load_single_file_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load single JSONL file with orjson."""
        jsonl_path = jsonl_dir / "SPEC-0000" / "requirements.jsonl"

        def load_with_orjson() -> list:
            with jsonl_path.open("rb") as f:
                return [orjson.loads(line) for line in f]

        result = benchmark(load_with_orjson)
        assert len(result) == 100

    def test_load_single_file_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Load single JSONL file with DuckDB."""
        jsonl_path = jsonl_dir / "SPEC-0000" / "requirements.jsonl"

        def load_with_duckdb() -> list:
            return duckdb_conn.execute(
                f"SELECT * FROM read_ndjson('{jsonl_path}')"
            ).fetchall()

        result = benchmark(load_with_duckdb)
        assert len(result) == 100

    def test_load_all_files_duckdb_glob(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Load ALL JSONL files with DuckDB glob pattern."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def load_all_with_duckdb() -> list:
            return duckdb_conn.execute(
                f"SELECT * FROM read_ndjson('{glob_pattern}')"
            ).fetchall()

        result = benchmark(load_all_with_duckdb)
        assert len(result) == 10_000  # 100 specs * 100 requirements

    def test_load_all_files_orjson_loop(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load ALL JSONL files with orjson in a loop."""

        def load_all_with_orjson() -> list:
            all_reqs = []
            for spec_dir in jsonl_dir.iterdir():
                jsonl_path = spec_dir / "requirements.jsonl"
                if jsonl_path.exists():
                    with jsonl_path.open("rb") as f:
                        all_reqs.extend(orjson.loads(line) for line in f)
            return all_reqs

        result = benchmark(load_all_with_orjson)
        assert len(result) == 10_000

    def test_aggregate_status_counts_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Aggregate status counts across all specs with DuckDB."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def aggregate_status() -> list:
            return duckdb_conn.execute(f"""
                SELECT spec_id, status, COUNT(*) as count
                FROM read_ndjson('{glob_pattern}')
                GROUP BY spec_id, status
                ORDER BY spec_id, status
            """).fetchall()

        result = benchmark(aggregate_status)
        # 100 specs * ~5 statuses (not all specs have all statuses)
        assert len(result) > 100

    def test_aggregate_status_counts_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Aggregate status counts with orjson + Python."""
        from collections import Counter

        def aggregate_status() -> dict:
            counts: dict[tuple[str, str], int] = Counter()
            for spec_dir in jsonl_dir.iterdir():
                jsonl_path = spec_dir / "requirements.jsonl"
                if jsonl_path.exists():
                    with jsonl_path.open("rb") as f:
                        for line in f:
                            req = orjson.loads(line)
                            counts[(req["spec_id"], req["status"])] += 1
            return dict(counts)

        result = benchmark(aggregate_status)
        assert len(result) > 100

    def test_filter_by_status_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Filter requirements by status with DuckDB."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def filter_verified() -> list:
            return duckdb_conn.execute(f"""
                SELECT id, spec_id, title
                FROM read_ndjson('{glob_pattern}')
                WHERE status = 'verified'
            """).fetchall()

        result = benchmark(filter_verified)
        # Should find ~20% of 10000 = ~2000 (random distribution)
        assert len(result) > 0

    def test_filter_by_status_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Filter requirements by status with orjson."""

        def filter_verified() -> list:
            results = []
            for spec_dir in jsonl_dir.iterdir():
                jsonl_path = spec_dir / "requirements.jsonl"
                if jsonl_path.exists():
                    with jsonl_path.open("rb") as f:
                        for line in f:
                            req = orjson.loads(line)
                            if req["status"] == "verified":
                                results.append(req)
            return results

        result = benchmark(filter_verified)
        assert len(result) > 0

    def test_point_lookup_by_id_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Point lookup by ID with DuckDB (worst case: scan all)."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")
        target_id = "REQ-SPEC-0050-0050"  # Middle of the dataset

        def lookup_by_id() -> list:
            return duckdb_conn.execute(f"""
                SELECT *
                FROM read_ndjson('{glob_pattern}')
                WHERE id = '{target_id}'
            """).fetchall()

        result = benchmark(lookup_by_id)
        assert len(result) == 1

    def test_point_lookup_by_id_orjson_targeted(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Point lookup by ID with orjson (targeted file)."""
        # If we know the spec from the ID, we can target the file
        target_id = "REQ-SPEC-0050-0050"
        spec_id = "SPEC-0050"
        jsonl_path = jsonl_dir / spec_id / "requirements.jsonl"

        def lookup_by_id() -> dict | None:
            with jsonl_path.open("rb") as f:
                for line in f:
                    req = orjson.loads(line)
                    if req["id"] == target_id:
                        return req
            return None

        result = benchmark(lookup_by_id)
        assert result is not None
        assert result["id"] == target_id

    def test_cross_spec_join_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Cross-spec analysis (e.g., find specs with most verified reqs)."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def cross_spec_analysis() -> list:
            return duckdb_conn.execute(f"""
                SELECT
                    spec_id,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END) as verified,
                    ROUND(100.0 * SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct
                FROM read_ndjson('{glob_pattern}')
                GROUP BY spec_id
                ORDER BY verified DESC
                LIMIT 10
            """).fetchall()

        result = benchmark(cross_spec_analysis)
        assert len(result) == 10

    def test_duckdb_startup_overhead(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: DuckDB connection + simple query (startup cost)."""
        jsonl_path = jsonl_dir / "SPEC-0000" / "requirements.jsonl"

        def connect_and_query() -> list:
            conn = duckdb.connect(":memory:")
            result = conn.execute(
                f"SELECT COUNT(*) FROM read_ndjson('{jsonl_path}')"
            ).fetchall()
            conn.close()
            return result

        result = benchmark(connect_and_query)
        assert result[0][0] == 100


class TestDuckDBWriteBenchmarks:
    """Benchmark DuckDB COPY for writing back to JSONL."""

    def test_write_jsonl_duckdb_copy(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Write filtered results to JSONL with DuckDB COPY."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")
        output_path = jsonl_dir / "output_verified.jsonl"

        def write_with_duckdb() -> int:
            duckdb_conn.execute(f"""
                COPY (
                    SELECT * FROM read_ndjson('{glob_pattern}')
                    WHERE status = 'verified'
                )
                TO '{output_path}'
            """)
            # Return line count
            with output_path.open("rb") as f:
                return sum(1 for _ in f)

        result = benchmark(write_with_duckdb)
        assert result > 0
        output_path.unlink(missing_ok=True)

    def test_write_jsonl_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Write filtered results to JSONL with orjson."""
        output_path = jsonl_dir / "output_verified_orjson.jsonl"

        def write_with_orjson() -> int:
            count = 0
            with output_path.open("wb") as out:
                for spec_dir in jsonl_dir.iterdir():
                    jsonl_path = spec_dir / "requirements.jsonl"
                    if jsonl_path.exists() and jsonl_path.is_file():
                        with jsonl_path.open("rb") as f:
                            for line in f:
                                req = orjson.loads(line)
                                if req["status"] == "verified":
                                    out.write(orjson.dumps(req))
                                    out.write(b"\n")
                                    count += 1
            return count

        result = benchmark(write_with_orjson)
        assert result > 0
        output_path.unlink(missing_ok=True)


class TestPolarsJsonlBenchmarks:
    """Benchmark suite for Polars JSONL operations."""

    def test_load_single_file_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load single JSONL file with Polars."""
        jsonl_path = jsonl_dir / "SPEC-0000" / "requirements.jsonl"

        def load_with_polars() -> pl.DataFrame:
            return pl.read_ndjson(jsonl_path)

        result = benchmark(load_with_polars)
        assert len(result) == 100

    def test_load_all_files_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load ALL JSONL files with Polars scan_ndjson + glob."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def load_all_with_polars() -> pl.DataFrame:
            # Polars doesn't support glob patterns directly in read_ndjson
            # So we'll use a lazy scan approach or load and concat
            all_files = list(jsonl_dir.glob("*/requirements.jsonl"))
            dfs = [pl.read_ndjson(f) for f in all_files]
            return pl.concat(dfs)

        result = benchmark(load_all_with_polars)
        assert len(result) == 10_000

    def test_filter_by_status_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Filter requirements by status with Polars."""
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def filter_verified() -> pl.DataFrame:
            all_files = list(jsonl_dir.glob("*/requirements.jsonl"))
            dfs = [pl.read_ndjson(f) for f in all_files]
            df = pl.concat(dfs)
            return df.filter(pl.col("status") == "verified")

        result = benchmark(filter_verified)
        assert len(result) > 0

    def test_aggregate_status_counts_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Aggregate status counts across all specs with Polars."""

        def aggregate_status() -> pl.DataFrame:
            all_files = list(jsonl_dir.glob("*/requirements.jsonl"))
            dfs = [pl.read_ndjson(f) for f in all_files]
            df = pl.concat(dfs)
            return (
                df.group_by(["spec_id", "status"])
                .agg(pl.len().alias("count"))
                .sort(["spec_id", "status"])
            )

        result = benchmark(aggregate_status)
        # 100 specs * ~5 statuses (not all specs have all statuses)
        assert len(result) > 100


class TestFullCRUDWorkflow:
    """Benchmark full CRUD workflows: load -> query -> update -> write back."""

    def test_update_single_spec_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load single spec, update some requirements, write back."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_updated.jsonl"

        def update_workflow() -> int:
            # Load
            with jsonl_path.open("rb") as f:
                reqs = [orjson.loads(line) for line in f]

            # Query and update: mark all 'proposed' as 'approved'
            updated = 0
            for req in reqs:
                if req["status"] == "proposed":
                    req["status"] = "approved"
                    updated += 1

            # Write back
            with output_path.open("wb") as f:
                for req in reqs:
                    f.write(orjson.dumps(req))
                    f.write(b"\n")

            return updated

        result = benchmark(update_workflow)
        output_path.unlink(missing_ok=True)
        # Should have updated some records
        assert result >= 0

    def test_update_single_spec_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Load single spec with DuckDB, update, write back."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_updated_duck.jsonl"

        def update_workflow() -> int:
            # Load into table, update, write back - all in SQL
            result = duckdb_conn.execute(f"""
                COPY (
                    SELECT
                        id, spec_id, title, req_type,
                        CASE WHEN status = 'proposed' THEN 'approved' ELSE status END as status,
                        created, updated, author, description, rationale,
                        acceptance_criteria, verified_by, depends_on, tags, source_section
                    FROM read_ndjson('{jsonl_path}')
                )
                TO '{output_path}'
            """)
            # Count how many were 'proposed'
            count = duckdb_conn.execute(f"""
                SELECT COUNT(*) FROM read_ndjson('{jsonl_path}')
                WHERE status = 'proposed'
            """).fetchone()
            return count[0] if count else 0

        result = benchmark(update_workflow)
        output_path.unlink(missing_ok=True)
        assert result >= 0

    def test_complex_update_orjson(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Complex update - add tag to all requirements with certain status."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_tagged.jsonl"

        def complex_update() -> int:
            # Load
            with jsonl_path.open("rb") as f:
                reqs = [orjson.loads(line) for line in f]

            # Complex update: add 'needs-review' tag to all 'implementing' requirements
            updated = 0
            for req in reqs:
                if req["status"] == "implementing":
                    tags = list(req.get("tags", []))
                    if "needs-review" not in tags:
                        tags.append("needs-review")
                        req["tags"] = tags
                        updated += 1

            # Write back
            with output_path.open("wb") as f:
                for req in reqs:
                    f.write(orjson.dumps(req))
                    f.write(b"\n")

            return updated

        result = benchmark(complex_update)
        output_path.unlink(missing_ok=True)
        assert result >= 0

    def test_complex_update_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Complex update with DuckDB - add tag using SQL."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_tagged_duck.jsonl"

        def complex_update() -> int:
            # DuckDB: use list_append to add tag
            duckdb_conn.execute(f"""
                COPY (
                    SELECT
                        id, spec_id, title, req_type, status,
                        created, updated, author, description, rationale,
                        acceptance_criteria, verified_by, depends_on,
                        CASE
                            WHEN status = 'implementing' AND NOT list_contains(tags, 'needs-review')
                            THEN list_append(tags, 'needs-review')
                            ELSE tags
                        END as tags,
                        source_section
                    FROM read_ndjson('{jsonl_path}')
                )
                TO '{output_path}'
            """)
            # Count updated
            count = duckdb_conn.execute(f"""
                SELECT COUNT(*) FROM read_ndjson('{jsonl_path}')
                WHERE status = 'implementing'
            """).fetchone()
            return count[0] if count else 0

        result = benchmark(complex_update)
        output_path.unlink(missing_ok=True)
        assert result >= 0

    def test_bulk_status_update_across_specs_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Update status across ALL specs, write back to separate files."""
        output_dir = jsonl_dir / "updated_specs"
        output_dir.mkdir(exist_ok=True)

        def bulk_update() -> int:
            glob_pattern = str(jsonl_dir / "SPEC-*" / "requirements.jsonl")

            # Load all, update status, partition by spec_id
            # DuckDB can write partitioned output!
            duckdb_conn.execute(f"""
                COPY (
                    SELECT
                        * REPLACE (
                            CASE WHEN status = 'proposed' THEN 'approved' ELSE status END as status
                        )
                    FROM read_ndjson('{glob_pattern}')
                )
                TO '{output_dir}' (
                    FORMAT JSON,
                    PARTITION_BY (spec_id)
                )
            """)
            # Count files created
            return len(list(output_dir.iterdir()))

        result = benchmark(bulk_update)
        # Cleanup
        import shutil

        shutil.rmtree(output_dir, ignore_errors=True)
        assert result > 0

    def test_join_requirements_tests_duckdb(
        self,
        benchmark: BenchmarkFixture,
        jsonl_dir: Path,
        duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Benchmark: Join requirements with their verified_by tests (simulated)."""
        # This simulates querying requirements and their associated tests
        glob_pattern = str(jsonl_dir / "*" / "requirements.jsonl")

        def join_query() -> list:
            # Unnest verified_by array to join with hypothetical tests
            return duckdb_conn.execute(f"""
                SELECT
                    r.id as req_id,
                    r.title as req_title,
                    r.status,
                    UNNEST(r.verified_by) as test_id
                FROM read_ndjson('{glob_pattern}') r
                WHERE len(r.verified_by) > 0
                LIMIT 1000
            """).fetchall()

        result = benchmark(join_query)
        assert len(result) > 0

    def test_update_single_spec_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Load single spec with Polars, update status, write back."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_updated_polars.jsonl"

        def update_workflow() -> int:
            # Load
            df = pl.read_ndjson(jsonl_path)

            # Query and update: mark all 'proposed' as 'approved'
            updated = df.filter(pl.col("status") == "proposed").height
            df = df.with_columns(
                pl.when(pl.col("status") == "proposed")
                .then(pl.lit("approved"))
                .otherwise(pl.col("status"))
                .alias("status")
            )

            # Write back
            df.write_ndjson(output_path)

            return updated

        result = benchmark(update_workflow)
        output_path.unlink(missing_ok=True)
        assert result >= 0

    def test_complex_update_polars(
        self, benchmark: BenchmarkFixture, jsonl_dir: Path
    ) -> None:
        """Benchmark: Complex update with Polars - add tag to list column."""
        spec_dir = jsonl_dir / "SPEC-0050"
        jsonl_path = spec_dir / "requirements.jsonl"
        output_path = spec_dir / "requirements_tagged_polars.jsonl"

        def complex_update() -> int:
            # Load
            df = pl.read_ndjson(jsonl_path)

            # Complex update: add 'needs-review' tag to all 'implementing' requirements
            # Count how many will be updated
            updated = df.filter(
                (pl.col("status") == "implementing")
                & ~pl.col("tags").list.contains("needs-review")
            ).height

            # Update tags for 'implementing' status
            df = df.with_columns(
                pl.when(
                    (pl.col("status") == "implementing")
                    & ~pl.col("tags").list.contains("needs-review")
                )
                .then(pl.col("tags").list.concat(pl.lit(["needs-review"])))
                .otherwise(pl.col("tags"))
                .alias("tags")
            )

            # Write back
            df.write_ndjson(output_path)

            return updated

        result = benchmark(complex_update)
        output_path.unlink(missing_ok=True)
        assert result >= 0
