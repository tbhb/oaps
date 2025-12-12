"""Unit tests for /dev workflow orchestration actions."""

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
from oaps.hooks.workflows import (
    _extract_feature_description,
    _extract_file_paths,
    _summarize_exploration,
    capture_architecture_decision,
    capture_review_decision,
    clear_failure_state,
    configure_complex_workflow,
    configure_simple_workflow,
    handle_agent_failure,
    init_dev_workflow,
    reset_review_state,
    set_awaiting_architecture_decision,
    set_awaiting_review_decision,
    skip_exploration_phase,
    track_architect_completion,
    track_developer_completion,
    track_explorer_completion,
    track_reviewer_completion,
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
        prompt="/dev Add a new feature for user authentication",
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
        tool_name="Task",
        tool_input={"subagent_type": "code-explorer", "prompt": "Explore the codebase"},
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
        tool_name="Task",
        tool_input={"subagent_type": "code-explorer"},
        tool_use_id="tool-123",
        tool_response={
            "result": "Found key files:\n- src/auth/login.py\n- src/auth/session.py"
        },
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
    def test_init_dev_workflow_creates_workflow_id(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = init_dev_workflow(user_prompt_context)

        assert result["status"] == "initialized"
        assert "workflow_id" in result
        assert len(str(result["workflow_id"])) == 8

    def test_init_dev_workflow_sets_active_flag(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        assert session.get("dev.active") == 1

    def test_init_dev_workflow_sets_initial_phase(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        assert session.get("dev.phase") == "discovery"

    def test_init_dev_workflow_extracts_feature_description(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        desc = session.get("dev.feature_description")
        assert desc == "Add a new feature for user authentication"

    def test_init_dev_workflow_initializes_explorer_tracking(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        assert session.get("dev.expected_explorers") == 3
        assert session.get("dev.explorer_count") == 0
        assert session.get("dev.exploration_complete") == 0

    def test_init_dev_workflow_initializes_architect_tracking(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        assert session.get("dev.expected_architects") == 3
        assert session.get("dev.architect_count") == 0
        assert session.get("dev.architecture_complete") == 0

    def test_init_dev_workflow_initializes_reviewer_tracking(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(user_prompt_context)

        assert session.get("dev.expected_reviewers") == 3
        assert session.get("dev.reviewer_count") == 0
        assert session.get("dev.review_complete") == 0

    def test_configure_simple_workflow_reduces_agent_counts(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = configure_simple_workflow(user_prompt_context)

        assert result["workflow_variant"] == "simple"
        assert session.get("dev.expected_explorers") == 1
        assert session.get("dev.expected_architects") == 1
        assert session.get("dev.expected_reviewers") == 1

    def test_configure_complex_workflow_sets_full_counts(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = configure_complex_workflow(user_prompt_context)

        assert result["workflow_variant"] == "complex"
        assert session.get("dev.expected_explorers") == 3
        assert session.get("dev.expected_architects") == 3
        assert session.get("dev.expected_reviewers") == 3
        assert session.get("dev.requires_security_review") == 1

    def test_skip_exploration_phase_marks_exploration_complete(
        self, user_prompt_context: HookContext, session: Session
    ) -> None:
        result = skip_exploration_phase(user_prompt_context)

        assert result["exploration_skipped"] is True
        assert session.get("dev.exploration_complete") == 1
        assert session.get("dev.phase") == "clarification"


class TestAgentTracking:
    def test_track_explorer_increments_count(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        result = track_explorer_completion(post_tool_use_context)

        assert result["explorer_count"] == 1
        assert session.get("dev.explorer_count") == 1

    def test_track_explorer_aggregates_findings(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        track_explorer_completion(post_tool_use_context)

        findings = session.get("dev.exploration_findings_raw")
        assert isinstance(findings, str)
        assert "Explorer 1 Findings" in findings
        assert "src/auth/login.py" in findings

    def test_track_explorer_marks_complete_when_all_done(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)
        session.set("dev.expected_explorers", 2)

        track_explorer_completion(post_tool_use_context)
        result = track_explorer_completion(post_tool_use_context)

        assert result["status"] == "exploration_complete"
        assert session.get("dev.exploration_complete") == 1
        assert session.get("dev.phase") == "clarification"

    def test_track_architect_increments_count(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        result = track_architect_completion(post_tool_use_context)

        assert result["architect_count"] == 1
        assert session.get("dev.architect_count") == 1

    def test_track_architect_marks_complete_when_all_done(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)
        session.set("dev.expected_architects", 1)

        result = track_architect_completion(post_tool_use_context)

        assert result["status"] == "architecture_complete"
        assert session.get("dev.architecture_complete") == 1
        assert session.get("dev.phase") == "architecture_review"

    def test_track_developer_marks_implementation_complete(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        result = track_developer_completion(post_tool_use_context)

        assert result["status"] == "implementation_complete"
        assert session.get("dev.implementation_complete") == 1
        assert session.get("dev.phase") == "review"

    def test_track_developer_extracts_modified_files(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        track_developer_completion(post_tool_use_context)

        modified = session.get("dev.modified_files")
        assert isinstance(modified, str)

    def test_track_developer_detects_security_critical_files(
        self,
        post_tool_use_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        transcript = tmp_path / "transcript.json"
        security_input = PostToolUseInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/home/user/project",
            tool_name="Task",
            tool_input={"subagent_type": "code-developer"},
            tool_use_id="tool-123",
            tool_response={
                "result": "Modified src/auth/password.py and src/auth/token.py"
            },
        )
        security_context = HookContext(
            hook_event_type=HookEventType.POST_TOOL_USE,
            hook_input=security_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )
        init_dev_workflow(security_context)

        result = track_developer_completion(security_context)

        assert result["requires_security_review"] is True
        assert session.get("dev.requires_security_review") == 1

    def test_track_reviewer_increments_count(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        result = track_reviewer_completion(post_tool_use_context)

        assert result["reviewer_count"] == 1
        assert session.get("dev.reviewer_count") == 1

    def test_track_reviewer_marks_complete_when_all_done(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)
        session.set("dev.expected_reviewers", 1)

        result = track_reviewer_completion(post_tool_use_context)

        assert result["status"] == "review_complete"
        assert session.get("dev.review_complete") == 1
        assert session.get("dev.phase") == "review_decision"


class TestUserDecisionCapture:
    def test_set_awaiting_architecture_decision(
        self, pre_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(pre_tool_use_context)

        result = set_awaiting_architecture_decision(pre_tool_use_context)

        assert result["status"] == "awaiting_architecture_decision"
        assert session.get("dev.awaiting_architecture_decision") == 1

    def test_capture_architecture_decision_option1(
        self,
        user_prompt_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(user_prompt_context)
        session.set("dev.awaiting_architecture_decision", 1)

        transcript = tmp_path / "transcript.json"
        decision_input = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="Go with option 1",
        )
        decision_context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=decision_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = capture_architecture_decision(decision_context)

        assert result["status"] == "architecture_approved"
        assert result["chosen_approach"] == "minimal"
        assert session.get("dev.architecture_approved") == 1
        assert session.get("dev.phase") == "implementation"

    def test_capture_architecture_decision_proceed(
        self,
        user_prompt_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(user_prompt_context)
        session.set("dev.awaiting_architecture_decision", 1)

        transcript = tmp_path / "transcript.json"
        decision_input = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="Looks good, proceed",
        )
        decision_context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=decision_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = capture_architecture_decision(decision_context)

        assert result["status"] == "architecture_approved"
        assert result["chosen_approach"] == "recommended"

    def test_capture_architecture_decision_unclear(
        self,
        user_prompt_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(user_prompt_context)
        session.set("dev.awaiting_architecture_decision", 1)

        transcript = tmp_path / "transcript.json"
        decision_input = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="Tell me more about the options",
        )
        decision_context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=decision_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = capture_architecture_decision(decision_context)

        assert result["status"] == "decision_unclear"

    def test_set_awaiting_review_decision(
        self, pre_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(pre_tool_use_context)

        result = set_awaiting_review_decision(pre_tool_use_context)

        assert result["status"] == "awaiting_review_decision"
        assert session.get("dev.awaiting_review_decision") == 1

    def test_capture_review_decision_fix_now(
        self,
        user_prompt_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(user_prompt_context)
        session.set("dev.awaiting_review_decision", 1)
        session.set("dev.implementation_complete", 1)

        transcript = tmp_path / "transcript.json"
        decision_input = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="Fix those issues now",
        )
        decision_context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=decision_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = capture_review_decision(decision_context)

        assert result["status"] == "fix_now"
        assert session.get("dev.review_decision") == "fix_now"
        assert session.get("dev.implementation_complete") == 0

    def test_capture_review_decision_defer(
        self,
        user_prompt_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(user_prompt_context)
        session.set("dev.awaiting_review_decision", 1)

        transcript = tmp_path / "transcript.json"
        decision_input = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/home/user/project",
            prompt="Skip those for now, defer them",
        )
        decision_context = HookContext(
            hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
            hook_input=decision_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = capture_review_decision(decision_context)

        assert result["status"] == "fix_later"
        assert session.get("dev.review_decision") == "fix_later"
        assert session.get("dev.phase") == "summary"


class TestErrorHandling:
    def test_handle_agent_failure_records_state(
        self,
        post_tool_use_context: HookContext,
        session: Session,
        mock_logger: MagicMock,
        tmp_path: Path,
        session_state_file: Path,
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        transcript = tmp_path / "transcript.json"
        failure_input = PostToolUseInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/home/user/project",
            tool_name="Task",
            tool_input={"subagent_type": "code-explorer"},
            tool_use_id="tool-123",
            tool_response={"error": "Agent failed"},
        )
        failure_context = HookContext(
            hook_event_type=HookEventType.POST_TOOL_USE,
            hook_input=failure_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=session_state_file,
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        result = handle_agent_failure(failure_context)

        assert result["status"] == "failure_recorded"
        assert result["agent_type"] == "code-explorer"
        assert result["can_retry"] is True
        assert session.get("dev.last_agent_failed") == 1
        assert session.get("dev.last_failed_agent_type") == "code-explorer"

    def test_handle_agent_failure_increments_count(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)

        handle_agent_failure(post_tool_use_context)
        result = handle_agent_failure(post_tool_use_context)

        assert result["failure_count"] == 2

    def test_handle_agent_failure_limits_retries(
        self, post_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(post_tool_use_context)
        session.set("dev.agent_failure_count", 2)

        result = handle_agent_failure(post_tool_use_context)

        assert result["failure_count"] == 3
        assert result["can_retry"] is False

    def test_clear_failure_state(
        self, pre_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(pre_tool_use_context)
        session.set("dev.last_agent_failed", 1)
        session.set("dev.last_failed_agent_type", "code-explorer")

        result = clear_failure_state(pre_tool_use_context)

        assert result["status"] == "failure_state_cleared"
        assert session.get("dev.last_agent_failed") == 0
        assert session.get("dev.last_failed_agent_type") == ""

    def test_reset_review_state(
        self, pre_tool_use_context: HookContext, session: Session
    ) -> None:
        init_dev_workflow(pre_tool_use_context)
        session.set("dev.review_complete", 1)
        session.set("dev.reviewer_count", 3)
        session.set("dev.review_findings_raw", "Some findings")

        result = reset_review_state(pre_tool_use_context)

        assert result["status"] == "review_state_reset"
        assert session.get("dev.review_complete") == 0
        assert session.get("dev.reviewer_count") == 0
        assert session.get("dev.review_findings_raw") == ""


class TestHelperFunctions:
    def test_extract_feature_description_from_dev_ng_command(self) -> None:
        prompt = "/dev Add user authentication feature"
        result = _extract_feature_description(prompt)
        assert result == "Add user authentication feature"

    def test_extract_feature_description_with_flags(self) -> None:
        prompt = "/dev --quick Fix the typo in README"
        result = _extract_feature_description(prompt)
        assert result == "Fix the typo in README"

    def test_extract_feature_description_with_oaps_prefix(self) -> None:
        prompt = "/oaps:dev Add a new API endpoint"
        result = _extract_feature_description(prompt)
        assert result == "Add a new API endpoint"

    def test_extract_feature_description_empty_prompt(self) -> None:
        assert _extract_feature_description("") == ""
        assert _extract_feature_description("/dev") == ""

    def test_extract_file_paths_from_text(self) -> None:
        text = "Modified files:\n- src/auth/login.py\n- src/api/users.py"
        result = _extract_file_paths(text)

        assert "src/auth/login.py" in result
        assert "src/api/users.py" in result

    def test_extract_file_paths_with_backticks(self) -> None:
        text = "Found `config.toml` and `src/main.py` in the project"
        result = _extract_file_paths(text)

        assert "config.toml" in result
        assert "src/main.py" in result

    def test_extract_file_paths_deduplicates(self) -> None:
        text = "Found src/main.py and also src/main.py again"
        result = _extract_file_paths(text)

        assert result.count("src/main.py") == 1

    def test_extract_file_paths_empty_text(self) -> None:
        assert _extract_file_paths("") == []
        assert _extract_file_paths("No file paths here") == []

    def test_summarize_exploration_short_text(self) -> None:
        findings = "Short findings"
        result = _summarize_exploration(findings)
        assert result == "Short findings"

    def test_summarize_exploration_truncates_long_text(self) -> None:
        long_text = "x" * 3000
        result = _summarize_exploration(long_text)

        assert len(result) < 3000
        assert "[Truncated for brevity]" in result

    def test_summarize_exploration_empty(self) -> None:
        assert _summarize_exploration("") == "No exploration findings available."


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
            prompt="/dev test",
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

        result = init_dev_workflow(context)

        assert result.get("error") == "No session available"
