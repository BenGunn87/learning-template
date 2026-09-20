---
name: run-session
description: Start or continue a short resumable learning Session, including external, generated, and hybrid Study Modes, when the user has time or asks to study.
---

# Run a learning Session

Read `docs/SPEC.md` sections 20–28 and 33–39, plus `docs/PLAN_STAGE_4.md` and `docs/PLAN_STAGE_6.md`. Treat repository files, not chat memory, as state.

1. Run `python3 scripts/learning.py state`, `validate`, and `detect-resumable-session`. If the repository is uninitialized, offer `init`; if invalid, report the error and stop. Never create a second Session while one is `active` or `paused`.
2. Resolve the time budget for this visit from the request or Context. If a Session is `paused`, prefer continuation, briefly show its Unit/stage, and follow `../resume-session/SKILL.md`. If it is `active`, treat it as potentially stale and use that Skill's recovery flow. Resume keeps the Session ID and adds a segment with the new budget.
3. Otherwise run `python3 scripts/learning.py plan-session-candidates --minutes <minutes>`. Use its review budget, due Reviews, Practice Units, technical availability, `blocked_by_gaps`, routing reasons, primary focus, fit, and priority to propose a compact plan. A blocking Gap prevents the dependent branch, not its remediation Unit. A suggested action marked `partial: true` is valid when the available time meets `min_partial_unit_minutes`; omit planner-only fields when calling `create-session`.
4. Create one Session with the selected actions, for example `create-session --minutes 25 --action review:cache-invalidation --action study:estimate-workload`. A single `--unit` remains valid when the script can infer the action.
5. Execute each planned or resumed action, including a partial Unit selected by the planner:
   - `review`: load and follow `.agents/skills/run-review/SKILL.md`;
   - `practice`: load and follow `.agents/skills/run-practice/SKILL.md`;
   - `study`: load `initialize-unit`, then `run-study`. `run-study` presents the Study Modes before preparing Resources and loads `find-resources` only for an external component.
6. When an action's full check is finished, persist its checkpoint with `update-checkpoint --action-status completed`, then build one new immutable Evidence using the appropriate schema and an ID `<session-id>-<type>-NNN`. Initial Evidence uses canonical `resources[]` copied from the actually studied Session Resources without checkpoint-only `status`; never create new Stage 6 records with legacy `resource`. Preserve the user's answers and takeaways as factual content; keep evaluation out of Evidence. Never overwrite earlier Evidence or create it for an unfinished check.
7. Load and follow `.agents/skills/assess-answer/SKILL.md` for each new Evidence. Assessment creation updates persistent Gap signals. After completed actions have Evidence and Assessment, run `update-progress` and `update-routing-metadata`, then complete the Session with every new Evidence ID in actual execution order. Rebuild the Frontier when Gap status or impact materially changes the route. A Session may also complete without Evidence when the user stops before any action becomes `in_progress`.
8. If an action remains unfinished when the user wants to stop, follow `../pause-session/SKILL.md`; budget exhaustion alone never changes Session state. Finally run `status` and summarize the outcome and next options.

The actual action list may be shorter than the plan. Completed actions stay `completed`, the current unfinished action is `in_progress`, and untouched actions remain `planned`. If a write fails, preserve already-created Primary Data and report its paths so the deterministic step can be retried.
