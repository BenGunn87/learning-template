---
name: build-learning-map
description: Build the initial Stage 1 knowledge graph from the repository Context and diagnostic, or validate an existing initial graph without adding user progress.
---

# Build the initial knowledge graph

Read `docs/SPEC.md`, `config/context.yaml`, `schemas/graph.schema.yaml`, and any existing `map/graph.yaml`. Do not replace a non-null Graph during init without explicit confirmation.

Create a useful initial map rather than an exhaustive ontology:

- cover the major areas of the topic;
- expand the most relevant near-term areas in more detail;
- use only `area`, `topic`, and `concept` nodes;
- use only `part-of`, `prerequisite`, and `related` edges;
- encode `part-of` from child to parent and `prerequisite` from prerequisite to dependent node;
- use durable, readable lowercase kebab-case IDs;
- keep Diagnostic and all user Progress out of the Graph.

Include `format_version: 1`. Prefer concise summaries, importance values, and tags only where they aid later decisions. Then run:

```bash
python3 scripts/learning.py validate graph
```

Resolve every validation error before continuing.

When an explicit Interest requires a missing concept, add only the nearest meaningful layer needed to link that Interest. Apply a small unambiguous additive delta with `expand-graph`; propose a large or ambiguous graph delta to the user before changing the Graph. Do not eagerly build product-specific subtrees.
