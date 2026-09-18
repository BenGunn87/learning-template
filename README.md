# Learning Template

Git-based template for learning one large topic through short, adaptive study sessions. The repository is the source of truth: Codex makes semantic learning decisions, while Python scripts validate and render deterministic state.

Stage 1 implements repository bootstrap and `init`. Stage 2 adds the first complete study Session. Stage 3 adds gap-targeted Practice and spaced Reviews. Stage 4 adds durable checkpoints, pause/resume and crash recovery, timed Session segments, and partially planned Units. Stage 5 adds persistent Gaps, user-declared Interests, adaptive Frontier routing, and explainable routing reasons. Unit mastery remains `learning`, `practice`, or `verified`; pausing never changes it.

## Setup

Create a repository from this template, then install the two Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

When using the virtual environment, either activate it or replace `python3` in the commands below with `.venv/bin/python`.

## Initialize a topic

Open the repository in Codex and say, for example:

```text
Хочу изучать System Design.
```

You can also explicitly invoke `$topic-onboarding`. Codex will conduct a short onboarding and diagnostic, then generate:

- `learning.yaml` — repository and topic metadata;
- `config/context.yaml` — goal, constraints, preferences, and diagnostic hypotheses;
- `map/graph.yaml` — the initial Knowledge Graph;
- `map/frontier.yaml` — 5–10 planning-only Skeleton Units.

Repository Skills live in `.agents/skills/` so Codex can discover them automatically.

## Deterministic commands

```bash
python3 scripts/learning.py state
python3 scripts/learning.py validate
python3 scripts/learning.py validate graph
python3 scripts/learning.py candidates
python3 scripts/learning.py session-candidates --minutes 25
python3 scripts/learning.py get-practice-units
python3 scripts/learning.py get-due-reviews
python3 scripts/learning.py list-gaps
python3 scripts/learning.py list-interests
python3 scripts/learning.py detect-weak-signals
python3 scripts/learning.py update-routing-metadata
python3 scripts/learning.py plan-session-candidates --minutes 25
python3 scripts/learning.py detect-resumable-session
python3 scripts/learning.py status
```

The `run-session` Skill normally orchestrates the internal commands, so users only need to say, for example:

```text
У меня есть 25 минут.
```

The deterministic write operations are also available for Skills and development:

```bash
python3 scripts/learning.py create-session --unit <unit-id> --minutes 25
python3 scripts/learning.py create-session --minutes 25 --action review:<unit-id> --action study:<unit-id>
python3 scripts/learning.py update-checkpoint <session-id> <checkpoint.yaml>
python3 scripts/learning.py pause-session <session-id>
python3 scripts/learning.py resume-session <session-id> --minutes 20
python3 scripts/learning.py recover-session <session-id> --minutes 20 [--checkpoint <reconstructed-checkpoint.yaml>]
python3 scripts/learning.py calculate-active-minutes <session-id>
python3 scripts/learning.py create-unit <unit.yaml>
python3 scripts/learning.py create-evidence <evidence.yaml>
python3 scripts/learning.py create-assessment <assessment.yaml>
python3 scripts/learning.py create-interest <interest.yaml>
python3 scripts/learning.py update-interest <interest-id> --status satisfied
python3 scripts/learning.py expand-graph <graph-delta.yaml>
python3 scripts/learning.py expand-graph <structural-graph-delta.yaml> --allow-unanchored
python3 scripts/learning.py update-progress
python3 scripts/learning.py complete-session <session-id> --evidence <evidence-id>
```

`state` reports `uninitialized`, `partial`, or `initialized`. Validation is read-only. Evidence and Assessment Events are create-only; Gaps and Interests preserve lifecycle history; Session checkpoint state is atomically replaceable; Progress and Frontier remain derived. Automatic `expand-graph` deltas must connect new nodes to the existing Graph; `--allow-unanchored` is reserved for an explicitly approved structural delta. A repeated `init` must not overwrite an initialized topic or existing Primary Data. One repository may contain at most one Session whose status is `active` or `paused`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

See `docs/SPEC.md` for the full MVP architecture and `docs/PLAN_STAGE_*.md` for the implementation stages.
