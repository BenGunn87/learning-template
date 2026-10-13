Implement a new **Course Reference** capability in the current `learning-template` repository.

The goal is to provide a persistent, human-readable working reference for reusable knowledge such as:

- definitions;
- formulas;
- rules;
- heuristics;
- relationships;
- trade-offs;
- other compact reusable knowledge.

Reference should remain simple, readable Markdown rather than becoming another structured knowledge database.

Read the current implementation first, especially:

- `docs/SPEC.md`
- repository structure
- Evidence schema/model
- Study / Practice / Review workflows
- Remediation
- Generated Resources
- Session/checkpoint logic
- current Skills
- current tests

Do not reintroduce development-stage terminology.

---

# 1. Core concept

Add:

```text
reference/
```

as a persistent course-level working reference.

Reference is:

```text
human-first Markdown
editable
Primary Data
shared between user and AI
```

Reference is NOT:

```text
Evidence
Progress
Assessment
Gap
Session history
Generated Resource
```

Editing Reference must not imply that the user has learned or mastered its contents.

---

# 2. Repository structure

Support:

```text
reference/
  index.md
```

Additional thematic files are created only when useful.

Examples:

```text
reference/
  index.md
  aerodynamics.md
  stability.md
  propulsion.md
```

or:

```text
reference/
  index.md
  storage.md
  consistency.md
  distributed-systems.md
```

Do not predefine course-specific filenames.

---

# 3. Lazy initialization

Reference should be optional.

Existing repositories do not need migration.

If `reference/` does not exist, the first Reference operation may create:

```text
reference/
reference/index.md
```

Do not create unnecessary thematic files automatically.

---

# 4. Human-first Markdown

Do not introduce a rigid schema for Reference entries.

Do not require fields such as:

```text
id
type
tags
nodes
related
formula
units
```

for every entry.

Use ordinary readable Markdown:

- headings;
- paragraphs;
- lists;
- tables;
- mathematical notation;
- examples;
- links between sections where useful.

Different knowledge types may use different layouts.

For example, a formula may naturally include variables and units, while a definition may require only a few paragraphs.

Primary design goal:

```text
Reference should be pleasant to open and read directly.
```

---

# 5. Reference remains opaque to deterministic code

The deterministic core should NOT semantically parse Reference contents.

It should not attempt to understand:

- formulas;
- definitions;
- trade-offs;
- relationships;
- topic types;
- conceptual duplication.

Semantic interpretation and editing belongs to the AI.

Preserve:

```text
AI creates meaning
code manages state
```

---

# 6. reference/index.md

`reference/index.md` is the human-readable entry point.

Example:

```markdown
# Reference

- [Aerodynamics](aerodynamics.md)
- [Stability and Control](stability.md)
- [Propulsion](propulsion.md)
```

Do not enforce a rigid index schema.

When creating or removing thematic files, AI should keep the index readable and useful.

---

# 7. What belongs in Reference

Main filter:

> Would this knowledge still be useful outside the current exercise or Session?

Good candidates:

```text
lift equation
definition of wing loading
stall relationship
CAP theorem
quorum rule
composite-index selection rule
replication trade-off
```

Poor candidates:

```text
answer to one exercise
one-off calculation
specific Session feedback
user mistake history
Assessment result
temporary explanation
```

Reference should be distilled reusable knowledge, not a complete course notebook.

---

# 8. System-initiated updates

After activities such as:

```text
Study
Practice
Remediation
```

the AI may notice reusable knowledge worth preserving.

It may propose:

```text
Стоит добавить формулу подъёмной силы в Reference.
```

or:

```text
В Reference уже есть раздел про quorum.
Предлагаю дополнить его этим ограничением.
```

A system-initiated proposal MUST NOT modify Reference immediately.

Require explicit user confirmation first.

Do not create a persistent "Reference proposal" entity.

The proposal is conversational only.

---

# 9. User-initiated updates

The user may explicitly request a Reference change at any time.

Examples:

```text
Добавь это в Reference.
Зафиксируй эту формулу.
Добавь это определение в справочник.
Обнови раздел про CAP.
```

This request itself counts as explicit authorization.

Do not ask for another confirmation.

User-initiated changes may happen:

```text
during Study
during Practice
during Remediation
outside a Session
```

---

# 10. Add vs update

Before adding new content, AI should inspect:

```text
reference/index.md
```

and relevant thematic files.

Then choose whether to:

```text
update an existing section
add a new section
create a new thematic file
```

Prefer updating an existing section when the new knowledge naturally belongs there.

Avoid unnecessary duplication.

Core principle:

```text
Reference should improve,
not merely grow.
```

---

# 11. Normal editing is allowed

Reference is NOT append-only.

AI/user may:

```text
rewrite
clarify
merge
split
restructure
correct
expand
shorten
improve examples
```

Do not implement a separate Reference history model.

Git already provides edit history.

---

# 12. Reference quality

When editing Reference, prefer content that is:

