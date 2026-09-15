#!/usr/bin/env python3
"""Command line interface for deterministic learning repository operations."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHONS = (SCRIPT_ROOT / ".venv/bin/python", SCRIPT_ROOT / ".venv/Scripts/python.exe")
for venv_python in VENV_PYTHONS:
    if venv_python.is_file() and Path(sys.executable).absolute() != venv_python.absolute():
        os.execv(str(venv_python), [str(venv_python), *sys.argv])

try:
    from learning_core import Repository
    from learning_core.yaml_io import YamlFileError, dump_yaml, load_yaml
except ModuleNotFoundError as exc:
    if exc.name in {"yaml", "jsonschema"}:
        print(
            "Missing Python dependencies. Run: python3 -m venv .venv && "
            ".venv/bin/python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Validate and inspect a learning repository")
    result.add_argument("--root", type=Path, default=SCRIPT_ROOT, help="repository root (default: directory containing this script)")
    subcommands = result.add_subparsers(dest="command", required=True)
    subcommands.add_parser("state", help="detect uninitialized, partial, or initialized state")
    validate = subcommands.add_parser("validate", help="validate repository data")
    validate.add_argument(
        "target",
        nargs="?",
        choices=("repository", "learning", "context", "graph", "frontier", "settings", "unit", "session", "evidence", "assessment", "progress"),
        default="repository",
    )
    validate.add_argument("identifier", nargs="?", help="id required for Unit, Session, Evidence, or Assessment")
    subcommands.add_parser("candidates", help="render technical graph candidates as YAML")
    session_candidates = subcommands.add_parser("session-candidates", help="rank Frontier Units for a time budget")
    session_candidates.add_argument("--minutes", type=int, required=True)
    session_candidates.add_argument("--on-date", help="ISO date used to detect due Reviews")
    plan_session = subcommands.add_parser("plan-session-candidates", help="plan study, practice, and due Review candidates")
    plan_session.add_argument("--minutes", type=int, required=True)
    plan_session.add_argument("--on-date", help="ISO date used to detect due Reviews")
    subcommands.add_parser("get-practice-units", help="list Units that need targeted Practice")
    due_reviews = subcommands.add_parser("get-due-reviews", help="list due Reviews")
    due_reviews.add_argument("--on-date", help="ISO date; defaults to local current date")
    review_outcome = subcommands.add_parser("calculate-review-outcome", help="derive one Review outcome from mastery grades")
    for dimension in ("recall", "understanding", "application"):
        review_outcome.add_argument(f"--{dimension}", required=True, choices=("failed", "hard", "good", "easy"))
    next_review = subcommands.add_parser("calculate-next-review", help="calculate a deterministic Review date and interval")
    next_review.add_argument("--outcome", required=True, choices=("failed", "hard", "good", "easy"))
    next_review.add_argument("--on-date", help="ISO date; defaults to local current date")
    next_review.add_argument("--previous-interval", type=int)
    next_review.add_argument("--repetitions", type=int)
    create_session = subcommands.add_parser("create-session", help="create one active Session")
    create_session.add_argument("--unit")
    create_session.add_argument("--action", action="append", help="planned action as study:unit, practice:unit, or review:unit")
    create_session.add_argument("--minutes", type=int, required=True)
    create_session.add_argument("--started-at", help="RFC 3339 timestamp; defaults to local current time")
    create_unit = subcommands.add_parser("create-unit", help="validate and safely create an initialized Unit")
    create_unit.add_argument("input", type=Path, help="YAML document to create")
    create_evidence = subcommands.add_parser("create-evidence", help="validate and append immutable Evidence")
    create_evidence.add_argument("input", type=Path, help="YAML document to create")
    create_assessment = subcommands.add_parser("create-assessment", help="validate and append an Assessment")
    create_assessment.add_argument("input", type=Path, help="YAML document to create")
    subcommands.add_parser("update-progress", help="rebuild derived Progress from Evidence and Assessments")
    complete_session = subcommands.add_parser("complete-session", help="complete an active Session after Progress update")
    complete_session.add_argument("session_id")
    complete_session.add_argument("--evidence", action="append", required=True, dest="evidence_ids")
    complete_session.add_argument("--completed-at", help="RFC 3339 timestamp; defaults to local current time")
    status = subcommands.add_parser("status", help="render the current learning status")
    status.add_argument("--on-date", help="ISO date used to display due Reviews")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = Repository(args.root)
    try:
        if args.command == "state":
            print(repository.state_as_yaml(), end="")
            return 0
        if args.command == "status":
            print(repository.render_status(args.on_date))
            return 0
        if args.command == "candidates":
            print(dump_yaml(repository.frontier_candidates()), end="")
            return 0
        if args.command == "session-candidates":
            print(dump_yaml(repository.session_candidates(args.minutes, args.on_date)), end="")
            return 0
        if args.command == "plan-session-candidates":
            print(dump_yaml(repository.plan_session_candidates(args.minutes, args.on_date)), end="")
            return 0
        if args.command == "get-practice-units":
            print(dump_yaml({"practice_units": repository.get_practice_units()}), end="")
            return 0
        if args.command == "get-due-reviews":
            print(dump_yaml({"due_reviews": repository.get_due_reviews(args.on_date)}), end="")
            return 0
        if args.command == "calculate-review-outcome":
            result = {dimension: getattr(args, dimension) for dimension in ("recall", "understanding", "application")}
            print(dump_yaml({"review_outcome": repository.calculate_review_outcome(result)}), end="")
            return 0
        if args.command == "calculate-next-review":
            if (args.previous_interval is None) != (args.repetitions is None):
                raise ValueError("previous interval and repetitions must be provided together")
            previous = None
            if args.previous_interval is not None:
                previous = {"interval_days": args.previous_interval, "repetitions": args.repetitions}
            print(dump_yaml({"review": repository.calculate_next_review(args.outcome, args.on_date, previous)}), end="")
            return 0
        if args.command == "create-session":
            actions = None
            if args.action:
                actions = []
                for value in args.action:
                    action_type, separator, unit = value.partition(":")
                    if not separator or action_type not in {"study", "practice", "review"} or not unit:
                        raise ValueError(f"invalid action: {value}")
                    actions.append({"type": action_type, "unit": unit})
            path, data = repository.create_session(args.unit, args.minutes, args.started_at, actions)
            print(dump_yaml({"created": str(path.relative_to(repository.root)), "session": data}), end="")
            return 0
        if args.command == "create-unit":
            path, outcome = repository.create_unit(load_yaml(args.input))
            print(dump_yaml({outcome: str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "create-evidence":
            path = repository.create_evidence(load_yaml(args.input))
            print(dump_yaml({"created": str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "create-assessment":
            path = repository.create_assessment(load_yaml(args.input))
            print(dump_yaml({"created": str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "update-progress":
            print(dump_yaml(repository.rebuild_progress()), end="")
            return 0
        if args.command == "complete-session":
            path, data, outcome = repository.complete_session(args.session_id, args.evidence_ids, args.completed_at)
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "session": data}), end="")
            return 0

        if args.target == "repository":
            if args.identifier:
                raise ValueError("repository validation does not accept an identifier")
            issues = repository.validate_repository()
        elif args.target == "graph":
            issues = repository.validate_graph()
        elif args.target == "frontier":
            issues = repository.validate_frontier()
        elif args.target == "unit":
            if not args.identifier:
                raise ValueError("Unit validation requires an id")
            issues = repository.validate_unit(args.identifier)
        elif args.target == "session":
            if not args.identifier:
                raise ValueError("Session validation requires an id")
            issues = repository.validate_session(args.identifier)
        elif args.target == "evidence":
            if not args.identifier:
                raise ValueError("Evidence validation requires an id")
            issues = repository.validate_evidence(args.identifier)
        elif args.target == "assessment":
            if not args.identifier:
                raise ValueError("Assessment validation requires an id")
            issues = repository.validate_assessment(args.identifier)
        elif args.target == "progress":
            if args.identifier:
                raise ValueError("Progress validation does not accept an identifier")
            issues = repository.validate_progress()
        elif args.target == "settings":
            if args.identifier:
                raise ValueError("Settings validation does not accept an identifier")
            issues = repository._validate_settings()
        else:
            if args.identifier:
                raise ValueError(f"{args.target} validation does not accept an identifier")
            issues = repository.validate_document(args.target)
        if issues:
            print("Validation failed:", file=sys.stderr)
            for issue in issues:
                print(f"- {issue.render()}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.target}")
        return 0
    except (ValueError, YamlFileError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
