Implement a new **Remediation phase** in the current `learning-template` repository.

This feature should allow the system to immediately teach/re-explain a weakness discovered by an Assessment, while keeping later independent Practice/Review as the only mechanism that can verify whether the weakness was actually fixed.

Read the current implementation first, especially:

- `docs/SPEC.md`
- `scripts/learning_core/reviews.py`
- `scripts/learning_core/sessions.py`
- `scripts/learning_core/routing.py`
- `scripts/learning_core/study.py`
- `scripts/learning_core/reevaluation.py`
- schemas
- CLI
- current tests

Do not reintroduce development-stage terminology.

---

# Core concept

The learning flow becomes:

```text
Practice / Review
→ Evidence
→ Assessment
→ Gap detected / confirmed
→ optional Remediation
→ Session complete
```

Later:

```text
ordinary Practice or Review
→ new independent Evidence
→ Assessment
→ Gap remains active or resolves
```

Core principle:

```text
repair now
verify later
```

Remediation is teaching, not assessment.

---

# 1. Do not modify Practice or Review scheduling

Do not add:

- a new Review type;
- a verification Review;
- special Gap scheduling;
- new Review eligibility rules;
- new Practice planning rules;
- `awaiting_verification`;
- a new spaced-repetition algorithm.

After Remediation, the existing engine continues normally.

The Gap remains active until ordinary future Practice or Review produces independent Evidence that changes its state through the existing Gap logic.

---

# 2. Where Remediation occurs

Remediation happens after an Assessment associated with:

```text
practice
or
review
```

when that Assessment creates, confirms, or otherwise exposes a relevant active Gap.

It happens inside the **same logical Session**.

Example:

```text
Session
├── Review
├── Evidence
├── Assessment
├── Remediation
└── complete
```

It may also follow Practice:

```text
Practice
→ Evidence
→ Assessment
→ Remediation
```

Do not create a new Session automatically.

---

# 3. Remediation is NOT a new Session action

Current Session actions remain:

```text
study
practice
review
```

Do not add:

```text
remediation
```

to `ACTION_FOR_EVIDENCE` or to the Session plan action types.

Remediation is a **post-assessment phase of the existing Practice/Review action**.

This is important because the existing checkpoint model requires the checkpoint action to correspond to an action already present in the Session plan.

For pause/resume during Remediation, keep:

```yaml
action: review
unit: some-unit
```

or:

```yaml
action: practice
unit: some-unit
```

and extend checkpoint state with something like:

```yaml
phase: remediation

remediation:
  id: remediation-...
  gap: gap-...
  level: 2
  step: example
  resource: null
```

Use names consistent with existing conventions.

Do not make `remediation` a fake Evidence-producing action.

---

# 4. Session lifecycle

The source Practice/Review action may remain `in_progress` while Remediation is being performed.

Evidence and Assessment may already exist, but the Session does not need to be completed until optional Remediation is finished or skipped.

After Remediation finishes, normal Session completion proceeds using the already-created Evidence.

Remediation itself must not add an Evidence ID to `session.evidence`.

---

# 5. Remediation levels

Support three semantic levels.

## Level 1 — Clarification

For a local mistake:

- forgotten fact;
- confused condition;
- missed factor;
- small misconception.

Typical flow:

```text
what was wrong
→ why
→ correct mental model
```

## Level 2 — Explanation + Example

For unstable understanding.

Typical flow:

```text
alternative explanation
→ new example
→ guided reasoning
```

## Level 3 — Mini-lesson

For a deeper/fundamental weakness.

Typical flow:

```text
context
→ concept
→ explanation
→ example
→ misconception
→ summary
```

The AI chooses the level semantically.

It may escalate from Level 1 → 2 → 3 if the user still does not understand.

Do not implement a deterministic algorithm for selecting the level.

---

# 6. Guided exercise

Remediation may include a short guided exercise.

During it the AI may:

- give hints;
- correct reasoning;
- ask leading questions;
- explain intermediate steps;
- provide extra examples.

Therefore:

