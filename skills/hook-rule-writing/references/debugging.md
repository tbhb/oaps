---
name: debugging
title: Debugging and troubleshooting
description: CLI commands for testing, debugging, and validating hook rules. Includes reading structured logs, common errors, and debugging strategies.
commands:
  oaps hooks test: Test which rules match a given hook input
  oaps hooks test --event pre_tool_use: Test with specific event type
  oaps hooks test --rule my-rule-id: Test specific rule only
  oaps hooks test --input test.json: Test with custom input JSON
  oaps hooks debug <rule-id>: Show detailed information about a rule
  oaps hooks debug <rule-id> --event pre_tool_use: Debug with simulated event
  oaps hooks debug <rule-id> -v: Show context variables
  oaps hooks validate: Validate all hook rule configurations
  oaps hooks validate --config file.toml: Validate specific config file
  oaps hooks list: List all configured hook rules
  oaps hooks list --event pre_tool_use: List rules for specific event
  oaps hooks list -v: Show detailed rule information
principles:
  - Use CLI commands to test rules before deployment
  - Check structured logs for runtime behavior
  - Validate expression syntax before testing conditions
  - Isolate issues by testing conditions and actions separately
best_practices:
  - "**Test incrementally**: Start with minimal input, add complexity gradually"
  - "**Validate first**: Run oaps hooks validate before testing"
  - "**Check event matching**: Verify rule events match the hook event type"
  - "**Use debug mode**: Run oaps hooks debug for detailed expression evaluation"
  - "**Review logs**: Check ~/.oaps/logs/hooks.log for runtime errors"
  - "**Test both paths**: Verify rules match when expected AND do not match otherwise"
checklist:
  - Rule ID exists and is correctly specified
  - Expression syntax is valid (oaps hooks validate passes)
  - Event type matches rule's events list
  - Condition evaluates to expected boolean
  - Actions are supported for the chosen event type
  - Rule is enabled (enabled = true or omitted)
related:
  - configuration
  - expressions
  - functions
---

## CLI commands

### oaps hooks test

Test which rules match a given hook input. Use for verifying rule conditions before deployment.

```bash
# Test with default pre_tool_use event (creates minimal input)
oaps hooks test

# Test with specific event type
oaps hooks test --event user_prompt_submit
oaps hooks test -e post_tool_use

# Test specific rule only
oaps hooks test --rule my-rule-id
oaps hooks test -r block-force-push

# Test with custom input JSON file
oaps hooks test --event pre_tool_use --input test_input.json

# Test with piped JSON input
echo '{"session_id": "test", "tool_name": "Bash", ...}' | oaps hooks test -e pre_tool_use

# Output as JSON
oaps hooks test --format json
```

**Exit codes:**

| Code | Description |
|------|-------------|
| 0 | Test completed successfully |
| 1 | Failed to load configuration files |
| 3 | Specified rule ID not found |
| 4 | Invalid input JSON |

### oaps hooks debug

Debug a specific hook rule with detailed information.

```bash
# Show rule details and validate expression
oaps hooks debug my-rule-id

# Debug with simulated event (tests event matching)
oaps hooks debug my-rule-id --event pre_tool_use

# Debug with custom input (evaluates condition)
oaps hooks debug my-rule-id --event pre_tool_use --input test.json

# Show context variables available to the expression
oaps hooks debug my-rule-id --event pre_tool_use -v
```

**Output sections:**

1. **RULE DETAILS**: Full rule configuration
2. **EXPRESSION VALIDATION**: Syntax check result
3. **EVENT MATCHING**: Whether rule events include the test event
4. **CONDITION EVALUATION**: Expression result against input
5. **SUMMARY**: Quick status overview

### oaps hooks validate

Validate all hook rule configurations for syntax and schema errors.

```bash
# Validate all rules from all sources
oaps hooks validate

# Validate specific config file
oaps hooks validate --config .oaps/hooks.d/security.toml

# Show detailed output including validated rules
oaps hooks validate --verbose

# Output as JSON
oaps hooks validate --format json
```

**Validates:**

- TOML syntax
- Pydantic schema validation
- Condition expression syntax
- Action configuration requirements

### oaps hooks list

List all configured hook rules.

```bash
# List all rules in table format
oaps hooks list

# Filter by event type
oaps hooks list --event pre_tool_use
oaps hooks list -e post_tool_use

# Filter by priority
oaps hooks list --priority high
oaps hooks list -p critical

# Show only enabled rules
oaps hooks list --enabled-only

# Show detailed information
oaps hooks list -v

# Output as JSON or YAML
oaps hooks list --format json
oaps hooks list --format yaml
```

## Reading hook logs

Hook execution logs are written to `~/.oaps/logs/hooks.log` using structured JSON format.

### Log file location

```bash
# Default location
~/.oaps/logs/hooks.log

# View recent entries
tail -f ~/.oaps/logs/hooks.log | jq .

# Filter by event type
cat ~/.oaps/logs/hooks.log | jq 'select(.hook_event == "pre_tool_use")'

# Filter by session
cat ~/.oaps/logs/hooks.log | jq 'select(.session_id == "your-session-id")'
```

### Log entry structure

```json
{
  "timestamp": "2024-12-17T10:30:00.000000Z",
  "level": "info",
  "event": "hook_started",
  "hook_event": "pre_tool_use",
  "session_id": "abc-123",
  "logger": "oaps.hooks"
}
```

### Key log events

