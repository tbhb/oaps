"""Assertion helpers for hook integration tests.

This module provides the HookAssertions class for fluent assertion
chaining on Claude CLI execution results and hook log output.
"""

from dataclasses import dataclass
from typing import Literal, Self

from ._environment import ClaudeTestEnvironment
from ._log_parser import HookLogParser
from ._runner import ClaudeExecutionResult


@dataclass(frozen=True, slots=True)
class HookAssertions:
    """Assertion helpers for hook integration tests.

    This class provides fluent assertion methods that can be chained
    together to verify hook behavior in integration tests.

    Attributes:
        env: The test environment configuration.
        result: The Claude CLI execution result.
    """

    env: ClaudeTestEnvironment
    result: ClaudeExecutionResult

    def _get_parser(self) -> HookLogParser:
        """Get a log parser for the hooks log file."""
        return HookLogParser(self.env.hooks_log_path)

    def assert_hook_triggered(self, event_type: str) -> Self:
        """Verify hook event was triggered (hook_started in logs).

        Args:
            event_type: The hook event type (e.g., "session_start").

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If hook was not triggered.
        """
        parser = self._get_parser()
        started_entries = parser.filter_by_event("hook_started")
        matching = [e for e in started_entries if e.hook_event == event_type]

        assert matching, (
            f"Expected hook_started event for '{event_type}' not found in logs. "
            f"Found events: {[e.hook_event for e in started_entries]}"
        )

        return self

    def assert_hook_blocked(
        self,
        reason_contains: str | None = None,
    ) -> Self:
        """Verify hook blocked operation (hook_blocked in logs).

        Args:
            reason_contains: Optional substring that must appear in block reason.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If hook did not block or reason doesn't match.
        """
        parser = self._get_parser()
        blocked_entries = parser.filter_by_event("hook_blocked")

        assert blocked_entries, (
            "Expected hook_blocked event not found in logs. "
            f"Events found: {[e.event for e in parser.parse()]}"
        )

        if reason_contains is not None:
            reasons = [str(e.data.get("reason", "")) for e in blocked_entries]
            matching = [r for r in reasons if reason_contains in r]
            assert matching, (
                f"Expected block reason containing '{reason_contains}' not found. "
                f"Actual reasons: {reasons}"
            )

        # Also verify exit code 2 (blocking exit code)
        assert self.result.return_code == 2, (
            f"Expected exit code 2 (block) but got {self.result.return_code}"
        )

        return self

    def assert_hook_completed(
        self,
        event_type: str | None = None,
    ) -> Self:
        """Verify hook completed successfully.

        Args:
            event_type: Optional hook event type to filter by.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If hook did not complete.
        """
        parser = self._get_parser()
        completed_entries = parser.filter_by_event("hook_completed")

        if event_type is not None:
            matching = [e for e in completed_entries if e.hook_event == event_type]
            assert matching, (
                f"Expected hook_completed event for '{event_type}' not found. "
                f"Completed events: {[e.hook_event for e in completed_entries]}"
            )
        else:
            assert completed_entries, (
                "Expected hook_completed event not found in logs. "
                f"Events found: {[e.event for e in parser.parse()]}"
            )

        return self

    def assert_no_hook_errors(self) -> Self:
        """Verify no hook_failed entries in logs.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If any hook_failed events were logged.
        """
        parser = self._get_parser()
        failed_entries = parser.filter_by_event("hook_failed")

        assert not failed_entries, (
            f"Expected no hook_failed events but found {len(failed_entries)}: "
            f"{[e.data.get('error', 'unknown') for e in failed_entries]}"
        )

        return self

    def assert_exit_code(self, expected: int) -> Self:
        """Verify the CLI exit code.

        Args:
            expected: Expected exit code.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If exit code doesn't match.
        """
        assert self.result.return_code == expected, (
            f"Expected exit code {expected} but got {self.result.return_code}. "
            f"stderr: {self.result.stderr}"
        )

        return self

    def assert_stdout_contains(self, substring: str) -> Self:
        """Verify stdout contains a substring.

        Args:
            substring: Expected substring in stdout.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If substring not found in stdout.
        """
        assert substring in self.result.stdout, (
            f"Expected stdout to contain '{substring}'. "
            f"Actual stdout: {self.result.stdout[:500]}"
        )

        return self

    def assert_stderr_contains(self, substring: str) -> Self:
        """Verify stderr contains a substring.

        Args:
            substring: Expected substring in stderr.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If substring not found in stderr.
        """
        assert substring in self.result.stderr, (
            f"Expected stderr to contain '{substring}'. "
            f"Actual stderr: {self.result.stderr[:500]}"
        )

        return self

    def assert_log_contains(
        self,
        event: str,
        *,
        key: str | None = None,
        value: object = None,
    ) -> Self:
        """Verify log contains an entry with specific attributes.

        Args:
            event: Event name to look for.
            key: Optional key in log data to check.
            value: Expected value for the key.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If matching log entry not found.
        """
        parser = self._get_parser()
        entries = parser.filter_by_event(event)

        assert entries, (
            f"Expected log event '{event}' not found. "
            f"Events found: {[e.event for e in parser.parse()]}"
        )

        if key is not None:
            matching = [e for e in entries if e.data.get(key) == value]
            assert matching, (
                f"Expected log event '{event}' with {key}={value} not found. "
                f"Actual values: {[e.data.get(key) for e in entries]}"
            )

        return self

    def _get_nested_value(self, obj: dict[str, object], path: str) -> object:
        """Get a value from a nested dictionary using dot notation.

        Args:
            obj: The dictionary to traverse.
            path: Dot-separated path to the value (e.g., "a.b.c").

        Returns:
            The value at the path, or None if not found.
        """
        current: object = obj
        for key in path.split("."):
            if not isinstance(current, dict):
                return None
            value = current.get(key)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            if value is None:
                return None
            current = value  # pyright: ignore[reportUnknownVariableType]
        return current  # pyright: ignore[reportUnknownVariableType]

    def assert_rules_matched(
        self,
        *,
        count: int | None = None,
        rule_ids: list[str] | None = None,
    ) -> Self:
        """Verify rules were matched during hook execution.

        Args:
            count: Expected number of matched rules (optional).
            rule_ids: Expected list of matched rule IDs (optional).

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If rules_matched event not found or values don't match.
        """
        parser = self._get_parser()
        matched_entries = parser.filter_by_event("rules_matched")

        assert matched_entries, (
            "Expected rules_matched event not found in logs. "
            f"Events found: {[e.event for e in parser.parse()]}"
        )

        entry = matched_entries[-1]  # Use the most recent entry

        if count is not None:
            actual_count = entry.data.get("count")
            assert actual_count == count, (
                f"Expected {count} rules matched but got {actual_count}"
            )

        if rule_ids is not None:
            actual_rule_ids = entry.data.get("rule_ids")
            assert actual_rule_ids == rule_ids, (
                f"Expected rule_ids {rule_ids} but got {actual_rule_ids}"
            )

        return self

    def assert_hook_output_contains(
        self,
        key: str,
        value: object = None,
    ) -> Self:
        """Verify hook output JSON contains a key with optional value check.

        Args:
            key: Key to look for (supports dot notation for nested keys).
            value: Expected value (optional, if None only checks key exists).

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If key not found or value doesn't match.
        """
        assert self.result.json_output is not None, (
            f"Expected JSON output but got None. stdout: {self.result.stdout[:500]}"
        )

        actual_value = self._get_nested_value(self.result.json_output, key)

        if value is None:
            assert actual_value is not None, (
                f"Expected key '{key}' in JSON output but not found. "
                f"Available keys: {list(self.result.json_output.keys())}"
            )
        else:
            assert actual_value == value, (
                f"Expected {key}={value!r} but got {actual_value!r}"
            )

        return self

    def assert_context_injected(self, content: str | None = None) -> Self:
        """Verify hookSpecificOutput.additionalContext exists in output.

        Args:
            content: Optional substring that must appear in additionalContext.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If additionalContext not found or content not present.
        """
        assert self.result.json_output is not None, (
            f"Expected JSON output but got None. stdout: {self.result.stdout[:500]}"
        )

        additional_context = self._get_nested_value(
            self.result.json_output, "hookSpecificOutput.additionalContext"
        )

        assert additional_context is not None, (
            "Expected hookSpecificOutput.additionalContext in JSON output "
            f"but not found. JSON output: {self.result.json_output}"
        )

        if content is not None:
            assert isinstance(additional_context, str), (
                "Expected additionalContext to be a string "
                f"but got {type(additional_context).__name__}"
            )
            assert content in additional_context, (
                f"Expected additionalContext to contain '{content}'. "
                f"Actual: {additional_context[:500]}"
            )

        return self

    def assert_permission_decision(
        self,
        decision: Literal["deny", "allow", "ask"],
    ) -> Self:
        """Verify hookSpecificOutput.permissionDecision matches expected value.

        Args:
            decision: Expected permission decision ("deny", "allow", or "ask").

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If permissionDecision not found or doesn't match.
        """
        assert self.result.json_output is not None, (
            f"Expected JSON output but got None. stdout: {self.result.stdout[:500]}"
        )

        actual_decision = self._get_nested_value(
            self.result.json_output, "hookSpecificOutput.permissionDecision"
        )

        assert actual_decision is not None, (
            "Expected hookSpecificOutput.permissionDecision in JSON output "
            f"but not found. JSON output: {self.result.json_output}"
        )

        assert actual_decision == decision, (
            f"Expected permissionDecision '{decision}' but got '{actual_decision}'"
        )

        return self

    def assert_permission_reason_contains(self, substring: str) -> Self:
        """Verify hookSpecificOutput.permissionDecisionReason contains substring.

        Args:
            substring: Expected substring in permissionDecisionReason.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If permissionDecisionReason not found or missing substring.
        """
        assert self.result.json_output is not None, (
            f"Expected JSON output but got None. stdout: {self.result.stdout[:500]}"
        )

        reason = self._get_nested_value(
            self.result.json_output, "hookSpecificOutput.permissionDecisionReason"
        )

        assert reason is not None, (
            "Expected hookSpecificOutput.permissionDecisionReason in JSON output "
            f"but not found. JSON output: {self.result.json_output}"
        )

        assert isinstance(reason, str), (
            "Expected permissionDecisionReason to be a string "
            f"but got {type(reason).__name__}"
        )

        assert substring in reason, (
            f"Expected permissionDecisionReason to contain '{substring}'. "
            f"Actual: {reason}"
        )

        return self