```text
concise
self-contained
technically accurate
useful outside the current Session
easy to scan
```

Do not paste long passages from Generated Resources or external articles.

Distill them into reusable working knowledge.

---

# 13. Reference during learning

Reference may be freely consulted during non-assessment learning phases such as:

```text
Study
Discussion
Remediation
```

These phases are supported learning.

Reference restrictions matter mainly during independent Evidence-producing activities.

---

# 14. Default assessment policy

Use this default policy:

```text
Recall
→ closed-reference

Understanding
→ usually closed-reference

Application
→ open-reference
```

Rationale:

```text
Recall tests retrieval.

Application tests whether the learner can select
and correctly use relevant knowledge.
```

This is a default, not an absolute rule.

A particular task may explicitly override it.

---

# 15. Make Reference policy explicit to the user

Before an independent task, tell the user whether Reference is allowed.

Examples:

```text
Эта часть проверяет recall — Reference не используем.
```

```text
Здесь проверяем применение — Reference можно использовать.
```

If one Evidence-producing activity contains different modes, divide it clearly.

Example:

```text
Part A — closed-reference
Part B — open-reference
```

Do not rely on hidden policy.

---

# 16. Evidence provenance

Extend Evidence so Reference conditions can be recorded per assessed dimension.

Do NOT use one global boolean because a single Evidence may contain both closed-reference recall and open-reference application.

Preferred optional structure:

```yaml
reference:
  - dimension: recall
    allowed: false
    used: false

  - dimension: application
    allowed: true
    used: true
    files:
      - reference/aerodynamics.md
```

Also valid:

```yaml
reference:
  - dimension: application
    allowed: true
    used: false
```

meaning that Reference was allowed but the user did not use it.

Do NOT add file hashes or `sha256`.

Git history is sufficient for now.

---

# 17. Evidence invariants

Enforce:

```text
used=true
→ allowed=true
```

If:

```text
used=true
```

then at least one actually used Reference file must be recorded.

For:

```text
allowed=false
```

require:

```text
used=false
```

Only record files the user actually consulted.

Do not record all Reference files merely because they were available.

---

# 18. Assessment interpretation

Assessment should have access to Reference-use metadata.

Examples:

```text
Recall failed while Reference was prohibited
→ likely recall weakness
```

```text
Application failed while Reference was allowed and used
→ likely application / understanding problem,
  not merely forgotten formula
```

Do not mechanically alter scores based on Reference use.

Reference access itself:

```text
does not increase mastery
does not decrease mastery
```

It is context for interpreting performance.

---

# 19. Reference is not Evidence

Editing Reference must NOT:

```text
create Evidence
create Assessment
update Progress
change Gap status
change Frontier
increment attempts
```

Even if the user personally supplied the content being added.

If knowledge needs verification, use normal Practice/Review.

---

# 20. Reference and Remediation

Remediation may freely read Reference.

It may also result in a proposed Reference update.

Example:

```text
Мы уточнили важное ограничение quorum.
Предлагаю обновить соответствующий раздел Reference.
```

If user confirms, update the Reference.

This must not resolve the Gap.

Preserve:

```text
repair now
verify later
```

---

# 21. Reference vs Generated Resource

Keep these concepts separate.

Generated Resource:

```text
material used in a specific learning attempt
immutable Primary Data
```

Reference:

```text
long-lived working knowledge
editable Primary Data
```

A useful idea from a Generated Resource may later be distilled into Reference, but never automatically copy the full resource.

---

# 22. Deterministic Reference module

Prefer a small responsibility-based module:

```text
scripts/learning_core/reference.py
```

with a mixin such as:

```text
ReferenceRepositoryMixin
```

Integrate it into the current repository mixin chain using the existing architecture.

Do not refactor unrelated modules.

Deterministic responsibilities should remain minimal:

```text
ensure reference directory/index
list reference files
read reference file
create reference file
replace reference file atomically
validate reference paths
```

Do not make deterministic code edit Markdown semantically.

---

# 23. Safe editing

Reference is Primary Data.

Writes must be atomic.

Reject:

```text
path traversal
writes outside reference/
invalid paths
accidental empty overwrite
```

Only support Markdown Reference files unless there is a clear existing project convention requiring otherwise.

Where practical, use an optimistic edit pattern:

```text
read current content
→ prepare replacement
→ ensure current content still matches expected state
→ replace atomically
```

Do not add cryptographic hashes solely for this feature.

A direct expected-content check is enough if needed.

---

# 24. manage-reference skill

Add a responsibility-specific Skill, for example:

```text
manage-reference
```

It should support:

```text
show/find Reference
add content
update content
create thematic file
```

Typical workflow:

```text
read index
→ identify relevant file
→ inspect related content
→ decide add/update
→ prepare readable Markdown
→ write
→ update index if required
```

For a system-initiated update:

```text
propose
→ wait for explicit confirmation
→ modify Reference
```

For an explicit user command:

```text
modify immediately
```

---

# 25. Learning Skills

