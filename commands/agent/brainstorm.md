---
description: Brainstorm agents for the project
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

# Brainstorm agents

You are helping a developer identify agents that would benefit their project. Use the agent-explorer agent to analyze the current state and suggest valuable new agents.

## Workflow

1. **Load skill context** - Run `oaps skill context agent-development --plugin --references structure frontmatter` to get detailed guidance

2. **Launch exploration** - Use the Task tool to launch an agent-explorer agent:

   ```
   Analyze the agents in this project:
   1. List all existing agents in .oaps/claude/agents/ and agents/
   2. Categorize agents by purpose (review, generation, analysis, validation, orchestration)
   3. Identify organization patterns
   4. Find gaps in agent coverage
   5. Suggest new agents that would benefit this project

   Focus on: code review, code generation, testing, documentation, analysis, and workflow automation.
   ```

3. **Review findings** - Read any key files the agent identified

4. **Present suggestions** - Summarize the exploration results:
   - Current agent coverage
   - Organization patterns
   - Identified gaps
   - Prioritized list of suggested new agents
   - For each suggestion: problem it solves, triggering scenarios, rough system prompt structure

5. **Gather feedback** - Ask user which suggestions interest them using AskUserQuestion

6. **Next steps** - If user wants to implement an agent, suggest using `/oaps:agent:write` with the agent description