```text
guided exercise != Evidence
```

A successful guided exercise must not:

- create Evidence;
- create Assessment;
- update Progress;
- resolve Gap;
- increment attempts.

---

# 7. Gap state must not change because of Remediation

Adding/completing Remediation must preserve the current Gap status.

Examples:

```text
detected → remediation → detected
confirmed → remediation → confirmed
```

Do not introduce a new Gap status such as:

```text
remediated
awaiting_verification
```

The existing independent Evidence / Assessment flow remains responsible for:

```text
detected / confirmed → resolved
```

---

# 8. Remediation provenance

Store completed Remediation provenance on the Gap.

Add an append-only collection approximately like:

```yaml
remediations:
  - id: remediation-indexing-001

    session: 2026-10-09-001
    unit: choose-storage-and-indexes

    source_evidence: evidence-...
    source_assessment: assessment-...

    level: 2

    focus: >
      Difference between selectivity and the usefulness
      of a composite index.

    misconceptions_addressed:
      - ...

    guided_exercise: true

    resource: null

    completed_at: ...
```

Exact naming may follow current schema conventions.

Multiple Remediations for one Gap are allowed.

Do not store full conversation transcripts.

---

# 9. Session record

The Session should also retain enough information to show which Remediations occurred during it.

Prefer lightweight references rather than duplicating the full Gap record.

For example:

```yaml
remediations:
  - gap: gap-indexing-application
    remediation: remediation-indexing-001
```

The Gap remains the main provenance record.

Ensure Session ↔ Gap remediation references validate both ways where practical.

---

# 10. Remediation validity

A completed Remediation must reference:

- an existing Session;
- an existing Gap;
- an existing source Evidence;
- an existing source Assessment;
- the Unit associated with the source Evidence.

The source Assessment must refer to the source Evidence.

The Gap should be relevant to the source Assessment.

Prefer requiring that the Gap contains an active/historical signal tied to that Evidence/Assessment rather than allowing arbitrary unrelated Gaps to be remediated through an unrelated Assessment.

Use current Assessment-chain semantics when deciding what “source Assessment” means.

Do not bypass the `unit.nodes` assessment boundary.

---

# 11. Do not mutate historical assessment data

Remediation does not rewrite:

- Evidence;
- Assessment;
- Gap signals;
- Assessment chains.

It only adds remediation provenance.

Reevaluation remains a separate mechanism.

---

# 12. Level 3 Generated Resource

For Level 3, persist the mini-lesson using the existing generated-resource system under:

```text
resources/generated/
```

Do not create a new resource directory.

Extend generated-resource metadata to distinguish its purpose.

Example:

```yaml
purpose: remediation
gap: gap-indexing-application
```

Existing normal generated learning resources should continue to mean Study material.

A reasonable model is:

```text
purpose: study
purpose: remediation
```

If existing resources do not currently contain `purpose`, preserve compatibility with the current repository by treating missing purpose as normal Study material rather than requiring all historical generated resources to be rewritten.

---

# 13. Important Generated Resource validation change

Current generated-resource validation assumes that its Session plans:

```text
type: study
```

for the resource Unit.

That is correct for Study resources but not for Remediation mini-lessons.

Update this rule carefully.

For a normal Study generated resource:

```text
purpose == study (or legacy/missing purpose)
```

require the existing Study relationship.

For:

```text
purpose == remediation
```

require:

- a valid `gap`;
- a valid Session;
- the Session contains the relevant source `practice` or `review` action for the Unit;
- the remediation record points to this resource.

Do not weaken validation for normal Study resources.

---

# 14. Pause / Resume

Remediation must support the existing logical Session pause/resume system.

Because Remediation is not a new Session action, its checkpoint should remain attached to the source action.

Example:

```yaml
checkpoint:
  action: review
  unit: choose-storage-and-indexes

  phase: remediation

  remediation:
    id: remediation-indexing-001
    gap: gap-indexing-application
    level: 3
    step: mini_lesson
    resource:
      id: resource-remediation-indexing-001
      path: resources/generated/resource-remediation-indexing-001.md
```

