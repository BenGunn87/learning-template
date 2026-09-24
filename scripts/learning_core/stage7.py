"""Deterministic Stage 7 append-only Assessment reevaluation operations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .issues import Issue
from .stage5 import STRONG_GRADES, WEAK_GRADES
from .stage6 import Stage6RepositoryMixin
from .yaml_io import YamlFileError, create_yaml, load_yaml, replace_yaml


REEVALUATION_REASONS = {"user_request", "contradiction", "rubric_change"}


class Stage7RepositoryMixin(Stage6RepositoryMixin):
    """Add auditable reevaluation while keeping Evidence immutable."""

    def _assessment_records(
        self,
        extra: tuple[Path, dict[str, Any]] | None = None,
    ) -> list[tuple[Path, dict[str, Any]]]:
        documents, issues = self._read_files("assessments")
        self._raise_issues(issues)
        records = [(path, data) for path, data in documents if isinstance(data, dict)]
        if extra is not None:
            for index, (path, _) in enumerate(records):
                if path == extra[0]:
                    records[index] = extra
                    break
            else:
                records.append(extra)
        return records

    def _assessment_chain_issues(
        self,
        records: list[tuple[Path, dict[str, Any]]],
    ) -> list[Issue]:
        issues: list[Issue] = []
        by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
        duplicates: set[str] = set()
        for path, assessment in records:
            assessment_id = assessment.get("id")
            if not isinstance(assessment_id, str):
                continue
            if assessment_id in by_id:
                duplicates.add(assessment_id)
            else:
                by_id[assessment_id] = (path, assessment)
        for assessment_id in sorted(duplicates):
            issues.append(Issue("assessments", f"duplicate Assessment id: {assessment_id}"))

        children: dict[str, list[str]] = {}
        groups: dict[str, list[str]] = {}
        for path, assessment in records:
            relative = self._relative(path)
            assessment_id = assessment.get("id")
            evidence_id = assessment.get("evidence")
            assessment_type = assessment.get("type")
            if isinstance(evidence_id, str) and isinstance(assessment_id, str):
                groups.setdefault(evidence_id, []).append(assessment_id)

            supersedes = assessment.get("supersedes")
            if assessment_type == "reevaluation":
                if supersedes == assessment_id and isinstance(assessment_id, str):
                    issues.append(Issue(relative, "Assessment cannot supersede itself", "$.supersedes"))
                target = by_id.get(supersedes) if isinstance(supersedes, str) else None
                if target is None and isinstance(supersedes, str):
                    issues.append(
                        Issue(relative, f"reevaluation references unknown Assessment: {supersedes}", "$.supersedes")
                    )
                elif target is not None and target[1].get("evidence") != evidence_id:
                    issues.append(
                        Issue(relative, "reevaluation target belongs to another Evidence", "$.supersedes")
                    )
                if isinstance(supersedes, str) and isinstance(assessment_id, str):
                    children.setdefault(supersedes, []).append(assessment_id)
            elif supersedes is not None:
                issues.append(Issue(relative, "initial Assessment must not have supersedes", "$.supersedes"))

        for target, child_ids in sorted(children.items()):
            if len(child_ids) > 1:
                issues.append(
                    Issue(
                        "assessments",
                        f"Assessment supersedes chain branches at {target}: {', '.join(sorted(child_ids))}",
                    )
                )

        for evidence_id, assessment_ids in sorted(groups.items()):
            group = set(assessment_ids)
            reported_cycles: set[frozenset[str]] = set()
            for start in sorted(group):
                path_positions: dict[str, int] = {}
                path_ids: list[str] = []
                current: str | None = start
                while current is not None and current in group:
                    if current in path_positions:
                        cycle = frozenset(path_ids[path_positions[current] :])
                        if cycle and cycle not in reported_cycles:
                            reported_cycles.add(cycle)
                            issues.append(
                                Issue(
                                    f"assessments/{evidence_id}",
                                    "Assessment supersedes cycle: " + " -> ".join(sorted(cycle)),
                                )
                            )
                        break
                    path_positions[current] = len(path_ids)
                    path_ids.append(current)
                    predecessor = by_id[current][1].get("supersedes")
                    current = predecessor if isinstance(predecessor, str) else None
            roots = [
                assessment_id
                for assessment_id in assessment_ids
                if by_id.get(assessment_id, (None, {}))[1].get("type") != "reevaluation"
            ]
            if len(roots) != 1:
                issues.append(
                    Issue(
                        f"assessments/{evidence_id}",
                        f"Evidence requires exactly one initial Assessment root; found {len(roots)}",
                    )
                )
            superseded = {
                assessment.get("supersedes")
                for _, assessment in records
                if assessment.get("evidence") == evidence_id
                and isinstance(assessment.get("supersedes"), str)
            }
            active = group - superseded
            if len(active) != 1:
                issues.append(
                    Issue(
                        f"assessments/{evidence_id}",
                        f"Evidence requires exactly one active Assessment; found {len(active)}",
                    )
                )
                continue

            tip = next(iter(active))
            chain: list[str] = []
            seen: set[str] = set()
            current: str | None = tip
            while current is not None and current in group:
                if current in seen:
                    issues.append(
                        Issue(f"assessments/{evidence_id}", f"Assessment supersedes cycle includes {current}")
                    )
                    break
                seen.add(current)
                chain.append(current)
                predecessor = by_id[current][1].get("supersedes")
                current = predecessor if isinstance(predecessor, str) else None
            if seen != group:
                missing = ", ".join(sorted(group - seen))
                issues.append(
                    Issue(
                        f"assessments/{evidence_id}",
                        f"Assessment chain is not linear and connected; unreachable: {missing}",
                    )
                )
                continue

            ordered = list(reversed(chain))
            for sequence, assessment_id in enumerate(ordered, start=1):
                path = by_id[assessment_id][0]
                expected = self.path(f"assessments/{evidence_id}/{sequence:03d}.yaml")
                if path != expected:
                    issues.append(
                        Issue(
                            self._relative(path),
                            f"Assessment chain position must use {self._relative(expected)}",
                        )
                    )
        return issues

    @staticmethod
    def _active_by_evidence(
        records: list[tuple[Path, dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        superseded = {
            assessment.get("supersedes")
            for _, assessment in records
            if isinstance(assessment.get("supersedes"), str)
        }
        return {
            assessment["evidence"]: assessment
            for _, assessment in records
            if isinstance(assessment.get("id"), str)
            and isinstance(assessment.get("evidence"), str)
            and assessment["id"] not in superseded
        }

    def active_assessment(self, evidence_id: str) -> dict[str, Any]:
        """Return the deterministic unsuperseded tip for one Evidence chain."""
        records = self._assessment_records()
        relevant = [item for item in records if item[1].get("evidence") == evidence_id]
        if not relevant:
            raise ValueError(f"Evidence has no Assessment: {evidence_id}")
        self._raise_issues(self._assessment_chain_issues(relevant))
        active = self._active_by_evidence(relevant)
        if evidence_id not in active:
            raise ValueError(f"Evidence has no unique active Assessment: {evidence_id}")
        return deepcopy(active[evidence_id])

    def _current_assessment_for_evidence(self, evidence_id: str) -> tuple[Path, dict[str, Any]]:
        active = self.active_assessment(evidence_id)
        matches = self._find_by_id("assessments", active["id"])
        if len(matches) != 1:
            raise ValueError(f"active Assessment cannot be resolved: {active['id']}")
        return matches[0]

    def validate_assessment(self, assessment: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_assessment(assessment, relative)
        if isinstance(assessment, str):
            matches = self._find_by_id("assessments", assessment)
            if len(matches) != 1:
                return issues
            path, assessment = matches[0]
            relative = self._relative(path)
        if not isinstance(assessment, dict):
            return issues
        relative = relative or f"assessments/{assessment.get('evidence', '<unknown>')}/001.yaml"
        if assessment.get("type") == "reevaluation" and assessment.get("reason") not in REEVALUATION_REASONS:
            issues.append(Issue(relative, "invalid reevaluation reason", "$.reason"))
        if assessment.get("type") == "reevaluation" and not isinstance(assessment.get("evaluated"), dict):
            issues.append(
                Issue(
                    relative,
                    "reevaluation Assessment requires evaluated dimension-to-node attribution",
                    "$.evaluated",
                )
            )

        path = self.path(relative)
        try:
            records = self._assessment_records((path, assessment))
        except ValueError:
            return issues
        issues.extend(self._assessment_chain_issues(records))
        unique = {(issue.file, issue.path, issue.message): issue for issue in issues}
        return list(unique.values())

    def validate_stage2_repository(self) -> list[Issue]:
        issues = super().validate_stage2_repository()
        try:
            records = self._assessment_records()
        except ValueError as exc:
            issues.append(Issue("assessments", str(exc)))
            return issues
        issues.extend(self._assessment_chain_issues(records))
        active = self._active_by_evidence(records)
        progress = self.read_progress()
        for unit_id, item in progress.items():
            if not isinstance(item, dict):
                continue
            evidence_id = item.get("latest_evidence")
            assessment_id = item.get("latest_assessment")
            expected = active.get(evidence_id, {}).get("id")
            if isinstance(evidence_id, str) and expected is not None and assessment_id != expected:
                issues.append(
                    Issue(
                        "progress/units.yaml",
                        f"latest_assessment must be active for Evidence {evidence_id}: {expected}",
                        f"$.{unit_id}.latest_assessment",
                    )
                )
        unique = {(issue.file, issue.path, issue.message): issue for issue in issues}
        return list(unique.values())

    def _active_gap_signals(self, gap: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            records = self._assessment_records()
        except ValueError:
            return []
        active_ids = {assessment["id"] for assessment in self._active_by_evidence(records).values()}
        return [
            signal
            for signal in gap.get("signals", [])
            if isinstance(signal, dict) and signal.get("assessment") in active_ids
        ]

    def detect_weak_signals(self, evidence_id: str | None = None) -> list[dict[str, Any]]:
        """Return weak signals only from active Assessment interpretations."""
        records = self._assessment_records()
        self._raise_issues(self._assessment_chain_issues(records))
        active = self._active_by_evidence(records)
        evidence_by_id = self._evidence_by_id()
        signals: list[dict[str, Any]] = []
        for current_evidence, assessment in active.items():
            if evidence_id is not None and current_evidence != evidence_id:
                continue
            evidence = evidence_by_id.get(current_evidence)
            evaluated = assessment.get("evaluated")
            if evidence is None or not isinstance(evaluated, dict):
                continue
            for dimension, evaluation in evaluated.items():
                result = assessment.get("result", {}).get(dimension)
                if result not in WEAK_GRADES or not isinstance(evaluation, dict):
                    continue
                for node_id in evaluation.get("nodes", []):
                    signals.append(
                        {
                            "evidence": current_evidence,
                            "assessment": assessment["id"],
                            "unit": evidence["unit"],
                            "dimension": dimension,
                            "result": result,
                            "node": node_id,
                            "candidate_nodes": [node_id],
                        }
                    )
        signals.sort(key=lambda item: (item["evidence"], item["dimension"], item["node"]))
        return signals

    def _evidence_by_id(self) -> dict[str, dict[str, Any]]:
        documents, issues = self._read_files("evidence")
        self._raise_issues(issues)
        return {
            data["id"]: data
            for _, data in documents
            if isinstance(data, dict) and isinstance(data.get("id"), str)
        }

    @staticmethod
    def _evaluation_includes(assessment: dict[str, Any], node: str, dimension: str) -> bool:
        evaluated = assessment.get("evaluated")
        if not isinstance(evaluated, dict):
            return False
        attribution = evaluated.get(dimension)
        return isinstance(attribution, dict) and node in attribution.get("nodes", [])

    def _expected_gap_status(
        self,
        gap: dict[str, Any],
        records: list[tuple[Path, dict[str, Any]]],
        evidence_by_id: dict[str, dict[str, Any]],
    ) -> str:
        active = self._active_by_evidence(records)
        active_ids = {assessment["id"] for assessment in active.values()}
        active_signals = [
            signal
            for signal in gap.get("signals", [])
            if isinstance(signal, dict) and signal.get("assessment") in active_ids
        ]
        if not active_signals:
            return "invalidated"

        node = gap.get("node")
        dimension = gap.get("dimension")
        signal_evidence = {
            signal.get("evidence")
            for signal in gap.get("signals", [])
            if isinstance(signal, dict)
        }

        def event_key(evidence_id: Any) -> tuple[str, str]:
            evidence = evidence_by_id.get(evidence_id, {})
            return str(evidence.get("created_at", "")), str(evidence_id or "")

        latest_weak = max(event_key(signal.get("evidence")) for signal in active_signals)
        resolvers = [
            assessment
            for evidence_id, assessment in active.items()
            if evidence_id not in signal_evidence
            and self._evaluation_includes(assessment, node, dimension)
            and assessment.get("result", {}).get(dimension) in STRONG_GRADES
        ]
        if resolvers:
            latest_resolver = max(event_key(assessment.get("evidence")) for assessment in resolvers)
            if latest_resolver > latest_weak:
                return "resolved"
        independent = {signal.get("evidence") for signal in active_signals}
        return "confirmed" if len(independent) >= 2 else "detected"

    def validate_gap(self, gap: Any, relative: str | None = None) -> list[Issue]:
        issues = super().validate_gap(gap, relative)
        if isinstance(gap, str):
            path = self.path(f"gaps/{gap}.yaml")
            try:
                gap = load_yaml(path)
            except YamlFileError:
                return issues
            relative = self._relative(path)
        if not isinstance(gap, dict):
            return issues
        relative = relative or f"gaps/{gap.get('id', '<unknown>')}.yaml"
        try:
            records = self._assessment_records()
            chain_issues = self._assessment_chain_issues(records)
            if not chain_issues and gap.get("signals"):
                expected = self._expected_gap_status(gap, records, self._evidence_by_id())
                if gap.get("status") != expected:
                    issues.append(
                        Issue(
                            relative,
                            f"Gap status is inconsistent with active Assessment signals; expected {expected}",
                            "$.status",
                        )
                    )
        except (ValueError, YamlFileError):
            pass
        unique = {(issue.file, issue.path, issue.message): issue for issue in issues}
        return list(unique.values())

    def _project_progress(
        self,
        records: list[tuple[Path, dict[str, Any]]],
    ) -> dict[str, Any]:
        evidence_by_id = self._evidence_by_id()
        active = self._active_by_evidence(records)
        attempts: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
        for evidence_id, assessment in active.items():
            evidence = evidence_by_id.get(evidence_id)
            if evidence is not None:
                attempts.setdefault(evidence["unit"], []).append((evidence, assessment))

        progress: dict[str, Any] = {}
        for unit_id in sorted(attempts):
            history = sorted(
                attempts[unit_id],
                key=lambda pair: (pair[0]["created_at"], pair[0]["id"]),
            )
            review: dict[str, Any] | None = None
            for evidence, assessment in history:
                result = assessment["result"]
                status = self._progress_status(result)
                outcome = self.calculate_review_outcome(result)
                if evidence["type"] == "review":
                    review = self.calculate_next_review(
                        outcome,
                        evidence["created_at"][:10],
                        review,
                    )
                elif status == "verified":
                    review = self.calculate_next_review(outcome, evidence["created_at"][:10])
            latest_evidence, latest_assessment = history[-1]
            item: dict[str, Any] = {
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
        return progress

    def rebuild_progress(self) -> dict[str, Any]:
        records = self._assessment_records()
        self._raise_issues(self._assessment_chain_issues(records))
        boundary_issues: list[Issue] = []
        for path, assessment in records:
            boundary_issues.extend(self._assessment_node_boundary_issues(assessment, self._relative(path)))
        self._raise_issues(boundary_issues)
        progress = self._project_progress(records)
        self._raise_issues(self.validate_schema("progress", progress, "progress/units.yaml"))
        replace_yaml(self.path("progress/units.yaml"), progress)
        return progress

    def _project_gaps(
        self,
        records: list[tuple[Path, dict[str, Any]]],
        reevaluation: dict[str, Any],
    ) -> tuple[dict[Path, dict[str, Any]], list[dict[str, str]]]:
        gap_documents, read_issues = self._read_files("gaps")
        self._raise_issues(read_issues)
        projected = {
            path: deepcopy(gap)
            for path, gap in gap_documents
            if isinstance(gap, dict)
        }
        evidence_by_id = self._evidence_by_id()
        evidence = evidence_by_id[reevaluation["evidence"]]
        evaluated = reevaluation.get("evaluated", {})
        for dimension, attribution in evaluated.items():
            if not isinstance(attribution, dict):
                continue
            result = reevaluation.get("result", {}).get(dimension)
            if result not in WEAK_GRADES:
                continue
            for node in attribution.get("nodes", []):
                existing = next(
                    (
                        (path, gap)
                        for path, gap in projected.items()
                        if gap.get("node") == node and gap.get("dimension") == dimension
                    ),
                    None,
                )
                signal = {
                    "evidence": evidence["id"],
                    "assessment": reevaluation["id"],
                    "result": result,
                    "observed_nodes": [node],
                }
                if existing is None:
                    gap_id = self._gap_id(node, dimension)
                    path = self.path(f"gaps/{gap_id}.yaml")
                    projected[path] = {
                        "format_version": 1,
                        "id": gap_id,
                        "created_at": reevaluation["created_at"],
                        "node": node,
                        "dimension": dimension,
                        "status": "detected",
                        "scope": "local",
                        "routing_impact": self._routing_impact_for(node, "detected"),
                        "signals": [signal],
                        "history": [
                            {
                                "status": "detected",
                                "at": reevaluation["created_at"],
                                "assessment": reevaluation["id"],
                                "reason": "reevaluation",
                            }
                        ],
                        "resolved_at": None,
                    }
                else:
                    _, gap = existing
                    if not any(item.get("assessment") == reevaluation["id"] for item in gap["signals"]):
                        gap["signals"].append(signal)

        changes: list[dict[str, str]] = []
        for path, gap in projected.items():
            old_matches = [
                old
                for old_path, old in gap_documents
                if old_path == path and isinstance(old, dict)
            ]
            old_status = old_matches[0].get("status") if old_matches else None
            new_status = self._expected_gap_status(gap, records, evidence_by_id)
            gap["status"] = new_status
            gap["resolved_at"] = (
                gap.get("resolved_at")
                if new_status == old_status == "resolved"
                else reevaluation["created_at"] if new_status == "resolved" else None
            )
            gap["routing_impact"] = self._routing_impact_for(
                gap["node"], new_status, gap.get("routing_impact")
            )
            if old_status is not None and new_status != old_status:
                gap["history"].append(
                    {
                        "status": new_status,
                        "at": reevaluation["created_at"],
                        "assessment": reevaluation["id"],
                        "reason": "reevaluation",
                    }
                )
            if old_status != new_status:
                changes.append(
                    {
                        "gap": gap["id"],
                        "from": old_status or "absent",
                        "to": new_status,
                    }
                )
        return projected, changes

    def _projected_gap_issues(
        self,
        projected: dict[Path, dict[str, Any]],
        records: list[tuple[Path, dict[str, Any]]],
    ) -> list[Issue]:
        issues: list[Issue] = []
        by_id = {assessment.get("id"): assessment for _, assessment in records}
        active_ids = {assessment["id"] for assessment in self._active_by_evidence(records).values()}
        evidence_by_id = self._evidence_by_id()
        allowed_transitions = {
            "detected": {"confirmed", "resolved", "invalidated"},
            "confirmed": {"detected", "resolved", "invalidated"},
            "resolved": {"detected", "confirmed", "invalidated"},
            "invalidated": {"detected", "confirmed", "resolved"},
        }
        for path, gap in projected.items():
            relative = self._relative(path)
            issues.extend(self.validate_schema("gap", gap, relative))
            for index, signal in enumerate(gap.get("signals", [])):
                assessment = by_id.get(signal.get("assessment")) if isinstance(signal, dict) else None
                if assessment is None:
                    issues.append(Issue(relative, "signal references unknown Assessment", f"$.signals[{index}].assessment"))
                    continue
                if assessment.get("evidence") != signal.get("evidence"):
                    issues.append(Issue(relative, "signal Assessment belongs to another Evidence", f"$.signals[{index}]"))
                dimension = gap.get("dimension")
                if signal.get("result") != assessment.get("result", {}).get(dimension):
                    issues.append(Issue(relative, "signal result does not match its Assessment", f"$.signals[{index}].result"))
            active_signals = [
                signal
                for signal in gap.get("signals", [])
                if signal.get("assessment") in active_ids
            ]
            independent = {signal.get("evidence") for signal in active_signals}
            status = gap.get("status")
            if status == "detected" and len(independent) != 1:
                issues.append(Issue(relative, "status=detected requires one active weak signal", "$.signals"))
            if status == "confirmed" and len(independent) < 2:
                issues.append(Issue(relative, "status=confirmed requires two active weak signals", "$.signals"))
            if status == "invalidated" and independent:
                issues.append(Issue(relative, "status=invalidated requires no active weak signals", "$.signals"))
            expected = self._expected_gap_status(gap, records, evidence_by_id)
            if status != expected:
                issues.append(Issue(relative, f"projected Gap status must be {expected}", "$.status"))
            history = gap.get("history", [])
            for index in range(1, len(history)):
                previous = history[index - 1].get("status")
                current = history[index].get("status")
                if current not in allowed_transitions.get(previous, set()):
                    issues.append(Issue(relative, f"invalid Gap transition: {previous} -> {current}", f"$.history[{index}].status"))
        return issues

    def rebuild_frontier(self) -> dict[str, Any]:
        current = self.read("frontier")
        if not isinstance(current, dict):
            raise ValueError("Frontier can only be rebuilt in an initialized repository")
        gap_documents, issues = self._read_files("gaps")
        self._raise_issues(issues)
        gaps = {
            path: gap
            for path, gap in gap_documents
            if isinstance(gap, dict)
        }
        frontier = self._project_frontier_document(current, gaps)
        self._raise_issues(self.validate_frontier(frontier, self.read("graph")))
        replace_yaml(self.path("map/frontier.yaml"), frontier)
        return frontier

    def create_assessment(self, data: Any) -> Path:
        if isinstance(data, dict) and data.get("type") == "reevaluation":
            result = self.reevaluate_assessment(data)
            return self.path(result["created"])
        return super().create_assessment(data)

    def reevaluate_assessment(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("type") != "reevaluation":
            raise ValueError("reevaluation input must be an Assessment with type=reevaluation")
        target_id = data.get("supersedes")
        target_matches = self._find_by_id("assessments", target_id) if isinstance(target_id, str) else []
        if len(target_matches) != 1:
            raise ValueError(f"reevaluation target must exist exactly once: {target_id}")
        _, target = target_matches[0]
        if target.get("evidence") != data.get("evidence"):
            raise ValueError("reevaluation target belongs to another Evidence")
        active_before = self.active_assessment(data["evidence"])
        if active_before.get("id") != target_id:
            raise ValueError(f"reevaluation target is not active: {target_id}")

        existing = [
            item
            for item in self._assessment_records()
            if item[1].get("evidence") == data.get("evidence")
        ]
        assessment_path = self.path(
            f"assessments/{data['evidence']}/{len(existing) + 1:03d}.yaml"
        )
        relative = self._relative(assessment_path)
        self._raise_issues(self.validate_assessment(data, relative))
        records = self._assessment_records((assessment_path, data))
        self._raise_issues(self._assessment_chain_issues(records))

        progress = self._project_progress(records)
        self._raise_issues(self.validate_schema("progress", progress, "progress/units.yaml"))
        gaps, gap_changes = self._project_gaps(records, data)
        self._raise_issues(self._projected_gap_issues(gaps, records))
        frontier = self._project_frontier_document(self.read("frontier"), gaps)
        gaps_by_id = {gap["id"]: gap for gap in gaps.values()}
        self._raise_issues(self.validate_frontier(frontier, self.read("graph"), gaps_by_id))

        progress_path = self.path("progress/units.yaml")
        writes: list[tuple[Path, dict[str, Any], bool, Any]] = [
            (assessment_path, data, True, None),
            (
                progress_path,
                progress,
                not progress_path.exists(),
                deepcopy(self.read_progress()) if progress_path.exists() else None,
            ),
        ]
        for path, gap in gaps.items():
            writes.append((path, gap, not path.exists(), load_yaml(path) if path.exists() else None))
        frontier_path = self.path("map/frontier.yaml")
        writes.append((frontier_path, frontier, False, self.read("frontier")))

        completed: list[tuple[Path, bool, Any]] = []
        try:
            for path, document, create, previous in writes:
                if create:
                    create_yaml(path, document)
                else:
                    replace_yaml(path, document)
                completed.append((path, create, previous))
        except Exception:
            rollback_errors: list[str] = []
            for path, created, previous in reversed(completed):
                try:
                    if created:
                        path.unlink(missing_ok=True)
                    else:
                        replace_yaml(path, previous)
                except Exception as rollback_error:  # pragma: no cover - catastrophic filesystem failure
                    rollback_errors.append(f"{path}: {rollback_error}")
            if rollback_errors:
                raise YamlFileError(
                    "reevaluation failed and rollback was incomplete: " + "; ".join(rollback_errors)
                )
            raise

        return {
            "created": relative,
            "old_assessment": target["id"],
            "new_assessment": data["id"],
            "reason": data["reason"],
            "effects": {
                "progress_updated": True,
                "gap_changes": gap_changes,
                "frontier_rebuilt": True,
            },
        }
