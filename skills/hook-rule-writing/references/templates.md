---
name: templates
title: Template variable substitution
description: Variable syntax, available context variables, nested path access, and fail-safe behavior for message templates. Load when writing action messages.
principles:
  - Templates provide dynamic content in static configuration
  - Unknown variables resolve to empty strings (fail-safe)
  - Use templates in messages, content, and value fields
  - Keep templates simple—complex logic belongs in conditions or Python actions
best_practices:
  - Verify variable names match context (hook_type, tool_name, etc.)
  - Use nested paths for tool_input fields (tool_input.command)
  - Test templates with representative hook events
  - Include context in log messages for debugging
  - Prefer specific variables over generic ones
checklist:
  - Template syntax uses ${variable} format
  - Variable names are spelled correctly
  - Nested paths use single dot notation (tool_input.field)
  - Templates are in supported fields (message, content, value)
  - Missing variables degrade gracefully
related:
  - conditions.md
  - configuration.md
---

# Template variable substitution

Templates allow dynamic content in action messages using `${variable}` syntax with values from the hook context.

## Syntax

### Basic syntax

Use `${variable}` to insert context values:

```toml
[[hooks.rules.actions]]
type = "warn"
message = "Tool ${tool_name} was used"
```

### Nested paths

Access nested fields with dot notation:

```toml
[[hooks.rules.actions]]
type = "log"
message = "Command: ${tool_input.command}"
```

### Variable pattern

Variables match the pattern: `${identifier}` or `${identifier.field}`

- Identifier: starts with letter or underscore, followed by letters, digits, or underscores
- Field: same rules as identifier
- Maximum nesting depth: one level (`tool_input.command`, not `tool_input.foo.bar`)

## Available variables

### Core context variables

| Variable | Type | Description |
|:---------|:-----|:------------|
| `${hook_type}` | string | Event type: `pre_tool_use`, `post_tool_use`, etc. |
| `${session_id}` | string | Claude session identifier |
| `${cwd}` | string | Current working directory |
| `${permission_mode}` | string | Permission mode |
| `${timestamp}` | string | ISO 8601 event timestamp |

### Tool context variables

Available for tool-related events (`pre_tool_use`, `post_tool_use`):

| Variable | Type | Description |
|:---------|:-----|:------------|
| `${tool_name}` | string | Name of the tool |
| `${tool_input}` | object | Tool input (use nested paths) |
| `${tool_output}` | object | Tool response (post_tool_use only) |

### Prompt context variables

Available for `user_prompt_submit` event:

| Variable | Type | Description |
|:---------|:-----|:------------|
| `${prompt}` | string | User prompt text |

### Git context variables

Available when git context is present:

| Variable | Type | Description |
|:---------|:-----|:------------|
| `${git_branch}` | string | Current branch name |
| `${git_is_dirty}` | bool | Has uncommitted changes |
| `${git_head_commit}` | string | HEAD commit SHA |
| `${git_is_detached}` | bool | HEAD is detached |

## Nested path access

### Tool input fields

Access tool input fields using dot notation:

```toml
# Bash tool
message = "Command: ${tool_input.command}"

# Read tool
message = "Reading file: ${tool_input.file_path}"

# Write tool
message = "Writing to: ${tool_input.file_path}"

# Edit tool
message = "Editing: ${tool_input.file_path}"

# Glob tool
message = "Pattern: ${tool_input.pattern}"

# Grep tool
message = "Searching for: ${tool_input.pattern} in ${tool_input.path}"
```

### Common tool_input fields by tool

**Bash:**

- `${tool_input.command}` - Shell command

**Read:**

- `${tool_input.file_path}` - File path

**Write:**

- `${tool_input.file_path}` - File path
- `${tool_input.content}` - Content (may be large)

**Edit:**

- `${tool_input.file_path}` - File path
- `${tool_input.old_string}` - Text to replace
- `${tool_input.new_string}` - Replacement text

**Glob:**

- `${tool_input.pattern}` - Glob pattern
- `${tool_input.path}` - Search path

**Grep:**

