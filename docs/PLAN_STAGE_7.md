Implement **Stage 7 — Assessment Reevaluation** in the current `learning-template` repository.

Use the existing architecture and Stage 1–6 implementation as the source of truth. Do not redesign working subsystems unless Stage 7 requires a minimal compatible change.

Read first:

* `docs/SPEC.md`
* `docs/PLAN_STAGE_1.md` … `docs/PLAN_STAGE_6.md`
* current Assessment / Evidence / Gap / Progress / Frontier implementation
* validation and rebuild code
* existing tests

Then create/update `docs/PLAN_STAGE_7.md` and implement the following.

## Goal

Support append-only reevaluation of an existing Assessment without modifying the source Evidence.

Core principle:

```text
Evidence = immutable fact
Assessment = revisable interpretation
```

A reevaluation creates a new Assessment:

```text
Assessment A
→ Assessment B supersedes A
→ Assessment C supersedes B
```

Old Assessments remain on disk and auditable.

## Reevaluation reasons

Support:

```text
user_request
contradiction
rubric_change
```

Reevaluation must never happen automatically.

Codex may recommend reevaluation, but an explicit reevaluation action is required.

## Source of truth

Reevaluation must reinterpret the original Evidence only.

Do not use later answers, later Evidence, chat memory, or Session summaries as part of the evidence being graded.

Later information may trigger the decision to reevaluate, but must not change the source Evidence.

## Assessment schema

Initial Assessment:

```yaml
type: initial
```

Reevaluation:

```yaml
type: reevaluation
supersedes: assessment-...
reason: user_request
```

For reevaluation:

* `supersedes` required;
* `reason` required;
* target Assessment must exist;
* target must belong to the same Evidence;
* target must currently be active.

## Supersedes chain

Allow only a linear chain:

```text
A → B → C
```

Reject:

* self-reference;
* cycles;
* cross-Evidence supersedes;
* branching such as `A → B` and `A → C`;
* superseding an already superseded Assessment.

There must be exactly one active Assessment per Evidence.

Implement a deterministic helper equivalent to:

```text
active_assessment(evidence_id)
```

## Formal assessment boundary

Preserve the existing invariant:

> Assessment may formally evaluate only Graph Nodes declared in the source `unit.nodes`.

Reevaluation must obey the same boundary.

Do not allow reevaluation to bypass this rule.

## Progress behavior

Progress is Derived.

Only the active Assessment for each Evidence participates in Progress rebuild.

A superseded Assessment must no longer affect current Progress.

Reevaluation is not a new learning attempt.

It must not increase:

```text
attempt count
practice count
review count
```

It only changes the interpretation of an existing attempt.

## Gap provenance

Existing Gap signals may reference both Evidence and Assessment.

Do not delete historical signals.

A Gap signal is current/active only when its Assessment is the active Assessment for that Evidence.

A signal from a superseded Assessment remains historical provenance but must no longer contribute to current Gap state.

## Gap lifecycle

Extend Gap status to support:

```text
detected
confirmed
resolved
invalidated
```

Semantics:

```text
resolved
= the learning weakness was real, but later learning improved it

invalidated
= the weakness was based on an Assessment interpretation that was later superseded
```

Do not conflate these states.

## Gap reconciliation

After reevaluation, recompute affected Gap state from active signals.

Required cases:

### detected → invalidated

A Gap has one active weak signal.

That Assessment is reevaluated as strong.

No active weak signal remains.

### confirmed → detected

Two independent weak signals confirmed the Gap.

One is reevaluated as strong.

One active weak signal remains.

### confirmed → invalidated

All active weak signals are removed through reevaluation.

### resolved → reopened

A strong Assessment that previously contributed to resolving a Gap is reevaluated as weak.

The Gap must return to `detected` or `confirmed` according to the remaining active signals.

Historical signals must remain stored.

## Gap history

Every reevaluation-driven state transition should leave an auditable history record.

Example:

```yaml
history:
  - status: detected
    at: ...
    evidence: ...

  - status: invalidated
    at: ...
    assessment: assessment-...
    reason: reevaluation
```

Use existing project conventions where possible.

## Frontier

After reevaluation:

```text
active Assessment changes
→ Progress rebuild
→ Gap reconciliation
→ Frontier rebuild
```

An `invalidated` Gap must not influence routing.

A downgraded `confirmed → detected` Gap should behave exactly like any other detected Gap according to existing Stage 5 routing rules.

## Workflow

Support a conversational workflow equivalent to:

