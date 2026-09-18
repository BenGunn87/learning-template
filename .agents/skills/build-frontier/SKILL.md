---
name: build-frontier
description: Build or rebuild the adaptive Frontier with five to ten planning-only Skeleton Units using graph availability, Progress, Gaps, Interests, Context, and diagnostic hypotheses.
---

# Build the adaptive Frontier

Read `docs/SPEC.md`, `docs/PLAN_STAGE_5.md`, `config/context.yaml`, `config/settings.yaml`, `map/graph.yaml`, `schemas/frontier.schema.yaml`, and current `progress/`, `gaps/`, and `interests/` data. Get deterministic technical input with:

```bash
python3 scripts/learning.py candidates
```

Use technical availability and prerequisite impact as constraints, then make the pedagogical prioritization. Diagnostic `strong` is only a hypothesis and does not by itself satisfy a prerequisite.

Prioritize with judgment rather than a strict queue:

- route around a confirmed `blocking` Gap by placing suitable remediation before its dependent branch;
- raise an `important` Gap, but do not let remediation consume the whole Frontier;
- keep the primary route moving;
- raise related branches for `pending` or `active` Interests without treating them as a hard override;
- leave `minor` Gaps opportunistic unless they fit the route.

Choose remediation separately from the Gap: use Review for forgetting verified material, targeted Practice for weak application, an existing or new study Unit for weak understanding, and a prerequisite Unit for missing foundations. Reuse an existing Unit when it is suitably narrow.

Use `prerequisite-impact` for the deterministic blocking check. When semantic relevance to the primary focus, goal, or Context makes a non-blocking Gap `important` or `minor`, persist that judgment with `update-gap-impact`; never downgrade a confirmed prerequisite Gap from `blocking`.

Create `map/frontier.yaml` with `format_version: 1`, a primary Graph Node focus, optional secondary Graph Node focuses, and the configured target number of Skeleton Units within the configured minimum and maximum. Each Unit contains only:

- `id`, `title`, `nodes`, `goal`, `estimated_minutes`, and `priority`;
- optional `blocked_by`, containing IDs of other Units in this Frontier;
- `routing_reasons`, with one or more `primary-route`, `gap`, `interest`, `context`, `diagnostic`, or `user-override` reasons. Gap and Interest reasons must reference their persistent IDs.

Keep IDs readable and stable. Do not add resources, Study Focus, practice, verification, assessment, or mastery. Frontier is Derived Data and may be rebuilt, but its content must remain reproducible from current Primary Data through this workflow.

After writing the Frontier, run `python3 scripts/learning.py update-routing-metadata`; this refreshes deterministic Gap impact and changes an Interest from `pending` to `active` only when a Frontier Unit explicitly references it. Then run `python3 scripts/learning.py validate frontier` and resolve all errors. Mark an Interest `satisfied` only through `update-interest` after semantically checking its original request, related nodes, current goal, Progress, and Evidence; Unit count alone is insufficient.
