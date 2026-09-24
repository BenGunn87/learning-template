"""Deterministic Stage 2 validation and repository state transitions."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .issues import Issue
from .yaml_io import YamlFileError, create_yaml, load_yaml, replace_yaml


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SESSION_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{3})$")


class Stage2RepositoryMixin:
    """Mixin kept separate so Stage 1 repository code remains easy to inspect."""

    root: Path

    def path(self, relative: Path | str) -> Path:  # pragma: no cover - supplied by Repository
        raise NotImplementedError

    def read(self, name: str) -> Any:  # pragma: no cover - supplied by Repository
        raise NotImplementedError

    def state(self) -> tuple[str, list[Issue]]:  # pragma: no cover - supplied by Repository
        raise NotImplementedError

    def validate_schema(self, name: str, data: Any, relative: str) -> list[Issue]:  # pragma: no cover
        raise NotImplementedError

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    @staticmethod
    def _raise_issues(issues: Iterable[Issue]) -> None:
        rendered = [issue.render() for issue in issues]
        if rendered:
            raise ValueError("\n".join(rendered))

    def _read_files(self, directory: str) -> tuple[list[tuple[Path, Any]], list[Issue]]:
        documents: list[tuple[Path, Any]] = []
        issues: list[Issue] = []
        base = self.path(directory)
        if not base.is_dir():
            return documents, issues
        for path in sorted(base.rglob("*.yaml")):
            try:
                documents.append((path, load_yaml(path)))
            except YamlFileError as exc:
                issues.append(Issue(self._relative(path), str(exc)))
        return documents, issues

    def _find_by_id(self, directory: str, document_id: str) -> list[tuple[Path, Any]]:
        documents, _ = self._read_files(directory)
        return [
            (path, data)
            for path, data in documents
            if isinstance(data, dict) and data.get("id") == document_id
        ]

    def _known_unit_ids(self) -> set[str]:
        known: set[str] = set()
        try:
            frontier = self.read("frontier")
            if isinstance(frontier, dict):
                known.update(
                    unit["id"]
                    for unit in frontier.get("units", [])
                    if isinstance(unit, dict) and isinstance(unit.get("id"), str)
                )
        except YamlFileError:
            pass
        units, _ = self._read_files("units")
        known.update(
            data["id"]
            for _, data in units
            if isinstance(data, dict) and isinstance(data.get("id"), str)
        )
        return known

    def read_progress(self) -> dict[str, Any]:
        path = self.path("progress/units.yaml")
        if not path.exists():
            return {}
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise YamlFileError(f"expected a mapping in {path}")
        return data

    def validate_unit(self, unit: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(unit, str):
            path = self.path(f"units/{unit}.yaml")
            relative = self._relative(path)
            try:
                unit = load_yaml(path)
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]
        relative = relative or f"units/{unit.get('id', '<unknown>')}.yaml" if isinstance(unit, dict) else "units/<unknown>.yaml"
        issues = self.validate_schema("unit", unit, relative)
        if not isinstance(unit, dict):
            return issues

        unit_id = unit.get("id")
        if isinstance(unit_id, str) and relative.startswith("units/") and Path(relative).name != f"{unit_id}.yaml":
            issues.append(Issue(relative, "file name must match Unit id"))
        try:
            graph = self.read("graph")
            graph_ids = {
                node.get("id")
                for node in graph.get("nodes", [])
                if isinstance(node, dict) and isinstance(node.get("id"), str)
            }
            for index, node_id in enumerate(unit.get("nodes", [])):
                if node_id not in graph_ids:
                    issues.append(Issue(relative, f"unit references unknown node: {node_id}", f"$.nodes[{index}]"))
        except (YamlFileError, AttributeError):
            pass
        return issues

    def validate_session(self, session: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(session, str):
            path = self.path(f"sessions/{session}.yaml")
            relative = self._relative(path)
            try:
                session = load_yaml(path)
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]
        relative = relative or f"sessions/{session.get('id', '<unknown>')}.yaml" if isinstance(session, dict) else "sessions/<unknown>.yaml"
        issues = self.validate_schema("session", session, relative)
        if not isinstance(session, dict):
            return issues

        session_id = session.get("id")
        if isinstance(session_id, str) and relative.startswith("sessions/") and Path(relative).name != f"{session_id}.yaml":
            issues.append(Issue(relative, "file name must match Session id"))
        planned = session.get("plan", {}).get("unit") if isinstance(session.get("plan"), dict) else None
        if isinstance(planned, str) and planned not in self._known_unit_ids():
            issues.append(Issue(relative, f"session references unknown planned Unit: {planned}", "$.plan.unit"))
        for index, evidence_id in enumerate(session.get("evidence", [])):
            matches = self._find_by_id("evidence", evidence_id)
            if not matches:
                issues.append(Issue(relative, f"session references unknown Evidence: {evidence_id}", f"$.evidence[{index}]"))
            elif len(matches) == 1 and isinstance(matches[0][1], dict) and matches[0][1].get("session") != session_id:
                issues.append(Issue(relative, f"Evidence belongs to another Session: {evidence_id}", f"$.evidence[{index}]"))
        return issues

    def validate_evidence(self, evidence: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(evidence, str):
            matches = self._find_by_id("evidence", evidence)
            if not matches:
                return [Issue("evidence", f"unknown Evidence: {evidence}")]
            if len(matches) > 1:
                return [Issue("evidence", f"duplicate Evidence id: {evidence}")]
            path, evidence = matches[0]
            relative = self._relative(path)
        relative = relative or "evidence/<unknown>.yaml"
        issues = self.validate_schema("evidence", evidence, relative)
        if not isinstance(evidence, dict):
            return issues

        evidence_id = evidence.get("id")
        unit_id = evidence.get("unit")
        session_id = evidence.get("session")
        expected = Path("evidence") / str(unit_id) / f"{evidence_id}.yaml"
        if relative.startswith("evidence/") and Path(relative) != expected:
            issues.append(Issue(relative, f"Evidence path must be {expected}"))
        if isinstance(unit_id, str) and not self.path(f"units/{unit_id}.yaml").is_file():
            issues.append(Issue(relative, f"evidence references unknown Unit: {unit_id}", "$.unit"))
        if isinstance(session_id, str) and not self.path(f"sessions/{session_id}.yaml").is_file():
            issues.append(Issue(relative, f"evidence references unknown Session: {session_id}", "$.session"))
        recall = evidence.get("recall")
        if isinstance(recall, dict):
            prompts, answers = recall.get("prompts"), recall.get("answers")
            if isinstance(prompts, list) and isinstance(answers, list) and len(prompts) != len(answers):
                issues.append(Issue(relative, "recall prompts and answers must have equal length", "$.recall"))
        return issues

    def validate_assessment(self, assessment: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(assessment, str):
            matches = self._find_by_id("assessments", assessment)
            if not matches:
                return [Issue("assessments", f"unknown Assessment: {assessment}")]
            if len(matches) > 1:
                return [Issue("assessments", f"duplicate Assessment id: {assessment}")]
            path, assessment = matches[0]
            relative = self._relative(path)
        relative = relative or "assessments/<unknown>/001.yaml"
        issues = self.validate_schema("assessment", assessment, relative)
        if not isinstance(assessment, dict):
            return issues

        evidence_id = assessment.get("evidence")
        expected_directory = Path("assessments") / str(evidence_id)
        relative_path = Path(relative)
        if relative.startswith("assessments/"):
            if assessment.get("type") == "reevaluation":
                if (
                    relative_path.parent != expected_directory
                    or not re.fullmatch(r"\d{3}\.yaml", relative_path.name)
                    or relative_path.name == "001.yaml"
                ):
                    issues.append(
                        Issue(
                            relative,
                            f"reevaluation Assessment path must be {expected_directory}/NNN.yaml after 001.yaml",
                        )
                    )
            else:
                expected = expected_directory / "001.yaml"
                if relative_path != expected:
                    issues.append(Issue(relative, f"initial Assessment path must be {expected}"))
        if isinstance(evidence_id, str) and not self._find_by_id("evidence", evidence_id):
            issues.append(Issue(relative, f"assessment references unknown Evidence: {evidence_id}", "$.evidence"))
        return issues

    def validate_progress(self, progress: Any | None = None) -> list[Issue]:
        relative = "progress/units.yaml"
        if progress is None:
            try:
                progress = self.read_progress()
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]
        issues = self.validate_schema("progress", progress, relative)
        if not isinstance(progress, dict):
            return issues
        initialized = {
            data.get("id")
            for _, data in self._read_files("units")[0]
            if isinstance(data, dict)
        }
        for unit_id, item in progress.items():
            if unit_id not in initialized:
                issues.append(Issue(relative, f"progress references unknown initialized Unit: {unit_id}", f"$.{unit_id}"))
            if not isinstance(item, dict):
                continue
            evidence_id = item.get("latest_evidence")
            assessment_id = item.get("latest_assessment")
            if isinstance(evidence_id, str) and not self._find_by_id("evidence", evidence_id):
                issues.append(Issue(relative, f"progress references unknown Evidence: {evidence_id}", f"$.{unit_id}.latest_evidence"))
            if isinstance(assessment_id, str) and not self._find_by_id("assessments", assessment_id):
                issues.append(Issue(relative, f"progress references unknown Assessment: {assessment_id}", f"$.{unit_id}.latest_assessment"))
        return issues

    def validate_stage2_repository(self) -> list[Issue]:
        issues: list[Issue] = []
        collections: dict[str, list[tuple[Path, Any]]] = {}
        for directory in ("units", "sessions", "evidence", "assessments"):
            documents, read_issues = self._read_files(directory)
            collections[directory] = documents
            issues.extend(read_issues)

        validators = {
            "units": self.validate_unit,
            "sessions": self.validate_session,
            "evidence": self.validate_evidence,
            "assessments": self.validate_assessment,
        }
        for directory, documents in collections.items():
            for path, data in documents:
                issues.extend(validators[directory](data, self._relative(path)))

        for directory in ("units", "sessions", "evidence", "assessments"):
            ids: dict[str, list[str]] = {}
            for path, data in collections[directory]:
                if isinstance(data, dict) and isinstance(data.get("id"), str):
                    ids.setdefault(data["id"], []).append(self._relative(path))
            for document_id, paths in ids.items():
                if len(paths) > 1:
                    issues.append(Issue(directory, f"duplicate id {document_id}: {', '.join(paths)}"))

        progress_path = self.path("progress/units.yaml")
        if progress_path.exists():
            issues.extend(self.validate_progress())
        unique: dict[tuple[str, str, str], Issue] = {}
        for issue in issues:
            unique[(issue.file, issue.path, issue.message)] = issue
        return list(unique.values())

    def _require_initialized_valid(self) -> None:
        state, state_issues = self.state()
        if state != "initialized":
            details = ": " + "; ".join(issue.render() for issue in state_issues) if state_issues else ""
            raise ValueError(f"learning repository is {state}{details}")
        self._raise_issues(self.validate_repository())

    def _candidate_data(self, minutes: int) -> dict[str, Any]:
        frontier = self.read("frontier")
        progress = self.read_progress()
        focus = frontier["focus"]["primary"]
        priority_order = {"high": 0, "medium": 1, "low": 2}
        candidates: list[dict[str, Any]] = []
        for unit in frontier["units"]:
            progress_status = progress.get(unit["id"], {}).get("status", "untouched")
            if progress_status == "verified":
                continue
            blockers = unit.get("blocked_by", [])
            unsatisfied = [
                blocker
                for blocker in blockers
                if progress.get(blocker, {}).get("status") != "verified"
            ]
            estimated = unit["estimated_minutes"]
            item = {
                "id": unit["id"],
                "title": unit["title"],
                "goal": unit["goal"],
                "estimated_minutes": estimated,
                "priority": unit["priority"],
                "primary_focus": focus in unit["nodes"],
                "progress": progress_status,
                "availability": "available" if not unsatisfied else "blocked",
                "blocked_by": unsatisfied,
            }
            item["_rank"] = (
                0 if not unsatisfied else 1,
                0 if progress_status in {"practice", "learning"} else 1,
                0 if item["primary_focus"] else 1,
                0 if estimated <= minutes else 1,
                abs(minutes - estimated),
                priority_order[unit["priority"]],
                unit["id"],
            )
            candidates.append(item)
        candidates.sort(key=lambda item: item.pop("_rank"))
        return {"time_budget_minutes": minutes, "candidates": candidates}

    def session_candidates(self, minutes: int) -> dict[str, Any]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        self._require_initialized_valid()
        return self._candidate_data(minutes)

    def create_session(self, unit_id: str, minutes: int, started_at: str | None = None) -> tuple[Path, dict[str, Any]]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        self._require_initialized_valid()
        frontier = self.read("frontier")
        frontier_ids = {unit["id"] for unit in frontier["units"]}
        if unit_id not in frontier_ids:
            raise ValueError(f"Unit is not present in Frontier: {unit_id}")
        if self.read_progress().get(unit_id, {}).get("status") == "verified":
            raise ValueError(f"Unit is already verified: {unit_id}")

        sessions, _ = self._read_files("sessions")
        active = [data.get("id") for _, data in sessions if isinstance(data, dict) and data.get("status") == "active"]
        if active:
            raise ValueError(f"active Session already exists: {', '.join(str(item) for item in active)}")

        started_at = started_at or self._now()
        date_prefix = started_at[:10]
        sequence = 1
        for _, data in sessions:
            if not isinstance(data, dict) or not isinstance(data.get("id"), str):
                continue
            match = SESSION_PATTERN.fullmatch(data["id"])
            if match and match.group(1) == date_prefix:
                sequence = max(sequence, int(match.group(2)) + 1)
        if sequence > 999:
            raise ValueError(f"Session id space exhausted for {date_prefix}")
        session_id = f"{date_prefix}-{sequence:03d}"
        data = {
            "format_version": 1,
            "id": session_id,
            "started_at": started_at,
            "time_budget_minutes": minutes,
            "status": "active",
            "plan": {"unit": unit_id},
            "actual": {"unit": None},
            "evidence": [],
            "completed_at": None,
        }
        self._raise_issues(self.validate_session(data, f"sessions/{session_id}.yaml"))
        path = self.path(f"sessions/{session_id}.yaml")
        create_yaml(path, data)
        return path, data

    def create_unit(self, data: Any) -> tuple[Path, str]:
        relative = f"units/{data.get('id', '<unknown>')}.yaml" if isinstance(data, dict) else "units/<unknown>.yaml"
        self._raise_issues(self.validate_unit(data, relative))
        path = self.path(relative)
        if path.exists():
            existing = load_yaml(path)
            self._raise_issues(self.validate_unit(existing, relative))
            if existing == data:
                return path, "reused"
            raise ValueError(f"refusing to overwrite initialized Unit: {data['id']}")
        create_yaml(path, data)
        return path, "created"

    def create_evidence(self, data: Any) -> Path:
        relative = (
            f"evidence/{data.get('unit', '<unknown>')}/{data.get('id', '<unknown>')}.yaml"
            if isinstance(data, dict)
            else "evidence/<unknown>.yaml"
        )
        self._raise_issues(self.validate_evidence(data, relative))
        evidence_id = data["id"]
        if self._find_by_id("evidence", evidence_id):
            raise ValueError(f"duplicate Evidence id: {evidence_id}")
        session = load_yaml(self.path(f"sessions/{data['session']}.yaml"))
        if session.get("status") != "active":
            raise ValueError(f"Evidence can only be added to an active Session: {data['session']}")
        path = self.path(relative)
        create_yaml(path, data)
        return path

    def create_assessment(self, data: Any) -> Path:
        relative = f"assessments/{data.get('evidence', '<unknown>')}/001.yaml" if isinstance(data, dict) else "assessments/<unknown>/001.yaml"
        self._raise_issues(self.validate_assessment(data, relative))
        assessment_id = data["id"]
        if self._find_by_id("assessments", assessment_id):
            raise ValueError(f"duplicate Assessment id: {assessment_id}")
        path = self.path(relative)
        create_yaml(path, data)
        return path

    @staticmethod
    def _progress_status(result: dict[str, str]) -> str:
        if result["recall"] == "failed" or result["understanding"] == "failed":
            return "learning"

        if result["application"] in {"failed", "hard"}:
            return "practice"

        return "verified"

    def rebuild_progress(self) -> dict[str, Any]:
        self._raise_issues(self.validate_stage2_repository())
        evidence_documents, _ = self._read_files("evidence")
        assessment_documents, _ = self._read_files("assessments")
        evidence_by_id = {
            data["id"]: data
            for _, data in evidence_documents
            if isinstance(data, dict) and isinstance(data.get("id"), str)
        }
        attempts: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
        for _, assessment in assessment_documents:
            if not isinstance(assessment, dict):
                continue
            evidence = evidence_by_id.get(assessment.get("evidence"))
            if evidence is not None:
                attempts.setdefault(evidence["unit"], []).append((evidence, assessment))

        progress: dict[str, Any] = {}
        for unit_id in sorted(attempts):
            history = sorted(
                attempts[unit_id],
                key=lambda pair: (pair[0]["created_at"], pair[0]["id"], pair[1]["id"]),
            )
            evidence, assessment = history[-1]
            result = assessment["result"]
            progress[unit_id] = {
                "status": self._progress_status(result),
                "attempts": len(history),
                "mastery": dict(result),
                "latest_evidence": evidence["id"],
                "latest_assessment": assessment["id"],
                "last_attempt": evidence["created_at"],
            }
        self._raise_issues(self.validate_progress(progress))
        replace_yaml(self.path("progress/units.yaml"), progress)
        return progress

    def complete_session(self, session_id: str, evidence_ids: list[str], completed_at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        self._raise_issues(self.validate_session(session_id))
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        if session["status"] == "completed":
            if session["evidence"] == evidence_ids:
                return path, session, "already-completed"
            raise ValueError(f"Session is already completed with different Evidence: {session_id}")
        if len(evidence_ids) != 1:
            raise ValueError("Stage 2 Session completion requires exactly one Evidence id")

        evidence_documents: list[dict[str, Any]] = []
        for evidence_id in evidence_ids:
            matches = self._find_by_id("evidence", evidence_id)
            if len(matches) != 1:
                raise ValueError(f"Session completion references unknown or duplicate Evidence: {evidence_id}")
            evidence = matches[0][1]
            if evidence.get("session") != session_id:
                raise ValueError(f"Evidence belongs to another Session: {evidence_id}")
            assessment_matches = [
                item for item in self._find_by_id("assessments", f"{evidence_id}-assessment-001")
                if isinstance(item[1], dict) and item[1].get("evidence") == evidence_id
            ]
            if not assessment_matches:
                assessment_path = self.path(f"assessments/{evidence_id}/001.yaml")
                if not assessment_path.is_file():
                    raise ValueError(f"Evidence has no Assessment: {evidence_id}")
            evidence_documents.append(evidence)

        unit_ids = {evidence["unit"] for evidence in evidence_documents}
        if len(unit_ids) != 1:
            raise ValueError("Stage 2 Session completion supports Evidence for exactly one Unit")
        progress = self.read_progress()
        for evidence in evidence_documents:
            if progress.get(evidence["unit"], {}).get("latest_evidence") != evidence["id"]:
                raise ValueError(f"Progress has not been updated from Evidence: {evidence['id']}")

        session["status"] = "completed"
        session["actual"] = {"unit": next(iter(unit_ids))}
        session["evidence"] = evidence_ids
        session["completed_at"] = completed_at or self._now()
        self._raise_issues(self.validate_session(session, f"sessions/{session_id}.yaml"))
        replace_yaml(path, session)
        return path, session, "completed"
