Fix the current Course Reference implementation so Evidence records not only whether Reference was **allowed**, but also whether the learner **actually used it**.

Keep the change small and focused.

Do NOT redesign the Reference system.

Do NOT add per-file provenance in this change.

---

# Problem

The current Evidence model records:

```yaml
reference:
  - dimension: application
    allowed: true
```

but deliberately does not record whether the learner actually consulted Reference.

This loses an important distinction.

These two situations currently look identical:

```text
Reference allowed
→ learner used it
→ still failed to apply the concept
```

and:

```text
Reference allowed
→ learner did not use it
→ failed because the formula/rule was not recalled
```

Those cases should be distinguishable during Assessment.

---

# Required model

Extend Reference metadata in Evidence to include:

```yaml
reference:
  - dimension: recall
    allowed: false
    used: false

  - dimension: application
    allowed: true
    used: true
```

`used` means:

> The learner actually consulted Course Reference while completing this part of the independent task.

It does NOT mean that the Reference was merely available.

---

# Invariants

Require:

```text
used=true
→ allowed=true
```

Therefore this is invalid:

```yaml
dimension: recall
allowed: false
used: true
```

When:

```text
allowed=false
```

require:

```text
used=false
```

When:

```text
allowed=true
```

both values are valid:

```text
used=false
used=true
```

---

# Do not add files yet

Do NOT add:

```yaml
files:
```

or hashes/version provenance in this fix.

For now we only need:

```text
dimension
allowed
used
```

We can add detailed file provenance later if real usage shows that it is useful.

Keep the schema minimal.

---

# User interaction

When Reference is allowed, the system needs a reliable way to know whether it was actually used.

Do not silently infer usage.

Accept explicit conversational signals such as:

```text
Я посмотрел в reference.
Я воспользовался справочником.
Я нашёл формулу в reference.
```

If the workflow itself opens/shows Reference for the learner during the independent task, that also counts as:

```text
used=true
```

If Reference was allowed but there is no indication that it was consulted:

```text
used=false
```

Do not repeatedly interrupt the learner during the task just to ask about usage.

If usage remains genuinely ambiguous when Evidence is about to be recorded, one short clarification is acceptable.

---

# Closed-reference tasks

For closed-reference Recall/Understanding:

```yaml
allowed: false
used: false
```

The workflow should continue to explicitly tell the learner that Reference is not allowed.

No behavior change is required beyond recording `used=false`.

---

# Open-reference tasks

For Application where Reference is allowed:

```yaml
allowed: true
used: true | false
```

Record the actual behavior.

Examples:

### Allowed and used

```yaml
reference:
  - dimension: application
    allowed: true
    used: true
```

### Allowed but not used

```yaml
reference:
  - dimension: application
    allowed: true
    used: false
```

---

# Mixed Evidence

A single Evidence may still contain multiple assessment conditions:

```yaml
reference:
  - dimension: recall
    allowed: false
    used: false

  - dimension: application
    allowed: true
    used: true
```

Preserve this per-dimension model.

Do not collapse it into a global Reference flag.

---

# Assessment semantics

Make Reference usage metadata available to the semantic Assessment workflow.

The AI may use it as context when interpreting a weak result.

For example:

```text
application weak
allowed=true
used=true
```

suggests that the main issue is probably not merely recalling the relevant formula/rule. The weakness may instead involve:

```text
selecting the right knowledge
understanding when it applies
using it correctly
reasoning from it
```

Whereas:

```text
application weak
allowed=true
used=false
```

does not provide that evidence.

The learner may simply have attempted the task from memory.

Important:

Do NOT implement deterministic scoring rules based on `used`.

Reference use:

```text
does not increase mastery
does not decrease mastery
```

It is contextual information for semantic interpretation.

---

# Skills

Update Practice / Review / relevant Evidence-producing skills.

Remove instructions that explicitly say not to track Reference usage.

Ensure the workflow:

1. establishes whether Reference is allowed;
2. makes that rule explicit to the learner;
3. tracks whether it was actually consulted;
4. records both `allowed` and `used` in Evidence.

Update any Assessment skill so it knows how to interpret these fields without mechanically changing scores.

Do not modify Study or Remediation semantics unnecessarily.

---

# Schema

Update `evidence.schema.yaml`.

Each Reference entry should require approximately:

```yaml
dimension: recall | understanding | application
allowed: boolean
used: boolean
```

Preserve existing dimension conventions from the current schema.

Validate:

```text
allowed=false + used=true
→ invalid
```

Do not add `files`.

---

# Validation

Update deterministic validation consistently with the schema.

At minimum:

```text
used=true requires allowed=true
allowed=false requires used=false
```

Preserve all existing Evidence validation.

Do not change Progress, Gap, Frontier, Review scheduling, Practice planning, or Reference file management.

---

# Documentation

Update `docs/SPEC.md`.

Remove the current statement that actual Reference usage is intentionally not collected.

Document instead:

```text
allowed = whether the task permitted Course Reference
used = whether the learner actually consulted Course Reference
```

Explain why both are useful:

```text
availability of help
!=
actual use of help
```

Document that usage is assessment context rather than a mastery signal.

Update README/Skills documentation only where needed.

---

# Tests

Add/update tests for at least:

## Closed-reference

```yaml
allowed: false
used: false
```

→ valid.

## Invalid closed-reference usage

```yaml
allowed: false
used: true
```

→ rejected.

## Open-reference used

```yaml
allowed: true
used: true
```

→ valid.

## Open-reference unused

```yaml
allowed: true
used: false
```

→ valid.

## Mixed Evidence

```text
recall: allowed=false, used=false
application: allowed=true, used=true
```

→ valid.

## Existing learning behavior

Adding `used` must not by itself change:

```text
Progress
Gap
Frontier
attempt counts
Review scheduling
Practice planning
```

## Assessment context

If there are skill/workflow tests for semantic Assessment input, verify that both `allowed` and `used` are available to it.

---

# Scope exclusions

Do NOT add:

```text
files
sha256
Reference version tracking
automatic scoring based on usage
Reference mastery
new assessment dimensions
Reference-specific Gap types
new scheduling logic
```

Do not refactor unrelated Course Reference code.

---

# Completion criteria

The fix is complete when the system can distinguish these two Evidence records:

```yaml
reference:
  - dimension: application
    allowed: true
    used: false
```

and:

```yaml
reference:
  - dimension: application
    allowed: true
    used: true
```

and semantic Assessment can use that distinction as context without deterministic mastery changes.

At the end report:

- files changed;
- Evidence schema changes;
- how actual usage is captured;
- skill/documentation changes;
- tests added;
- any deviations and why.