- `${tool_input.pattern}` - Search pattern
- `${tool_input.path}` - Search path

## Usage in action fields

### Message field

Most common usage for user-facing messages:

```toml
[[hooks.rules.actions]]
type = "deny"
message = "Cannot execute ${tool_input.command} - operation not allowed"

[[hooks.rules.actions]]
type = "warn"
message = "Writing to ${tool_input.file_path} outside project directory"

[[hooks.rules.actions]]
type = "log"
level = "info"
message = "[${timestamp}] ${tool_name}: ${tool_input.file_path}"
```

### Content field

For inject actions:

```toml
[[hooks.rules.actions]]
type = "inject"
content = "Note: This operation was triggered from ${cwd} on branch ${git_branch}"
```

### Value field

For modify and transform actions:

```toml
[[hooks.rules.actions]]
type = "transform"
field = "tool_input.command"
value = "echo 'Modified from: ${tool_input.command}'"
```

## Fail-safe behavior

### Unknown variables

Unknown variables resolve to empty strings:

```toml
message = "Value: ${nonexistent_variable}"
# Result: "Value: "
```

### Missing nested fields

Missing nested fields resolve to empty strings:

```toml
message = "Field: ${tool_input.nonexistent_field}"
# Result: "Field: "
```

### Null values

Null values resolve to empty strings:

```toml
# If git context is not available
message = "Branch: ${git_branch}"
# Result: "Branch: "
```

### Design rationale

Fail-safe behavior ensures:

- Templates never cause rule failures
- Partial information is better than errors
- Configuration remains resilient to context variations

## Template examples

### Comprehensive logging

```toml
[[hooks.rules]]
id = "detailed-tool-log"
events = ["post_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "info"
message = "[${timestamp}] Session ${session_id}: ${tool_name} in ${cwd}"
```

### Security warnings

```toml
[[hooks.rules]]
id = "warn-external-command"
events = ["pre_tool_use"]
priority = "high"
condition = 'tool_name == "Bash" and tool_input.command =~ "curl|wget"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "External network request: ${tool_input.command}"
```

### Path-based messages

```toml
[[hooks.rules]]
id = "block-system-files"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Write" and
tool_input.file_path =~ "^/(etc|usr|var)/"
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Cannot write to system path: ${tool_input.file_path}"
```

### Git-aware messages

```toml
[[hooks.rules]]
id = "warn-dirty-push"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command =~ "git\\s+push" and
git_is_dirty == true
'''
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Pushing with uncommitted changes on branch ${git_branch}"
```

### Multi-field messages

```toml
[[hooks.rules]]
id = "log-edit-operations"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Edit"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "info"
message = "Edit: ${tool_input.file_path} - replaced '${tool_input.old_string}' with '${tool_input.new_string}'"
```

## Escaping and special characters

### Literal dollar signs

To include a literal `$` followed by `{`, use `$${`:

```toml
message = "Price: $${amount}"
# Result: "Price: ${amount}" (literal)
```

### Quotes in messages

TOML strings handle quotes:

```toml
# Single quotes in double-quoted string
message = "File '${tool_input.file_path}' was modified"

# Double quotes in literal string
message = 'File "${tool_input.file_path}" was modified'
```

### Multi-line messages

Use TOML multi-line strings:

```toml
[[hooks.rules.actions]]
type = "log"
message = """
Tool: ${tool_name}
Path: ${tool_input.file_path}
Time: ${timestamp}
"""
```

## Debugging templates

### Verify variable availability

Check that variables exist in the hook event type:

- `tool_input` only available in tool events
- `prompt` only available in `user_prompt_submit`
- `git_*` only available when git context present

### Test with logging

Add temporary log actions to verify template output:

```toml
[[hooks.rules]]
id = "debug-template"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Write"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "debug"
message = "DEBUG: tool_name=${tool_name} file_path=${tool_input.file_path}"
```

### Common issues

**Empty output**: Variable name misspelled or not available for event type.

**Literal ${...} in output**: Variable pattern not recognized (check syntax).

**Partial output**: Nested path incorrect or field missing.
