# Learning Template

Git-based template for learning one large topic through short, adaptive study sessions. The repository is the source of truth: Codex makes semantic learning decisions, while Python scripts validate and render deterministic state.

Stage 1 implements repository bootstrap and `init`. Full study Sessions, Resources, Evidence, Assessment, Progress, and Reviews are intentionally not implemented yet.

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
python3 scripts/learning.py status
```

`state` reports `uninitialized`, `partial`, or `initialized`. Validation is read-only. A repeated `init` must not overwrite an initialized topic or existing Primary Data.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

See `docs/SPEC.md` for the full MVP architecture and `docs/PLAN.md` for the Stage 1 boundary.

