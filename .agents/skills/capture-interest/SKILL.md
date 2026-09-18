---
name: capture-interest
description: Capture an explicit user-declared learning topic for later or deeper study as a persistent Interest without forcing it to become the next Unit.
---

# Capture a learning Interest

Use this workflow only for an explicit request such as “хочу глубже изучить…”, “добавь в темы…”, or “позже хочу пройти…”. Do not infer Interests from ordinary questions or weak Assessment results. If the user says to study it next, preserve that as a user override in Frontier routing rather than treating the Interest itself as a hard override.

Read `map/graph.yaml`, `schemas/interest.schema.yaml`, and current `interests/`. Find the nearest existing Graph Nodes that faithfully represent the request. Use `inspect-related-nodes` when relationships are unclear.

Graph expansion is integration-first. Before creating any parent, topic, or area node, search the existing Graph for semantic attachment candidates. Prefer, in order:

```text
reuse an existing node
→ attach a new leaf to an existing branch
→ add a new intermediate node
→ add a new top-level area
```

Do not add a grouping node when an existing node already represents the same or a sufficiently close learning dimension. Add an intermediate parent only when no existing node is a reasonable semantic parent, the parent is a genuinely distinct concept rather than a synonym or rephrasing, and it improves the current hierarchy instead of starting a parallel taxonomy. Small automatic expansion must remain anchored to the pre-existing Graph.

If the Graph is too coarse, prepare the smallest meaningful additive layer and apply a small, unambiguous, anchored YAML delta with `expand-graph`. A new disconnected or top-level branch is a structural delta: explain why it is genuinely separate, show the proposal, request user confirmation, and only then use `expand-graph --allow-unanchored`. Treat a new top-level area as the most expensive option. Do not create an exhaustive vendor or implementation subtree merely because it might become useful later.

Create one Interest YAML with:

- a durable `interest-...` ID;
- current RFC 3339 `created_at`, `source: user`, and the user's original request;
- one or more valid `related_nodes`;
- `status: pending` and a matching first history entry.

Call `create-interest`, then validate the Interest. Do not make it the next Unit or mark it active. `build-frontier` decides how it competes with the primary route; `update-routing-metadata` activates it only after a Frontier Unit explicitly carries its Interest routing reason. Only semantic review of the original request, goal, graph coverage, Progress, and Evidence may mark it `satisfied`. Use `dismissed` only when the user explicitly withdraws it.
