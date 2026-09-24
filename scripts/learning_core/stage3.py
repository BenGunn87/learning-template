"""Deterministic Stage 3 targeted-practice and review operations."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .issues import Issue
from .stage2 import SESSION_PATTERN, Stage2RepositoryMixin
from .yaml_io import YamlFileError, create_yaml, load_yaml, replace_yaml


OUTCOME_ORDER = {"failed": 0, "hard": 1, "good": 2, "easy": 3}
ACTION_FOR_EVIDENCE = {"initial": "study", "practice": "practice", "review": "review"}


class Stage3RepositoryMixin(Stage2RepositoryMixin):
    """Add gap-targeted attempts and derived spaced-review scheduling."""

    def _settings(self) -> dict[str, Any]:
        data = load_yaml(self.path("config/settings.yaml"))
        if not isinstance(data, dict):
            raise YamlFileError("expected a mapping in config/settings.yaml")
        return data

    def _review_settings(self) -> dict[str, Any]:
        settings = self._settings()
        self._raise_issues(self.validate_schema("settings", settings, "config/settings.yaml"))
        return settings["review"]

    @staticmethod
    def _date(value: str | date | None = None) -> date:
        if value is None:
            return datetime.now().astimezone().date()
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value[:10])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid ISO date: {value}") from exc

    @staticmethod
    def calculate_review_outcome(result: dict[str, str]) -> str:
        required = {"recall", "understanding", "application"}
        if set(result) != required or any(value not in OUTCOME_ORDER for value in result.values()):
            raise ValueError("review result must contain recall, understanding, and application grades")
        return min(result.values(), key=OUTCOME_ORDER.__getitem__)

    def calculate_next_review(
        self,
        outcome: str,
        on_date: str | date | None = None,
        previous: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if outcome not in OUTCOME_ORDER:
            raise ValueError(f"unknown review outcome: {outcome}")
        settings = self._review_settings()
        current = self._date(on_date)
        if previous is None:
            interval = settings["initial_intervals"][outcome]
            repetitions = 0
            review = {
                "due": (current + timedelta(days=interval)).isoformat(),
                "interval_days": interval,
                "repetitions": repetitions,
            }
        else:
            interval_days = previous.get("interval_days")
            repetitions = previous.get("repetitions")
            if (
                isinstance(interval_days, bool)
                or not isinstance(interval_days, int)
                or interval_days < 1
                or isinstance(repetitions, bool)
                or not isinstance(repetitions, int)
                or repetitions < 0
            ):
                raise ValueError("previous Review requires a positive interval and non-negative repetitions")
            if outcome == "failed":
                interval = settings["initial_intervals"]["failed"]
            else:
                interval = max(1, math.ceil(interval_days * settings["multipliers"][outcome]))
            review = {
                "last": current.isoformat(),
                "due": (current + timedelta(days=interval)).isoformat(),
                "interval_days": interval,
                "repetitions": repetitions + 1,
            }
        return review

    def validate_session(self, session: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_session(session, relative)
        if isinstance(session, str):
            path = self.path(f"sessions/{session}.yaml")
            try:
                session = load_yaml(path)
            except YamlFileError:
                return issues
        if not isinstance(session, dict):
            return issues
        relative = relative or f"sessions/{session.get('id', '<unknown>')}.yaml"
        known = self._known_unit_ids()
        for section in ("plan", "actual"):
            container = session.get(section)
            if not isinstance(container, dict):
                continue
            for index, action in enumerate(container.get("actions", [])):
                if isinstance(action, dict) and action.get("unit") not in known:
                    issues.append(
                        Issue(relative, f"session references unknown {section} Unit: {action.get('unit')}", f"$.{section}.actions[{index}].unit")
                    )
        return issues

    @staticmethod
    def _evidence_prompts(evidence: dict[str, Any]) -> list[str]:
        if evidence.get("type") == "initial":
            recall = evidence.get("recall", {})
            practice = evidence.get("practice", {})
            return [*recall.get("prompts", []), practice.get("prompt", "")]
        if evidence.get("type") == "practice":
            return [evidence.get("practice", {}).get("prompt", "")]
        if evidence.get("type") == "review":
            return [evidence.get("prompt", "")]
        return []

    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        return " ".join(prompt.casefold().split())

    def validate_evidence(self, evidence: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_evidence(evidence, relative)
        if isinstance(evidence, str):
            matches = self._find_by_id("evidence", evidence)
            if len(matches) != 1:
                return issues
            evidence = matches[0][1]
        if not isinstance(evidence, dict):
            return issues
        relative = relative or f"evidence/{evidence.get('unit', '<unknown>')}/{evidence.get('id', '<unknown>')}.yaml"
        evidence_type = evidence.get("type")
        if evidence_type not in {"practice", "review"}:
            return issues

        based_on = evidence.get("based_on")
        reference_key = "evidence" if evidence_type == "practice" else "previous_evidence"
        reference_id = based_on.get(reference_key) if isinstance(based_on, dict) else None
        reference_matches = self._find_by_id("evidence", reference_id) if isinstance(reference_id, str) else []
        if not reference_matches:
            issues.append(Issue(relative, f"{evidence_type} references unknown Evidence: {reference_id}", f"$.based_on.{reference_key}"))
        elif len(reference_matches) == 1 and reference_matches[0][1].get("unit") != evidence.get("unit"):
            issues.append(Issue(relative, "based-on Evidence belongs to another Unit", f"$.based_on.{reference_key}"))

        session_id = evidence.get("session")
        if isinstance(session_id, str):
            session_path = self.path(f"sessions/{session_id}.yaml")
            if session_path.is_file():
                session = load_yaml(session_path)
                planned = session.get("plan", {}).get("actions", [])
                expected_action = {"type": ACTION_FOR_EVIDENCE[evidence_type], "unit": evidence.get("unit")}
                if expected_action not in planned:
                    issues.append(Issue(relative, f"Evidence is not present in Session plan: {expected_action}"))

        prompt = evidence.get("practice", {}).get("prompt") if evidence_type == "practice" else evidence.get("prompt")
        if isinstance(prompt, str):
            normalized = self._normalize_prompt(prompt)
            previous_documents, _ = self._read_files("evidence")
            previous_prompts = {
                self._normalize_prompt(item)
                for _, document in previous_documents
                if (
                    isinstance(document, dict)
                    and document.get("unit") == evidence.get("unit")
                    and document.get("id") != evidence.get("id")
                )
                for item in self._evidence_prompts(document)
                if item
            }
            if normalized in previous_prompts:
                issues.append(Issue(relative, "prompt must not repeat a previous prompt verbatim", "$.prompt"))
        return issues

    def validate_assessment(self, assessment: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_assessment(assessment, relative)
        if isinstance(assessment, str):
            matches = self._find_by_id("assessments", assessment)
            if len(matches) != 1:
                return issues
            assessment = matches[0][1]
        if not isinstance(assessment, dict):
            return issues
        relative = relative or f"assessments/{assessment.get('evidence', '<unknown>')}/001.yaml"
        evidence_matches = self._find_by_id("evidence", assessment.get("evidence"))
        if len(evidence_matches) == 1 and assessment.get("type") != "reevaluation":
            evidence_type = evidence_matches[0][1].get("type")
            if assessment.get("type") != evidence_type:
                issues.append(Issue(relative, f"Assessment type must match Evidence type: {evidence_type}", "$.type"))
        if assessment.get("type") == "review" and isinstance(assessment.get("result"), dict):
            try:
                expected = self.calculate_review_outcome(assessment["result"])
            except ValueError:
                pass
            else:
                if assessment.get("review_outcome") != expected:
                    issues.append(Issue(relative, f"review_outcome must be {expected}", "$.review_outcome"))
        return issues

    def create_evidence(self, data: Any) -> Path:
        relative = (
            f"evidence/{data.get('unit', '<unknown>')}/{data.get('id', '<unknown>')}.yaml"
            if isinstance(data, dict)
            else "evidence/<unknown>.yaml"
        )
        self._raise_issues(self.validate_evidence(data, relative))
        if isinstance(data, dict):
            evidence_type = data.get("type")
            expected_action = ACTION_FOR_EVIDENCE.get(evidence_type)
            session_id = data.get("session")
            unit_id = data.get("unit")
            if expected_action and isinstance(session_id, str):
                session_path = self.path(f"sessions/{session_id}.yaml")
                if session_path.is_file():
                    planned = load_yaml(session_path).get("plan", {}).get("actions", [])
                    if {"type": expected_action, "unit": unit_id} not in planned:
                        raise ValueError(f"Evidence requires a planned {expected_action} action: {unit_id}")

            if evidence_type in {"practice", "review"} and isinstance(unit_id, str):
                progress = self.read_progress().get(unit_id)
                required_status = "practice" if evidence_type == "practice" else "verified"
                if not progress or progress.get("status") != required_status:
                    raise ValueError(f"{evidence_type.capitalize()} Evidence requires status={required_status}: {unit_id}")
                reference_key = "evidence" if evidence_type == "practice" else "previous_evidence"
                based_on = data.get("based_on")
                reference_id = based_on.get(reference_key) if isinstance(based_on, dict) else None
                if reference_id != progress.get("latest_evidence"):
                    raise ValueError(f"{evidence_type.capitalize()} must be based on the latest Evidence: {progress.get('latest_evidence')}")
                if evidence_type == "review":
                    review = progress.get("review")
                    if not isinstance(review, dict) or self._date(review["due"]) > self._date(data.get("created_at")):
                        raise ValueError(f"Review is not due: {unit_id}")
        return super().create_evidence(data)

    def get_practice_units(self) -> list[dict[str, Any]]:
        self._require_initialized_valid()
        progress = self.read_progress()
        frontier = self.read("frontier")
        frontier_by_id = {unit["id"]: unit for unit in frontier["units"]}
        candidates = []
        for unit_id, item in progress.items():
            if item["status"] != "practice":
                continue
            unit = frontier_by_id.get(unit_id, {})
            weaknesses = [dimension for dimension, grade in item["mastery"].items() if grade in {"failed", "hard"}]
            candidates.append(
                {
                    "id": unit_id,
                    "title": unit.get("title", unit_id),
                    "weaknesses": weaknesses,
                    "latest_evidence": item["latest_evidence"],
                    "estimated_minutes": unit.get("estimated_minutes", 0),
                    "primary_focus": frontier["focus"]["primary"] in unit.get("nodes", []),
                    "priority": unit.get("priority", "medium"),
                }
            )
        candidates.sort(key=lambda item: (not item["primary_focus"], {"high": 0, "medium": 1, "low": 2}[item["priority"]], item["id"]))
        return candidates

    def get_due_reviews(self, on_date: str | date | None = None) -> list[dict[str, Any]]:
        self._require_initialized_valid()
        current = self._date(on_date)
        progress = self.read_progress()
        frontier = self.read("frontier")
        frontier_by_id = {unit["id"]: unit for unit in frontier["units"]}
        candidates = []
        for unit_id, item in progress.items():
            review = item.get("review")
            if item["status"] != "verified" or not isinstance(review, dict):
                continue
            due = self._date(review["due"])
            if due > current:
                continue
            unit = frontier_by_id.get(unit_id, {})
            candidates.append(
                {
                    "id": unit_id,
                    "title": unit.get("title", unit_id),
                    "due": review["due"],
                    "overdue_days": (current - due).days,
                    "interval_days": review["interval_days"],
                    "repetitions": review["repetitions"],
                    "mastery": item["mastery"],
                    "latest_evidence": item["latest_evidence"],
                    "primary_focus": frontier["focus"]["primary"] in unit.get("nodes", []),
                    "priority": unit.get("priority", "medium"),
                }
            )
        candidates.sort(
            key=lambda item: (
                -item["overdue_days"],
                min(OUTCOME_ORDER[grade] for grade in item["mastery"].values()),
                not item["primary_focus"],
                {"high": 0, "medium": 1, "low": 2}[item["priority"]],
                item["id"],
            )
        )
        return candidates

    def plan_session_candidates(self, minutes: int, on_date: str | date | None = None) -> dict[str, Any]:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("time budget must be a positive integer")
        self._require_initialized_valid()
        base = self._candidate_data(minutes)
        practice = self.get_practice_units()
        due = self.get_due_reviews(on_date)
        settings = self._review_settings()
        review_budget = math.floor(minutes * settings["max_session_share"])
        review_minutes = settings["estimated_minutes"]
        review_slots = review_budget // review_minutes
        selected_reviews = due[:review_slots]
        remaining = minutes - len(selected_reviews) * review_minutes

        suggested = [{"type": "review", "unit": item["id"]} for item in selected_reviews]
        available = [item for item in base["candidates"] if item["availability"] == "available"]
        practice_ids = {item["id"] for item in practice}
        main = next((item for item in available if item["id"] in practice_ids and item["estimated_minutes"] <= remaining), None)
        if main is None:
            main = next((item for item in available if item["estimated_minutes"] <= remaining), None)
        if main is not None:
            action_type = "practice" if main["progress"] == "practice" else "study"
            suggested.append({"type": action_type, "unit": main["id"]})

        return {
            **base,
            "review_budget_minutes": review_budget,
            "review_estimated_minutes": review_minutes,
            "practice_units": practice,
            "due_reviews": due,
            "suggested_actions": suggested,
        }

    def session_candidates(self, minutes: int, on_date: str | date | None = None) -> dict[str, Any]:
        return self.plan_session_candidates(minutes, on_date)

    def _infer_action(self, unit_id: str, on_date: str | date | None = None) -> str:
        item = self.read_progress().get(unit_id)
        if not item:
            return "study"
        if item["status"] == "practice":
            return "practice"
        if item["status"] == "learning":
            return "study"
        due_ids = {candidate["id"] for candidate in self.get_due_reviews(on_date)}
        if unit_id in due_ids:
            return "review"
        raise ValueError(f"Unit is verified and its Review is not due: {unit_id}")

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
        for action in actions:
            if not isinstance(action, dict) or action.get("type") not in ACTION_FOR_EVIDENCE.values():
                raise ValueError(f"invalid Session action: {action}")
            action_type, action_unit = action.get("type"), action.get("unit")
            if action_unit not in frontier_ids:
                raise ValueError(f"Unit is not present in Frontier: {action_unit}")
            state = progress.get(action_unit, {}).get("status", "untouched")
            if action_type == "practice" and state != "practice":
                raise ValueError(f"Practice action requires status=practice: {action_unit}")
            if action_type == "review" and action_unit not in due_ids:
                raise ValueError(f"Review action requires a due verified Unit: {action_unit}")
            if action_type == "study" and state == "verified":
                raise ValueError(f"Study action cannot repeat a verified Unit: {action_unit}")

        review_count = sum(action["type"] == "review" for action in actions)
        settings = self._review_settings()
        if review_count * settings["estimated_minutes"] > math.floor(minutes * settings["max_session_share"]):
            raise ValueError("Review actions exceed the configured Session review budget")

        sessions, _ = self._read_files("sessions")
        active = [data.get("id") for _, data in sessions if isinstance(data, dict) and data.get("status") == "active"]
        if active:
            raise ValueError(f"active Session already exists: {', '.join(str(item) for item in active)}")
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
            "plan": {"unit": actions[0]["unit"], "actions": actions},
            "actual": {"unit": None, "actions": []},
            "evidence": [],
            "completed_at": None,
        }
        self._raise_issues(self.validate_session(data, f"sessions/{session_id}.yaml"))
        path = self.path(f"sessions/{session_id}.yaml")
        create_yaml(path, data)
        return path, data

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
            history = sorted(attempts[unit_id], key=lambda pair: (pair[0]["created_at"], pair[0]["id"], pair[1]["id"]))
            review: dict[str, Any] | None = None
            for evidence, assessment in history:
                result = assessment["result"]
                status = self._progress_status(result)
                outcome = self.calculate_review_outcome(result)
                if evidence["type"] == "review":
                    if review is None:
                        review = self.calculate_next_review(outcome, evidence["created_at"][:10])
                    else:
                        review = self.calculate_next_review(outcome, evidence["created_at"][:10], review)
                elif status == "verified":
                    review = self.calculate_next_review(outcome, evidence["created_at"][:10])
            latest_evidence, latest_assessment = history[-1]
            item = {
                "status": self._progress_status(latest_assessment["result"]),
                "attempts": len(history),
                "mastery": dict(latest_assessment["result"]),
                "latest_evidence": latest_evidence["id"],
                "latest_assessment": latest_assessment["id"],
                "last_attempt": latest_evidence["created_at"],
            }
            if review is not None:
                item["review"] = review
            progress[unit_id] = item
        self._raise_issues(self.validate_progress(progress))
        replace_yaml(self.path("progress/units.yaml"), progress)
        return progress

    def complete_session(
        self,
        session_id: str,
        evidence_ids: list[str],
        completed_at: str | None = None,
    ) -> tuple[Path, dict[str, Any], str]:
        self._raise_issues(self.validate_session(session_id))
        path = self.path(f"sessions/{session_id}.yaml")
        session = load_yaml(path)
        if session["status"] == "completed":
            if session["evidence"] == evidence_ids:
                return path, session, "already-completed"
            raise ValueError(f"Session is already completed with different Evidence: {session_id}")
        if not evidence_ids:
            raise ValueError("Session completion requires at least one Evidence id")

        documents = []
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
        actual_actions = [
            {"type": ACTION_FOR_EVIDENCE[evidence["type"]], "unit": evidence["unit"]}
            for evidence in documents
        ]
        for action in actual_actions:
            if action not in session["plan"]["actions"]:
                raise ValueError(f"Completed action was not planned: {action}")
        session["status"] = "completed"
        session["actual"] = {"unit": documents[0]["unit"], "actions": actual_actions}
        session["evidence"] = evidence_ids
        session["completed_at"] = completed_at or self._now()
        self._raise_issues(self.validate_session(session, f"sessions/{session_id}.yaml"))
        replace_yaml(path, session)
        return path, session, "completed"