Requirements:

- pausing must preserve current Remediation state;
- resume must continue the same Remediation;
- an already-created mini-lesson must be reused;
- do not regenerate it automatically;
- full conversation transcript is not required.

Use the existing checkpoint machinery instead of building another resume system.

---

# 15. In-progress vs completed Remediation

Do not record an unfinished Remediation in Gap provenance as if it were completed.

During execution/pause, checkpoint/Session state may describe the in-progress Remediation.

Only when Remediation is completed should the durable Gap `remediations[]` record be appended.

Make this transition deterministic and idempotent.

Repeating the completion command with the same data should not create duplicate remediation records.

---

# 16. Skipping Remediation

Remediation is optional.

The user must be able to say approximately:

```text
skip remediation
finish session
```

In that case:

- Gap remains active;
- no remediation provenance is created;
- Session completes normally.

Do not require every weak Assessment to trigger Remediation.

---

# 17. Several Gaps from one Assessment

One Assessment may expose several Gaps.

The AI may choose which are worth remediating now.

Prioritization is semantic, with general preference for:

1. blocking/prerequisite Gap;
2. confirmed Gap;
3. recurring Gap;
4. Gap directly limiting the current Unit;
5. minor/local weakness.

Do not require all Gaps to be remediated before Session completion.

A Session may contain multiple completed remediation records.

---

# 18. Module structure

Prefer adding a responsibility-based module:

```text
scripts/learning_core/remediation.py
```

with something like:

```text
RemediationRepositoryMixin
```

It should sit above the currently required functionality in the mixin chain.

Because Remediation depends on:

- Sessions;
- Gaps/routing;
- generated Resources;
- active Assessment / reevaluation semantics;

placing it after `ReevaluationRepositoryMixin` is likely the cleanest dependency direction.

For example:

```text
RemediationRepositoryMixin(ReevaluationRepositoryMixin)
```

and the public Repository then inherits from Remediation.

Inspect the actual current inheritance chain before applying this literally.

Do not perform unrelated architecture refactors.

---

# 19. Deterministic API

Add minimal deterministic operations for concepts such as:

```text
start remediation
complete remediation
validate remediation
read/list remediation state
```

Exact method/CLI naming should follow existing conventions.

Deterministic code manages state only.

It must not decide pedagogically:

- what explanation to give;
- which example to use;
- whether Level 1 or Level 3 is better.

Preserve:

```text
AI creates meaning
code manages state
```

---

# 20. CLI / skill workflow

Update the conversational learning workflow so that after an Assessment produces an active Gap it can offer:

```text
We found a weakness here.
Do you want to work through it now?
```

If yes:

```text
choose remediation level semantically
→ teach
→ optionally guided exercise
→ record completed remediation
→ finish Session
```

If no:

```text
finish Session normally
```

Do not automatically claim the Gap has been fixed.

The user-facing language should clearly distinguish:

```text
we worked on this weakness
```

from:

```text
the weakness is verified as resolved
```

---

# 21. Schemas and validation

Update schemas minimally.

Validate at least:

### Gap remediation record

- valid remediation ID;
- valid level `1 | 2 | 3`;
- existing Session;
- existing Unit;
- existing Evidence;
- existing Assessment;
- Assessment ↔ Evidence relationship;
- Unit ↔ Evidence relationship;
- resource reference if present;
- completed timestamp;
- no duplicate remediation IDs.

### Session

- remediation references point to real Gap remediation records;
- in-progress remediation checkpoint belongs to the current source Practice/Review action;
- no completed remediation is falsely recorded as in-progress.

### Generated resource

- correct purpose;
- Gap exists for remediation resources;
- Session/action relation is valid;
- immutable resource behavior preserved.

---

# 22. No Progress changes

Creating or completing Remediation must not invoke semantics that change Progress.

Test explicitly that these remain identical before/after Remediation:

```text
status
mastery
latest_evidence
latest_assessment
attempts
review schedule
```

unless some unrelated existing action changed them.

