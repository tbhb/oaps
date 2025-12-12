---
description: Brainstorm slash commands for the project
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

# Brainstorm slash commands

You are helping a developer identify slash commands that would benefit their project. Use the command-explorer agent to analyze the current state and suggest valuable new commands.

## Workflow

1. **Load skill context** - Run `oaps skill context command-development --references structure dynamic-features` to get detailed guidance

2. **Launch exploration** - Use the Task tool to launch a command-explorer agent:

   ```
   Analyze the slash commands in this project:
   1. List all existing commands in .oaps/claude/commands/ and commands/
   2. Categorize commands by purpose (workflow, review, testing, deployment, docs)
   3. Identify namespace organization patterns
   4. Find gaps in command coverage
   5. Suggest new commands that would benefit this project

   Focus on: workflow automation, code review, testing, deployment, documentation, and developer experience.
   ```

3. **Review findings** - Read any key files the agent identified

4. **Present suggestions** - Summarize the exploration results:
   - Current command coverage
   - Namespace organization
   - Identified gaps
   - Prioritized list of suggested new commands
   - For each suggestion: problem it solves, expected arguments, rough prompt structure

5. **Gather feedback** - Ask user which suggestions interest them using AskUserQuestion

6. **Next steps** - If user wants to implement a command, suggest using `/oaps:command:write` with the command description