```text
select Assessment
→ load original Evidence
→ show current Assessment
→ select reevaluation reason
→ reinterpret same Evidence
→ create new Assessment
→ supersede previous Assessment
→ reconcile Gaps
→ rebuild Progress
→ rebuild Frontier
→ explain what changed
```

## Result explanation

After a successful reevaluation, Codex should be able to explain concisely:

```text
Old assessment:
application: hard

New assessment:
application: good

Reason:
...

Effects:
Progress updated
Gap ... invalidated
Frontier rebuilt
```

## Semantic vs deterministic responsibilities

Preserve:

```text
AI creates meaning
code manages state
```

Codex:

* rereads Evidence;
* produces the semantic reevaluation;
* explains the change.

Deterministic code:

* validates supersedes chain;
* finds active Assessment;
* checks same Evidence;
* checks `unit.nodes`;
* reconciles Gap state;
* rebuilds Progress;
* rebuilds Frontier;
* validates repository consistency.

## No new Evidence

Reevaluation must not:

* create new Evidence;
* create a new Session;
* represent another learning attempt.

If new questions are asked and the user provides new answers, that is a new Practice/Review and must create new Evidence instead.

## Atomicity

Before writing the new Assessment, perform a full deterministic preflight.

Check at least:

* target Assessment exists;
* target is active;
* same Evidence;
* valid reason;
* valid supersedes chain;
* evaluated Nodes belong to `unit.nodes`;
* projected Gap transitions are valid.

If any check fails, no partial state change should remain.

Avoid situations where the new Assessment is written but Gap/Progress/Frontier state is only partially updated.

Use existing atomic write conventions.

## Validation

Add deterministic validation for:

* initial Assessment must not have `supersedes`;
* reevaluation must have `supersedes`;
* reevaluation must have valid `reason`;
* target Assessment exists;
* same Evidence;
* target was active;
* no cycles;
* no branching;
* exactly one active Assessment per Evidence;
* reevaluation obeys `unit.nodes`;
* current Gap state is consistent with active signals.

## Tests

Add tests for at least:

### Basic reevaluation

```text
Evidence
→ Assessment A
→ Reevaluation B
```

B active, A preserved.

### Three-event chain

```text
A → B → C
```

Only C active.

### Cross-Evidence rejection

Assessment for Evidence B cannot supersede Assessment for Evidence A.

### Branch rejection

```text
A → B
A → C
```

must fail.

### Progress improves

```text
hard → good
```

Progress rebuild reflects `good`.

Attempt count unchanged.

### Progress worsens

```text
good → hard
```

Progress rebuild reflects the weaker active Assessment.

### detected → invalidated

Single weak signal reevaluated as strong.

### confirmed → detected

One of two independent weak signals removed.

### confirmed → invalidated

All current weak signals removed.

### resolved → reopened

Previously resolving strong Assessment reevaluated as weak.

### Historical provenance

Signals from superseded Assessments remain stored but inactive.

### Frontier

Invalidated Gap no longer affects routing.

### Unit boundary

Reevaluation cannot formally assess a Node outside `unit.nodes`.

### No new Evidence

Evidence count does not change.

### Atomic failure

A mixed/invalid reevaluation must leave:

```text
Assessments unchanged
Progress unchanged
Gaps unchanged
Frontier unchanged
```

## Documentation

Update `docs/SPEC.md` with:

* reevaluation workflow;
* reasons;
* linear `supersedes` chain;
* active Assessment semantics;
* Progress semantics;
* active vs historical Gap signals;
* `invalidated`;
* difference between `resolved` and `invalidated`;
* Gap downgrade/reopen behavior;
* explicit-action requirement.

## Scope exclusions

Do not implement:

```text
automatic contradiction detection
automatic reevaluation
batch reevaluation
rubric migration framework
long-inactivity recalibration
LLM judge ensembles
confidence calibration
full UI
```

Keep Stage 7 focused on the reevaluation mechanism itself.

## Verification

Run the complete test suite.

At minimum:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Use the actual current project commands if they differ.

Also manually verify one scenario:

```text
create Evidence
→ create initial weak Assessment
→ Gap detected
→ reevaluate same Evidence as good
→ old Assessment remains
→ new Assessment active
→ Gap invalidated
→ Progress rebuilt
→ Frontier rebuilt
→ validate
→ rebuild
→ validate again
```

After implementation, report:

* files changed;
* data-model changes;
* how active Assessment is determined;
* Gap reconciliation behavior;
* tests added;
* commands run and results;
* known limitations.

Do not perform unrelated refactors.
