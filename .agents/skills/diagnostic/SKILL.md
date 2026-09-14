---
name: diagnostic
description: Run or resume the short initial diagnostic for a learning topic and record strong, weak, and unknown hypotheses without granting mastery.
---

# Run the initial diagnostic

Read `docs/SPEC.md`, `config/settings.yaml`, and `config/context.yaml`. The Context must already contain the user's goal, experience, constraints, and preferences.

If `diagnostic.enabled` is false, set `diagnostic.status: skipped` and stop.

Otherwise ask a short adaptive set of questions covering representative parts of the topic. Start with three to six questions that reveal starting depth and meaningful gaps; do not attempt exhaustive coverage or turn this into an exam.

After the initial questions, evaluate whether the diagnostic actually found the user's current boundary of understanding. If all assessed areas are `strong`, or if the user's stated goal requires higher-level practical or integrative ability that has not yet been tested, ask one or two harder or integrative follow-up questions targeted at that goal. For example, prefer a scenario that requires combining several concepts, making trade-offs, or explaining a decision rather than asking more factual questions.

Do not infer `strong` or `weak` for an area that was not meaningfully tested. Record such areas as `unknown` when they matter for routing.

Stop when either:

* the diagnostic has identified at least one meaningful weak/unknown boundary that is useful for choosing the initial route; or
* additional questions are unlikely to materially change the initial routing.

Keep the diagnostic short. Normally stay within 3–8 questions total.

Update only the `diagnostic` section of `config/context.yaml`:

- set `status: completed` and `completed_at`;
- add a concise overall `summary` when useful;
- record each representative area as `strong`, `weak`, or `unknown`, with a short evidence-based note.

These values are hypotheses used for routing. Never create Progress, mark prerequisites complete, or claim verified mastery from this diagnostic. Validate with:

```bash
python3 scripts/learning.py validate context
```

