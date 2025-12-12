---
name: expansion-patterns
title: Expansion patterns
description: Strategies for elaborating ideas including minimal vs maximal versions, variation generation, detail development, and scenario exploration. Load when developing ideas beyond initial concepts.
commands: {}
principles:
  - '**Explore the space**: Generate multiple variations before converging'
  - '**Scale intentionally**: Understand minimal and maximal expressions'
  - '**Add detail progressively**: Develop specifics as understanding grows'
  - '**Test with scenarios**: Concrete examples reveal hidden assumptions'
best_practices:
  - '**Generate variations first**: Create options before evaluating'
  - '**Define the spectrum**: Identify minimal and maximal versions'
  - '**Use scenarios for validation**: Test ideas against realistic situations'
  - '**Document the journey**: Record how ideas evolve through expansion'
checklist:
  - Minimal viable version defined
  - Maximal vision articulated
  - At least 3 variations generated
  - Key scenarios documented
  - Detail level appropriate to status
references: {}
related:
  - exploration-patterns
  - critique-patterns
---

## Minimal vs maximal versions

### Why define both

Understanding the full spectrum of an idea helps:

- Identify the core essence (what's truly necessary)
- Envision the ultimate potential (what's possible)
- Find the right scope for current context
- Communicate options to stakeholders

### Minimal version (MVP thinking)

The smallest expression that delivers core value.

**Questions to identify minimal:**

- What is the single most important outcome?
- What can be removed while preserving essence?
- What would a one-day prototype look like?
- What would disappoint no one but delight a few?

**Documentation template:**

```markdown
### Minimal version

**Core value**: [Single sentence describing essential benefit]
**Includes**:
- [Essential element 1]
- [Essential element 2]

**Explicitly excludes**:
- [Non-essential element 1]
- [Non-essential element 2]

**Trade-offs accepted**:
- [Limitation 1]
- [Limitation 2]
```

### Maximal version (vision thinking)

The fullest expression assuming unlimited resources.

**Questions to identify maximal:**

- What would this look like with infinite time and budget?
- What adjacent problems could this solve?
- How would this scale to millions of users?
- What would make this the definitive solution?

**Documentation template:**

```markdown
### Maximal version

**Full vision**: [Paragraph describing complete potential]
**Includes**:
- [All minimal elements]
- [Extended capability 1]
- [Extended capability 2]
- [Adjacent feature 1]

**Assumes**:
- [Resource assumption 1]
- [Technology assumption 2]

**Timeline**: [Rough estimate to full vision]
```

### Finding the right scope

Place current work on the spectrum:

```
Minimal ----[Current Scope]---------------- Maximal
   |              |                           |
   v              v                           v
One day       3-6 months                   Years
```

## Variation generation

### Divergent thinking techniques

Generate multiple variations before evaluating:

**Quantity over quality (initially)**

- Set a target (e.g., "Generate 10 variations")
- Suspend judgment during generation
- Include wild ideas alongside practical ones
- Build on previous variations

**Variation dimensions**

| Dimension | Questions | Example variations |
|-----------|-----------|-------------------|
| Scale | What if bigger? Smaller? | Single user vs enterprise |
| Speed | What if faster? Slower? | Real-time vs batch processing |
| Audience | Who else could use this? | Developers vs end users |
| Platform | Where else could this live? | Web vs mobile vs CLI |
| Automation | More manual? More automated? | Human review vs AI-driven |
| Scope | Broader? Narrower? | One feature vs full product |

### Variation documentation

```markdown
## Variations

### Variation A: [Name]
**Focus**: [What this emphasizes]
**Differs from baseline**: [Key changes]
**Pros**: [Advantages]
**Cons**: [Disadvantages]
**Best for**: [Ideal context]

### Variation B: [Name]
[Same structure...]

### Variation C: [Name]
[Same structure...]
```

### Evaluation criteria

After generating variations, evaluate against:

- Alignment with constraints
- Resource requirements
- Risk level
- Time to value
- Learning potential
- Strategic fit

## Detail development

### Progressive elaboration

Add detail as understanding grows:

| Stage | Detail level | Focus |
|-------|--------------|-------|
| Seed | Headlines only | Core concept |
| Exploring | Bullet points | Key questions and findings |
| Refining | Paragraphs | Developed thinking |
| Crystallized | Full documentation | Complete specification |

### Areas to develop

**Functional details**

- What does it do specifically?
- What are the inputs and outputs?
- What are the key operations?

**User experience details**

- Who uses it and how?
- What's the interaction flow?
- What does success look like for users?

**Technical details**

- What architecture patterns apply?
- What technologies are involved?
- What are the key interfaces?

**Operational details**

- How is it deployed and maintained?
- What monitoring is needed?
- How does it scale?

### Detail documentation structure

```markdown
## Detailed specification

### Functional description
[Expanded description of what the idea does]

### User interactions
[How users engage with the idea]

### Technical approach
[Implementation considerations]

### Operational model
[How it runs and is maintained]
```

## Scenario exploration

### Why use scenarios

Scenarios reveal:

- Hidden assumptions in the idea
- Edge cases not yet considered
- User needs not addressed
- Integration challenges
- Potential failure modes

### Scenario types

| Type | Purpose | Example |
|------|---------|---------|
| Happy path | Ideal usage | User successfully completes task |
| Edge case | Boundary conditions | User with 10,000 items |
| Error case | Failure handling | Network disconnects mid-operation |
| Adversarial | Misuse or attack | User attempts to bypass limits |
| Integration | System interaction | Data imported from external system |
| Scale | Volume testing | 1 million concurrent users |
| Migration | Transition handling | Existing users upgrading |

### Scenario documentation template

```markdown
### Scenario: [Name]

**Type**: [Happy path / Edge case / Error case / etc.]
**Actors**: [Who is involved]
**Preconditions**: [Starting state]

**Steps**:
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Expected outcome**: [What should happen]
**Alternative outcomes**: [Other possible results]
**Questions raised**: [What this scenario reveals]
```

### Scenario-driven refinement

Use scenarios to improve the idea:

1. Write scenario before implementation details
2. Walk through scenario step by step
3. Note where the idea is unclear or incomplete
4. Update idea documentation with insights
5. Create new scenarios to test refinements
