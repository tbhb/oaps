---
description: >-
  This skill should be used when the user asks to "create a hook rule",
  "write a hook", "add a hook rule", "debug a hook", "test a hook",
  "review hook rules", "brainstorm hooks", or needs guidance on hook
  rule syntax, conditions, actions, expressions, or hook development
  best practices for OAPS.
---

# Hook rule writing for OAPS

This skill provides guidance for creating, reviewing, testing, and debugging hook rules in OAPS. Hook rules are rule-based automation that respond to Claude Code events, enabling enforcement of project standards, automated workflows, and guardrails without writing custom code.

## About hook rules

Hook rules define automated responses to Claude Code events. When an event occurs (tool use, user prompt, session lifecycle), OAPS evaluates configured rules against the event context and executes matching actions. Rules are written in TOML and stored in hook configuration files.

The hook system operates on a simple principle: events trigger rule evaluation, conditions determine matches, and actions execute responses. This declarative approach separates policy from implementation, making rules readable, maintainable, and auditable.

Hook rules serve several purposes:

1. **Guardrails** - Prevent dangerous operations (blocking destructive commands, protecting sensitive files)
2. **Automation** - Trigger scripts or inject context based on events
3. **Observability** - Log events for debugging and auditing
4. **Guidance** - Provide warnings or suggestions to Claude during operation

Rules are stored in `.oaps/hooks.toml` for project-specific rules or distributed via OAPS plugins. Multiple rule sources are merged and evaluated together, with priorities determining execution order.

## Quick start

A minimal hook rule blocks a dangerous bash command:

```toml
[[rules]]
id = "block-rm-rf"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash" and "rm -rf" in tool_input.command'
result = "block"
actions = [{ type = "deny", message = "Destructive rm -rf commands are not allowed." }]
```

This rule:

- Triggers on `pre_tool_use` events (before tool execution)
- Matches when the Bash tool is invoked with `rm -rf` in the command
- Blocks execution with a denial message

A more sophisticated rule warns about file modifications without blocking:

```toml
[[rules]]
id = "warn-env-modification"
events = ["pre_tool_use"]
condition = '''
  tool_name in ["Edit", "Write"] and
  $matches_glob(tool_input.file_path, "**/.env*")
'''
result = "warn"
priority = "high"
description = "Warn when modifying environment files"
actions = [
  { type = "warn", message = "Modifying ${tool_input.file_path}. Ensure sensitive values are not committed." },
  { type = "log", level = "info", message = "Environment file modification: ${tool_input.file_path}" }
]
```

## Hook rule anatomy

Every hook rule has these core components:

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the rule (kebab-case recommended) |
| `events` | list | Event types that trigger evaluation: `pre_tool_use`, `post_tool_use`, `permission_request`, `user_prompt_submit`, `notification`, `session_start`, `session_end`, `stop`, `subagent_stop`, `pre_compact`, or `all` |
| `condition` | string | Expression evaluated against event context; rule matches when true |
| `result` | string | Outcome type when rule matches: `block`, `ok`, or `warn` |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `priority` | string | `medium` | Evaluation order: `critical`, `high`, `medium`, `low` |
| `terminal` | bool | `false` | Stop evaluating further rules if this rule matches |
| `enabled` | bool | `true` | Toggle rule without removing it |
| `description` | string | none | Human-readable explanation of the rule's purpose |
| `actions` | list | `[]` | Actions to execute when rule matches |

### Action configuration

Actions define what happens when a rule matches. Each action has a `type` and type-specific fields:

**Permission actions** (for `pre_tool_use`, `permission_request`):

- `deny` - Block the operation; requires `message`
- `allow` - Explicitly permit the operation

**Feedback actions** (all events):

- `log` - Write to hook log; requires `level` (debug/info/warning/error) and `message`
- `warn` - Add warning to system messages; requires `message`
- `suggest` - Add suggestion to system messages; requires `message`
- `inject` - Add context to hook output; requires `content`

**Modification actions** (for `pre_tool_use`, `permission_request`):

- `modify` - Change tool input fields; requires `field`, `operation`, `value`
- `transform` - Execute script/Python to modify input; requires `entrypoint` or `command`/`script`

**Execution actions** (all events):

- `python` - Run Python function; requires `entrypoint` (format: `module.path:function_name`)
- `shell` - Run shell command; requires `command` or `script`

Actions support template substitution in message and content fields. Use `${variable}` syntax to interpolate context values (e.g., `${tool_name}`, `${tool_input.file_path}`).

## Workflow selection

Select the appropriate workflow based on the task:

### Brainstorm workflow

Use when exploring what hook rules to create for a project. This workflow:

1. Analyzes project structure and existing configuration
2. Identifies common patterns that benefit from automation
3. Suggests rules categorized by purpose (guardrails, automation, observability)

### Write workflow

Use when creating new hook rules. This workflow:

1. Gathers requirements (event type, condition, desired outcome)
2. Drafts rule configuration with appropriate actions
3. Validates syntax and expression correctness
4. Tests rule against sample scenarios

### Review workflow

Use when auditing existing hook rules. This workflow:

1. Loads all active rules from configuration
2. Checks for common issues (overlapping conditions, missing terminal flags, priority conflicts)
3. Validates expressions and action configurations
4. Suggests improvements for clarity and maintainability

### Test workflow

Use when debugging or validating hook behavior. This workflow:

1. Creates test scenarios with mock event contexts
2. Evaluates rules against test contexts
3. Verifies expected matches and action execution
4. Reports expression evaluation details for debugging

## Key concepts

### Events

Hook events correspond to Claude Code lifecycle points:

