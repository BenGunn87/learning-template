"""Post-assessment teaching provenance; independent checks still own mastery."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .issues import Issue
from .reevaluation import ReevaluationRepositoryMixin
from .study import RESOURCE_ID_PATTERN
from .yaml_io import YamlFileError, create_text, load_yaml, replace_yaml


class RemediationRepositoryMixin(ReevaluationRepositoryMixin):
    """Keep optional teaching in the source Practice/Review logical Session."""

    @staticmethod
    def _checkpoint_remediation(session: dict[str, Any]) -> dict[str, Any] | None:
        checkpoint = session.get("checkpoint")
        if not isinstance(checkpoint, dict) or checkpoint.get("phase") != "remediation":
            return None
        state = checkpoint.get("remediation")
        if not isinstance(state, dict):
            return None
        return {**deepcopy(state), "session": session.get("id"), "unit": checkpoint.get("unit")}

    def list_remediations(self, session_id: str | None = None, gap_id: str | None = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        gaps, issues = self._read_files("gaps")
        self._raise_issues(issues)
        for _, gap in gaps:
            if isinstance(gap, dict):
                result.extend(
                    {**deepcopy(record), "status": "completed"}
                    for record in gap.get("remediations", [])
                    if isinstance(record, dict)
                )
        sessions, issues = self._read_files("sessions")
        self._raise_issues(issues)
        for _, session in sessions:
            if not isinstance(session, dict):
                continue
            current = self._checkpoint_remediation(session)
            if current is not None:
                result.append({**current, "status": "in_progress"})
            result.extend(
                {**deepcopy(record), "status": "skipped"}
                for record in session.get("skipped_remediations", [])
                if isinstance(record, dict)
            )
        return [
            item for item in result
            if (session_id is None or item.get("session") == session_id)
            and (gap_id is None or item.get("gap") == gap_id)
        ]

    def _source_issues(
        self, record: dict[str, Any], gap: dict[str, Any], session: dict[str, Any], relative: str,
    ) -> list[Issue]:
        issues: list[Issue] = []
        if record.get("gap") != gap.get("id"):
            issues.append(Issue(relative, "Remediation Gap does not match its provenance record"))
        if record.get("session") != session.get("id"):
            issues.append(Issue(relative, "Remediation belongs to another Session"))
        unit_id = record.get("unit")
        unit_matches = self._find_by_id("units", unit_id) if isinstance(unit_id, str) else []
        if len(unit_matches) != 1:
            issues.append(Issue(relative, f"Remediation references unknown Unit: {unit_id}"))
        evidence_id = record.get("source_evidence")
        evidence_matches = self._find_by_id("evidence", evidence_id) if isinstance(evidence_id, str) else []
        assessment_id = record.get("source_assessment")
        assessment_matches = self._find_by_id("assessments", assessment_id) if isinstance(assessment_id, str) else []
        if len(evidence_matches) != 1:
            issues.append(Issue(relative, f"Remediation references unknown Evidence: {evidence_id}"))
        else:
            evidence = evidence_matches[0][1]
            if evidence.get("unit") != unit_id:
                issues.append(Issue(relative, "Remediation Unit does not match source Evidence"))
            if evidence.get("session") != session.get("id"):
                issues.append(Issue(relative, "Remediation source Evidence belongs to another Session"))
            action = evidence.get("type")
            if action not in {"practice", "review"}:
                issues.append(Issue(relative, "Remediation requires source Practice or Review Evidence"))
            if {"type": action, "unit": unit_id} not in session.get("plan", {}).get("actions", []):
                issues.append(Issue(relative, "Remediation source action is absent from Session plan"))
        if len(assessment_matches) != 1:
            issues.append(Issue(relative, f"Remediation references unknown Assessment: {assessment_id}"))
        else:
            assessment_path, assessment = assessment_matches[0]
            if assessment.get("evidence") != evidence_id:
                issues.append(Issue(relative, "Remediation Assessment belongs to another Evidence"))
            issues.extend(self._assessment_node_boundary_issues(assessment, self._relative(assessment_path)))
            if (
                not self._evaluation_includes(assessment, gap.get("node"), gap.get("dimension"))
                or assessment.get("result", {}).get(gap.get("dimension")) not in {"failed", "hard"}
            ):
                issues.append(Issue(relative, "Remediation source Assessment must attribute the Gap node/dimension as weak"))
        if not any(
            isinstance(signal, dict)
            and signal.get("evidence") == evidence_id
            and signal.get("assessment") == assessment_id
            for signal in gap.get("signals", [])
        ):
            issues.append(Issue(relative, "Remediation Gap has no signal from its source Evidence/Assessment"))
        return issues

    def _remediation_resource_issues(self, record: dict[str, Any], relative: str) -> list[Issue]:
        reference = record.get("resource")
        if reference is None:
            if record.get("level") == 3 and "completed_at" in record:
                return [Issue(relative, "completed Level 3 Remediation requires a Generated Resource")]
            return []
        if not isinstance(reference, dict):
            return []  # Schema validation reports the shape.
        resource_id = reference.get("id")
        if not isinstance(resource_id, str) or not RESOURCE_ID_PATTERN.fullmatch(resource_id):
            return [Issue(relative, "invalid Remediation Generated Resource id")]
        expected = f"resources/generated/{resource_id}.md"
        if reference.get("path") != expected:
            return [Issue(relative, f"Remediation Resource path must be {expected}")]
        try:
            content = self.path(expected).read_text(encoding="utf-8")
        except OSError:
            return [Issue(relative, f"Remediation references unknown Generated Resource: {resource_id}")]
        metadata, _, issues = self._parse_generated_document(content, expected)
        issues.extend(self.validate_schema("resource", metadata, expected))
        if isinstance(metadata, dict):
            for field in ("unit", "session", "gap"):
                if metadata.get(field) != record.get(field):
                    issues.append(Issue(relative, f"Remediation Resource {field} mismatch"))
            if metadata.get("id") != resource_id or metadata.get("purpose") != "remediation":
                issues.append(Issue(relative, "Remediation Resource must match its ID and purpose=remediation"))
        if record.get("level") != 3:
            issues.append(Issue(relative, "Remediation Generated Resources require Level 3"))
        return issues

    def _remediation_issues(
        self, record: dict[str, Any], gap: dict[str, Any], session: dict[str, Any], relative: str,
    ) -> list[Issue]:
        issues = self.validate_schema("remediation", record, relative)
        issues.extend(self._source_issues(record, gap, session, relative))
        issues.extend(self._remediation_resource_issues(record, relative))
        ended_at = record.get("completed_at", record.get("skipped_at"))
        if isinstance(ended_at, str):
            try:
                ended = self._timestamp(ended_at)
                for directory, field in (("evidence", "source_evidence"), ("assessments", "source_assessment")):
                    matches = self._find_by_id(directory, record.get(field))
                    if len(matches) == 1 and ended < self._timestamp(matches[0][1].get("created_at")):
                        issues.append(Issue(relative, "Remediation cannot end before its source event"))
                if session.get("completed_at") and ended > self._timestamp(session["completed_at"]):
                    issues.append(Issue(relative, "Remediation cannot end after its Session"))
            except ValueError as exc:
                issues.append(Issue(relative, str(exc)))
        return issues

    def validate_gap(self, gap: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_gap(gap, relative)
        if isinstance(gap, str):
            try:
                gap = load_yaml(self.path(f"gaps/{gap}.yaml"))
            except YamlFileError:
                return issues
        if not isinstance(gap, dict):
            return issues
        relative = relative or f"gaps/{gap.get('id', '<unknown>')}.yaml"
        seen: set[str] = set()
        for record in gap.get("remediations", []):
            if not isinstance(record, dict):
                continue
            remediation_id = record.get("id")
            if isinstance(remediation_id, str):
                if remediation_id in seen:
                    issues.append(Issue(relative, f"duplicate Remediation id: {remediation_id}"))
                seen.add(remediation_id)
            matches = self._find_by_id("sessions", record.get("session")) if isinstance(record.get("session"), str) else []
            if len(matches) != 1:
                issues.append(Issue(relative, f"Remediation references unknown Session: {record.get('session')}"))
                issues.extend(self.validate_schema("remediation", record, relative))
                continue
            session = matches[0][1]
            issues.extend(self._remediation_issues(record, gap, session, relative))
            reference = {"gap": gap.get("id"), "remediation": remediation_id}
            if reference not in session.get("remediations", []):
                issues.append(Issue(relative, "Gap Remediation has no matching Session reference"))
        return issues

    def validate_session(
        self, session: Any, relative: str | None = None, *, gaps_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> list[Issue]:
        issues = super().validate_session(session, relative)
        if isinstance(session, str):
            try:
                session = load_yaml(self.path(f"sessions/{session}.yaml"))
            except YamlFileError:
                return issues
        if not isinstance(session, dict):
            return issues
        relative = relative or f"sessions/{session.get('id', '<unknown>')}.yaml"

        def get_gap(gap_id: Any) -> dict[str, Any] | None:
            if not isinstance(gap_id, str):
                return None
            if gaps_by_id is not None and gap_id in gaps_by_id:
                return gaps_by_id[gap_id]
            matches = self._find_by_id("gaps", gap_id)
            return matches[0][1] if len(matches) == 1 else None

        seen: set[str] = set()
        for reference in session.get("remediations", []):
            if not isinstance(reference, dict):
                continue
            remediation_id = reference.get("remediation")
            gap = get_gap(reference.get("gap"))
            records = [
                record for record in gap.get("remediations", [])
                if isinstance(record, dict) and record.get("id") == remediation_id
            ] if gap is not None else []
            if len(records) != 1:
                issues.append(Issue(relative, "Session Remediation reference must point to one completed Gap record"))
            else:
                issues.extend(self._remediation_issues(records[0], gap, session, relative))
                if "completed_at" not in records[0]:
                    issues.append(Issue(relative, "Session Remediation reference is not completed"))
            if isinstance(remediation_id, str):
                if remediation_id in seen:
                    issues.append(Issue(relative, f"duplicate Session Remediation id: {remediation_id}"))
                seen.add(remediation_id)
        current = self._checkpoint_remediation(session)
        skipped = session.get("skipped_remediations", [])
        for record in ([current] if current else []) + [item for item in skipped if isinstance(item, dict)]:
            remediation_id = record.get("id")
            if isinstance(remediation_id, str):
                if remediation_id in seen:
                    issues.append(Issue(relative, "Remediation cannot be both in_progress, completed, or skipped"))
                seen.add(remediation_id)
            gap = get_gap(record.get("gap"))
            if gap is None:
                issues.append(Issue(relative, f"Remediation references unknown Gap: {record.get('gap')}"))
                issues.extend(self.validate_schema("remediation", record, relative))
            else:
                issues.extend(self._remediation_issues(record, gap, session, relative))
                if any(isinstance(item, dict) and item.get("id") == remediation_id for item in gap.get("remediations", [])):
                    issues.append(Issue(relative, "completed Remediation cannot be in_progress or skipped"))
        checkpoint = session.get("checkpoint")
        if isinstance(checkpoint, dict):
            if (checkpoint.get("phase") == "remediation") != isinstance(checkpoint.get("remediation"), dict):
                issues.append(Issue(relative, "phase=remediation requires Remediation state and vice versa"))
            if current is not None:
                evidence_matches = self._find_by_id("evidence", current.get("source_evidence"))
                if len(evidence_matches) == 1 and checkpoint.get("action") != evidence_matches[0][1].get("type"):
                    issues.append(Issue(relative, "Remediation checkpoint action must match source Evidence"))
                key = (checkpoint.get("action"), checkpoint.get("unit"))
                actions = session.get("actual", {}).get("actions", [])
                if session.get("status") not in {"active", "paused"} or not any(
                    self._action_key(action) == key and action.get("status") == "in_progress"
                    for action in actions if isinstance(action, dict)
                ):
                    issues.append(Issue(relative, "Remediation checkpoint requires an unfinished source action"))
        return issues

    def validate_learning_records(self) -> list[Issue]:
        issues = super().validate_learning_records()
        seen: set[str] = set()
        for record in self.list_remediations():
            remediation_id = record.get("id")
            if isinstance(remediation_id, str):
                if remediation_id in seen:
                    issues.append(Issue("sessions", f"duplicate global Remediation id: {remediation_id}"))
                seen.add(remediation_id)
        return issues

    def validate_remediation(self, remediation_id: str) -> list[Issue]:
        records = [record for record in self.list_remediations() if record.get("id") == remediation_id]
        if len(records) != 1:
            return [Issue("gaps", f"unknown or duplicate Remediation: {remediation_id}")]
        record = records[0]
        return self.validate_gap(record["gap"]) + self.validate_session(record["session"])

    def _generated_session_issues(self, metadata: dict[str, Any], session: dict[str, Any], relative: str) -> list[Issue]:
        if metadata.get("purpose", "study") != "remediation":
            return super()._generated_session_issues(metadata, session, relative)
        issues: list[Issue] = []
        gap_matches = self._find_by_id("gaps", metadata.get("gap")) if isinstance(metadata.get("gap"), str) else []
        if len(gap_matches) != 1:
            return [Issue(relative, "Remediation Resource references unknown Gap")]
        gap = gap_matches[0][1]
        records = [record for record in gap.get("remediations", []) if isinstance(record, dict)]
        records.extend(record for record in session.get("skipped_remediations", []) if isinstance(record, dict))
        current = self._checkpoint_remediation(session)
        if current is not None:
            records.append(current)
        reference = {"id": metadata.get("id"), "path": relative}
        owners = [record for record in records if record.get("resource") == reference and record.get("session") == session.get("id")]
        if len(owners) != 1:
            issues.append(Issue(relative, "Remediation Resource must be linked to one in-progress, completed, or skipped Remediation"))
        else:
            issues.extend(self._source_issues(owners[0], gap, session, relative))
            if owners[0].get("unit") != metadata.get("unit") or owners[0].get("level") != 3:
                issues.append(Issue(relative, "Remediation Resource requires its source Unit and Level 3"))
        unit_matches = self._find_by_id("units", metadata.get("unit"))
        coverage = metadata.get("coverage", [])
        if isinstance(coverage, list) and len(unit_matches) == 1:
            if gap.get("node") not in coverage or any(node not in unit_matches[0][1].get("nodes", []) for node in coverage):
                issues.append(Issue(relative, "Remediation Resource coverage must include the Gap within unit.nodes"))
        return issues

    def _remediation_timestamp(self, session: dict[str, Any], value: str | None) -> str:
        timestamp = value or self._now()
        parsed = self._timestamp(timestamp)
        latest = session.get("checkpoint")
        if parsed < self._timestamp(session["segments"][-1]["started_at"]) or (
            isinstance(latest, dict) and parsed < self._timestamp(latest["updated_at"])
        ):
            raise ValueError("Remediation timestamp cannot precede the current segment/checkpoint")
        return timestamp

    def start_remediation(self, data: Any, started_at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        if not isinstance(data, dict):
            raise ValueError("Remediation input must be a mapping")
        record = {"step": "explanation", "misconceptions_addressed": [], "guided_exercise": False, "resource": None, **deepcopy(data)}
        self._raise_issues(self.validate_schema("remediation", record, "remediation/<input>"))
        if "step" not in record or "completed_at" in record or "skipped_at" in record:
            raise ValueError("start Remediation requires in-progress teaching state")
        path = self.path(f"sessions/{record['session']}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session))
        if session["status"] != "active":
            raise ValueError("Remediation can only start in an active Session")
        existing = [item for item in self.list_remediations() if item.get("id") == record["id"]]
        if existing:
            same = {key: value for key, value in existing[0].items() if key != "status"}
            if len(existing) == 1 and existing[0]["status"] == "in_progress" and same == record:
                return path, session, "already-started"
            raise ValueError(f"Remediation id already exists with different state: {record['id']}")
        if self._checkpoint_remediation(session) is not None:
            raise ValueError("complete or skip the current Remediation first")
        gap_matches = self._find_by_id("gaps", record["gap"])
        if len(gap_matches) != 1:
            raise ValueError(f"unknown Gap: {record['gap']}")
        gap = gap_matches[0][1]
        if gap.get("status") not in {"detected", "confirmed"}:
            raise ValueError("Remediation requires an active Gap")
        self._raise_issues(self._remediation_issues(record, gap, session, "remediation/<input>"))
        if self.active_assessment(record["source_evidence"])["id"] != record["source_assessment"]:
            raise ValueError("Remediation must start from the active source Assessment")
        if record["resource"] is not None:
            raise ValueError("create the Level 3 Resource after starting Remediation")
        timestamp = self._remediation_timestamp(session, started_at)
        assessment = self._find_by_id("assessments", record["source_assessment"])[0][1]
        if self._timestamp(timestamp) < self._timestamp(assessment["created_at"]):
            raise ValueError("Remediation cannot start before its source Assessment")
        action = self._find_by_id("evidence", record["source_evidence"])[0][1]["type"]
        checkpoint = {
            "unit": record["unit"], "action": action,
            "stage": "remediation", "phase": "remediation",
            "completed_steps": {"evidence_created": True, "assessment_created": True},
            "remediation": {key: value for key, value in record.items() if key not in {"unit", "session"}},
        }
        self._apply_checkpoint(session, checkpoint, timestamp, "in_progress")
        self._raise_issues(self.validate_session(session))
        replace_yaml(path, session)
        return path, session, "started"

    def _apply_checkpoint(self, session: dict[str, Any], checkpoint: dict[str, Any], updated_at: str, action_status: str) -> None:
        current = self._checkpoint_remediation(session)
        if current is not None:
            new = checkpoint.get("remediation")
            if checkpoint.get("phase") != "remediation" or not isinstance(new, dict) or action_status != "in_progress":
                raise ValueError("complete or skip Remediation before leaving its checkpoint")
            for field in ("id", "gap", "source_evidence", "source_assessment"):
                if new.get(field) != current.get(field):
                    raise ValueError(f"in-progress Remediation {field} cannot change")
            if new.get("level", 0) < current["level"]:
                raise ValueError("Remediation level may escalate but cannot decrease")
            if current.get("resource") is not None and new.get("resource") != current["resource"]:
                raise ValueError("saved Remediation Resource must be reused")
        super()._apply_checkpoint(session, checkpoint, updated_at, action_status)

    def create_generated_resource(self, content: str) -> tuple[Path, str]:
        metadata, _, parse_issues = self._parse_generated_document(content, "resources/generated/<input>.md")
        if not isinstance(metadata, dict) or metadata.get("purpose", "study") != "remediation":
            return super().create_generated_resource(content)
        self._raise_issues(parse_issues + self.validate_schema("resource", metadata, "resources/generated/<input>.md"))
        relative = f"resources/generated/{metadata['id']}.md"
        path = self.path(relative)
        if path.exists():
            self._raise_issues(self._validate_generated_document(content, relative))
            if path.read_text(encoding="utf-8") == content:
                return path, "reused"
            raise ValueError(f"refusing to overwrite generated Resource: {metadata['id']}")
        session_path = self.path(f"sessions/{metadata['session']}.yaml")
        session = load_yaml(session_path)
        self._raise_issues(self.validate_session(session))
        current = self._checkpoint_remediation(session)
        if session.get("status") != "active" or current is None or current.get("level") != 3:
            raise ValueError("Remediation Resource creation requires active Level 3 Remediation")
        if current.get("resource") is not None:
            raise ValueError("reuse the saved Remediation Resource")
        session["checkpoint"]["updated_at"] = self._remediation_timestamp(session, metadata["created_at"])
        session["checkpoint"]["remediation"]["resource"] = {"id": metadata["id"], "path": relative}
        self._raise_issues(self._validate_generated_document(content, relative, session=session))
        create_text(path, content)
        try:
            self._raise_issues(self.validate_session(session))
            replace_yaml(session_path, session)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path, "created"

    @staticmethod
    def _leave_remediation(session: dict[str, Any], timestamp: str) -> None:
        checkpoint = session["checkpoint"]
        checkpoint.pop("remediation", None)
        checkpoint.pop("phase", None)
        checkpoint["stage"] = "assessment"
        checkpoint["updated_at"] = timestamp

    def complete_remediation(self, remediation_id: str, completed_at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        records = [item for item in self.list_remediations() if item.get("id") == remediation_id]
        if len(records) != 1:
            raise ValueError(f"unknown or duplicate Remediation: {remediation_id}")
        current = records[0]
        session_path = self.path(f"sessions/{current['session']}.yaml")
        session = load_yaml(session_path)
        if current["status"] == "completed":
            self._raise_issues(self.validate_remediation(remediation_id))
            if completed_at is not None and completed_at != current["completed_at"]:
                raise ValueError("completed Remediation cannot be rewritten with a different timestamp")
            return session_path, session, "already-completed"
        if current["status"] != "in_progress" or session.get("status") != "active":
            raise ValueError("complete Remediation requires its active Session")
        self._raise_issues(self.validate_session(session))
        timestamp = self._remediation_timestamp(session, completed_at)
        record = {key: value for key, value in current.items() if key not in {"status", "step"}}
        record["completed_at"] = timestamp
        gap_path, gap = self._find_by_id("gaps", record["gap"])[0]
        self._raise_issues(self._remediation_issues(record, gap, session, self._relative(gap_path)))
        previous_gap = deepcopy(gap)
        gap.setdefault("remediations", []).append(record)
        session.setdefault("remediations", []).append({"gap": gap["id"], "remediation": remediation_id})
        self._leave_remediation(session, timestamp)
        self._raise_issues(self.validate_schema("gap", gap, self._relative(gap_path)))
        self._raise_issues(self.validate_session(session, gaps_by_id={gap["id"]: gap}))
        replace_yaml(gap_path, gap)
        try:
            replace_yaml(session_path, session)
        except Exception:
            replace_yaml(gap_path, previous_gap)
            raise
        return session_path, session, "completed"

    def skip_remediation(self, session_id: str, skipped_at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session))
        current = self._checkpoint_remediation(session)
        if current is None:
            return path, session, "already-skipped"
        if session.get("status") != "active":
            raise ValueError("resume the Session before skipping Remediation")
        timestamp = self._remediation_timestamp(session, skipped_at)
        record = {key: value for key, value in current.items() if key != "step"}
        record["skipped_at"] = timestamp
        session.setdefault("skipped_remediations", []).append(record)
        self._leave_remediation(session, timestamp)
        self._raise_issues(self.validate_session(session))
        replace_yaml(path, session)
        return path, session, "skipped"

    def complete_session(self, session_id: str, evidence_ids: list[str], completed_at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"sessions/{session_id}.yaml")
        original = load_yaml(path)
        current = self._checkpoint_remediation(original)
        if current is None:
            return super().complete_session(session_id, evidence_ids, completed_at)
        if current["source_evidence"] not in evidence_ids:
            raise ValueError("Session completion must include Remediation source Evidence")
        # Finishing the Session is an explicit skip of its unfinished teaching.
        timestamp = completed_at or self._now()
        self.skip_remediation(session_id, timestamp)
        try:
            return super().complete_session(session_id, evidence_ids, timestamp)
        except Exception:
            replace_yaml(path, original)
            raise
