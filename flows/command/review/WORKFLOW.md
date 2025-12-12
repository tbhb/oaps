---
description: Review an existing command for quality and effectiveness
---

## Review command

Follow these steps to review an existing command for quality, completeness, and effectiveness.

### Step 1: Read the command file

Read the command file to understand its current configuration:

```bash
cat .oaps/claude/commands/<command-name>.md
# or for namespaced:
cat .oaps/claude/commands/<namespace>/<command-name>.md
```

### Step 2: Review structure

Check the command follows proper structure:

**Frontmatter (if present):**

- [ ] YAML syntax is valid
- [ ] `description` is clear and under 60 characters
- [ ] `allowed-tools` is appropriately restrictive
- [ ] `model` is specified only if needed
- [ ] `argument-hint` matches actual arguments
- [ ] `disable-model-invocation` used appropriately

**Command body:**

- [ ] Written as instructions FOR Claude (not messages to user)
- [ ] Clear about what task to perform
- [ ] Process steps defined if multi-step
- [ ] Output expectations specified

### Step 3: Review argument handling

If command uses arguments:

**$ARGUMENTS usage:**

- [ ] Handles case when no arguments provided
- [ ] Usage documented in comments

**Positional arguments ($1, $2, etc.):**

- [ ] Each argument clearly documented in `argument-hint`
- [ ] Handles missing arguments gracefully
- [ ] Order is logical and documented

**File references (@syntax):**

- [ ] File paths are valid
- [ ] Handles missing files gracefully
- [ ] Read tool is in allowed-tools

### Step 4: Review tool restrictions

Check `allowed-tools` configuration:

- [ ] Tools are as restrictive as possible
- [ ] Bash uses command filters (e.g., `Bash(git:*)` not `Bash(*)`)
- [ ] Only necessary tools are included
- [ ] Restrictions don't prevent command from working

**Security considerations:**

- [ ] No destructive operations without restriction
- [ ] Sensitive operations require appropriate tools
- [ ] Principle of least privilege applied

### Step 5: Review documentation

Check command is well-documented:

- [ ] `description` clearly explains purpose
- [ ] Comment block shows usage examples
- [ ] Requirements documented
- [ ] Edge cases noted

### Step 6: Test command execution

Test the command works correctly:

1. **Basic invocation:** `/command-name`
2. **With arguments:** `/command-name arg1 arg2`
3. **Edge cases:** Missing arguments, invalid inputs

**Test checklist:**

- [ ] Command appears in `/help`
- [ ] Description shows correctly
- [ ] Arguments expand properly
- [ ] File references load
- [ ] Bash execution works
- [ ] Tool restrictions apply

### Step 7: Document findings

Create a review summary:

```markdown
## Command Review: /command-name

### Structure
- [ ] Valid YAML frontmatter
- [ ] Instructions written for Claude
- [ ] Clear process steps

### Arguments
- [ ] Properly documented
- [ ] Handles edge cases
- [ ] Order is logical

### Tools
- [ ] Appropriately restrictive
- [ ] Bash filters used
- [ ] Necessary tools included

### Documentation
- [ ] Clear description
- [ ] Usage examples
- [ ] Requirements noted

### Issues Found
1. [Issue description] - [Severity]

### Recommendations
1. [Specific recommendation]
```

### Step 8: Apply fixes

If issues were found:

1. Edit the command file to address issues
2. Re-test command execution
3. Commit with descriptive message:

```bash
oaps command save --message "reviewed and fixed" <command-name>
```
