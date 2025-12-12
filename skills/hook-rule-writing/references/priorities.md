---
name: priorities
title: Priority system and rule ordering
description: Priority levels, evaluation order, terminal flag behavior, and guidelines for selecting appropriate priorities. Load when designing rule precedence.
principles:
  - Use the minimum priority level that achieves the goal
  - Reserve critical priority for security and safety rules only
  - Use terminal flag sparingly—most rules should allow continued evaluation
  - Consider rule interaction when assigning priorities
best_practices:
  - Start with medium priority and adjust based on testing
  - Use critical only for rules that must never be overridden
  - Group related rules at the same priority level
  - Document why non-default priorities are chosen
  - Test priority interactions with overlapping conditions
checklist:
  - Priority level matches rule importance
  - Terminal flag is only set when evaluation must stop
  - Critical rules are security/safety related
  - Rule order within same priority is intentional
  - Priority selection is documented in rule description
related:
  - conditions.md
  - configuration.md
---

# Priority system and rule ordering

The priority system controls which rules evaluate first and whether evaluation continues after a match.

## Priority levels

Four priority levels determine evaluation order:

| Priority | String Value | Numeric Value | Evaluation Order |
|:---------|:-------------|:-------------:|:----------------:|
| Critical | `"critical"` | 0 | First (highest) |
| High | `"high"` | 1 | Second |
| Medium | `"medium"` | 2 | Third (default) |
| Low | `"low"` | 3 | Last (lowest) |

Rules evaluate in priority order. Within the same priority level, rules evaluate in definition order (the order they appear in configuration files).

## Setting priority

Specify priority in the rule configuration:

```toml
[[hooks.rules]]
id = "security-check"
events = ["pre_tool_use"]
priority = "critical"  # Evaluates first
condition = 'tool_name == "Bash" and tool_input.command =~ "sudo"'
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "sudo commands are not allowed"
```

If omitted, priority defaults to `"medium"`:

```toml
[[hooks.rules]]
id = "log-writes"
events = ["post_tool_use"]
# priority defaults to "medium"
condition = 'tool_name == "Write"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
message = "File written: ${tool_input.file_path}"
```

## Rule ordering

### Priority-based ordering

Rules sort by priority first:

```toml
# Evaluates third (medium priority, default)
[[hooks.rules]]
id = "rule-a"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash"'
# ...

# Evaluates first (critical priority)
[[hooks.rules]]
id = "rule-b"
events = ["pre_tool_use"]
priority = "critical"
condition = 'tool_name == "Bash"'
# ...

# Evaluates second (high priority)
[[hooks.rules]]
id = "rule-c"
events = ["pre_tool_use"]
priority = "high"
condition = 'tool_name == "Bash"'
# ...
```

Evaluation order: `rule-b` (critical), `rule-c` (high), `rule-a` (medium).

### Definition order within priority

Rules at the same priority level evaluate in definition order:

```toml
# Evaluates first among medium-priority rules
[[hooks.rules]]
id = "medium-first"
events = ["pre_tool_use"]
priority = "medium"
condition = 'tool_name == "Write"'
# ...

# Evaluates second among medium-priority rules
[[hooks.rules]]
id = "medium-second"
events = ["pre_tool_use"]
priority = "medium"
condition = 'tool_name == "Write"'
# ...
```

## Terminal flag

The `terminal` flag stops rule evaluation when a rule matches:

```toml
[[hooks.rules]]
id = "allow-read-operations"
events = ["pre_tool_use"]
priority = "high"
terminal = true  # Stop evaluation if this rule matches
condition = 'tool_name == "Read"'
result = "ok"

[[hooks.rules.actions]]
type = "allow"
```

### Default behavior

By default, `terminal = false`. All matching rules execute their actions.

### When to use terminal

Use `terminal = true` when:

- An allow rule should bypass all subsequent checks
- A block rule should prevent any further processing
- Optimization requires skipping unnecessary rules

