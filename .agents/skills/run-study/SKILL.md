---
name: run-study
description: Select an external, generated, or hybrid Study Mode; prepare and study its Resources; optionally discuss them; then conduct independent Recall, Practice, and user-authored Takeaways.
---

# Run the study interaction

Read the active Session, initialized Unit, related Graph Nodes and prerequisites, Context, Diagnostic, Progress, Gaps, and Interests. Before preparing a Resource, present `external`, `generated`, and `hybrid`. Recommend one briefly when useful, but let the user override it. Study Mode belongs to this attempt, never to the Unit.

Prepare the selected mode:

- For `external`, load and follow `../find-resources/SKILL.md` and record the user's selection as `type: external` with a separate `format`.
- For `generated`, author a teaching-oriented article adapted to the Unit goal and relevant context. Avoid reteaching mastered prerequisites; explain known Gaps more carefully; use Interests only for relevant examples. For current, fast-changing, specification-dependent, or fact-sensitive claims, verify appropriate sources first and list them in frontmatter. Do not reveal answers to later Practice.
- For `hybrid`, prepare one external and one generated Resource. The generated article must stand independently rather than summarize the selected external material. Ask which order the user prefers.

Generated material is Primary Data. Give it a stable `resource-...` ID and full YAML frontmatter matching `schemas/resource.schema.yaml`, including `type: generated`, `format: article`, Unit, Session, depth, coverage, and supporting sources. Write the complete Markdown document to a staging file and persist it with `python3 scripts/learning.py create-generated-resource <file.md>`. Never overwrite or automatically regenerate an existing generated Resource. A flexible article should normally explain why the topic matters, key concepts and causal relationships, examples, common misconceptions, and a short summary without forcing irrelevant headings.

Persist a minimal canonical checkpoint with `update-checkpoint` after mode selection, Resource preparation, showing Study Focus, completion of each Resource, meaningful Discussion, every substantive Recall or Practice answer, and every stage change. Include `study_mode`, ordered `resources[]`, each Resource's `status: selected | completed`, completed-step flags, and only the current prompt/scenario and substantive answers needed to continue. A mode-only checkpoint may start with an empty `resources[]`. Never store a transcript. On resume, keep the saved order and completion statuses; reuse every saved generated Resource ID/path and never generate a replacement automatically.

Show the Unit's two or three Study Focus questions without answers, then let the user study each Resource. Only Resources marked `completed` are synchronized into `Session.study.resources` as actually used.

After Resource study, allow optional questions, clarifications, alternative explanations, examples, or comparison. If the Discussion is meaningful, save a compact `discussion_summary` with only applicable fields from `questions_raised`, `clarifications`, `misconceptions`, `possible_gaps`, `new_interests`, and `assessment_focus`. Omit it when discussion was not meaningful. An explicit new Interest may use `capture-interest`; never infer an Interest merely because a topic was mentioned.

Discussion is supported Study, not Evidence. It must not update Progress, create Evidence, or confirm a Gap. A possible weakness may shape `assessment_focus`, but only the independent check below can produce Evidence and an Assessment-backed Gap.

Clearly announce the transition to independent verification, then:

1. Ask a small set of questions that test recall and understanding without consulting the Resources. Require answers in the user's own words.
2. Give one compact scenario or exercise aligned with the Unit practice goal. Use examples different from the generated article and prefer a decision and trade-off explanation over a factual quiz.
3. Ask the user for two to four concise Takeaways in their own words. Do not write Takeaways for them. Point out a material error and let the user correct it when needed.

Keep the exact prompts, the substance of every user answer, and the ordered actually studied Resources available for Evidence. Retain enough specificity to tell which lowest Graph Nodes each recall, understanding, or application check actually tested; `assess-answer` records that mapping in `Assessment.evaluated`. Record factual observations separately. Do not assess mastery, update Progress, or complete the Session in this skill.

If interrupted before the whole check is complete, leave the interaction only in the checkpoint; it is not Evidence. Follow `../pause-session/SKILL.md` when the user asks to stop.
