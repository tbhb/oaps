---
description: Create a new slash command from scratch
default: true
---

## Create command

Follow these steps in order, skipping steps only when there is a clear reason why they are not applicable.

### Step 1: Understand the command's purpose

Skip this step only when the command's purpose and usage are already clearly understood.

To create an effective command, clearly understand:

- What task the command should accomplish
- What inputs (arguments) the command needs
- Whether the command requires specific tools
- How often the command will be used

Ask clarifying questions such as:

- "What specific task should this command perform?"
- "What arguments should the command accept?"
- "Should this command be invocable programmatically, or manual-only?"

**Critical concept:** Commands are instructions FOR Claude, not messages TO users. Write commands as directives about what Claude should do.

Conclude this step when there is a clear understanding of the command's purpose.

### Step 2: Choose command location

Determine where the command should live:

| Location | Scope | Use for |
|----------|-------|---------|
| `.oaps/claude/commands/` | Project-specific | Team workflows, project tasks |
| `commands/` (OAPS plugin) | All OAPS projects | OAPS-provided workflows |

For project commands, consider namespace organization:

```text
.oaps/claude/commands/
├── git/
│   └── commit.md      # /commit (project:git)
├── ci/
│   └── build.md       # /build (project:ci)
└── review.md          # /review (project)
```

### Step 3: Create the command file

Create a markdown file at the chosen location.

**Simple command (no frontmatter):**

```markdown
Review this code for security vulnerabilities including:
- SQL injection
- XSS attacks
- Authentication issues

Provide specific line numbers and severity ratings.
```

**Command with configuration:**

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep
argument-hint: [file-path]
---

Review @$1 for security vulnerabilities...
```

### Step 4: Add frontmatter (if needed)

Add YAML frontmatter for configuration:

```yaml
---
description: Brief description for /help
allowed-tools: Read, Write, Bash(git:*)
model: sonnet
argument-hint: [arg1] [arg2]
disable-model-invocation: false
---
```

**When to add frontmatter:**

- Need to restrict/specify tools
- Want clear description in `/help`
- Command accepts arguments
- Need specific model
- Should be manual-only

For detailed field specifications, see `references/frontmatter-reference.md`.

### Step 5: Add dynamic features (if needed)

**Arguments:**

```markdown
Fix issue #$ARGUMENTS following our standards.
# or positional:
Deploy $1 to $2 environment with version $3.
```

**File references:**

```markdown
Review @$1 for issues.
# or static:
Review @package.json and @tsconfig.json for consistency.
```

**Bash execution:**

```markdown
Current changes: !`git diff --name-only`

Review each changed file for issues.
```

### Step 6: Validate the command

Test the command works correctly:

1. Invoke the command with `/command-name`
2. Verify arguments expand correctly
3. Check file references load
4. Confirm bash execution works
5. Verify tool restrictions apply

**Common issues:**

- Command not appearing: Check `.md` extension and directory
- Arguments not working: Verify `$1`, `$ARGUMENTS` syntax
- Bash failing: Check `allowed-tools` includes `Bash`

### Step 7: Document the command

Add a comment block explaining usage:

```markdown
---
description: Deploy application to environment
argument-hint: [environment] [version]
---

<!--
Usage: /deploy [staging|production] [version]
Requires: AWS credentials configured
Example: /deploy staging v1.2.3
-->

Deploy application to $1 environment using version $2...
```

### Step 8: Commit the command

Once validated and tested:

```bash
oaps command save --message "command created" <command-name>
```

Or commit manually:

```bash
git add .oaps/claude/commands/<command-name>.md
git commit -m "feat: add /command-name command"
```

### Step 9: Iterate

After using the command in practice:

- Improve argument handling for edge cases
- Add validation for required arguments
- Expand tool restrictions if needed
- Clarify description for discoverability
