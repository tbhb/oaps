"""Tests for transcript discovery and parsing."""

from pathlib import Path

import polars as pl
import pytest

from oaps.cli._commands._analyze._transcript import (
    TranscriptDirectory,
    TranscriptFile,
    discover_transcript_directory,
    extract_agent_info_from_transcript,
    extract_tool_usage_from_transcript,
    extract_usage_from_transcript,
    load_all_transcripts,
    parse_transcript_file,
    project_path_to_transcript_dir,
)


class TestProjectPathToTranscriptDir:
    def test_transforms_path_correctly(self):
        project_path = Path("/Users/tony/Code/github.com/tbhb/oaps")
        result = project_path_to_transcript_dir(project_path)

        # Both slashes and periods are replaced with dashes
        expected = (
            Path.home()
            / ".claude"
            / "projects"
            / "-Users-tony-Code-github-com-tbhb-oaps"
        )
        assert result == expected

    def test_handles_root_path(self):
        project_path = Path("/")
        result = project_path_to_transcript_dir(project_path)

        expected = Path.home() / ".claude" / "projects" / "-"
        assert result == expected


class TestTranscriptFile:
    def test_creates_main_session_file(self):
        tf = TranscriptFile(
            path=Path("/test/abc123.jsonl"),
            session_id="abc123",
            is_agent=False,
        )

        assert tf.session_id == "abc123"
        assert tf.is_agent is False
        assert tf.agent_id is None

    def test_creates_agent_file(self):
        tf = TranscriptFile(
            path=Path("/test/agent-xyz789.jsonl"),
            session_id="xyz789",
            is_agent=True,
            agent_id="xyz789",
        )

        assert tf.session_id == "xyz789"
        assert tf.is_agent is True
        assert tf.agent_id == "xyz789"


class TestTranscriptDirectory:
    def test_total_files_property(self):
        main = [
            TranscriptFile(Path("/a.jsonl"), "a", False),
            TranscriptFile(Path("/b.jsonl"), "b", False),
        ]
        agents = [
            TranscriptFile(Path("/agent-c.jsonl"), "c", True, "c"),
        ]
        td = TranscriptDirectory(
            path=Path("/test"),
            project_path=Path("/project"),
            main_sessions=main,
            agent_transcripts=agents,
        )

        assert td.total_files == 3

    def test_all_files_property(self):
        main = [TranscriptFile(Path("/a.jsonl"), "a", False)]
        agents = [TranscriptFile(Path("/agent-b.jsonl"), "b", True, "b")]
        td = TranscriptDirectory(
            path=Path("/test"),
            project_path=Path("/project"),
            main_sessions=main,
            agent_transcripts=agents,
        )

        assert len(td.all_files) == 2


class TestDiscoverTranscriptDirectory:
    def test_returns_none_when_directory_missing(self, tmp_path: Path):
        result = discover_transcript_directory(
            tmp_path,
            transcript_dir_override=tmp_path / "nonexistent",
        )

        assert result is None

    def test_discovers_main_sessions(self, tmp_path: Path):
        # Create mock transcript files
        session_file = tmp_path / "12345678-1234-1234-1234-123456789012.jsonl"
        session_file.write_text('{"type": "test"}\n')

        result = discover_transcript_directory(
            tmp_path / "project",
            transcript_dir_override=tmp_path,
        )

        assert result is not None
        assert len(result.main_sessions) == 1
        assert (
            result.main_sessions[0].session_id == "12345678-1234-1234-1234-123456789012"
        )

    def test_discovers_agent_transcripts(self, tmp_path: Path):
        agent_file = tmp_path / "agent-abc123.jsonl"
        agent_file.write_text('{"type": "test"}\n')

        result = discover_transcript_directory(
            tmp_path / "project",
            transcript_dir_override=tmp_path,
        )

        assert result is not None
        assert len(result.agent_transcripts) == 1
        assert result.agent_transcripts[0].agent_id == "abc123"


class TestParseTranscriptFile:
    def test_parses_jsonl_file(self, tmp_path: Path):
        jsonl_path = tmp_path / "test.jsonl"
        jsonl_path.write_text('{"a": 1}\n{"a": 2}\n{"a": 3}\n')

        df = parse_transcript_file(jsonl_path)

        assert df.height == 3
        assert "a" in df.columns

    def test_raises_on_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_transcript_file(tmp_path / "nonexistent.jsonl")


