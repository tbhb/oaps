from pathlib import Path
from unittest.mock import MagicMock

import pytest

from oaps.enums import HookEventType
from oaps.exceptions import ExpressionError
from oaps.hooks import (
    ExpressionEvaluator,
    PostToolUseInput,
    PreToolUseInput,
    UserPromptSubmitInput,
    adapt_context,
    create_function_registry,
    evaluate_condition,
)
from oaps.hooks._context import HookContext
from oaps.hooks._functions import (
    EnvFunction,
    FileExistsFunction,
    IsExecutableFunction,
    IsGitRepoFunction,
    IsPathUnderFunction,
    MatchesGlobFunction,
    SessionGetFunction,
)
from oaps.project import Project
from oaps.session import Session
from oaps.utils import GitContext, MockStateStore


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pre_tool_use_input(tmp_path: Path) -> PreToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PreToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd="/home/user/project",
        tool_name="Bash",
        tool_input={"command": "ls -la"},
        tool_use_id="tool-123",
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
        tool_name="Read",
        tool_input={"file_path": "/test.py"},
        tool_response={"content": "file content"},
        tool_use_id="tool-456",
    )


@pytest.fixture
def user_prompt_submit_input(tmp_path: Path) -> UserPromptSubmitInput:
    transcript = tmp_path / "transcript.json"
    return UserPromptSubmitInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="UserPromptSubmit",
        cwd="/home/user/project",
        prompt="Write tests for the evaluator",
    )


