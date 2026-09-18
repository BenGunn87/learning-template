---
name: assess-answer
description: Interpret one immutable initial, Practice, or Review Evidence event as an Assessment while keeping factual answers, evaluation, and review scheduling separate.
---

# Assess an Evidence event

Read `schemas/assessment.schema.yaml`, the referenced Evidence, its initialized Unit, the relevant verification goal, and `map/graph.yaml`. Base the Assessment only on demonstrated answers, not on the user's confidence or claimed completion.

Assign each dimension one fixed value:

- `failed`: no usable demonstration or a fundamental misconception;
- `hard`: partial success with an important gap, uncertainty, or heavy prompting;
- `good`: correct and independently usable understanding;
- `easy`: precise, fluent understanding with clear transfer or trade-off reasoning.

Add concise Evidence-grounded gaps and a useful summary. Keep `result` as the complete current mastery state, including a carried-forward grade when the current Evidence did not retest that dimension. Separately add `evaluated`: for every dimension actually tested now, list the lowest meaningful Graph Nodes tested by that dimension. Omit a dimension from `evaluated` when its result was only carried forward. Do not attribute a parent merely because it contains the tested concept, and do not use one shared node list when different dimensions tested different nodes.

Use the same `type` as the Evidence and ID `<evidence-id>-assessment-001`. For Review Evidence, call `calculate-review-outcome` with all three grades and store its result as `review_outcome`; never calculate the interval or due date yourself. Stage the YAML and call `create-assessment`.

`create-assessment` applies Gap logic only to dimension/node pairs in `evaluated`; grades present only in `result` cannot become signals. One Evidence contributes at most one independent signal to a given node and dimension. A second weak Evidence confirms the Gap. A successful reevaluation may resolve either a detected or confirmed Gap, while a later weak signal reopens the same Gap ID as confirmed. Inspect the result with `list-gaps`; use `detect-weak-signals --evidence <id>` when attribution needs review. Never promote child signals to a parent or create a `cross-concept` Gap without semantic evidence from several related child concepts.

For targeted Practice, normally include only its target dimension in `evaluated`. Carry forward a non-target dimension in `result` only when the new Evidence neither tests nor contradicts it; do not add that dimension to `evaluated`. A Review prompt should be broad enough to support all three required grades while emphasizing the historically weak dimension; attribute each demonstrated dimension only to the nodes its prompt actually tested.

Do not copy Assessment into Evidence, use numerical scores, overwrite an earlier Assessment, or grant mastery in a dimension the attempt did not demonstrate.
