---
name: resume-session
description: Resume a paused learning Session or recover a potentially stale active Session from its repository checkpoint.
---

# Resume or recover a learning Session

Run `python3 scripts/learning.py detect-resumable-session`. Repository state is authoritative, and the same logical Session ID must be retained.

For `paused`, briefly show the saved Unit and stage, prefer continuation, and call:

```bash
python3 scripts/learning.py resume-session <session-id> --minutes <new-budget>
```

This starts one new segment. Reuse the saved Resource, prompt or scenario, and substantive answers; skip completed steps. Repeating resume while already active must not add a segment.

For a potentially stale `active` Session with a checkpoint, explain that recovery will close the interrupted segment at `checkpoint.updated_at`, then call:

```bash
python3 scripts/learning.py recover-session <session-id> --minutes <new-budget>
```

If no checkpoint exists, do not invent state. Ask where the user stopped, persist the reconstructed minimum checkpoint only after they answer, and then recover. A Review due date and Unit mastery remain unchanged until completed Evidence and Assessment exist.
