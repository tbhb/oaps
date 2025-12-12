---
name: activation-hooks
title: Skill activation hooks
description: Guidance on adding activation hooks for skills. Covers both OAPS plugin builtin hooks (src/oaps/hooks/builtin/skills.toml) and project-level hooks (.oaps/hooks.toml). Load when adding automatic skill suggestions.
commands:
  uv run pytest tests/unit/hooks/test_builtin_hooks.py: Run builtin hook tests
  uv run pytest tests/integration/hooks/: Run integration tests
  oaps hooks test: Validate hook configuration
  oaps hooks list: List all loaded hooks
  oaps hooks list --builtin: List builtin hooks only
principles:
  - Activation hooks help users discover skills at the right time
  - Use suggest actions to recommend skills without blocking
  - Match specific keywords and phrases that indicate skill relevance
  - Test both positive and negative match cases
best_practices:
  - "**Use word boundaries**: Prevent partial word matches with `(?<![a-zA-Z])` and `(?![a-zA-Z])`"
  - "**Case insensitivity**: Use `(?i)` flag for prompt matching"
  - "**Specific triggers**: Match exact phrases users would say"
  - "**Priority high for suggestions**: Reserve critical for enforcement rules"
  - "**Test edge cases**: Verify matching and non-matching prompts"
checklist:
  - Rule ID follows naming conventions (lowercase, hyphens)
  - Condition uses word boundaries for keyword matching
  - Has both "suggest" action (for Claude) and "warn" action (for user)
  - Consider both prompt-based and file-based triggers if applicable
  - For builtin hooks: file uses [[rules]] format, unit tests added
  - For project hooks: file uses [[hooks.rules]] format
related:
  - hook-rule-writing
  - builtin-hooks
---

## What are skill activation hooks

Skill activation hooks are rules that automatically suggest skills when users work on relevant tasks. They detect keywords in prompts or file operations and recommend the appropriate skill without blocking the user's workflow.

Activation hooks help users discover skills at the right time, whether built into OAPS or specific to a project.

## When to add activation hooks

Add an activation hook when:

- The skill addresses a specific domain (Python, specs, agents, etc.)
- Users might not know the skill exists or when to use it
- Specific keywords or file patterns reliably indicate relevance

Skip activation hooks when:

- The skill is general-purpose without clear trigger conditions
- Manual invocation is preferred
- The skill is rarely used or highly specialized

## Hook locations

### OAPS plugin skills (builtin hooks)

For skills distributed with the OAPS plugin (in `skills/` at project root), add activation hooks to:

```
src/oaps/hooks/builtin/skills.toml
```

Builtin hooks use the `[[rules]]` format and require unit tests.

### Project-level skills (project hooks)

For project-specific skills (in `.oaps/claude/skills/`), add activation hooks to:

```
.oaps/hooks.toml           # Main project hooks file
.oaps/hooks.d/*.toml       # Drop-in hook files
```

Project hooks use the `[[hooks.rules]]` format.

## Rule format

Skill activation rules typically use two actions:

1. **`suggest`** - Injects context into Claude's conversation (visible in `<system-reminder>` tags)
2. **`warn`** - Displays a notification to the user in the terminal

Using both ensures Claude receives guidance while the user knows which skills are being suggested.

### Builtin hooks format

Builtin hook files use `[[rules]]` sections:

```toml
[[rules]]
id = "my-skill"
description = "Suggest my skill for relevant work"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])keyword(?![a-zA-Z]).*"
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider using the my-skill skill (Skill tool) for guidance."

[[rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-skill"
```

### Project hooks format

Project hook files use `[[hooks.rules]]` sections:

```toml
[[hooks.rules]]
id = "my-project-skill"
description = "Suggest my project skill for relevant work"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])keyword(?![a-zA-Z]).*"
'''
result = "ok"

[[hooks.rules.actions]]
type = "suggest"
message = "Consider using the my-project-skill skill for guidance."

[[hooks.rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-project-skill"
```

## Existing builtin activation rules

The `skills.toml` file contains these activation rules:

### Prompt-based rules (user_prompt_submit)

| Rule ID                   | Keywords                                      | Description                                   |
|:--------------------------|:----------------------------------------------|:----------------------------------------------|
| `skill-developer`         | skill, skills, create/write/build skill       | Suggests skill developer for skill work       |
| `agent-developer`         | agent, agents, subagent, create/write agent   | Suggests agent developer for agent work       |
| `command-developer`       | command, slash command, create/write command  | Suggests command developer for slash commands |
| `python-practices-prompt` | python, pytest, ruff, typing                  | Enforces Python practices (critical priority) |
| `spec-writing-prompt`     | spec, specification, requirements, test cases | Suggests spec writing skill                   |

### File-based rules (pre_tool_use)

| Rule ID                 | File Pattern  | Description                                         |
|:------------------------|:--------------|:----------------------------------------------------|
| `python-practices-file` | `*.py`        | Enforces Python practices when editing Python files |
| `spec-writing-file`     | `**/specs/**` | Suggests spec writing for spec file operations      |

### Priority conventions

- **critical**: Enforcement rules that must execute first (Python practices)
- **high**: Recommendation rules for skill suggestions
- **medium**: Default for general rules
- **low**: Logging or audit rules

## Adding builtin activation hooks (OAPS plugin skills)

