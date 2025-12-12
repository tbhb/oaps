# Event-specific hook rule examples

OAPS supports 10 hook event types, each corresponding to a specific point in the Claude Code lifecycle. This document provides complete, working examples for each event type, with guidance on when and how to use them effectively.

## Event type summary

| Event | When it fires | Primary use cases |
|-------|---------------|-------------------|
| `pre_tool_use` | Before tool execution | Block, modify, or warn about operations |
| `post_tool_use` | After tool execution | Log results, inject context |
| `user_prompt_submit` | User submits prompt | Inject context, filter prompts |
| `permission_request` | Permission dialog shown | Auto-approve or auto-deny |
| `session_start` | Session begins | Setup, welcome context |
| `session_end` | Session ends | Cleanup, logging |
| `pre_compact` | Before memory compaction | Preserve critical context |
| `notification` | Notification shown | Filter or transform |
| `stop` | User interrupts (Ctrl+C) | Cleanup on interrupt |
| `subagent_stop` | Subagent terminates | Subagent cleanup |

---

## pre_tool_use

Fires before a tool executes. This is the primary event for enforcement rules since it can block or modify operations before they happen.

**Available context:** `tool_name`, `tool_input`, `tool_use_id`, `session_id`, `cwd`, `permission_mode`

**Supported actions:** deny, allow, warn, suggest, inject, modify, transform, script, python, log

### Example 1: Block dangerous rm commands

```toml
[[rules]]
id = "block-rm-rf"
description = "Block recursive force delete commands"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "rm\\s+(-[^\\s]*r[^\\s]*f|-[^\\s]*f[^\\s]*r|--force\\s+--recursive|--recursive\\s+--force)"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Recursive force delete (rm -rf) is blocked for safety. Use explicit paths and review files first."
```

### Example 2: Block writes outside project directory

```toml
[[rules]]
id = "block-writes-outside-project"
description = "Prevent writing files outside project boundary"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name in ["Write", "Edit"]
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write to '${tool_input.file_path}' - path is outside project directory."
```

### Example 3: Modify bash commands to add safety flags

```toml
[[rules]]
id = "add-npm-ci-flag"
description = "Use npm ci instead of npm install in CI"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
$env("CI") != null
and tool_name == "Bash"
and tool_input.command.starts_with("npm install")
and not tool_input.command =~~ "--ci|\\bci\\b"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "tool_input.command"
operation = "replace"
value = "npm ci"
```

### Example 4: Warn when modifying sensitive configuration

```toml
[[rules]]
id = "warn-config-modification"
description = "Warn when modifying configuration files"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name in ["Write", "Edit"]
and ($matches_glob(tool_input.file_path, "**/.env*")
     or $matches_glob(tool_input.file_path, "**/config/**")
     or $matches_glob(tool_input.file_path, "**/*.config.*"))
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Modifying configuration file '${tool_input.file_path}'. Ensure no secrets or credentials are hardcoded."
```

---

## post_tool_use

Fires after a tool completes execution. Use for logging, analysis, and injecting follow-up context. Cannot block the operation (it already happened).

