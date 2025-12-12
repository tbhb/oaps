---
description: Test agents for triggering and functionality
argument-hint: [agent-name]
allowed-tools:
  - AskUserQuestion
  - Bash(oaps:*)
  - Glob
  - Grep
  - Read
  - Skill
  - Task
  - TodoWrite
---

# Test agents

You are helping a developer validate agent triggering and functionality through systematic testing.

Test scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context agent-development --plugin --references triggering system-prompts` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If agent name provided: test that specific agent
   - If empty: list agents and offer to test specific ones

3. **Read agent definition** - Read the agent file to understand:
   - Frontmatter configuration
   - Triggering examples
   - System prompt structure
   - Tool restrictions

4. **Validate structure** - Run `oaps agent validate <name>` to check configuration:
   - Report any parsing errors
   - Note any warnings
   - Fix structure issues before proceeding with functional tests

5. **Analyze triggering examples** - Review the description for:
   - What explicit requests should trigger the agent
   - What proactive scenarios should trigger it
   - What variations should work

6. **Test explicit triggering** - For each example in the description:
   - Note the expected user message
   - Note the expected assistant response
   - Document how to test manually

7. **Test phrasing variations** - Plan tests with variations:
   - Rephrase requests differently
   - Use synonyms for key terms
   - Try shorter/longer versions

8. **Test proactive triggering** - If agent should trigger proactively:
   - Identify prerequisite actions
   - Plan statements that should trigger without explicit request

9. **Test negative cases** - Verify agent does NOT trigger when:
   - Request is similar but out of scope
   - A different agent should handle it

10. **Test functionality** - Once triggered, verify:
    - Agent follows its defined process
    - Meets quality standards
    - Produces correctly formatted output
    - Handles edge cases

11. **Present results** - Summarize test outcomes:
    - Triggering tests (explicit, variations, proactive, negative)
    - Functional tests
    - Edge cases that need attention
    - Recommendations for improvements

12. **Document findings** - If issues found, offer to:
    - Launch agent-developer agent to add triggering examples or clarify system prompt
    - Create todo items for tracking
    - Suggest using `/oaps:agent:write` for rewrites
