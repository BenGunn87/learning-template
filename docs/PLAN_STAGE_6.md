Implement **Stage 6 — Study Modes & Generated Learning Material** in the current `learning-template` repository.

Use the existing repository architecture and Stage 1–5 implementation as the source of truth. Do not redesign already working subsystems unless required for Stage 6 compatibility.

Read first:

* `docs/SPEC.md`
* `docs/PLAN_STAGE_1.md`
* `docs/PLAN_STAGE_2.md`
* `docs/PLAN_STAGE_3.md`
* `docs/PLAN_STAGE_4.md`
* `docs/PLAN_STAGE_5.md`
* current Session, Evidence, checkpoint, validation, rebuild, and learning workflow implementations
* existing tests

Then create `docs/PLAN_STAGE_6.md` using the Stage 6 specification below and implement it.

## Goal

Extend the Study phase so every Unit can be studied using one of three modes:

```text
external
generated
hybrid
```

The existing learning pipeline after Study must remain mostly unchanged:

```text
Unit
→ choose study mode
→ prepare resource(s)
→ study
→ optional discussion
→ active recall
→ practice
→ evidence
→ assessment
→ progress
```

Preserve the existing architecture:

```text
Graph Node = what needs to be known
Unit = concrete learning action
Resource = how we learn it this time

Evidence = immutable fact
Assessment = append-only interpretation

Gap = Primary
Interest = Primary

Progress = Derived
Frontier = Derived
```

Keep the principle:

```text
AI creates meaning
code manages state
```

Do not move semantic lesson generation into deterministic Python code.

---

## 1. Study modes

Add Study Mode at the Session/study-attempt level:

```yaml
study:
  mode: external | generated | hybrid
```

Study Mode must not become a permanent property of Unit.

The same Unit may use different Study Modes in different Sessions.

### external

Use the existing external-resource workflow.

### generated

Create a learning article specifically for the current Unit and user context.

### hybrid

Use two independent resources:

```text
external resource
+
generated resource
```

Generated content must not automatically be a summary of the selected external article.

The user may study them in either order.

---

## 2. Study-mode selection

Before Resource selection/preparation, the conversational workflow should present:

```text
external
generated
hybrid
```

Codex may recommend one mode and briefly explain why, but the user must be able to override the recommendation.

Do not implement a complex deterministic recommendation engine.

This remains semantic AI behavior.

---

## 3. Resource model

Preserve:

```text
Unit = what we learn
Resource = how we learn it this time
```

Extend the resource concept to distinguish:

```text
external
generated
```

A Session must support multiple actually-used resources.

For example:

```yaml
study:
  mode: hybrid

  resources:
    - type: external
      title: ...
      url: ...
      format: article
      status: completed

    - type: generated
      id: resource-...
      path: resources/generated/resource-....md
      status: completed
```

Do not copy complete external articles into the repository.

---

## 4. Generated resources

Add:

```text
resources/
└── generated/
```

Generated learning material is **Primary Data**.

Reason: after generation it cannot be deterministically reconstructed in identical form.

A generated resource must have a stable ID and be persisted as a full document.

Suggested format:

```yaml
---
format_version: 1

id: resource-quorum-20260919-001
type: generated
created_at: ...

unit: quorum-reads-writes
session: session-...

title: Quorum reads and writes

learning_goal: >
  Understand how quorum reads and writes affect
  consistency, latency and availability.

depth: working

coverage:
  - quorum-basics
  - read-quorum
  - write-quorum

sources: []
---
```

Then include the complete generated learning material as Markdown body.

Follow existing repository conventions where possible.

---

## 5. Generation context

The conversational generation workflow should consider relevant information from:

```text
Unit goal
related graph nodes
prerequisites
Context
Diagnostic
Progress
Gaps
Interests
desired depth
```

The generated material should be adapted to the current user and Unit goal.

Avoid unnecessarily reteaching mastered prerequisites.

Known Gaps may receive more explanation.

Interests may influence examples where relevant, but must not derail the Unit goal.

---

## 6. Generated material structure

Use a flexible teaching-oriented structure similar to:

```text
Why this matters
Key concepts
Core explanation
Mental model / causal relationships
Examples
Common mistakes or misconceptions
Short summary
```

