---
name: actions
title: Action types
description: All 11 hook action types for permission control, context injection, and automation. Load when configuring rule actions.
commands: {}
principles:
  - Match action type to rule intent - deny for blocking, warn for guidance
  - Use fail-open semantics - automation errors should not block operations
  - Prefer declarative actions over scripts when possible
best_practices:
  - "**Use deny for hard blocks**: Stop dangerous operations completely"
  - "**Use warn/suggest for guidance**: Provide non-blocking feedback"
  - "**Use inject for context**: Add information without modifying behavior"
  - "**Use modify for input transformation**: Change tool inputs declaratively"
  - "**Use transform for complex transformations**: Run scripts when modify is insufficient"
  - "**Use log for telemetry**: Record events without affecting execution"
checklist:
  - Action type is supported by the chosen event
  - Required fields are provided
  - Message templates use correct ${var} syntax
  - Timeouts are set for long-running scripts
related:
  - events
  - expressions
---

## Action categories

| Category   | Action types                       | Purpose                                |
|------------|------------------------------------|----------------------------------------|
| Permission | `deny`, `allow`, `warn`, `suggest` | Control execution and provide feedback |
| Context    | `inject`, `modify`, `transform`    | Add or modify context and inputs       |
| Automation | `script`, `python`, `log`          | Execute code and record events         |

## Permission actions

### deny

Block the operation and stop processing.

**Purpose:** Prevent dangerous or disallowed operations from executing.

**Supported events:** `pre_tool_use`, `permission_request`, `user_prompt_submit`

**Behavior by event:**

- `pre_tool_use`: Sets `permissionDecision="deny"` and raises BlockHook
- `permission_request`: Sets deny decision and raises BlockHook
- Other hooks: Raises BlockHook with the message

**Required fields:** None

**Optional fields:**

| Field       | Type    | Default                         | Description                         |
|-------------|---------|---------------------------------|-------------------------------------|
| `message`   | STRING  | "Operation denied by hook rule" | Message template explaining denial  |
| `interrupt` | BOOLEAN | true                            | Whether to interrupt the agent loop |

**Example:**

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
message = "Force push blocked. Use --force-with-lease instead."
```

```toml
[[rules]]
id = "block-rm-rf"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "rm\\s+-rf\\s+/"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Dangerous rm -rf command blocked: ${tool_input.command}"
```

### allow

Explicitly allow the operation.

**Purpose:** Auto-approve safe operations without user confirmation.

**Supported events:** `pre_tool_use`, `permission_request`

**Behavior by event:**

- `pre_tool_use`: Sets `permissionDecision="allow"`
- `permission_request`: Sets allow decision
- Other hooks: No-op

**Required fields:** None

**Optional fields:** None (message is ignored)

**Example:**

```toml
[[rules]]
id = "auto-approve-tests"
events = ["permission_request"]
condition = '''
tool_name == "Bash"
and (
    tool_input.command.starts_with("pytest")
    or tool_input.command.starts_with("uv run pytest")
)
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

```toml
[[rules]]
id = "allow-read-project-files"
events = ["permission_request"]
condition = '''
tool_name == "Read" and $is_path_under(tool_input.file_path, cwd)
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### warn

Add a warning message without blocking.

**Purpose:** Provide cautionary feedback while allowing the operation to proceed.

**Supported events:** All events

**Behavior:** Adds the rendered message to `system_messages`. Does NOT block execution or set permission decisions.

**Required fields:**

| Field     | Type   | Description              |
|-----------|--------|--------------------------|
| `message` | STRING | Warning message template |

**Optional fields:** None

**Example:**

```toml
[[rules]]
id = "warn-sudo"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "sudo"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Using sudo. Ensure this is intentional and necessary."
```

```toml
[[rules]]
id = "warn-main-branch"
events = ["pre_tool_use"]
condition = '''
$current_branch() == "main"
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "You are committing directly to main branch."
```

### suggest

Provide a suggestion without blocking.