For skills distributed with the OAPS plugin, follow these steps to add activation hooks to `src/oaps/hooks/builtin/skills.toml`.

### Step 1: Determine trigger conditions

Identify what should trigger the skill:

- **Keywords**: What words indicate relevance? (e.g., "hook", "rule", "automation")
- **Action phrases**: What actions suggest the skill? (e.g., "create a hook", "write rules")
- **File patterns**: What files indicate relevance? (e.g., `*.toml`, `hooks.d/`)

### Step 2: Write the TOML rule

Add the rule to `src/oaps/hooks/builtin/skills.toml`:

```toml
# =============================================================================
# My New Skill
# =============================================================================

[[rules]]
id = "my-new-skill"
description = "Suggest my new skill for relevant work"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])keyword(?![a-zA-Z]).*" or prompt =~ "(?i).*(create|write|build).*thing.*"
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider using the my-new-skill skill (Skill tool) for guidance on thing structure and best practices."

[[rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-new-skill"
```

### Step 3: Add unit tests

Create tests in `tests/unit/hooks/test_builtin_hooks.py`:

```python
class TestMyNewSkillRule:
    def test_matches_keyword(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Help me with keyword stuff")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "my-new-skill" in rule_ids

    def test_matches_action_phrase(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Create a thing for my project")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "my-new-skill" in rule_ids

    def test_case_insensitive(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("KEYWORD configuration")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "my-new-skill" in rule_ids

    def test_does_not_match_unrelated(self, builtin_rules, ctx_factory):
        ctx = ctx_factory.user_prompt_submit("Fix the bug in main.py")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "my-new-skill" not in rule_ids

    def test_word_boundary_prevents_partial_match(self, builtin_rules, ctx_factory):
        # "keyword" embedded in another word should not match
        ctx = ctx_factory.user_prompt_submit("Use mykeywordtool")
        matched = match_rules(builtin_rules, ctx)
        rule_ids = [m.rule.id for m in matched]
        assert "my-new-skill" not in rule_ids
```

### Step 4: Run tests and validate

```bash
# Run unit tests
uv run pytest tests/unit/hooks/test_builtin_hooks.py -v -k "my_new_skill"

# Run all builtin hook tests
uv run pytest tests/unit/hooks/test_builtin_hooks.py -v

# Validate hook configuration
oaps hooks test

# List builtin hooks to verify loading
oaps hooks list --builtin
```

## Adding file-based activation

For skills triggered by file operations, use `pre_tool_use` events:

```toml
[[rules]]
id = "my-skill-file"
description = "Suggest my skill when working with relevant files"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Edit" or tool_name == "Write" or tool_name == "Read") and matches_glob(tool_input["file_path"], "**/*.ext")
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider using the my-skill skill when working with .ext files."

[[rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-skill"
```

Test file-based rules with `PreToolUseInputBuilder`:

```python
def test_matches_ext_file_edit(self, builtin_rules, ctx_factory):
    ctx = ctx_factory.pre_tool_use(
        PreToolUseInputBuilder().with_edit_file(
            "/project/config.ext", "old", "new"
        )
    )
    matched = match_rules(builtin_rules, ctx)
    rule_ids = [m.rule.id for m in matched]
    assert "my-skill-file" in rule_ids
```

## Adding project-level activation hooks

For project-specific skills, add activation hooks to `.oaps/hooks.toml` or a drop-in file in `.oaps/hooks.d/`.

### Basic project hook

Add to `.oaps/hooks.toml`:

```toml
[[hooks.rules]]
id = "my-project-skill"
description = "Suggest my project skill for domain work"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])domain-keyword(?![a-zA-Z]).*"
'''
result = "ok"

[[hooks.rules.actions]]
type = "suggest"
message = "Consider using the my-project-skill skill for domain guidance."

[[hooks.rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-project-skill"
```

### Using drop-in files

For better organization, create a dedicated file in `.oaps/hooks.d/`:

```toml
# .oaps/hooks.d/skill-activation.toml

[[rules]]
id = "my-project-skill"
description = "Suggest my project skill for domain work"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])domain-keyword(?![a-zA-Z]).*"
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider using the my-project-skill skill for domain guidance."

[[rules.actions]]
type = "warn"
message = "💡 Skill suggested: my-project-skill"
```

Drop-in files use `[[rules]]` format (same as builtin hooks), while the main `.oaps/hooks.toml` uses `[[hooks.rules]]` format.

### Testing project hooks

Validate project hooks with:

```bash
oaps hooks test
oaps hooks list
```

## Regex pattern guidelines

### Word boundaries

Use lookahead/lookbehind to prevent partial matches:

```
(?<![a-zA-Z])keyword(?![a-zA-Z])
```

This matches "keyword" but not "mykeyword" or "keywordish".

### Case insensitivity

Start patterns with `(?i)` flag:

```
(?i).*keyword.*
```

Or use the `=~~` operator for case-insensitive matching.

### Multiple keywords

Combine patterns with `or`:

```toml
condition = '''
prompt =~ "(?i).*(?<![a-zA-Z])keyword1(?![a-zA-Z]).*" or prompt =~ "(?i).*(?<![a-zA-Z])keyword2(?![a-zA-Z]).*"
'''
```

### Action phrases

Match creation/modification verbs with the target:

```
(?i).*(create|write|build|add|develop|make).*thing.*
```
