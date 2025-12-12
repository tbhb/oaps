---
name: anatomy
title: Skill anatomy and structure
description: Core concepts, components, and progressive disclosure design for Claude Code skills
related:
  - skill-references
  - skill-workflows
  - templating
principles:
  - Skills are modular, self-contained packages that extend Claude's capabilities
  - Progressive disclosure manages context efficiently through four-level loading
  - Information lives in either SKILL.md or references, not both
best_practices:
  - Keep SKILL.md under 2,000 words
  - Use scripts for deterministic or repeatedly rewritten code
  - Use references for detailed documentation loaded as needed
  - Use assets for output files not loaded into context
checklist:
  - SKILL.md has proper YAML frontmatter (name, description, version)
  - Description uses third-person with specific trigger phrases
  - Progressive disclosure principle applied (lean SKILL.md, detailed references)
  - Resources organized in appropriate directories (scripts, references, assets)
commands:
  oaps skill create <name>: Create a new skill from template
  oaps skill validate <name>: Validate skill structure and content
  oaps skill save --message "<msg>" <name>: Commit skill with validation
references:
  https://docs.anthropic.com/en/docs/claude-code: Claude Code documentation
---

# Skill anatomy and structure

Skills are modular, self-contained packages that extend Claude's capabilities by providing specialized knowledge, workflows, and tools. They transform Claude from a general-purpose agent into a specialized agent equipped with procedural knowledge that no model can fully possess.

## What skills provide

1. **Specialized workflows** - Multi-step procedures for specific domains (see `references/skill-workflows.md`)
1. **Tool integrations** - Instructions for working with specific file formats or APIs
1. **Domain expertise** - Company-specific knowledge, schemas, business logic
1. **Bundled resources** - Scripts, references, and assets for complex and repetitive tasks (see `references/skill-references.md`)
1. **Jinja templating** - Dynamic content in references and workflows (see `references/templating.md`)
1. **Project overrides** - Extend or customize builtin skills (see `references/overrides.md`)

## Skill directory structure

Every skill consists of a required SKILL.md file and optional bundled resources:

```text
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
├── workflows/             - Task-specific multi-step procedures
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation loaded into context as needed
    ├── templates/        - Jinja2 templates for generating content
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

## SKILL.md requirements

**Metadata Quality:** The `name` and `description` in YAML frontmatter determine when Claude will use the skill. Be specific about what the skill does and when to use it. Use third-person (e.g. "This skill should be used when..." instead of "Use this skill when...").

**Writing style:** Write the entire skill using **imperative/infinitive form** (verb-first instructions), not second person. Use objective, instructional language (e.g., "To accomplish X, do Y" rather than "You should do X").

**Keep SKILL.md lean:** Target 1,500-2,000 words for the body. Move detailed content to references:

- Detailed patterns → `references/patterns.md`
- Advanced techniques → `references/advanced.md`
- Migration guides → `references/migration.md`
- API references → `references/api-reference.md`

## Bundled resources

### Scripts (`scripts/`)

Executable code (Python/Bash/etc.) for tasks that require deterministic reliability or are repeatedly rewritten.

- **When to include**: When the same code is being rewritten repeatedly or deterministic reliability is needed
- **Example**: `scripts/rotate_pdf.py` for PDF rotation tasks
- **Benefits**: Token efficient, deterministic, may be executed without loading into context
- **Note**: Scripts may still need to be read by Claude for patching or environment-specific adjustments

### References (`references/`)

Documentation and reference material intended to be loaded as needed into context to inform Claude's process and thinking.

- **When to include**: For documentation that Claude should reference while working
- **Examples**: `references/finance.md` for financial schemas, `references/mnda.md` for company NDA template
- **Use cases**: Database schemas, API documentation, domain knowledge, company policies, detailed workflow guides
- **Benefits**: Keeps SKILL.md lean, loaded only when Claude determines it's needed
- **Best practice**: If files are large (>10k words), include grep search patterns in SKILL.md
- **Avoid duplication**: Information should live in either SKILL.md or references files, not both

For detailed guidance on creating and organizing references, see `references/skill-references.md`. For Jinja templating in references, see `references/templating.md`.

### Templates (`templates/`)

Jinja2 template files for generating dynamic content. Templates use the `.j2` extension and support the full Jinja2 feature set.

- **When to include**: When generating repetitive content with variable substitution
- **Examples**: `templates/skill.md.j2` for skill templates, `templates/workflow.md.j2` for workflow templates
- **Benefits**: Consistent output format, reduces manual editing
- **Note**: Templates are rendered at runtime with context from the skill and user

For detailed guidance on Jinja templating, see `references/templating.md`.

### Assets (`assets/`)

Files not intended to be loaded into context, but rather used within the output Claude produces.

- **When to include**: When the skill needs files that will be used in the final output
- **Examples**: `assets/logo.png` for brand assets, `assets/slides.pptx` for PowerPoint templates
- **Use cases**: Templates, images, icons, boilerplate code, fonts, sample documents
- **Benefits**: Separates output resources from documentation, enables Claude to use files without loading them into context

### Workflows (`workflows/`)

Task-specific multi-step procedures that guide Claude through specific operations. Each workflow specifies which references should be loaded for that task.

- **When to include**: When the skill supports multiple distinct tasks
- **Examples**: `workflows/default.md` for main workflow, `workflows/review.md` for review tasks
- **Benefits**: Task-specific guidance, automatic reference loading
- **Structure**: YAML frontmatter with `name`, `description`, `references` array, followed by numbered steps

For detailed guidance on writing workflows, see `references/skill-workflows.md`.

## Progressive disclosure design principle

Skills use a four-level loading system to manage context efficiently:

1. **Metadata (name + description)** - Always in context (~100 words)
1. **SKILL.md body** - When skill triggers (\<5k words)
1. **Bundled resources** - As needed by Claude (Unlimited\*)
1. **Retrieved context** - From `Bash` tool calls to `oaps` CLI context commands (Unlimited\*)

\*Unlimited because scripts and CLI commands can be executed without reading into context window.
