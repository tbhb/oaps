---
description: Review an existing agent for quality and effectiveness
---

## Review agent

Follow these steps to review an existing agent for quality, completeness, and effectiveness.

### Step 1: Read the agent file

Read the agent file to understand its current configuration:

```bash
cat agents/<agent-name>.md
# or for project agents:
cat .oaps/claude/agents/<agent-name>.md
```

### Step 2: Validate structure

Run validation to check basic requirements:

```bash
oaps agent validate <agent-name>
```

Note any validation errors for later correction.

### Step 3: Review frontmatter

Check each frontmatter field:

**name**

- Is it 3-50 characters?
- Uses only lowercase, numbers, hyphens?
- Starts and ends with alphanumeric?
- Is it descriptive and memorable?

**description**

- Does it start with triggering conditions ("Use this agent when...")?
- Are there 2-4 `<example>` blocks?
- Do examples show both proactive and reactive triggering?
- Is commentary present explaining why agent triggers?

**model**

- Is `inherit` used unless specific model needed?
- If specific model, is the choice justified?

**color**

- Is the color distinct from other agents in the same plugin?
- Does it follow semantic conventions (blue=analysis, red=critical, etc.)?

**tools**

- Are tools restricted to minimum needed?
- Does least privilege principle apply?

### Step 4: Review system prompt

Evaluate the system prompt against quality criteria:

**Structure**

- [ ] Role description present ("You are...")
- [ ] Core responsibilities listed (3-8 items)
- [ ] Process steps defined (5-12 steps)
- [ ] Quality standards specified
- [ ] Output format defined
- [ ] Edge cases handled

**Clarity**

- [ ] Written in second person ("You are...", "You will...")
- [ ] Instructions are specific, not vague
- [ ] Process steps are actionable
- [ ] Output format is unambiguous

**Completeness**

- [ ] Handles typical task execution
- [ ] Addresses edge cases
- [ ] Covers error scenarios
- [ ] Provides guidance for unclear requirements

**Length**

- Minimum: ~500 words
- Standard: 1,000-2,000 words
- Maximum: <10,000 words

### Step 5: Review triggering examples

For each `<example>` block:

- [ ] Context is specific (not "User needs help")
- [ ] User message shows exact phrasing that triggers
- [ ] Assistant response shows how to invoke agent
- [ ] Commentary explains WHY agent triggers

Check coverage:

- [ ] At least one explicit request example
- [ ] At least one proactive trigger example (if applicable)
- [ ] Different phrasings covered

### Step 6: Test triggering

If possible, test that the agent triggers correctly:

1. Use phrasing from examples
2. Try variations not in examples
3. Verify agent triggers when expected
4. Verify agent does NOT trigger when inappropriate

### Step 7: Document findings

Create a review summary:

```markdown
## Agent Review: <agent-name>

### Validation
- [ ] Passes `oaps agent validate`

### Frontmatter
- [ ] Name follows conventions
- [ ] Description complete with examples
- [ ] Model appropriate
- [ ] Color distinctive
- [ ] Tools appropriately restricted

### System Prompt
- [ ] Well-structured
- [ ] Clear and specific
- [ ] Complete coverage
- [ ] Appropriate length

### Triggering
- [ ] Examples cover key scenarios
- [ ] Triggers reliably in testing

### Issues Found
1. [Issue description] - [Severity: Critical/Major/Minor]

### Recommendations
1. [Specific recommendation]
```

### Step 8: Apply fixes

If issues were found:

1. Edit the agent file to address issues
2. Re-run validation
3. Re-test triggering
4. Commit with `oaps agent save --message "reviewed and fixed" <agent-name>`