Do not force an identical template for every subject.

Generated material should optimize for understanding rather than encyclopedic completeness.

Do not deliberately reveal answers to future Practice tasks.

Use different examples in Practice.

---

## 7. Sources

Generated material may be based on model knowledge or verified external sources.

For topics that are current, fast-changing, specification-dependent, or fact-sensitive, the workflow should verify appropriate sources first.

Store referenced sources inside the generated resource:

```yaml
sources:
  - title: ...
    url: ...
```

In Hybrid mode, distinguish between:

```text
the external resource studied by the user
```

and:

```text
sources used to support the generated article
```

These are separate concepts.

---

## 8. Discussion

After studying resources, the user may discuss the material with Codex.

Discussion may contain:

```text
questions
clarifications
alternative explanations
additional examples
comparison of external and generated material
```

Do not store the entire conversation transcript.

If the discussion was meaningful, store a compact `discussion_summary` inside the Session.

Example:

```yaml
discussion_summary:
  questions_raised:
    - Why does increasing W affect write availability?

  clarifications:
    - Explained difference between quorum intersection and consistency guarantees.

  misconceptions:
    - User initially treated R + W > N as sufficient for every consistency guarantee.

  possible_gaps:
    - relationship between quorum and consistency guarantees

  new_interests:
    - sloppy quorum

  assessment_focus:
    - distinguish quorum intersection from consistency guarantees
```

If there was no meaningful discussion, the field may be absent or null.

Do not create a separate top-level Primary entity for DiscussionSummary.

---

## 9. Discussion boundaries

Discussion is Study, not Assessment.

Enforce conceptually:

```text
Study / Discussion != Evidence
```

DiscussionSummary:

* must not update Progress;
* must not create Evidence;
* must not directly create a confirmed Gap.

A possible weakness discovered in Discussion follows:

```text
discussion
→ possible_gap
→ assessment_focus
→ recall/practice
→ evidence
→ assessment
→ existing Gap mechanism
```

If the user explicitly expresses a new Interest during Discussion, the existing Stage 5 Interest mechanism may be used.

Do not infer an Interest merely because Codex mentioned a topic.

---

## 10. Assessment boundary

After Study/Discussion, clearly switch from supported learning to independent verification.

DiscussionSummary may influence:

```text
what should be tested
```

but never:

```text
the assessment result itself
```

Only independent Recall/Practice creates Evidence.

Do not weaken this boundary.

---

## 11. Session schema

Extend Session representation to support approximately:

```yaml
study:
  mode: external | generated | hybrid

  resources:
    - ...

  discussion_summary:
    ...
```

Store only actually-used resources.

If a suggested resource is replaced before study, history should reflect what was actually studied.

Do not store the complete Study transcript.

---

## 12. Evidence compatibility

Evidence should support multiple Resources.

Preferred new representation:

```yaml
resources:
  - type: external
    url: ...

  - type: generated
    id: resource-...
```

Old Evidence containing a single:

```yaml
resource:
```

must remain valid.

Do not require migration of historical Evidence.

---

## 13. Pause / Resume

Stage 4 behavior must work with all Study Modes.

Checkpoint state must contain enough information to restore:

```text
selected study mode
selected resources
which resources were completed
current Study stage
whether meaningful Discussion happened
```

Example concept:

```yaml
checkpoint:
  unit: quorum-reads-writes
  action: study
  stage: study

  study_mode: hybrid

  resources:
    external:
      selected: true
      completed: true

    generated:
      id: resource-quorum-20260919-001
      completed: false
```

Do not store full Discussion transcript in checkpoint.

Very important:

If a generated resource already exists before pause, Resume must reference and reuse it.

Do **not** generate a replacement article automatically.

---

## 14. Hybrid resume behavior

Support this workflow:

```text
choose hybrid
→ study external
→ pause
→ resume
→ study generated
→ discussion
→ recall
→ practice
```

Checkpoint/resume must know that the external resource is already complete while the generated resource is not.

Also support the reverse order:

```text
generated
→ external
```

---

## 15. Deterministic validation

Extend deterministic scripts only where necessary.

Validate:

```text
valid study_mode values
generated-resource structure
resource IDs
resource paths
generated-resource existence
Session resource references
Evidence resource references
checkpoint consistency
```

