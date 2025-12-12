# pyright: reportMissingParameterType=false, reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
"""Tests for built-in hook rules in src/oaps/hooks/builtin/.

These tests verify that the skill activation rules detect appropriate prompts
and file operations, suggesting relevant skills without blocking.
"""

from pathlib import Path

import pytest

from oaps.config import HookRuleConfiguration
from oaps.config._hooks_loader import load_drop_in_rules
from oaps.hooks import execute_rules, match_rules
from oaps.utils._logging import create_hooks_logger
from oaps.utils._paths import get_package_dir

from .fixtures import (
    HookContextFactory,
    PreToolUseInputBuilder,
    assert_result,
)


@pytest.fixture
def builtin_rules() -> list[HookRuleConfiguration]:
    """Load all built-in hook rules from the package."""
    builtin_dir = get_package_dir() / "hooks" / "builtin"
    logger = create_hooks_logger()
    return load_drop_in_rules(builtin_dir, logger)


@pytest.fixture
def ctx_factory(tmp_path: Path) -> HookContextFactory:
    return HookContextFactory(tmp_path)


def get_rule_by_id(
    rules: list[HookRuleConfiguration], rule_id: str
) -> HookRuleConfiguration | None:
    """Find a rule by its ID."""
    for rule in rules:
        if rule.id == rule_id:
            return rule
    return None


