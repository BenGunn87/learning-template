from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from learning_core import Repository  # noqa: E402
from learning_core.yaml_io import load_yaml  # noqa: E402


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def graph_fixture() -> dict:
    return {
        "format_version": 1,
        "nodes": [
            {"id": "foundations", "title": "Foundations", "type": "area", "importance": "core"},
            {"id": "core-concept", "title": "Core concept", "type": "concept", "importance": "core"},
        ],
        "edges": [
            {"from": "core-concept", "to": "foundations", "type": "part-of"},
        ],
    }


def context_fixture() -> dict:
    return {
        "format_version": 1,
        "goal": {"why": "professional-growth", "outcome": "Apply the topic independently."},
        "experience": {"level": "beginner"},
        "depth": "working",
        "constraints": {"default_session_minutes": 25},
        "preferences": {"languages": ["en"], "resources": ["documentation"]},
        "diagnostic": {
            "status": "completed",
            "completed_at": "2026-09-14",
            "areas": [{"area": "Foundations", "level": "weak"}],
        },
    }


def frontier_fixture() -> dict:
    return {
        "format_version": 1,
        "focus": {"primary": "foundations", "secondary": []},
        "units": [
            {
                "id": f"unit-{index}",
                "title": f"Unit {index}",
                "nodes": ["foundations"],
                "goal": "Learn one useful part.",
                "estimated_minutes": 25,
                "priority": "high" if index == 1 else "medium",
            }
            for index in range(1, 6)
        ],
    }


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copytree(PROJECT_ROOT / "schemas", self.root / "schemas")
        shutil.copytree(PROJECT_ROOT / ".agents", self.root / ".agents")
        for directory in ("units", "evidence", "assessments", "sessions", "progress", "indexes", "scripts"):
            (self.root / directory).mkdir(parents=True)
        write_yaml(
            self.root / "config/settings.yaml",
            {
                "session": {"default_minutes": 25},
                "frontier": {"target_units": 7, "min_units": 5, "max_units": 10},
                "diagnostic": {"enabled": True},
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_uninitialized(self) -> Repository:
        write_yaml(
            self.root / "learning.yaml",
            {"format_version": 1, "topic": None, "learning_core": {"version": "0.3.0"}},
        )
        write_yaml(self.root / "config/context.yaml", None)
        write_yaml(self.root / "map/graph.yaml", None)
        write_yaml(self.root / "map/frontier.yaml", None)
        return Repository(self.root)

    def make_initialized(self) -> Repository:
        write_yaml(
            self.root / "learning.yaml",
            {
                "format_version": 1,
                "topic": {"id": "example-topic", "title": "Example Topic"},
                "learning_core": {"version": "0.3.0"},
                "created_at": "2026-09-14",
            },
        )
        write_yaml(self.root / "config/context.yaml", context_fixture())
        write_yaml(self.root / "map/graph.yaml", graph_fixture())
        write_yaml(self.root / "map/frontier.yaml", frontier_fixture())
        return Repository(self.root)

    def assert_issue_contains(self, issues, text: str) -> None:
        self.assertTrue(any(text in issue.render() for issue in issues), [issue.render() for issue in issues])

    def test_detects_uninitialized_repository(self) -> None:
        state, issues = self.make_uninitialized().state()
        self.assertEqual("uninitialized", state)
        self.assertEqual([], issues)

    def test_detects_initialized_repository(self) -> None:
        repository = self.make_initialized()
        state, issues = repository.state()
        self.assertEqual("initialized", state)
        self.assertEqual([], issues)
        self.assertEqual([], repository.validate_repository())

    def test_schema_validation(self) -> None:
        repository = self.make_initialized()
        context = context_fixture()
        context["goal"]["outcome"] = ""
        issues = repository.validate_document("context", context)
        self.assert_issue_contains(issues, "should be non-empty")

    def test_duplicate_node_id(self) -> None:
        repository = self.make_initialized()
        graph = graph_fixture()
        graph["nodes"].append({"id": "foundations", "title": "Duplicate", "type": "topic"})
        self.assert_issue_contains(repository.validate_graph(graph), "duplicate node id")

    def test_edge_to_unknown_node(self) -> None:
        repository = self.make_initialized()
        graph = graph_fixture()
        graph["edges"].append({"from": "missing", "to": "foundations", "type": "related"})
        self.assert_issue_contains(repository.validate_graph(graph), "edge references unknown node")

    def test_invalid_node_type(self) -> None:
        repository = self.make_initialized()
        graph = graph_fixture()
        graph["nodes"][0]["type"] = "chapter"
        self.assert_issue_contains(repository.validate_graph(graph), "is not one of")

    def test_invalid_edge_type(self) -> None:
        repository = self.make_initialized()
        graph = graph_fixture()
        graph["edges"][0]["type"] = "contains"
        self.assert_issue_contains(repository.validate_graph(graph), "is not one of")

    def test_frontier_unit_with_unknown_node(self) -> None:
        repository = self.make_initialized()
        frontier = frontier_fixture()
        frontier["units"][0]["nodes"] = ["missing"]
        self.assert_issue_contains(repository.validate_frontier(frontier, graph_fixture()), "unit references unknown node")

    def test_partial_initialization(self) -> None:
        repository = self.make_uninitialized()
        learning = repository.read("learning")
        learning["topic"] = {"id": "example-topic", "title": "Example Topic"}
        learning["created_at"] = "2026-09-14"
        write_yaml(self.root / "learning.yaml", learning)
        state, issues = repository.state()
        self.assertEqual("partial", state)
        self.assert_issue_contains(issues, "initialization is incomplete")

    def test_yaml_dates_remain_strings(self) -> None:
        repository = self.make_initialized()
        learning = load_yaml(repository.path("learning.yaml"))
        self.assertEqual("2026-09-14", learning["created_at"])
        self.assertIsInstance(learning["created_at"], str)

    def test_malformed_yaml_is_reported_as_partial(self) -> None:
        repository = self.make_uninitialized()
        (self.root / "map/graph.yaml").write_text("nodes: [\n", encoding="utf-8")
        state, issues = repository.state()
        self.assertEqual("partial", state)
        self.assert_issue_contains(issues, "cannot read")

    def test_validation_is_idempotent_and_read_only(self) -> None:
        repository = self.make_initialized()
        tracked = [repository.path(path) for path in Repository.DOCUMENTS.values()]
        before = {path: path.read_bytes() for path in tracked}
        self.assertEqual([], repository.validate_repository())
        self.assertEqual([], repository.validate_repository())
        after = {path: path.read_bytes() for path in tracked}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
