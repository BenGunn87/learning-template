---
name: pause-session
description: Safely pause the current learning Session when the user asks to stop, pause, or continue later.
---

# Pause a learning Session

Run `python3 scripts/learning.py detect-resumable-session` and require the repository's single unfinished Session to be `active`. Capture only the minimum state needed to continue: Unit, action, stage, completed-step flags, Study Mode, ordered selected Resources and each completion status, compact `discussion_summary` when present, current prompt or scenario, substantive answers already given, and an optional short note. Never store a chat transcript. Preserve an existing generated Resource ID and path exactly.

Write the checkpoint YAML and call:

```bash
python3 scripts/learning.py pause-session <session-id> --checkpoint <checkpoint.yaml>
```

This atomically timestamps the checkpoint, closes the open segment, and sets Session status to `paused`. Do not create Evidence or Assessment for an unfinished check, update Progress, lower mastery, or mark the Unit paused. A repeated pause is a no-op.

If no action has started, complete the Session without Evidence instead of pausing it. Report the persisted Unit, stage, completed steps, and the next safe continuation point.
