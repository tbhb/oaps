---
description: This skill should be used when the user asks to "brainstorm", "explore an idea", "refine a concept", "crystallize thinking", "capture an idea", "develop a hypothesis", or needs guidance on structured ideation, concept development, or idea documentation.
---

# Idea writing

This skill provides guidance for brainstorming, exploring, refining, and documenting ideas. It includes progressively-disclosed references on idea document structure, exploration patterns, expansion techniques, critique methods, and synthesis approaches for effective ideation.

## About idea documents

Idea documents capture concepts at various stages of development, from initial seeds to crystallized insights. They follow a structured lifecycle (seed, exploring, refining, crystallized, archived) that supports iterative development and connection discovery between related ideas.

**Storage location**: All ideas are stored in `.oaps/docs/ideas/` (hidden directory at project root).

**ID format**: `YYYYMMDD-HHmmss-slug` (e.g., `20251218-164449-worktree-management`)

## Critical: Always use CLI commands

**NEVER** search for idea files manually using Glob, Grep, or find. **ALWAYS** use these CLI commands:

| Command | Description |
|---------|-------------|
| `oaps idea list` | List all ideas |
| `oaps idea search <query>` | Search ideas by content |
| `oaps idea show <id>` | View full idea (use FULL ID from list/search) |
| `oaps idea create "<title>"` | Create new idea |
| `oaps idea resume [<id>]` | Get resume summary |

## Steps

**MANDATORY STEPS FOR ALL IDEA WRITING TASKS**

1. **Gather context** - Run `oaps skill orient idea-writing` to see available references and workflows

1. **Identify relevant references** - Review the references table from step 1 and select those matching your task

1. **Load dynamic context and references** - Run `oaps skill context idea-writing --references <names...>`

1. **Review loaded references and commands** - Read through the guidance. The **Allowed commands** table at the end of the output is authoritative for what commands can be run.

1. **Follow the workflow** - Adhere to the selected workflow's steps for capturing, exploring, refining, or crystallizing ideas.
