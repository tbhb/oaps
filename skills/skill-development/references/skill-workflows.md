---
name: skill-workflows
title: Documenting workflows in skills
description: Guidance on documenting workflows within skills. Covers workflow patterns, writing style, and when to place workflows in SKILL.md vs references.
principles:
  - Workflows guide Claude through multi-step procedures
  - Use imperative form for clear, actionable instructions
  - Name workflows using verb-noun convention (e.g., create-spec, review-req)
  - Core workflows belong in SKILL.md; detailed variations go in references
  - Workflows should be sequential and unambiguous
best_practices:
  - "**Verb-noun naming**: Name workflows as `verb-noun` (e.g., `create-spec`, `review-req`, `add-test`)"
  - "**Numbered steps**: Use numbered lists for sequential procedures"
  - "**Imperative form**: Write 'Create the file' not 'You should create the file'"
  - "**Decision points**: Clearly mark conditional branches"
  - "**Completion criteria**: State when each step is complete"
  - "**Error handling**: Include what to do when things go wrong"
checklist:
  - Workflow name follows verb-noun convention
  - Steps are numbered and sequential
  - Instructions use imperative form
  - Decision points are clearly marked
  - Each step has clear completion criteria
  - Error handling is included where appropriate
related:
  - skill-references
---

## What are workflows

Workflows are multi-step procedures that guide Claude through specific tasks. They provide the procedural knowledge that transforms Claude from a general-purpose assistant into a specialized agent for a particular domain.

Effective workflows:

- Break complex tasks into clear, sequential steps
- Include decision points for handling variations
- Specify completion criteria for each step
- Handle common errors and edge cases

## Workflow naming conventions

Workflow names MUST follow **verb-noun** convention. The verb describes the action, and the noun describes what is being acted upon. This convention ensures workflows are immediately understandable from their name.

### Format

```
<verb>-<noun>[-<qualifier>]
```

### Common verbs

| Verb     | Use for                                       |
|----------|-----------------------------------------------|
| `add`    | Creating new items within existing structures |
| `create` | Creating new top-level entities               |
| `delete` | Removing items permanently                    |
| `move`   | Relocating items between locations            |
| `remove` | Taking items out of structures                |
| `review` | Evaluating quality or completeness            |
| `split`  | Dividing into multiple parts                  |
| `update` | Modifying existing items                      |

### Examples

**Good:**

- `create-spec` - Create a new specification
- `review-req` - Review requirements
- `add-test` - Add test cases
- `update-spec` - Update a specification
- `delete-req` - Delete requirements
- `split-spec` - Split specification into multiple files
- `move-spec-items` - Move items between spec pages
- `review-spec-organization` - Review spec file organization

**Avoid:**

- `spec-create` - Noun-verb (wrong order)
- `req-add` - Noun-verb (wrong order)
- `test-review` - Noun-verb (wrong order)
- `new-spec` - Adjective-noun (no verb)
- `specification-creation` - Too verbose

### Rationale

Verb-noun ordering aligns with:

1. **Imperative form**: Matches how workflow steps are written ("Create the spec")
2. **Command patterns**: Follows CLI conventions (`git add`, `git commit`)
3. **Discoverability**: Users can search by action ("what can I create?") or target ("what can I do with specs?")
4. **Consistency**: All OAPS skills use this convention

## When to document workflows

### Core workflows in SKILL.md

Place workflows in SKILL.md when:

- The workflow is central to the skill's purpose
- Every use of the skill involves this workflow
- The workflow is relatively concise (under 500 words)

### Detailed workflows in references

Move workflows to references when:

- The workflow has many variations or branches
- The workflow is used only for specific subtasks
- Including it would make SKILL.md too long
- The workflow requires extensive examples

### Hybrid approach

Use SKILL.md for the main workflow with references for details:

```markdown
## Main workflow

1. Gather requirements (Step 1)
2. Design the solution (Step 2)
3. Implement the solution (Step 3)
4. Validate the result (Step 4)

For detailed implementation patterns, see `references/implementation-patterns.md`.
```

## Writing style

### Use imperative form

Write instructions as commands, not suggestions:

**Good:**

```markdown
1. Create the configuration file
2. Add the required fields
3. Validate the configuration
```

**Avoid:**

```markdown
1. You should create the configuration file
2. The next step is to add the required fields
3. Then you can validate the configuration
```

### Be specific and actionable

**Good:**

```markdown
1. Run `oaps skill create my-skill` to initialize the skill directory
```

**Avoid:**

```markdown
1. Initialize the skill using the appropriate command
```

### State completion criteria

**Good:**

```markdown
1. Run the tests until all pass
2. Verify the output matches the expected format
3. Confirm no linting errors remain
```

**Avoid:**