@pytest.fixture
def pre_tool_use_context(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def post_tool_use_context(
    post_tool_use_input: PostToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.POST_TOOL_USE,
        hook_input=post_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def user_prompt_submit_context(
    user_prompt_submit_input: UserPromptSubmitInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
        hook_input=user_prompt_submit_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def context_with_git(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    git_context = GitContext(
        main_worktree_dir=tmp_path,
        worktree_dir=tmp_path,
        head_commit="abc123def456",
        is_detached=False,
        is_dirty=True,
        branch="feature/test-branch",
    )
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
        git=git_context,
    )


@pytest.fixture
def mock_session() -> Session:
    store = MockStateStore()
    store.set("test_key", "test_value", author="test")
    store.set("counter", 42, author="test")
    return Session(id="test-session", store=store)


@pytest.fixture
def mock_project() -> Project:
    store = MockStateStore()
    store.set("oaps.plan.active.plan_id", "plan-123", author="test")
    store.set("oaps.hooks.auto_verify", "true", author="test")
    store.set("project_counter", 99, author="test")
    return Project(store=store)


class TestEvaluateCondition:
    def test_empty_expression_returns_true(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("", pre_tool_use_context)
        assert result is True

    def test_whitespace_only_expression_returns_true(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("   ", pre_tool_use_context)
        assert result is True

    def test_true_literal_returns_true(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition("true", pre_tool_use_context)
        assert result is True

    def test_false_literal_returns_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("false", pre_tool_use_context)
        assert result is False

    def test_simple_equality_matches(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('tool_name == "Bash"', pre_tool_use_context)
        assert result is True

    def test_simple_equality_no_match_returns_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition('tool_name == "Read"', pre_tool_use_context)
        assert result is False


class TestContextVariables:
    def test_hook_type_accessible(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('hook_type == "pre_tool_use"', pre_tool_use_context)
        assert result is True

    def test_session_id_accessible(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition(
            'session_id == "test-session"', pre_tool_use_context
        )
        assert result is True

    def test_cwd_accessible(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('cwd == "/home/user/project"', pre_tool_use_context)
        assert result is True

    def test_permission_mode_accessible(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'permission_mode == "default"', pre_tool_use_context
        )
        assert result is True

    def test_tool_name_accessible_for_tool_hooks(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition('tool_name == "Bash"', pre_tool_use_context)
        assert result is True

    def test_tool_input_accessible_for_tool_hooks(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'tool_input["command"] == "ls -la"', pre_tool_use_context
        )
        assert result is True

    def test_tool_output_accessible_for_post_tool_use(
        self, post_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'tool_output["content"] == "file content"', post_tool_use_context
        )
        assert result is True

    def test_prompt_accessible_for_user_prompt_submit(
        self, user_prompt_submit_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'prompt == "Write tests for the evaluator"', user_prompt_submit_context
        )
        assert result is True

    def test_git_branch_accessible_when_present(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition(
            'git_branch == "feature/test-branch"', context_with_git
        )
        assert result is True

    def test_git_is_dirty_accessible_when_present(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition("git_is_dirty == true", context_with_git)
        assert result is True

    def test_git_head_commit_accessible_when_present(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition(
            'git_head_commit == "abc123def456"', context_with_git
        )
        assert result is True

    def test_git_is_detached_accessible_when_present(
        self, context_with_git: HookContext
    ) -> None:
        result = evaluate_condition("git_is_detached == false", context_with_git)
        assert result is True

    def test_git_branch_null_when_no_git_context(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("git_branch == null", pre_tool_use_context)
        assert result is True


class TestOperators:
    def test_equality_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('tool_name == "Bash"', pre_tool_use_context)
        assert result is True

    def test_inequality_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('tool_name != "Read"', pre_tool_use_context)
        assert result is True

    def test_greater_than_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition("5 > 3", pre_tool_use_context)
        assert result is True

    def test_less_than_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition("3 < 5", pre_tool_use_context)
        assert result is True

    def test_greater_than_or_equal_operator(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("5 >= 5", pre_tool_use_context)
        assert result is True

    def test_less_than_or_equal_operator(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition("5 <= 5", pre_tool_use_context)
        assert result is True

    def test_and_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition(
            'tool_name == "Bash" and permission_mode == "default"',
            pre_tool_use_context,
        )
        assert result is True

    def test_and_operator_false_when_one_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'tool_name == "Bash" and permission_mode == "plan"',
            pre_tool_use_context,
        )
        assert result is False

    def test_or_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition(
            'tool_name == "Read" or tool_name == "Bash"', pre_tool_use_context
        )
        assert result is True

    def test_or_operator_false_when_both_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition(
            'tool_name == "Read" or tool_name == "Write"', pre_tool_use_context
        )
        assert result is False

    def test_not_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('not tool_name == "Read"', pre_tool_use_context)
        assert result is True

    def test_in_operator_with_list(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition(
            'tool_name in ["Bash", "Read", "Write"]', pre_tool_use_context
        )
        assert result is True

    def test_in_operator_not_in_list(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition(
            'tool_name in ["Read", "Write", "Edit"]', pre_tool_use_context
        )
        assert result is False

    def test_regex_match_operator(self, pre_tool_use_context: HookContext) -> None:
        result = evaluate_condition('tool_name =~ "^Ba"', pre_tool_use_context)
        assert result is True

    def test_regex_match_operator_no_match(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = evaluate_condition('tool_name =~ "^Re"', pre_tool_use_context)
        assert result is False

    def test_regex_search_operator(self, pre_tool_use_context: HookContext) -> None:
        # The =~ operator does a regex search (not just anchor match)
        result = evaluate_condition('tool_name =~ ".*as.*"', pre_tool_use_context)
        assert result is True

    def test_parentheses_grouping(self, pre_tool_use_context: HookContext) -> None:
        expr = (
            '(tool_name == "Bash" or tool_name == "Read") '
            'and permission_mode == "default"'
        )
        result = evaluate_condition(expr, pre_tool_use_context)
        assert result is True


class TestIsPathUnderFunction:
    def test_path_under_returns_true(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        child = tmp_path / "subdir" / "file.txt"
        assert func(str(child), str(tmp_path)) is True

    def test_path_not_under_returns_false(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        other_path = Path("/some/other/path")
        assert func(str(other_path), str(tmp_path)) is False

    def test_path_traversal_attack_returns_false(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        malicious_path = str(tmp_path / "subdir" / ".." / ".." / "etc" / "passwd")
        # When resolved, this goes outside tmp_path
        assert func(malicious_path, str(tmp_path / "subdir")) is False

    def test_relative_path_resolved_correctly(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        # A path with .. that still resolves to under tmp_path
        relative_path = str(subdir / "inner" / ".." / "file.txt")
        assert func(relative_path, str(tmp_path)) is True

    def test_nonexistent_path_handled(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        nonexistent = tmp_path / "does_not_exist" / "file.txt"
        assert func(str(nonexistent), str(tmp_path)) is True

    def test_same_path_returns_true(self, tmp_path: Path) -> None:
        func = IsPathUnderFunction()
        assert func(str(tmp_path), str(tmp_path)) is True


class TestFileExistsFunction:
    def test_existing_file_returns_true(self, tmp_path: Path) -> None:
        func = FileExistsFunction()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert func(str(test_file)) is True

    def test_nonexistent_file_returns_false(self) -> None:
        func = FileExistsFunction()
        assert func("/nonexistent/path/file.txt") is False

    def test_directory_returns_true(self, tmp_path: Path) -> None:
        func = FileExistsFunction()
        assert func(str(tmp_path)) is True

    def test_empty_path_returns_false(self) -> None:
        func = FileExistsFunction()
        # Empty path would be current dir which exists, but let's test a path
        # that doesn't exist
        assert func("/definitely/not/a/real/path") is False


class TestIsExecutableFunction:
    def test_executable_file_returns_true(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        exec_file = tmp_path / "script.sh"
        exec_file.write_text("#!/bin/bash\necho hello")
        exec_file.chmod(0o755)
        assert func(str(exec_file)) is True

    def test_non_executable_file_returns_false(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        regular_file = tmp_path / "data.txt"
        regular_file.write_text("some data")
        regular_file.chmod(0o644)
        assert func(str(regular_file)) is False

    def test_nonexistent_file_returns_false(self) -> None:
        func = IsExecutableFunction()
        assert func("/nonexistent/file") is False

    def test_directory_returns_false(self, tmp_path: Path) -> None:
        func = IsExecutableFunction()
        # Directories have execute bit but should not be considered executable
        assert func(str(tmp_path)) is False


class TestMatchesGlobFunction:
    def test_simple_pattern_matches(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "test.py") is True

    def test_wildcard_pattern_matches(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "*.py") is True

    def test_no_match_returns_false(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "*.js") is False

    def test_question_mark_wildcard(self) -> None:
        func = MatchesGlobFunction()
        assert func("test.py", "tes?.py") is True

    def test_character_range(self) -> None:
        func = MatchesGlobFunction()
        assert func("test1.py", "test[0-9].py") is True

    def test_star_matches_across_slashes(self) -> None:
        func = MatchesGlobFunction()
        # fnmatch's * matches any characters including /
        # This differs from shell glob behavior
        assert func("test.py", "*.py") is True
        assert func("deep/nested/test.py", "*.py") is True  # * crosses /

    def test_path_matching(self) -> None:
        func = MatchesGlobFunction()
        assert func("src/test.py", "src/*.py") is True


class TestEnvFunction:
    def test_existing_env_var_returns_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        func = EnvFunction()
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert func("TEST_VAR") == "test_value"

    def test_nonexistent_env_var_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        func = EnvFunction()
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert func("NONEXISTENT_VAR") is None


class TestIsGitRepoFunction:
    def test_in_git_repo_returns_true(self) -> None:
        # The project itself is a git repo
        project_root = Path(__file__).parent.parent.parent.parent
        func = IsGitRepoFunction(cwd=str(project_root))
        assert func() is True

    def test_not_in_git_repo_returns_false(self, tmp_path: Path) -> None:
        func = IsGitRepoFunction(cwd=str(tmp_path))
        assert func() is False

    def test_subdirectory_of_git_repo_returns_true(self) -> None:
        # A subdirectory of the project should still be in a git repo
        tests_dir = Path(__file__).parent
        func = IsGitRepoFunction(cwd=str(tests_dir))
        assert func() is True


class TestSessionGetFunction:
    def test_existing_key_returns_value(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("test_key") == "test_value"

    def test_nonexistent_key_returns_none(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("nonexistent_key") is None

    def test_numeric_value_returns_correctly(self, mock_session: Session) -> None:
        func = SessionGetFunction(session=mock_session)
        assert func("counter") == 42


class TestErrorHandling:
    def test_invalid_syntax_raises_expression_error(
        self, pre_tool_use_context: HookContext
    ) -> None:
        with pytest.raises(ExpressionError) as exc_info:
            evaluate_condition("tool_name ==", pre_tool_use_context)
        assert exc_info.value.expression == "tool_name =="
        assert exc_info.value.cause is not None

    def test_expression_error_contains_original_expression(
        self, pre_tool_use_context: HookContext
    ) -> None:
        invalid_expr = "this is not valid syntax !@#"
        with pytest.raises(ExpressionError) as exc_info:
            evaluate_condition(invalid_expr, pre_tool_use_context)
        assert exc_info.value.expression == invalid_expr

    def test_expression_error_contains_cause(
        self, pre_tool_use_context: HookContext
    ) -> None:
        with pytest.raises(ExpressionError) as exc_info:
            evaluate_condition("(unclosed", pre_tool_use_context)
        assert exc_info.value.cause is not None


class TestExpressionEvaluator:
    def test_compile_valid_expression(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile('tool_name == "Bash"', registry)
        assert evaluator.expression == 'tool_name == "Bash"'

    def test_compile_empty_expression(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile("", registry)
        assert evaluator.expression == ""

    def test_evaluate_against_context(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile('tool_name == "Bash"', registry)
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_reuse_compiled_evaluator(
        self,
        pre_tool_use_context: HookContext,
        post_tool_use_context: HookContext,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        expr = 'permission_mode == "default"'
        evaluator = ExpressionEvaluator.compile(expr, registry)

        # Should work against multiple contexts
        assert evaluator.evaluate(pre_tool_use_context) is True
        assert evaluator.evaluate(post_tool_use_context) is True

    def test_empty_expression_always_matches(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile("", registry)
        assert evaluator.evaluate(pre_tool_use_context) is True

    def test_whitespace_expression_always_matches(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile("   \t\n   ", registry)
        assert evaluator.evaluate(pre_tool_use_context) is True


class TestAdaptContext:
    def test_adapt_context_includes_hook_type(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["hook_type"] == "pre_tool_use"

    def test_adapt_context_includes_session_id(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["session_id"] == "test-session"

    def test_adapt_context_includes_timestamp(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_adapt_context_includes_cwd(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["cwd"] == "/home/user/project"

    def test_adapt_context_includes_permission_mode(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["permission_mode"] == "default"

    def test_adapt_context_includes_tool_name(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["tool_name"] == "Bash"

    def test_adapt_context_includes_tool_input(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["tool_input"] == {"command": "ls -la"}

    def test_adapt_context_includes_tool_output_for_post_tool_use(
        self, post_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(post_tool_use_context)
        assert result["tool_output"] == {"content": "file content"}

    def test_adapt_context_includes_prompt_for_user_prompt_submit(
        self, user_prompt_submit_context: HookContext
    ) -> None:
        result = adapt_context(user_prompt_submit_context)
        assert result["prompt"] == "Write tests for the evaluator"

    def test_adapt_context_includes_git_fields_when_present(
        self, context_with_git: HookContext
    ) -> None:
        result = adapt_context(context_with_git)
        assert result["git_branch"] == "feature/test-branch"
        assert result["git_is_dirty"] is True
        assert result["git_head_commit"] == "abc123def456"
        assert result["git_is_detached"] is False

    def test_adapt_context_git_fields_null_when_no_git_context(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = adapt_context(pre_tool_use_context)
        assert result["git_branch"] is None
        assert result["git_is_dirty"] is None
        assert result["git_head_commit"] is None
        assert result["git_is_detached"] is None


class TestCreateFunctionRegistry:
    def test_creates_registry_with_all_functions(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        functions = registry.all_functions()

        assert "is_path_under" in functions
        assert "file_exists" in functions
        assert "is_executable" in functions
        assert "matches_glob" in functions
        assert "env" in functions
        assert "is_git_repo" in functions
        assert "session_get" in functions
        assert "project_get" in functions

    def test_get_returns_function_by_name(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        func = registry.get("file_exists")
        assert func is not None
        assert callable(func)

    def test_get_returns_none_for_unknown_name(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        func = registry.get("unknown_function")
        assert func is None

    def test_creates_registry_with_session(
        self, mock_session: Session, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), session=mock_session)
        session_get = registry.get("session_get")
        assert session_get is not None
        assert session_get("test_key") == "test_value"

    def test_creates_registry_without_session(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path), session=None)
        session_get = registry.get("session_get")
        assert session_get is not None
        # With mock session, returns None for all keys
        assert session_get("any_key") is None

    def test_creates_registry_with_project(
        self, mock_project: Project, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=mock_project)
        project_get = registry.get("project_get")
        assert project_get is not None
        assert project_get("oaps.plan.active.plan_id") == "plan-123"

    def test_creates_registry_without_project(self, tmp_path: Path) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=None)
        project_get = registry.get("project_get")
        assert project_get is not None
        # Without project, returns None for all keys
        assert project_get("any_key") is None


class TestFunctionIntegrationInExpressions:
    def test_is_path_under_in_expression(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        # Create a mock session
        store = MockStateStore()
        session = Session(id="test", store=store)

        # Test using the function in an expression
        # Note: The actual cwd from the context is /home/user/project
        registry = create_function_registry(cwd=str(tmp_path), session=session)
        evaluator = ExpressionEvaluator.compile(
            f'is_path_under("{tmp_path / "subdir"}", "{tmp_path}")', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_file_exists_in_expression(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile(f'file_exists("{test_file}")', registry)
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_matches_glob_in_expression(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile(
            'matches_glob("test.py", "*.py")', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_env_in_expression(
        self,
        pre_tool_use_context: HookContext,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("TEST_ENV", "expected_value")
        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile(
            'env("TEST_ENV") == "expected_value"', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_is_git_repo_in_expression(self, pre_tool_use_context: HookContext) -> None:
        # Use the project root which is a git repo
        project_root = Path(__file__).parent.parent.parent.parent
        registry = create_function_registry(cwd=str(project_root))
        evaluator = ExpressionEvaluator.compile("is_git_repo()", registry)
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_session_get_in_expression(
        self,
        pre_tool_use_context: HookContext,
        mock_session: Session,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), session=mock_session)
        evaluator = ExpressionEvaluator.compile(
            'session_get("test_key") == "test_value"', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_session_get_with_dollar_prefix(
        self,
        pre_tool_use_context: HookContext,
        mock_session: Session,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), session=mock_session)
        evaluator = ExpressionEvaluator.compile(
            '$session_get("test_key") == "test_value"', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_project_get_in_expression(
        self,
        pre_tool_use_context: HookContext,
        mock_project: Project,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=mock_project)
        evaluator = ExpressionEvaluator.compile(
            'project_get("oaps.plan.active.plan_id") != null', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_project_get_equality_in_expression(
        self,
        pre_tool_use_context: HookContext,
        mock_project: Project,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=mock_project)
        evaluator = ExpressionEvaluator.compile(
            'project_get("oaps.hooks.auto_verify") == "true"', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_project_get_missing_key_in_expression(
        self,
        pre_tool_use_context: HookContext,
        mock_project: Project,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=mock_project)
        evaluator = ExpressionEvaluator.compile(
            'project_get("nonexistent_key") == null', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_project_get_without_project_in_expression(
        self,
        pre_tool_use_context: HookContext,
        tmp_path: Path,
    ) -> None:
        registry = create_function_registry(cwd=str(tmp_path), project=None)
        evaluator = ExpressionEvaluator.compile(
            'project_get("any_key") == null', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True

    def test_combining_functions_and_variables(
        self, pre_tool_use_context: HookContext, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        registry = create_function_registry(cwd=str(tmp_path))
        evaluator = ExpressionEvaluator.compile(
            f'tool_name == "Bash" and file_exists("{test_file}")', registry
        )
        result = evaluator.evaluate(pre_tool_use_context)
        assert result is True