class TestExtractUsageFromTranscript:
    def test_returns_empty_when_no_message_column(self):
        df = pl.DataFrame({"other": [1, 2, 3]})
        result = extract_usage_from_transcript(df)

        assert result.height == 0

    def test_extracts_usage_data(self):
        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "sessionId": ["session1"],
                "message": [
                    {
                        "model": "claude-3-5-sonnet-20241022",
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_input_tokens": 10,
                            "cache_read_input_tokens": 5,
                        },
                    }
                ],
            }
        )

        result = extract_usage_from_transcript(df)

        assert result.height == 1
        assert result["input_tokens"][0] == 100
        assert result["output_tokens"][0] == 50


class TestExtractToolUsageFromTranscript:
    def test_returns_empty_when_no_message_column(self):
        df = pl.DataFrame({"other": [1, 2, 3]})
        result = extract_tool_usage_from_transcript(df)

        assert result.height == 0

    def test_extracts_tool_usage_from_message_content(self):
        # Tool usage is stored in message.content as JSON array
        content_with_tools = (
            '[{"type": "tool_use", "name": "Read"}, {"type": "text", "text": "Hello"}]'
        )
        content_with_write = '[{"type": "tool_use", "name": "Write"}]'

        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:01Z"],
                "sessionId": ["session1", "session1"],
                "message": [
                    {"content": content_with_tools, "model": "test"},
                    {"content": content_with_write, "model": "test"},
                ],
            }
        )

        result = extract_tool_usage_from_transcript(df)

        assert result.height == 2
        assert "tool_name" in result.columns
        assert result["tool_name"].to_list() == ["Read", "Write"]

    def test_extracts_multiple_tools_from_single_message(self):
        # Single message with multiple tool uses
        content = (
            '[{"type": "tool_use", "name": "Read"}, '
            '{"type": "tool_use", "name": "Grep"}]'
        )

        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "sessionId": ["session1"],
                "message": [{"content": content, "model": "test"}],
            }
        )

        result = extract_tool_usage_from_transcript(df)

        assert result.height == 2
        assert result["tool_name"].to_list() == ["Read", "Grep"]

    def test_skips_messages_without_tool_use(self):
        # Message without tool_use type
        content = '[{"type": "text", "text": "Hello"}]'

        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "sessionId": ["session1"],
                "message": [{"content": content, "model": "test"}],
            }
        )

        result = extract_tool_usage_from_transcript(df)

        assert result.height == 0

    def test_handles_invalid_json_content(self):
        # Invalid JSON in content
        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "sessionId": ["session1"],
                "message": [{"content": "not valid json", "model": "test"}],
            }
        )

        result = extract_tool_usage_from_transcript(df)

        assert result.height == 0


class TestExtractAgentInfoFromTranscript:
    def test_returns_empty_when_no_agent_columns(self):
        df = pl.DataFrame({"other": [1, 2, 3]})
        result = extract_agent_info_from_transcript(df)

        assert result.height == 0

    def test_extracts_sidechain_info(self):
        df = pl.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "sessionId": ["session1"],
                "isSidechain": [True],
            }
        )

        result = extract_agent_info_from_transcript(df)

        assert result.height == 1
        assert "is_sidechain" in result.columns


class TestLoadAllTranscripts:
    def test_returns_empty_dataframe_when_no_files(self, tmp_path: Path):
        td = TranscriptDirectory(
            path=tmp_path,
            project_path=tmp_path,
            main_sessions=[],
            agent_transcripts=[],
        )

        result = load_all_transcripts(td)

        assert result.height == 0

    def test_loads_and_concatenates_transcripts(self, tmp_path: Path):
        # Create two transcript files
        file1 = tmp_path / "12345678-1234-1234-1234-123456789012.jsonl"
        file1.write_text('{"a": 1}\n')

        file2 = tmp_path / "87654321-4321-4321-4321-210987654321.jsonl"
        file2.write_text('{"a": 2}\n')

        td = TranscriptDirectory(
            path=tmp_path,
            project_path=tmp_path,
            main_sessions=[
                TranscriptFile(file1, "12345678-1234-1234-1234-123456789012", False),
                TranscriptFile(file2, "87654321-4321-4321-4321-210987654321", False),
            ],
            agent_transcripts=[],
        )

        result = load_all_transcripts(td)

        assert result.height == 2
        assert "_source_session_id" in result.columns
