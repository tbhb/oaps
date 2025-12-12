---
description: Test command functionality and edge cases
---

## Test command

Follow these steps to thoroughly test a command's functionality and edge cases.

### Step 1: Review command definition

Read the command to understand expected behavior:

```bash
cat .oaps/claude/commands/<command-name>.md
```

Extract:

- Expected arguments from `argument-hint`
- Tool restrictions from `allowed-tools`
- Model setting from `model`
- Whether manual-only from `disable-model-invocation`

### Step 2: Test basic invocation

Test the command appears and executes:

1. Check command appears in `/help`
2. Invoke with `/command-name`
3. Verify Claude executes the command
4. Check output matches expectations

**Test cases:**

| Test | Command | Expected | Passed? |
|------|---------|----------|---------|
| Appears in help | `/help` | Shows command | |
| Basic invoke | `/command-name` | Executes | |
| Description shown | `/help` | Shows description | |

### Step 3: Test argument handling

If command uses arguments:

**$ARGUMENTS tests:**

| Test | Command | Expected | Passed? |
|------|---------|----------|---------|
| With argument | `/cmd value` | Uses "value" | |
| No argument | `/cmd` | Handles gracefully | |
| Multiple words | `/cmd word1 word2` | Uses full string | |

**Positional argument tests ($1, $2, etc.):**

| Test | Command | Expected | Passed? |
|------|---------|----------|---------|
| All arguments | `/cmd a b c` | $1=a, $2=b, $3=c | |
| Missing optional | `/cmd a` | $1=a, $2 empty | |
| Missing required | `/cmd` | Error/guidance | |

### Step 4: Test file references

If command uses `@` file references:

| Test | File State | Expected | Passed? |
|------|------------|----------|---------|
| File exists | Present | Loads content | |
| File missing | Absent | Error/guidance | |
| Invalid path | Wrong path | Error message | |

### Step 5: Test bash execution

If command uses `!`backtick`` bash execution:

| Test | Command State | Expected | Passed? |
|------|---------------|----------|---------|
| Command succeeds | Valid command | Output included | |
| Command fails | Invalid command | Error handled | |
| Permission denied | No access | Error message | |

### Step 6: Test tool restrictions

Verify `allowed-tools` work correctly:

1. Command can use allowed tools
2. Command cannot use restricted tools
3. Bash filters apply correctly

**Test cases:**

| Tool | Allowed? | Test Action | Passed? |
|------|----------|-------------|---------|
| Read | Yes/No | Read a file | |
| Write | Yes/No | Write a file | |
| Bash | Filtered | Run filtered cmd | |
| Bash | Filtered | Run non-filtered | |

### Step 7: Test model selection

If command specifies `model`:

1. Verify command uses specified model
2. Compare behavior with different models
3. Check if model choice is appropriate

### Step 8: Test edge cases

Test unusual scenarios:

| Scenario | Test | Expected | Passed? |
|----------|------|----------|---------|
| Empty input | `/cmd ""` | Handles gracefully | |
| Special chars | `/cmd <>&` | Handles correctly | |
| Long input | `/cmd [long string]` | Works or limits | |
| Unicode | `/cmd emojis` | Handles correctly | |

### Step 9: Test programmatic invocation

If `disable-model-invocation` is not true:

1. Ask Claude to use the command programmatically
2. Verify SlashCommand tool can invoke it
3. Check arguments pass correctly

If `disable-model-invocation` is true:

1. Verify Claude cannot invoke programmatically
2. Confirm manual invocation still works

### Step 10: Document test results

Create a test report:

```markdown
## Command Test Report: /command-name

### Basic Functionality
- Appears in /help: [Pass/Fail]
- Basic invocation: [Pass/Fail]
- Description correct: [Pass/Fail]

### Argument Handling
- With arguments: [Pass/Fail]
- Missing arguments: [Pass/Fail]
- Edge cases: [Pass/Fail]

### File References
- Existing files: [Pass/Fail]
- Missing files: [Pass/Fail]

### Bash Execution
- Valid commands: [Pass/Fail]
- Invalid commands: [Pass/Fail]

### Tool Restrictions
- Allowed tools work: [Pass/Fail]
- Restricted tools blocked: [Pass/Fail]

### Issues Found
1. [Issue description]

### Recommendations
1. [Specific fix]
```

### Step 11: Fix issues

If tests reveal problems:

1. Edit command to fix issues
2. Re-run failed tests
3. Commit fixes:

```bash
oaps command save --message "fixed: [issue]" <command-name>
```
