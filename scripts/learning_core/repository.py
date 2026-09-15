"""Repository state detection and shared deterministic operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from jsonschema import FormatChecker
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for

from .issues import Issue
from .stage3 import Stage3RepositoryMixin
from .yaml_io import YamlFileError, dump_yaml, load_yaml


class Repository(Stage3RepositoryMixin):
    DOCUMENTS = {
        "learning": Path("learning.yaml"),
        "context": Path("config/context.yaml"),
        "graph": Path("map/graph.yaml"),
        "frontier": Path("map/frontier.yaml"),
    }
    SCHEMAS = {
        name: Path("schemas") / f"{name}.schema.yaml"
        for name in (*DOCUMENTS, "settings", "unit", "session", "evidence", "assessment", "progress")
    }
    REQUIRED_DIRECTORIES = (
        "config",
        "map",
        "units",
        "evidence",
        "assessments",
        "sessions",
        "progress",
        "indexes",
        "scripts",
        "schemas",
        ".agents/skills",
    )

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()

    def path(self, relative: Path | str) -> Path:
        return self.root / relative

    def read(self, name: str) -> Any:
        return load_yaml(self.path(self.DOCUMENTS[name]))

    def _read_or_issue(self, name: str) -> tuple[Any, list[Issue]]:
        relative = str(self.DOCUMENTS[name])
        try:
            return self.read(name), []
        except YamlFileError as exc:
            return None, [Issue(relative, str(exc))]

    def state(self) -> tuple[str, list[Issue]]:
        documents: dict[str, Any] = {}
        issues: list[Issue] = []
        for name in self.DOCUMENTS:
            documents[name], read_issues = self._read_or_issue(name)
            issues.extend(read_issues)

        if issues:
            return "partial", issues

        learning = documents["learning"]
        if not isinstance(learning, dict) or "topic" not in learning:
            return "partial", [Issue("learning.yaml", "topic is missing")]

        topic = learning["topic"]
        generated = {name: documents[name] for name in ("context", "graph", "frontier")}
        if topic is None and all(value is None for value in generated.values()):
            return "uninitialized", []

        if isinstance(topic, dict) and all(isinstance(value, dict) for value in generated.values()):
            return "initialized", []

        for name, value in generated.items():
            if value is None:
                issues.append(Issue(str(self.DOCUMENTS[name]), "initialization is incomplete"))
        if topic is None:
            issues.append(Issue("learning.yaml", "topic is null but generated data exists"))
        return "partial", issues

    def _schema(self, name: str) -> tuple[Any, list[Issue]]:
        relative = str(self.SCHEMAS[name])
        try:
            return load_yaml(self.path(self.SCHEMAS[name])), []
        except YamlFileError as exc:
            return None, [Issue(relative, str(exc))]

    @staticmethod
    def _json_path(parts: Iterable[Any]) -> str:
        rendered = "$"
        for part in parts:
            rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
        return rendered

    def validate_document(self, name: str, data: Any | None = None) -> list[Issue]:
        relative = str(self.DOCUMENTS[name])
        if data is None:
            try:
                data = self.read(name)
            except YamlFileError as exc:
                return [Issue(relative, str(exc))]

        return self.validate_schema(name, data, relative)

    def validate_schema(self, name: str, data: Any, relative: str) -> list[Issue]:
        schema, issues = self._schema(name)
        if issues:
            return issues

        try:
            validator_class = validator_for(schema)
            validator_class.check_schema(schema)
        except SchemaError as exc:
            return [Issue(str(self.SCHEMAS[name]), f"invalid schema: {exc.message}")]

        validator = validator_class(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
        return [
            Issue(relative, error.message, self._json_path(error.absolute_path))
            for error in errors
        ]

    def validate_graph(self, graph: Any | None = None) -> list[Issue]:
        if graph is None:
            try:
                graph = self.read("graph")
            except YamlFileError as exc:
                return [Issue("map/graph.yaml", str(exc))]

        issues = self.validate_document("graph", graph)
        if not isinstance(graph, dict):
            return issues

        nodes = graph.get("nodes")
        edges = graph.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            return issues

        ids: list[str] = [node.get("id") for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)]
        known = set(ids)
        duplicates = sorted({node_id for node_id in ids if ids.count(node_id) > 1})
        for node_id in duplicates:
            issues.append(Issue("map/graph.yaml", f"duplicate node id: {node_id}", "$.nodes"))

        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                continue
            source, target = edge.get("from"), edge.get("to")
            for endpoint, value in (("from", source), ("to", target)):
                if isinstance(value, str) and value not in known:
                    issues.append(Issue("map/graph.yaml", f"edge references unknown node: {value}", f"$.edges[{index}].{endpoint}"))
            if isinstance(source, str) and source == target:
                issues.append(Issue("map/graph.yaml", "self-referencing edge is not allowed", f"$.edges[{index}]"))

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            for replacement in node.get("replaced_by", []):
                if replacement not in known:
                    issues.append(Issue("map/graph.yaml", f"replacement references unknown node: {replacement}", f"$.nodes[{index}].replaced_by"))
        return issues

    def validate_frontier(self, frontier: Any | None = None, graph: Any | None = None) -> list[Issue]:
        if frontier is None:
            try:
                frontier = self.read("frontier")
            except YamlFileError as exc:
                return [Issue("map/frontier.yaml", str(exc))]
        if graph is None:
            try:
                graph = self.read("graph")
            except YamlFileError as exc:
                return [Issue("map/graph.yaml", str(exc))]

        issues = self.validate_document("frontier", frontier)
        if not isinstance(frontier, dict) or not isinstance(graph, dict):
            return issues

        graph_ids = {
            node.get("id")
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        units = frontier.get("units", [])
        try:
            settings = load_yaml(self.path("config/settings.yaml"))
            minimum = settings["frontier"]["min_units"]
            maximum = settings["frontier"]["max_units"]
            if isinstance(units, list) and isinstance(minimum, int) and isinstance(maximum, int) and not minimum <= len(units) <= maximum:
                issues.append(Issue("map/frontier.yaml", f"frontier must contain between {minimum} and {maximum} units", "$.units"))
        except (YamlFileError, KeyError, TypeError):
            # Repository/settings validation reports the more actionable error.
            pass
        unit_ids = [unit.get("id") for unit in units if isinstance(unit, dict) and isinstance(unit.get("id"), str)]
        for duplicate in sorted({unit_id for unit_id in unit_ids if unit_ids.count(unit_id) > 1}):
            issues.append(Issue("map/frontier.yaml", f"duplicate unit id: {duplicate}", "$.units"))
        known_units = set(unit_ids)

        focus = frontier.get("focus", {})
        focus_nodes: list[tuple[str, Any]] = [("$.focus.primary", focus.get("primary"))]
        focus_nodes.extend((f"$.focus.secondary[{index}]", value) for index, value in enumerate(focus.get("secondary", [])))
        for path, node_id in focus_nodes:
            if isinstance(node_id, str) and node_id not in graph_ids:
                issues.append(Issue("map/frontier.yaml", f"focus references unknown node: {node_id}", path))

        for index, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            for node_index, node_id in enumerate(unit.get("nodes", [])):
                if node_id not in graph_ids:
                    issues.append(Issue("map/frontier.yaml", f"unit references unknown node: {node_id}", f"$.units[{index}].nodes[{node_index}]"))
            for blocker_index, blocker in enumerate(unit.get("blocked_by", [])):
                if blocker not in known_units:
                    issues.append(Issue("map/frontier.yaml", f"blocked_by references unknown unit: {blocker}", f"$.units[{index}].blocked_by[{blocker_index}]"))
                if blocker == unit.get("id"):
                    issues.append(Issue("map/frontier.yaml", "unit cannot block itself", f"$.units[{index}].blocked_by[{blocker_index}]"))
        return issues

    def _validate_settings(self) -> list[Issue]:
        try:
            settings = load_yaml(self.path("config/settings.yaml"))
        except YamlFileError as exc:
            return [Issue("config/settings.yaml", str(exc))]
        issues = self.validate_schema("settings", settings, "config/settings.yaml")
        try:
            frontier = settings["frontier"]
            minimum = frontier["min_units"]
            target = frontier["target_units"]
            maximum = frontier["max_units"]
            minutes = settings["session"]["default_minutes"]
            enabled = settings["diagnostic"]["enabled"]
            review = settings["review"]
        except (KeyError, TypeError):
            return [Issue("config/settings.yaml", "required settings are missing")]
        if not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in (minimum, target, maximum, minutes)):
            issues.append(Issue("config/settings.yaml", "minute and frontier limits must be positive integers"))
        elif not minimum <= target <= maximum:
            issues.append(Issue("config/settings.yaml", "frontier limits must satisfy min_units <= target_units <= max_units"))
        if not isinstance(enabled, bool):
            issues.append(Issue("config/settings.yaml", "diagnostic.enabled must be boolean"))
        initial = review.get("initial_intervals", {}) if isinstance(review, dict) else {}
        if isinstance(initial, dict) and all(isinstance(initial.get(key), int) for key in ("failed", "hard", "good", "easy")):
            if not initial["failed"] <= initial["hard"] <= initial["good"] <= initial["easy"]:
                issues.append(Issue("config/settings.yaml", "initial review intervals must increase from failed to easy", "$.review.initial_intervals"))
        return issues

    def validate_repository(self) -> list[Issue]:
        issues: list[Issue] = []
        for directory in self.REQUIRED_DIRECTORIES:
            if not self.path(directory).is_dir():
                issues.append(Issue(directory, "required directory is missing"))

        learning, read_issues = self._read_or_issue("learning")
        issues.extend(read_issues)
        if not read_issues:
            issues.extend(self.validate_document("learning", learning))
        issues.extend(self._validate_settings())

        state, state_issues = self.state()
        issues.extend(state_issues)
        if state == "initialized":
            context = self.read("context")
            graph = self.read("graph")
            frontier = self.read("frontier")
            issues.extend(self.validate_document("context", context))
            issues.extend(self.validate_graph(graph))
            issues.extend(self.validate_frontier(frontier, graph))
        elif state == "partial":
            context, context_issues = self._read_or_issue("context")
            graph, graph_issues = self._read_or_issue("graph")
            frontier, frontier_issues = self._read_or_issue("frontier")
            issues.extend(context_issues + graph_issues + frontier_issues)
            if isinstance(context, dict):
                issues.extend(self.validate_document("context", context))
            if isinstance(graph, dict):
                issues.extend(self.validate_graph(graph))
            if isinstance(frontier, dict):
                issues.extend(self.validate_frontier(frontier, graph))

        issues.extend(self.validate_stage2_repository())

        unique: dict[tuple[str, str, str], Issue] = {}
        for issue in issues:
            unique[(issue.file, issue.path, issue.message)] = issue
        return list(unique.values())

    def frontier_candidates(self) -> dict[str, Any]:
        graph = self.read("graph")
        context = self.read("context")
        issues = self.validate_graph(graph) + self.validate_document("context", context)
        if issues:
            raise ValueError("\n".join(issue.render() for issue in issues))

        prerequisites: dict[str, list[str]] = {}
        for edge in graph["edges"]:
            if edge["type"] == "prerequisite":
                prerequisites.setdefault(edge["to"], []).append(edge["from"])
        candidates = []
        for node in graph["nodes"]:
            if node.get("status", "active") == "deprecated":
                continue
            required = sorted(prerequisites.get(node["id"], []))
            candidates.append(
                {
                    "node": node["id"],
                    "title": node["title"],
                    "type": node["type"],
                    "importance": node.get("importance", "supporting"),
                    "availability": "available" if not required else "blocked",
                    "prerequisites": required,
                }
            )
        candidates.sort(key=lambda item: ({"core": 0, "supporting": 1, "optional": 2}[item["importance"]], item["title"].casefold()))
        return {
            "diagnostic_hypotheses": context["diagnostic"].get("areas", []),
            "candidates": candidates,
        }

    def render_status(self, on_date: str | None = None) -> str:
        state, state_issues = self.state()
        if state == "uninitialized":
            return "Learning repository\n\nState: uninitialized\nStart with: init or ‘Хочу изучать …’"
        if state == "partial":
            details = "\n".join(f"- {issue.render()}" for issue in state_issues) or "- generated files are incomplete"
            return f"Learning repository\n\nState: partial\n{details}"

        validation_issues = self.validate_repository()
        if validation_issues:
            details = "\n".join(f"- {issue.render()}" for issue in validation_issues)
            return f"Learning repository\n\nState: initialized, invalid\n{details}"

        learning = self.read("learning")
        context = self.read("context")
        graph = self.read("graph")
        frontier = self.read("frontier")
        node_titles = {node["id"]: node["title"] for node in graph["nodes"]}
        frontier_titles = {unit["id"]: unit["title"] for unit in frontier["units"]}
        unit_documents, _ = self._read_files("units")
        unit_titles = {
            data["id"]: data["title"]
            for _, data in unit_documents
            if isinstance(data, dict) and isinstance(data.get("id"), str) and isinstance(data.get("title"), str)
        }
        titles = {**frontier_titles, **unit_titles}
        progress = self.read_progress()
        lines = [learning["topic"]["title"], "", "Goal:", context["goal"]["outcome"].strip()]

        if progress:
            lines.extend(["", f"Completed attempts: {sum(item['attempts'] for item in progress.values())}"])
            verified = [unit_id for unit_id, item in progress.items() if item["status"] == "verified"]
            lines.extend(["", "Verified:"])
            lines.extend(f"- {titles.get(unit_id, unit_id)}" for unit_id in verified)
            if not verified:
                lines.append("- none")

            due_reviews = self.get_due_reviews(on_date)
            lines.extend(["", "Reviews due:"])
            if due_reviews:
                for review in due_reviews:
                    overdue = f" ({review['overdue_days']} days overdue)" if review["overdue_days"] else ""
                    lines.append(f"- {review['title']} — due {review['due']}{overdue}")
            else:
                lines.append("- none")

            practice = [unit_id for unit_id, item in progress.items() if item["status"] == "practice"]
            lines.extend(["", "Needs practice:"])
            if practice:
                for unit_id in practice:
                    lines.append(f"- {titles.get(unit_id, unit_id)}")
                    weaknesses = [
                        dimension
                        for dimension, grade in progress[unit_id]["mastery"].items()
                        if grade in {"failed", "hard"}
                    ]
                    if weaknesses:
                        lines.append(f"  weakness: {', '.join(weaknesses)}")
                    assessment_id = progress[unit_id]["latest_assessment"]
                    matches = self._find_by_id("assessments", assessment_id)
                    if matches and isinstance(matches[0][1], dict):
                        lines.extend(f"  - {gap}" for gap in matches[0][1].get("gaps", []))
            else:
                lines.append("- none")

            learning_units = [unit_id for unit_id, item in progress.items() if item["status"] == "learning"]
            if learning_units:
                lines.extend(["", "Needs learning:"])
                lines.extend(f"- {titles.get(unit_id, unit_id)}" for unit_id in learning_units)
        else:
            lines.extend(["", "Completed attempts: 0", "", "Diagnostic:"])
            diagnostic = context["diagnostic"]
            if diagnostic["status"] == "completed":
                for level in ("strong", "weak", "unknown"):
                    areas = [area["area"] for area in diagnostic.get("areas", []) if area["level"] == level]
                    lines.append(f"{level.capitalize()}:")
                    lines.extend(f"- {area}" for area in areas)
                    if not areas:
                        lines.append("- none")
            else:
                lines.append(diagnostic["status"])

        sessions, _ = self._read_files("sessions")
        active = [data["id"] for _, data in sessions if isinstance(data, dict) and data.get("status") == "active"]
        if active:
            lines.extend(["", "Active Session:", f"- {active[0]}"])

        default_minutes = context.get("constraints", {}).get("default_session_minutes", 25)
        candidates = self._candidate_data(default_minutes)["candidates"]
        lines.extend([
            "",
            "Primary focus:",
            node_titles.get(frontier["focus"]["primary"], frontier["focus"]["primary"]),
            "",
            "Next:",
        ])
        available = [candidate for candidate in candidates if candidate["availability"] == "available"]
        for index, candidate in enumerate(available[:3], start=1):
            progress_label = f" [{candidate['progress']}]" if candidate["progress"] != "untouched" else ""
            lines.append(f"{index}. {candidate['title']} — {candidate['estimated_minutes']} min{progress_label}")
        if not available:
            lines.append("- no available Units")
        return "\n".join(lines)

    def state_as_yaml(self) -> str:
        state, issues = self.state()
        return dump_yaml({"state": state, "issues": [issue.render() for issue in issues]})
