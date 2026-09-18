---
name: status
description: Show repository-backed learning progress, persistent Gaps, Interests, due Reviews, active Session, focus, and adaptive next Units when the user asks for status or progress.
---

# Show learning status

Read `docs/SPEC.md` and run:

```bash
python3 scripts/learning.py status
```

Use the script output as the factual status; do not reconstruct state from chat memory. Supplement it with `list-gaps` and `list-interests` when their lifecycle detail is relevant. It reports the one paused or potentially stale active Session, its persisted checkpoint, and active time from closed segments. Keep Unit mastery, persistent Gaps, Interests, and review scheduling distinct: Unit mastery statuses remain `learning`, `practice`, and `verified`; review dates live under `Progress.review`; Gap and Interest states live in their own Primary Data. Pause never implies failure or changes mastery. You may add a brief interpretation but must not invent repository state.
