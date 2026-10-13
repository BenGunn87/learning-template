---
name: manage-reference
description: Show or find reusable course knowledge in Reference, or add and update its editable Markdown when the user requests or confirms a change.
---

# Manage the course Reference

Reference is editable Primary Data in `reference/`: compact definitions, formulas, rules, heuristics, relationships, and trade-offs useful outside one exercise or Session. It is not Evidence, a Generated Resource, or proof of mastery. Work inside or outside a Session without changing its checkpoint, Evidence, Assessments, Progress, Gaps, Frontier, attempts, or Review dates.

For a system-initiated change, propose the concrete addition or correction conversationally and wait for explicit user confirmation before any Reference operation that could write, including lazy initialization. A proposal alone creates no files or persistent proposal entity. An explicit user request such as “Добавь это в справочник” already authorizes the change; do not ask for a second confirmation. Read-only inspection of existing files may prepare a proposal without creating Reference.

For a requested lookup or authorized edit, use `python3 scripts/learning.py list-reference` and `read-reference` to inspect `reference/index.md` and only relevant files. These operations initialize a missing Reference with a minimal index. Find the relevant material semantically. Prefer improving an existing section over duplicating it; create thematic files only when useful, with filenames suited to the actual course.

Distill concise, self-contained Markdown with headings, paragraphs, examples, tables, or mathematical notation as appropriate. Formulas may explain variables and units. Do not require entry IDs, frontmatter, tags, types, or a fixed layout. Do not copy entire Generated Resources or external articles. You may clarify, correct, merge, split, restructure, or shorten existing content; Git provides history.

For an update, first save the exact current content to a staging file outside `reference/` and inspect that snapshot. Prepare the replacement from this snapshot in a separate file, then persist it through the CLI. For a new thematic file, stage its complete Markdown and use create:

```bash
python3 scripts/learning.py create-reference reference/<topic>.md <replacement.md>
python3 scripts/learning.py read-reference reference/<topic>.md > <expected.md>
python3 scripts/learning.py update-reference reference/<topic>.md <replacement.md> --expected <expected.md>
python3 scripts/learning.py validate reference
```

Keep the exact previously read content in the expected file, separate from the replacement. If the content changed, reread it and incorporate the current text before retrying. Empty writes, overwrites through create, unsafe paths, and symlinks are rejected. When creating a thematic file, also update `reference/index.md` through `update-reference` to keep navigation readable; code does not generate index links or parse Markdown. If the index update fails, retain the thematic file, report it, and retry the index update using fresh content.

There are no CLI operations for deletion or renaming. In particular, do not delete or rename files referenced by historical Evidence. Existing content may be edited. Do not add a separate history, structured entry database, hashes, automatic backlinks, or mastery tracking.

Reference is freely available in Study, Discussion, and Remediation. For independent checks, default to closed Reference for recall and understanding, open Reference for application; allow explicit task-specific overrides. State the policy before the task, separate mixed-policy parts, and retain `reference: [{dimension: ..., allowed: ...}]` in checkpoint and subsequent Evidence for assessed dimensions only. Trust the learner: do not ask whether they used Reference, collect file provenance, or police compliance. Reference permission is context for Assessment and never mechanically changes a grade.
