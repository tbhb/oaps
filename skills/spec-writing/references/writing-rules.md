---
name: writing-rules
title: Requirement writing rules
description: Requirement quality rules for clarity, accuracy, and testability. Load when writing or improving requirement quality.
commands: {}
principles:
  - Requirements must be unambiguous, testable, and implementation-independent
  - Each requirement expresses a single verifiable need
  - Requirements use consistent terminology and follow agreed patterns
  - Requirements are independent of their organizational context
best_practices:
  - Use active voice with the responsible entity as the grammatical subject
  - Express requirements positively rather than negatively
  - Define all terms in a project glossary before use
  - Separate complex requirements into distinct, atomic clauses
  - Include explicit conditions and quantification where applicable
checklist:
  - All terms defined in glossary
  - Active voice with clear subject
  - Single thought per requirement
  - No vague terms (adequate, reasonable, user-friendly)
  - No escape clauses (where possible, as appropriate)
  - Testable and measurable
  - Independent of headings and context
  - Positive framing (avoid 'not' constructions)
references:
  https://www.incose.org/: INCOSE - International Council on Systems Engineering
  https://www.incose.org/docs/default-source/working-groups/requirements-wg/rwg-publications/incose-gwrr-2022.pdf: INCOSE Guide to Writing Requirements
---

# Requirement writing rules

This reference provides comprehensive quality rules for writing requirements based on INCOSE guidelines. These rules ensure requirements are clear, accurate, testable, and maintainable.

## Accuracy

Requirements must precisely express what is needed without ambiguity or imprecision.

### Structured statements

Requirements conform to agreed patterns and templates. Use consistent grammatical structures throughout the specification.

**Good**: "The system shall store user credentials for a minimum of 90 days."

**Bad**: "User credentials need to be stored for some time."

### Active voice

The responsible entity is clearly identified as the grammatical subject performing the action.

**Good**: "The sensor shall measure temperature every 5 seconds."

**Bad**: "Temperature measurements shall be taken every 5 seconds."

### Appropriate subject-verb

The grammatical subject matches the organizational level and responsibility being specified.

**Good**: "The authentication module shall validate user credentials within 2 seconds."

**Bad**: "Authentication shall happen quickly." (no clear subject)

### Defined terms

All technical terms, acronyms, and domain-specific vocabulary are defined in the project glossary before use in requirements.

**Good**: "The HVAC shall maintain cabin temperature within the specified range." (with HVAC defined in glossary)

**Bad**: "The climate control thingy shall keep it comfortable." (undefined informal terms)

### Definite articles

Use "the" rather than "a" or "an" when referring to specific entities in the system.

**Good**: "The database shall encrypt the user password."

**Bad**: "A database shall encrypt a user password."

### Common units

Use consistent measurement standards throughout the specification (SI units preferred unless domain conventions dictate otherwise).

**Good**: "The motor shall operate at temperatures between -40°C and 85°C."

**Bad**: "The motor shall operate in cold and hot conditions." (mixing standards or using vague terms)

### Avoid vague terms

Eliminate subjective or indefinite terms that cannot be objectively verified.

**Vague terms to avoid**: adequate, reasonable, user-friendly, appropriate, sufficient, easy, fast, slow, robust, flexible, modular, efficient, optimal, maximum (without value).

**Good**: "The interface shall respond to user input within 100 milliseconds."

**Bad**: "The interface shall be fast and user-friendly."

### Avoid escape clauses

Remove phrases that allow non-compliance or create loopholes in the requirement.

**Escape clauses to avoid**: where possible, if possible, as appropriate, to the extent practical, as applicable, when necessary.

**Good**: "The backup system shall activate within 30 seconds of primary system failure."

**Bad**: "The backup system shall activate within 30 seconds where possible."

### Avoid open-ended clauses

Eliminate incomplete lists or unbounded sets that leave requirements indefinite.

**Open-ended phrases to avoid**: including but not limited to, etc., and so on, such as.

**Good**: "The system shall support the following file formats: PDF, DOCX, XLSX, and PPTX."

**Bad**: "The system shall support file formats including but not limited to PDF, DOCX, etc."

## Concision

Requirements should be brief and direct, containing only essential information.

### Remove superfluous infinitives

Eliminate unnecessary phrases that weaken or inflate the requirement statement.

**Phrases to remove**: shall be able to, shall be capable of, shall have the ability to, shall have the capability to.

**Good**: "The user shall modify account settings."

**Bad**: "The user shall be able to modify account settings."

### Separate clauses

Each condition, action, or constraint appears in a distinct clause rather than combining multiple thoughts.

**Good**:

- "The sensor shall detect motion within 5 meters."
- "The sensor shall report detections within 500 milliseconds."

**Bad**: "The sensor shall detect motion within 5 meters and report it quickly."

## Non-ambiguity

Requirements must have a single, clear interpretation.

### Correct grammar

Requirements follow proper grammatical structure to ensure clear meaning.

