---
name: status
description: Show repository-backed learning progress, mastery gaps, due Reviews, review dates, active Session, focus, and next Units when the user asks for status or progress.
---

# Show learning status

Read `docs/SPEC.md` and run:

```bash
python3 scripts/learning.py status
```

Use the script output as the factual status; do not reconstruct state from chat memory. It reports the one paused or potentially stale active Session, its persisted checkpoint, and active time from closed segments. Keep Unit mastery and review scheduling distinct: the only mastery statuses are `learning`, `practice`, and `verified`, while due dates and intervals live under `Progress.review`. Pause never implies failure or changes mastery. You may add a brief interpretation but must not invent Progress, mastery, Reviews, or Sessions absent from repository files.
