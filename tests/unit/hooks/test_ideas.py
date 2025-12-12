"""Unit tests for /idea workflow orchestration actions."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.enums import HookEventType
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import (
    PostToolUseInput,
    PreToolUseInput,
    UserPromptSubmitInput,
)
from oaps.hooks.ideas import (
    _extract_idea_title,
    _replace_section,
    init_idea_workflow,
    track_document_creation,
)
from oaps.session import Session
from oaps.utils import create_state_store

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def mock_logger() -> MagicMock:
    from unittest.mock import MagicMock

    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    state_dir = tmp_path / ".oaps" / "state"
    state_dir.mkdir(parents=True)
    return state_dir


@pytest.fixture
def session_state_file(state_dir: Path) -> Path:
    return state_dir / "test-session.state"


@pytest.fixture
def session(session_state_file: Path) -> Session:
    store = create_state_store(session_state_file, session_id="test-session")
    return Session(id="test-session", store=store)


@pytest.fixture
def user_prompt_submit_input(tmp_path: Path) -> UserPromptSubmitInput:
    transcript = tmp_path / "transcript.json"
    return UserPromptSubmitInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="UserPromptSubmit",
        cwd="/home/user/project",
        prompt="/idea My new brainstorming idea",
    )


@pytest.fixture
def user_prompt_context(
    user_prompt_submit_input: UserPromptSubmitInput,
    mock_logger: MagicMock,
    tmp_path: Path,
    session_state_file: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
        hook_input=user_prompt_submit_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=session_state_file,
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def pre_tool_use_input(tmp_path: Path) -> PreToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PreToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd="/home/user/project",
        tool_name="Write",
        tool_input={
            "file_path": "/home/user/project/.oaps/docs/ideas/20241218-120000-test.md",
            "content": "# Test idea content",
        },
        tool_use_id="tool-123",
    )


@pytest.fixture
def pre_tool_use_context(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
    session_state_file: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=session_state_file,
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def post_tool_use_input(tmp_path: Path) -> PostToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PostToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PostToolUse",
        cwd="/home/user/project",
        tool_name="Write",
        tool_input={
            "file_path": "/home/user/project/.oaps/docs/ideas/20241218-120000-test.md",
            "content": "# Test idea content",
        },
        tool_use_id="tool-123",
        tool_response={"result": "File written successfully"},
    )


@pytest.fixture
def post_tool_use_context(
    post_tool_use_input: PostToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
    session_state_file: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.POST_TOOL_USE,
        hook_input=post_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=session_state_file,
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


class TestWorkflowInitialization:
    def test_init_idea_workflow_creates_workflow_id(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = init_idea_workflow(user_prompt_context)

        assert result["status"] == "initialized"
        assert "workflow_id" in result
        assert len(str(result["workflow_id"])) == 8

    def test_init_idea_workflow_sets_active_flag(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(user_prompt_context)

        assert session.get("idea.active") == 1

    def test_init_idea_workflow_sets_initial_phase(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(user_prompt_context)

        assert session.get("idea.phase") == "seed"

    def test_init_idea_workflow_extracts_title(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(user_prompt_context)

        title = session.get("idea.title")
        assert title == "My new brainstorming idea"

    def test_init_idea_workflow_sets_document_created_flag(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(user_prompt_context)

        assert session.get("idea.document_created") == 0

    def test_init_idea_workflow_sets_status(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(user_prompt_context)

        assert session.get("idea.status") == "seed"

    def test_init_idea_workflow_returns_suggest_message(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = init_idea_workflow(user_prompt_context)

        assert "suggest_message" in result
        assert "initialized" in str(result["suggest_message"])


class TestDocumentTracking:
    def test_track_document_creation_sets_path(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        # Initialize workflow first
        init_idea_workflow(post_tool_use_context)

        result = track_document_creation(post_tool_use_context)

        assert result["status"] == "document_created"
        file_path = "/home/user/project/.oaps/docs/ideas/20241218-120000-test.md"
        assert result["path"] == file_path

    def test_track_document_creation_updates_phase(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(post_tool_use_context)

        track_document_creation(post_tool_use_context)

        assert session.get("idea.phase") == "exploring"

    def test_track_document_creation_extracts_idea_id(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(post_tool_use_context)

        track_document_creation(post_tool_use_context)

        # ID is extracted from filename stem
        assert session.get("idea.idea_id") == "20241218-120000-test"

    def test_track_document_creation_sets_document_created_flag(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_idea_workflow(post_tool_use_context)

        track_document_creation(post_tool_use_context)

        assert session.get("idea.document_created") == 1

    def test_track_document_creation_returns_error_without_tool_input(
        self,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
        session: Session,
    ) -> None:
        transcript = tmp_path / "transcript.json"
        empty_input = PostToolUseInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/home/user/project",
            tool_name="Write",
            tool_input={},  # No file_path
            tool_use_id="tool-123",
            tool_response={"result": "success"},
        )
        context = HookContext(
            hook_event_type=HookEventType.POST_TOOL_USE,
            hook_input=empty_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        init_idea_workflow(context)
        result = track_document_creation(context)

        assert "error" in result


class TestHelperFunctions:
    def test_extract_idea_title_from_idea_command(self) -> None:
        prompt = "/idea My amazing new idea"
        result = _extract_idea_title(prompt)
        assert result == "My amazing new idea"

    def test_extract_idea_title_with_flags(self) -> None:
        prompt = "/idea --type technical My technical idea"
        result = _extract_idea_title(prompt)
        assert result == "My technical idea"

    def test_extract_idea_title_with_oaps_prefix(self) -> None:
        prompt = "/oaps:idea An idea with prefix"
        result = _extract_idea_title(prompt)
        assert result == "An idea with prefix"

    def test_extract_idea_title_empty(self) -> None:
        assert _extract_idea_title("") == ""
        assert _extract_idea_title("/idea") == ""

    def test_extract_idea_title_limits_length(self) -> None:
        long_title = "x" * 150
        result = _extract_idea_title(f"/idea {long_title}")
        assert len(result) <= 100

    def test_extract_idea_title_first_line_only(self) -> None:
        prompt = "/idea First line\nSecond line\nThird line"
        result = _extract_idea_title(prompt)
        assert result == "First line"

    def test_replace_section_replaces_content(self) -> None:
        body = """Some content before

