---
name: requirement-writing
title: Requirement writing
description: Writing clear, testable requirements, acceptance criteria formats, avoiding ambiguity. Load when writing requirements or acceptance criteria.
commands: {}
principles:
  - "**Be specific**: Avoid vague terms like 'fast', 'easy', 'user-friendly'"
  - '**Be testable**: Every requirement should have a verifiable outcome'
  - '**Be atomic**: One requirement per statement'
  - '**Use "shall" consistently**: All requirements use "shall" for mandatory statements'
best_practices:
  - "**Active voice**: 'The system shall display...' not 'It shall be displayed...'"
  - "**Measurable criteria**: 'Response time under 200ms' not 'fast response'"
  - '**Avoid implementation details**: Describe what, not how'
  - '**Include negative requirements**: What the system must NOT do'
  - '**Define edge cases**: Explicitly state boundary behavior'
checklist:
  - Requirement uses active voice
  - Requirement is atomic (single testable statement)
  - Requirement avoids ambiguous terms
  - Requirement specifies measurable criteria where applicable
  - Acceptance criteria covers happy path and error cases
references: {}
---

## Writing testable requirements

### Avoid ambiguous terms

| Ambiguous     | Specific                       |
| ------------- | ------------------------------ |
| fast          | responds within 200ms          |
| user-friendly | completes in 3 clicks or fewer |
| secure        | encrypts data using AES-256    |
| reliable      | 99.9% uptime                   |
| easy          | requires no training           |
| flexible      | supports JSON and XML formats  |

### Requirement structure

```
[Subject] shall [action] [object] [condition/constraint]
```

All requirements in specifications are mandatory. Use "shall" consistently for all requirement statements.

Examples:

- The system shall display an error message when the user enters invalid credentials.
- The API shall return a 404 status code when the requested resource does not exist.
- The service shall cache responses for up to 5 minutes.

## Acceptance criteria formats

### Given-When-Then (Gherkin)

Best for behavior-driven specifications:

```gherkin
Given the user is logged in
  And the user has admin privileges
When the user clicks "Delete Account"
Then the system displays a confirmation dialog
  And the account is not deleted until confirmed
```

### Checklist format

Best for simple, discrete criteria:

```markdown
- [ ] User can create an account with email and password
- [ ] Password must be at least 8 characters
- [ ] Email verification is sent within 5 minutes
- [ ] Duplicate email addresses are rejected
```

### Structured format

Best for formal specifications:

```markdown
**AC-001**: Account creation validation
- **Preconditions**: User is on registration page
- **Input**: Valid email, password meeting requirements
- **Expected outcome**: Account created, verification email sent
- **Error conditions**:
  - Invalid email format: Display "Invalid email address"
  - Password too short: Display "Password must be at least 8 characters"
```

## Functional vs non-functional requirements

### Functional requirements

What the system does:

- "The system shall allow users to reset their password via email"
- "The API shall return paginated results for collections over 100 items"

### Non-functional requirements

How well the system performs:

- **Performance**: "Search results shall load within 500ms"
- **Scalability**: "The system shall support 10,000 concurrent users"
- **Security**: "Passwords shall be hashed using bcrypt with cost factor 12"
- **Reliability**: "The service shall maintain 99.95% uptime"
- **Usability**: "Core tasks shall be completable within 3 clicks"

## Implementation planning

While all requirements in a spec are mandatory, teams may prioritize implementation order using methods like:

### MoSCoW method (for backlog ordering)

- **Must have**: Critical for launch, implement first
- **Should have**: Important, implement next
- **Could have**: Desirable if time permits
- **Won't have**: Out of scope for this release

### Numerical priority (for triage)

- **P0**: Blocks release
- **P1**: High priority
- **P2**: Medium priority
- **P3**: Lower priority

Note: These methods are for implementation planning, not for specifying requirement optionality. All requirements in a spec are mandatory once approved.