**Available context:** `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `session_id`, `cwd`

**Supported actions:** warn, suggest, inject, script, python, log

### Example 5: Log file modifications

```toml
[[rules]]
id = "log-file-writes"
description = "Log all file modifications for audit"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name in ["Write", "Edit"]'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "File modified: ${tool_input.file_path}"
```

### Example 6: Suggest running tests after code changes

```toml
[[rules]]
id = "suggest-tests-after-edit"
description = "Suggest running tests after modifying Python source"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name in ["Write", "Edit"]
and $matches_glob(tool_input.file_path, "src/**/*.py")
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Source file modified. Consider running 'pytest' to verify changes."
```

### Example 7: Inject context after reading specific files

```toml
[[rules]]
id = "inject-api-context"
description = "Inject API documentation context after reading API files"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Read"
and $matches_glob(tool_input.file_path, "**/api/**/*.py")
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = "This API module follows REST conventions. See docs/api-guidelines.md for endpoint patterns and error handling."
```

---

## user_prompt_submit

Fires when the user submits a prompt, before Claude processes it. Ideal for injecting project-specific context or filtering prompts.

**Available context:** `prompt`, `session_id`, `cwd`, `permission_mode`

**Supported actions:** deny, warn, suggest, inject, script, python, log

### Example 8: Inject project guidelines on deployment prompts

```toml
[[rules]]
id = "inject-deploy-guidelines"
description = "Inject deployment guidelines when user mentions deploy"
events = ["user_prompt_submit"]
priority = "medium"
condition = 'prompt.as_lower =~~ "deploy|release|production"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Deployment checklist:
1. All tests must pass (just test)
2. Linting must pass (just lint)
3. Version bump required in pyproject.toml
4. CHANGELOG.md must be updated
See docs/release-process.md for full procedure.
"""
```

### Example 9: Warn about potentially destructive prompts

```toml
[[rules]]
id = "warn-destructive-prompts"
description = "Warn when prompt suggests destructive operations"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt.as_lower =~~ "delete all|remove all|drop.*table|truncate|reset.*database|wipe"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "This prompt suggests a potentially destructive operation. Please confirm this is intentional."
```

### Example 10: Suggest skill activation

```toml
[[rules]]
id = "suggest-python-skill"
description = "Suggest Python practices skill for Python-related prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "(?i).*(?<![a-zA-Z])(python|pytest|ruff|typing)(?![a-zA-Z]).*"
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider using the oaps:python-practices skill for Python development best practices."
```

---

## permission_request

Fires when Claude requests user permission for an operation. Use to auto-approve safe patterns or auto-deny risky operations.

**Available context:** `tool_name`, `tool_input`, `tool_use_id`, `session_id`, `cwd`

**Supported actions:** deny, allow, warn, suggest, script, python, log

### Example 11: Auto-approve safe read operations

```toml
[[rules]]
id = "auto-approve-reads"
description = "Auto-approve reading project files"
events = ["permission_request"]
priority = "medium"
terminal = true
condition = '''
tool_name == "Read"
and $is_path_under(tool_input.file_path, cwd)
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Example 12: Auto-approve test commands

```toml
[[rules]]
id = "auto-approve-pytest"
description = "Auto-approve pytest and test commands"
events = ["permission_request"]
priority = "medium"
terminal = true
condition = '''
tool_name == "Bash"
and (tool_input.command.starts_with("pytest")
     or tool_input.command.starts_with("just test")
     or tool_input.command.starts_with("npm test"))
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Example 13: Auto-deny operations outside project

```toml
[[rules]]
id = "deny-external-writes"
description = "Auto-deny write operations outside project"
events = ["permission_request"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit"]
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write files outside project directory."
```

---

## session_start

Fires when a Claude Code session begins. Use for environment setup, welcome messages, and initial context injection.

**Available context:** `session_id`, `source` (startup/resume/clear/compact), `cwd`, `transcript_path`

**Supported actions:** inject, script, python, log

### Example 14: Inject welcome context on startup

```toml
[[rules]]
id = "welcome-context"
description = "Inject project context on session start"
events = ["session_start"]
priority = "medium"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Project: OAPS (Overengineered Agentic Project System)
Commands: just test, just lint, just format
Python: 3.10+, use uv run for all Python execution
Guidelines: See CLAUDE.md for development practices
"""
```

### Example 15: Log session start for audit

```toml
[[rules]]
id = "log-session-start"
description = "Log session starts for audit trail"
events = ["session_start"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Session started: ${session_id} (${source}) in ${cwd}"
```

### Example 16: Inject context after compaction

```toml
[[rules]]
id = "post-compact-context"
description = "Restore critical context after compaction"
events = ["session_start"]
priority = "high"
condition = 'source == "compact"'
result = "ok"

[[rules.actions]]
type = "inject"
content = "IMPORTANT: This project uses Python 3.12+. Never use 'from __future__ import annotations'."
```

---

## session_end

Fires when a session ends. Use for cleanup operations and final logging. Cannot inject context (session is ending).

**Available context:** `session_id`, `reason` (clear/logout/prompt_input_exit/other), `cwd`

**Supported actions:** script, python, log

### Example 17: Log session end

```toml
[[rules]]
id = "log-session-end"
description = "Log session end with reason"
events = ["session_end"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Session ended: ${session_id} reason=${reason}"
```

### Example 18: Run cleanup script on session end

```toml
[[rules]]
id = "cleanup-temp-files"
description = "Clean up temporary files on session end"
events = ["session_end"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "script"
command = "rm -f /tmp/oaps-session-*"
```

---

## pre_compact

Fires before memory compaction. Critical for preserving context that must survive compaction boundaries.

**Available context:** `session_id`, `trigger` (manual/auto), `custom_instructions`, `cwd`

**Supported actions:** inject, script, python, log

### Example 19: Preserve critical project context

```toml
[[rules]]
id = "preserve-project-context"
description = "Inject critical context before compaction"
events = ["pre_compact"]
priority = "critical"
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = """
CRITICAL CONTEXT TO PRESERVE:
- Project: OAPS hook system
- Python version: 3.12+ required
- Never use: from __future__ import annotations
- Run tests: just test
- Run linting: just lint
"""
```

### Example 20: Preserve current task state

```toml
[[rules]]
id = "preserve-task-state"
description = "Preserve task state from session store"
events = ["pre_compact"]
priority = "high"
condition = '$session_get("current_task") != null'
result = "ok"

[[rules.actions]]
type = "inject"
content = "CURRENT TASK: Continuing work on ${$session_get('current_task')}"
```

---

## notification

Fires before a notification is displayed. Use to filter, transform, or suppress notifications.

**Available context:** `session_id`, `message`, `notification_type` (permission_prompt/idle_prompt/auth_success/elicitation_dialog), `cwd`

**Supported actions:** script, python, log

### Example 21: Log notifications for debugging

```toml
[[rules]]
id = "log-notifications"
description = "Log all notifications for debugging"
events = ["notification"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "Notification [${notification_type}]: ${message}"
```

### Example 22: Log idle prompts separately

```toml
[[rules]]
id = "log-idle-prompts"
description = "Track idle prompt frequency"
events = ["notification"]
priority = "low"
condition = 'notification_type == "idle_prompt"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Idle prompt displayed - session may be waiting for user input"
```

---

## stop

Fires when the user interrupts an operation (Ctrl+C or Escape). Use for cleanup and logging.

**Available context:** `session_id`, `stop_hook_active`, `cwd`

**Supported actions:** script, python, log

### Example 23: Log user interrupts

```toml
[[rules]]
id = "log-user-interrupt"
description = "Log when user interrupts operation"
events = ["stop"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "Operation interrupted by user (Ctrl+C or Escape)"
```

### Example 24: Cleanup on interrupt

```toml
[[rules]]
id = "cleanup-on-interrupt"
description = "Run cleanup when user interrupts"
events = ["stop"]
priority = "medium"
condition = "not stop_hook_active"
result = "ok"

[[rules.actions]]
type = "script"
command = "rm -f /tmp/oaps-partial-*"
```

---

## subagent_stop

Fires when a subagent (spawned via Task tool) terminates. Use for subagent-specific cleanup and logging.

**Available context:** `session_id`, `stop_hook_active`, `cwd`

**Supported actions:** script, python, log

### Example 25: Log subagent completion

```toml
[[rules]]
id = "log-subagent-stop"
description = "Log subagent termination"
events = ["subagent_stop"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Subagent terminated in session ${session_id}"
```

### Example 26: Cleanup subagent resources

```toml
[[rules]]
id = "cleanup-subagent"
description = "Clean up subagent temporary resources"
events = ["subagent_stop"]
priority = "medium"
condition = "not stop_hook_active"
result = "ok"

[[rules.actions]]
type = "script"
command = "rm -rf /tmp/subagent-workspace-*"
```

---

## Event selection guidelines

| Goal | Recommended event | Rationale |
|------|-------------------|-----------|
| Block dangerous operations | `pre_tool_use` | Can deny before execution |
| Transform tool inputs | `pre_tool_use` | Can modify inputs via modify/transform |
| Audit tool usage | `post_tool_use` | Has access to tool response |
| Inject project context | `user_prompt_submit` | Early injection, before planning |
| Auto-approve safe operations | `permission_request` | Direct control over permission dialogs |
| Session initialization | `session_start` | First opportunity for context |
| Preserve state across compaction | `pre_compact` | Context survives memory boundaries |
| Final cleanup | `session_end` | Last opportunity before exit |

---

## Best practices

1. **Use `pre_tool_use` for enforcement**: This is the only event that can block operations before they execute.

2. **Use `terminal = true` for definitive decisions**: When a rule should stop further evaluation (e.g., explicit allow or deny).

3. **Set appropriate priorities**: Use `critical` for safety rules, `high` for standards enforcement, `medium` for suggestions.

4. **Match result to intent**: Use `block` with `deny`, `warn` with `warn/suggest`, `ok` with `allow/inject/log`.

5. **Keep conditions focused**: Target specific scenarios rather than overly broad patterns.

6. **Log for observability**: Even if a rule does not block, logging provides valuable audit trails.

7. **Use `pre_compact` for critical state**: Any context essential for continuity should be injected before compaction.
