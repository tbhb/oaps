---
description: Create a new agent from scratch
default: true
---

## Create agent

Follow these steps in order, skipping steps only when there is a clear reason why they are not applicable.

### Step 1: Understand the agent's purpose

Skip this step only when the agent's purpose and triggering conditions are already clearly understood.

To create an effective agent, clearly understand:

- What tasks the agent should handle autonomously
- When Claude should trigger this agent (triggering conditions)
- What distinguishes this from a command (agents are FOR autonomous work, commands are FOR user-initiated actions)

Ask clarifying questions such as:

- "What specific tasks should this agent handle?"
- "Should this agent trigger proactively after certain actions, or only when explicitly requested?"
- "Can you give examples of user requests that should trigger this agent?"

Conclude this step when there is a clear understanding of the agent's purpose and triggering scenarios.

### Step 2: Choose creation method

Two methods are available:

**Method 1: AI-assisted generation (recommended for complex agents)**

Use the prompt pattern from `references/agent-creation-system-prompt.md` to generate agent configuration:

```text
Create an agent configuration based on this request: "[DESCRIPTION]"
```

This returns JSON with `identifier`, `whenToUse`, and `systemPrompt` fields that can be converted to agent file format.

**Method 2: Manual creation (recommended for simple agents)**

1. Choose agent identifier (3-50 chars, lowercase, hyphens)
2. Write description with triggering examples
3. Select model (usually `inherit`)
4. Choose color for visual identification
5. Define tools (if restricting access)
6. Write system prompt following patterns in `references/system-prompt-design.md`

### Step 3: Write the agent file

Create the agent file at the appropriate location:

- **Plugin agents**: `agents/<agent-name>.md`
- **Project agents**: `.oaps/claude/agents/<agent-name>.md`

The file must include:

1. **YAML frontmatter** with required fields:
   - `name`: Agent identifier (lowercase, hyphens, 3-50 chars)
   - `description`: Triggering conditions with `<example>` blocks
   - `model`: Usually `inherit`
   - `color`: Visual identifier (blue, cyan, green, yellow, magenta, red)
   - `tools`: Optional array to restrict tool access

2. **System prompt** (markdown body) following patterns in `references/system-prompt-design.md`

For detailed field requirements, see `references/anatomy.md`.

### Step 4: Write triggering examples

The description field must include 2-4 `<example>` blocks showing when the agent should trigger.

Each example must include:

- `Context:` - Situation description
- `user:` - User request in quotes
- `assistant:` - How Claude responds before triggering
- `<commentary>` - Why this agent triggers
- Optional second `assistant:` showing agent invocation

For example formats and best practices, see `references/triggering-examples.md`.

### Step 5: Write the system prompt

The markdown body becomes the agent's system prompt. Follow the structure:

```markdown
You are [role] specializing in [domain].

**Your Core Responsibilities:**
1. [Primary responsibility]
2. [Secondary responsibility]

**[Task] Process:**
1. [Step one]
2. [Step two]
[...]

**Quality Standards:**
- [Standard 1]
- [Standard 2]

**Output Format:**
[What to provide]

**Edge Cases:**
- [Edge case 1]: [How to handle]
```

For detailed patterns and examples, see `references/system-prompt-design.md`.

### Step 6: Validate the agent

Run validation to check structure and content:

```bash
oaps agent validate <agent-name>
```

Validation checks:

- Identifier format (3-50 chars, lowercase, hyphens)
- Required frontmatter fields present
- Description includes triggering examples
- System prompt length (20-10,000 chars)

Fix any reported errors before proceeding.

### Step 7: Test triggering

Test that the agent triggers correctly:

1. Start a new Claude session
2. Use similar phrasing to your triggering examples
3. Verify Claude loads the agent
4. Check that the agent provides expected functionality

If the agent doesn't trigger as expected:

- Add more triggering examples with different phrasings
- Make triggering conditions more specific in description
- Check that examples show Claude using the Task tool

### Step 8: Commit the agent

Once validated and tested:

```bash
oaps agent save --message "agent created" <agent-name>
```

**MANDATORY:** Always use `oaps agent save` to commit agents instead of manual git commits.

### Step 9: Iterate

After testing with real tasks, iterate based on performance:

- Strengthen triggering examples if agent doesn't trigger reliably
- Expand system prompt if agent misses edge cases
- Add quality standards if output quality varies
- Restrict tools if agent has unnecessary access
