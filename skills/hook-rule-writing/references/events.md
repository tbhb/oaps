---
name: events
title: Hook event types
description: All 10 hook event types with input fields, supported actions, and output capabilities. Load when selecting events for hook rules.
commands: {}
principles:
  - Match events to rule intent - use PreToolUse for blocking, PostToolUse for logging
  - Prefer narrow event scopes - avoid "all" unless truly universal
  - Understand event timing - pre-events can modify, post-events can only observe
best_practices:
  - "**Use PreToolUse for enforcement**: Block or modify operations before execution"
  - "**Use PostToolUse for telemetry**: Log results and inject follow-up context"
  - "**Use UserPromptSubmit for context**: Inject project knowledge at prompt time"
  - "**Use SessionStart for initialization**: Set up session-specific state"
  - "**Use PreCompact for preservation**: Inject critical context before memory compaction"
checklist:
  - Event type matches the rule's purpose
  - Rule condition uses fields available for the event
  - Actions are supported by the chosen event type
  - Output requirements are compatible with event capabilities
related:
  - actions
  - expressions
  - functions
---

## Event type catalog

| Event | Lifecycle phase | Decision support | Primary use cases |
|-------|-----------------|------------------|-------------------|
| `pre_tool_use` | Before tool execution | deny, allow, modify | Block dangerous operations, transform inputs |
| `post_tool_use` | After tool execution | block, context | Log results, suggest follow-up actions |
| `user_prompt_submit` | On prompt submission | block, context | Inject context, warn on sensitive topics |
| `permission_request` | On permission dialog | deny, allow | Auto-approve safe patterns, deny risky operations |
| `notification` | On notification sent | suppress | Filter noisy alerts |
| `session_start` | Session begins | context | Log session start, inject welcome context |
| `session_end` | Session ends | N/A | Log session summary, cleanup |
| `stop` | User stops operation | block | Log stop reason, cleanup |
| `subagent_stop` | Subagent stopped | block | Log subagent termination |
| `pre_compact` | Before compaction | context | Inject critical context to preserve |

## Tool lifecycle events

### pre_tool_use

Trigger before tool execution. Use for blocking dangerous operations, modifying inputs, or enforcing policies.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Unique session identifier |
| `transcript_path` | STRING | Path to session transcript file |
| `permission_mode` | STRING | Permission mode (default, plan, acceptEdits, bypassPermissions) |
| `hook_event_name` | STRING | Always "PreToolUse" |
| `cwd` | STRING | Current working directory |
| `tool_name` | STRING | Tool name (Bash, Write, Read, Edit, etc.) |
| `tool_input` | MAPPING | Tool-specific input parameters |
| `tool_use_id` | STRING | Unique tool invocation ID |

**Supported actions:** deny, allow, warn, suggest, inject, modify, transform, script, python, log

**Output capabilities:**

- `permissionDecision`: "allow" or "deny"
- `permissionDecisionReason`: Human-readable explanation
- `updatedInput`: Modified tool input fields

**Example rule:**

```toml
[[rules]]
id = "block-force-push"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "push.*--force"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Force push blocked - use --force-with-lease instead"
```

### post_tool_use

Trigger after tool execution. Use for logging, analysis, or injecting follow-up suggestions.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "PostToolUse" |
| `tool_name` | STRING | Tool name |
| `tool_input` | MAPPING | Tool input parameters |
| `tool_response` | STRING | Tool execution result |
| `tool_use_id` | STRING | Tool invocation ID |
| `cwd` | STRING | Current working directory |

**Supported actions:** warn, suggest, inject, script, python, log

**Output capabilities:**

- `decision`: "block" to stop processing
- `reason`: Reason for blocking
- `additionalContext`: Context to inject

**Example rule:**

```toml
[[rules]]
id = "log-file-writes"
events = ["post_tool_use"]
condition = 'tool_name in ["Write", "Edit"]'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "File modified: ${tool_input.file_path}"
```

## User interaction events

### user_prompt_submit

Trigger when user submits a prompt. Use for context injection, prompt validation, or warning on sensitive topics.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "UserPromptSubmit" |
| `prompt` | STRING | User's prompt text |
| `permission_mode` | STRING | Permission mode |
| `cwd` | STRING | Current working directory |

**Supported actions:** deny, warn, suggest, inject, script, python, log

**Output capabilities:**

- `additionalContext`: Context to inject (supports plain text output)
- `decision`: "block" to reject prompt
- `reason`: Reason for blocking

**Example rule:**

```toml
[[rules]]
id = "inject-project-context"
events = ["user_prompt_submit"]
condition = 'prompt.as_lower =~~ "deploy"'
result = "ok"

[[rules.actions]]
type = "inject"
content = "Deployment requires approval from #ops channel. See DEPLOY.md for procedures."
```

### permission_request

Trigger when Claude requests user permission. Use for auto-approval of safe patterns or auto-denial of risky operations.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "PermissionRequest" |
| `tool_name` | STRING | Tool requesting permission |
| `tool_input` | MAPPING | Tool input parameters |
| `tool_use_id` | STRING | Tool invocation ID |
| `cwd` | STRING | Current working directory |

