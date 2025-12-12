---
name: testing
title: Testing hook rules
description: Unit testing with oaps hooks test, creating test fixtures, testing conditions and actions independently, and integration testing patterns.
commands:
  oaps hooks test: Test which rules match given input
  oaps hooks test --event pre_tool_use: Test with specific event type
  oaps hooks test --rule <id>: Test specific rule only
  oaps hooks test --input <file>: Test with JSON fixture file
  oaps hooks validate: Validate all rules before testing
  oaps hooks debug <id> --event <type>: Debug specific rule evaluation
principles:
  - Test rules before deployment
  - Create fixtures for repeatable testing
  - Test both matching and non-matching cases
  - Validate syntax before testing behavior
  - Test actions separately from conditions
best_practices:
  - "**Validate first**: Run oaps hooks validate before testing behavior"
  - "**Test incrementally**: Start with minimal input, add complexity"
  - "**Test both paths**: Verify match AND non-match cases"
  - "**Use fixtures**: Create reusable JSON test files"
  - "**Test in isolation**: Test one rule at a time with --rule"
  - "**Automate tests**: Include hook tests in CI pipeline"
checklist:
  - oaps hooks validate passes with no errors
  - Rule matches expected inputs (positive test)
  - Rule does not match unexpected inputs (negative test)
  - Actions produce expected behavior
  - Edge cases covered (empty strings, null values, special characters)
  - Tests run in CI before deployment
related:
  - debugging
  - expressions
  - configuration
---

## Unit testing with oaps hooks test

The `oaps hooks test` command simulates hook events and shows which rules match. Use it to verify rule behavior before deployment.

### Basic test workflow

```bash
# 1. Validate syntax
oaps hooks validate

# 2. List rules to find IDs
oaps hooks list

# 3. Test with default input
oaps hooks test

# 4. Test specific rule
oaps hooks test --rule my-rule-id

# 5. Test with custom input
oaps hooks test --rule my-rule-id --input test_input.json
```

### Test specific event types

```bash
# Test pre_tool_use (default)
oaps hooks test --event pre_tool_use

# Test post_tool_use
oaps hooks test --event post_tool_use

# Test user_prompt_submit
oaps hooks test --event user_prompt_submit

# Test permission_request
oaps hooks test --event permission_request

# Test session lifecycle
oaps hooks test --event session_start
oaps hooks test --event session_end
```

### Filter to specific rule

```bash
# Test only the named rule
oaps hooks test --rule block-force-push --event pre_tool_use --input force_push.json

# Useful for isolating behavior
oaps hooks test --rule protect-env-files --event pre_tool_use --input env_access.json
```

### JSON output for automation

```bash
# Output as JSON for scripting
oaps hooks test --format json --input test.json

# Parse with jq
oaps hooks test --format json | jq '.matched_rules[].rule_id'
```

## Creating test input JSON fixtures

Create JSON files that represent hook inputs for testing.

### PreToolUse input structure

```json
{
  "session_id": "test-session-001",
  "transcript_path": "/tmp/test-transcript.json",
  "permission_mode": "default",
  "cwd": "/path/to/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git push --force origin main"
  },
  "tool_use_id": "test-tool-use-001"
}
```

### PostToolUse input structure

```json
{
  "session_id": "test-session-001",
  "transcript_path": "/tmp/test-transcript.json",
  "permission_mode": "default",
  "cwd": "/path/to/project",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/project/src/main.py",
    "content": "print('hello')"
  },
  "tool_response": {
    "success": true
  },
  "tool_use_id": "test-tool-use-001"
}
```

### UserPromptSubmit input structure

```json
{
  "session_id": "test-session-001",
  "transcript_path": "/tmp/test-transcript.json",
  "permission_mode": "default",
  "cwd": "/path/to/project",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "deploy to production"
}
```

### PermissionRequest input structure

```json
{
  "session_id": "test-session-001",
  "transcript_path": "/tmp/test-transcript.json",
  "permission_mode": "default",
  "cwd": "/path/to/project",
  "hook_event_name": "PermissionRequest",
  "tool_name": "Bash",
  "tool_input": {
    "command": "pytest tests/"
  },
  "tool_use_id": "test-tool-use-001"
}
```

### SessionStart input structure

```json
{
  "session_id": "00000000-0000-0000-0000-000000000000",
  "transcript_path": "/tmp/test-transcript.json",
  "hook_event_name": "SessionStart",
  "cwd": "/path/to/project",
  "source": "startup"
}
```

### Organize fixtures by test scenario

```
tests/
└── fixtures/
    └── hooks/
        ├── pre_tool_use/
        │   ├── bash_force_push.json
        │   ├── bash_safe_command.json
        │   ├── write_outside_project.json
        │   └── write_inside_project.json
        ├── permission_request/
        │   ├── pytest_command.json
        │   └── dangerous_command.json
        └── user_prompt_submit/
            ├── deploy_prompt.json
            └── normal_prompt.json
```

## Testing conditions independently

Test condition expressions using `oaps hooks debug` before testing full rules.

### Debug expression evaluation

```bash
# Show condition and evaluation result
oaps hooks debug my-rule-id --event pre_tool_use --input test.json

# Show all context variables
oaps hooks debug my-rule-id --event pre_tool_use --input test.json -v
```

### Verify context variables

```bash
# Check what variables are available
oaps hooks debug my-rule-id --event pre_tool_use -v
```

Output shows context variables:

```
Context variables available:
  cwd: /path/to/project
  git_branch: main
  hook_type: pre_tool_use
  permission_mode: default
  session_id: test-session
  tool_input: {'command': 'git push'}
  tool_name: Bash
```

