---
name: resume-session
description: Resume a paused learning Session or recover a potentially stale active Session from persisted or reconstructed semantic state.
---

# Resume or recover a learning Session

Run `python3 scripts/learning.py detect-resumable-session`. Repository state is authoritative, and the same logical Session ID must be retained.

For `paused`, briefly show the saved Unit and stage, prefer continuation, and call:

```bash
python3 scripts/learning.py resume-session <session-id> --minutes <new-budget>
```

This starts one new segment. Reuse the saved Study Mode, Resource order, completion statuses, generated Resource IDs/paths, discussion summary, prompt or scenario, and substantive answers; skip completed Resources and steps. Never automatically regenerate saved material. Repeating resume while already active must not add a segment.

For a potentially stale `active` Session with a checkpoint, explain that recovery will close the interrupted segment at `checkpoint.updated_at`, then call:

```bash
python3 scripts/learning.py recover-session <session-id> --minutes <new-budget>
```

If no checkpoint exists, do not invent state or ask the user to estimate elapsed time. Ask only for the minimum semantic state: current Unit, action, stage, completed steps, Study Mode, ordered Resources and completion states when known, compact discussion summary when applicable, and any partial interaction. Write that reconstructed state to a temporary checkpoint YAML and pass it directly to recovery:

```bash
python3 scripts/learning.py recover-session <session-id> --minutes <new-budget> --checkpoint <checkpoint.yaml>
```

Never call ordinary `update-checkpoint` on the stale segment first. Recovery closes that segment at its own `started_at`, opens the new segment, and only then saves the reconstructed checkpoint with the recovery timestamp. A Review due date and Unit mastery remain unchanged until completed Evidence and Assessment exist.
