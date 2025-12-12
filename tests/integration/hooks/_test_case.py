"""Test case coordinator for Claude CLI hook integration tests.

This module provides the ClaudeHookTestCase class that coordinates
environment setup, hook configuration, command execution, and assertions.
"""

from dataclasses import dataclass

from ._assertions import HookAssertions
from ._config import HookConfigBuilder
from ._environment import ClaudeTestEnvironment
from ._runner import ClaudeExecutionResult, ClaudeRunner


@dataclass(frozen=True, slots=True)
class ClaudeHookTestCase:
    """Coordinated test case for Claude CLI hook integration tests.

    This class provides a high-level interface for integration tests,
    combining environment management, hook configuration, CLI execution,
    and assertion helpers into a single cohesive API.

    Attributes:
        env: The test environment configuration.
        runner: The Claude CLI runner.
    """

    env: ClaudeTestEnvironment
    runner: ClaudeRunner

    def configure_hooks(self, builder: HookConfigBuilder) -> None:
        """Write hook config to .oaps/oaps.toml.

        Args:
            builder: Configured HookConfigBuilder with rules.
        """
        builder.write_to(self.env.get_oaps_toml_path())

    def run_prompt(self, prompt: str) -> HookAssertions:
        """Execute prompt and return assertions helper.

        Args:
            prompt: The prompt to send to Claude.

        Returns:
            HookAssertions instance for fluent assertion chaining.
        """
        result = self.runner.run_prompt(prompt)
        return HookAssertions(env=self.env, result=result)

    def run_prompt_raw(self, prompt: str) -> ClaudeExecutionResult:
        """Execute prompt and return raw result.

        Useful when you need direct access to the execution result
        without the assertion wrapper.

        Args:
            prompt: The prompt to send to Claude.

        Returns:
            ClaudeExecutionResult with return code, output, and timing.
        """
        return self.runner.run_prompt(prompt)

    def run_command(
        self,
        args: list[str],
        *,
        stdin: str | None = None,
    ) -> HookAssertions:
        """Execute raw Claude CLI command and return assertions helper.

        Args:
            args: Command arguments to pass to claude.
            stdin: Optional input to send via stdin.

        Returns:
            HookAssertions instance for fluent assertion chaining.
        """
        result = self.runner.run_command(args, stdin=stdin)
        return HookAssertions(env=self.env, result=result)

    def get_assertions(
        self,
        result: ClaudeExecutionResult,
    ) -> HookAssertions:
        """Create assertions helper from an existing result.

        Args:
            result: A previously obtained execution result.

        Returns:
            HookAssertions instance for fluent assertion chaining.
        """
        return HookAssertions(env=self.env, result=result)
