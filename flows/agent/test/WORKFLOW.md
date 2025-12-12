---
description: Test agent triggering and functionality
---

## Test agent

Follow these steps to thoroughly test an agent's triggering conditions and functionality.

### Step 1: Review triggering examples

Read the agent's description to understand expected triggering scenarios:

```bash
cat agents/<agent-name>.md | head -50
```

Extract:

- Triggering conditions ("Use this agent when...")
- Example contexts
- Example user messages
- Expected assistant responses

### Step 2: Test explicit triggering

Test that the agent triggers on explicit requests matching the examples:

1. Start a fresh Claude session
2. Use exact phrasing from an example
3. Verify Claude announces using the agent
4. Verify agent produces expected output

**Test cases:**

| Example Used | Triggered? | Output Correct? | Notes |
|--------------|------------|-----------------|-------|
| Example 1    |            |                 |       |
| Example 2    |            |                 |       |
| Example 3    |            |                 |       |

### Step 3: Test phrasing variations

Test triggering with variations not in examples:

1. Rephrase the same request differently
2. Use synonyms for key terms
3. Try shorter/longer versions

**Test cases:**

| Variation | Triggered? | Notes |
|-----------|------------|-------|
| [variation 1] |         |       |
| [variation 2] |         |       |
| [variation 3] |         |       |

### Step 4: Test proactive triggering

If the agent should trigger proactively (after certain actions):

1. Perform the prerequisite action
2. Make a statement that doesn't explicitly request the agent
3. Verify Claude proactively uses the agent

**Example scenario:**

```text
1. Write some code
2. Say "I've finished implementing the feature"
3. Check if code-review agent triggers proactively
```

### Step 5: Test negative cases

Verify the agent does NOT trigger inappropriately:

1. Make requests similar but not within scope
2. Verify a different agent or direct response is used

**Test cases:**

| Request | Should NOT Trigger | Passed? |
|---------|-------------------|---------|
| [similar but out of scope] |     |         |

### Step 6: Test system prompt functionality

Once triggered, verify the agent:

- Follows its defined process
- Meets quality standards
- Produces correctly formatted output
- Handles edge cases appropriately

**Functional tests:**

| Scenario | Expected Behavior | Actual Behavior | Passed? |
|----------|-------------------|-----------------|---------|
| Typical task |                |                 |         |
| Edge case 1 |                 |                 |         |
| Edge case 2 |                 |                 |         |

### Step 7: Test tool restrictions

If the agent has tool restrictions:

1. Trigger the agent
2. Verify it can use allowed tools
3. Verify it cannot use restricted tools

### Step 8: Document results

Create a test report:

```markdown
## Agent Test Report: <agent-name>

### Triggering Tests
- Explicit requests: [X/Y passed]
- Phrasing variations: [X/Y passed]
- Proactive triggers: [X/Y passed]
- Negative cases: [X/Y passed]

### Functional Tests
- Process followed: [Yes/No]
- Output format correct: [Yes/No]
- Edge cases handled: [Yes/No]

### Issues Found
1. [Issue description]

### Recommendations
1. [If triggering unreliable, add more examples]
2. [If output inconsistent, clarify system prompt]
```

### Step 9: Fix issues

If tests reveal problems:

**Triggering issues:**

- Add more `<example>` blocks with varied phrasings
- Make triggering conditions more specific
- Add commentary explaining when NOT to trigger

**Functionality issues:**

- Expand process steps in system prompt
- Add missing edge case handling
- Clarify output format requirements

After fixes:

1. Re-run relevant tests
2. Commit with `oaps agent save --message "improved triggering" <agent-name>`
