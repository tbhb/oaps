---
name: document-structure
title: Idea document structure
description: Idea document format, frontmatter fields, status values, section organization. Load when creating new ideas or understanding document conventions.
commands:
  tree <path>: View idea directory structure
  ls <path>: List idea files
principles:
  - '**Capture early, refine later**: Document raw ideas before they fade'
  - '**Progressive development**: Ideas evolve through defined stages'
  - '**Connection discovery**: Link related ideas to find patterns'
  - '**Preserve context**: Record the circumstances that sparked the idea'
best_practices:
  - '**Use consistent frontmatter**: Include all required metadata fields'
  - '**Update status regularly**: Move ideas through the lifecycle stages'
  - '**Link related ideas**: Cross-reference connected concepts'
  - '**Tag for discovery**: Use meaningful tags for categorization'
  - '**Record provenance**: Note sources and inspirations'
checklist:
  - Frontmatter includes required fields (id, title, status, type, created)
  - Status reflects current development stage
  - Core concept section captures the essential idea
  - Context section explains why/when the idea emerged
  - Related ideas are linked in frontmatter
references: {}
---

## Idea document format

### Required frontmatter fields

```yaml
---
id: IDEA-001           # Unique identifier
title: Idea title      # Descriptive title
status: seed           # Current lifecycle stage
type: general          # Idea category (general, product, technical, process, research)
created: 2024-01-15    # Creation date
updated: 2024-01-15    # Last update date
author: Name           # Idea author
tags: []               # Discovery tags
related_ideas: []      # Links to connected ideas (by ID)
references: []         # External sources and inspirations
workflow: default      # Workflow used for development
---
```

### Status values and emojis

| Status      | Emoji | Description                                    |
| ----------- | ----- | ---------------------------------------------- |
| seed        | seed         | Initial capture, minimal development           |
| exploring   | mag          | Active investigation, gathering information    |
| refining    | arrows_counterclockwise          | Iterating on core concept, addressing gaps     |
| crystallized| gem          | Fully developed, clear and actionable          |
| archived    | package          | Preserved but no longer active development     |

### Document structure

```markdown
<!-- IDEA HEADER START -->
# [Status Emoji] [Title]

**ID**: [ID] | **Status**: [Status] | **Type**: [Type]
**Created**: [Date] | **Updated**: [Date] | **Author**: [Author]
**Tags**: [tag1, tag2, tag3]
<!-- IDEA HEADER END -->

## Core concept

[The essential idea in 2-3 sentences]

## Context

[Why did this idea emerge? What problem does it address? What triggered it?]

## Questions to explore

- [ ] [Question 1]
- [ ] [Question 2]
- [ ] [Question 3]

## Prior art

[What related work exists? How does this idea compare?]

## Connections

[How does this relate to other ideas? What patterns emerge?]

## Development notes

### [Date] - [Note title]

[Notes from exploration/refinement sessions]

## Open questions

[Unresolved questions that need further thought]

## Next steps

- [ ] [Action 1]
- [ ] [Action 2]

<!-- IDEA FOOTER START -->
---
**Related ideas**: [IDEA-XXX](link), [IDEA-YYY](link)
**References**: [Source 1](url), [Source 2](url)
<!-- IDEA FOOTER END -->
```

## Idea types

### General

Default type for miscellaneous ideas without specific domain focus.

### Product

Ideas for new products, features, or user-facing capabilities. Includes value proposition, target users, and success metrics.

### Technical

Technical concepts, architectural patterns, or implementation approaches. Includes trade-offs, constraints, and proof of concept considerations.

### Process

Process improvements, workflow optimizations, or operational changes. Includes current state analysis and transition planning.

### Research

Research directions, hypotheses to test, or areas to investigate. Includes methodology considerations and validation approaches.

## Identification scheme

Format: `IDEA-NNN` where NNN is a zero-padded sequential number.

Examples:

- `IDEA-001`: First idea in the collection
- `IDEA-042`: Forty-second idea
- `IDEA-137`: One hundred thirty-seventh idea

Generate new IDs by finding the highest existing ID and incrementing.