**Purpose:** Offer guidance or recommendations while allowing the operation to proceed.

**Supported events:** All events

**Behavior:** Adds the rendered message to `system_messages`. Semantically similar to `warn` but intended for guidance rather than caution.

**Required fields:**

| Field     | Type   | Description                 |
|-----------|--------|-----------------------------|
| `message` | STRING | Suggestion message template |

**Optional fields:** None

**Example:**

```toml
[[rules]]
id = "suggest-type-hints"
events = ["post_tool_use"]
condition = '''
tool_name == "Write"
and tool_input.file_path.ends_with(".py")
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Remember to add type hints to new functions."
```

## Context actions

### inject

Inject additional context into hook output.

**Purpose:** Add information to the conversation without modifying tool behavior.

**Supported events:** `session_start`, `post_tool_use`, `pre_compact`, `user_prompt_submit`

**Behavior:** Adds content to the `additionalContext` field. For unsupported hook types, logs a warning and continues (fail-open).

**Required fields:**

| Field     | Type   | Description                |
|-----------|--------|----------------------------|
| `content` | STRING | Content template to inject |

**Optional fields:**

| Field     | Type   | Description                                      |
|-----------|--------|--------------------------------------------------|
| `message` | STRING | Fallback for `content` (backwards compatibility) |

**Example:**

```toml
[[rules]]
id = "welcome-context"
events = ["session_start"]
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Project: OAPS
Commands: just test, just lint, just format
Python: 3.12+ (NEVER use 'from __future__ import annotations')
"""
```

```toml
[[rules]]
id = "deploy-context"
events = ["user_prompt_submit"]
condition = 'prompt.as_lower =~~ "deploy"'
result = "ok"

[[rules.actions]]
type = "inject"
content = "Deployment requires approval. See DEPLOY.md for procedures."
```

### modify

Modify tool input fields declaratively.

**Purpose:** Transform tool inputs using declarative operations.

**Supported events:** `pre_tool_use`, `permission_request`

**Behavior:** Applies the specified operation to the target field and stores the result in `updated_input`.

**Required fields:**

| Field       | Type   | Description                                      |
|-------------|--------|--------------------------------------------------|
| `field`     | STRING | Target field path (dot notation for nested)      |
| `operation` | STRING | Operation: "set", "append", "prepend", "replace" |

**Optional fields:**

| Field     | Type   | Description                               |
|-----------|--------|-------------------------------------------|
| `value`   | STRING | New value or content (supports templates) |
| `pattern` | STRING | Regex pattern for "replace" operation     |

**Operations:**

| Operation | Description                        | Requires           |
|-----------|------------------------------------|--------------------|
| `set`     | Replace field value entirely       | `value`            |
| `append`  | Add to end of string field         | `value`            |
| `prepend` | Add to beginning of string field   | `value`            |
| `replace` | Regex substitution on string field | `pattern`, `value` |

**Example:**

```toml
[[rules]]
id = "add-dry-run"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash"
and tool_input.command.starts_with("rm")
and not tool_input.command =~~ "--dry-run"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " --dry-run"
```

```toml
[[rules]]
id = "replace-force-push"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "--force"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "replace"
pattern = "--force"
value = "--force-with-lease"
```

```toml
[[rules]]
id = "set-timeout"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.timeout == null
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "timeout"
operation = "set"
value = "60000"
```

### transform

Transform tool inputs via script or Python code.

**Purpose:** Complex transformations that cannot be expressed with `modify`.

**Supported events:** `pre_tool_use`, `permission_request`

**Behavior:** Execute the configured script or Python function, parse JSON output, and merge `transform_input` into the accumulator's `updated_input`.

**Required fields (one of):**

| Field        | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `entrypoint` | STRING | Python function as `module.path:function_name` |
| `command`    | STRING | Shell command to execute                       |
| `script`     | STRING | Multi-line shell script                        |

**Optional fields:**

