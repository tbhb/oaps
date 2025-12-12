---
description: Update an existing agent
---

## Update agent

Follow these steps to update an existing agent's configuration, triggering, or functionality.

### Step 1: Identify what needs updating

Common update scenarios:

- **Triggering improvements**: Agent doesn't trigger reliably
- **System prompt enhancements**: Agent output quality varies
- **Tool restriction changes**: Agent needs more/fewer tools
- **Model changes**: Agent needs different model capabilities
- **Bug fixes**: Agent behaves incorrectly in certain cases

### Step 2: Read current agent

Read the agent file to understand current configuration:

```bash
cat agents/<agent-name>.md
```

Note the current state of the section(s) being updated.

### Step 3: Update triggering (if needed)

To improve triggering reliability:

**Add more examples:**

```markdown
<example>
Context: [New scenario]
user: "[New phrasing]"
assistant: "[Response]"
<commentary>
[Explanation]
</commentary>
</example>
```

**Improve triggering conditions:**

- Make conditions more specific
- Add keywords users commonly use
- Clarify when NOT to trigger

**Fix over-triggering:**

- Remove overly broad examples
- Add specificity to conditions
- Distinguish from similar agents

### Step 4: Update system prompt (if needed)

To improve output quality:

**Add process steps:**

```markdown
**[Task] Process:**
1. [Existing steps]
2. [NEW step for missing case]
```

**Add edge case handling:**

```markdown
**Edge Cases:**
- [Existing cases]
- [NEW case]: [How to handle]
```

**Clarify output format:**

```markdown
**Output Format:**
[More specific format requirements]
```

**Add quality standards:**

```markdown
**Quality Standards:**
- [Existing standards]
- [NEW standard]
```

### Step 5: Update tools (if needed)

To change tool access:

**Restrict tools:**

```yaml
tools: ["Read", "Grep"]  # Remove Write, Bash, etc.
```

**Expand tools:**

```yaml
tools: ["Read", "Write", "Grep", "Bash"]  # Add needed tools
```

**Give full access:**

```yaml
# Remove tools field entirely, or:
tools: ["*"]
```

### Step 6: Update model (if needed)

To change model:

```yaml
model: inherit  # Use parent model (recommended)
model: haiku    # Fast, simple tasks
model: sonnet   # Balanced quality/speed
model: opus     # Complex reasoning
```

### Step 7: Validate changes

Run validation after making changes:

```bash
oaps agent validate <agent-name>
```

Fix any errors before proceeding.

### Step 8: Test changes

Test that updates work as expected:

1. **If triggering changed**: Test with new examples and variations
2. **If system prompt changed**: Test output quality and edge cases
3. **If tools changed**: Verify agent can/cannot use expected tools
4. **If model changed**: Verify performance characteristics

### Step 9: Commit update

Once validated and tested:

```bash
oaps agent save --message "updated: [what changed]" <agent-name>
```

Use descriptive commit messages:

- "updated: improved triggering reliability"
- "updated: added edge case handling"
- "updated: restricted tool access"
- "updated: fixed output format"