---

# 23. No Gap routing changes caused by Remediation

Because Gap status remains unchanged, Remediation itself should not change:

```text
routing_impact
Frontier Gap routing reason
blocking behavior
```

Do not rebuild or rewrite routing merely because remediation was recorded unless required for repository consistency.

---

# 24. Future verification remains unchanged

Do not add special handling for the next Practice/Review.

Example:

```text
Review weak
→ Gap detected
→ Remediation
→ Session complete

later existing planner selects Practice
→ new Evidence
→ Assessment strong
→ existing Gap logic resolves Gap
```

or:

```text
later scheduled Review
→ new Evidence
→ Assessment weak
→ Gap remains active
→ optional second Remediation
```

Both must work using existing mechanisms.

---

# 25. Tests

Add tests for at least the following.

## Basic remediation

```text
weak Practice/Review Assessment
→ Gap active
→ Remediation completed
```

Verify:

```text
Gap status unchanged
Progress unchanged
Evidence count unchanged
Assessment count unchanged
remediation provenance added
Session reference added
```

## Confirmed Gap

```text
confirmed Gap
→ Remediation
```

Gap remains `confirmed`.

## Skip

Weak Assessment followed by skipped Remediation completes normally and creates no remediation record.

## Multiple Remediations

Same Gap can have:

```text
remediation #1
remediation #2
```

with distinct IDs.

## Several Gaps

Only selected Gaps receive remediation records.

Others remain untouched.

## Guided exercise

Successful guided exercise does not create Evidence or resolve the Gap.

## Level 3 resource

Mini-lesson is persisted as a normal immutable Generated Resource with remediation metadata.

It is linked to the correct Gap and Session.

## Existing Study generated resources

Normal Study Resource validation still behaves exactly as before.

## Pause / resume

```text
Assessment
→ start Remediation
→ pause
→ resume
→ complete same Remediation
```

No duplicate Remediation and no regenerated Resource.

## Invalid source references

Reject:

- unknown Gap;
- unknown Evidence;
- unknown Assessment;
- Assessment belonging to another Evidence;
- Unit mismatch;
- unrelated Gap if deterministic provenance can establish the mismatch.

## Idempotency

Completing the same remediation twice does not duplicate it.

## Existing future Practice

After Remediation, normal future Practice still works unchanged and may resolve the Gap through existing logic.

## Existing future Review

Same for normal Review.

## Rebuild / validation

Remediation provenance survives:

```text
validate
→ rebuild
→ validate
```

without changing Progress/Frontier semantics.

---

# 26. Documentation

Update `docs/SPEC.md`.

Document:

- Remediation purpose;
- `repair now, verify later`;
- three levels;
- same-Session semantics;
- Remediation is not Evidence;
- Gap status does not change;
- repeat Remediation;
- Level 3 Generated Resources;
- Pause/Resume;
- ordinary future Practice/Review remains responsible for verification.

Update README/module overview if a new `remediation.py` module is introduced.

Do not create development-plan documents.

---

# 27. Scope exclusions

Do not implement:

```text
new Review type
verification Review
Gap-specific scheduler
awaiting-verification status
new mastery state
new Progress state
automatic Gap resolution
automatic immediate reassessment
automatic Review rescheduling
Practice planner changes
full remediation transcript persistence
hard time limit
```

Do not change existing learning algorithms unnecessarily.

---

# Completion criteria

The implementation is complete when this real workflow works:

```text
user performs Review
→ answer exposes weakness
→ Evidence and Assessment are recorded
→ Gap is detected/confirmed
→ user immediately receives targeted teaching
→ optional guided exercise
→ Remediation is recorded
→ Gap remains active
→ Session completes
→ later ordinary Practice/Review independently tests knowledge
→ existing Gap logic decides whether Gap remains or resolves
```

At the end report:

- files changed;
- data-model additions;
- how pause/resume works;
- how Level 3 resources differ from normal Study resources;
- deterministic invariants added;
- tests added;
- any known limitations.

Do not perform unrelated refactors.