---
name: find-resources
description: Find and present replaceable external learning Resources for an initialized Unit when external or hybrid Study Mode needs material or the user rejects it.
---

# Find external learning Resources

Read the initialized Unit and the language and format preferences in `config/context.yaml`. Search current web sources and verify that each recommended direct URL is accessible and actually covers the Unit goal.

Present two or three alternatives. For each include title, direct URL, `format`, language, estimated study time, difficulty, and a short reason tied to the Unit goal and current Session budget. Cite the source page used for the recommendation. When persisted, use `type: external`; `format` carries `article`, `documentation`, `video`, `course`, `book`, or `interactive`.

Do not silently choose, and do not modify the Unit based on a Resource. Wait for the user's choice. If the user rejects the options, search again while preserving the same Unit goal. Candidate Resources are not repository state; only selected Resources enter the checkpoint, and only actually studied Resources enter Session history and Evidence.
