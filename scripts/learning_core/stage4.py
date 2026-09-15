"""Deterministic Stage 4 pause, resume, checkpoint, and segment operations."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .issues import Issue
from .stage2 import SESSION_PATTERN
from .stage3 import ACTION_FOR_EVIDENCE, Stage3RepositoryMixin
from .yaml_io import create_yaml, load_yaml, replace_yaml


UNFINISHED_SESSION_STATUSES = {"active", "paused"}
ACTION_STATUSES = {"planned", "in_progress", "completed"}


class Stage4RepositoryMixin(Stage3RepositoryMixin):
    """Add resumable logical Sessions made of one or more timed segments."""

    @staticmethod
    def _timestamp(value: str, label: str = "timestamp") -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid RFC 3339 {label}: {value}") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"RFC 3339 {label} must include a timezone: {value}")
        return parsed

    def _resumable_documents(self) -> list[tuple[Path, dict[str, Any]]]:
        sessions, _ = self._read_files("sessions")
        return [
            (path, data)
            for path, data in sessions
            if isinstance(data, dict) and data.get("status") in UNFINISHED_SESSION_STATUSES
        ]

    def validate_session(self, session: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_session(session, relative)
        if isinstance(session, str):
            path = self.path(f"sessions/{session}.yaml")
            try:
                session = load_yaml(path)
            except ValueError:
                return issues
        if not isinstance(session, dict):
            return issues
        relative = relative or f"sessions/{session.get('id', '<unknown>')}.yaml"

        segments = session.get("segments")
        status = session.get("status")
        if isinstance(segments, list) and segments:
            parsed_segments: list[tuple[datetime, datetime | None]] = []
            for index, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    continue
                try:
                    started = self._timestamp(segment.get("started_at"), "segment started_at")
                    ended_value = segment.get("ended_at")
                    ended = self._timestamp(ended_value, "segment ended_at") if isinstance(ended_value, str) else None
                except ValueError as exc:
                    issues.append(Issue(relative, str(exc), f"$.segments[{index}]"))
                    continue
                if ended is not None and ended < started:
                    issues.append(Issue(relative, "segment cannot end before it starts", f"$.segments[{index}].ended_at"))
                if (ended is None) != (segment.get("end_reason") is None):
                    issues.append(Issue(relative, "ended_at and end_reason must either both be set or both be null", f"$.segments[{index}]"))
                if index < len(segments) - 1 and ended is None:
                    issues.append(Issue(relative, "only the latest segment may be open", f"$.segments[{index}]"))
                parsed_segments.append((started, ended))

            for index in range(1, len(parsed_segments)):
                previous_end = parsed_segments[index - 1][1]
                current_start = parsed_segments[index][0]
                if previous_end is not None and current_start < previous_end:
                    issues.append(Issue(relative, "Session segments must not overlap", f"$.segments[{index}].started_at"))

            open_count = sum(
                isinstance(segment, dict) and segment.get("ended_at") is None
                for segment in segments
            )
            expected_open = 1 if status == "active" else 0
            if open_count != expected_open:
                issues.append(Issue(relative, f"status={status} requires {expected_open} open segment(s)", "$.segments"))
            latest = segments[-1]
            if isinstance(latest, dict) and session.get("time_budget_minutes") != latest.get("budget_minutes"):
                issues.append(Issue(relative, "time_budget_minutes must match the latest segment budget", "$.time_budget_minutes"))
            if isinstance(segments[0], dict) and session.get("started_at") != segments[0].get("started_at"):
                issues.append(Issue(relative, "started_at must match the first segment", "$.started_at"))

        plan_actions = session.get("plan", {}).get("actions") if isinstance(session.get("plan"), dict) else None
        actual_actions = session.get("actual", {}).get("actions") if isinstance(session.get("actual"), dict) else None
        if isinstance(plan_actions, list) and isinstance(actual_actions, list):
            planned_keys = [(item.get("type"), item.get("unit")) for item in plan_actions if isinstance(item, dict)]
            actual_keys = [(item.get("type"), item.get("unit")) for item in actual_actions if isinstance(item, dict)]
            if actual_keys != planned_keys:
                issues.append(Issue(relative, "actual actions must match planned actions in order", "$.actual.actions"))
            statuses = [item.get("status") for item in actual_actions if isinstance(item, dict)]
            if sum(value == "in_progress" for value in statuses) > 1:
                issues.append(Issue(relative, "at most one Session action may be in_progress", "$.actual.actions"))
            order = {"completed": 0, "in_progress": 1, "planned": 2}
            known_statuses = [value for value in statuses if value in order]
            if known_statuses != sorted(known_statuses, key=order.__getitem__):
                issues.append(Issue(relative, "action states must be completed, then optionally in_progress, then planned", "$.actual.actions"))
            if status == "paused" and statuses.count("in_progress") != 1:
                issues.append(Issue(relative, "a paused Session requires one in_progress action", "$.actual.actions"))
            if status == "completed" and "in_progress" in statuses:
                issues.append(Issue(relative, "a completed Session cannot have an in_progress action", "$.actual.actions"))

        checkpoint = session.get("checkpoint")
        in_progress_keys = [
            self._action_key(action)
            for action in actual_actions or []
            if isinstance(action, dict) and action.get("status") == "in_progress"
        ]
        if in_progress_keys and not isinstance(checkpoint, dict):
            issues.append(Issue(relative, "an in_progress action requires a checkpoint", "$.checkpoint"))
        if isinstance(checkpoint, dict):
            checkpoint_key = (checkpoint.get("action"), checkpoint.get("unit"))
            if isinstance(plan_actions, list) and checkpoint_key not in [
                (item.get("type"), item.get("unit")) for item in plan_actions if isinstance(item, dict)
            ]:
                issues.append(Issue(relative, "checkpoint action is not present in the Session plan", "$.checkpoint"))
            if in_progress_keys and checkpoint_key != in_progress_keys[0]:
                issues.append(Issue(relative, "checkpoint must identify the in_progress action", "$.checkpoint"))
            try:
                checkpoint_at = self._timestamp(checkpoint.get("updated_at"), "checkpoint updated_at")
            except ValueError as exc:
                issues.append(Issue(relative, str(exc), "$.checkpoint.updated_at"))
            else:
                try:
                    session_started = self._timestamp(session.get("started_at"), "Session started_at")
                except ValueError:
                    pass
                else:
                    if checkpoint_at < session_started:
                        issues.append(Issue(relative, "checkpoint cannot precede the Session", "$.checkpoint.updated_at"))
        return issues

    def validate_stage2_repository(self) -> list[Issue]:
        issues = super().validate_stage2_repository()
        resumable = self._resumable_documents()
        if len(resumable) > 1:
            ids = ", ".join(str(data.get("id")) for _, data in resumable)
            issues.append(Issue("sessions", f"at most one active or paused Session is allowed: {ids}"))
        return issues

    def detect_resumable_session(self) -> dict[str, Any]:
        resumable = self._resumable_documents()
        if len(resumable) > 1:
            ids = ", ".join(str(data.get("id")) for _, data in resumable)
            raise ValueError(f"multiple unfinished Sessions found: {ids}")
        if not resumable:
            return {"resumable": False}
        _, session = resumable[0]
        self._raise_issues(self.validate_session(session))
        return {
            "resumable": True,
            "session_id": session["id"],
            "status": session["status"],
            "potentially_stale": session["status"] == "active",
            "checkpoint": deepcopy(session.get("checkpoint")),
            "active_minutes": self.calculate_active_minutes(session["id"]),
        }

    def plan_session_candidates(self, minutes: int, on_date: str | None = None) -> dict[str, Any]:
        result = super().plan_session_candidates(minutes, on_date)
        resumable = self.detect_resumable_session()
        session_settings = self._settings()["session"]
        threshold = session_settings.get("min_partial_unit_minutes", 10)
        result["min_partial_unit_minutes"] = threshold

        if resumable["resumable"]:
            checkpoint = resumable.get("checkpoint")
            action = None
            if isinstance(checkpoint, dict):
                action = {"type": checkpoint["action"], "unit": checkpoint["unit"], "resume": True}
            result["resumable_session"] = resumable
            result["suggested_actions"] = [action] if action else []
            return result

        review_count = sum(action["type"] == "review" for action in result["suggested_actions"])
        remaining = minutes - review_count * result["review_estimated_minutes"]
        result["remaining_minutes"] = remaining
        has_main_action = any(action["type"] != "review" for action in result["suggested_actions"])
        if not has_main_action and remaining >= threshold:
            available = [item for item in result["candidates"] if item["availability"] == "available"]
            if available:
                main = available[0]
                action_type = "practice" if main["progress"] == "practice" else "study"
                action: dict[str, Any] = {"type": action_type, "unit": main["id"]}
                if main["estimated_minutes"] > remaining:
                    action.update({"partial": True, "available_minutes": remaining})
                result["suggested_actions"].append(action)
        return result

    def create_session(
        self,
        unit_id: str | None,
        minutes: int,
        started_at: str | None = None,
        actions: list[dict[str, str]] | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        self._require_initialized_valid()
        started_at = started_at or self._now()
        self._timestamp(started_at, "Session started_at")
        if actions is None:
            if not unit_id:
                raise ValueError("Session requires a Unit or at least one action")
            actions = [{"type": self._infer_action(unit_id, started_at[:10]), "unit": unit_id}]
        elif unit_id is not None:
            raise ValueError("use either --unit or explicit actions, not both")
        if not actions:
            raise ValueError("Session requires at least one action")

        frontier_ids = {unit["id"] for unit in self.read("frontier")["units"]}
        progress = self.read_progress()
        due_ids = {item["id"] for item in self.get_due_reviews(started_at[:10])}
        normalized_actions: list[dict[str, str]] = []
        for action in actions:
            if not isinstance(action, dict) or set(action) != {"type", "unit"} or action.get("type") not in ACTION_FOR_EVIDENCE.values():
                raise ValueError(f"invalid Session action: {action}")
            action_type, action_unit = action["type"], action["unit"]
            if action_unit not in frontier_ids:
                raise ValueError(f"Unit is not present in Frontier: {action_unit}")
            state = progress.get(action_unit, {}).get("status", "untouched")
            if action_type == "practice" and state != "practice":
                raise ValueError(f"Practice action requires status=practice: {action_unit}")
            if action_type == "review" and action_unit not in due_ids:
                raise ValueError(f"Review action requires a due verified Unit: {action_unit}")
            if action_type == "study" and state == "verified":
                raise ValueError(f"Study action cannot repeat a verified Unit: {action_unit}")
            normalized_actions.append({"type": action_type, "unit": action_unit})
        if len({(item["type"], item["unit"]) for item in normalized_actions}) != len(normalized_actions):
            raise ValueError("Session actions must be unique")

        review_count = sum(action["type"] == "review" for action in normalized_actions)
        review_settings = self._review_settings()
        if review_count * review_settings["estimated_minutes"] > int(minutes * review_settings["max_session_share"]):
            raise ValueError("Review actions exceed the configured Session review budget")

        sessions, _ = self._read_files("sessions")
        unfinished = [
            data.get("id")
            for _, data in sessions
            if isinstance(data, dict) and data.get("status") in UNFINISHED_SESSION_STATUSES
        ]
        if unfinished:
            raise ValueError(f"unfinished Session already exists: {', '.join(str(item) for item in unfinished)}")
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
            "plan": {"unit": normalized_actions[0]["unit"], "actions": normalized_actions},
            "actual": {
                "unit": None,
                "actions": [{**action, "status": "planned"} for action in normalized_actions],
            },
            "segments": [
                {
                    "started_at": started_at,
                    "ended_at": None,
                    "budget_minutes": minutes,
                    "end_reason": None,
                }
            ],
            "checkpoint": None,
            "evidence": [],
            "completed_at": None,
        }
        self._raise_issues(self.validate_session(data, f"sessions/{session_id}.yaml"))
        path = self.path(f"sessions/{session_id}.yaml")
        create_yaml(path, data)
        return path, data

    @staticmethod
    def _action_key(action: dict[str, Any]) -> tuple[Any, Any]:
        return action.get("type"), action.get("unit")

    def _apply_checkpoint(
        self,
        session: dict[str, Any],
        checkpoint: dict[str, Any],
        updated_at: str,
        action_status: str,
    ) -> None:
        if action_status not in {"in_progress", "completed"}:
            raise ValueError(f"checkpoint action status must be in_progress or completed: {action_status}")
        checkpoint = deepcopy(checkpoint)
        checkpoint["updated_at"] = updated_at
        key = (checkpoint.get("action"), checkpoint.get("unit"))
        matching = [action for action in session["actual"]["actions"] if self._action_key(action) == key]
        if len(matching) != 1:
            raise ValueError(f"checkpoint action is not present exactly once in Session plan: {key}")
        target = matching[0]
        if target["status"] == "completed" and action_status != "completed":
            raise ValueError(f"completed Session action cannot return to {action_status}: {key}")
        if action_status == "in_progress":
            other = [
                action for action in session["actual"]["actions"]
                if action["status"] == "in_progress" and action is not target
            ]
            if other:
                raise ValueError(f"complete the current action before starting another: {self._action_key(other[0])}")
        target["status"] = action_status
        session["actual"]["unit"] = checkpoint["unit"]
        session["checkpoint"] = checkpoint

    def update_checkpoint(
        self,
        session_id: str,
        checkpoint: dict[str, Any],
        updated_at: str | None = None,
        action_status: str = "in_progress",
    ) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session, self._relative(path)))
        if session["status"] != "active":
            raise ValueError(f"checkpoint can only be updated for an active Session: {session_id}")
        timestamp = updated_at or checkpoint.get("updated_at") or self._now()
        parsed = self._timestamp(timestamp, "checkpoint updated_at")
        open_segment = session["segments"][-1]
        if parsed < self._timestamp(open_segment["started_at"], "segment started_at"):
            raise ValueError("checkpoint cannot precede the current segment")
        existing = session.get("checkpoint")
        if isinstance(existing, dict) and parsed < self._timestamp(existing["updated_at"], "checkpoint updated_at"):
            raise ValueError("checkpoint timestamp cannot move backwards")
        self._apply_checkpoint(session, checkpoint, timestamp, action_status)
        self._raise_issues(self.validate_session(session, self._relative(path)))
        if session == load_yaml(path):
            return path, session, "already-updated"
        replace_yaml(path, session)
        return path, session, "updated"

    def _close_open_segment(self, session: dict[str, Any], ended_at: str, reason: str) -> None:
        if reason not in {"paused", "completed", "recovered"}:
            raise ValueError(f"invalid segment end reason: {reason}")
        open_segments = [segment for segment in session["segments"] if segment["ended_at"] is None]
        if len(open_segments) != 1:
            raise ValueError("Session must have exactly one open segment")
        segment = open_segments[0]
        if self._timestamp(ended_at, "segment ended_at") < self._timestamp(segment["started_at"], "segment started_at"):
            raise ValueError("segment cannot end before it starts")
        segment["ended_at"] = ended_at
        segment["end_reason"] = reason

    def pause_session(
        self,
        session_id: str,
        checkpoint: dict[str, Any] | None = None,
        paused_at: str | None = None,
    ) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session, self._relative(path)))
        if session["status"] == "paused":
            return path, session, "already-paused"
        if session["status"] == "completed":
            raise ValueError(f"completed Session cannot be paused: {session_id}")
        timestamp = paused_at or self._now()
        self._timestamp(timestamp, "pause timestamp")
        saved = checkpoint if checkpoint is not None else session.get("checkpoint")
        if not isinstance(saved, dict):
            raise ValueError("pause requires a checkpoint")
        existing = session.get("checkpoint")
        if isinstance(existing, dict) and self._timestamp(timestamp) < self._timestamp(existing["updated_at"]):
            raise ValueError("pause timestamp cannot precede the latest checkpoint")
        self._apply_checkpoint(session, saved, timestamp, "in_progress")
        self._close_open_segment(session, timestamp, "paused")
        session["status"] = "paused"
        self._raise_issues(self.validate_session(session, self._relative(path)))
        replace_yaml(path, session)
        return path, session, "paused"

    def resume_session(
        self,
        session_id: str | None,
        minutes: int,
        resumed_at: str | None = None,
    ) -> tuple[Path, dict[str, Any], str]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        detected = self.detect_resumable_session()
        if not detected["resumable"]:
            raise ValueError("no active or paused Session exists")
        actual_id = detected["session_id"]
        if session_id is not None and session_id != actual_id:
            raise ValueError(f"unfinished Session is {actual_id}, not {session_id}")
        path = self.path(f"sessions/{actual_id}.yaml")
        session = load_yaml(path)
        if session["status"] == "active":
            return path, session, "already-active"
        timestamp = resumed_at or self._now()
        parsed = self._timestamp(timestamp, "resume timestamp")
        previous_end = self._timestamp(session["segments"][-1]["ended_at"], "segment ended_at")
        if parsed < previous_end:
            raise ValueError("new segment cannot start before the previous segment ended")
        session["segments"].append(
            {"started_at": timestamp, "ended_at": None, "budget_minutes": minutes, "end_reason": None}
        )
        session["time_budget_minutes"] = minutes
        session["status"] = "active"
        if isinstance(session.get("checkpoint"), dict):
            session["checkpoint"]["updated_at"] = timestamp
        self._raise_issues(self.validate_session(session, self._relative(path)))
        replace_yaml(path, session)
        return path, session, "resumed"

    def recover_session(
        self,
        session_id: str | None,
        minutes: int,
        recovered_at: str | None = None,
    ) -> tuple[Path, dict[str, Any], str]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        detected = self.detect_resumable_session()
        if not detected["resumable"] or detected["status"] != "active":
            raise ValueError("no potentially stale active Session exists")
        actual_id = detected["session_id"]
        if session_id is not None and session_id != actual_id:
            raise ValueError(f"active Session is {actual_id}, not {session_id}")
        path = self.path(f"sessions/{actual_id}.yaml")
        session = load_yaml(path)
        checkpoint = session.get("checkpoint")
        if not isinstance(checkpoint, dict):
            raise ValueError("active Session has no reliable checkpoint; user input is required for recovery")
        timestamp = recovered_at or self._now()
        self._timestamp(timestamp, "recovery timestamp")
        last_recovery = session.get("last_recovery")
        if isinstance(last_recovery, dict) and last_recovery.get("recovered_at") == timestamp:
            return path, session, "already-recovered"
        checkpoint_at = checkpoint["updated_at"]
        if self._timestamp(timestamp) < self._timestamp(checkpoint_at):
            raise ValueError("recovery timestamp cannot precede the latest checkpoint")
        self._close_open_segment(session, checkpoint_at, "recovered")
        session["segments"].append(
            {"started_at": timestamp, "ended_at": None, "budget_minutes": minutes, "end_reason": None}
        )
        session["time_budget_minutes"] = minutes
        session["last_recovery"] = {"recovered_at": timestamp, "checkpoint_at": checkpoint_at}
        session["checkpoint"]["updated_at"] = timestamp
        self._raise_issues(self.validate_session(session, self._relative(path)))
        replace_yaml(path, session)
        return path, session, "recovered"

    def calculate_active_minutes(self, session_id: str) -> int | float:
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session, self._relative(path)))
        seconds = 0.0
        for segment in session["segments"]:
            if segment["ended_at"] is None:
                continue
            start = self._timestamp(segment["started_at"])
            end = self._timestamp(segment["ended_at"])
            seconds += (end - start).total_seconds()
        minutes = round(seconds / 60, 2)
        return int(minutes) if minutes.is_integer() else minutes

    def complete_session(
        self,
        session_id: str,
        evidence_ids: list[str],
        completed_at: str | None = None,
    ) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        self._raise_issues(self.validate_session(session, self._relative(path)))
        if session["status"] == "completed":
            if session["evidence"] == evidence_ids:
                return path, session, "already-completed"
            raise ValueError(f"Session is already completed with different Evidence: {session_id}")
        if session["status"] == "paused":
            raise ValueError("resume a paused Session before completing it")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Session completion contains duplicate Evidence ids")

        documents: list[dict[str, Any]] = []
        for evidence_id in evidence_ids:
            matches = self._find_by_id("evidence", evidence_id)
            if len(matches) != 1:
                raise ValueError(f"Session completion references unknown or duplicate Evidence: {evidence_id}")
            evidence = matches[0][1]
            if evidence.get("session") != session_id:
                raise ValueError(f"Evidence belongs to another Session: {evidence_id}")
            assessment_path = self.path(f"assessments/{evidence_id}/001.yaml")
            if not assessment_path.is_file():
                raise ValueError(f"Evidence has no Assessment: {evidence_id}")
            documents.append(evidence)

        progress = self.read_progress()
        latest_by_unit = {evidence["unit"]: evidence["id"] for evidence in documents}
        for unit_id, evidence_id in latest_by_unit.items():
            if progress.get(unit_id, {}).get("latest_evidence") != evidence_id:
                raise ValueError(f"Progress has not been updated from Evidence: {evidence_id}")

        completed_keys = [(ACTION_FOR_EVIDENCE[evidence["type"]], evidence["unit"]) for evidence in documents]
        if len(completed_keys) != len(set(completed_keys)):
            raise ValueError("a Session action may create Evidence only once")
        actual_actions = session["actual"]["actions"]
        for key in completed_keys:
            matching = [action for action in actual_actions if self._action_key(action) == key]
            if len(matching) != 1:
                raise ValueError(f"Completed action was not planned exactly once: {key}")
            matching[0]["status"] = "completed"
        if any(action["status"] == "in_progress" for action in actual_actions):
            raise ValueError("an unfinished in_progress action must be paused, not completed")

        timestamp = completed_at or self._now()
        self._timestamp(timestamp, "Session completed_at")
        checkpoint = session.get("checkpoint")
        if isinstance(checkpoint, dict) and self._timestamp(timestamp) < self._timestamp(checkpoint["updated_at"]):
            raise ValueError("Session completion cannot precede the latest checkpoint")
        self._close_open_segment(session, timestamp, "completed")
        session["status"] = "completed"
        session["actual"]["unit"] = next(
            (action["unit"] for action in actual_actions if action["status"] == "completed"),
            None,
        )
        session["evidence"] = list(evidence_ids)
        session["completed_at"] = timestamp
        if isinstance(session.get("checkpoint"), dict):
            session["checkpoint"]["updated_at"] = timestamp
        self._raise_issues(self.validate_session(session, self._relative(path)))
        replace_yaml(path, session)
        return path, session, "completed"
