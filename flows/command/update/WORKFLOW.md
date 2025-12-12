---
description: Update an existing command
---

## Update command

Follow these steps to update an existing command's configuration, behavior, or documentation.

### Step 1: Identify what needs updating

Common update scenarios:

- **Argument changes**: Add, remove, or modify arguments
- **Tool restrictions**: Change allowed tools
- **Model changes**: Use different model
- **Description updates**: Improve discoverability
- **Bug fixes**: Fix incorrect behavior
- **Documentation**: Improve usage guidance

### Step 2: Read current command

Read the command file to understand current state:

```bash
cat .oaps/claude/commands/<command-name>.md
```

Note the current configuration and behavior.

### Step 3: Update frontmatter (if needed)

**Update description:**

```yaml
---
description: More descriptive text here
---
```

**Update allowed-tools:**

```yaml
---
# Add tools:
allowed-tools: Read, Write, Grep, Bash(git:*)

# Or restrict:
allowed-tools: Read, Grep
---
```

**Update model:**

```yaml
---
model: haiku    # For faster execution
model: opus     # For complex tasks
---
```

**Update argument-hint:**

```yaml
---
argument-hint: [new-arg] [optional-arg]
---
```

**Add manual-only restriction:**

```yaml
---
disable-model-invocation: true
---
```

### Step 4: Update command body (if needed)

**Improve instructions:**

Make instructions clearer and more specific:

```markdown
# Before (vague):
Review the code.

# After (specific):
Review this code for:
1. Security vulnerabilities (SQL injection, XSS)
2. Performance issues (N+1 queries, memory leaks)
3. Code style violations

Provide file:line references for each issue.
```

**Add argument handling:**

```markdown
# Add argument validation:
If $1 is provided:
  Process file at $1
Otherwise:
  Explain usage: /command [file-path]
  List recently modified files as suggestions
```

**Add file references:**

```markdown
# Add static file references:
Review @package.json dependencies and @tsconfig.json settings.

# Add dynamic file references:
Review @$1 for issues.
```

**Add bash execution:**

```markdown
Current branch: !`git branch --show-current`
Recent changes: !`git diff --name-only HEAD~5`

Based on this context, proceed with review.
```

### Step 5: Update documentation

**Update comment block:**

```markdown
---
description: Deploy to environment
argument-hint: [environment] [version]
---

<!--
UPDATED: [date]

Usage: /deploy [staging|production] [version]
Requires: AWS credentials configured
Examples:
  /deploy staging v1.2.3
  /deploy production v2.0.0

Changes:
  - Added version argument
  - Added production environment support
-->
```

### Step 6: Validate changes

Test the updated command:

1. **Basic functionality**: Command still works
2. **New features**: Changes work as expected
3. **Backward compatibility**: Existing usage still works
4. **Edge cases**: Handle missing/invalid inputs

### Step 7: Commit update

Once validated:

```bash
oaps command save --message "updated: [what changed]" <command-name>
```

Use descriptive commit messages:

- "updated: added version argument"
- "updated: improved tool restrictions"
- "updated: fixed argument handling"
- "updated: clarified description"

### Common update patterns

**Adding validation:**

```markdown
# Before:
Deploy to $1

# After:
Validate environment: !`echo "$1" | grep -E "^(dev|staging|prod)$" || echo "INVALID"`

If $1 is valid environment:
  Deploy to $1
Otherwise:
  Explain valid environments: dev, staging, prod
```

**Adding error handling:**

```markdown
# Before:
Build: !`npm run build`

# After:
Build result: !`npm run build 2>&1 || echo "BUILD_FAILED"`

If build succeeded:
  Report success
If build failed:
  Analyze error output
  Suggest fixes
```

**Improving discoverability:**

```yaml
# Before:
---
description: Review PR
---

# After:
---
description: Review PR for code quality and security issues
argument-hint: [pr-number]
---
```
