---
name: anatomy
title: Command anatomy and structure
description: Core concepts, file structure, and dynamic features for Claude Code slash commands
related:
  - frontmatter-reference
  - interactive-commands
principles:
  - Commands are instructions FOR Claude, not messages TO users
  - Commands provide reusable, consistent workflows
  - Dynamic arguments and file references enable flexible commands
  - Tool restrictions enforce principle of least privilege
best_practices:
  - Write commands as directives about what Claude should do
  - Use argument-hint to document expected arguments
  - Restrict tools to minimum needed
  - Use namespaced directories for organization
checklist:
  - Command is written as instructions for Claude
  - Description is clear and under 60 characters
  - Arguments documented with argument-hint
  - Tool restrictions applied appropriately
commands:
  oaps command validate <name>: Validate command structure
  oaps command save --message "<msg>" <name>: Commit command with validation
references:
  https://docs.anthropic.com/en/docs/claude-code: Claude Code documentation
---

# Command anatomy and structure

Slash commands are frequently-used prompts defined as markdown files that Claude executes during interactive sessions. They provide reusable, consistent workflows that can be shared across teams and projects.

## Key concept: commands are instructions for Claude

**Commands are written for agent consumption, not human consumption.**

When a user invokes `/command-name`, the command content becomes Claude's instructions. Write commands as directives TO Claude about what to do.

**Correct (instructions for Claude):**

```markdown
Review this code for security vulnerabilities including:
- SQL injection
- XSS attacks
- Authentication issues

Provide specific line numbers and severity ratings.
```

**Incorrect (messages to user):**

```markdown
This command will review your code for security issues.
You'll receive a report with vulnerability details.
```

## Command locations

| Type | Location | Scope | Label in /help |
|------|----------|-------|----------------|
| **Project** | `.oaps/claude/commands/` | This project | (project) |
| **OAPS plugin** | `commands/` | All OAPS projects | (oaps) |

## File format

Commands are markdown files with `.md` extension.

### Simple command (no frontmatter)

```markdown
Review this code for common issues and suggest improvements.
```

### Command with frontmatter

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep
model: sonnet
argument-hint: [file-path]
---

Review @$1 for security vulnerabilities...
```

## Organization

### Flat structure

For small command sets (5-15 commands):

```text
.oaps/claude/commands/
├── build.md
├── test.md
├── deploy.md
└── review.md
```

### Namespaced structure

For larger command sets (15+ commands):

```text
.oaps/claude/commands/
├── ci/
│   ├── build.md        # /build (project:ci)
│   ├── test.md         # /test (project:ci)
│   └── lint.md         # /lint (project:ci)
├── git/
│   ├── commit.md       # /commit (project:git)
│   └── pr.md           # /pr (project:git)
└── docs/
    └── generate.md     # /generate (project:docs)
```

## Dynamic arguments

### $ARGUMENTS

Captures all arguments as a single string:

```markdown
---
argument-hint: [issue-number]
---

Fix issue #$ARGUMENTS following our coding standards.
```

**Usage:** `/fix-issue 123` expands to "Fix issue #123..."

### Positional arguments ($1, $2, $3...)

Captures individual arguments:

```markdown
---
argument-hint: [pr-number] [priority] [assignee]
---

Review PR #$1 with priority $2. Assign to $3 for follow-up.
```

**Usage:** `/review-pr 123 high alice` expands with $1=123, $2=high, $3=alice

## File references

### @ syntax

Include file contents in command:

```markdown
Review @$1 for:
- Code quality
- Best practices
- Potential bugs
```

**Usage:** `/review-file src/api.ts` reads `src/api.ts` into context

### Static file references

```markdown
Review @package.json and @tsconfig.json for consistency.
```

## Bash execution

Execute bash commands to gather context:

```markdown
Current changes: !`git diff --name-only`

Review each changed file for issues.
```

**Important:** Requires `Bash` in `allowed-tools`.

## Quick reference

### Frontmatter fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| description | string | No | Shown in /help |
| allowed-tools | string/array | No | Tool restrictions |
| model | string | No | sonnet/opus/haiku |
| argument-hint | string | No | Document arguments |
| disable-model-invocation | boolean | No | Manual-only |

### Dynamic features

| Feature | Syntax | Example |
|---------|--------|---------|
| All arguments | `$ARGUMENTS` | Fix issue #$ARGUMENTS |
| Positional args | `$1`, `$2`, `$3` | Deploy $1 to $2 |
| File reference | `@path` | Review @$1 |
| Bash execution | `!`command`` | !`git status` |

### Common patterns

**Review pattern:**

```markdown
---
description: Review code changes
allowed-tools: Read, Bash(git:*)
---

Files changed: !`git diff --name-only`

Review each file for code quality and potential bugs.
```

**Testing pattern:**

```markdown
---
description: Run tests for file
argument-hint: [test-file]
allowed-tools: Bash(pytest:*)
---

Run tests: !`pytest $1`

Analyze results and suggest fixes for failures.
```

**Documentation pattern:**

```markdown
---
description: Generate docs for file
argument-hint: [source-file]
---

Generate comprehensive documentation for @$1 including:
- Function descriptions
- Parameter documentation
- Usage examples
```
