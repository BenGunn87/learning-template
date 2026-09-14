---
name: topic-onboarding
description: Initialize an uninitialized learning repository when the user says they want to study a topic or explicitly asks to run init. Do not use for starting a study session in an initialized repository.
---

# Initialize a learning topic

Read `docs/SPEC.md` and `docs/PLAN.md`, then run:

```bash
python3 scripts/learning.py state
```

If the repository is initialized, do not overwrite it. Explain which topic is already configured and offer `status`. If it is partial, inspect the non-null artifacts, preserve them, and resume only the missing steps; ask before replacing any existing Primary Data.

For an uninitialized repository, gather the topic plus the following context in roughly five or six conversational questions. Reuse facts already supplied by the user:

- motivation and concrete desired outcome;
- current experience;
- desired depth: `overview`, `working`, or `deep`;
- usual session duration and, if useful, sessions per week;
- acceptable material languages and preferred resource formats.

Write `learning.yaml` with a durable lowercase kebab-case topic ID, title, core version, and current date. Write `config/context.yaml` against `schemas/context.schema.yaml`, initially setting `diagnostic.status: pending`. Keep dates as `YYYY-MM-DD` strings and preserve all unrelated fields when resuming.

Continue the same init flow by reading and following, in order:

1. `../diagnostic/SKILL.md`
2. `../build-learning-map/SKILL.md`
3. `../build-frontier/SKILL.md`

Finish with `python3 scripts/learning.py validate` and `python3 scripts/learning.py status`. Do not begin a full learning Unit during Stage 1.

