"""Stage 5 adaptive routing, persistent gaps, and user interests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .issues import Issue
from .stage4 import Stage4RepositoryMixin
from .yaml_io import YamlFileError, create_yaml, load_yaml, replace_yaml


WEAK_GRADES = {"failed", "hard"}
STRONG_GRADES = {"good", "easy"}
GAP_STATUSES = {"detected", "confirmed", "resolved"}
INTEREST_TRANSITIONS = {
    "pending": {"active", "dismissed"},
    "active": {"satisfied", "dismissed"},
    "satisfied": set(),
    "dismissed": set(),
}


class Stage5RepositoryMixin(Stage4RepositoryMixin):
    """Add Primary Gap/Interest data without changing earlier-stage models."""

    def _graph_node_ids(self) -> set[str]:
        graph = self.read("graph")
        return {
            node["id"]
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }

    def _frontier_reason_references(self) -> tuple[set[str], set[str]]:
        frontier = self.read("frontier")
        gaps: set[str] = set()
        interests: set[str] = set()
        for unit in frontier.get("units", []):
            if not isinstance(unit, dict):
                continue
            for reason in unit.get("routing_reasons", []):
                if not isinstance(reason, dict):
                    continue
                if reason.get("type") == "gap" and isinstance(reason.get("gap"), str):
                    gaps.add(reason["gap"])
                if reason.get("type") == "interest" and isinstance(reason.get("interest"), str):
                    interests.add(reason["interest"])
        return gaps, interests

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
        try:
            known_nodes = self._graph_node_ids()
        except (YamlFileError, AttributeError):
            return issues
        for index, node_id in enumerate(assessment.get("observed_nodes", [])):
            if node_id not in known_nodes:
                issues.append(Issue(relative, f"Assessment references unknown observed node: {node_id}", f"$.observed_nodes[{index}]"))
        return issues

    def validate_gap(self, gap: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(gap, str):
            path = self.path(f"gaps/{gap}.yaml")
            relative = self._relative(path)
            try:
                gap = load_yaml(path)
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]
        relative = relative or (
            f"gaps/{gap.get('id', '<unknown>')}.yaml" if isinstance(gap, dict) else "gaps/<unknown>.yaml"
        )
        issues = self.validate_schema("gap", gap, relative)
        if not isinstance(gap, dict):
            return issues

        gap_id = gap.get("id")
        if isinstance(gap_id, str) and relative.startswith("gaps/") and Path(relative).name != f"{gap_id}.yaml":
            issues.append(Issue(relative, "file name must match Gap id"))
        node = gap.get("node")
        try:
            known_nodes = self._graph_node_ids()
        except (YamlFileError, AttributeError):
            known_nodes = set()
        if isinstance(node, str) and known_nodes and node not in known_nodes:
            issues.append(Issue(relative, f"gap references unknown node: {node}", "$.node"))

        signals = gap.get("signals", [])
        evidence_ids: list[str] = []
        for index, signal in enumerate(signals):
            if not isinstance(signal, dict):
                continue
            evidence_id = signal.get("evidence")
            assessment_id = signal.get("assessment")
            if isinstance(evidence_id, str):
                evidence_ids.append(evidence_id)
                if len(self._find_by_id("evidence", evidence_id)) != 1:
                    issues.append(Issue(relative, f"signal references unknown Evidence: {evidence_id}", f"$.signals[{index}].evidence"))
            assessment_matches = self._find_by_id("assessments", assessment_id) if isinstance(assessment_id, str) else []
            if len(assessment_matches) != 1:
                issues.append(Issue(relative, f"signal references unknown Assessment: {assessment_id}", f"$.signals[{index}].assessment"))
            else:
                assessment = assessment_matches[0][1]
                if assessment.get("evidence") != evidence_id:
                    issues.append(Issue(relative, "signal Assessment belongs to another Evidence", f"$.signals[{index}]"))
            for node_index, observed in enumerate(signal.get("observed_nodes", [])):
                if known_nodes and observed not in known_nodes:
                    issues.append(Issue(relative, f"signal references unknown node: {observed}", f"$.signals[{index}].observed_nodes[{node_index}]"))

        if len(evidence_ids) != len(set(evidence_ids)):
            issues.append(Issue(relative, "Gap signals must use independent Evidence", "$.signals"))
        status = gap.get("status")
        if status == "detected" and len(set(evidence_ids)) != 1:
            issues.append(Issue(relative, "status=detected requires exactly one independent weak signal", "$.signals"))
        if status in {"confirmed", "resolved"} and len(set(evidence_ids)) < 2:
            issues.append(Issue(relative, f"status={status} requires two independent weak signals", "$.signals"))
        if gap.get("routing_impact") == "blocking" and status != "confirmed":
            issues.append(Issue(relative, "only a confirmed Gap may be blocking", "$.routing_impact"))
        if isinstance(node, str) and status == "confirmed":
            try:
                has_dependents = bool(self.prerequisite_impact(node)["dependent_units"])
            except (ValueError, YamlFileError, AttributeError):
                has_dependents = False
            if has_dependents and gap.get("routing_impact") != "blocking":
                issues.append(Issue(relative, "confirmed prerequisite Gap must be blocking", "$.routing_impact"))
            if not has_dependents and gap.get("routing_impact") == "blocking":
                issues.append(Issue(relative, "blocking Gap has no dependent Frontier Unit", "$.routing_impact"))
        history = gap.get("history", [])
        if history and isinstance(history[0], dict) and history[0].get("status") != "detected":
            issues.append(Issue(relative, "Gap history must start with detected", "$.history[0].status"))
        if history and isinstance(history[-1], dict) and history[-1].get("status") != status:
            issues.append(Issue(relative, "latest history status must match Gap status", "$.history"))
        allowed_transitions = {"detected": {"confirmed"}, "confirmed": {"resolved"}, "resolved": {"confirmed"}}
        for index in range(1, len(history)):
            previous = history[index - 1].get("status") if isinstance(history[index - 1], dict) else None
            current = history[index].get("status") if isinstance(history[index], dict) else None
            if current not in allowed_transitions.get(previous, set()):
                issues.append(Issue(relative, f"invalid Gap transition: {previous} -> {current}", f"$.history[{index}].status"))
        if gap.get("scope") == "local" and isinstance(node, str):
            for index, signal in enumerate(signals):
                if isinstance(signal, dict) and node not in signal.get("observed_nodes", []):
                    issues.append(Issue(relative, "local Gap signal must observe the Gap node", f"$.signals[{index}].observed_nodes"))
        resolved_at = gap.get("resolved_at")
        if (status == "resolved") != isinstance(resolved_at, str):
            issues.append(Issue(relative, "resolved_at must be set exactly when status=resolved", "$.resolved_at"))
        return issues

    def validate_interest(self, interest: Any, relative: str | None = None) -> list[Issue]:
        if isinstance(interest, str):
            path = self.path(f"interests/{interest}.yaml")
            relative = self._relative(path)
            try:
                interest = load_yaml(path)
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]
        relative = relative or (
            f"interests/{interest.get('id', '<unknown>')}.yaml"
            if isinstance(interest, dict)
            else "interests/<unknown>.yaml"
        )
        issues = self.validate_schema("interest", interest, relative)
        if not isinstance(interest, dict):
            return issues
        interest_id = interest.get("id")
        if isinstance(interest_id, str) and relative.startswith("interests/") and Path(relative).name != f"{interest_id}.yaml":
            issues.append(Issue(relative, "file name must match Interest id"))
        try:
            known_nodes = self._graph_node_ids()
        except (YamlFileError, AttributeError):
            known_nodes = set()
        for index, node_id in enumerate(interest.get("related_nodes", [])):
            if known_nodes and node_id not in known_nodes:
                issues.append(Issue(relative, f"interest references unknown node: {node_id}", f"$.related_nodes[{index}]"))
        history = interest.get("history", [])
        if history and isinstance(history[-1], dict) and history[-1].get("status") != interest.get("status"):
            issues.append(Issue(relative, "latest history status must match Interest status", "$.history"))
        if history and isinstance(history[0], dict) and history[0].get("status") != "pending":
            issues.append(Issue(relative, "Interest history must start with pending", "$.history[0].status"))
        return issues

    def validate_stage2_repository(self) -> list[Issue]:
        issues = super().validate_stage2_repository()
        collections: dict[str, list[tuple[Path, Any]]] = {}
        for directory in ("gaps", "interests"):
            documents, read_issues = self._read_files(directory)
            collections[directory] = documents
            issues.extend(read_issues)
        for path, gap in collections["gaps"]:
            issues.extend(self.validate_gap(gap, self._relative(path)))
        for path, interest in collections["interests"]:
            issues.extend(self.validate_interest(interest, self._relative(path)))

        for directory in ("gaps", "interests"):
            ids: dict[str, list[str]] = {}
            for path, data in collections[directory]:
                if isinstance(data, dict) and isinstance(data.get("id"), str):
                    ids.setdefault(data["id"], []).append(self._relative(path))
            for document_id, paths in ids.items():
                if len(paths) > 1:
                    issues.append(Issue(directory, f"duplicate id {document_id}: {', '.join(paths)}"))

        gap_keys: dict[tuple[str, str], list[str]] = {}
        for path, gap in collections["gaps"]:
            if isinstance(gap, dict) and isinstance(gap.get("node"), str) and isinstance(gap.get("dimension"), str):
                gap_keys.setdefault((gap["node"], gap["dimension"]), []).append(self._relative(path))
        for key, paths in gap_keys.items():
            if len(paths) > 1:
                issues.append(Issue("gaps", f"duplicate node/dimension Gap {key}: {', '.join(paths)}"))
        unique = {(issue.file, issue.path, issue.message): issue for issue in issues}
        return list(unique.values())

    def list_gaps(self, status: str | None = None) -> list[dict[str, Any]]:
        if status is not None and status not in GAP_STATUSES:
            raise ValueError(f"unknown Gap status: {status}")
        documents, issues = self._read_files("gaps")
        self._raise_issues(issues)
        result = [deepcopy(data) for _, data in documents if isinstance(data, dict) and (status is None or data.get("status") == status)]
        result.sort(key=lambda item: (item.get("created_at", ""), item.get("id", "")))
        return result

    def list_interests(self, status: str | None = None) -> list[dict[str, Any]]:
        valid = {"pending", "active", "satisfied", "dismissed"}
        if status is not None and status not in valid:
            raise ValueError(f"unknown Interest status: {status}")
        documents, issues = self._read_files("interests")
        self._raise_issues(issues)
        result = [deepcopy(data) for _, data in documents if isinstance(data, dict) and (status is None or data.get("status") == status)]
        result.sort(key=lambda item: (item.get("created_at", ""), item.get("id", "")))
        return result

    def create_gap(self, data: Any) -> tuple[Path, str]:
        relative = f"gaps/{data.get('id', '<unknown>')}.yaml" if isinstance(data, dict) else "gaps/<unknown>.yaml"
        self._raise_issues(self.validate_gap(data, relative))
        path = self.path(relative)
        if path.exists():
            existing = load_yaml(path)
            if existing == data:
                return path, "reused"
            raise ValueError(f"refusing to overwrite Gap: {data['id']}")
        if isinstance(data, dict) and self._gap_for_key(data["node"], data["dimension"]):
            raise ValueError(f"Gap already exists for node/dimension: {data['node']}/{data['dimension']}")
        create_yaml(path, data)
        return path, "created"

    def update_gap_impact(self, gap_id: str, impact: str) -> tuple[Path, dict[str, Any], str]:
        if impact not in {"blocking", "important", "minor"}:
            raise ValueError(f"unknown routing impact: {impact}")
        path = self.path(f"gaps/{gap_id}.yaml")
        gap = load_yaml(path)
        self._raise_issues(self.validate_gap(gap, self._relative(path)))
        if gap["routing_impact"] == impact:
            return path, gap, "already-updated"
        has_dependents = bool(self.prerequisite_impact(gap["node"])["dependent_units"])
        if impact == "blocking" and (gap["status"] != "confirmed" or not has_dependents):
            raise ValueError("blocking impact requires a confirmed prerequisite Gap")
        if gap["status"] == "confirmed" and has_dependents and impact != "blocking":
            raise ValueError("a confirmed prerequisite Gap must remain blocking")
        gap["routing_impact"] = impact
        self._raise_issues(self.validate_gap(gap, self._relative(path)))
        replace_yaml(path, gap)
        return path, gap, "updated"

    def create_interest(self, data: Any) -> tuple[Path, str]:
        relative = (
            f"interests/{data.get('id', '<unknown>')}.yaml" if isinstance(data, dict) else "interests/<unknown>.yaml"
        )
        self._raise_issues(self.validate_interest(data, relative))
        if data.get("status") != "pending" or len(data.get("history", [])) != 1:
            raise ValueError("a new Interest must start as pending with one history entry")
        path = self.path(relative)
        if path.exists():
            existing = load_yaml(path)
            self._raise_issues(self.validate_interest(existing, relative))
            if existing == data:
                return path, "reused"
            raise ValueError(f"refusing to overwrite Interest: {data['id']}")
        create_yaml(path, data)
        return path, "created"

    def update_interest(self, interest_id: str, status: str, at: str | None = None) -> tuple[Path, dict[str, Any], str]:
        path = self.path(f"interests/{interest_id}.yaml")
        interest = load_yaml(path)
        self._raise_issues(self.validate_interest(interest, self._relative(path)))
        current = interest["status"]
        if current == status:
            return path, interest, "already-updated"
        if status not in INTEREST_TRANSITIONS.get(current, set()):
            raise ValueError(f"invalid Interest transition: {current} -> {status}")
        if status == "active":
            _, referenced_interests = self._frontier_reason_references()
            if interest_id not in referenced_interests:
                raise ValueError(f"Interest cannot become active before Frontier services it: {interest_id}")
        timestamp = at or self._now()
        self._timestamp(timestamp, "Interest transition timestamp")
        interest["status"] = status
        interest["history"].append({"status": status, "at": timestamp})
        self._raise_issues(self.validate_interest(interest, self._relative(path)))
        replace_yaml(path, interest)
        return path, interest, "updated"

    def expand_graph(self, delta: Any) -> dict[str, Any]:
        if not isinstance(delta, dict) or set(delta) != {"nodes", "edges"}:
            raise ValueError("graph delta must contain exactly nodes and edges")
        if not isinstance(delta["nodes"], list) or not isinstance(delta["edges"], list):
            raise ValueError("graph delta nodes and edges must be arrays")
        graph = deepcopy(self.read("graph"))
        existing_nodes = {node.get("id"): node for node in graph.get("nodes", []) if isinstance(node, dict)}
        added_nodes: list[str] = []
        for node in delta["nodes"]:
            node_id = node.get("id") if isinstance(node, dict) else None
            if node_id in existing_nodes:
                if existing_nodes[node_id] != node:
                    raise ValueError(f"graph delta conflicts with existing node: {node_id}")
                continue
            graph["nodes"].append(deepcopy(node))
            added_nodes.append(node_id)
        existing_edges = {(edge.get("from"), edge.get("to"), edge.get("type")) for edge in graph.get("edges", []) if isinstance(edge, dict)}
        added_edges: list[dict[str, str]] = []
        for edge in delta["edges"]:
            key = (edge.get("from"), edge.get("to"), edge.get("type")) if isinstance(edge, dict) else None
            if key in existing_edges:
                continue
            graph["edges"].append(deepcopy(edge))
            if isinstance(edge, dict):
                added_edges.append(deepcopy(edge))
                existing_edges.add(key)
        self._raise_issues(self.validate_graph(graph))
        replace_yaml(self.path("map/graph.yaml"), graph)
        return {"added_nodes": added_nodes, "added_edges": added_edges}

    def _lowest_unit_nodes(self, unit_id: str) -> list[str]:
        path = self.path(f"units/{unit_id}.yaml")
        unit = load_yaml(path)
        selected = set(unit.get("nodes", []))
        graph = self.read("graph")
        parents = {
            edge["to"]
            for edge in graph.get("edges", [])
            if isinstance(edge, dict)
            and edge.get("type") == "part-of"
            and edge.get("from") in selected
            and edge.get("to") in selected
        }
        return sorted(selected - parents) or sorted(selected)

    def detect_weak_signals(self, evidence_id: str | None = None) -> list[dict[str, Any]]:
        assessments, issues = self._read_files("assessments")
        self._raise_issues(issues)
        signals: list[dict[str, Any]] = []
        for _, assessment in assessments:
            if not isinstance(assessment, dict) or (evidence_id is not None and assessment.get("evidence") != evidence_id):
                continue
            matches = self._find_by_id("evidence", assessment.get("evidence"))
            if len(matches) != 1:
                continue
            evidence = matches[0][1]
            nodes = self._lowest_unit_nodes(evidence["unit"])
            for dimension, result in assessment.get("result", {}).items():
                if result in WEAK_GRADES:
                    signals.append(
                        {
                            "evidence": evidence["id"],
                            "assessment": assessment["id"],
                            "unit": evidence["unit"],
                            "dimension": dimension,
                            "result": result,
                            "candidate_nodes": nodes,
                        }
                    )
        signals.sort(key=lambda item: (item["evidence"], item["dimension"]))
        return signals

    def _prerequisite_adjacency(self) -> dict[str, set[str]]:
        adjacency: dict[str, set[str]] = {}
        for edge in self.read("graph").get("edges", []):
            if isinstance(edge, dict) and edge.get("type") == "prerequisite":
                adjacency.setdefault(edge["from"], set()).add(edge["to"])
        return adjacency

    def _depends_on(self, prerequisite: str, target: str) -> bool:
        adjacency = self._prerequisite_adjacency()
        pending = list(adjacency.get(prerequisite, set()))
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(adjacency.get(current, set()) - seen)
        return False

    def prerequisite_impact(self, node_id: str) -> dict[str, Any]:
        if node_id not in self._graph_node_ids():
            raise ValueError(f"unknown graph node: {node_id}")
        frontier = self.read("frontier")
        dependent_units: list[str] = []
        for unit in frontier.get("units", []):
            if isinstance(unit, dict) and any(self._depends_on(node_id, target) for target in unit.get("nodes", [])):
                dependent_units.append(unit["id"])
        unfinished = self._resumable_documents()
        current_units: set[str] = set()
        for _, session in unfinished:
            for action in session.get("plan", {}).get("actions", []):
                if isinstance(action, dict):
                    current_units.add(action.get("unit"))
        return {
            "node": node_id,
            "is_prerequisite": bool(dependent_units),
            "dependent_units": sorted(dependent_units),
            "affects_current_session": bool(current_units.intersection(dependent_units)),
        }

    def _routing_impact_for(self, node_id: str, status: str, current: str | None = None) -> str:
        if status == "confirmed" and self.prerequisite_impact(node_id)["dependent_units"]:
            return "blocking"
        if current in {"important", "minor"}:
            return current
        graph = self.read("graph")
        nodes = {node["id"]: node for node in graph.get("nodes", []) if isinstance(node, dict)}
        frontier = self.read("frontier")
        focus = frontier.get("focus", {})
        focus_nodes = {focus.get("primary"), *focus.get("secondary", [])}
        if nodes.get(node_id, {}).get("importance") == "core" or node_id in focus_nodes:
            return "important"
        return "minor"

    @staticmethod
    def _gap_id(node_id: str, dimension: str) -> str:
        return f"gap-{node_id}-{dimension}-001"

    def _gap_for_key(self, node_id: str, dimension: str) -> tuple[Path, dict[str, Any]] | None:
        matches = [
            (path, data)
            for path, data in self._read_files("gaps")[0]
            if isinstance(data, dict) and data.get("node") == node_id and data.get("dimension") == dimension
        ]
        if len(matches) > 1:
            raise ValueError(f"duplicate Gap for node/dimension: {node_id}/{dimension}")
        return matches[0] if matches else None

    def _apply_gap_signal(
        self,
        assessment: dict[str, Any],
        evidence: dict[str, Any],
        node_id: str,
        dimension: str,
        observed_nodes: list[str],
    ) -> tuple[Path | None, str]:
        result = assessment["result"][dimension]
        existing = self._gap_for_key(node_id, dimension)
        timestamp = assessment["created_at"]
        if result in WEAK_GRADES:
            signal = {
                "evidence": evidence["id"],
                "assessment": assessment["id"],
                "result": result,
                "observed_nodes": list(observed_nodes),
            }
            if existing is None:
                gap_id = self._gap_id(node_id, dimension)
                path = self.path(f"gaps/{gap_id}.yaml")
                gap = {
                    "format_version": 1,
                    "id": gap_id,
                    "created_at": timestamp,
                    "node": node_id,
                    "dimension": dimension,
                    "status": "detected",
                    "scope": "local",
                    "routing_impact": self._routing_impact_for(node_id, "detected"),
                    "signals": [signal],
                    "history": [{"status": "detected", "at": timestamp, "evidence": evidence["id"]}],
                    "resolved_at": None,
                }
                self._raise_issues(self.validate_gap(gap, self._relative(path)))
                create_yaml(path, gap)
                return path, "detected"
            path, gap = existing
            if any(item.get("evidence") == evidence["id"] for item in gap["signals"]):
                return path, "already-applied"
            gap["signals"].append(signal)
            old_status = gap["status"]
            new_status = "confirmed" if old_status in {"detected", "resolved"} else old_status
            gap["status"] = new_status
            gap["resolved_at"] = None
            if new_status != old_status:
                gap["history"].append({"status": new_status, "at": timestamp, "evidence": evidence["id"]})
            gap["routing_impact"] = self._routing_impact_for(node_id, new_status, gap.get("routing_impact"))
            self._raise_issues(self.validate_gap(gap, self._relative(path)))
            replace_yaml(path, gap)
            return path, "reopened" if old_status == "resolved" else "confirmed" if new_status != old_status else "updated"

        targeted = (
            result in STRONG_GRADES
            and evidence.get("type") == "practice"
            and evidence.get("target", {}).get("dimension") == dimension
        )
        if targeted and existing is not None:
            path, gap = existing
            if gap["status"] == "confirmed":
                gap["status"] = "resolved"
                gap["resolved_at"] = timestamp
                gap["routing_impact"] = self._routing_impact_for(node_id, "resolved", gap.get("routing_impact"))
                gap["history"].append({"status": "resolved", "at": timestamp, "evidence": evidence["id"]})
                self._raise_issues(self.validate_gap(gap, self._relative(path)))
                replace_yaml(path, gap)
                return path, "resolved"
        return existing[0] if existing else None, "ignored"

    def update_gaps_for_evidence(
        self,
        evidence_id: str,
        observed_nodes: list[str] | None = None,
        dimension: str | None = None,
    ) -> list[dict[str, Any]]:
        evidence_matches = self._find_by_id("evidence", evidence_id)
        if len(evidence_matches) != 1:
            raise ValueError(f"unknown or duplicate Evidence: {evidence_id}")
        assessment_matches = [
            item for item in self._read_files("assessments")[0]
            if isinstance(item[1], dict) and item[1].get("evidence") == evidence_id
        ]
        if len(assessment_matches) != 1:
            raise ValueError(f"Evidence requires exactly one Assessment: {evidence_id}")
        evidence = evidence_matches[0][1]
        assessment = assessment_matches[0][1]
        nodes = observed_nodes or self._lowest_unit_nodes(evidence["unit"])
        unknown = set(nodes) - self._graph_node_ids()
        if unknown:
            raise ValueError(f"unknown observed graph nodes: {', '.join(sorted(unknown))}")
        dimensions = [dimension] if dimension else list(assessment["result"])
        if any(item not in {"recall", "understanding", "application"} for item in dimensions):
            raise ValueError(f"unknown mastery dimension: {dimension}")
        changes: list[dict[str, Any]] = []
        for node_id in nodes:
            for current_dimension in dimensions:
                path, outcome = self._apply_gap_signal(
                    assessment, evidence, node_id, current_dimension, nodes
                )
                if outcome != "ignored":
                    changes.append(
                        {
                            "gap": path.stem if path is not None else None,
                            "node": node_id,
                            "dimension": current_dimension,
                            "outcome": outcome,
                        }
                    )
        return changes

    def create_assessment(self, data: Any) -> Path:
        path = super().create_assessment(data)
        if isinstance(data, dict) and isinstance(data.get("evidence"), str):
            self.update_gaps_for_evidence(data["evidence"], data.get("observed_nodes"))
        return path

    def update_routing_metadata(self, at: str | None = None) -> dict[str, Any]:
        timestamp = at or self._now()
        self._timestamp(timestamp, "routing update timestamp")
        updated_gaps: list[str] = []
        for path, gap in self._read_files("gaps")[0]:
            if not isinstance(gap, dict):
                continue
            expected = self._routing_impact_for(gap["node"], gap["status"], gap.get("routing_impact"))
            if gap.get("routing_impact") != expected:
                gap["routing_impact"] = expected
                self._raise_issues(self.validate_gap(gap, self._relative(path)))
                replace_yaml(path, gap)
                updated_gaps.append(gap["id"])

        _, referenced_interests = self._frontier_reason_references()
        activated: list[str] = []
        for path, interest in self._read_files("interests")[0]:
            if not isinstance(interest, dict) or interest.get("status") != "pending" or interest.get("id") not in referenced_interests:
                continue
            interest["status"] = "active"
            interest["history"].append({"status": "active", "at": timestamp})
            self._raise_issues(self.validate_interest(interest, self._relative(path)))
            replace_yaml(path, interest)
            activated.append(interest["id"])
        return {"updated_gaps": updated_gaps, "activated_interests": activated}

    def inspect_related_nodes(self, node_id: str) -> dict[str, Any]:
        graph = self.read("graph")
        nodes = {node["id"]: node for node in graph.get("nodes", []) if isinstance(node, dict)}
        if node_id not in nodes:
            raise ValueError(f"unknown graph node: {node_id}")
        incoming: list[dict[str, str]] = []
        outgoing: list[dict[str, str]] = []
        for edge in graph.get("edges", []):
            if not isinstance(edge, dict):
                continue
            if edge.get("to") == node_id:
                incoming.append(deepcopy(edge))
            if edge.get("from") == node_id:
                outgoing.append(deepcopy(edge))
        return {
            "node": deepcopy(nodes[node_id]),
            "incoming": incoming,
            "outgoing": outgoing,
            "gaps": [gap["id"] for gap in self.list_gaps() if gap.get("node") == node_id],
            "interests": [interest["id"] for interest in self.list_interests() if node_id in interest.get("related_nodes", [])],
        }

    def _candidate_data(self, minutes: int) -> dict[str, Any]:
        result = super()._candidate_data(minutes)
        gap_by_id = {gap["id"]: gap for gap in self.list_gaps()}
        interest_by_id = {interest["id"]: interest for interest in self.list_interests()}
        frontier = self.read("frontier")
        units = {unit["id"]: unit for unit in frontier.get("units", []) if isinstance(unit, dict)}
        blocking_gaps = [gap for gap in gap_by_id.values() if gap.get("status") == "confirmed" and gap.get("routing_impact") == "blocking"]
        for candidate in result["candidates"]:
            unit = units.get(candidate["id"], {})
            reasons = deepcopy(unit.get("routing_reasons", []))
            candidate["routing_reasons"] = reasons
            candidate["related_gaps"] = sorted(
                {reason["gap"] for reason in reasons if reason.get("type") == "gap" and reason.get("gap") in gap_by_id}
            )
            candidate["related_interests"] = sorted(
                {reason["interest"] for reason in reasons if reason.get("type") == "interest" and reason.get("interest") in interest_by_id}
            )
            gap_blockers = sorted(
                gap["id"]
                for gap in blocking_gaps
                if any(self._depends_on(gap["node"], target) for target in unit.get("nodes", []))
            )
            candidate["blocked_by_gaps"] = gap_blockers
            if gap_blockers:
                candidate["availability"] = "blocked"
        result["candidates"].sort(
            key=lambda item: (
                item["availability"] != "available",
                not any(reason.get("type") == "gap" for reason in item["routing_reasons"]),
                not any(reason.get("type") == "primary-route" for reason in item["routing_reasons"]),
                not any(reason.get("type") == "interest" for reason in item["routing_reasons"]),
                {"high": 0, "medium": 1, "low": 2}[item["priority"]],
                item["id"],
            )
        )
        return result