<!-- idea-header-start -->
Old header content
<!-- idea-header-end -->

Some content after"""

        result = _replace_section(
            body, "idea-header-start", "idea-header-end", "New header"
        )

        assert "New header" in result
        assert "Old header content" not in result

    def test_replace_section_preserves_markers(self) -> None:
        body = """<!-- test-start -->
Old content
<!-- test-end -->"""

        result = _replace_section(body, "test-start", "test-end", "New content")

        assert "<!-- test-start -->" in result
        assert "<!-- test-end -->" in result
        assert "New content" in result

    def test_replace_section_handles_multiline_content(self) -> None:
        body = """<!-- section-start -->
Line 1
Line 2
Line 3
<!-- section-end -->"""

        result = _replace_section(body, "section-start", "section-end", "Single line")

        assert "Single line" in result
        assert "Line 1" not in result
        assert "Line 2" not in result

    def test_replace_section_returns_unchanged_if_no_markers(self) -> None:
        body = "Content without markers"

        result = _replace_section(body, "start", "end", "Replacement")

        assert result == body


class TestNoSessionHandling:
    def test_init_returns_error_without_session_file(
        self, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        transcript = tmp_path / "transcript.json"
        input_data = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="/idea test",
        )
        context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=input_data,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=tmp_path / "nonexistent" / "state.db",
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = init_idea_workflow(context)

        assert result.get("error") == "No session available"

    def test_track_document_creation_returns_error_without_session(
        self, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        transcript = tmp_path / "transcript.json"
        input_data = PostToolUseInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/home/user/project",
            tool_name="Write",
            tool_input={"file_path": "/some/path.md"},
            tool_use_id="tool-123",
            tool_response={"result": "success"},
        )
        context = HookContext(
            hook_event_type=HookEventType.POST_TOOL_USE,
            hook_input=input_data,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=tmp_path / "nonexistent" / "state.db",
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = track_document_creation(context)

        assert result.get("error") == "No session"
