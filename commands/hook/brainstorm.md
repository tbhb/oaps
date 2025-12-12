---
description: Brainstorm hook rules for the project
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

# Brainstorm hook rules

You are helping a developer identify hook rules that would benefit their project. Use the hook-explorer agent to analyze the current state and suggest valuable new rules.

## Workflow

1. **Load skill context** - Run `oaps skill context hook-rule-writing --references patterns` to get detailed guidance

2. **Launch exploration** - Use the Task tool to launch a hook-explorer agent:

   ```
   Analyze the hook rules in this project:
   1. List all existing rules with `oaps hooks list`
   2. Read hook configuration files
   3. Identify rule categories and patterns
   4. Find gaps in event coverage
   5. Suggest new rules that would benefit this project

   Focus on: guardrails, automation opportunities, observability needs, and guidance rules.
   ```

3. **Review findings** - Read any key files the agent identified

4. **Present suggestions** - Summarize the exploration results:
   - Current rule coverage
   - Identified gaps
   - Prioritized list of suggested new rules
   - For each suggestion: problem it solves, target event, rough condition logic

5. **Gather feedback** - Ask user which suggestions interest them using AskUserQuestion

6. **Next steps** - If user wants to implement a rule, suggest using `/hook:write` with the rule description
