---
name: find-resources
description: Find and present replaceable learning Resources for an initialized Unit when a Session needs material or the user rejects the current material.
---

# Find learning Resources

Read the initialized Unit and the language and format preferences in `config/context.yaml`. Search current web sources and verify that each recommended direct URL is accessible and actually covers the Unit goal.

Present two or three alternatives. For each include title, direct URL, type, language, estimated study time, difficulty, and a short reason tied to the Unit goal and current Session budget. Cite the source page used for the recommendation.

Do not silently choose, and do not modify the Unit based on a Resource. Wait for the user's choice. If the user rejects the options, search again while preserving the same Unit goal. Candidate Resources are not repository state; only the Resource actually used is later recorded in Evidence.
