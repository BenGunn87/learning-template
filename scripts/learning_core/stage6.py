"""Deterministic Stage 6 resource, Study Mode, and discussion state operations."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .issues import Issue
from .stage5 import Stage5RepositoryMixin
from .yaml_io import YamlFileError, create_text, load_yaml, load_yaml_text


STUDY_MODES = {"external", "generated", "hybrid"}
RESOURCE_ID_PATTERN = re.compile(r"^resource-[a-z0-9]+(?:-[a-z0-9]+)*$")


class Stage6RepositoryMixin(Stage5RepositoryMixin):
    """Add generated Primary Resources and per-attempt Study Mode state."""

    def _stage6_records_required(self) -> bool:
        try:
            learning = self.read("learning")
            version = learning.get("learning_core", {}).get("version", "0.0.0")
            return tuple(int(part) for part in version.split(".")) >= (0, 6, 0)
        except (AttributeError, TypeError, ValueError, YamlFileError):
            return False

    @staticmethod
    def _parse_generated_document(content: str, relative: str) -> tuple[Any, str, list[Issue]]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return None, "", [Issue(relative, "generated Resource must start with YAML frontmatter")]
        try:
            closing = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
        except StopIteration:
            return None, "", [Issue(relative, "generated Resource frontmatter is not closed")]
        try:
            metadata = load_yaml_text("\n".join(lines[1:closing]))
        except YamlFileError as exc:
            return None, "", [Issue(relative, str(exc), "$.frontmatter")]
        body = "\n".join(lines[closing + 1 :]).strip()
        issues = [] if body else [Issue(relative, "generated Resource Markdown body must not be empty", "$.body")]
        return metadata, body, issues

    def _validate_generated_document(self, content: str, relative: str) -> list[Issue]:
        metadata, _, issues = self._parse_generated_document(content, relative)
        issues.extend(self.validate_schema("resource", metadata, relative))
        if not isinstance(metadata, dict):
            return issues

        resource_id = metadata.get("id")
        expected = Path("resources/generated") / f"{resource_id}.md"
        if relative.startswith("resources/generated/") and Path(relative) != expected:
            issues.append(Issue(relative, f"generated Resource path must be {expected}"))

        unit_id = metadata.get("unit")
        if isinstance(unit_id, str) and not self.path(f"units/{unit_id}.yaml").is_file():
            issues.append(Issue(relative, f"generated Resource references unknown Unit: {unit_id}", "$.unit"))

        session_id = metadata.get("session")
        if isinstance(session_id, str):
            session_path = self.path(f"sessions/{session_id}.yaml")
            if not session_path.is_file():
                issues.append(Issue(relative, f"generated Resource references unknown Session: {session_id}", "$.session"))
            else:
                try:
                    session = load_yaml(session_path)
                except YamlFileError:
                    session = None
                planned = session.get("plan", {}).get("actions", []) if isinstance(session, dict) else []
                if {"type": "study", "unit": unit_id} not in planned:
                    issues.append(Issue(relative, "generated Resource Session does not plan its Unit for study", "$.session"))

        try:
            graph = self.read("graph")
            graph_ids = {
                node.get("id")
                for node in graph.get("nodes", [])
                if isinstance(node, dict) and isinstance(node.get("id"), str)
            }
            for index, node_id in enumerate(metadata.get("coverage", [])):
                if node_id not in graph_ids:
                    issues.append(Issue(relative, f"generated Resource covers unknown node: {node_id}", f"$.coverage[{index}]"))
        except (AttributeError, YamlFileError):
            pass
        return issues

    def validate_generated_resource(self, resource_id: str) -> list[Issue]:
        if not RESOURCE_ID_PATTERN.fullmatch(resource_id):
            return [Issue("resources/generated", f"invalid generated Resource id: {resource_id}")]
        path = self.path(f"resources/generated/{resource_id}.md")
        relative = self._relative(path)
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return [Issue(relative, f"unknown generated Resource: {resource_id}")]
        except OSError as exc:
            return [Issue(relative, f"cannot read {path}: {exc}")]
        return self._validate_generated_document(content, relative)

    def _generated_metadata(self, reference: dict[str, Any]) -> tuple[Any, list[Issue]]:
        relative = str(reference.get("path", "resources/generated/<unknown>.md"))
        path = self.path(relative)
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None, [Issue(relative, "referenced generated Resource does not exist")]
        except OSError as exc:
            return None, [Issue(relative, f"cannot read {path}: {exc}")]
        metadata, _, _ = self._parse_generated_document(content, relative)
        issues = self._validate_generated_document(content, relative)
        return metadata, issues

    def _validate_resource_references(
        self,
        resources: Any,
        relative: str,
        path_prefix: str,
        *,
        unit_id: Any,
        session_id: Any,
    ) -> list[Issue]:
        if not isinstance(resources, list):
            return []
        issues: list[Issue] = []
        identities: set[tuple[Any, Any]] = set()
        for index, resource in enumerate(resources):
            if not isinstance(resource, dict):
                continue
            resource_type = resource.get("type")
            identity = (
                resource_type,
                resource.get("url") if resource_type == "external" else resource.get("id"),
            )
            if identity in identities:
                issues.append(Issue(relative, "duplicate Resource reference", f"{path_prefix}[{index}]"))
            identities.add(identity)
            if resource_type != "generated":
                continue
            if not isinstance(resource.get("id"), str) or not RESOURCE_ID_PATTERN.fullmatch(resource["id"]):
                continue
            expected_path = f"resources/generated/{resource.get('id')}.md"
            if resource.get("path") != expected_path:
                issues.append(Issue(relative, f"generated Resource path must be {expected_path}", f"{path_prefix}[{index}].path"))
                continue
            metadata, resource_issues = self._generated_metadata(resource)
            issues.extend(resource_issues)
            if not isinstance(metadata, dict):
                continue
            comparisons = {
                "id": resource.get("id"),
                "title": resource.get("title"),
                "unit": unit_id,
                "session": session_id,
                "format": resource.get("format"),
            }
            for field, expected in comparisons.items():
                if expected is not None and metadata.get(field) != expected:
                    issues.append(
                        Issue(
                            relative,
                            f"generated Resource {field} does not match its document",
                            f"{path_prefix}[{index}].{field if field in resource else 'path'}",
                        )
                    )
        return issues

    @staticmethod
    def _resource_identity(resource: dict[str, Any]) -> tuple[Any, Any]:
        resource_type = resource.get("type")
        return resource_type, resource.get("url") if resource_type == "external" else resource.get("id")

    @staticmethod
    def _mode_resource_issues(mode: Any, resources: Any, relative: str, path: str, complete: bool) -> list[Issue]:
        if mode not in STUDY_MODES or not isinstance(resources, list):
            return []
        types = [item.get("type") for item in resources if isinstance(item, dict)]
        issues: list[Issue] = []
        if len(types) != len(set(types)):
            issues.append(Issue(relative, "Study Mode may use at most one Resource of each type", path))
        expected = {"external"} if mode == "external" else {"generated"} if mode == "generated" else {"external", "generated"}
        if any(item not in expected for item in types):
            issues.append(Issue(relative, f"resources are inconsistent with study mode {mode}", path))
        if complete and set(types) != expected:
            issues.append(Issue(relative, f"completed study mode {mode} requires {', '.join(sorted(expected))} Resource(s)", path))
        return issues

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
        session_id = session.get("id")

        plan_actions = session.get("plan", {}).get("actions", [])
        actual_actions = session.get("actual", {}).get("actions", [])
        plan_studies = sum(
            isinstance(action, dict) and action.get("type") == "study"
            for action in plan_actions
        ) if isinstance(plan_actions, list) else 0
        actual_studies = sum(
            isinstance(action, dict) and action.get("type") == "study"
            for action in actual_actions
        ) if isinstance(actual_actions, list) else 0
        if max(plan_studies, actual_studies) > 1:
            path = "$.plan.actions" if plan_studies > 1 else "$.actual.actions"
            issues.append(
                Issue(
                    relative,
                    "the current Session model supports only one Study attempt per Session",
                    path,
                )
            )

        study = session.get("study")
        if isinstance(study, dict):
            used = study.get("resources")
            complete = session.get("status") == "completed" and any(
                action.get("type") == "study" and action.get("status") == "completed"
                for action in session.get("actual", {}).get("actions", [])
                if isinstance(action, dict)
            )
            issues.extend(self._mode_resource_issues(study.get("mode"), used, relative, "$.study.resources", complete))
            study_units = [
                action.get("unit")
                for action in session.get("actual", {}).get("actions", [])
                if isinstance(action, dict) and action.get("type") == "study"
            ]
            unit_id = study_units[0] if len(study_units) == 1 else session.get("plan", {}).get("unit")
            issues.extend(
                self._validate_resource_references(
                    used,
                    relative,
                    "$.study.resources",
                    unit_id=unit_id,
                    session_id=session_id,
                )
            )

        checkpoint = session.get("checkpoint")
        if isinstance(checkpoint, dict) and "study_mode" in checkpoint:
            mode = checkpoint.get("study_mode")
            resources = checkpoint.get("resources")
            if checkpoint.get("action") != "study":
                issues.append(Issue(relative, "study_mode is only valid for a study checkpoint", "$.checkpoint.study_mode"))
            if not isinstance(resources, list):
                issues.append(Issue(relative, "canonical study checkpoint requires resources", "$.checkpoint.resources"))
            else:
                issues.extend(self._mode_resource_issues(mode, resources, relative, "$.checkpoint.resources", False))
                issues.extend(
                    self._validate_resource_references(
                        resources,
                        relative,
                        "$.checkpoint.resources",
                        unit_id=checkpoint.get("unit"),
                        session_id=session_id,
                    )
                )
                completed = [item for item in resources if isinstance(item, dict) and item.get("status") == "completed"]
                used = study.get("resources", []) if isinstance(study, dict) else []
                if [self._resource_identity(item) for item in completed] != [self._resource_identity(item) for item in used]:
                    issues.append(Issue(relative, "Session study resources must equal completed checkpoint resources", "$.study.resources"))
            if isinstance(study, dict) and study.get("mode") != mode:
                issues.append(Issue(relative, "Session and checkpoint Study Modes must match", "$.study.mode"))
            summary = checkpoint.get("discussion_summary")
            if summary is not None and (not isinstance(study, dict) or study.get("discussion_summary") != summary):
                issues.append(Issue(relative, "Session discussion_summary must match checkpoint", "$.study.discussion_summary"))
        return issues

    def validate_evidence(self, evidence: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_evidence(evidence, relative)
        if isinstance(evidence, str):
            matches = self._find_by_id("evidence", evidence)
            if len(matches) != 1:
                return issues
            _, evidence = matches[0]
        if not isinstance(evidence, dict):
            return issues
        relative = relative or f"evidence/{evidence.get('unit', '<unknown>')}/{evidence.get('id', '<unknown>')}.yaml"
        resources = evidence.get("resources")
        if isinstance(resources, list):
            issues.extend(
                self._validate_resource_references(
                    resources,
                    relative,
                    "$.resources",
                    unit_id=evidence.get("unit"),
                    session_id=evidence.get("session"),
                )
            )
            session_path = self.path(f"sessions/{evidence.get('session')}.yaml")
            if session_path.is_file():
                try:
                    session = load_yaml(session_path)
                except YamlFileError:
                    session = None
                study = session.get("study") if isinstance(session, dict) else None
                used = study.get("resources", []) if isinstance(study, dict) else []
                if [self._resource_identity(item) for item in resources if isinstance(item, dict)] != [
                    self._resource_identity(item) for item in used if isinstance(item, dict)
                ]:
                    issues.append(Issue(relative, "Evidence resources must match the Session's studied resources", "$.resources"))
                if isinstance(study, dict):
                    issues.extend(self._mode_resource_issues(study.get("mode"), resources, relative, "$.resources", True))
        return issues

    def validate_stage2_repository(self) -> list[Issue]:
        issues = super().validate_stage2_repository()
        generated = self.path("resources/generated")
        if self._stage6_records_required() and not generated.is_dir():
            issues.append(Issue("resources/generated", "required Stage 6 directory is missing"))
            return issues
        ids: dict[str, list[str]] = {}
        if generated.is_dir():
            for path in sorted(generated.glob("*.md")):
                relative = self._relative(path)
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError as exc:
                    issues.append(Issue(relative, f"cannot read {path}: {exc}"))
                    continue
                metadata, _, _ = self._parse_generated_document(content, relative)
                issues.extend(self._validate_generated_document(content, relative))
                if isinstance(metadata, dict) and isinstance(metadata.get("id"), str):
                    ids.setdefault(metadata["id"], []).append(relative)
        for resource_id, paths in ids.items():
            if len(paths) > 1:
                issues.append(Issue("resources/generated", f"duplicate generated Resource id {resource_id}: {', '.join(paths)}"))
        return issues

    def _apply_checkpoint(
        self,
        session: dict[str, Any],
        checkpoint: dict[str, Any],
        updated_at: str,
        action_status: str,
    ) -> None:
        existing_study = session.get("study")
        existing_summary = (
            deepcopy(existing_study.get("discussion_summary"))
            if isinstance(existing_study, dict) and isinstance(existing_study.get("discussion_summary"), dict)
            else None
        )
        super()._apply_checkpoint(session, checkpoint, updated_at, action_status)
        if checkpoint.get("action") != "study" or "study_mode" not in checkpoint:
            return
        resources = checkpoint.get("resources", [])
        completed = [deepcopy(item) for item in resources if isinstance(item, dict) and item.get("status") == "completed"]
        if not completed:
            session.pop("study", None)
            return
        study: dict[str, Any] = {"mode": checkpoint["study_mode"], "resources": completed}
        if isinstance(checkpoint.get("discussion_summary"), dict):
            study["discussion_summary"] = deepcopy(checkpoint["discussion_summary"])
        elif existing_summary is not None:
            study["discussion_summary"] = existing_summary
        session["study"] = study

    def update_checkpoint(
        self,
        session_id: str,
        checkpoint: dict[str, Any],
        updated_at: str | None = None,
        action_status: str = "in_progress",
    ) -> tuple[Path, dict[str, Any], str]:
        if self._stage6_records_required() and checkpoint.get("action") == "study":
            session_path = self.path(f"sessions/{session_id}.yaml")
            session = load_yaml(session_path)
            existing = session.get("checkpoint")
            continuing_legacy = isinstance(existing, dict) and "resource" in existing and "study_mode" not in existing
            if not continuing_legacy and ("study_mode" not in checkpoint or not isinstance(checkpoint.get("resources"), list)):
                raise ValueError("new Stage 6 study checkpoint requires study_mode and resources")
        return super().update_checkpoint(session_id, checkpoint, updated_at, action_status)

    def create_evidence(self, data: Any) -> Path:
        if (
            self._stage6_records_required()
            and isinstance(data, dict)
            and data.get("type") == "initial"
            and not isinstance(data.get("resources"), list)
        ):
            raise ValueError("new Stage 6 initial Evidence requires resources")
        return super().create_evidence(data)

    def create_generated_resource(self, content: str) -> tuple[Path, str]:
        metadata, _, parse_issues = self._parse_generated_document(content, "resources/generated/<input>.md")
        self._raise_issues(parse_issues)
        if not isinstance(metadata, dict) or not isinstance(metadata.get("id"), str):
            raise ValueError("generated Resource frontmatter requires an id")
        resource_id = metadata["id"]
        relative = f"resources/generated/{resource_id}.md"
        path = self.path(relative)
        self._raise_issues(self._validate_generated_document(content, relative))
        if path.exists():
            if path.read_text(encoding="utf-8") == content:
                return path, "reused"
            raise ValueError(f"refusing to overwrite generated Resource: {resource_id}")
        create_text(path, content)
        return path, "created"
