---
description: Write a new hook rule with guided workflow
argument-hint: [rule-description]
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

# Write hook rule

You are helping a developer create a new hook rule using a structured workflow. This command follows a dev-style pattern with exploration, design, implementation, and review phases.

Initial request: $ARGUMENTS

## Phase 1: Discovery

**Goal**: Understand what rule needs to be created

1. Create todo list with all phases
2. If rule description is unclear, ask user for:
   - What problem are they solving?
   - What event should trigger the rule?
   - What should happen when triggered (block, warn, log)?
   - Any specific conditions or edge cases?
3. Summarize understanding and confirm with user

---

## Phase 2: Exploration

**Goal**: Understand existing hooks and patterns

1. Load skill context: `oaps skill context hook-rule-writing --references events expressions actions`

2. Launch hook-explorer agent to analyze current state:

   ```
   Analyze the hook system to inform creating a new rule for: [rule description]

   1. Run `oaps hooks list` to see existing rules
   2. Read hook configuration files
   3. Find similar rules that could serve as templates
   4. Identify patterns for conditions, actions, and priorities
   5. Note any rules this new rule might interact with
   ```

3. Read key files the explorer identified

4. Present summary of relevant patterns and similar rules

---

## Phase 3: Clarifying Questions

**Goal**: Fill in gaps before designing

**CRITICAL**: Do not skip this phase.

1. Review exploration findings and original request
2. Identify underspecified aspects:
   - Exact matching criteria (paths, commands, patterns)
   - Edge cases and exceptions
   - Priority relative to existing rules
   - Whether rule should be terminal
3. Present questions to user in organized list
4. Wait for answers before proceeding

---

## Phase 4: Design & Implementation

**Goal**: Design and implement the hook rule

1. Launch hook-developer agent with full context:

   ```
   Design and implement a hook rule based on these requirements:

   [Include: original request, exploration findings, user answers to questions]

   Follow the write workflow:
   1. Create rule skeleton with unique ID
   2. Define events array
   3. Write condition expression
   4. Configure actions matching result type
   5. Set priority and flags
   6. Validate with `oaps hooks validate`
   7. Add to appropriate configuration file
   ```

2. Review the implementation
3. Present the rule to user with explanation:
   - What the rule does
   - When it triggers
   - What actions it takes
   - How it interacts with existing rules

4. Ask user for approval before finalizing

---

## Phase 5: Review

**Goal**: Ensure rule quality and correctness

1. Launch hook-reviewer agent:

   ```
   Review the newly created hook rule: [rule ID]

   Check for:
   - Condition correctness (matches intended scenarios)
   - Action appropriateness (matches result type)
   - Security concerns
   - Maintainability
   - Interaction with existing rules
   ```

2. Present review findings to user
3. If issues need fixing, launch another hook-developer agent to address them

---

## Phase 6: Summary

**Goal**: Document what was created

1. Mark all todos complete
2. Summarize:
   - Rule created with ID and purpose
   - Configuration file modified
   - Key design decisions
   - Suggested next steps (testing, monitoring)
