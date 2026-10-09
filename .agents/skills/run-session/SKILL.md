---
name: run-session
description: Start or continue a short resumable learning Session, including external, generated, and hybrid Study Modes, when the user has time or asks to study.
---

# Run a learning Session

Read `docs/SPEC.md` sections 19–28 and 33–41. Treat repository files, not chat memory, as state.

1. Run `python3 scripts/learning.py state`, `validate`, and `detect-resumable-session`. If the repository is uninitialized, offer `init`; if invalid, report the error and stop. Never create a second Session while one is `active` or `paused`.
2. Resolve the time budget for this visit from the request or Context. If a Session is `paused`, prefer continuation, briefly show its Unit/stage, and follow `../resume-session/SKILL.md`. If it is `active`, treat it as potentially stale and use that Skill's recovery flow. Resume keeps the Session ID and adds a segment with the new budget.
3. Otherwise run `python3 scripts/learning.py plan-session-candidates --minutes <minutes>`. Use its review budget, due Reviews, Practice Units, technical availability, `blocked_by_gaps`, routing reasons, primary focus, fit, and priority to propose a compact plan. A blocking Gap prevents the dependent branch, not its remediation Unit. A suggested action marked `partial: true` is valid when the available time meets `min_partial_unit_minutes`; omit planner-only fields when calling `create-session`.
4. Create one Session with the selected actions, for example `create-session --minutes 25 --action review:cache-invalidation --action study:estimate-workload`. A single `--unit` remains valid when the script can infer the action.
5. Execute each planned or resumed action, including a partial Unit selected by the planner:
   - `review`: load and follow `.agents/skills/run-review/SKILL.md`;
   - `practice`: load and follow `.agents/skills/run-practice/SKILL.md`;
   - `study`: load `initialize-unit`, then `run-study`. `run-study` presents the Study Modes before preparing Resources and loads `find-resources` only for an external component.
6. When an action's full check is finished, save its checkpoint and build one immutable Evidence using the appropriate schema and an ID `<session-id>-<type>-NNN`. Keep Practice/Review `in_progress` until its Assessment and optional Remediation are finished or skipped; Study may use `update-checkpoint --action-status completed`. Initial Evidence uses canonical `resources[]` copied from actually studied Session Resources without checkpoint-only `status`; never create new study records with legacy `resource`. Preserve answers and takeaways as factual content, without evaluation. Never overwrite Evidence or create it for an unfinished check.
7. Load and follow `.agents/skills/assess-answer/SKILL.md` for each new Evidence, then run `update-progress`. Assessment creation updates persistent Gap signals. For Practice/Review with a relevant active Gap, offer a short targeted explanation now. If accepted, follow `../run-remediation/SKILL.md`; if declined, finish the source action normally. Remediation stays in this Session and never changes mastery or Review dates. After teaching is finished or skipped, mark the source action completed with `update-checkpoint --action-status completed`. Once selected actions are finished, run `update-routing-metadata` and complete the Session with all its Evidence IDs in execution order. Rebuild Frontier only when Assessment/Gap status or impact changes routing, never because teaching was recorded. A Session may also complete without Evidence before any action becomes `in_progress`.
8. If an action remains unfinished when the user wants to stop, follow `../pause-session/SKILL.md`; budget exhaustion alone never changes Session state. Finally run `status` and summarize the outcome and next options.

The actual action list may be shorter than the plan. Completed actions stay `completed`, the current unfinished action is `in_progress`, and untouched actions remain `planned`. If a write fails, preserve already-created Primary Data and report its paths so the deterministic step can be retried.

On continuation, inspect the saved phase before executing a check. `phase: remediation` resumes `run-remediation` directly: its Evidence and Assessment already exist. For an assessment checkpoint, completed teaching references, or skipped teaching, read existing Evidence for this Session from relevant Unit directories and resolve each active Assessment. Reuse these events and include their IDs in Session completion; do not repeat the check or append another Assessment merely because the action is still `in_progress`.

If the user says to finish the Session during teaching, `complete-session` explicitly skips the unfinished Remediation and retains any mini-lesson in `Session.skipped_remediations`; include the source Evidence ID. If they want to continue later, pause instead. Describe completed teaching as work on a weakness, never as verified resolution.