| Event | Level | Description |
|-------|-------|-------------|
| `hook_started` | info | Hook execution began |
| `hook_input` | info | Input received (sanitized) |
| `hook_input_full` | debug | Full input JSON |
| `hook_completed` | info | Hook finished successfully |
| `hook_blocked` | warning | Hook blocked the operation |
| `hook_failed` | error | Hook execution failed |

### Enable debug logging

Set the log level in your configuration:

```toml
# .oaps/oaps.toml
[hooks]
log_level = "debug"
```

Or use environment variable:

```bash
export OAPS_HOOKS__LOG_LEVEL=debug
```

## Common errors

### Expression syntax errors

**Error:** `Invalid expression syntax: ...`

**Cause:** The condition expression has syntax errors.

**Fix:**

```bash
# Validate the rule
oaps hooks validate

# Check expression syntax in debug output
oaps hooks debug my-rule-id
```

**Common syntax issues:**

```toml
# Wrong: Missing quotes around string
condition = 'tool_name == Bash'

# Correct: Strings must be quoted
condition = 'tool_name == "Bash"'

# Wrong: Using = instead of ==
condition = 'tool_name = "Bash"'

# Correct: Use == for equality
condition = 'tool_name == "Bash"'

# Wrong: Invalid function call
condition = '$is_path_under(tool_input.file_path)'

# Correct: Function requires two arguments
condition = '$is_path_under(tool_input.file_path, cwd)'
```

### Invalid action configuration

**Error:** `'python' requires entrypoint, command, or script`

**Cause:** Execution action missing required field.

**Fix:**

```toml
# Wrong: Missing execution field
[[rules.actions]]
type = "python"
timeout_ms = 5000

# Correct: Include entrypoint
[[rules.actions]]
type = "python"
entrypoint = "myproject.hooks:handler"
timeout_ms = 5000
```

**Error:** `Action type 'deny' should have a message`

**Cause:** Warning for missing message on permission action.

**Fix:**

```toml
# Add message for user feedback
[[rules.actions]]
type = "deny"
message = "Operation blocked: ${tool_name}"
```

### Rule not matching when expected

**Symptoms:** Rule does not trigger when it should.

**Debugging steps:**

1. Check event type:

   ```bash
   oaps hooks debug my-rule-id --event pre_tool_use
   ```

   Verify "MATCHES" in EVENT MATCHING section.

2. Check rule is enabled:

   ```bash
   oaps hooks list --enabled-only | grep my-rule-id
   ```

3. Evaluate condition with input:

   ```bash
   oaps hooks debug my-rule-id --event pre_tool_use --input test.json -v
   ```

   Check "Expression evaluated to: true/false" in CONDITION EVALUATION.

4. Verify context variables:

   ```bash
   oaps hooks debug my-rule-id --event pre_tool_use -v
   ```

   Review "Context variables available" section.

**Common causes:**

```toml
# Wrong: Event type not in rule's events list
events = ["post_tool_use"]
# But testing with pre_tool_use event

# Wrong: Condition too specific
condition = 'tool_input.command == "git push"'
# Fails for "git push origin main"

# Correct: Use pattern matching
condition = 'tool_input.command.starts_with("git push")'
```

### Rule matching when not expected

**Symptoms:** Rule triggers unexpectedly.

**Debugging steps:**

1. Check condition is not empty:

   ```toml
   # Empty condition always matches!
   condition = ''
   ```

2. Test with actual input:

   ```bash
   oaps hooks test --event pre_tool_use --input actual_input.json
   ```

3. Review condition logic:

   ```toml
   # Wrong: Missing "not" or incorrect operator
   condition = 'tool_name == "Bash" or true'  # Always true!

   # Correct: Proper boolean logic
   condition = 'tool_name == "Bash" and tool_input.command =~~ "sudo"'
   ```

## Debugging strategies

### Isolate the problem

Test components independently:

```bash
# 1. Validate syntax
oaps hooks validate

# 2. Check rule loads correctly
oaps hooks list | grep my-rule-id

# 3. Test event matching
oaps hooks debug my-rule-id --event pre_tool_use

# 4. Test condition evaluation
oaps hooks debug my-rule-id --event pre_tool_use --input test.json

# 5. Test full rule matching
oaps hooks test --rule my-rule-id --event pre_tool_use --input test.json
```

### Create minimal test cases

Start with the simplest possible input:

```json
{
  "session_id": "test-session",
  "transcript_path": "/tmp/test.json",
  "permission_mode": "default",
  "cwd": "/path/to/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "echo test"},
  "tool_use_id": "test-id"
}
```

Gradually add complexity until the issue manifests.

### Use verbose output

Enable verbose mode for detailed information:

```bash
# Debug command with verbose
oaps hooks debug my-rule-id --event pre_tool_use -v

# List with verbose
oaps hooks list -v

# Validate with verbose
oaps hooks validate --verbose
```

### Check precedence

Later configuration sources override earlier ones:

```bash
# List rules showing source files
oaps hooks list -v

# Check which file defines the rule
oaps hooks debug my-rule-id
# Look at "Source file" in RULE DETAILS
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `OAPS_HOOKS__DROPIN_DIR` | Override drop-in directory path |
| `OAPS_HOOKS__LOG_LEVEL` | Set log level (debug, info, warning, error) |
| `OAPS_HOOKS__LOG_MAX_BYTES` | Maximum log file size before rotation |
| `OAPS_HOOKS__LOG_BACKUP_COUNT` | Number of rotated log files to keep |

```bash
# Enable debug logging for a single run
OAPS_HOOKS__LOG_LEVEL=debug oaps hooks test --event pre_tool_use

# Use custom drop-in directory
OAPS_HOOKS__DROPIN_DIR=/custom/hooks.d oaps hooks list
```