Do not implement semantic article generation in Python.

---

## 16. Backward compatibility

Existing Stage 1–5 repositories must remain valid.

Do not require repository migration.

Historical Sessions/Evidence without:

```text
study_mode
resources[]
discussion_summary
```

must continue to validate and rebuild.

An old single external `resource` may logically be treated as equivalent to external mode where necessary, but do not rewrite historical data automatically.

Existing Stage 1–5 tests must continue to pass.

---

## 17. Rebuild behavior

Generated resources are Primary Data.

Rebuild must:

* never recreate generated articles;
* never rewrite generated articles;
* preserve their IDs and references;
* preserve historical resource usage.

Progress, Frontier and other Derived state should remain rebuildable according to existing rules.

---

## 18. Tests

Add tests covering at least:

### External regression

```text
external
→ resource
→ study
→ recall
→ practice
→ evidence
→ assessment
```

Existing behavior still works.

### Generated mode

```text
generated
→ generated file created
→ Session references it
→ study
→ practice
→ Evidence references it
```

### Generated + pause/resume

```text
generate article
→ pause
→ resume
```

The same generated resource is reused.

### Hybrid

```text
hybrid
→ external resource
→ generated resource
→ both studied
→ Evidence references both
```

### Hybrid ordering

Support both:

```text
external → generated
```

and:

```text
generated → external
```

### Hybrid partial pause

```text
first resource completed
second resource incomplete
→ pause
→ resume
```

Correct state must be restored.

### Discussion summary

Meaningful Discussion creates a summary.

No meaningful Discussion does not require one.

### Discussion boundary

A DiscussionSummary alone must not:

```text
create Evidence
update Progress
create confirmed Gap
```

### Possible Gap

Verify flow:

```text
possible_gap
→ assessment_focus
→ weak Evidence
→ Assessment
→ existing Gap mechanism
```

### Interest

Explicitly stated Interest during Discussion may use the existing Stage 5 Interest mechanism.

### Backward compatibility

Old repositories and old Session/Evidence formats continue to validate and rebuild.

---

## 19. SPEC update

After implementation, update `docs/SPEC.md` with:

* Study Modes;
* Generated Resource as Primary Data;
* `resources/generated/`;
* multiple resources per study attempt;
* Hybrid semantics;
* DiscussionSummary;
* Discussion/Assessment boundary;
* new checkpoint semantics;
* backward compatibility with old single-resource records.

Do not unnecessarily redefine mastery, Progress, Gap or Frontier semantics.

---

## 20. Scope exclusions

Do not implement:

```text
long-inactivity recalibration
assessment reevaluation workflow
automatic course generation
automatic regeneration of generated articles
full chat transcript persistence
RAG over generated materials
resource-quality scoring
external-vs-generated ranking
complex study-mode recommendation algorithm
Web UI
multi-agent architecture
advanced learning-style personalization
```

Keep Stage 6 focused.

---

## 21. Verification

Run the complete existing test suite plus the new Stage 6 tests.

At minimum:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/learning.py validate
```

Use actual project commands if they differ.

Also manually verify a complete scenario:

```text
start Session
→ choose hybrid
→ select external article
→ generate article
→ study first resource
→ pause
→ resume
→ study second resource
→ discuss
→ active recall
→ practice
→ assessment
→ inspect Session
→ inspect Evidence
→ validate
→ rebuild
```

After rebuild, generated resources and historical Resource references must remain unchanged.

---

## Implementation approach

Before modifying code:

1. inspect the current repository;
2. identify the smallest set of files/components that need changes;
3. preserve existing conventions;
4. update/add tests together with implementation;
5. avoid speculative refactoring.

If the current implementation differs from assumptions in this prompt, adapt Stage 6 to the actual architecture rather than forcing the examples literally.

After implementation, provide a concise report containing:

* files changed;
* data-model changes;
* workflow changes;
* backward-compatibility behavior;
* tests added;
* commands run and results;
* any known limitations or follow-up items.

Stage 6 is complete only when all three modes:

```text
external
generated
hybrid
```

can complete the full existing learning cycle, including Pause/Resume, without breaking Stage 1–5 behavior.
