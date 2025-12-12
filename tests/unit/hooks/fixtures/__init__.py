"""Hook testing fixtures.

This package provides testing utilities for hook rules, conditions, and actions.
Import from here to access all fixtures and helpers.
"""

from .assertions import ExecutionResultAssertion, assert_result
from .contexts import HookContextFactory, create_git_context, create_mock_logger
from .inputs import (
    InputBuilder,
    NotificationInputBuilder,
    PermissionRequestInputBuilder,
    PostToolUseInputBuilder,
    PreCompactInputBuilder,
    PreToolUseInputBuilder,
    SessionEndInputBuilder,
    SessionStartInputBuilder,
    StopInputBuilder,
    SubagentStopInputBuilder,
    UserPromptSubmitInputBuilder,
    create_input,
)
from .rules import EventType, RuleBuilder, action, rule
from .scripts import ScriptRunner, create_python_script, create_shell_script

__all__ = [
    # Rules
    "EventType",
    # Assertions
    "ExecutionResultAssertion",
    # Contexts
    "HookContextFactory",
    # Inputs
    "InputBuilder",
    "NotificationInputBuilder",
    "PermissionRequestInputBuilder",
    "PostToolUseInputBuilder",
    "PreCompactInputBuilder",
    "PreToolUseInputBuilder",
    "RuleBuilder",
    # Scripts
    "ScriptRunner",
    "SessionEndInputBuilder",
    "SessionStartInputBuilder",
    "StopInputBuilder",
    "SubagentStopInputBuilder",
    "UserPromptSubmitInputBuilder",
    "action",
    "assert_result",
    "create_git_context",
    "create_input",
    "create_mock_logger",
    "create_python_script",
    "create_shell_script",
    "rule",
]
