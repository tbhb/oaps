# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# ruff: noqa: FBT003, TRY300, PLR0911, PLR0912
"""Transcript discovery, loading, and parsing for Claude Code sessions.

This module handles:
- Auto-discovery of transcript directory from project root
- Identification of main sessions vs agent transcripts
- Parsing JSONL transcript files with polars
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from collections.abc import Iterator

# Schema inference length for Polars JSONL parsing
# Higher value captures sparse fields that only appear on some entries
SCHEMA_INFER_LENGTH = 10000

# Transcript file patterns
MAIN_SESSION_PATTERN = "????????-????-????-????-????????????.jsonl"  # UUID pattern
AGENT_TRANSCRIPT_PATTERN = "agent-*.jsonl"


@dataclass(frozen=True, slots=True)
class TranscriptFile:
    """Represents a single transcript file.

    Attributes:
        path: Full path to the transcript file.
        session_id: Session ID extracted from filename (UUID for main sessions).
        is_agent: Whether this is an agent transcript (sidechain).
        agent_id: Agent ID for agent transcripts, None for main sessions.
    """

    path: Path
    session_id: str
    is_agent: bool
    agent_id: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptDirectory:
    """Information about a Claude Code transcript directory.

    Attributes:
        path: Path to the transcript directory.
        project_path: Original project path that was transformed.
        main_sessions: List of main session transcript files.
        agent_transcripts: List of agent transcript files.
    """

    path: Path
    project_path: Path
    main_sessions: list[TranscriptFile]
    agent_transcripts: list[TranscriptFile]

    @property
    def total_files(self) -> int:
        """Total number of transcript files."""
        return len(self.main_sessions) + len(self.agent_transcripts)

    @property
    def all_files(self) -> list[TranscriptFile]:
        """All transcript files (main sessions + agent transcripts)."""
        return [*self.main_sessions, *self.agent_transcripts]


def project_path_to_transcript_dir(project_path: Path) -> Path:
    """Transform a project path to its Claude Code transcript directory.

    Claude Code stores transcripts in ~/.claude/projects/ with the project path
    transformed: both slashes and dots become dashes, and the absolute path is used.

    Example:
        /Users/tony/Code/github.com/tbhb/oaps
        -> ~/.claude/projects/-Users-tony-Code-github-com-tbhb-oaps/

    Args:
        project_path: Absolute path to the project root.

    Returns:
        Path to the transcript directory.
    """
    # Ensure we have an absolute path
    project_path = project_path.resolve()

    # Transform path: /Users/tony/Code/github.com -> -Users-tony-Code-github-com
    # Note: Both slashes and dots are replaced with dashes
    path_str = str(project_path)
    transformed = path_str.replace("/", "-").replace(".", "-")

    # Claude stores in ~/.claude/projects/
    return Path.home() / ".claude" / "projects" / transformed


def discover_transcript_directory(
    project_path: Path,
    transcript_dir_override: Path | None = None,
) -> TranscriptDirectory | None:
    """Discover and analyze a Claude Code transcript directory.

    Args:
        project_path: Path to the project root.
        transcript_dir_override: Optional override for transcript directory.

    Returns:
        TranscriptDirectory with discovered files, or None if directory not found.
    """
    if transcript_dir_override is not None:
        transcript_dir = transcript_dir_override
    else:
        transcript_dir = project_path_to_transcript_dir(project_path)

    if not transcript_dir.exists():
        return None

    # Discover main sessions (UUID.jsonl files)
    main_sessions: list[TranscriptFile] = []
    for path in transcript_dir.glob(MAIN_SESSION_PATTERN):
        session_id = path.stem  # UUID without extension
        main_sessions.append(
            TranscriptFile(
                path=path,
                session_id=session_id,
                is_agent=False,
                agent_id=None,
            )
        )

    # Discover agent transcripts (agent-*.jsonl files)
    agent_transcripts: list[TranscriptFile] = []
    for path in transcript_dir.glob(AGENT_TRANSCRIPT_PATTERN):
        # Extract agent ID from filename (e.g., agent-abc123.jsonl -> abc123)
        agent_id = path.stem.removeprefix("agent-")
        # Agent transcripts don't have their own session ID in filename
        # We'll extract it from the content if needed
        agent_transcripts.append(
            TranscriptFile(
                path=path,
                session_id=agent_id,  # Use agent ID as identifier
                is_agent=True,
                agent_id=agent_id,
            )
        )

    # Sort by modification time (most recent first)
    main_sessions.sort(key=lambda t: t.path.stat().st_mtime, reverse=True)
    agent_transcripts.sort(key=lambda t: t.path.stat().st_mtime, reverse=True)

    return TranscriptDirectory(
        path=transcript_dir,
        project_path=project_path,
        main_sessions=main_sessions,
        agent_transcripts=agent_transcripts,
    )


def parse_transcript_file(path: Path) -> pl.DataFrame:
    """Parse a single JSONL transcript file into a DataFrame.

    Args:
        path: Path to the transcript file.

    Returns:
        DataFrame with parsed transcript entries.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        pl.exceptions.ComputeError: If the file is malformed.
    """
    return pl.read_ndjson(str(path), infer_schema_length=SCHEMA_INFER_LENGTH)


def iter_transcript_rows(path: Path) -> Iterator[dict[str, object]]:
    """Iterate over rows in a transcript file.

    This is more memory-efficient for large files than loading everything at once.

    Args:
        path: Path to the transcript file.

    Yields:
        Dictionary for each row in the transcript.
    """
    df = parse_transcript_file(path)
    yield from df.iter_rows(named=True)


def extract_usage_from_transcript(df: pl.DataFrame) -> pl.DataFrame:
    """Extract token usage data from a transcript DataFrame.

    Filters to assistant messages with usage data and extracts:
    - input_tokens, output_tokens
    - cache_creation_input_tokens, cache_read_input_tokens
    - model name
    - timestamp

    Args:
        df: DataFrame with transcript data.

    Returns:
        DataFrame with usage data extracted.
    """
    # Check for required columns
    if "message" not in df.columns:
        return pl.DataFrame()

    # Filter to rows with message.usage data
    # The message field is a struct with nested usage data
    try:
        # Extract usage fields from the message struct
        usage_df = df.filter(pl.col("message").is_not_null()).select(
            [
                pl.col("timestamp"),
                pl.col("sessionId").alias("session_id"),
                # Extract from message struct
                pl.col("message").struct.field("model").alias("model"),
                pl.col("message").struct.field("usage").alias("usage"),
            ]
        )

        # Filter to rows with usage data
        usage_df = usage_df.filter(pl.col("usage").is_not_null())

        if usage_df.height == 0:
            return pl.DataFrame()

        # Extract usage fields
        result = usage_df.select(
            [
                pl.col("timestamp"),
                pl.col("session_id"),
                pl.col("model"),
                pl.col("usage").struct.field("input_tokens").alias("input_tokens"),
                pl.col("usage").struct.field("output_tokens").alias("output_tokens"),
                pl.col("usage")
                .struct.field("cache_creation_input_tokens")
                .alias("cache_creation_input_tokens"),
                pl.col("usage")
                .struct.field("cache_read_input_tokens")
                .alias("cache_read_input_tokens"),
            ]
        )

        # Fill nulls with 0 for cache fields (they may not always be present)
        return result.with_columns(
            [
                pl.col("cache_creation_input_tokens").fill_null(0),
                pl.col("cache_read_input_tokens").fill_null(0),
            ]
        )
    except pl.exceptions.StructFieldNotFoundError:
        return pl.DataFrame()


def _extract_tool_names_from_content(content: str | None) -> list[str]:
    """Extract tool names from message content JSON.

    The content field contains a JSON array like:
    [{"type": "tool_use", "name": "Read", ...}, ...]

    Args:
        content: JSON string of message content.

    Returns:
        List of tool names found in the content.
    """
    import json

    if content is None:
        return []

    try:
        parsed: list[dict[str, object]] | object = json.loads(content)
        if not isinstance(parsed, list):
            return []

        return [
            str(item["name"])
            for item in parsed
            if isinstance(item, dict)
            and item.get("type") == "tool_use"
            and isinstance(item.get("name"), str)
        ]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def _extract_tool_details_from_content(
    content: str | None,
) -> list[tuple[str, str | None]]:
    """Extract tool names and relevant details from message content JSON.

    For specific tools, extracts additional context:
    - Bash: the command being run
    - Read/Write/Edit: the file_path
    - Glob/Grep: the path or pattern
    - Task: the subagent_type

    Args:
        content: JSON string of message content.

    Returns:
        List of (tool_name, detail) tuples. Detail is None if not applicable.
    """
    import json

    if content is None:
        return []

    try:
        parsed: list[dict[str, object]] | object = json.loads(content)
        if not isinstance(parsed, list):
            return []

        results: list[tuple[str, str | None]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "tool_use":
                continue
            name = item.get("name")
            if not isinstance(name, str):
                continue

            detail: str | None = None
            tool_input = item.get("input")
            if isinstance(tool_input, dict):
                if name == "Bash":
                    cmd = tool_input.get("command")
                    if isinstance(cmd, str):
                        # Extract first word/command from bash command
                        detail = cmd.split()[0] if cmd.strip() else None
                elif name in {"Read", "Write", "Edit"}:
                    path = tool_input.get("file_path")
                    if isinstance(path, str):
                        detail = path
                elif name in {"Glob", "Grep"}:
                    path = tool_input.get("path")
                    if isinstance(path, str):
                        detail = path
                elif name == "Task":
                    agent = tool_input.get("subagent_type")
                    if isinstance(agent, str):
                        detail = agent

            results.append((name, detail))

        return results
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def _serialize_tool_details(content: str | None) -> str:
    """Serialize tool details to JSON for polars storage."""
    import json

    details = _extract_tool_details_from_content(content)
    return json.dumps(details)


def extract_tool_usage_from_transcript(df: pl.DataFrame) -> pl.DataFrame:
    """Extract tool usage data from a transcript DataFrame.

    Tool usage is stored in message.content as a JSON array containing
    objects with type="tool_use" and a name field. Token usage is extracted
    from message.usage to associate output tokens with tool invocations.

    Extracts:
    - tool_name
    - tool_detail (command for Bash, path for file tools, agent type for Task)
    - timestamp
    - session_id
    - output_tokens (tokens used to generate the tool call)

    Args:
        df: DataFrame with transcript data.

    Returns:
        DataFrame with tool usage data including token consumption.
    """
    import json

    if "message" not in df.columns:
        return pl.DataFrame()

    try:
        # Filter to rows with message data
        filtered = df.filter(pl.col("message").is_not_null())

        if filtered.height == 0:
            return pl.DataFrame()

        # Extract content and usage from message struct
        with_content = filtered.select(
            [
                pl.col("timestamp"),
                pl.col("sessionId").alias("session_id"),
                pl.col("message").struct.field("content").alias("content"),
                pl.col("message").struct.field("usage").alias("usage"),
            ]
        )

        # Filter to rows with content
        with_content = with_content.filter(pl.col("content").is_not_null())

        if with_content.height == 0:
            return pl.DataFrame()

        # Extract output_tokens from usage struct
        with_content = with_content.with_columns(
            pl.col("usage").struct.field("output_tokens").alias("output_tokens")
        )

        # Extract tool details (name + detail) from content JSON
        with_tools = with_content.with_columns(
            pl.col("content")
            .map_elements(_serialize_tool_details, return_dtype=pl.Utf8)
            .alias("tool_details_json")
        )

        # Parse the JSON and filter to rows with tools
        def count_tools(json_str: str) -> int:
            return len(json.loads(json_str))

        with_tools = with_tools.with_columns(
            pl.col("tool_details_json")
            .map_elements(count_tools, return_dtype=pl.Int64)
            .alias("tool_count")
        )

        with_tools = with_tools.filter(pl.col("tool_count") > 0)

        if with_tools.height == 0:
            return pl.DataFrame()

        # Calculate tokens per tool (distribute evenly across tools in message)
        with_tools = with_tools.with_columns(
            (pl.col("output_tokens") / pl.col("tool_count"))
            .cast(pl.Int64)
            .alias("tokens_per_tool")
        )

        # Expand each row to multiple rows (one per tool)
        rows: list[dict[str, object]] = []
        for row in with_tools.iter_rows(named=True):
            tool_details: list[list[str | None]] = json.loads(
                str(row["tool_details_json"])
            )
            tokens_per = int(row["tokens_per_tool"] or 0)
            for tool_name, tool_detail in tool_details:
                rows.append(
                    {
                        "timestamp": row["timestamp"],
                        "session_id": row["session_id"],
                        "tool_name": tool_name,
                        "tool_detail": tool_detail,
                        "output_tokens": tokens_per,
                    }
                )

        if not rows:
            return pl.DataFrame()

        return pl.DataFrame(rows).select(
            [
                pl.col("timestamp"),
                pl.col("session_id"),
                pl.col("tool_name"),
                pl.col("tool_detail"),
                pl.col("output_tokens"),
            ]
        )
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.StructFieldNotFoundError):
        return pl.DataFrame()


def extract_agent_info_from_transcript(df: pl.DataFrame) -> pl.DataFrame:
    """Extract agent/sidechain information from a transcript DataFrame.

    Looks for Task tool invocations and agent markers:
    - isSidechain field
    - agentId field
    - subagent_type from Task tool input

    Args:
        df: DataFrame with transcript data.

    Returns:
        DataFrame with agent information.
    """
    # Check for agent markers
    has_sidechain = "isSidechain" in df.columns
    has_agent_id = "agentId" in df.columns

    if not has_sidechain and not has_agent_id:
        return pl.DataFrame()

    try:
        cols = [pl.col("timestamp")]

        if "sessionId" in df.columns:
            cols.append(pl.col("sessionId").alias("session_id"))

        if has_sidechain:
            cols.append(pl.col("isSidechain").alias("is_sidechain"))

        if has_agent_id:
            cols.append(pl.col("agentId").alias("agent_id"))

        # Filter to rows with sidechain or agent data
        agent_df = df.select(cols)

        if has_sidechain:
            return agent_df.filter(pl.col("is_sidechain").is_not_null())

        return agent_df
    except pl.exceptions.ColumnNotFoundError:
        return pl.DataFrame()


def load_all_transcripts(
    transcript_dir: TranscriptDirectory,
    *,
    include_agents: bool = True,
) -> pl.DataFrame:
    """Load and concatenate all transcript files into a single DataFrame.

    Args:
        transcript_dir: Discovered transcript directory.
        include_agents: Whether to include agent transcripts.

    Returns:
        Concatenated DataFrame with all transcript data.
    """
    dfs: list[pl.DataFrame] = []

    # Load main sessions
    for transcript in transcript_dir.main_sessions:
        try:
            df = parse_transcript_file(transcript.path)
            # Add source info
            df = df.with_columns(
                [
                    pl.lit(transcript.session_id).alias("_source_session_id"),
                    pl.lit(False).alias("_is_agent_transcript"),
                ]
            )
            dfs.append(df)
        except (pl.exceptions.ComputeError, FileNotFoundError):
            continue

    # Load agent transcripts if requested
    if include_agents:
        for transcript in transcript_dir.agent_transcripts:
            try:
                df = parse_transcript_file(transcript.path)
                # Add source info
                df = df.with_columns(
                    [
                        pl.lit(transcript.agent_id).alias("_source_session_id"),
                        pl.lit(True).alias("_is_agent_transcript"),
                    ]
                )
                dfs.append(df)
            except (pl.exceptions.ComputeError, FileNotFoundError):
                continue

    if not dfs:
        return pl.DataFrame()

    # Concatenate with diagonal strategy to handle schema differences
    return pl.concat(dfs, how="diagonal")


def load_usage_data(
    transcript_dir: TranscriptDirectory,
    *,
    include_agents: bool = True,
) -> pl.DataFrame:
    """Load and extract usage data from all transcript files.

    This function processes each file individually and extracts only the usage
    data before concatenating, avoiding schema conflicts from different struct
    types in the raw JSONL files.

    Args:
        transcript_dir: Discovered transcript directory.
        include_agents: Whether to include agent transcripts.

    Returns:
        DataFrame with usage data (consistent schema).
    """
    usage_dfs: list[pl.DataFrame] = []

    # Process main sessions
    for transcript in transcript_dir.main_sessions:
        try:
            df = parse_transcript_file(transcript.path)
            usage = extract_usage_from_transcript(df)
            if usage.height > 0:
                # Add source info
                usage = usage.with_columns(
                    [
                        pl.lit(transcript.session_id).alias("_source_session_id"),
                        pl.lit(False).alias("_is_agent_transcript"),
                    ]
                )
                usage_dfs.append(usage)
        except (
            pl.exceptions.ComputeError,
            pl.exceptions.SchemaError,
            FileNotFoundError,
        ):
            # Skip files that can't be parsed due to schema issues
            continue

    # Process agent transcripts if requested
    if include_agents:
        for transcript in transcript_dir.agent_transcripts:
            try:
                df = parse_transcript_file(transcript.path)
                usage = extract_usage_from_transcript(df)
                if usage.height > 0:
                    # Add source info
                    usage = usage.with_columns(
                        [
                            pl.lit(transcript.agent_id).alias("_source_session_id"),
                            pl.lit(True).alias("_is_agent_transcript"),
                        ]
                    )
                    usage_dfs.append(usage)
            except (
                pl.exceptions.ComputeError,
                pl.exceptions.SchemaError,
                FileNotFoundError,
            ):
                # Skip files that can't be parsed due to schema issues
                continue

    if not usage_dfs:
        return pl.DataFrame()

    return pl.concat(usage_dfs)


def load_tool_data(
    transcript_dir: TranscriptDirectory,
    *,
    include_agents: bool = True,
) -> pl.DataFrame:
    """Load and extract tool usage data from all transcript files.

    Args:
        transcript_dir: Discovered transcript directory.
        include_agents: Whether to include agent transcripts.

    Returns:
        DataFrame with tool usage data (consistent schema).
    """
    tool_dfs: list[pl.DataFrame] = []

    # Process main sessions
    for transcript in transcript_dir.main_sessions:
        try:
            df = parse_transcript_file(transcript.path)
            tools = extract_tool_usage_from_transcript(df)
            if tools.height > 0:
                tool_dfs.append(tools)
        except (
            pl.exceptions.ComputeError,
            pl.exceptions.SchemaError,
            FileNotFoundError,
        ):
            continue

    # Process agent transcripts if requested
    if include_agents:
        for transcript in transcript_dir.agent_transcripts:
            try:
                df = parse_transcript_file(transcript.path)
                tools = extract_tool_usage_from_transcript(df)
                if tools.height > 0:
                    tool_dfs.append(tools)
            except (
                pl.exceptions.ComputeError,
                pl.exceptions.SchemaError,
                FileNotFoundError,
            ):
                continue

    if not tool_dfs:
        return pl.DataFrame()

    return pl.concat(tool_dfs)
