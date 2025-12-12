"""Integration tests for Claude Code CLI with OAPS hooks."""

import pytest

from ._config import HookConfigBuilder
from ._test_case import ClaudeHookTestCase

pytestmark = [pytest.mark.integration, pytest.mark.claude_integration]


class TestClaudeHookIntegration:
    def test_session_start_hook_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        assertions = claude_test_case.run_prompt("What is 2+2?")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_pre_tool_use_blocking(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="block-bash",
            events={"pre_tool_use"},
            condition='tool_name == "Bash"',
            result="block",
            description="Bash blocked for testing",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Run the command: echo hello")

        assertions.assert_hook_blocked(reason_contains="Bash blocked")

    def test_hook_with_warning_result(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="warn-bash",
            events={"pre_tool_use"},
            condition='tool_name == "Bash"',
            result="warn",
            description="Bash command detected",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Run the command: ls")

        (
            assertions.assert_hook_triggered("pre_tool_use")
            .assert_hook_completed("pre_tool_use")
            .assert_no_hook_errors()
        )

    def test_multiple_hooks_execute_in_priority_order(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = (
            HookConfigBuilder()
            .add_rule(
                rule_id="low-priority",
                events={"session_start"},
                result="ok",
                priority="low",
                description="Low priority hook",
            )
            .add_rule(
                rule_id="high-priority",
                events={"session_start"},
                result="ok",
                priority="high",
                description="High priority hook",
            )
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_rules_matched(count=2, rule_ids=["high-priority", "low-priority"])
            .assert_no_hook_errors()
        )

    def test_terminal_hook_stops_processing(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = (
            HookConfigBuilder()
            .add_rule(
                rule_id="terminal-block",
                events={"pre_tool_use"},
                condition='tool_name == "Bash"',
                result="block",
                terminal=True,
                priority="critical",
                description="Terminal block",
            )
            .add_rule(
                rule_id="would-warn",
                events={"pre_tool_use"},
                condition="true",
                result="warn",
                priority="high",
                description="Should not execute",
            )
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Run: echo test")

        assertions.assert_hook_blocked(reason_contains="Terminal block")

    def test_post_tool_use_hook_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="post-tool-log",
            events={"post_tool_use"},
            result="ok",
            description="Post tool use hook",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Read the file pyproject.toml")

        assertions.assert_hook_completed("post_tool_use").assert_no_hook_errors()

    def test_user_prompt_submit_hook_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="prompt-hook",
            events={"user_prompt_submit"},
            result="ok",
            description="User prompt submit hook",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("What is the meaning of life?")

        (
            assertions.assert_hook_triggered("user_prompt_submit")
            .assert_hook_completed("user_prompt_submit")
            .assert_no_hook_errors()
        )

    def test_notification_hook_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="notification-hook",
            events={"notification"},
            result="ok",
            description="Notification hook",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Run the command: whoami")

        # Just verify no errors - notification may or may not fire
        # depending on permission mode
        assertions.assert_no_hook_errors()

    def test_session_end_hook_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="session-end-hook",
            events={"session_end"},
            result="ok",
            description="Session end hook",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Say hello")

        (
            assertions.assert_hook_triggered("session_end")
            .assert_hook_completed("session_end")
            .assert_no_hook_errors()
        )

    def test_all_event_hook_fires_for_multiple_events(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="catch-all",
            events={"all"},
            result="ok",
            description="Catch all events",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello world")

        assertions.assert_hook_completed().assert_no_hook_errors()

    def test_condition_with_tool_input(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="block-rm",
            events={"pre_tool_use"},
            condition='tool_name == "Bash" and tool_input["command"] =~ "rm"',
            result="block",
            description="rm command blocked",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Run: rm -rf /tmp/test")

        assertions.assert_hook_blocked(reason_contains="rm command blocked")

    def test_disabled_rule_does_not_fire(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="disabled-block",
            events={"session_start"},
            condition="true",
            result="block",
            priority="critical",
            enabled=False,
            description="Should not block",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_completed("session_start")
            .assert_rules_matched(count=0, rule_ids=[])
            .assert_no_hook_errors()
        )


@pytest.mark.integration
class TestClaudeHookBlocking:
    def test_block_returns_exit_code_2(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="always-block",
            events={"session_start"},
            condition="true",
            result="block",
            description="Always block",
        )
        claude_test_case.configure_hooks(builder)

        result = claude_test_case.run_prompt_raw("Hello")

        assert result.return_code == 2

    def test_block_reason_in_stderr(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="block-with-reason",
            events={"session_start"},
            condition="true",
            result="block",
            description="Blocked because reasons",
        )
        claude_test_case.configure_hooks(builder)

        result = claude_test_case.run_prompt_raw("Hello")

        assert result.return_code == 2, (
            f"Expected exit code 2 but got {result.return_code}"
        )
        assert "Blocked because reasons" in result.stderr, (
            f"Expected block reason in stderr. Actual stderr: {result.stderr}"
        )


@pytest.mark.integration
class TestClaudeHookLogging:
    def test_hook_log_file_created(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        _ = claude_test_case.run_prompt("Hello")

        assert claude_test_case.env.hooks_log_path.exists()

    def test_hook_log_contains_session_id(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        from ._log_parser import HookLogParser

        _ = claude_test_case.run_prompt("Hello")

        parser = HookLogParser(claude_test_case.env.hooks_log_path)
        entries = parser.parse()

        session_ids = [e.session_id for e in entries if e.session_id]
        assert session_ids, "Expected log entries with session_id"

    def test_hook_log_contains_timestamps(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        from ._log_parser import HookLogParser

        _ = claude_test_case.run_prompt("Hello")

        parser = HookLogParser(claude_test_case.env.hooks_log_path)
        entries = parser.parse()

        timestamps = [e.timestamp for e in entries if e.timestamp]
        assert timestamps, "Expected log entries with timestamps"


@pytest.mark.integration
class TestHookEventSmoke:
    def test_session_start_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-session-start",
            events={"session_start"},
            result="ok",
            description="Smoke test for session_start event",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    @pytest.mark.skip(reason="session_end does not fire in print mode (-p)")
    def test_session_end_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-session-end",
            events={"session_end"},
            result="ok",
            description="Smoke test for session_end event",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_end")
            .assert_hook_completed("session_end")
            .assert_no_hook_errors()
        )

    def test_pre_tool_use_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-pre-tool-use",
            events={"pre_tool_use"},
            result="ok",
            description="Smoke test for pre_tool_use event",
        )
        claude_test_case.configure_hooks(builder)

        # Create a file to read in the test project
        test_file = claude_test_case.env.project_root / "test.txt"
        test_file.write_text("test content")

        # Use explicit instruction to force tool use
        prompt = f"Use the Read tool to read {test_file}"
        assertions = claude_test_case.run_prompt(prompt)

        (
            assertions.assert_hook_triggered("pre_tool_use")
            .assert_hook_completed("pre_tool_use")
            .assert_no_hook_errors()
        )

    def test_post_tool_use_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-post-tool-use",
            events={"post_tool_use"},
            result="ok",
            description="Smoke test for post_tool_use event",
        )
        claude_test_case.configure_hooks(builder)

        # Create a file to read in the test project
        test_file = claude_test_case.env.project_root / "test.txt"
        test_file.write_text("test content")

        # Use explicit instruction to force tool use
        prompt = f"Use the Read tool to read {test_file}"
        assertions = claude_test_case.run_prompt(prompt)

        (
            assertions.assert_hook_triggered("post_tool_use")
            .assert_hook_completed("post_tool_use")
            .assert_no_hook_errors()
        )

    def test_user_prompt_submit_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-user-prompt-submit",
            events={"user_prompt_submit"},
            result="ok",
            description="Smoke test for user_prompt_submit event",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello world")

        (
            assertions.assert_hook_triggered("user_prompt_submit")
            .assert_hook_completed("user_prompt_submit")
            .assert_no_hook_errors()
        )

    @pytest.mark.skip(reason="permission_request does not fire in print mode (-p)")
    def test_permission_request_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-permission-request",
            events={"permission_request"},
            result="ok",
            description="Smoke test for permission_request event",
        )
        claude_test_case.configure_hooks(builder)

        # Trigger a tool that requires permission
        assertions = claude_test_case.run_prompt(
            "Use the Bash tool to run: echo hello. You MUST use the Bash tool."
        )

        (
            assertions.assert_hook_triggered("permission_request")
            .assert_hook_completed("permission_request")
            .assert_no_hook_errors()
        )

    @pytest.mark.skip(reason="notification does not fire in print mode (-p)")
    def test_notification_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-notification",
            events={"notification"},
            result="ok",
            description="Smoke test for notification event",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt(
            "Use the Bash tool to run: whoami. You MUST use the Bash tool."
        )

        (
            assertions.assert_hook_triggered("notification")
            .assert_hook_completed("notification")
            .assert_no_hook_errors()
        )

    def test_stop_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-stop",
            events={"stop"},
            result="ok",
            description="Smoke test for stop event",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Say hello")

        (
            assertions.assert_hook_triggered("stop")
            .assert_hook_completed("stop")
            .assert_no_hook_errors()
        )

    def test_subagent_stop_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-subagent-stop",
            events={"subagent_stop"},
            result="ok",
            description="Smoke test for subagent_stop event",
        )
        claude_test_case.configure_hooks(builder)

        # Use Task tool to spawn a subagent
        assertions = claude_test_case.run_prompt(
            "Use the Task tool with subagent_type='Explore' to answer: What is 2+2?"
        )

        (
            assertions.assert_hook_triggered("subagent_stop")
            .assert_hook_completed("subagent_stop")
            .assert_no_hook_errors()
        )

    @pytest.mark.skip(reason="pre_compact only fires during context compaction")
    def test_pre_compact_event_fires(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-pre-compact",
            events={"pre_compact"},
            result="ok",
            description="Smoke test for pre_compact event",
        )
        claude_test_case.configure_hooks(builder)

        # Would need a very long conversation to trigger context compaction
        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("pre_compact")
            .assert_hook_completed("pre_compact")
            .assert_no_hook_errors()
        )


@pytest.mark.integration
class TestHookActionSmoke:
    def test_log_action_with_info_level(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-log-action",
            events={"session_start"},
            actions=[{"type": "log", "level": "info", "message": "Smoke test log"}],
            result="ok",
            description="Smoke test for log action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_deny_action_with_message(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-deny-action",
            events={"session_start"},
            actions=[{"type": "deny", "message": "Denied by smoke test"}],
            result="block",
            description="Smoke test for deny action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        # Verify the hook was triggered and completed without errors
        # Note: Blocking behavior depends on hook system integration
        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_allow_action(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-allow-action",
            events={"session_start"},
            actions=[{"type": "allow"}],
            result="ok",
            description="Smoke test for allow action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_warn_action_with_message(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-warn-action",
            events={"session_start"},
            actions=[{"type": "warn", "message": "Warning from smoke test"}],
            result="warn",
            description="Smoke test for warn action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_suggest_action_with_content(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-suggest-action",
            events={"session_start"},
            actions=[{"type": "suggest", "content": "Suggested from smoke test"}],
            result="ok",
            description="Smoke test for suggest action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_inject_action_with_content(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-inject-action",
            events={"session_start"},
            actions=[{"type": "inject", "content": "Injected context from smoke test"}],
            result="ok",
            description="Smoke test for inject action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_rules_matched(count=1, rule_ids=["smoke-inject-action"])
            .assert_context_injected("Injected context from smoke test")
            .assert_no_hook_errors()
        )

    def test_shell_action_with_echo_command(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-shell-action",
            events={"session_start"},
            actions=[{"type": "shell", "command": "echo 'smoke test shell action'"}],
            result="ok",
            description="Smoke test for shell action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )

    def test_python_action_with_entrypoint(
        self,
        claude_test_case: ClaudeHookTestCase,
    ) -> None:
        # Create a simple Python script for the test
        scripts_dir = claude_test_case.env.oaps_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        script_path = scripts_dir / "smoke_test.py"
        script_path.write_text("print('smoke test python action')\n")

        builder = HookConfigBuilder().add_rule(
            rule_id="smoke-python-action",
            events={"session_start"},
            actions=[{"type": "python", "entrypoint": ".oaps/scripts/smoke_test.py"}],
            result="ok",
            description="Smoke test for python action",
        )
        claude_test_case.configure_hooks(builder)

        assertions = claude_test_case.run_prompt("Hello")

        (
            assertions.assert_hook_triggered("session_start")
            .assert_hook_completed("session_start")
            .assert_no_hook_errors()
        )