class TestSkillDeveloperRule:
    def test_matches_skill_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("How do I create a skill?")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_matches_skills_plural(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Tell me about skills")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_matches_create_skill(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a new skill for testing")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_matches_write_skill(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("write a skill that helps with debugging")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_matches_build_skill(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Build a skill for code review")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_matches_develop_skill(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("develop a skill")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("SKILL development")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" in rule_ids

    def test_does_not_match_unrelated_prompt(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in main.py")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "skill-developer" not in rule_ids

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a skill")
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        # Rule should have result="ok" and suggest action
        rule = get_rule_by_id(builtin_rules, "skill-developer")
        assert rule is not None
        assert rule.result == "ok"


class TestAgentDeveloperRule:
    def test_matches_agent_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("How do I create an agent?")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_matches_agents_plural(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Tell me about agents")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_matches_subagent(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("How do subagents work?")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_matches_create_agent(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a new agent")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_matches_write_agent(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("write an agent for code review")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_matches_build_agent(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Build an agent")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("AGENT development")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" in rule_ids

    def test_does_not_match_unrelated_prompt(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in main.py")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "agent-developer" not in rule_ids

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create an agent")
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "agent-developer")
        assert rule is not None
        assert rule.result == "ok"


class TestCommandDeveloperRule:
    def test_matches_command_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("How do I create a command?")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_matches_commands_plural(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Tell me about commands")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_matches_slash_command(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("How do slash commands work?")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_matches_create_command(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a new command")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_matches_write_slash(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("write a slash command for deployment")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_matches_build_command(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Build a command")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("COMMAND development")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" in rule_ids

    def test_does_not_match_unrelated_prompt(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in main.py")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "command-developer" not in rule_ids

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a command")
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "command-developer")
        assert rule is not None
        assert rule.result == "ok"


class TestPythonPracticesPromptRule:
    def test_matches_python_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Write some python code")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_pytest_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Run pytest on this module")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_ruff_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the ruff errors")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_basedpyright_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Check basedpyright errors")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_type_hints(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Add type hints to the function")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_typing_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Use typing module")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_create_python(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a python script")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_implement_python(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("implement the python version")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_matches_test_coverage(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Improve test coverage")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("PYTHON programming")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" in rule_ids

    def test_does_not_match_unrelated_prompt(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in README.md")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-prompt" not in rule_ids

    def test_has_critical_priority(self, builtin_rules, ctx_factory):
        rule = get_rule_by_id(builtin_rules, "python-practices-prompt")
        assert rule is not None
        assert rule.priority.value == "critical"

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("write python code")
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "python-practices-prompt")
        assert rule is not None
        assert rule.result == "ok"


class TestPythonPracticesFileRule:
    def test_matches_edit_python_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/src/main.py", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-file" in rule_ids

    def test_matches_write_python_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_write_file("/project/src/utils.py", "content")
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-file" in rule_ids

    def test_does_not_match_read_python_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_read_file("/project/src/main.py")
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-file" not in rule_ids

    def test_does_not_match_non_python_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file("/project/README.md", "old", "new")
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-file" not in rule_ids

    def test_matches_python_file_in_nested_path(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/src/sub/module/file.py", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "python-practices-file" in rule_ids

    def test_has_critical_priority(self, builtin_rules, ctx_factory):
        rule = get_rule_by_id(builtin_rules, "python-practices-file")
        assert rule is not None
        assert rule.priority.value == "critical"

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/src/main.py", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "python-practices-file")
        assert rule is not None
        assert rule.result == "ok"


class TestSpecWritingPromptRule:
    def test_matches_spec_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Write a spec for the feature")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_specs_plural(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Review the specs")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_specification_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Update the specification")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_specifications_plural(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Review all specifications")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_requirements_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Add a requirement")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_test_cases_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Write test cases for the feature")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_create_spec(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_write_spec(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("write a spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_review_spec(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("review the spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_update_spec(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("update the spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_add_requirements(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("add requirements to the spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_review_requirements(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("review the requirements")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_add_tests(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("add tests to the spec")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_add_test_cases(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("add test cases")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_split_spec(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("split this spec into pages")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_matches_spec_organization(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("review spec organization")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("SPEC writing")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" in rule_ids

    def test_does_not_match_unrelated_prompt(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in main.py")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-prompt" not in rule_ids

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("create a spec")
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "spec-writing-prompt")
        assert rule is not None
        assert rule.result == "ok"


class TestSpecWritingFileRule:
    def test_matches_edit_spec_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/specs/feature.md", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" in rule_ids

    def test_matches_write_spec_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_write_file(
                "/project/specs/new-feature.md", "content"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" in rule_ids

    def test_matches_read_spec_file(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_read_file("/project/specs/feature.md")
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" in rule_ids

    def test_matches_nested_spec_path(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/docs/specs/api/endpoints.md", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" in rule_ids

    def test_does_not_match_non_spec_directory(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/src/main.py", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" not in rule_ids

    def test_does_not_match_bash_command(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_bash_command("ls specs/")
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "spec-writing-file" not in rule_ids

    def test_produces_suggestion_not_block(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/specs/feature.md", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        result = execute_rules(matched, ctx)

        assert_result(result).not_blocked()
        rule = get_rule_by_id(builtin_rules, "spec-writing-file")
        assert rule is not None
        assert rule.result == "ok"


class TestBuiltinRulesStructure:
    def test_all_rules_have_valid_structure(self, builtin_rules):
        assert len(builtin_rules) > 0, "Should have at least one builtin rule"

        for rule in builtin_rules:
            assert rule.id, f"Rule should have an id: {rule}"
            assert rule.events, f"Rule {rule.id} should have events"
            assert rule.condition, f"Rule {rule.id} should have a condition"
            assert rule.result in ("ok", "block", "warn"), (
                f"Rule {rule.id} has invalid result: {rule.result}"
            )
            assert rule.actions, f"Rule {rule.id} should have actions"

    def test_all_rules_use_suggest_action(self, builtin_rules):
        for rule in builtin_rules:
            action_types = [a.type for a in rule.actions]
            assert "suggest" in action_types, (
                f"Rule {rule.id} should use suggest action, but has: {action_types}"
            )

    def test_all_rules_have_descriptions(self, builtin_rules):
        for rule in builtin_rules:
            assert rule.description, f"Rule {rule.id} should have a description"

    def test_user_prompt_rules_listen_to_correct_event(self, builtin_rules):
        prompt_rule_ids = [
            "skill-developer",
            "agent-developer",
            "command-developer",
            "python-practices-prompt",
            "spec-writing-prompt",
        ]
        for rule in builtin_rules:
            if rule.id in prompt_rule_ids:
                assert "user_prompt_submit" in rule.events, (
                    f"Rule {rule.id} should listen to user_prompt_submit"
                )

    def test_file_rules_listen_to_correct_event(self, builtin_rules):
        file_rule_ids = [
            "python-practices-file",
            "spec-writing-file",
        ]
        for rule in builtin_rules:
            if rule.id in file_rule_ids:
                assert "pre_tool_use" in rule.events, (
                    f"Rule {rule.id} should listen to pre_tool_use"
                )

    def test_python_rules_have_critical_priority(self, builtin_rules):
        python_rule_ids = ["python-practices-prompt", "python-practices-file"]
        for rule in builtin_rules:
            if rule.id in python_rule_ids:
                assert rule.priority.value == "critical", (
                    f"Rule {rule.id} should have critical priority"
                )

    def test_other_rules_have_high_priority(self, builtin_rules):
        high_priority_rule_ids = [
            "skill-developer",
            "agent-developer",
            "command-developer",
            "spec-writing-prompt",
            "spec-writing-file",
        ]
        for rule in builtin_rules:
            if rule.id in high_priority_rule_ids:
                assert rule.priority.value == "high", (
                    f"Rule {rule.id} should have high priority"
                )


class TestMultipleRulesMatching:
    def test_python_prompt_about_skills_matches_multiple_rules(
        self, builtin_rules, ctx_factory
    ):
        ctx = ctx_factory.user_prompt_submit("Create a Python skill for code analysis")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]

        assert "skill-developer" in rule_ids
        assert "python-practices-prompt" in rule_ids

    def test_python_file_edit_matches_python_rule(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/src/main.py", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]

        assert "python-practices-file" in rule_ids
        assert "spec-writing-file" not in rule_ids

    def test_spec_file_edit_matches_spec_rule(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.pre_tool_use(
            PreToolUseInputBuilder().with_edit_file(
                "/project/specs/feature.md", "old", "new"
            )
        )
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]

        assert "spec-writing-file" in rule_ids
        assert "python-practices-file" not in rule_ids

    def test_rules_sorted_by_priority(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Create a Python skill for code analysis")
        matched = match_rules(builtin_rules, ctx)

        # Critical priority rules should come first
        priorities = [m.rule.priority.value for m in matched]
        critical_indices = [i for i, p in enumerate(priorities) if p == "critical"]
        high_indices = [i for i, p in enumerate(priorities) if p == "high"]

        if critical_indices and high_indices:
            assert max(critical_indices) < min(high_indices), (
                "Critical rules should come before high priority rules"
            )
