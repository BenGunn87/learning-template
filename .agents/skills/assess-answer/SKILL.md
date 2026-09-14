---
name: assess-answer
description: Interpret one immutable Evidence event as an initial Assessment of recall, understanding, and application, while keeping factual answers and evaluation separate.
---

# Assess an Evidence event

Read `schemas/assessment.schema.yaml`, the referenced Evidence, and its initialized Unit. Base the assessment only on demonstrated answers and practice, not on the user's claim that the Resource was completed.

Assign each dimension one fixed value:

- `failed`: no usable demonstration or a fundamental misconception;
- `hard`: partial success with an important gap, uncertainty, or heavy prompting;
- `good`: correct and independently usable understanding;
- `easy`: precise, fluent understanding with clear transfer or trade-off reasoning.

Add concise gaps grounded in Evidence and a useful summary. Do not copy the Assessment into Evidence, use numerical scores, or add review scheduling. Stage an initial event with ID `<evidence-id>-assessment-001`, type `initial`, and an RFC 3339 timestamp, then call `python3 scripts/learning.py create-assessment <file>`. Stage 2 does not reevaluate or overwrite an existing Assessment.
