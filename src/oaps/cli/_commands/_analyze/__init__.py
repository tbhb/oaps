# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Analyze commands for OAPS CLI."""

# Import command modules to register decorators
# Re-export exit codes from shared
from oaps.cli._commands._shared import ExitCode

from . import _usage as _usage

# Re-export app
from ._app import app

# Re-export transcript utilities
from ._transcript import (
    TranscriptDirectory,
    TranscriptFile,
    discover_transcript_directory,
    extract_agent_info_from_transcript,
    extract_tool_usage_from_transcript,
    extract_usage_from_transcript,
    iter_transcript_rows,
    load_all_transcripts,
    parse_transcript_file,
    project_path_to_transcript_dir,
)

# Re-export usage analysis
from ._usage import (
    DailyUsage,
    SessionUsage,
    UsageAnalysis,
    WeeklyUsage,
    analyze_usage,
    parse_since_filter,
)

__all__ = [
    "DailyUsage",
    "ExitCode",
    "SessionUsage",
    "TranscriptDirectory",
    "TranscriptFile",
    "UsageAnalysis",
    "WeeklyUsage",
    "analyze_usage",
    "app",
    "discover_transcript_directory",
    "extract_agent_info_from_transcript",
    "extract_tool_usage_from_transcript",
    "extract_usage_from_transcript",
    "iter_transcript_rows",
    "load_all_transcripts",
    "parse_since_filter",
    "parse_transcript_file",
    "project_path_to_transcript_dir",
]
