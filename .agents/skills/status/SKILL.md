---
name: status
description: Show the current state, diagnostic summary, focus, and initial route of a learning repository when the user asks for status or progress.
---

# Show learning status

Read `docs/SPEC.md` and run:

```bash
python3 scripts/learning.py status
```

Use the script output as the factual status; do not reconstruct state from chat memory. You may add a brief interpretation, but do not invent Progress, mastery, reviews, or Sessions that are not present in repository files.
