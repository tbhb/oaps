---
description: Identify potential hook rules from usage patterns
allowed-tools:
  - AskUserQuestion
  - Bash(oaps:*)
  - Read
  - Skill
  - Task
  - TodoWrite
---

# Identify hook candidates

You are helping a developer discover potential hook rules based on their actual Claude Code usage patterns. Analyze the hook log to find repeated patterns that could benefit from automation.

## Workflow

1. **Load skill context** - Run `oaps skill context hook-rule-writing --references patterns` to get detailed guidance

2. **Analyze usage patterns** - Run the candidates command to find repeated patterns:

   ```bash
   oaps hooks candidates --format plain --since 7d
   ```

3. **Review the output** - The analysis will show:
   - **OAPS Command Chains**: Commands using `oaps` with `&&`, `|`, or `;` (high-value automation candidates)
   - **Repeated Bash Commands**: Frequently executed commands
   - **Tool Patterns**: Frequent file access patterns (Read/Write)

4. **Prioritize candidates** - For each category, evaluate:
   - Would a hook rule add value here?
   - Is the pattern consistent enough to automate?
   - What would the hook do (guide, warn, block, or modify)?

5. **Present findings** - Summarize the analysis:
   - Top 3-5 automation opportunities
   - For each: the pattern, proposed hook type, and expected benefit
   - Any patterns that should NOT be hooks (explain why)

6. **Gather feedback** - Ask the user which candidates interest them using AskUserQuestion

7. **Next steps** - For candidates the user wants to implement:
   - If simple: Suggest using `/hook:write` with the pattern description
   - If complex: Suggest using `/hook:brainstorm` to explore the design space first

## Tips

- **Lower thresholds** if few candidates appear: `oaps hooks candidates -n 3`
- **Expand time range** for more data: `oaps hooks candidates --since 30d`
- **Check for errors** that might indicate missing guardrails: `oaps hooks errors --since 7d`
- Focus on **workflow automation** - chains of commands that always run together
- Look for **consistency patterns** - things that should always happen a certain way
