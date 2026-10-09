---
name: run-remediation
description: Teach a relevant active Gap after a Practice or Review Assessment inside the same Session, or resume that teaching without creating another independent attempt.
---

# Teach after an Assessment

Read the current Session/checkpoint, source Evidence, its active Assessment, Unit, and relevant Gaps. Remediation is optional teaching after Practice/Review, not a Session plan action. Offer it only for an active Gap with a signal tied to this source Evidence/Assessment. Prefer blocking prerequisite, confirmed, recurring, or directly limiting Gaps; the user need not work on every Gap.

If `checkpoint.phase: remediation` exists, continue its saved ID, Gap, level, step, and Resource. Do not redo Practice/Review, append Evidence/Assessment, or regenerate a saved mini-lesson. Otherwise, after the user accepts, choose the level semantically:

- **1 — Clarification:** what was wrong, why, and the correct mental model for a local mistake.
- **2 — Explanation + Example:** an alternative explanation, a new example, and guided reasoning for unstable understanding.
- **3 — Mini-lesson:** context, concept, explanation, example, misconception, and summary for a fundamental weakness.

Stage a YAML document matching `schemas/remediation.schema.yaml` with `id: remediation-...`, `session`, `unit`, `gap`, `source_evidence`, `source_assessment`, `level`, and concise `focus`. `step`, `misconceptions_addressed`, `guided_exercise`, and null `resource` have defaults in `start-remediation`. Call:

```bash
python3 scripts/learning.py start-remediation <remediation.yaml>
```

The source action must still be `in_progress` or `planned`; never mark it completed before offering teaching. Use the active Assessment tip to start. Older completed teaching keeps its original historical Assessment even after reevaluation.

Teach at the selected depth. You may give hints, leading questions, corrections, and a short guided exercise. Guided success is not independent Evidence: never assess it, resolve the Gap, increment attempts, reschedule Review, or immediately retest mastery. Escalate 1 → 2 → 3 when useful. Persist changes to level, step, addressed misconceptions, and the guided-exercise flag using the existing `update-checkpoint`; keep the source action/unit and `phase: remediation`. Save only concise teaching state, without a transcript.

For Level 3, author a mini-lesson adapted to the Gap and source Unit. Use existing generated-resource frontmatter plus `purpose: remediation` and `gap: <gap-id>`. Coverage includes the Gap node and stays within `unit.nodes`. Verify changing or specification-dependent claims against appropriate sources. Stage the full Markdown and call `create-generated-resource <lesson.md>`: it attaches the Resource ID/path to the active checkpoint, with rollback on a write failure. Reuse that document on resume. Level 3 cannot complete without a saved Resource; Levels 1 and 2 need no saved article.

When teaching is finished, call:

```bash
python3 scripts/learning.py complete-remediation <remediation-id>
```

This appends Gap provenance and a lightweight Session reference, then returns the source checkpoint to `stage: assessment`. It leaves the source action `in_progress`, allowing another selected Gap to receive teaching before the caller marks the action completed. Completion is idempotent. Explain that we worked on the weakness and that ordinary later Practice/Review will verify it.

If the user skips, call `skip-remediation <session-id>` and return to normal action completion. A saved mini-lesson stays linked through `Session.skipped_remediations`; no completed Gap provenance is created. If they finish the Session immediately, pass all already-created Evidence IDs to `complete-session`, which performs this skip. If they stop to continue later, follow `../pause-session/SKILL.md` instead.
