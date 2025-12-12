---
description: Review existing skills for quality
argument-hint: [skill-name-or-path]
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

# Review skill

You are helping a developer review a Claude Code skill for quality, structure, and effectiveness.

Target: $ARGUMENTS

## Phase 1: Identify Target

**Goal**: Determine what to review

1. If no target specified, ask user what skill to review
2. Locate the skill:
   - Check `.oaps/claude/skills/` for project skills
   - Check `skills/` for plugin skills
3. Confirm the skill exists and summarize what you'll review

---

## Phase 2: Load Context

**Goal**: Prepare for review

1. Load skill context: `oaps skill context skill-development --references skill-structure skill-references`

2. Read the target skill's structure:
   - skill.md
   - All files in references/
   - All files in workflows/
   - All files in templates/ (if exists)

---

## Phase 3: Review

**Goal**: Comprehensive skill review

1. Launch skill-reviewer agent:

   ```
   Review the skill: [skill name or path]

   Perform comprehensive review covering:
   - Structure correctness (directory layout, required files)
   - skill.md quality (frontmatter, description, steps)
   - Reference quality (progressive disclosure, completeness, organization)
   - Workflow quality (steps, references, default designation)
   - Template quality (syntax, variables, output format)
   - Progressive disclosure (appropriate content placement)

   Use confidence scoring and only report issues ≥ 80 confidence.
   ```

2. Present review findings organized by severity

---

## Phase 4: Summary

**Goal**: Actionable summary

1. List high-priority issues that need attention
2. Provide specific fix suggestions for each issue
3. Note any strengths worth preserving
4. Suggest next steps (fixes to make, tests to run)
