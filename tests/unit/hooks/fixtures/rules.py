"""RuleBuilder with fluent API for hook testing.

Provides a builder class for creating HookRuleConfiguration and MatchedRule
instances with sensible defaults and convenience methods.
"""

from typing import TYPE_CHECKING, Literal, Self

from oaps.config import HookRuleActionConfiguration, HookRuleConfiguration, RulePriority
from oaps.hooks import MatchedRule

if TYPE_CHECKING:
    pass


# Type alias for event types
type EventType = Literal[
    "all",
    "pre_tool_use",
    "post_tool_use",
    "permission_request",
    "user_prompt_submit",
    "notification",
    "session_start",
    "session_end",
    "stop",
    "subagent_stop",
    "pre_compact",
]


class RuleBuilder:
    """Fluent builder for HookRuleConfiguration with convenience methods."""

    def __init__(self, rule_id: str) -> None:
        self._id: str = rule_id
        self._events: set[EventType] = {"all"}
        self._condition: str = ""
        self._priority: RulePriority = RulePriority.MEDIUM
        self._enabled: bool = True
        self._result: Literal["block", "ok", "warn"] = "ok"
        self._terminal: bool = False
        self._description: str | None = None
        self._actions: list[HookRuleActionConfiguration] = []

    # Event methods

    def on_events(self, *events: EventType) -> Self:
        """Set the events this rule applies to.

        Args:
            *events: One or more event type names.

        Returns:
            Self for chaining.
        """
        self._events = set(events)
        return self

    def on_all_events(self) -> Self:
        """Set the rule to apply to all events.

        Returns:
            Self for chaining.
        """
        self._events = {"all"}
        return self

    def on_pre_tool_use(self) -> Self:
        """Set the rule to apply to pre_tool_use events only.

        Returns:
            Self for chaining.
        """
        self._events = {"pre_tool_use"}
        return self

    def on_post_tool_use(self) -> Self:
        """Set the rule to apply to post_tool_use events only.

        Returns:
            Self for chaining.
        """
        self._events = {"post_tool_use"}
        return self

    def on_user_prompt_submit(self) -> Self:
        """Set the rule to apply to user_prompt_submit events only.

        Returns:
            Self for chaining.
        """
        self._events = {"user_prompt_submit"}
        return self

    def on_permission_request(self) -> Self:
        """Set the rule to apply to permission_request events only.

        Returns:
            Self for chaining.
        """
        self._events = {"permission_request"}
        return self

    # Condition methods

    def when(self, condition: str) -> Self:
        """Set the condition expression.

        Args:
            condition: The condition expression string.

        Returns:
            Self for chaining.
        """
        self._condition = condition
        return self

    def always(self) -> Self:
        """Set the rule to always match (empty condition).

        Returns:
            Self for chaining.
        """
        self._condition = ""
        return self

    # Priority methods

    def with_priority(self, priority: RulePriority) -> Self:
        """Set the rule priority.

        Args:
            priority: The priority level.

        Returns:
            Self for chaining.
        """
        self._priority = priority
        return self

    def critical(self) -> Self:
        """Set critical priority.

        Returns:
            Self for chaining.
        """
        self._priority = RulePriority.CRITICAL
        return self

    def high(self) -> Self:
        """Set high priority.

        Returns:
            Self for chaining.
        """
        self._priority = RulePriority.HIGH
        return self

    def medium(self) -> Self:
        """Set medium priority (default).

        Returns:
            Self for chaining.
        """
        self._priority = RulePriority.MEDIUM
        return self

    def low(self) -> Self:
        """Set low priority.

        Returns:
            Self for chaining.
        """
        self._priority = RulePriority.LOW
        return self

    # Result type methods

    def blocks(self) -> Self:
        """Set result type to block.

        Returns:
            Self for chaining.
        """
        self._result = "block"
        return self

    def allows(self) -> Self:
        """Set result type to ok (allow).

        Returns:
            Self for chaining.
        """
        self._result = "ok"
        return self

    def warns(self) -> Self:
        """Set result type to warn.

        Returns:
            Self for chaining.
        """
        self._result = "warn"
        return self

    # Terminal method

    def terminal(self) -> Self:
        """Mark the rule as terminal (stops further rule processing).

        Returns:
            Self for chaining.
        """
        self._terminal = True
        return self

    def non_terminal(self) -> Self:
        """Mark the rule as non-terminal (default).

        Returns:
            Self for chaining.
        """
        self._terminal = False
        return self

    # Description method

    def with_description(self, description: str) -> Self:
        """Set the rule description.

        Args:
            description: The description text.

        Returns:
            Self for chaining.
        """
        self._description = description
        return self

    # Enabled/disabled

    def enabled(self) -> Self:
        """Enable the rule (default).

        Returns:
            Self for chaining.
        """
        self._enabled = True
        return self

    def disabled(self) -> Self:
        """Disable the rule.

        Returns:
            Self for chaining.
        """
        self._enabled = False
        return self

    # Action methods

    def with_action(self, action: HookRuleActionConfiguration) -> Self:
        """Add an action to the rule.

        Args:
            action: The action configuration to add.

        Returns:
            Self for chaining.
        """
        self._actions.append(action)
        return self

    def with_actions(self, *actions: HookRuleActionConfiguration) -> Self:
        """Add multiple actions to the rule.

        Args:
            *actions: Action configurations to add.

        Returns:
            Self for chaining.
        """
        self._actions.extend(actions)
        return self

    # Convenience action methods

    def log(self, level: Literal["debug", "info", "warning", "error"] = "info") -> Self:
        """Add a log action.

        Args:
            level: The log level.

        Returns:
            Self for chaining.
        """
        self._actions.append(HookRuleActionConfiguration(type="log", level=level))
        return self

    def deny(self, message: str | None = None, *, interrupt: bool = True) -> Self:
        """Add a deny action.

        Args:
            message: Optional message to display.
            interrupt: Whether to interrupt the agent loop.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(
                type="deny", message=message, interrupt=interrupt
            )
        )
        return self

    def allow(self, message: str | None = None) -> Self:
        """Add an allow action.

        Args:
            message: Optional message to display.

        Returns:
            Self for chaining.
        """
        self._actions.append(HookRuleActionConfiguration(type="allow", message=message))
        return self

    def warn(self, message: str | None = None) -> Self:
        """Add a warn action.

        Args:
            message: Optional message to display.

        Returns:
            Self for chaining.
        """
        self._actions.append(HookRuleActionConfiguration(type="warn", message=message))
        return self

    def inject(self, content: str) -> Self:
        """Add an inject action.

        Args:
            content: Content to inject.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(type="inject", content=content)
        )
        return self

    def suggest(self, message: str) -> Self:
        """Add a suggest action.

        Args:
            message: Suggestion message.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(type="suggest", message=message)
        )
        return self

    def shell(
        self,
        command: str | None = None,
        script: str | None = None,
        timeout_ms: int | None = None,
    ) -> Self:
        """Add a shell action.

        Args:
            command: Command to execute.
            script: Script content to execute.
            timeout_ms: Timeout in milliseconds.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(
                type="shell",
                command=command,
                script=script,
                timeout_ms=timeout_ms,
            )
        )
        return self

    def python(self, entrypoint: str, timeout_ms: int | None = None) -> Self:
        """Add a python action.

        Args:
            entrypoint: Python module:function entrypoint.
            timeout_ms: Timeout in milliseconds.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(
                type="python",
                entrypoint=entrypoint,
                timeout_ms=timeout_ms,
            )
        )
        return self

    def modify(
        self,
        field: str,
        operation: Literal["set", "append", "prepend", "replace"],
        value: str,
        pattern: str | None = None,
    ) -> Self:
        """Add a modify action.

        Args:
            field: Target field path.
            operation: Operation to perform.
            value: New value or content.
            pattern: Regex pattern for replace operation.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(
                type="modify",
                field=field,
                operation=operation,
                value=value,
                pattern=pattern,
            )
        )
        return self

    def transform(self, entrypoint: str) -> Self:
        """Add a transform action.

        Args:
            entrypoint: Python module:function entrypoint.

        Returns:
            Self for chaining.
        """
        self._actions.append(
            HookRuleActionConfiguration(type="transform", entrypoint=entrypoint)
        )
        return self

    # Build methods

    def build(self) -> HookRuleConfiguration:
        """Build the HookRuleConfiguration.

        Returns:
            The configured HookRuleConfiguration.
        """
        return HookRuleConfiguration(
            id=self._id,
            events=self._events,
            condition=self._condition,
            priority=self._priority,
            enabled=self._enabled,
            result=self._result,
            terminal=self._terminal,
            description=self._description,
            actions=self._actions,
        )

    def matched(self, match_order: int = 0) -> MatchedRule:
        """Build and wrap in a MatchedRule.

        Args:
            match_order: Position in the matched sequence.

        Returns:
            A MatchedRule wrapping the built configuration.
        """
        return MatchedRule(rule=self.build(), match_order=match_order)


def rule(rule_id: str) -> RuleBuilder:
    """Create a new RuleBuilder with the given ID.

    Args:
        rule_id: The unique rule identifier.

    Returns:
        A new RuleBuilder instance.
    """
    return RuleBuilder(rule_id)


def action(
    action_type: Literal[
        "log",
        "python",
        "shell",
        "deny",
        "allow",
        "warn",
        "suggest",
        "inject",
        "modify",
        "transform",
    ],
    **kwargs: object,
) -> HookRuleActionConfiguration:
    """Create a HookRuleActionConfiguration with the given type and options.

    Args:
        action_type: The action type.
        **kwargs: Additional action configuration fields.

    Returns:
        A HookRuleActionConfiguration instance.
    """
    return HookRuleActionConfiguration(type=action_type, **kwargs)  # pyright: ignore[reportArgumentType]