Update appropriate Study / Practice / Remediation Skills so the AI may semantically notice reusable knowledge.

After a relevant activity, it may ask itself:

```text
Is there reusable knowledge here worth preserving?
```

If not:

```text
do nothing
```

If yes:

```text
offer a concise Reference add/update
```

Do NOT force a Reference suggestion at the end of every Session.

Avoid noisy suggestions.

---

# 26. Practice / Review workflows

Before producing independent Evidence, determine and communicate Reference policy.

Default:

```text
recall         closed
understanding  closed
application    open
```

Allow semantic override when appropriate.

After the user responds, include actual Reference use in Evidence.

Do NOT change:

```text
Practice planner
Review scheduler
Gap lifecycle
Progress lifecycle
Frontier routing
```

---

# 27. Existing repositories

Do not require migration.

Repositories without `reference/` remain valid.

Initialize Reference lazily on first use.

Existing Evidence without Reference metadata remains valid unless the current project explicitly does not require backward compatibility.

Do not rewrite historical Evidence merely to add Reference fields.

---

# 28. Validation

Keep validation intentionally minimal.

Validate:

```text
Reference paths stay inside reference/
Markdown files are readable
Evidence Reference paths point to Reference files
used=true implies allowed=true
used=true implies at least one file
allowed=false implies used=false
```

Do NOT validate:

```text
formula correctness
Markdown section structure
definitions
semantic duplicates
trade-off quality
topic taxonomy
```

Those remain semantic responsibilities.

---

# 29. Tests

Add tests for at least:

## Lazy initialization

First Reference operation creates:

```text
reference/index.md
```

when Reference does not yet exist.

## Add thematic file

Create a file such as:

```text
reference/aerodynamics.md
```

and ensure index can reference it.

## Update existing Reference

Existing Markdown can be edited without creating a new Primary entity.

## Safe paths

Reject attempts to write outside `reference/`.

## No learning-state mutation

Reference edits leave unchanged:

```text
Evidence
Assessment
Progress
Gap
Frontier
Session
```

## User initiated update

Explicit user workflow can update Reference without a second confirmation.

## System initiated proposal

A proposal alone does not modify Reference.

Only confirmed execution does.

## Closed-reference Evidence

This is valid:

```yaml
reference:
  - dimension: recall
    allowed: false
    used: false
```

## Open-reference unused

This is valid:

```yaml
reference:
  - dimension: application
    allowed: true
    used: false
```

## Open-reference used

This is valid:

```yaml
reference:
  - dimension: application
    allowed: true
    used: true
    files:
      - reference/aerodynamics.md
```

## Invalid usage

Reject:

```text
allowed=false
used=true
```

Reject:

```text
used=true
without files
```

## Mixed Evidence

One Evidence supports:

```text
recall closed-reference
+
application open-reference
```

without losing information.

## Rebuild

```text
validate
→ rebuild
→ validate
```

does not rewrite or regenerate Reference.

---

# 30. Documentation

Update `docs/SPEC.md` to describe:

- purpose of Reference;
- Primary Data status;
- human-first Markdown;
- lazy initialization;
- system-initiated vs user-initiated edits;
- confirmation rules;
- add/update behavior;
- open-reference vs closed-reference;
- Evidence provenance;
- separation from mastery and Evidence;
- relationship to Remediation and Generated Resources.

Update README/repository tree/module overview where relevant.

Do not create implementation-stage planning documents.

---

# 31. Scope exclusions

Do NOT implement:

```text
typed Reference entries
formula database
Reference knowledge graph
Markdown AST schema
automatic backlinks
semantic duplicate detector
vector search / RAG
Reference mastery
flashcards generated automatically from Reference
spaced repetition of Reference entries
automatic Reference editing without user confirmation
separate Reference history outside Git
content hashes / sha256 provenance
```

Keep the first version intentionally simple.

---

# Completion criteria

The feature is complete when these workflows work.

## System-initiated

```text
Study aerodynamics
→ encounter lift equation
→ AI suggests adding it to Reference
→ user confirms
→ readable section appears in reference/aerodynamics.md
```

## User-initiated

```text
user:
"Добавь это определение в Reference"

→ AI inspects existing Reference
→ chooses add or update
→ modifies readable Markdown
→ no extra confirmation
→ no learning-state mutation
```

## Open-reference Application

```text
Application task
→ AI explicitly says Reference is allowed
→ user uses reference/aerodynamics.md
→ Evidence records:

allowed=true
used=true
files=[reference/aerodynamics.md]
```

## Closed-reference Recall

```text
Recall task
→ AI explicitly says Reference is not allowed
→ Evidence records:

allowed=false
used=false
```

All existing learning behavior should remain unchanged aside from the new optional Reference capability.

At the end, report:

- files/modules added or changed;
- Evidence schema changes;
- Reference file operations;
- Skill changes;
- validation invariants;
- tests added;
- any deviations from this design and why.

Do not perform unrelated refactors.