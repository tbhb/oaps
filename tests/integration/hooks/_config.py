"""Hook configuration builder for integration tests.

This module provides the HookConfigBuilder class for constructing
hook rule configurations programmatically in TOML format.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Self


@dataclass(slots=True)
class HookConfigBuilder:
    """Builder for hook rule configurations.

    This class provides a fluent interface for constructing hook rules
    that can be written to oaps.toml files for integration testing.

    Example:
        builder = HookConfigBuilder()
        builder.add_rule(
            rule_id="block-bash",
            events={"pre_tool_use"},
            condition='tool_name == "Bash"',
            result="block",
            description="Block all Bash commands",
        )
        builder.write_to(oaps_toml_path)
    """

    _rules: list[dict[str, object]] = field(default_factory=list)

    def add_rule(
        self,
        rule_id: str,
        events: set[str],
        *,
        condition: str = "true",
        result: Literal["block", "ok", "warn"] = "ok",
        priority: str = "medium",
        terminal: bool = False,
        description: str = "",
        actions: list[dict[str, object]] | None = None,
        enabled: bool = True,
    ) -> Self:
        """Add a hook rule to the configuration.

        Args:
            rule_id: Unique identifier for the rule.
            events: Set of event types this rule applies to.
            condition: Rule condition expression (default: "true").
            result: Rule result type ("block", "ok", "warn").
            priority: Rule priority ("critical", "high", "medium", "low").
            terminal: Whether to stop processing after this rule.
            description: Human-readable description of the rule.
            actions: List of action configurations.
            enabled: Whether the rule is enabled (default: True).

        Returns:
            Self for method chaining.
        """
        rule: dict[str, object] = {
            "id": rule_id,
            "events": sorted(events),
            "condition": condition,
            "result": result,
            "priority": priority,
            "terminal": terminal,
            "enabled": enabled,
        }

        if description:
            rule["description"] = description

        if actions:
            rule["actions"] = actions

        self._rules.append(rule)
        return self

    def build_toml(self) -> str:
        """Build the TOML configuration string.

        Returns:
            TOML-formatted string with all configured rules.
        """
        import tomli_w

        config: dict[str, object] = {}

        if self._rules:
            # Build hooks.rules section
            hooks_config: dict[str, list[dict[str, object]]] = {"rules": self._rules}
            config["hooks"] = hooks_config

        return tomli_w.dumps(config)

    def write_to(self, oaps_toml_path: Path) -> None:
        """Write the configuration to a TOML file.

        Args:
            oaps_toml_path: Path to the oaps.toml file.
        """
        toml_content = self.build_toml()
        oaps_toml_path.write_text(toml_content)

    def clear(self) -> Self:
        """Clear all configured rules.

        Returns:
            Self for method chaining.
        """
        self._rules.clear()
        return self
