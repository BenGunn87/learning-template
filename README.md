# Learning Template

Git-based template for learning one large topic through short, adaptive study sessions. The repository is the source of truth: Codex makes semantic learning decisions, while Python scripts validate and render deterministic state.

Stage 1 implements repository bootstrap and `init`. Stage 2 adds the first complete study Session: Unit materialization, Resource-guided study, Active Recall, Practice, immutable Evidence, Assessment, derived Progress, and repository-backed status. Reviews remain intentionally out of scope.

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
python3 scripts/learning.py status
```

The `run-session` Skill normally orchestrates the internal Stage 2 commands, so users only need to say, for example:

```text
У меня есть 25 минут.
```

The deterministic write operations are also available for Skills and development:

```bash
python3 scripts/learning.py create-session --unit <unit-id> --minutes 25
python3 scripts/learning.py create-unit <unit.yaml>
python3 scripts/learning.py create-evidence <evidence.yaml>
python3 scripts/learning.py create-assessment <assessment.yaml>
python3 scripts/learning.py update-progress
python3 scripts/learning.py complete-session <session-id> --evidence <evidence-id>
```

`state` reports `uninitialized`, `partial`, or `initialized`. Validation is read-only. Primary Events are create-only, Progress is rebuildable, and a repeated `init` must not overwrite an initialized topic or existing Primary Data.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

See `docs/SPEC.md` for the full MVP architecture, `docs/PLAN_STAGE_1.md` for the Stage 1 boundary, and `docs/PLAN_STAGE_2.md` for the first complete Session.
