---
description: Brainstorm skills for the project
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

# Brainstorm skills

You are helping a developer identify opportunities for new Claude Code skills in their project.

## Phase 1: Understand Project

**Goal**: Understand the project's domain and structure

1. Read project documentation (README, CLAUDE.md)
2. Explore project structure to understand the domain
3. Identify key technologies and patterns used

---

## Phase 2: Analyze Existing Skills

**Goal**: Understand current skill coverage

1. Launch skill-explorer agent:

   ```
   Analyze the skill system to identify opportunities for new skills:

   1. List all existing skills in .oaps/claude/skills/ and skills/
   2. Categorize skills by domain (development, documentation, testing, etc.)
   3. Map what workflows are currently skill-guided
   4. Identify gaps in coverage
   5. Note project areas without skill support
   ```

2. Summarize findings about current state

---

## Phase 3: Identify Opportunities

**Goal**: Find valuable new skill opportunities

Consider skills for:

1. **Domain-specific guidance**
   - Project patterns and conventions
   - Architecture decisions
   - Domain terminology

2. **Workflow automation**
   - Common development tasks
   - Review processes
   - Testing approaches

3. **Documentation support**
   - API documentation
   - User guides
   - Architecture docs

4. **Integration patterns**
   - External services
   - Build systems
   - Deployment

---

## Phase 4: Present Recommendations

**Goal**: Actionable skill recommendations

For each recommended skill:

1. **Name and purpose**: What the skill would cover
2. **Trigger phrases**: When it should activate
3. **Key references**: What knowledge it would provide
4. **Key workflows**: What procedures it would guide
5. **Value**: Why this skill would help the project
6. **Effort estimate**: Simple (1 reference, 1 workflow) / Medium / Complex

Present skills in priority order based on:
- Frequency of relevant tasks
- Complexity of tasks requiring guidance
- Gap in existing coverage

---

## Phase 5: Next Steps

**Goal**: Path forward

1. Ask user which skills interest them most
2. For selected skills, offer to start `/oaps:skill:write` workflow
3. Note any skills that might be better as project-specific vs plugin