**Good**: "The system shall validate input before processing the transaction."

**Bad**: "The system shall validate input before processing transaction the."

### Correct spelling

Use consistent and accurate spelling throughout the specification.

**Good**: "The authorization module shall authenticate users."

**Bad**: "The authorisation module shall athenticate users." (mixed spelling conventions)

### Correct punctuation

Punctuation clarifies the relationships between clauses and prevents misinterpretation.

**Good**: "The system shall log errors, warnings, and informational messages."

**Bad**: "The system shall log errors warnings and informational messages."

### Logical expressions

Define and consistently apply conventions for logical operators (AND, OR, NOT).

**Good**: "The alarm shall activate when (temperature > 100°C) OR (pressure > 5 bar)."

**Bad**: "The alarm shall activate when temperature or pressure is high." (ambiguous logic)

### Positive framing

Express requirements in positive terms stating what the system shall do, rather than what it shall not do.

**Good**: "The system shall encrypt all transmitted data."

**Bad**: "The system shall not transmit unencrypted data."

### Avoid oblique symbol

Do not use "/" (slash) in ways that create ambiguity about whether alternatives are mutually exclusive or inclusive.

**Good**: "The report shall include date and time." or "The report shall include either date or time."

**Bad**: "The report shall include date/time." (unclear if both or either)

## Singularity

Each requirement expresses exactly one verifiable need.

### Single thought

One primary action, condition, or constraint per requirement.

**Good**:

- "The system shall authenticate the user."
- "The system shall log the authentication attempt."

**Bad**: "The system shall authenticate the user and log the attempt."

### Avoid combinators

Do not use "and", "or", or "then" to join multiple concepts in a single requirement.

**Good**:

- "The display shall show battery voltage."
- "The display shall show battery current."

**Bad**: "The display shall show battery voltage and current."

**Exception**: Combinators are acceptable when listing parameters of a single action or describing a compound object (e.g., "The system shall store user name and email address").

### No purpose phrases

Rationale and justification belong in separate requirement attributes, not in the requirement statement itself.

**Good**: "The system shall hash passwords using bcrypt." (rationale in separate field: "To protect against rainbow table attacks")

**Bad**: "The system shall hash passwords using bcrypt to protect against rainbow table attacks."

### No parentheses

Remove supplementary information, examples, or clarifications embedded in parentheses.

**Good**: "The report shall include transaction ID, timestamp, and amount." (with examples in separate documentation)

**Bad**: "The report shall include transaction ID (e.g., TXN-12345), timestamp, and amount."

### Explicit enumeration

List all items explicitly rather than providing examples.

**Good**: "The system shall accept the following payment types: credit card, debit card, and bank transfer."

**Bad**: "The system shall accept payment types such as credit cards."

### Supporting diagrams

Reference state machines, sequence diagrams, or other visual models for complex behavioral requirements.

**Good**: "The connection state machine shall transition according to diagram D-123."

**Bad**: A single requirement attempting to describe all state transitions in text.

## Completeness

Requirements contain all information necessary for understanding without reference to external context.

### Avoid pronouns

Do not use personal pronouns (he, she, it, they) or indefinite pronouns (this, that, these, those) that require context to interpret.

**Good**: "The payment gateway shall encrypt the credit card number."

**Bad**: "It shall encrypt this before transmission."

### Independent of headings

Requirements are understandable when read in isolation, without relying on section headings or document structure.

**Good**: "The login module shall lock the account after 5 failed authentication attempts."

**Bad**: "Shall lock after 5 failed attempts." (requires heading "Login Module Requirements" for context)

## Realism

Requirements must be achievable with available technology, resources, and constraints.

### Avoid absolutes

Do not use absolute terms unless they are genuinely required and achievable.

**Problematic absolutes**: 100%, always, never, all, none, every, completely, totally, absolutely.

**Good**: "The backup system shall have 99.99% availability."

**Bad**: "The backup system shall never fail."

**Exception**: Absolutes are acceptable when truly required (e.g., "The safety interlock shall always prevent operation when the door is open").

## Conditions

Requirements specify when they apply and under what circumstances.

### Explicit conditions

State the applicability conditions explicitly rather than implying them.

**Good**: "When the battery voltage falls below 3.0V, the system shall enter low-power mode."

**Bad**: "The system shall enter low-power mode." (missing trigger condition)

### Multiple conditions

When multiple conditions apply, clarify the logical operators connecting them.

**Good**: "When (speed > 100 km/h) AND (engine temperature > 90°C), the system shall display a warning."

**Bad**: "When speed and temperature are high, the system shall warn the user."

## Uniqueness

Each requirement appears exactly once in the specification.

### Classification

Organize requirements by type (functional, performance, interface, safety, etc.) to prevent duplication.

**Good**: Requirements organized with clear taxonomy and unique identifiers.

**Bad**: Same requirement appearing in multiple sections with different wording.

### Unique expression