### Test expression components

Break complex conditions into parts:

```toml
# Original complex condition
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "git\\s+push"
and $current_branch() == "main"
'''
```

Test each part:

```bash
# Test 1: Verify tool_name
echo '{"tool_name": "Bash", ...}' | oaps hooks test -e pre_tool_use

# Test 2: Verify command pattern
echo '{"tool_input": {"command": "git push origin main"}, ...}' | oaps hooks test -e pre_tool_use

# Test 3: Check branch function
oaps hooks debug my-rule-id --event pre_tool_use -v
# Look for git_branch in context
```

### Test edge cases

Create fixtures for boundary conditions:

```json
// Empty command
{"tool_input": {"command": ""}}

// Command with special characters
{"tool_input": {"command": "echo 'test && rm -rf /'"}}

// Null tool_input
{"tool_input": null}

// Missing fields
{"tool_name": "Bash"}
```

## Testing actions

### Test deny action

```bash
# Should show rule with result "block"
oaps hooks test --rule block-force-push --input force_push.json
```

Expected output:

```
Matched 1 rule(s) for event=pre_tool_use, tool=Bash

  [1] block-force-push (priority: high)
      Result: block
```

### Test allow action

```bash
# Should show rule with result "ok" and allow action
oaps hooks test --rule auto-approve-tests --event permission_request --input pytest.json
```

### Test warn/suggest actions

```bash
# Should show rule with result "warn"
oaps hooks test --rule warn-sudo --input sudo_command.json
```

### Verify action configuration

```bash
# Check action details in debug output
oaps hooks debug warn-sudo --event pre_tool_use

# Look for RULE DETAILS section showing actions
```

## Integration testing with Claude Code

### Manual integration test

1. Deploy rules to `.oaps/hooks.d/test.toml`
2. Start Claude Code session
3. Trigger the rule condition
4. Verify expected behavior (block, warn, etc.)
5. Check logs at `~/.oaps/logs/hooks.log`

### Test in isolated environment

```bash
# Create test directory
mkdir -p /tmp/test-project/.oaps/hooks.d
cd /tmp/test-project

# Copy test rules
cp my-rule.toml .oaps/hooks.d/

# Initialize git if needed for git functions
git init

# Start Claude Code
claude
```

### Verify log output

```bash
# Watch logs during testing
tail -f ~/.oaps/logs/hooks.log | jq .

# Filter for specific rule
tail -f ~/.oaps/logs/hooks.log | jq 'select(.rule_id == "my-rule-id")'
```

## Test organization patterns

### Test file naming

```
tests/
└── hooks/
    ├── test_security_rules.sh
    ├── test_workflow_rules.sh
    └── fixtures/
        ├── security/
        │   ├── rm_rf_root.json
        │   └── force_push.json
        └── workflow/
            ├── commit_main.json
            └── commit_feature.json
```

### Shell test script

```bash
#!/bin/bash
# tests/hooks/test_security_rules.sh

set -e

FIXTURES_DIR="$(dirname "$0")/fixtures/security"

echo "Testing security rules..."

# Test 1: Block rm -rf /
echo "Test: block-rm-rf should match"
RESULT=$(oaps hooks test --rule block-rm-rf --event pre_tool_use --input "$FIXTURES_DIR/rm_rf_root.json" --format json)
MATCHED=$(echo "$RESULT" | jq '.matched_count')
if [ "$MATCHED" -ne 1 ]; then
    echo "FAIL: Expected 1 match, got $MATCHED"
    exit 1
fi
echo "PASS"

# Test 2: Safe command should not match
echo "Test: block-rm-rf should NOT match safe command"
RESULT=$(oaps hooks test --rule block-rm-rf --event pre_tool_use --input "$FIXTURES_DIR/safe_rm.json" --format json)
MATCHED=$(echo "$RESULT" | jq '.matched_count')
if [ "$MATCHED" -ne 0 ]; then
    echo "FAIL: Expected 0 matches, got $MATCHED"
    exit 1
fi
echo "PASS"

echo "All security rule tests passed!"
```

### Makefile integration

```makefile
.PHONY: test-hooks validate-hooks

validate-hooks:
	oaps hooks validate

test-hooks: validate-hooks
	./tests/hooks/test_security_rules.sh
	./tests/hooks/test_workflow_rules.sh

test: test-unit test-hooks
```

## Validation checklist before deployment

Run through this checklist before deploying hook rules to production.

### Syntax validation

```bash
# Must pass with no errors
oaps hooks validate
```

### Positive tests (should match)

```bash
# Test each rule with matching input
oaps hooks test --rule <id> --input matching_input.json --format json | jq '.matched_count == 1'
```

### Negative tests (should not match)

```bash
# Test each rule with non-matching input
oaps hooks test --rule <id> --input non_matching_input.json --format json | jq '.matched_count == 0'
```

### Event type verification

```bash
# Verify rule responds to correct events
oaps hooks debug <id> --event pre_tool_use
# Check "MATCHES" in EVENT MATCHING section
```

### Priority and terminal flags

```bash
# List rules to verify priority order
oaps hooks list --event pre_tool_use

# Check critical rules are terminal
oaps hooks debug <id> | grep -E "Priority:|Terminal:"
```

### Action compatibility

```bash
# Verify actions are supported by event type
oaps hooks validate --verbose
```

### CI integration

```yaml
# .github/workflows/ci.yml
jobs:
  test-hooks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install OAPS
        run: pip install oaps
      - name: Validate hooks
        run: oaps hooks validate
      - name: Test hooks
        run: ./tests/hooks/run_all.sh
```
