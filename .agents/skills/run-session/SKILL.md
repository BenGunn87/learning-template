---
name: run-session
description: Run a complete short learning Session when the user says they have time, asks to study, or invokes session with a minute budget in an initialized learning repository.
---

# Run a learning Session

Read `docs/SPEC.md` sections 20–28 and 33–38, plus `docs/PLAN_STAGE_2.md`. Treat repository files, not chat memory, as state.

1. Run `python3 scripts/learning.py state` and `python3 scripts/learning.py validate`. If the repository is uninitialized, do not create a Session; offer `init`. If it is invalid, report the validation error and stop.
2. Resolve the time budget from the user's request or `config/context.yaml`, then run `python3 scripts/learning.py session-candidates --minutes <minutes>`. Recommend an available Unit using availability, existing Progress, primary focus, fit, and priority. Show up to three reasonable choices when the decision is not obvious. Frontier is a recommendation and the user may choose another available candidate.
3. After the Unit is chosen, run `create-session`. Never create a second Session when an active one exists; report its ID. Stage 2 has no pause/resume recovery workflow.
4. Load and follow `.agents/skills/initialize-unit/SKILL.md` for the planned Unit, then `.agents/skills/find-resources/SKILL.md`. The user must explicitly choose a Resource.
5. Load and follow `.agents/skills/run-study/SKILL.md`. Do not accept merely reading or watching as completion.
6. Build Evidence from the actual interaction. Preserve the user's recall answers, practice answer, and takeaways as factual content; keep interpretation out of Evidence. Use ID `<session-id>-initial`, type `initial`, and an RFC 3339 timestamp. Stage the YAML document and call `create-evidence`.
7. Load and follow `.agents/skills/assess-answer/SKILL.md` for that Evidence.
8. Run `update-progress`, then `complete-session <session-id> --evidence <evidence-id>`. Only after all succeed, run `status` and summarize the result and next options.

Use the schema files as the exact data contract. If a later write fails, do not delete or rewrite already-created Primary Data; report the preserved paths and stop so the deterministic operation can be retried safely.
