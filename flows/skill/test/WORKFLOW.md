---
description: Test a skill by using it on real tasks
---

## Test skill

### Step 1: Identify test scenarios

Determine representative test scenarios that exercise the skill:

- Common use cases the skill should handle well
- Edge cases that might reveal weaknesses
- Phrases that should trigger the skill (from description)
- Phrases that should NOT trigger the skill

### Step 2: Test skill activation

Verify the skill triggers appropriately:

- Use trigger phrases from the skill description
- Confirm the skill is suggested or loaded
- Verify non-trigger phrases don't activate the skill

### Step 3: Execute test scenarios

Run through each test scenario:

1. Start a new conversation or context
1. Invoke the skill with a test prompt
1. Observe the guidance quality and relevance
1. Note any missing information or unclear instructions

### Step 4: Evaluate workflow selection

If the skill has multiple workflows:

- Verify the correct workflow is suggested for each scenario
- Check that workflow references are appropriate
- Confirm workflow steps are actionable and clear

### Step 5: Document issues

Record any problems discovered:

- **Activation issues**: Skill not triggering when expected, or triggering incorrectly
- **Content gaps**: Missing information needed to complete tasks
- **Clarity issues**: Confusing or ambiguous instructions
- **Workflow issues**: Wrong workflow selected, missing steps

### Step 6: Prioritize improvements

Categorize issues by impact:

- **Critical**: Prevents task completion
- **High**: Significant friction or confusion
- **Medium**: Noticeable but workable
- **Low**: Minor polish items

### Step 7: Iterate

For each issue identified:

1. Determine the root cause (description, content, workflow, references)
1. Apply the appropriate workflow (update-skill, update-reference, update-workflow)
1. Re-test to verify the fix