| Event | Description | Common actions |
|-------|-------------|----------------|
| `pre_tool_use` | Before tool execution | deny, allow, modify, transform, warn |
| `post_tool_use` | After tool execution | log, inject |
| `permission_request` | User permission prompt | deny, allow |
| `user_prompt_submit` | User submits prompt | deny, warn, inject |
| `notification` | System notification shown | log |
| `session_start` | Session begins | log, inject |
| `session_end` | Session ends | log |
| `stop` | User interrupts (Ctrl+C) | log |
| `subagent_stop` | Subagent terminates | log |
| `pre_compact` | Before memory compaction | inject |

### Expressions

Conditions use rule-engine syntax (Python-like expressions) evaluated against event context. Available context variables depend on the event type:

**Common variables:**

- `hook_type` - Event type name
- `session_id` - Current session identifier
- `cwd` - Working directory
- `permission_mode` - Current permission mode (default/plan/acceptEdits/bypassPermissions)

**Tool-specific variables** (pre_tool_use, post_tool_use, permission_request):

- `tool_name` - Name of the tool (Bash, Edit, Write, etc.)
- `tool_input` - Tool input parameters as object
- `tool_output` - Tool response (post_tool_use only)

**Prompt variables** (user_prompt_submit):

- `prompt` - User's submitted prompt text

**Git variables** (when in git repository):

- `git_branch` - Current branch name
- `git_is_dirty` - Repository has uncommitted changes
- `git_staged_files`, `git_modified_files`, `git_untracked_files`, `git_conflict_files` - File lists

**Expression functions** (called with `$` prefix):

- `$is_path_under(path, base)` - Secure path containment check
- `$file_exists(path)` - Check file existence
- `$matches_glob(path, pattern)` - Glob pattern matching
- `$env(name)` - Get environment variable
- `$is_git_repo()` - Check if in git repository
- `$session_get(key)` - Get value from session store
- `$project_get(key)` - Get value from project store
- `$is_staged(path)`, `$is_modified(path)` - Git file status
- `$git_has_staged(pattern?)`, `$git_has_modified(pattern?)` - Pattern-based git checks
- `$current_branch()` - Get current branch name

### Priorities

Rules evaluate in priority order: `critical` > `high` > `medium` > `low`. Within the same priority, rules evaluate in definition order.

- **critical** - Safety-critical rules (blocking dangerous operations)
- **high** - Important enforcement (project standards)
- **medium** - Standard automation (default)
- **low** - Optional suggestions

### Terminal behavior

When `terminal = true`, matching this rule stops further rule evaluation. Use for:

- Allow-list patterns (explicit allows that skip remaining checks)
- Block-list patterns (immediate rejection without further checks)
- Performance optimization (skip unnecessary evaluations)

### Result types

The `result` field determines the overall outcome when a rule matches:

- **block** - Operation is prevented. Use with `deny` action for definitive rejection.
- **warn** - Operation proceeds with advisory messages. Use with `warn` or `suggest` actions.
- **ok** - Operation is explicitly permitted or augmented. Use with `allow`, `inject`, or modification actions.

Match the `result` to the intended behavior. A `block` result with no `deny` action logs a warning but does not prevent execution. A `warn` result with a `deny` action has undefined behavior.

## Reference guide

The skill includes reference documents for detailed information:

| Reference | When to load |
|-----------|--------------|
| `events.md` | Writing rules for specific event types, understanding event payloads |
| `expressions.md` | Complex conditions, available functions, expression debugging |
| `actions.md` | Configuring actions, understanding action types and their fields |
| `patterns.md` | Common rule patterns, recipes for typical use cases |
| `troubleshooting.md` | Debugging rule behavior, common mistakes, validation errors |

To load references, run:

```bash
oaps skill context hook-rule-writing --references <names...>
```

## Getting started

To begin hook rule development:

1. **Identify the automation need** - Determine what behavior to enforce, automate, or observe. Consider the event type that corresponds to the target behavior.

2. **Draft the condition** - Write an expression that matches the specific scenario. Start simple and refine based on testing. Conditions support boolean operators (`and`, `or`, `not`), comparisons, membership tests (`in`), and function calls.

3. **Select appropriate actions** - Choose actions that match the `result` type. For `block` results, use `deny`. For `warn` results, use `warn` or `suggest`. For `ok` results, use `log`, `inject`, or modification actions.

4. **Set priority and terminal behavior** - Place safety-critical rules at `critical` priority. Use `terminal = true` for definitive allow/deny decisions.

5. **Test the rule** - Use the test workflow to verify behavior against sample scenarios before deployment.

6. **Iterate** - Refine conditions and actions based on real-world behavior. Monitor hook logs for unexpected matches or misses.

For complex rules or unfamiliar patterns, load the relevant references before writing. The `patterns.md` reference provides recipes for common use cases.

## Common patterns

Several patterns appear frequently in hook rule development:

**Tool-specific rules** - Match on `tool_name` to target specific tools:

```
tool_name == "Bash" and "sudo" in tool_input.command
```

**Path-based rules** - Use `$matches_glob` or `$is_path_under` for file targeting:

```
tool_name == "Edit" and $matches_glob(tool_input.file_path, "**/test_*.py")
```

**Git-aware rules** - Combine git functions for repository context:

```
$is_git_repo() and $git_has_staged("*.py") and $current_branch() == "main"
```

**Environment-conditional rules** - Check environment for deployment context:

```
$env("CI") == "true" or $env("OAPS_ENV") == "production"
```

Load the `patterns.md` reference for comprehensive recipes covering guardrails, automation, logging, and advanced use cases.
