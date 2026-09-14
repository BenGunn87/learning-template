---
name: build-frontier
description: Build or rebuild the derived Stage 1 Frontier with five to ten planning-only Skeleton Units based on Context, diagnostic, and the knowledge graph.
---

# Build the initial Frontier

Read `docs/SPEC.md`, `config/context.yaml`, `config/settings.yaml`, `map/graph.yaml`, and `schemas/frontier.schema.yaml`. Get deterministic technical input with:

```bash
python3 scripts/learning.py candidates
```

Use the candidates as constraints, then make the pedagogical prioritization. Diagnostic `strong` is only a hypothesis and does not by itself satisfy a prerequisite.

Create `map/frontier.yaml` with `format_version: 1`, a primary Graph Node focus, optional secondary Graph Node focuses, and the configured target number of Skeleton Units within the configured minimum and maximum. Each Unit contains only:

- `id`, `title`, `nodes`, `goal`, `estimated_minutes`, and `priority`;
- optional `blocked_by`, containing IDs of other Units in this Frontier.

Keep IDs readable and stable. Do not add resources, Study Focus, practice, verification, assessment, or mastery. Frontier is Derived Data and may be rebuilt, but its content must remain reproducible from current Primary Data through this workflow.

Run `python3 scripts/learning.py validate frontier` and resolve all errors.

