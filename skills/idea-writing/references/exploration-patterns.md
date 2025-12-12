---
name: exploration-patterns
title: Exploration patterns
description: Techniques for exploring ideas including question frameworks, prior art research, connection discovery, and constraint identification. Load when moving ideas from seed to exploring status.
commands: {}
principles:
  - '**Question first**: Good exploration starts with good questions'
  - '**Seek prior art**: Understand what exists before reinventing'
  - '**Find connections**: Ideas gain power when linked to others'
  - '**Name constraints**: Identify boundaries to define the solution space'
best_practices:
  - '**Use structured questioning**: Apply frameworks like 5 Whys or Socratic method'
  - '**Document research findings**: Record what you learn during exploration'
  - '**Map relationships**: Create visual or textual maps of idea connections'
  - '**Embrace constraints**: Limitations often spark creative solutions'
checklist:
  - Key questions identified and documented
  - Prior art research conducted
  - Related ideas linked
  - Constraints explicitly stated
  - Exploration notes recorded with dates
references:
  https://en.wikipedia.org/wiki/Five_whys: Five Whys technique
  https://en.wikipedia.org/wiki/Socratic_method: Socratic questioning
related:
  - document-structure
  - synthesis-patterns
---

## Question frameworks

### 5 Whys technique

Drill down to root causes or core motivations by asking "why" repeatedly.

**Process:**

1. State the idea or observation
2. Ask "Why?" and record the answer
3. Ask "Why?" about that answer
4. Repeat until reaching fundamental causes (typically 5 iterations)
5. Document the chain of reasoning

**Example:**

- Idea: We should add a notification system
- Why? Users miss important updates
- Why? They don't check the app regularly
- Why? The app doesn't surface time-sensitive information
- Why? We prioritized features over engagement patterns
- Why? We lacked user behavior data
- Root insight: Need user behavior analytics before notification design

### Socratic questioning

Systematic inquiry to clarify thinking and uncover assumptions.

**Question types:**

| Type | Purpose | Examples |
|------|---------|----------|
| Clarification | Define terms and scope | "What do you mean by...?" "Can you give an example?" |
| Assumptions | Surface hidden beliefs | "What are we assuming?" "Is this always true?" |
| Evidence | Examine support | "What evidence supports this?" "How do we know?" |
| Perspectives | Consider alternatives | "What would critics say?" "How might others view this?" |
| Implications | Explore consequences | "If this is true, what follows?" "What are the risks?" |
| Meta-questions | Examine the question | "Why is this important?" "What's the real question here?" |

### SCAMPER technique

Creative exploration through systematic modification.

- **S**ubstitute: What could be replaced?
- **C**ombine: What could be merged?
- **A**dapt: What could be borrowed from elsewhere?
- **M**odify: What could be changed in form or function?
- **P**ut to other uses: What else could this serve?
- **E**liminate: What could be removed?
- **R**earrange: What could be reordered or reversed?

## Prior art research

### Research strategy

1. **Define search terms**: Identify keywords and synonyms for your idea
2. **Search broadly first**: Cast a wide net across domains
3. **Document findings**: Record sources, key points, and relevance
4. **Analyze gaps**: Note what existing solutions lack
5. **Identify differentiators**: Clarify what makes your idea unique

### Sources to check

| Source type | Examples | Best for |
|-------------|----------|----------|
| Academic | Google Scholar, arXiv, ResearchGate | Theoretical foundations |
| Industry | Trade publications, company blogs | Current practices |
| Open source | GitHub, GitLab, package registries | Implementation patterns |
| Patents | Google Patents, USPTO | Novel approaches |
| Communities | Stack Overflow, Reddit, Discord | Practitioner insights |
| Standards | W3C, IETF, ISO | Established conventions |

### Documentation template

```markdown
### Prior art: [Name/Title]

**Source**: [URL or citation]
**Relevance**: High/Medium/Low
**Summary**: [2-3 sentence description]
**Strengths**: [What it does well]
**Gaps**: [What it lacks or misses]
**Applicability**: [How it relates to your idea]
```

## Connection discovery

### Finding related ideas

1. **Tag analysis**: Review tags for overlap with other ideas
2. **Domain mapping**: Identify ideas in the same problem space
3. **Temporal proximity**: Check ideas created around the same time
4. **Author patterns**: Look for themes in your own idea history
5. **Keyword search**: Search idea corpus for related terms

### Connection types

| Type | Description | Example |
|------|-------------|---------|
| Supports | One idea strengthens another | Caching supports performance goals |
| Conflicts | Ideas are mutually exclusive | Simplicity vs comprehensive features |
| Extends | One idea builds on another | Mobile app extends web platform |
| Combines | Ideas merge into something new | Search + recommendations = discovery |
| Contrasts | Ideas illuminate each other by difference | Sync vs async processing |
| Depends | One idea requires another | API requires authentication system |

### Mapping connections

Create a connection map in your notes:

```
IDEA-042 (this idea)
  |-- supports --> IDEA-015 (performance optimization)
  |-- extends --> IDEA-023 (user dashboard)
  |-- conflicts --> IDEA-031 (minimal interface)
  |-- depends --> IDEA-008 (authentication)
```

## Constraint identification

### Constraint categories

| Category | Questions to ask |
|----------|------------------|
| Technical | What are the platform/language limitations? |
| Resource | What time/budget/team constraints exist? |
| Regulatory | What compliance requirements apply? |
| Business | What strategic constraints exist? |
| User | What user capabilities or preferences limit options? |
| Integration | What existing systems must be accommodated? |
| Scale | What volume or growth considerations apply? |

### Constraint documentation

```markdown
## Constraints

### Must have (non-negotiable)
- [Constraint 1]: [Reason]
- [Constraint 2]: [Reason]

### Should have (important but flexible)
- [Constraint 3]: [Trade-off if violated]
- [Constraint 4]: [Trade-off if violated]

### Nice to have (preferences)
- [Constraint 5]: [Benefit if satisfied]
```

### Using constraints creatively

Constraints often spark innovation:

1. **Embrace limits**: Work within constraints rather than fighting them
2. **Question necessity**: Ask if constraints are real or assumed
3. **Find workarounds**: Look for creative solutions within bounds
4. **Combine constraints**: Multiple constraints can suggest unique solutions
5. **Flip constraints**: Consider the opposite of each constraint
