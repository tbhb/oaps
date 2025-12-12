# pyright: reportArgumentType=false
"""Unit tests for the logs _sources module."""

import json
from pathlib import Path

import polars as pl
import pytest

from oaps.cli._commands._logs._sources import (
    LogSource,
    _infer_source_hint,
    _normalize_schema,
    list_sessions,
    load_logs,
    resolve_source,
)


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary log directory structure."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    sessions_dir = logs_dir / "sessions"
    sessions_dir.mkdir()

    # Patch the utility functions to use our temp directory
    monkeypatch.setattr(
        "oaps.cli._commands._logs._sources.get_oaps_log_dir",
        lambda: logs_dir,
    )
    monkeypatch.setattr(
        "oaps.cli._commands._logs._sources.get_oaps_hooks_log_file",
        lambda: logs_dir / "hooks.log",
    )
    monkeypatch.setattr(
        "oaps.cli._commands._logs._sources.get_oaps_cli_log_file",
        lambda: logs_dir / "cli.log",
    )

    return logs_dir


@pytest.fixture
def sample_log_entries() -> list[dict[str, object]]:
    return [
        {
            "timestamp": "2025-01-01T10:00:00Z",
            "level": "info",
            "event": "hook_started",
            "session_id": "abc-123",
            "hook_event": "session_start",
        },
        {
            "timestamp": "2025-01-01T10:00:01Z",
            "level": "info",
            "event": "hook_completed",
            "session_id": "abc-123",
            "hook_event": "session_start",
        },
        {
            "timestamp": "2025-01-01T10:00:02Z",
            "level": "error",
            "event": "hook_failed",
            "session_id": "abc-123",
            "hook_event": "pre_tool_use",
            "reason": "Rule evaluation failed",
        },
    ]


