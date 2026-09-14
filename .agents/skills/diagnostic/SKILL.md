---
name: diagnostic
description: Run or resume the short initial diagnostic for a learning topic and record strong, weak, and unknown hypotheses without granting mastery.
---

# Run the initial diagnostic

Read `docs/SPEC.md`, `config/settings.yaml`, and `config/context.yaml`. The Context must already contain the user's goal, experience, constraints, and preferences.

If `diagnostic.enabled` is false, set `diagnostic.status: skipped` and stop. Otherwise ask a short adaptive set of questions covering representative parts of the topic. Prefer three to six questions that reveal starting depth and meaningful gaps; do not attempt exhaustive coverage or turn this into an exam.

Update only the `diagnostic` section of `config/context.yaml`:

- set `status: completed` and `completed_at`;
- add a concise overall `summary` when useful;
- record each representative area as `strong`, `weak`, or `unknown`, with a short evidence-based note.

These values are hypotheses used for routing. Never create Progress, mark prerequisites complete, or claim verified mastery from this diagnostic. Validate with:

```bash
python3 scripts/learning.py validate context
```

