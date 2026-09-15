---
name: run-session
description: Run a complete short learning Session when the user says they have time, asks to study, or invokes session with a minute budget in an initialized learning repository.
---

# Run a learning Session

Read `docs/SPEC.md` sections 20–28 and 33–38, plus `docs/PLAN_STAGE_3.md`. Treat repository files, not chat memory, as state.

1. Run `python3 scripts/learning.py state` and `python3 scripts/learning.py validate`. If the repository is uninitialized, offer `init`. If invalid, report the validation error and stop. If an active Session exists, report its ID; Stage 3 has no pause/resume recovery workflow.
2. Resolve the time budget from the request or Context and run `python3 scripts/learning.py plan-session-candidates --minutes <minutes>`. Use its review budget, due Reviews, Practice Units, availability, primary focus, fit, and priority to propose a compact plan. Do not turn overdue Reviews into a debt or exceed the configured review share.
3. Create one Session with the selected actions, for example `create-session --minutes 25 --action review:cache-invalidation --action study:estimate-workload`. A single `--unit` remains valid when the script can infer the action.
4. Execute each planned action that fits the remaining budget:
   - `review`: load and follow `.agents/skills/run-review/SKILL.md`;
   - `practice`: load and follow `.agents/skills/run-practice/SKILL.md`;
   - `study`: load `initialize-unit`, `find-resources`, and `run-study` in that order. The user must explicitly choose the Resource.
5. For every completed action, build a new immutable Evidence using the appropriate schema and an ID `<session-id>-<type>-NNN`. Preserve the user's answers and takeaways as factual content; keep evaluation out of Evidence. Never overwrite earlier Evidence.
6. Load and follow `.agents/skills/assess-answer/SKILL.md` for each new Evidence. After all completed actions have Evidence and Assessment, run `update-progress`, then complete the Session with every new Evidence ID in actual execution order.
7. Run `status` and summarize the outcome and next options.

The actual action list may be shorter than the plan when Practice or Review consumes the remaining budget. This is a valid completed Session. If a write fails, preserve already-created Primary Data and report its paths so the deterministic step can be retried.
