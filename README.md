# Learning Template

Git-based template for learning one large topic through short, adaptive study sessions. The repository is the source of truth: an AI agent (Codex or Claude Code) makes semantic learning decisions, while Python scripts validate and render deterministic state.

The system supports topic initialization, complete study Sessions, gap-targeted Practice, and spaced Reviews. Durable checkpoints, pause/resume, crash recovery, and timed Session segments let a Unit continue across several visits. Persistent Gaps and user-declared Interests guide adaptive Frontier routing with explainable reasons. Study Modes use external, generated, or hybrid materials, with immutable generated Resources, multi-Resource Evidence, and compact Discussion summaries. Append-only Assessment reevaluation preserves historical interpretations, reconciles Gaps, and atomically rebuilds derived state. Unit mastery remains `learning`, `practice`, or `verified`; pausing never changes it.

## Setup

Create a repository from this template, then install the two Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

When using the virtual environment, either activate it or replace `python3` in the commands below with `.venv/bin/python`.

## Initialize a topic

Open the repository in Codex or Claude Code and say, for example:

```text
Хочу изучать System Design.
```

You can also explicitly invoke the Skill: `$topic-onboarding` in Codex or `/topic-onboarding` in Claude Code. The agent will conduct a short onboarding and diagnostic, then generate:

- `learning.yaml` — repository and topic metadata;
- `config/context.yaml` — goal, constraints, preferences, and diagnostic hypotheses;
- `map/graph.yaml` — the initial Knowledge Graph;
- `map/frontier.yaml` — 5–10 planning-only Skeleton Units.

## Agent support

Both agents share one set of instructions and Skills:

- `AGENTS.md` — repository rules for any agent; Codex reads it directly.
- `CLAUDE.md` — imports `AGENTS.md` and adds Claude Code notes.
- `.agents/skills/` — the single source of Repository Skills, discovered by Codex.
- `.claude/skills` — a symlink to `../.agents/skills`, so Claude Code discovers the same Skills. Edit Skills only in `.agents/skills/`.
- `.claude/settings.json` — pre-approves `scripts/learning.py` and the test runner in Claude Code; personal overrides go to the ignored `.claude/settings.local.json`.

On Windows, clone with symlinks enabled (`git clone -c core.symlinks=true ...`, which requires Developer Mode or administrator rights). Otherwise replace the link with a copy (`rm .claude/skills && cp -R .agents/skills .claude/skills`) and repeat the copy after every Skill change; `tests/test_agent_compat.py` detects a stale copy.

## Deterministic commands

```bash
python3 scripts/learning.py state
python3 scripts/learning.py validate
python3 scripts/learning.py validate graph
python3 scripts/learning.py validate resource <resource-id>
python3 scripts/learning.py candidates
python3 scripts/learning.py session-candidates --minutes 25
python3 scripts/learning.py get-practice-units
python3 scripts/learning.py get-due-reviews
python3 scripts/learning.py list-gaps
python3 scripts/learning.py list-interests
python3 scripts/learning.py detect-weak-signals
python3 scripts/learning.py active-assessment <evidence-id>
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
python3 scripts/learning.py create-generated-resource <resource.md>
python3 scripts/learning.py create-assessment <assessment.yaml>
python3 scripts/learning.py reevaluate-assessment <reevaluation.yaml>
python3 scripts/learning.py create-interest <interest.yaml>
python3 scripts/learning.py update-interest <interest-id> --status satisfied
python3 scripts/learning.py expand-graph <graph-delta.yaml>
python3 scripts/learning.py expand-graph <structural-graph-delta.yaml> --allow-unanchored
python3 scripts/learning.py update-progress
python3 scripts/learning.py rebuild-frontier
python3 scripts/learning.py complete-session <session-id> --evidence <evidence-id>
```

`state` reports `uninitialized`, `partial`, or `initialized`. Validation is read-only. Evidence and generated Resources are immutable; Assessment Events are append-only and may form a validated linear reevaluation chain. Gaps and Interests preserve lifecycle history; Session checkpoint state is atomically replaceable; Progress and Frontier remain derived. Automatic `expand-graph` deltas must connect new nodes to the existing Graph; `--allow-unanchored` is reserved for an explicitly approved structural delta. A repeated `init` must not overwrite an initialized topic or existing Primary Data. One repository may contain at most one Session whose status is `active` or `paused`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

See `docs/SPEC.md` for the architecture and product requirements.

## Learning core

`scripts/learning.py` is the CLI entry point. `scripts/learning_core/` contains:

| Module | Responsibility |
| --- | --- |
| `repository.py` | Repository bootstrap, state detection, shared validation, candidates, and status |
| `learning_cycle.py` | Unit, Evidence, Assessment, and Session records; learning cycle transitions |
| `reviews.py` | Targeted Practice and spaced Review scheduling |
| `sessions.py` | Checkpoints, pause/resume, recovery, and timed segments |
| `routing.py` | Gaps, Interests, graph expansion, and adaptive routing |
| `study.py` | Study Modes, Resources, and Discussion state |
| `reevaluation.py` | Assessment chains, Gap reconciliation, and atomic derived state rebuilds |

The `Repository` class composes the responsibility mixins through their inheritance chain. `issues.py` and `yaml_io.py` provide validation messages and safe YAML persistence.
