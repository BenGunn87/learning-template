---
name: assess-answer
description: Interpret one immutable initial, Practice, or Review Evidence event as an Assessment while keeping factual answers, evaluation, and review scheduling separate.
---

# Assess an Evidence event

Read `schemas/assessment.schema.yaml`, the referenced Evidence, its initialized Unit, and the relevant verification goal. Base the Assessment only on demonstrated answers, not on the user's confidence or claimed completion.

Assign each dimension one fixed value:

- `failed`: no usable demonstration or a fundamental misconception;
- `hard`: partial success with an important gap, uncertainty, or heavy prompting;
- `good`: correct and independently usable understanding;
- `easy`: precise, fluent understanding with clear transfer or trade-off reasoning.

Add concise Evidence-grounded gaps and a useful summary. Use the same `type` as the Evidence and ID `<evidence-id>-assessment-001`. For Review Evidence, call `calculate-review-outcome` with all three grades and store its result as `review_outcome`; never calculate the interval or due date yourself. Stage the YAML and call `create-assessment`.

For targeted Practice, reassess the target dimension from the new attempt. Carry forward a non-target dimension from the previous Assessment only when the new Evidence neither tests nor contradicts it; do not treat “not asked again” as failure. A Review prompt should be broad enough to support all three required grades while emphasizing the historically weak dimension.

Do not copy Assessment into Evidence, use numerical scores, overwrite an earlier Assessment, or grant mastery in a dimension the attempt did not demonstrate.