def _write_jsonl(path: Path, entries: list[dict[str, object]]) -> None:
    """Write log entries as JSONL file."""
    with path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestResolveSource:
    def test_resolve_hooks_source(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        _write_jsonl(hooks_log, sample_log_entries)

        source = resolve_source("hooks")

        assert source.name == "hooks"
        assert source.source_type == "hooks"
        assert source.paths == (hooks_log,)

    def test_resolve_hooks_case_insensitive(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        _write_jsonl(hooks_log, sample_log_entries)

        source = resolve_source("HOOKS")

        assert source.name == "hooks"
        assert source.source_type == "hooks"

    def test_resolve_hooks_not_found(self, log_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Hooks log not found"):
            resolve_source("hooks")

    def test_resolve_cli_source(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        cli_log = log_dir / "cli.log"
        _write_jsonl(cli_log, sample_log_entries)

        source = resolve_source("cli")

        assert source.name == "cli"
        assert source.source_type == "cli"
        assert source.paths == (cli_log,)

    def test_resolve_cli_not_found(self, log_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="CLI log not found"):
            resolve_source("cli")

    def test_resolve_session_by_exact_id(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"
        session_id = "a39cb323-4567-890a-bcde-fghijklmnopq"
        session_log = sessions_dir / f"{session_id}.log"
        _write_jsonl(session_log, sample_log_entries)

        source = resolve_source(f"session:{session_id}")

        assert source.source_type == "session"
        assert source.paths == (session_log,)
        assert "sess:" in source.name

    def test_resolve_session_by_prefix(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"
        session_id = "a39cb323-4567-890a-bcde-fghijklmnopq"
        session_log = sessions_dir / f"{session_id}.log"
        _write_jsonl(session_log, sample_log_entries)

        source = resolve_source("session:a39c")

        assert source.source_type == "session"
        assert source.paths == (session_log,)
        assert source.name == "sess:a39cb323"

    def test_resolve_session_multiple_matches(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"

        session1 = sessions_dir / "abc-session-1.log"
        session2 = sessions_dir / "abc-session-2.log"
        _write_jsonl(session1, sample_log_entries)
        _write_jsonl(session2, sample_log_entries)

        source = resolve_source("session:abc")

        assert source.source_type == "session"
        assert len(source.paths) == 2
        assert "abc*" in source.name
        assert "(2)" in source.name

    def test_resolve_session_not_found_with_available_hint(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"
        session_log = sessions_dir / "xyz-123.log"
        _write_jsonl(session_log, sample_log_entries)

        with pytest.raises(FileNotFoundError, match="No sessions matching 'abc'"):
            resolve_source("session:abc")

    def test_resolve_session_no_sessions_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        monkeypatch.setattr(
            "oaps.cli._commands._logs._sources.get_oaps_log_dir",
            lambda: logs_dir,
        )

        with pytest.raises(FileNotFoundError, match="Sessions directory not found"):
            resolve_source("session:abc")

    def test_resolve_all_sources(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        cli_log = log_dir / "cli.log"
        sessions_dir = log_dir / "sessions"
        session_log = sessions_dir / "sess-001.log"

        _write_jsonl(hooks_log, sample_log_entries)
        _write_jsonl(cli_log, sample_log_entries)
        _write_jsonl(session_log, sample_log_entries)

        source = resolve_source("all")

        assert source.name == "all"
        assert source.source_type == "all"
        assert len(source.paths) == 3
        assert hooks_log in source.paths
        assert cli_log in source.paths
        assert session_log in source.paths

    def test_resolve_all_only_hooks(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        _write_jsonl(hooks_log, sample_log_entries)

        source = resolve_source("all")

        assert source.source_type == "all"
        assert source.paths == (hooks_log,)

    def test_resolve_all_no_logs_found(self, log_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No log files found"):
            resolve_source("all")

    def test_invalid_source_format(self, log_dir: Path) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            resolve_source("unknown")

    def test_invalid_source_format_helpful_message(self, log_dir: Path) -> None:
        with pytest.raises(ValueError, match=r"hooks.*cli.*session.*all"):
            resolve_source("invalid_source_name")


class TestInferSourceHint:
    def test_hooks_log(self) -> None:
        path = Path("/some/path/to/hooks.log")
        assert _infer_source_hint(path) == "hooks"

    def test_cli_log(self) -> None:
        path = Path("/some/path/to/cli.log")
        assert _infer_source_hint(path) == "cli"

    def test_session_log(self) -> None:
        path = Path("/some/path/to/a39cb323-4567-890a-bcde.log")
        assert _infer_source_hint(path) == "sess:a39cb323"

    def test_session_log_short_id(self) -> None:
        path = Path("/some/path/to/abc.log")
        assert _infer_source_hint(path) == "sess:abc"


class TestLoadLogs:
    def test_load_single_log_file(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        _write_jsonl(hooks_log, sample_log_entries)

        source = LogSource(name="hooks", paths=(hooks_log,), source_type="hooks")
        df = load_logs(source)

        assert df.height == 3
        assert "_source" in df.columns
        assert df["_source"][0] == "hooks"

    def test_load_multiple_log_files(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        cli_log = log_dir / "cli.log"

        _write_jsonl(hooks_log, sample_log_entries)
        _write_jsonl(cli_log, sample_log_entries)

        source = LogSource(name="all", paths=(hooks_log, cli_log), source_type="all")
        df = load_logs(source)

        assert df.height == 6
        assert "_source" in df.columns

        source_values = df["_source"].to_list()
        assert "hooks" in source_values
        assert "cli" in source_values

    def test_load_handles_missing_file_in_multi(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        missing_log = log_dir / "missing.log"

        _write_jsonl(hooks_log, sample_log_entries)

        source = LogSource(
            name="all", paths=(hooks_log, missing_log), source_type="all"
        )
        df = load_logs(source)

        # Should only load from existing file
        assert df.height == 3

    def test_load_handles_malformed_file(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        hooks_log = log_dir / "hooks.log"
        malformed_log = log_dir / "malformed.log"

        _write_jsonl(hooks_log, sample_log_entries)
        malformed_log.write_text("this is not valid json\n")

        source = LogSource(
            name="all", paths=(hooks_log, malformed_log), source_type="all"
        )
        df = load_logs(source)

        # Should skip malformed file and load from valid one
        assert df.height == 3

    def test_load_empty_when_all_files_malformed(self, log_dir: Path) -> None:
        malformed1 = log_dir / "bad1.log"
        malformed2 = log_dir / "bad2.log"

        malformed1.write_text("not json\n")
        malformed2.write_text("also not json\n")

        source = LogSource(
            name="all", paths=(malformed1, malformed2), source_type="all"
        )
        df = load_logs(source)

        assert df.height == 0
        assert "timestamp" in df.columns
        assert "level" in df.columns
        assert "event" in df.columns
        assert "_source" in df.columns

    def test_load_with_schema_differences(self, log_dir: Path) -> None:
        file1 = log_dir / "file1.log"
        file2 = log_dir / "file2.log"

        # File 1 has 'count' as int
        entries1 = [{"timestamp": "2025-01-01T10:00:00Z", "event": "a", "count": 5}]
        # File 2 has 'count' as string
        entries2 = [{"timestamp": "2025-01-01T10:00:01Z", "event": "b", "count": "10"}]

        _write_jsonl(file1, entries1)
        _write_jsonl(file2, entries2)

        source = LogSource(name="test", paths=(file1, file2), source_type="all")
        df = load_logs(source)

        # Should successfully merge with normalized schema
        assert df.height == 2


class TestNormalizeSchema:
    def test_preserves_string_columns(self) -> None:
        df = pl.DataFrame({"name": ["alice", "bob"], "level": ["info", "error"]})
        result = _normalize_schema(df)

        assert result["name"].dtype == pl.Utf8
        assert result["level"].dtype == pl.Utf8
        assert result["name"].to_list() == ["alice", "bob"]

    def test_converts_int_to_string(self) -> None:
        df = pl.DataFrame({"count": [1, 2, 3]})
        result = _normalize_schema(df)

        assert result["count"].dtype == pl.Utf8
        assert result["count"].to_list() == ["1", "2", "3"]

    def test_converts_float_to_string(self) -> None:
        df = pl.DataFrame({"value": [1.5, 2.7, 3.9]})
        result = _normalize_schema(df)

        assert result["value"].dtype == pl.Utf8
        assert "1.5" in result["value"].to_list()

    def test_converts_bool_to_string(self) -> None:
        df = pl.DataFrame({"flag": [True, False]})
        result = _normalize_schema(df)

        assert result["flag"].dtype == pl.Utf8
        assert result["flag"].to_list() == ["true", "false"]

    def test_serializes_struct_to_json(self) -> None:
        df = pl.DataFrame({"data": [{"key": "value1"}, {"key": "value2"}]}).cast(
            {"data": pl.Struct({"key": pl.Utf8})}
        )
        result = _normalize_schema(df)

        assert result["data"].dtype == pl.Utf8
        # Should be JSON encoded
        assert '{"key":"value1"}' in result["data"][0]

    def test_converts_list_to_string(self) -> None:
        df = pl.DataFrame({"items": [["a", "b"], ["c", "d"]]})
        result = _normalize_schema(df)

        assert result["items"].dtype == pl.Utf8


class TestListSessions:
    def test_lists_sessions_sorted_by_mtime(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"

        sess1 = sessions_dir / "session-001.log"
        sess2 = sessions_dir / "session-002.log"
        sess3 = sessions_dir / "session-003.log"

        _write_jsonl(sess1, sample_log_entries)
        _write_jsonl(sess2, sample_log_entries)
        _write_jsonl(sess3, sample_log_entries)

        # Simulate different mtimes by touching files
        import time

        time.sleep(0.01)
        sess2.touch()
        time.sleep(0.01)
        sess3.touch()

        sessions = list_sessions(limit=10)

        # Most recent first
        assert len(sessions) == 3
        assert sessions[0][0] == "session-003"
        assert sessions[1][0] == "session-002"
        assert sessions[2][0] == "session-001"

    def test_respects_limit(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"

        for i in range(5):
            sess = sessions_dir / f"session-{i:03d}.log"
            _write_jsonl(sess, sample_log_entries)

        sessions = list_sessions(limit=3)

        assert len(sessions) == 3

    def test_returns_empty_when_no_sessions_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        monkeypatch.setattr(
            "oaps.cli._commands._logs._sources.get_oaps_log_dir",
            lambda: logs_dir,
        )

        sessions = list_sessions()

        assert sessions == []

    def test_returns_empty_when_no_session_files(self, log_dir: Path) -> None:
        # sessions_dir exists (created by fixture) but is empty
        sessions = list_sessions()

        assert sessions == []

    def test_returns_session_id_and_path(
        self, log_dir: Path, sample_log_entries: list[dict[str, object]]
    ) -> None:
        sessions_dir = log_dir / "sessions"
        sess = sessions_dir / "my-session-id.log"
        _write_jsonl(sess, sample_log_entries)

        sessions = list_sessions()

        assert len(sessions) == 1
        session_id, path = sessions[0]
        assert session_id == "my-session-id"
        assert path == sess
