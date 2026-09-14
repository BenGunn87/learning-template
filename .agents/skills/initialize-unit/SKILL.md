---
name: initialize-unit
description: Materialize a selected Frontier Skeleton Unit into a concrete initialized Unit immediately before study, without adding resources, assessment, or user progress.
---

# Initialize a Unit

Read the selected Skeleton in `map/frontier.yaml`, its Nodes and prerequisites in `map/graph.yaml`, `config/context.yaml`, relevant `progress/units.yaml` and Evidence when present, and `schemas/unit.schema.yaml`.

If `units/<unit-id>.yaml` already exists, run `python3 scripts/learning.py validate unit <unit-id>` and reuse it. Never silently replace an initialized Unit.

Otherwise create a concrete Unit that preserves the Skeleton ID and learning intent and contains:

- a precise learning goal and positive estimated minutes;
- non-empty concepts;
- two or three Study Focus questions without answers;
- one scenario or exercise goal that tests application;
- enabled recall, understanding, and application verification.

The Unit may reference only known Graph Nodes. Do not include Resources, mastery, assessment, Session state, next review, or any other user progress. Stage the YAML document, call `python3 scripts/learning.py create-unit <file>`, and retain the file only after validation succeeds.
