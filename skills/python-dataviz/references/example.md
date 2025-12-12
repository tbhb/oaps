---
name: example
title: Example Reference
description: An example reference demonstrating the reference structure
required: false
principles:
  - TODO Add principles that guide this domain
  - Each principle should be actionable and specific
best_practices:
  - TODO Add best practices for this domain
  - Focus on common mistakes to avoid
checklist:
  - TODO Add checklist items for validation
  - Each item should be verifiable
commands:
  oaps skill validate <name>: Validate skill structure and content
references:
  https://docs.anthropic.com/en/docs/claude-code: Claude Code documentation
---

# Example Reference

TODO: Replace this with actual reference content.

This reference file demonstrates the structure of a skill reference:

1. **YAML Frontmatter** - Contains metadata for discovery and organization
2. **Principles** - High-level guidance that shapes decisions
3. **Best Practices** - Concrete recommendations based on experience
4. **Checklist** - Verifiable items for quality assurance
5. **Commands** - CLI commands relevant to this reference
6. **References** - External links for further reading

## Using References

References are loaded on-demand to keep context lean. To load this reference:

```bash
oaps skill context <skill-name> --references example
```

## Next Steps

1. Rename this file to match your reference topic (e.g., `api.md`, `patterns.md`)
2. Update the frontmatter metadata
3. Replace the body content with your actual documentation
4. Delete this file if no references are needed
