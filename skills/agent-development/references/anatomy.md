---
name: anatomy
title: Agent anatomy and structure
description: Core concepts, file structure, and frontmatter fields for Claude Code agents
related:
  - system-prompt-design
  - triggering-examples
  - builtin-agents
principles:
  - Agents are autonomous subprocesses for complex, multi-step tasks
  - Agents are FOR autonomous work; commands are FOR user-initiated actions
  - Triggering via description field with examples is critical for reliability
  - Least privilege principle applies to tool restrictions
best_practices:
  - Include 2-4 triggering examples in description
  - Use inherit for model unless specific capabilities needed
  - Choose distinct colors for agents in same plugin
  - Restrict tools to minimum needed
  - Write clear, structured system prompts
checklist:
  - Agent file has proper YAML frontmatter (name, description, model, color)
  - Name follows conventions (3-50 chars, lowercase, hyphens)
  - Description includes triggering conditions and example blocks
  - System prompt defines responsibilities, process, and output format
commands:
  oaps agent validate <name>: Validate agent file structure
  oaps agent save --message "<msg>" <name>: Commit agent with validation
references:
  https://docs.anthropic.com/en/docs/claude-code: Claude Code documentation
---

# Agent anatomy and structure

Agents are autonomous subprocesses that handle complex, multi-step tasks independently. They are invoked via the Task tool and run with their own system prompt, enabling specialized capabilities without manual orchestration.

## Key distinction: agents vs commands

| Aspect | Agents | Commands |
|--------|--------|----------|
| **Purpose** | Autonomous multi-step work | User-initiated single actions |
| **Triggering** | Claude decides based on description | User explicitly invokes |
| **Execution** | Subprocess with own context | Inline in main conversation |
| **Use case** | Code review, analysis, generation | Git operations, quick tasks |

## Agent file structure

Every agent is a markdown file with YAML frontmatter:

```markdown
---
name: agent-identifier
description: Use this agent when [triggering conditions]. Examples:

<example>
Context: [Situation description]
user: "[User request]"
assistant: "[How assistant should respond and use this agent]"
<commentary>
[Why this agent should be triggered]
</commentary>
</example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

You are [agent role description]...

**Your Core Responsibilities:**
1. [Responsibility 1]
2. [Responsibility 2]

**Analysis Process:**
[Step-by-step workflow]

**Output Format:**
[What to return]
```

## Agent locations

| Type | Location | Purpose |
|------|----------|---------|
| **Plugin-distributed** | `agents/` | Ship with plugin, available globally |
| **Project-specific** | `.oaps/claude/agents/` | Project customizations only |

All `.md` files in these directories are auto-discovered and namespaced:

- Plugin agent `agents/reviewer.md` in plugin `my-plugin` becomes `my-plugin:reviewer`
- Users invoke via Task tool with `subagent_type: "my-plugin:reviewer"`

## Frontmatter fields

### name (required)

Agent identifier used for namespacing and invocation.

**Format:** lowercase letters, numbers, hyphens only
**Length:** 3-50 characters
**Pattern:** Must start and end with alphanumeric

**Good examples:**

- `code-reviewer`
- `test-generator`
- `api-docs-writer`
- `security-analyzer`

**Bad examples:**

- `helper` (too generic)
- `-agent-` (starts/ends with hyphen)
- `my_agent` (underscores not allowed)
- `ag` (too short, < 3 chars)

### description (required)

Defines when Claude should trigger this agent. **This is the most critical field.**

**Must include:**

1. Triggering conditions ("Use this agent when...")
2. Multiple `<example>` blocks showing usage
3. Context, user request, and assistant response in each example
4. `<commentary>` explaining why agent triggers

**Length:** 10-5,000 characters
**Recommended:** 200-1,000 characters with 2-4 examples

For detailed example format, see `references/triggering-examples.md`.

### model (required)

Which model the agent should use.

**Options:**

| Value | Description | Use when |
|-------|-------------|----------|
| `inherit` | Same as parent | Default choice |
| `haiku` | Fast, cheap | Simple validation, formatting |
| `sonnet` | Balanced | Most use cases |
| `opus` | Most capable | Complex reasoning, architecture |

**Recommendation:** Use `inherit` unless agent needs specific model capabilities.

### color (required)

Visual identifier for agent in UI.

**Options:** `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`

**Guidelines:**

- Choose distinct colors for different agents in same plugin
- Use consistent colors for similar agent types:
  - Blue/cyan: Analysis, review
  - Green: Success-oriented tasks
  - Yellow: Caution, validation
  - Red: Critical, security
  - Magenta: Creative, generation

### tools (optional)

Restrict agent to specific tools.

**Format:** Array of tool names

```yaml
tools: ["Read", "Write", "Grep", "Bash"]
```

**Default:** If omitted, agent has access to all tools

**Best practice:** Apply principle of least privilege

**Common tool sets:**

| Use case | Tools |
|----------|-------|
| Read-only analysis | `["Read", "Grep", "Glob"]` |
| Code generation | `["Read", "Write", "Grep"]` |
| Testing | `["Read", "Bash", "Grep"]` |
| Full access | Omit field or use `["*"]` |

## Quick reference

### Minimal agent

```markdown
---
name: simple-agent
description: Use this agent when... Examples: <example>...</example>
model: inherit
color: blue
---

You are an agent that [does X].

Process:
1. [Step 1]
2. [Step 2]

Output: [What to provide]
```

### Frontmatter summary

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| name | Yes | lowercase-hyphens | code-reviewer |
| description | Yes | Text + examples | Use when... <example>... |
| model | Yes | inherit/sonnet/opus/haiku | inherit |
| color | Yes | Color name | blue |
| tools | No | Array of tool names | ["Read", "Grep"] |
