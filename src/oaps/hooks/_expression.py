"""Expression evaluation for hook conditions.

This module provides the expression evaluator for hook condition expressions,
using rule-engine as the underlying expression parser and evaluator with
custom OAPS functions.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import rule_engine
import rule_engine.builtins as rule_builtins
from rule_engine import errors as rule_errors

from oaps.exceptions import ExpressionError

from ._functions import (
    CurrentBranchFunction,
    EnvFunction,
    FileExistsFunction,
    GitFileInFunction,
    GitHasConflictsFunction,
    GitHasModifiedFunction,
    GitHasStagedFunction,
    GitHasUntrackedFunction,
    HasConflictsFunction,
    IsExecutableFunction,
    IsGitRepoFunction,
    IsModifiedFunction,
    IsPathUnderFunction,
    IsStagedFunction,
    MatchesGlobFunction,
    ProjectGetFunction,
    SessionGetFunction,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from oaps.hooks._context import HookContext
    from oaps.project import Project
    from oaps.session import Session
    from oaps.utils import GitContext


@runtime_checkable
class ExpressionFunction(Protocol):
    """Protocol for custom expression functions."""

    def __call__(self, *args: object) -> object:
        """Execute the function with provided arguments."""
        ...


@dataclass(frozen=True, slots=True)
class FunctionRegistry:
    """Registry of custom expression functions.

    Provides lookup for custom functions by name (without the $ prefix).
    """

    _functions: dict[str, Callable[..., object]] = field(default_factory=dict)

    def get(self, name: str) -> Callable[..., object] | None:
        """Get function by name (without $ prefix).

        Args:
            name: Function name without the $ prefix.

        Returns:
            The function callable, or None if not found.
        """
        return self._functions.get(name)

    def all_functions(self) -> dict[str, Callable[..., object]]:
        """Get all registered functions.

        Returns:
            A copy of the function registry dictionary.
        """
        return dict(self._functions)


def create_function_registry(
    cwd: str,
    session: Session | None = None,
    git: GitContext | None = None,
    project: Project | None = None,
) -> FunctionRegistry:
    """Create a registry with all OAPS expression functions.

    Args:
        cwd: Current working directory for path-relative functions.
        session: Session for $session_get. If None, returns None for all keys.
        git: GitContext for git-related functions. If None, git functions
             return safe defaults (False/None).
        project: Project for $project_get. If None, returns None for all keys.

    Returns:
        A FunctionRegistry with all OAPS expression functions registered.
    """
    from oaps.session import Session as SessionClass  # noqa: PLC0415
    from oaps.utils import MockStateStore  # noqa: PLC0415

    # Use mock session if none provided
    if session is None:
        session = SessionClass(id="mock", store=MockStateStore())

    # Extract git file sets with safe defaults when git context is None
    staged_files: frozenset[str] = git.staged_files if git else frozenset()
    modified_files: frozenset[str] = git.modified_files if git else frozenset()
    untracked_files: frozenset[str] = git.untracked_files if git else frozenset()
    conflict_files: frozenset[str] = git.conflict_files if git else frozenset()
    branch: str | None = git.branch if git else None

    functions: dict[str, Callable[..., object]] = {
        # Path and file functions
        "is_path_under": IsPathUnderFunction(),
        "file_exists": FileExistsFunction(),
        "is_executable": IsExecutableFunction(),
        "matches_glob": MatchesGlobFunction(),
        "env": EnvFunction(),
        "is_git_repo": IsGitRepoFunction(cwd=cwd),
        "session_get": SessionGetFunction(session=session),
        "project_get": ProjectGetFunction(project=project),
        # Git file status functions
        "is_staged": IsStagedFunction(staged_files=staged_files),
        "is_modified": IsModifiedFunction(modified_files=modified_files),
        "has_conflicts": HasConflictsFunction(conflict_files=conflict_files),
        "current_branch": CurrentBranchFunction(branch=branch),
        # Git has_* pattern matching functions
        "git_has_staged": GitHasStagedFunction(staged_files=staged_files),
        "git_has_modified": GitHasModifiedFunction(modified_files=modified_files),
        "git_has_untracked": GitHasUntrackedFunction(untracked_files=untracked_files),
        "git_has_conflicts": GitHasConflictsFunction(conflict_files=conflict_files),
        # Git file lookup function
        "git_file_in": GitFileInFunction(git=git),
    }
    return FunctionRegistry(_functions=functions)


def _extract_cwd(hook_input: object) -> str | None:
    """Extract cwd from hook_input using getattr."""
    cwd: object = getattr(hook_input, "cwd", None)
    if cwd is not None:
        return str(cwd)
    return None


def _extract_optional_attr(hook_input: object, attr: str) -> object:
    """Extract optional attribute from hook_input, returning None if missing."""
    return getattr(hook_input, attr, None)


def _adapt_git_context(context: HookContext, result: dict[str, object]) -> None:
    """Add git context variables to result dict."""
    if context.git is not None:
        result["git_branch"] = context.git.branch
        result["git_is_dirty"] = context.git.is_dirty
        result["git_head_commit"] = context.git.head_commit
        result["git_is_detached"] = context.git.is_detached
        result["git_staged_files"] = list(context.git.staged_files)
        result["git_modified_files"] = list(context.git.modified_files)
        result["git_untracked_files"] = list(context.git.untracked_files)
        result["git_conflict_files"] = list(context.git.conflict_files)
    else:
        result["git_branch"] = None
        result["git_is_dirty"] = None
        result["git_head_commit"] = None
        result["git_is_detached"] = None
        result["git_staged_files"] = []
        result["git_modified_files"] = []
        result["git_untracked_files"] = []
        result["git_conflict_files"] = []


def _adapt_project_context(context: HookContext, result: dict[str, object]) -> None:
    """Add project context variables to result dict."""
    if context.project is not None:
        result["project_has_changes"] = context.project.has_changes
        result["project_uncommitted_count"] = context.project.uncommitted_count
        result["project_staged_count"] = context.project.staged_count
        result["project_modified_count"] = context.project.modified_count
        result["project_untracked_count"] = context.project.untracked_count

        if context.project.diff_stats is not None:
            result["project_diff_additions"] = (
                context.project.diff_stats.total_additions
            )
            result["project_diff_deletions"] = (
                context.project.diff_stats.total_deletions
            )
            result["project_diff_files_changed"] = (
                context.project.diff_stats.files_changed
            )
        else:
            result["project_diff_additions"] = None
            result["project_diff_deletions"] = None
            result["project_diff_files_changed"] = None

        result["project_recent_commits"] = [
            {
                "sha": c.sha,
                "message": c.message,
                "author_name": c.author_name,
                "author_email": c.author_email,
                "timestamp": c.timestamp,
                "files_changed": c.files_changed,
                "parent_shas": list(c.parent_shas),
            }
            for c in context.project.recent_commits
        ]
    else:
        result["project_has_changes"] = None
        result["project_uncommitted_count"] = None
        result["project_staged_count"] = None
        result["project_modified_count"] = None
        result["project_untracked_count"] = None
        result["project_diff_additions"] = None
        result["project_diff_deletions"] = None
        result["project_diff_files_changed"] = None
        result["project_recent_commits"] = []


def adapt_context(context: HookContext) -> dict[str, object]:
    """Convert HookContext to expression evaluation context dict.

    Maps HookContext fields to expression variable names for use
    in rule-engine evaluation.

    Args:
        context: The HookContext to adapt.

    Returns:
        A dictionary suitable for rule-engine evaluation.
    """
    hook_input = context.hook_input
    result: dict[str, object] = {
        "hook_type": context.hook_event_type.value,
        "session_id": context.claude_session_id,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }

    # Extract common fields from hook_input using getattr
    result["cwd"] = _extract_cwd(hook_input)
    result["permission_mode"] = _extract_optional_attr(hook_input, "permission_mode")

    # Tool-specific fields
    result["tool_name"] = _extract_optional_attr(hook_input, "tool_name")
    result["tool_input"] = _extract_optional_attr(hook_input, "tool_input")
    result["tool_output"] = _extract_optional_attr(hook_input, "tool_response")

    # Prompt-specific fields
    result["prompt"] = _extract_optional_attr(hook_input, "prompt")

    # Add git and project context
    _adapt_git_context(context, result)
    _adapt_project_context(context, result)

    return result


def _create_rule_context(registry: FunctionRegistry) -> rule_engine.Context:
    """Create a rule-engine Context with custom function support.

    Args:
        registry: The function registry providing custom functions.

    Returns:
        A rule-engine Context configured for OAPS expressions.

    Note:
        Custom functions are registered as builtins so they can be accessed
        with the $function_name() syntax (e.g., $session_get("key")).
        They can also be accessed without the $ prefix for backwards compatibility.
    """
    functions = registry.all_functions()

    def resolver(thing: dict[str, Any], name: str) -> object:  # pyright: ignore[reportExplicitAny]
        # Handle custom functions without $ prefix (backwards compatibility)
        if name in functions:
            return functions[name]
        # Fall back to standard dict lookup
        return thing.get(name)

    # Create context with resolver for non-$ function access
    ctx = rule_engine.Context(
        resolver=resolver,
        default_value=None,
    )

    # Add custom functions to builtins for $function_name() syntax
    # The $ prefix in expressions triggers built-in scope resolution
    ctx.builtins = rule_builtins.Builtins.from_defaults(
        values=functions,
    )

    return ctx


@dataclass(frozen=True, slots=True)
class ExpressionEvaluator:
    """Evaluates condition expressions against hook contexts.

    Compiles an expression string once at creation time and can evaluate
    it efficiently against multiple contexts.
    """

    expression: str
    _rule: rule_engine.Rule | None = field(default=None, repr=False, compare=False)
    _registry: FunctionRegistry = field(
        default_factory=FunctionRegistry, repr=False, compare=False
    )

    @classmethod
    def compile(
        cls,
        expression: str,
        registry: FunctionRegistry,
    ) -> ExpressionEvaluator:
        """Compile an expression string.

        Args:
            expression: The expression to compile. Empty/whitespace returns
                        an evaluator that always matches.
            registry: Function registry for custom functions.

        Returns:
            An ExpressionEvaluator instance.

        Raises:
            ExpressionError: If the expression is syntactically invalid.
        """
        # Empty expression always matches
        if not expression.strip():
            return cls(expression=expression, _rule=None, _registry=registry)

        rule_context = _create_rule_context(registry)

        try:
            rule = rule_engine.Rule(expression, context=rule_context)
            return cls(expression=expression, _rule=rule, _registry=registry)
        except rule_errors.RuleSyntaxError as e:
            msg = f"Invalid expression syntax: {e}"
            raise ExpressionError(msg, expression=expression, cause=e) from e
        except rule_errors.SymbolResolutionError as e:
            msg = f"Unknown symbol in expression: {e.symbol_name}"
            raise ExpressionError(msg, expression=expression, cause=e) from e

    def evaluate(self, context: HookContext) -> bool:
        """Evaluate the expression against the given context.

        Args:
            context: The hook context to evaluate against.

        Returns:
            True if the expression matches (or is empty), False otherwise.

        Raises:
            ExpressionError: If evaluation fails.
        """
        # Empty expression always matches
        if self._rule is None:
            return True

        context_dict = adapt_context(context)

        try:
            result = self._rule.matches(context_dict)
            return bool(result)
        except rule_errors.EvaluationError as e:
            msg = f"Expression evaluation failed: {e}"
            raise ExpressionError(msg, expression=self.expression, cause=e) from e


def evaluate_condition(
    expression: str,
    context: HookContext,
    session: Session | None = None,
) -> bool:
    """Convenience function to compile and evaluate an expression.

    For one-off evaluations. If evaluating the same expression against
    multiple contexts, use ExpressionEvaluator.compile() directly for
    better performance.

    Args:
        expression: The expression to evaluate.
        context: The hook context.
        session: Optional session for $session_get.

    Returns:
        True if condition matches, False otherwise.

    Raises:
        ExpressionError: If the expression is invalid or evaluation fails.
    """
    cwd = _extract_cwd(context.hook_input) or ""
    registry = create_function_registry(cwd=cwd, session=session, git=context.git)
    evaluator = ExpressionEvaluator.compile(expression, registry)
    return evaluator.evaluate(context)
