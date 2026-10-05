# Agent instructions

This repository is a Git-based learning system for one large topic. Any AI agent (Codex, Claude Code) working here follows the same rules. The full architecture is in `docs/SPEC.md`.

## Core rules

- The repository is the source of truth. Chat memory is never state: re-read files and run `python3 scripts/learning.py state` / `detect-resumable-session` instead of relying on earlier conversation.
- The agent makes semantic decisions (onboarding, diagnostic, Knowledge Graph, Units, materials, questions, Assessments, Gaps, routing suggestions).
- Scripts own deterministic state. Never hand-compute or hand-edit what `scripts/learning.py` can compute: validation, prerequisites, Session state, Review intervals, Progress, Frontier, indexes. Write Primary Data only through its `create-*` / `update-*` commands.
- Evidence and generated Resources are immutable. Assessments are append-only; revise one only with `reevaluate-assessment`. Progress and Frontier are derived and are rebuilt, not edited.
- At most one Session may be `active` or `paused`. Pausing never changes Unit mastery.
- Load only the local context a step needs; do not read the whole history by default.

## Skills

Skills live in `.agents/skills/<name>/SKILL.md` (Claude Code sees the same files through the `.claude/skills` symlink). Pick the Skill by the user's intent:

| User intent | Skill |
| --- | --- |
| Wants to study a new topic, or asks for `init` in an uninitialized repository | `topic-onboarding` |
| Has time to study ("У меня есть 25 минут") or asks to study | `run-session` |
| Wants to stop or continue later | `pause-session` |
| Returns to a paused or interrupted Session | `resume-session` |
| Asks about progress or status | `status` |
| Mentions a topic to study later or deeper | `capture-interest` |

The other Skills (`diagnostic`, `build-learning-map`, `build-frontier`, `initialize-unit`, `run-study`, `find-resources`, `run-practice`, `run-review`, `assess-answer`) are loaded by these entry points; follow their references rather than skipping steps.

## Development

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Keep current product requirements in `docs/SPEC.md` and usage instructions in `README.md`; update both when behavior changes. Completed development plans and fix instructions belong in Git history.
