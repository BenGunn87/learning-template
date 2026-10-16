"""Read existing repository records without changing or rebuilding learning state."""

from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from scripts.learning_core import Repository
from scripts.learning_core.yaml_io import YamlFileError

from .models import Edge, Gap, Node, Progress, Unit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / "web/fixtures/demo"


class Snapshot:
    """One request's data. Instances are never retained between requests."""

    def __init__(self, demo: bool):
        self.repository = Repository(DEMO_ROOT if demo else PROJECT_ROOT)
        self.validator = Repository(PROJECT_ROOT)
        self.mode = "demo" if demo else "repository"
        self.state, issues = self.repository.state()
        self.warnings = [issue.render() for issue in issues]
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.units: dict[str, Unit] = {}
        self.gaps: list[Gap] = []
        if self.state == "uninitialized":
            return

        try:
            graph = self.repository.read("graph")
            graph_issues = self.validator.validate_graph(graph)
            if graph_issues:
                raise ValueError("; ".join(issue.render() for issue in graph_issues))
            self.nodes = {node["id"]: Node.model_validate(node) for node in graph["nodes"]}
            self.edges = [
                Edge(source=edge["from"], target=edge["to"], type=edge["type"])
                for edge in graph["edges"]
            ]
        except (YamlFileError, ValueError, TypeError, KeyError) as exc:
            raise HTTPException(503, f"Не удалось прочитать Knowledge Graph: {exc}") from exc

        self._read_units()
        self._read_gaps()

    def envelope(self) -> dict:
        return {"mode": self.mode, "repository_state": self.state, "warnings": self.warnings}

    def _read_units(self) -> None:
        frontier_ids: set[str] = set()
        try:
            frontier = self.repository.read("frontier")
            if frontier is not None:
                if not isinstance(frontier, dict) or not isinstance(frontier.get("units"), list):
                    raise ValueError("ожидался список frontier.units")
                for record in frontier["units"]:
                    try:
                        unit = Unit.model_validate({**record, "kind": "planned", "in_frontier": True, "progress": None})
                        self.units[unit.id] = unit
                        frontier_ids.add(unit.id)
                    except (ValidationError, TypeError) as exc:
                        self.warnings.append(f"Пропущена запись Frontier: {exc}")
        except (YamlFileError, ValueError) as exc:
            self.warnings.append(f"Frontier недоступен: {exc}")

        try:
            progress = self.repository.read_progress()
        except YamlFileError as exc:
            self.warnings.append(f"Progress недоступен: {exc}")
            progress = {}

        records, issues = self.repository._read_files("units")
        self.warnings.extend(issue.render() for issue in issues)
        seen: set[str] = set()
        for path, record in records:
            try:
                unit = Unit.model_validate({**record, "kind": "initialized", "in_frontier": record.get("id") in frontier_ids, "progress": None})
                if unit.id in seen:
                    self.warnings.append(f"Повторный ID Unit {unit.id}: {path.name}; использована первая запись.")
                    continue
                seen.add(unit.id)
                if unit.id in progress:
                    try:
                        unit.progress = Progress.model_validate(progress[unit.id])
                    except ValidationError as exc:
                        self.warnings.append(f"Progress {unit.id} пропущен: {exc}")
                self.units[unit.id] = unit
            except (ValidationError, TypeError, AttributeError) as exc:
                self.warnings.append(f"Unit {path.name} пропущена: {exc}")

    def _read_gaps(self) -> None:
        # list_gaps owns existing reading/sorting semantics. A malformed optional
        # file falls back to readable records so it does not hide the whole map.
        try:
            records = self.repository.list_gaps()
        except (ValueError, TypeError) as exc:
            self.warnings.append(f"Часть Gaps недоступна: {exc}")
            documents, _ = self.repository._read_files("gaps")
            records = [record for _, record in documents if isinstance(record, dict)]
        for record in records:
            if record.get("status") not in {"detected", "confirmed"}:
                continue
            try:
                self.gaps.append(Gap.model_validate(record))
            except ValidationError as exc:
                self.warnings.append(f"Gap пропущен: {exc}")

    def node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            raise HTTPException(404, "Node не найден")
        return self.nodes[node_id]

    def unit(self, unit_id: str) -> Unit:
        if unit_id not in self.units:
            raise HTTPException(404, "Unit не найдена")
        return self.units[unit_id]

    def node_details(self, node_id: str) -> dict:
        node = self.node(node_id)
        edges = [edge for edge in self.edges if node_id in {edge.source, edge.target}]
        parents = {edge.target for edge in edges if edge.type == "part-of" and edge.source == node_id}
        children = {edge.source for edge in edges if edge.type == "part-of" and edge.target == node_id}
        neighbors = {edge.target if edge.source == node_id else edge.source for edge in edges}
        return {
            **self.envelope(),
            "node": node,
            "parents": [self.nodes[key] for key in sorted(parents)],
            "children": [self.nodes[key] for key in sorted(children)],
            "related_nodes": [self.nodes[key] for key in sorted(neighbors)],
            "edges": edges,
            "units": sorted((unit for unit in self.units.values() if node_id in unit.nodes), key=lambda unit: unit.title),
            "gaps": [gap for gap in self.gaps if gap.node == node_id],
        }

    def unit_details(self, unit_id: str) -> dict:
        unit = self.unit(unit_id)
        missing = set(unit.nodes) - self.nodes.keys()
        if missing:
            self.warnings.append(f"У Unit отсутствуют Nodes: {', '.join(sorted(missing))}")
        return {
            **self.envelope(),
            "unit": unit,
            "nodes": [self.nodes[key] for key in unit.nodes if key in self.nodes],
            "gaps": [gap for gap in self.gaps if gap.node in unit.nodes],
        }