```toml
# Terminal allow for safe operations
[[hooks.rules]]
id = "allow-safe-reads"
events = ["pre_tool_use"]
priority = "high"
terminal = true
condition = 'tool_name == "Read" and $is_path_under(tool_input.file_path, cwd)'
result = "ok"

[[hooks.rules.actions]]
type = "allow"
```

### Terminal with blocking rules

Critical security rules often use terminal to ensure immediate blocking:

```toml
[[hooks.rules]]
id = "block-system-access"
events = ["pre_tool_use"]
priority = "critical"
terminal = true  # Stop immediately on match
condition = '''
tool_name == "Bash" and
tool_input.command =~ "^(rm -rf /|dd if=|mkfs)"
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "System-damaging command blocked"
```

## When to use each priority level

### Critical priority

Use for rules that must always evaluate first and should rarely be overridden:

- Security boundaries (blocking dangerous commands)
- Safety checks (preventing data loss)
- Compliance requirements (audit logging)

```toml
[[hooks.rules]]
id = "block-credential-exposure"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and
tool_input.command =~ "(curl|wget).*(-d|--data).*password"
'''
result = "block"
terminal = true

[[hooks.rules.actions]]
type = "deny"
message = "Potential credential exposure in command"
```

### High priority

Use for important rules that should evaluate early but may be overridden:

- Permission checks
- Path restrictions
- Resource limits

```toml
[[hooks.rules]]
id = "restrict-external-writes"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write" and
not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Cannot write outside project: ${tool_input.file_path}"
```

### Medium priority (default)

Use for standard operational rules:

- Logging and monitoring
- Warnings and suggestions
- Default behaviors

```toml
[[hooks.rules]]
id = "warn-large-file-read"
events = ["pre_tool_use"]
priority = "medium"
condition = 'tool_name == "Read"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Reading file: ${tool_input.file_path}"
```

### Low priority

Use for optional or fallback rules:

- Analytics and metrics
- Non-critical logging
- Catch-all handlers

```toml
[[hooks.rules]]
id = "log-all-tool-use"
events = ["post_tool_use"]
priority = "low"
condition = "true"  # Always matches
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "debug"
message = "Tool used: ${tool_name}"
```

## Priority selection examples

### Security-first pattern

Layer security rules from critical to low:

```toml
# Critical: Hard blocks that cannot be bypassed
[[hooks.rules]]
id = "block-rm-root"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = 'tool_name == "Bash" and tool_input.command =~ "rm\\s+-rf\\s+/"'
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Removing root directory is forbidden"

# High: Require confirmation for risky operations
[[hooks.rules]]
id = "warn-sudo"
events = ["pre_tool_use"]
priority = "high"
condition = 'tool_name == "Bash" and tool_input.command =~ "sudo"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "sudo command requires explicit approval"

# Medium: Standard logging
[[hooks.rules]]
id = "log-bash"
events = ["post_tool_use"]
priority = "medium"
condition = 'tool_name == "Bash"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
message = "Command executed: ${tool_input.command}"
```

### Allow-list pattern

Use high-priority terminal allows with low-priority catch-all blocks:

```toml
# High: Explicitly allow safe operations
[[hooks.rules]]
id = "allow-project-writes"
events = ["pre_tool_use"]
priority = "high"
terminal = true
condition = '''
tool_name == "Write" and
$is_path_under(tool_input.file_path, cwd) and
not (tool_input.file_path =~ "\\.env")
'''
result = "ok"

[[hooks.rules.actions]]
type = "allow"

# Low: Block everything else
[[hooks.rules]]
id = "block-other-writes"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Write"'
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Write not in allow-list: ${tool_input.file_path}"
```

## Debugging priority issues

### Check effective rule order

Rules load from multiple sources with precedence. Later sources can override earlier rules with the same ID:

1. Built-in hooks (lowest)
2. User config
3. Project hooks.toml
4. Project drop-in files
5. Project inline rules
6. Local overrides
7. Worktree config (highest)

### Common issues

**Rules not firing**: Check that priority is not lower than a terminal rule that matches first.

**Wrong rule winning**: Verify priority levels and definition order.

**Actions accumulating**: Ensure terminal flag is set when evaluation should stop.
