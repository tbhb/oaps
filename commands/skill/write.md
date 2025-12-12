---
description: Write a new skill with guided workflow
argument-hint: [skill-description]
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

# Write skill

You are helping a developer create a new Claude Code skill using a structured workflow. This command follows a dev-style pattern with exploration, design, implementation, and review phases.

Initial request: $ARGUMENTS

## Phase 1: Discovery

**Goal**: Understand what skill needs to be created

1. Create todo list with all phases
2. If skill description is unclear, ask user for:
   - What domain or task does this skill cover?
   - What references will it need?
   - What workflows should it support?
   - Should it be project-specific or plugin-distributed?
3. Summarize understanding and confirm with user

---

## Phase 2: Exploration

**Goal**: Understand existing skills and patterns

1. Load skill context: `oaps skill context skill-development --references skill-structure skill-references skill-workflows`

2. Launch skill-explorer agent to analyze current state:

   ```
   Analyze the skill system to inform creating a new skill for: [skill description]

   1. List existing skills in .oaps/claude/skills/ and skills/
   2. Find similar skills that could serve as templates
   3. Identify patterns for structure, references, and workflows
   4. Note any organization this new skill should follow
   5. Check for related skills this might interact with
   ```

3. Read key files the explorer identified

4. Present summary of relevant patterns and similar skills

---

## Phase 3: Clarifying Questions

**Goal**: Fill in gaps before designing

**CRITICAL**: Do not skip this phase.

1. Review exploration findings and original request
2. Identify underspecified aspects:
   - Exact skill location (project vs plugin)
   - Reference organization
   - Workflow structure
   - Template needs
   - Activation triggers
3. Present questions to user in organized list
4. Wait for answers before proceeding

---

## Phase 4: Design & Implementation

**Goal**: Design and implement the skill

1. Launch skill-developer agent with full context:

   ```
   Design and implement a skill based on these requirements:

   [Include: original request, exploration findings, user answers to questions]

   Follow the workflow:
   1. Choose appropriate location and directory name
   2. Create skill.md with proper frontmatter
   3. Plan and create references
   4. Plan and create workflows
   5. Add templates if needed
   6. Validate with `oaps skill validate`
   7. Create all skill files
   ```

2. Review the implementation
3. Present the skill to user with explanation:
   - What the skill covers
   - How to activate it
   - What references it includes
   - What workflows it supports
   - How it fits with existing skills

4. Ask user for approval before finalizing

---

## Phase 5: Review

**Goal**: Ensure skill quality and correctness

1. Launch skill-reviewer agent:

   ```
   Review the newly created skill: [skill name]

   Check for:
   - Structure correctness (directory layout, frontmatter)
   - skill.md quality (description, steps)
   - Reference quality (progressive disclosure, completeness)
   - Workflow quality (clear steps, proper references)
   - Template quality (if applicable)
   ```

2. Present review findings to user
3. If issues need fixing, launch another skill-developer agent to address them

---

## Phase 6: Summary

**Goal**: Document what was created

1. Mark all todos complete
2. Summarize:
   - Skill created with name and purpose
   - Directory location
   - Key design decisions
   - How to activate the skill
   - Suggested next steps (testing, documentation)
