#!/usr/bin/env python3
"""Minimal command line interface for deterministic Stage 1 operations."""

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
    from learning_core.yaml_io import YamlFileError, dump_yaml
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
    validate.add_argument("target", nargs="?", choices=("repository", "learning", "context", "graph", "frontier"), default="repository")
    subcommands.add_parser("candidates", help="render technical graph candidates as YAML")
    subcommands.add_parser("status", help="render the current learning status")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = Repository(args.root)
    try:
        if args.command == "state":
            print(repository.state_as_yaml(), end="")
            return 0
        if args.command == "status":
            print(repository.render_status())
            return 0
        if args.command == "candidates":
            print(dump_yaml(repository.frontier_candidates()), end="")
            return 0

        if args.target == "repository":
            issues = repository.validate_repository()
        elif args.target == "graph":
            issues = repository.validate_graph()
        elif args.target == "frontier":
            issues = repository.validate_frontier()
        else:
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
