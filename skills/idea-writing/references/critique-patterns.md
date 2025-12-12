---
name: critique-patterns
title: Critique patterns
description: Techniques for evaluating ideas including assumption identification, weakness surfacing, counter-argument generation, and risk assessment. Load when refining or challenging ideas.
commands: {}
principles:
  - '**Steel man first**: Understand the idea at its strongest before critiquing'
  - '**Separate idea from ego**: Critique the idea, not the person'
  - '**Seek disconfirmation**: Actively look for reasons the idea might fail'
  - '**Balance criticism with construction**: Pair problems with potential solutions'
best_practices:
  - '**Document assumptions explicitly**: Make hidden beliefs visible'
  - "**Generate counter-arguments**: Challenge your own thinking"
  - '**Assess risks systematically**: Categorize and prioritize concerns'
  - '**Use multiple critique lenses**: Technical, business, user, operational'
checklist:
  - Key assumptions identified and documented
  - Weaknesses acknowledged honestly
  - Counter-arguments generated
  - Risks assessed with severity and likelihood
  - Critique balanced with constructive suggestions
references: {}
related:
  - exploration-patterns
  - synthesis-patterns
---

## Assumption identification

### Why surface assumptions

Every idea rests on assumptions. Unstated assumptions become hidden risks:

- They may prove false
- Different stakeholders may assume differently
- They constrain solution space invisibly
- They create blind spots in planning

### Assumption categories

| Category | Questions | Examples |
|----------|-----------|----------|
| User | Who uses this? What do they need? | "Users want real-time updates" |
| Technical | What technology capabilities exist? | "The API can handle 1000 RPS" |
| Market | What market conditions hold? | "Competitors won't copy this quickly" |
| Resource | What resources are available? | "We can hire two more engineers" |
| Timeline | How long will things take? | "Integration takes 2 weeks" |
| Dependency | What else must happen? | "Legal will approve the approach" |

### Assumption documentation template

```markdown
## Assumptions

### Critical assumptions (if wrong, idea fails)
| Assumption | Evidence for | Evidence against | How to validate |
|------------|--------------|------------------|-----------------|
| [Assumption 1] | [Support] | [Concerns] | [Validation approach] |

### Supporting assumptions (if wrong, idea needs adjustment)
| Assumption | Impact if wrong | Alternative |
|------------|-----------------|-------------|
| [Assumption 1] | [What changes] | [Backup plan] |

### Background assumptions (generally accepted)
- [Assumption that's reasonably safe]
- [Another reasonable assumption]
```

### Validating assumptions

For each critical assumption:

1. **State it clearly**: Write it as a testable proposition
2. **Gather evidence**: What supports or contradicts it?
3. **Design validation**: How could you test it cheaply?
4. **Set triggers**: What would indicate it's wrong?
5. **Plan contingencies**: What if it proves false?

## Weakness surfacing

### Pre-mortem technique

Imagine the idea has failed. Work backward to identify causes.

**Process:**

1. Assume the idea was implemented and failed completely
2. Ask: "What went wrong?"
3. Generate as many failure causes as possible
4. Categorize by type and likelihood
5. Identify which weaknesses are addressable

### Weakness categories

| Category | Description | Questions |
|----------|-------------|-----------|
| Design flaws | Fundamental concept problems | "Is the core approach sound?" |
| Execution risks | Implementation challenges | "Can we actually build this?" |
| Adoption barriers | User acceptance issues | "Will people use this?" |
| Resource gaps | Missing capabilities | "Do we have what we need?" |
| External factors | Environmental threats | "What could change outside our control?" |
| Integration issues | System compatibility | "Does this work with existing systems?" |

### Weakness documentation

```markdown
## Known weaknesses

### Critical weaknesses (must address)
- **[Weakness 1]**: [Description]
  - Impact: [What happens if not addressed]
  - Mitigation: [Potential solution or workaround]

### Significant weaknesses (should address)
- **[Weakness 2]**: [Description]
  - Impact: [Consequences]
  - Mitigation: [Approach]

### Minor weaknesses (nice to address)
- **[Weakness 3]**: [Description]
  - Mitigation: [If time permits]
```

## Counter-argument generation

### Devil's advocate technique

Systematically argue against your own idea.

**Process:**

1. State the strongest case for the idea
2. Adopt an opposing perspective
3. Generate arguments against the idea
4. Respond to each counter-argument
5. Strengthen the idea based on insights

### Common counter-argument patterns

| Pattern | Challenge | Response approach |
|---------|-----------|-------------------|
| "It's been tried" | Prior attempts failed | Explain what's different now |
| "Too complex" | Simpler alternatives exist | Justify complexity or simplify |
| "Won't scale" | Works small, fails large | Demonstrate scalability plan |
| "No market" | Users don't want this | Provide evidence of demand |
| "Too risky" | Potential downsides | Show risk mitigation |
| "Wrong timing" | Market/tech not ready | Explain timing advantages |

### Counter-argument documentation

```markdown
## Counter-arguments and responses

### [Counter-argument 1]
**Challenge**: [The argument against]
**Validity**: High/Medium/Low
**Response**: [How to address this concern]
**Residual concern**: [What remains unresolved]

### [Counter-argument 2]
[Same structure...]
```

### Red team exercise

Assign roles to challenge the idea from different perspectives:

- **Skeptic**: Questions fundamental assumptions
- **Competitor**: Argues alternatives are better
- **User advocate**: Challenges usability claims
- **Finance**: Questions ROI and costs
- **Operations**: Raises maintenance concerns
- **Security**: Identifies vulnerabilities

## Risk assessment

### Risk identification

Sources of risk:

- Assumption failures
- Identified weaknesses
- Unaddressed counter-arguments
- External dependencies
- Unknown unknowns

### Risk matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | Critical/High/Med/Low | [Action] |
| [Risk 2] | [L] | [I] | [S] | [Action] |

**Severity calculation:**

| | High impact | Medium impact | Low impact |
|---|-------------|---------------|------------|
| **High likelihood** | Critical | High | Medium |
| **Medium likelihood** | High | Medium | Low |
| **Low likelihood** | Medium | Low | Low |

### Risk response strategies

| Strategy | When to use | Example |
|----------|-------------|---------|
| Avoid | Risk is unacceptable | Change approach to eliminate risk |
| Mitigate | Risk can be reduced | Add safeguards or redundancy |
| Transfer | Others can handle better | Insurance, contracts, partnerships |
| Accept | Risk is tolerable | Document and monitor |

### Risk documentation

```markdown
## Risk assessment

### Critical risks (must mitigate before proceeding)
| Risk | Description | Mitigation | Owner |
|------|-------------|------------|-------|
| [Risk 1] | [Details] | [Actions] | [Who] |

### High risks (should mitigate)
[Same structure...]

### Medium risks (monitor)
[Same structure...]

### Accepted risks (documented)
- [Risk]: [Rationale for acceptance]
```

## Constructive critique

### Balancing criticism with solutions

For every weakness identified, consider:

1. **Acknowledge the problem**: State it clearly
2. **Explore causes**: Why does this weakness exist?
3. **Generate solutions**: What could address it?
4. **Evaluate solutions**: Which are feasible?
5. **Recommend action**: What should be done?

### Critique documentation format

```markdown
### Critique: [Issue identified]

**Observation**: [What the problem is]
**Impact**: [Why it matters]
**Cause**: [Why it exists]
**Options**:
1. [Solution A]: [Pros/cons]
2. [Solution B]: [Pros/cons]
**Recommendation**: [Suggested action]
```