Each distinct need is captured in exactly one requirement, with other requirements referencing it as needed.

**Good**: "REQ-AUTH-001: The system shall authenticate users using two-factor authentication."
Referenced by: "REQ-LOGIN-003: The login process shall invoke REQ-AUTH-001."

**Bad**: Multiple requirements stating the same authentication need in different modules.

## Abstraction

Requirements specify what is needed, not how to implement it.

### Solution-free

Avoid specifying implementation details unless there is a compelling rationale (regulatory compliance, interface with existing systems, proven technology mandate).

**Good**: "The system shall store user preferences persistently."

**Bad**: "The system shall store user preferences in a MySQL database using InnoDB storage engine."

**Exception**: "The payment processor shall communicate using the ISO 8583 protocol." (mandated interface standard)

## Quantification

Requirements include specific, measurable criteria for verification.

### Universal qualification

Use "each" instead of "all", "any", or "both" to specify universal quantification clearly.

**Good**: "Each sensor shall report its status every 10 seconds."

**Bad**: "All sensors shall report their status regularly."

### Range of values

Define quantities with appropriate ranges, tolerances, and bounds.

**Good**: "The motor shall operate at speeds between 1000 rpm and 5000 rpm, ±50 rpm."

**Bad**: "The motor shall operate at various speeds."

### Measurable performance

Specify performance targets with concrete, measurable values.

**Good**: "The search function shall return results within 2 seconds for 95% of queries."

**Bad**: "The search function shall be fast."

### Temporal dependencies

Define time-related requirements explicitly with specific durations, frequencies, or deadlines.

**Avoid indefinite temporal terms**: eventually, soon, later, promptly, quickly, slowly, near real-time (without definition).

**Good**: "The system shall complete the transaction within 5 seconds of user confirmation."

**Bad**: "The system shall complete transactions promptly."

## Uniformity

Consistent terminology and notation throughout the specification.

### Consistent terms and units

Use identical terms for identical concepts and consistent units of measurement.

**Good**: Throughout specification: "authentication", "milliseconds", "megabytes"

**Bad**: Mixing "authentication", "login verification", "sign-in"; mixing "ms", "milliseconds", "msec"

### Consistent acronyms

Acronyms are defined once and used identically throughout all documentation.

**Good**: First use: "Application Programming Interface (API)", subsequent uses: "API"

**Bad**: Mixing "API", "A.P.I.", "api", "Api" throughout documents

### Avoid abbreviations

Do not abbreviate unless the abbreviation is formally defined in the glossary.

**Good**: "The system shall process a maximum of 1000 transactions per second."

**Bad**: "The sys shall process max 1000 txns/sec."

### Style guide

Apply a project-wide style guide for formatting, capitalization, and terminology.

**Good**: Consistent use of "shall" for all requirements

**Bad**: Mixing "shall", "must", "will", "needs to" inconsistently

### Decimal format

Use consistent notation and precision for numerical values.

**Good**: "The sensor shall measure temperature with 0.1°C precision."

**Bad**: Mixing "0.1", ".10", "0.10" for the same precision throughout the specification

## Modularity

Requirements are organized into logical, manageable groups.

### Related requirements

Group logically connected requirements together to improve traceability and maintainability.

**Good**: All authentication requirements grouped under "Authentication Module Requirements"

**Bad**: Authentication requirements scattered across system, user interface, and database sections

### Structured sets

Requirements conform to defined templates and organizational patterns.

**Good**: Requirements following a consistent structure:

- ID: REQ-MOD-NNN
- Title: Brief descriptive name
- Statement: "The [subject] shall [action] [object] [condition]."
- Rationale: Why this requirement exists
- Verification: How it will be tested

**Bad**: Inconsistent requirement format mixing different structures and missing key attributes

## Application Guidelines

When writing or reviewing requirements:

1. **Start with the subject**: Identify the responsible system element
2. **Use "shall" for mandatory requirements**: Consistent modal verb
3. **Include one testable statement**: Single verifiable need
4. **Add explicit conditions**: When does this apply?
5. **Quantify with measurable criteria**: How will we verify?
6. **Review against these rules**: Use as a checklist for quality

## Common Patterns

### Functional requirements

"The [system element] shall [action] [object] [performance criteria] [conditions]."

Example: "The payment gateway shall encrypt the credit card number using AES-256 within 100 milliseconds when processing a transaction."

### Performance requirements

"The [system element] shall [perform action] within [time/quantity] under [conditions]."

Example: "The database shall execute search queries within 2 seconds when the dataset contains up to 1 million records."

### Interface requirements

"The [system element] shall [communicate/exchange] [data] with [external element] using [protocol/format]."

Example: "The telemetry module shall transmit sensor data to the ground station using the CCSDS protocol."

### Constraint requirements

"The [system element] shall [comply with/operate within] [constraint]."

Example: "The device shall operate within an ambient temperature range of -20°C to 60°C."
