"""Result assertion helpers for hook testing.

Provides fluent assertion helpers for ExecutionResult and related types.
"""

from typing import TYPE_CHECKING, Self, final

if TYPE_CHECKING:
    from oaps.hooks import ExecutionResult


@final
class ExecutionResultAssertion:
    """Fluent assertion helper for ExecutionResult."""

    def __init__(self, result: ExecutionResult) -> None:
        self._result: ExecutionResult = result

    @property
    def result(self) -> ExecutionResult:
        """Access the underlying result for additional assertions."""
        return self._result

    def blocked(self, reason_contains: str | None = None) -> Self:
        """Assert that execution was blocked.

        Args:
            reason_contains: If provided, assert block_reason contains this string.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If not blocked or reason doesn't match.
        """
        assert self._result.should_block, (
            f"Expected execution to be blocked, but it was not. Result: {self._result}"
        )
        if reason_contains is not None:
            assert self._result.block_reason is not None, (
                f"Expected block_reason to contain '{reason_contains}', "
                f"but block_reason is None"
            )
            assert reason_contains in self._result.block_reason, (
                f"Expected block_reason to contain '{reason_contains}', "
                f"but got: '{self._result.block_reason}'"
            )
        return self

    def not_blocked(self) -> Self:
        """Assert that execution was not blocked.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If execution was blocked.
        """
        assert not self._result.should_block, (
            f"Expected execution to not be blocked, but it was. "
            f"Block reason: {self._result.block_reason}"
        )
        return self

    def has_warnings(self, *expected: str) -> Self:
        """Assert that warnings contain expected strings.

        Args:
            *expected: Strings that should appear in the warnings.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If any expected string is not in warnings.
        """
        for exp in expected:
            assert any(exp in w for w in self._result.warnings), (
                f"Expected warnings to contain '{exp}', "
                f"but got: {self._result.warnings}"
            )
        return self

    def no_warnings(self) -> Self:
        """Assert that there are no warnings.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If there are any warnings.
        """
        assert len(self._result.warnings) == 0, (
            f"Expected no warnings, but got: {self._result.warnings}"
        )
        return self

    def warning_count(self, count: int) -> Self:
        """Assert exact number of warnings.

        Args:
            count: Expected number of warnings.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If warning count doesn't match.
        """
        actual = len(self._result.warnings)
        assert actual == count, (
            f"Expected {count} warnings, but got {actual}: {self._result.warnings}"
        )
        return self

    def rule_executed(self, rule_id: str) -> Self:
        """Assert that a specific rule was executed.

        Args:
            rule_id: The ID of the rule that should have been executed.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If rule was not executed.
        """
        executed_ids = [r.rule_id for r in self._result.rule_results]
        assert rule_id in executed_ids, (
            f"Expected rule '{rule_id}' to be executed, "
            f"but executed rules were: {executed_ids}"
        )
        return self

    def rule_not_executed(self, rule_id: str) -> Self:
        """Assert that a specific rule was not executed.

        Args:
            rule_id: The ID of the rule that should not have been executed.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If rule was executed.
        """
        executed_ids = [r.rule_id for r in self._result.rule_results]
        assert rule_id not in executed_ids, (
            f"Expected rule '{rule_id}' to not be executed, "
            f"but it was. Executed rules: {executed_ids}"
        )
        return self

    def rules_executed(self, *rule_ids: str) -> Self:
        """Assert that specific rules were executed in order.

        Args:
            *rule_ids: Rule IDs in expected execution order.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If rules don't match.
        """
        executed_ids = tuple(r.rule_id for r in self._result.rule_results)
        assert executed_ids == rule_ids, (
            f"Expected rules {rule_ids} to be executed in order, "
            f"but got: {executed_ids}"
        )
        return self

    def rule_count(self, count: int) -> Self:
        """Assert exact number of rules executed.

        Args:
            count: Expected number of executed rules.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If rule count doesn't match.
        """
        actual = len(self._result.rule_results)
        assert actual == count, f"Expected {count} rules executed, but got {actual}"
        return self

    def terminated_early(self) -> Self:
        """Assert that execution terminated early due to a terminal rule.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If not terminated early.
        """
        assert self._result.terminated_early, (
            "Expected execution to terminate early, but it did not"
        )
        return self

    def not_terminated_early(self) -> Self:
        """Assert that execution did not terminate early.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If terminated early.
        """
        assert not self._result.terminated_early, (
            "Expected execution to not terminate early, but it did"
        )
        return self

    def action_succeeded(self, rule_id: str, action_index: int = 0) -> Self:
        """Assert that a specific action in a rule succeeded.

        Args:
            rule_id: The rule ID.
            action_index: Index of the action within the rule.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If action didn't succeed or doesn't exist.
        """
        for rule_result in self._result.rule_results:
            if rule_result.rule_id == rule_id:
                assert action_index < len(rule_result.action_results), (
                    f"Rule '{rule_id}' has {len(rule_result.action_results)} actions, "
                    f"but tried to access index {action_index}"
                )
                action_result = rule_result.action_results[action_index]
                assert action_result.success, (
                    f"Expected action {action_index} in rule '{rule_id}' to succeed, "
                    f"but it failed with error: {action_result.error}"
                )
                return self
        executed_ids = [r.rule_id for r in self._result.rule_results]
        msg = f"Rule '{rule_id}' not found. Executed rules: {executed_ids}"
        raise AssertionError(msg)

    def action_failed(
        self, rule_id: str, action_index: int = 0, error_contains: str | None = None
    ) -> Self:
        """Assert that a specific action in a rule failed.

        Args:
            rule_id: The rule ID.
            action_index: Index of the action within the rule.
            error_contains: If provided, assert error message contains this string.

        Returns:
            Self for chaining.

        Raises:
            AssertionError: If action didn't fail or error doesn't match.
        """
        for rule_result in self._result.rule_results:
            if rule_result.rule_id == rule_id:
                assert action_index < len(rule_result.action_results), (
                    f"Rule '{rule_id}' has {len(rule_result.action_results)} actions, "
                    f"but tried to access index {action_index}"
                )
                action_result = rule_result.action_results[action_index]
                assert not action_result.success, (
                    f"Expected action {action_index} in rule '{rule_id}' to fail, "
                    f"but it succeeded"
                )
                if error_contains is not None:
                    assert action_result.error is not None, (
                        f"Expected error to contain '{error_contains}', "
                        f"but error is None"
                    )
                    assert error_contains in action_result.error, (
                        f"Expected error to contain '{error_contains}', "
                        f"but got: '{action_result.error}'"
                    )
                return self
        executed_ids = [r.rule_id for r in self._result.rule_results]
        msg = f"Rule '{rule_id}' not found. Executed rules: {executed_ids}"
        raise AssertionError(msg)


def assert_result(result: ExecutionResult) -> ExecutionResultAssertion:
    """Create a fluent assertion wrapper for an ExecutionResult.

    Args:
        result: The ExecutionResult to assert on.

    Returns:
        ExecutionResultAssertion for fluent assertions.

    Example:
        assert_result(result).not_blocked().rule_executed("my-rule")
    """
    return ExecutionResultAssertion(result)
