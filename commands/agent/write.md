---
description: Write a new agent with guided workflow
argument-hint: [agent-description]
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

# Write agent

You are helping a developer create a new Claude Code agent using a structured workflow. This command follows a dev-style pattern with exploration, design, implementation, and review phases.

Initial request: $ARGUMENTS

## Phase 1: Discovery

**Goal**: Understand what agent needs to be created

1. Create todo list with all phases
2. If agent description is unclear, ask user for:
   - What tasks should this agent handle autonomously?
   - When should Claude trigger this agent (proactively, on request, or both)?
   - What tools does it need access to?
   - Should it be project-specific or plugin-distributed?
3. Summarize understanding and confirm with user

---

## Phase 2: Exploration

**Goal**: Understand existing agents and patterns

1. Load skill context: `oaps skill context agent-development --plugin --references structure frontmatter triggering system-prompts`

2. Launch agent-explorer agent to analyze current state:

   ```
   Analyze the agent system to inform creating a new agent for: [agent description]

   1. List existing agents in .oaps/claude/agents/ and agents/
   2. Find similar agents that could serve as templates
   3. Identify patterns for frontmatter, triggering examples, and system prompts
   4. Note any namespace organization this new agent should follow
   5. Check for related agents this might interact with
   ```

3. Read key files the explorer identified

4. Present summary of relevant patterns and similar agents

---

## Phase 3: Clarifying Questions

**Goal**: Fill in gaps before designing

**CRITICAL**: Do not skip this phase.

1. Review exploration findings and original request
2. Identify underspecified aspects:
   - Exact agent location (project vs plugin)
   - Triggering scenarios (explicit, proactive, or both)
   - Tool restrictions needed
   - Model selection (inherit/haiku/sonnet/opus)
   - System prompt structure and key responsibilities
3. Present questions to user in organized list
4. Wait for answers before proceeding

---

## Phase 4: Design & Implementation

**Goal**: Design and implement the agent

1. Launch agent-developer agent with full context:

   ```
   Design and implement an agent based on these requirements:

   [Include: original request, exploration findings, user answers to questions]

   Follow the workflow:
   1. Choose appropriate location and filename
   2. Write frontmatter with name, description (with examples), model, color, tools
   3. Create system prompt with proper structure
   4. Include 2-4 triggering examples in description
   5. Validate with `oaps agent validate <name>`
   6. Create the agent file
   ```

2. Review the implementation
3. Present the agent to user with explanation:
   - What the agent does
   - When it triggers
   - What tools it can use
   - How it fits with existing agents

4. Ask user for approval before finalizing

---

## Phase 5: Review

**Goal**: Ensure agent quality and correctness

1. Launch agent-reviewer agent:

   ```
   Review the newly created agent: [agent name]

   Check for:
   - Frontmatter correctness (valid YAML, appropriate values)
   - Triggering quality (examples complete, cover key scenarios)
   - System prompt quality (structured, specific, actionable)
   - Tool restrictions (least privilege)
   - Organization (naming, placement)
   ```

2. Present review findings to user
3. If issues need fixing, launch another agent-developer agent to address them

---

## Phase 6: Summary

**Goal**: Document what was created

1. Mark all todos complete
2. Summarize:
   - Agent created with name and purpose
   - File location
   - Key design decisions
   - Triggering scenarios
   - Suggested next steps (testing, iteration)
