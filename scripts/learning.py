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
        choices=("repository", "learning", "context", "graph", "frontier", "settings", "unit", "session", "evidence", "assessment", "progress", "gap", "interest", "resource"),
        default="repository",
    )
    validate.add_argument("identifier", nargs="?", help="id required for entity-specific validation targets")
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
    subcommands.add_parser("detect-resumable-session", help="detect the one active or paused Session")
    update_checkpoint = subcommands.add_parser("update-checkpoint", help="persist minimal resumable Session state")
    update_checkpoint.add_argument("session_id")
    update_checkpoint.add_argument("input", type=Path, help="checkpoint YAML document")
    update_checkpoint.add_argument("--updated-at", help="RFC 3339 timestamp; overrides checkpoint.updated_at")
    update_checkpoint.add_argument(
        "--action-status",
        choices=("in_progress", "completed"),
        default="in_progress",
        help="execution state for the checkpoint action",
    )
    pause_session = subcommands.add_parser("pause-session", help="checkpoint and pause the active Session")
    pause_session.add_argument("session_id")
    pause_session.add_argument("--checkpoint", type=Path, help="checkpoint YAML; latest saved checkpoint is used when omitted")
    pause_session.add_argument("--paused-at", help="RFC 3339 timestamp; defaults to local current time")
    resume_session = subcommands.add_parser("resume-session", help="resume the paused logical Session with a new segment")
    resume_session.add_argument("session_id", nargs="?")
    resume_session.add_argument("--minutes", type=int, required=True)
    resume_session.add_argument("--resumed-at", help="RFC 3339 timestamp; defaults to local current time")
    recover_session = subcommands.add_parser("recover-session", help="recover a potentially stale active Session")
    recover_session.add_argument("session_id", nargs="?")
    recover_session.add_argument("--minutes", type=int, required=True)
    recover_session.add_argument("--recovered-at", help="RFC 3339 timestamp; defaults to local current time")
    recover_session.add_argument(
        "--checkpoint",
        type=Path,
        help="reconstructed semantic checkpoint YAML, only when no saved checkpoint exists",
    )
    active_minutes = subcommands.add_parser("calculate-active-minutes", help="sum closed Session segment durations")
    active_minutes.add_argument("session_id")
    create_unit = subcommands.add_parser("create-unit", help="validate and safely create an initialized Unit")
    create_unit.add_argument("input", type=Path, help="YAML document to create")
    create_evidence = subcommands.add_parser("create-evidence", help="validate and append immutable Evidence")
    create_evidence.add_argument("input", type=Path, help="YAML document to create")
    create_resource = subcommands.add_parser(
        "create-generated-resource",
        help="validate and persist an immutable generated Markdown Resource",
    )
    create_resource.add_argument("input", type=Path, help="Markdown document with YAML frontmatter")
    create_assessment = subcommands.add_parser("create-assessment", help="validate and append an Assessment")
    create_assessment.add_argument("input", type=Path, help="YAML document to create")
    list_gaps = subcommands.add_parser("list-gaps", help="list persistent learning Gaps")
    list_gaps.add_argument("--status", choices=("detected", "confirmed", "resolved"))
    create_gap = subcommands.add_parser("create-gap", help="create a semantically reviewed Gap")
    create_gap.add_argument("input", type=Path, help="Gap YAML document")
    gap_impact = subcommands.add_parser("update-gap-impact", help="set semantic Gap routing priority within prerequisite constraints")
    gap_impact.add_argument("gap_id")
    gap_impact.add_argument("--impact", required=True, choices=("blocking", "important", "minor"))
    weak_signals = subcommands.add_parser("detect-weak-signals", help="list weak signals explicitly attributed by Assessment.evaluated")
    weak_signals.add_argument("--evidence")
    update_gaps = subcommands.add_parser("update-gaps", help="apply one Assessment to Gap lifecycle state")
    update_gaps.add_argument("--evidence", required=True)
    update_gaps.add_argument(
        "--node",
        action="append",
        dest="nodes",
        help="optional filter; cannot add a node absent from Assessment.evaluated",
    )
    update_gaps.add_argument(
        "--dimension",
        choices=("recall", "understanding", "application"),
        help="optional filter; cannot add a dimension absent from Assessment.evaluated",
    )
    list_interests = subcommands.add_parser("list-interests", help="list user-declared Interests")
    list_interests.add_argument("--status", choices=("pending", "active", "satisfied", "dismissed"))
    create_interest = subcommands.add_parser("create-interest", help="create a persistent user Interest")
    create_interest.add_argument("input", type=Path, help="Interest YAML document")
    update_interest = subcommands.add_parser("update-interest", help="advance an Interest lifecycle status")
    update_interest.add_argument("interest_id")
    update_interest.add_argument("--status", required=True, choices=("active", "satisfied", "dismissed"))
    update_interest.add_argument("--at", help="RFC 3339 transition timestamp")
    related = subcommands.add_parser("inspect-related-nodes", help="inspect graph edges and adaptive routing links")
    related.add_argument("node")
    impact = subcommands.add_parser("prerequisite-impact", help="compute dependent Frontier Units for a graph node")
    impact.add_argument("node")
    expand_graph = subcommands.add_parser("expand-graph", help="apply a validated additive graph delta")
    expand_graph.add_argument("input", type=Path, help="YAML with nodes and edges arrays")
    expand_graph.add_argument(
        "--allow-unanchored",
        action="store_true",
        help="apply an explicitly approved structural delta that creates a new root branch",
    )
    routing = subcommands.add_parser("update-routing-metadata", help="refresh Gap impact and activate serviced Interests")
    routing.add_argument("--at", help="RFC 3339 update timestamp")
    subcommands.add_parser("update-progress", help="rebuild derived Progress from Evidence and Assessments")
    complete_session = subcommands.add_parser("complete-session", help="complete an active Session after Progress update")
    complete_session.add_argument("session_id")
    complete_session.add_argument("--evidence", action="append", default=[], dest="evidence_ids")
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
        if args.command == "detect-resumable-session":
            print(dump_yaml(repository.detect_resumable_session()), end="")
            return 0
        if args.command == "update-checkpoint":
            path, data, outcome = repository.update_checkpoint(
                args.session_id,
                load_yaml(args.input),
                args.updated_at,
                args.action_status,
            )
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "session": data}), end="")
            return 0
        if args.command == "pause-session":
            checkpoint = load_yaml(args.checkpoint) if args.checkpoint else None
            path, data, outcome = repository.pause_session(args.session_id, checkpoint, args.paused_at)
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "session": data}), end="")
            return 0
        if args.command == "resume-session":
            path, data, outcome = repository.resume_session(args.session_id, args.minutes, args.resumed_at)
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "session": data}), end="")
            return 0
        if args.command == "recover-session":
            checkpoint = load_yaml(args.checkpoint) if args.checkpoint else None
            path, data, outcome = repository.recover_session(
                args.session_id,
                args.minutes,
                args.recovered_at,
                checkpoint,
            )
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "session": data}), end="")
            return 0
        if args.command == "calculate-active-minutes":
            print(dump_yaml({"session_id": args.session_id, "active_minutes": repository.calculate_active_minutes(args.session_id)}), end="")
            return 0
        if args.command == "create-unit":
            path, outcome = repository.create_unit(load_yaml(args.input))
            print(dump_yaml({outcome: str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "create-evidence":
            path = repository.create_evidence(load_yaml(args.input))
            print(dump_yaml({"created": str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "create-generated-resource":
            try:
                content = args.input.read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"cannot read {args.input}: {exc}") from exc
            path, outcome = repository.create_generated_resource(content)
            print(dump_yaml({outcome: str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "create-assessment":
            path = repository.create_assessment(load_yaml(args.input))
            print(dump_yaml({"created": str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "list-gaps":
            print(dump_yaml({"gaps": repository.list_gaps(args.status)}), end="")
            return 0
        if args.command == "create-gap":
            path, outcome = repository.create_gap(load_yaml(args.input))
            print(dump_yaml({outcome: str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "update-gap-impact":
            path, data, outcome = repository.update_gap_impact(args.gap_id, args.impact)
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "gap": data}), end="")
            return 0
        if args.command == "detect-weak-signals":
            print(dump_yaml({"weak_signals": repository.detect_weak_signals(args.evidence)}), end="")
            return 0
        if args.command == "update-gaps":
            print(dump_yaml({"changes": repository.update_gaps_for_evidence(args.evidence, args.nodes, args.dimension)}), end="")
            return 0
        if args.command == "list-interests":
            print(dump_yaml({"interests": repository.list_interests(args.status)}), end="")
            return 0
        if args.command == "create-interest":
            path, outcome = repository.create_interest(load_yaml(args.input))
            print(dump_yaml({outcome: str(path.relative_to(repository.root))}), end="")
            return 0
        if args.command == "update-interest":
            path, data, outcome = repository.update_interest(args.interest_id, args.status, args.at)
            print(dump_yaml({outcome: str(path.relative_to(repository.root)), "interest": data}), end="")
            return 0
        if args.command == "inspect-related-nodes":
            print(dump_yaml(repository.inspect_related_nodes(args.node)), end="")
            return 0
        if args.command == "prerequisite-impact":
            print(dump_yaml(repository.prerequisite_impact(args.node)), end="")
            return 0
        if args.command == "expand-graph":
            print(dump_yaml(repository.expand_graph(load_yaml(args.input), allow_unanchored=args.allow_unanchored)), end="")
            return 0
        if args.command == "update-routing-metadata":
            print(dump_yaml(repository.update_routing_metadata(args.at)), end="")
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
        elif args.target == "gap":
            if not args.identifier:
                raise ValueError("Gap validation requires an id")
            issues = repository.validate_gap(args.identifier)
        elif args.target == "interest":
            if not args.identifier:
                raise ValueError("Interest validation requires an id")
            issues = repository.validate_interest(args.identifier)
        elif args.target == "resource":
            if not args.identifier:
                raise ValueError("Resource validation requires an id")
            issues = repository.validate_generated_resource(args.identifier)
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