```markdown
1. Run the tests
2. Check the output
3. Fix any issues
```

## Workflow patterns

### Linear workflow

For straightforward sequential tasks:

```markdown
## Creating a new feature

1. Create the feature branch: `git checkout -b feat/my-feature`
2. Implement the feature in `src/features/`
3. Add tests in `tests/unit/`
4. Run `just test` to verify all tests pass
5. Run `just lint` to check code quality
6. Commit with conventional commit message
```

### Conditional workflow

For tasks with decision points:

```markdown
## Handling user input

1. Validate the input format

2. Check input type:
   - **If file path**: Read the file and extract content
   - **If URL**: Fetch the URL and parse response
   - **If raw text**: Use directly

3. Process the extracted content

4. Return formatted result
```

### Iterative workflow

For tasks that may require multiple passes:

```markdown
## Fixing test failures

1. Run `just test` to identify failing tests

2. For each failing test:
   1. Read the test file to understand the expected behavior
   2. Read the implementation being tested
   3. Identify the discrepancy
   4. Fix either the test or implementation
   5. Re-run the specific test to verify

3. Run `just test` again to confirm all tests pass

4. If new failures appear, repeat from step 2
```

### Checklist workflow

For verification tasks:

```markdown
## Pre-commit checklist

Before committing, verify:

- [ ] All tests pass: `just test`
- [ ] No linting errors: `just lint`
- [ ] Type checking passes: `just lint-python`
- [ ] Documentation is updated
- [ ] Commit message follows conventional commits
```

## Decision points

### Marking branches clearly

Use clear formatting for decision points:

```markdown
3. Determine the appropriate action:

   **If the file exists:**
   - Read the current content
   - Merge with new content
   - Write the merged result

   **If the file does not exist:**
   - Create the file with new content
   - Set appropriate permissions
```

### Nested decisions

For complex decision trees:

```markdown
3. Handle the response:

   **If successful (2xx status):**
   - Parse the response body
   - Extract required fields
   - Continue to step 4

   **If client error (4xx status):**
   - **If 401 Unauthorized**: Refresh credentials and retry
   - **If 404 Not Found**: Log warning and skip
   - **If other 4xx**: Report error to user

   **If server error (5xx status):**
   - Wait 5 seconds
   - Retry up to 3 times
   - If still failing, report error
```

## Error handling

### Inline error handling

For simple error cases:

```markdown
3. Run the build command: `just build`
   - If build fails, check the error output and fix the issue before continuing
```

### Dedicated error sections

For complex error handling:

```markdown
## Workflow

1. Fetch the data from the API
2. Parse the response
3. Store in database

## Error handling

### API errors

- **Connection timeout**: Check network connectivity; retry after 30 seconds
- **Rate limited (429)**: Wait for the Retry-After header duration
- **Server error (5xx)**: Retry up to 3 times with exponential backoff

### Parse errors

- **Invalid JSON**: Log the raw response; report to user
- **Missing fields**: Use default values where safe; warn about missing data
```

## Linking workflows and references

### Reference detailed steps

```markdown
## Main workflow

1. Set up the environment
2. Configure authentication (see `references/authentication.md`)
3. Run the migration
4. Verify the results
```

### Reference patterns and examples

```markdown
## Creating tests

1. Identify what to test
2. Choose the appropriate test pattern (see `references/testing-patterns.md`)
3. Write the test
4. Verify the test passes
```

### Reference troubleshooting

```markdown
## Deployment workflow

1. Build the package
2. Run pre-deployment checks
3. Deploy to staging
4. Verify staging deployment
5. Deploy to production

If any step fails, see `references/troubleshooting.md` for common issues.
```

## Examples

### Good workflow documentation

From a hypothetical `database-migration` skill:

```markdown
## Running migrations

1. Check current migration status: `oaps db status`

2. Review pending migrations in `migrations/pending/`

3. For each pending migration:
   1. Read the migration file to understand changes
   2. Verify the migration is safe for the current data
   3. Run in dry-run mode: `oaps db migrate --dry-run`
   4. If dry-run succeeds, run for real: `oaps db migrate`

4. Verify the migration completed:
   - Check `oaps db status` shows no pending migrations
   - Run `oaps db verify` to check data integrity
   - Test affected queries in the application

5. If any issues arise, see `references/rollback-procedures.md`
```

### Workflow with clear completion criteria

```markdown
## Code review workflow

1. Read the PR description to understand the intent
   - **Complete when**: Intent and scope are clear

2. Review each changed file for correctness
   - **Complete when**: All logic is understood and verified

3. Check for test coverage
   - **Complete when**: New code has appropriate tests

4. Verify code style and conventions
   - **Complete when**: No style violations remain

5. Provide feedback or approve
   - **Complete when**: Review comments are submitted or PR is approved
```