| Field        | Type    | Default  | Description             |
|--------------|---------|----------|-------------------------|
| `timeout_ms` | INTEGER | 10000    | Timeout in milliseconds |
| `cwd`        | STRING  | hook cwd | Working directory       |
| `env`        | MAPPING | {}       | Environment variables   |
| `shell`      | STRING  | /bin/sh  | Shell interpreter       |

**Return value:** JSON object with `transform_input` key containing field modifications:

```json
{
  "transform_input": {
    "command": "modified command"
  }
}
```

**Example:**

```toml
[[rules]]
id = "transform-command"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command.starts_with("npm")
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "my_hooks.transforms:npm_to_pnpm"
timeout_ms = 5000
```

Python function:

```python
def npm_to_pnpm(context):
    command = context.hook_input.tool_input.get("command", "")
    if command.startswith("npm "):
        command = "pnpm " + command[4:]
    return {"transform_input": {"command": command}}
```

## Automation actions

### script

Execute a shell script.

**Purpose:** Run external commands for side effects (logging, notifications, etc.).

**Supported events:** All events

**Behavior:** Execute the command or script, optionally passing hook context as JSON on stdin. Process return value for permission decisions or context injection.

**Required fields (one of):**

| Field     | Type   | Description              |
|-----------|--------|--------------------------|
| `command` | STRING | Shell command to execute |
| `script`  | STRING | Multi-line shell script  |

**Optional fields:**

| Field        | Type    | Default  | Description                                            |
|--------------|---------|----------|--------------------------------------------------------|
| `timeout_ms` | INTEGER | 10000    | Timeout in milliseconds                                |
| `cwd`        | STRING  | hook cwd | Working directory                                      |
| `env`        | MAPPING | {}       | Environment variables                                  |
| `shell`      | STRING  | /bin/sh  | Shell interpreter                                      |
| `stdin`      | STRING  | "none"   | Input type: "none" or "json"                           |
| `stdout`     | STRING  | "ignore" | Output handling: "ignore", "log", "append_stop_reason" |
| `stderr`     | STRING  | "ignore" | Error handling: "ignore", "log", "append_to_stdout"    |

**Return value:** JSON object for permission decisions or context:

```json
{
  "deny": true,
  "deny_message": "Operation blocked",
  "inject": "Additional context"
}
```

**Example:**

```toml
[[rules]]
id = "notify-deploy"
events = ["post_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "deploy"
'''
result = "ok"

[[rules.actions]]
type = "script"
command = "curl -X POST https://hooks.slack.com/... -d '{\"text\": \"Deploy triggered\"}'"
timeout_ms = 5000
```

```toml
[[rules]]
id = "custom-validation"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash"
'''
result = "ok"

[[rules.actions]]
type = "script"
stdin = "json"
script = """
#!/bin/bash
# Read JSON input
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# Custom validation logic
if [[ "$command" == *"dangerous"* ]]; then
    echo '{"deny": true, "deny_message": "Command contains dangerous pattern"}'
fi
"""
```

### python

Execute a Python function in-process.

**Purpose:** Run Python code for complex logic, validation, or side effects.

**Supported events:** All events

**Behavior:** Import and execute the specified Python function with the hook context. Process return value for permission decisions or context injection.

**Required fields:**

| Field        | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `entrypoint` | STRING | Python function as `module.path:function_name` |

**Optional fields:**

| Field        | Type    | Default | Description             |
|--------------|---------|---------|-------------------------|
| `timeout_ms` | INTEGER | 10000   | Timeout in milliseconds |

**Function signature:**

```python
def hook_function(context: HookContext) -> dict | None:
    ...
```

**Return value:** Dictionary with optional keys:

| Key               | Type    | Description               |
|-------------------|---------|---------------------------|
| `deny`            | BOOLEAN | Set to true to deny       |
| `deny_message`    | STRING  | Reason for denial         |
| `allow`           | BOOLEAN | Set to true to allow      |
| `inject`          | STRING  | Context to inject         |
| `warn`            | STRING  | Warning message           |
| `transform_input` | MAPPING | Input field modifications |