**Supported actions:** deny, allow, warn, suggest, script, python, log

**Output capabilities:**

- `permissionDecision`: "allow" or "deny"
- `permissionDecisionReason`: Human-readable explanation

**Example rule:**

```toml
[[rules]]
id = "auto-approve-tests"
events = ["permission_request"]
condition = '''
tool_name == "Bash" and tool_input.command.starts_with("pytest")
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### notification

Trigger before notification display. Use for filtering noisy alerts.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "Notification" |
| `message` | STRING | Notification message |
| `notification_type` | STRING | Type: permission_prompt, idle_prompt, auth_success, elicitation_dialog |
| `cwd` | STRING | Current working directory |

**Supported actions:** script, python, log

**Output capabilities:**

- Empty output allows notification
- `suppressOutput: true` to suppress

**Example rule:**

```toml
[[rules]]
id = "suppress-idle-prompts"
events = ["notification"]
condition = 'notification_type == "idle_prompt"'
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "Suppressed idle prompt"
```

## Session lifecycle events

### session_start

Trigger when session begins. Use for environment setup, welcome messages, or context injection.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier (UUID) |
| `hook_event_name` | STRING | Always "SessionStart" |
| `source` | STRING | How session started: startup, resume, clear, compact |
| `cwd` | STRING | Current working directory |
| `transcript_path` | STRING | Path to session transcript |

**Supported actions:** inject, script, python, log

**Output capabilities:**

- `additionalContext`: Context to inject at session start

**Example rule:**

```toml
[[rules]]
id = "welcome-context"
events = ["session_start"]
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = "Project: OAPS. Run `just test` for tests, `just lint` for linting."
```

### session_end

Trigger when session ends. Use for cleanup and logging.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "SessionEnd" |
| `reason` | STRING | Why ended: clear, logout, prompt_input_exit, other |
| `cwd` | STRING | Current working directory |

**Supported actions:** script, python, log

**Output:** No specific output schema. Exit code 0 indicates success.

**Example rule:**

```toml
[[rules]]
id = "log-session-end"
events = ["session_end"]
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Session ended: ${reason}"
```

### stop

Trigger when user interrupts an operation (Ctrl+C or Escape).

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "Stop" |
| `stop_hook_active` | BOOLEAN | Whether stop hooks are active |
| `cwd` | STRING | Current working directory |

**Supported actions:** script, python, log

**Example rule:**

```toml
[[rules]]
id = "log-stop"
events = ["stop"]
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "Operation interrupted by user"
```

### subagent_stop

Trigger when a subagent (spawned via Task tool) terminates.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "SubagentStop" |
| `stop_hook_active` | BOOLEAN | Whether stop hooks are active |
| `cwd` | STRING | Current working directory |

**Supported actions:** script, python, log

## Memory management events

### pre_compact

Trigger before memory compaction. Use for injecting critical context that must be preserved.

**Input fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | STRING | Session identifier |
| `hook_event_name` | STRING | Always "PreCompact" |
| `trigger` | STRING | What triggered compaction: manual, auto |
| `custom_instructions` | STRING | User's custom compaction instructions |
| `cwd` | STRING | Current working directory |

**Supported actions:** inject, script, python, log

**Output capabilities:**

- `additionalContext`: Critical context to preserve

**Example rule:**

```toml
[[rules]]
id = "preserve-state"
events = ["pre_compact"]
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = "CRITICAL: Project uses Python 3.12+. Never use 'from __future__ import annotations'."
```

## Common input fields

All events receive these common fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | STRING | Yes | Unique session identifier |
| `transcript_path` | STRING | Yes | Path to session transcript file |
| `permission_mode` | STRING | Yes | Permission mode |
| `hook_event_name` | STRING | Yes | Event type name |
| `cwd` | STRING | No | Current working directory |

## Context variable mapping

Hook input fields map to expression context variables:

| Context variable | Input field |
|------------------|-------------|
| `hook_type` | `hook_event_name` |
| `session_id` | `session_id` |
| `cwd` | `cwd` |
| `permission_mode` | `permission_mode` |
| `tool_name` | `tool_name` |
| `tool_input` | `tool_input` |
| `tool_output` | `tool_response` |
| `prompt` | `prompt` |
| `notification` | `{type: notification_type, message: message}` |

## Event selection guidance

Choose events based on your rule's intent:

| Intent | Event(s) | Rationale |
|--------|----------|-----------|
| Block dangerous commands | `pre_tool_use` | Can deny before execution |
| Transform tool inputs | `pre_tool_use` | Can modify inputs |
| Log tool usage | `post_tool_use` | Has access to results |
| Inject project context | `user_prompt_submit`, `session_start` | Early context injection |
| Auto-approve safe operations | `permission_request` | Direct permission control |
| Preserve critical state | `pre_compact` | Context survives compaction |
| Cleanup on exit | `session_end` | Final opportunity for cleanup |