**Example:**

```toml
[[rules]]
id = "custom-python-validation"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash"
'''
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.validators:validate_bash_command"
timeout_ms = 5000
```

Python function:

```python
def validate_bash_command(context):
    command = context.hook_input.tool_input.get("command", "")

    # Block commands with certain patterns
    dangerous_patterns = ["rm -rf /", ":(){ :|:& };:"]
    for pattern in dangerous_patterns:
        if pattern in command:
            return {
                "deny": True,
                "deny_message": f"Dangerous pattern detected: {pattern}"
            }

    # Warn about sudo
    if "sudo" in command:
        return {"warn": "Using sudo - ensure this is necessary"}

    return None
```

### log

Write a structured log entry.

**Purpose:** Record events without affecting execution.

**Supported events:** All events

**Behavior:** Write a log entry at the specified level with the rendered message.

**Required fields:**

| Field     | Type   | Description          |
|-----------|--------|----------------------|
| `message` | STRING | Log message template |

**Optional fields:**

| Field   | Type   | Default | Description                                    |
|---------|--------|---------|------------------------------------------------|
| `level` | STRING | "info"  | Log level: "debug", "info", "warning", "error" |

**Example:**

```toml
[[rules]]
id = "log-tool-use"
events = ["pre_tool_use"]
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Tool: ${tool_name}, Input: ${tool_input}"
```

```toml
[[rules]]
id = "log-dangerous-commands"
events = ["pre_tool_use"]
condition = '''
tool_name == "Bash" and tool_input.command =~~ "sudo|rm\\s+-rf"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "Potentially dangerous command: ${tool_input.command}"
```

## Action support by event

| Event                | deny | allow | warn | suggest | inject | modify | transform | script | python | log |
|----------------------|------|-------|------|---------|--------|--------|-----------|--------|--------|-----|
| `pre_tool_use`       | Y    | Y     | Y    | Y       | Y      | Y      | Y         | Y      | Y      | Y   |
| `post_tool_use`      | -    | -     | Y    | Y       | Y      | -      | -         | Y      | Y      | Y   |
| `user_prompt_submit` | Y    | -     | Y    | Y       | Y      | -      | -         | Y      | Y      | Y   |
| `permission_request` | Y    | Y     | Y    | Y       | -      | Y      | Y         | Y      | Y      | Y   |
| `notification`       | -    | -     | -    | -       | -      | -      | -         | Y      | Y      | Y   |
| `session_start`      | -    | -     | -    | -       | Y      | -      | -         | Y      | Y      | Y   |
| `session_end`        | -    | -     | -    | -       | -      | -      | -         | Y      | Y      | Y   |
| `stop`               | -    | -     | -    | -       | -      | -      | -         | Y      | Y      | Y   |
| `subagent_stop`      | -    | -     | -    | -       | -      | -      | -         | Y      | Y      | Y   |
| `pre_compact`        | -    | -     | -    | -       | Y      | -      | -         | Y      | Y      | Y   |

## Template syntax

Action fields that support templates (`message`, `content`, `value`) use `${var}` syntax:

```
${tool_name}                    # Context variable
${tool_input.command}           # Nested field
${tool_input.file_path}         # Tool input field
```

**Available variables:**

- All context variables from the event
- `tool_input.*` for tool input fields
- `cwd`, `session_id`, `permission_mode`

## Multiple actions

Rules can have multiple actions that execute in order:

```toml
[[rules]]
id = "warn-and-log"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash" and tool_input.command =~~ "sudo"'
result = "warn"

[[rules.actions]]
type = "log"
level = "warning"
message = "sudo command detected: ${tool_input.command}"

[[rules.actions]]
type = "warn"
message = "Using sudo. Ensure this is necessary."
```

## Fail-open behavior

Automation actions (`script`, `python`, `transform`) use fail-open semantics:

- Errors are logged but do not block the operation
- Timeouts are logged but do not block
- Invalid return values are ignored

This ensures hook errors do not disrupt normal operations.
