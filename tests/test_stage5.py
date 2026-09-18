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


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


class Stage5Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copytree(PROJECT_ROOT / "schemas", self.root / "schemas")
        for directory in (
            "units",
            "evidence",
            "assessments",
            "sessions",
            "progress",
            "indexes",
            "scripts",
            "gaps",
            "interests",
            ".agents/skills",
        ):
            (self.root / directory).mkdir(parents=True)
        write_yaml(
            self.root / "learning.yaml",
            {
                "format_version": 1,
                "topic": {"id": "system-design", "title": "System Design"},
                "learning_core": {"version": "0.5.0"},
                "created_at": "2026-09-14",
            },
        )
        write_yaml(
            self.root / "config/context.yaml",
            {
                "format_version": 1,
                "goal": {"why": "professional-growth", "outcome": "Design backend systems independently."},
                "experience": {"level": "beginner"},
                "depth": "working",
                "constraints": {"default_session_minutes": 25},
                "preferences": {"languages": ["en"], "resources": ["documentation"]},
                "diagnostic": {
                    "status": "completed",
                    "completed_at": "2026-09-14",
                    "areas": [{"area": "Replication", "level": "weak"}],
                },
            },
        )
        write_yaml(
            self.root / "config/settings.yaml",
            {
                "session": {"default_minutes": 25, "min_partial_unit_minutes": 10},
                "frontier": {"target_units": 5, "min_units": 5, "max_units": 10},
                "diagnostic": {"enabled": True},
                "review": {
                    "max_session_share": 0.25,
                    "estimated_minutes": 5,
                    "initial_intervals": {"failed": 1, "hard": 3, "good": 7, "easy": 14},
                    "multipliers": {"hard": 1.5, "good": 2.0, "easy": 3.0},
                },
            },
        )
        write_yaml(
            self.root / "map/graph.yaml",
            {
                "format_version": 1,
                "nodes": [
                    {"id": "replication", "title": "Replication", "type": "area", "importance": "core"},
                    {"id": "quorum", "title": "Quorum", "type": "concept", "importance": "core"},
                    {"id": "consensus", "title": "Consensus", "type": "concept", "importance": "core"},
                ],
                "edges": [
                    {"from": "quorum", "to": "replication", "type": "part-of"},
                    {"from": "quorum", "to": "consensus", "type": "prerequisite"},
                ],
            },
        )
        units = [
            {
                "id": "practice-quorum" if index == 1 else "study-consensus" if index == 2 else f"unit-{index}",
                "title": "Practice quorum" if index == 1 else "Study consensus" if index == 2 else f"Unit {index}",
                "nodes": ["replication", "quorum"] if index == 1 else ["consensus"] if index == 2 else ["replication"],
                "goal": "Make one concrete system design decision.",
                "estimated_minutes": 25,
                "priority": "high" if index < 3 else "medium",
                "routing_reasons": [{"type": "primary-route"}],
            }
            for index in range(1, 6)
        ]
        write_yaml(
            self.root / "map/frontier.yaml",
            {"format_version": 1, "focus": {"primary": "replication", "secondary": []}, "units": units},
        )
        self.repository = Repository(self.root)
        self.repository.create_unit(
            {
                "format_version": 1,
                "id": "practice-quorum",
                "title": "Practice quorum",
                "nodes": ["replication", "quorum"],
                "goal": "Apply quorum reasoning to failure scenarios.",
                "estimated_minutes": 25,
                "concepts": ["read quorum", "write quorum"],
                "study_focus": ["When do quorums overlap?", "What happens during failures?"],
                "practice": {"type": "scenario", "goal": "Choose quorum parameters."},
                "verification": {
                    "recall": {"enabled": True},
                    "understanding": {"enabled": True},
                    "application": {"enabled": True},
                },
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add_existing_storage_branch(self) -> None:
        graph = self.repository.read("graph")
        graph["nodes"].extend(
            [
                {"id": "data-systems", "title": "Data systems", "type": "area", "importance": "core"},
                {
                    "id": "storage-selection",
                    "title": "Storage selection",
                    "type": "topic",
                    "importance": "supporting",
                },
            ]
        )
        graph["edges"].append({"from": "storage-selection", "to": "data-systems", "type": "part-of"})
        write_yaml(self.root / "map/graph.yaml", graph)

    def attempt(
        self,
        evidence_type: str,
        day: str,
        grade: str,
        previous: str | None = None,
        *,
        result: dict[str, str] | None = None,
        evaluated: dict[str, dict[str, list[str]]] | None = None,
        include_evaluated: bool = True,
    ) -> str:
        _, session = self.repository.create_session("practice-quorum", 25, f"{day}T10:00:00+05:00")
        evidence_id = f"{session['id']}-{evidence_type}-001"
        common = {
            "format_version": 1,
            "id": evidence_id,
            "unit": "practice-quorum",
            "session": session["id"],
            "type": evidence_type,
            "created_at": f"{day}T10:20:00+05:00",
            "takeaways": ["Quorum choices depend on failure and consistency goals."],
            "observations": [],
        }
        if evidence_type == "initial":
            evidence = {
                **common,
                "resource": {
                    "title": "Quorum notes",
                    "url": "https://example.com/quorum",
                    "type": "article",
                    "language": "en",
                },
                "recall": {"prompts": ["What is a quorum?"], "answers": ["A voting subset."]},
                "practice": {"prompt": "Choose R and W for N=3.", "answer": "I am not sure."},
            }
        elif evidence_type == "practice":
            evidence = {
                **common,
                "target": {"dimension": "application"},
                "based_on": {"evidence": previous},
                "practice": {
                    "prompt": f"Choose quorum parameters for the scenario on {day}.",
                    "answer": "A reasoned choice." if grade in {"good", "easy"} else "An incomplete choice.",
                },
            }
        else:
            evidence = {
                **common,
                "based_on": {"previous_evidence": previous},
                "prompt": f"Re-evaluate a quorum trade-off on {day}.",
                "answer": "An incomplete review answer.",
            }
        self.repository.create_evidence(evidence)
        result = result or {"recall": "good", "understanding": "good", "application": grade}
        if evaluated is None:
            dimensions = ("application",) if evidence_type == "practice" else ("recall", "understanding", "application")
            evaluated = {dimension: {"nodes": ["quorum"]} for dimension in dimensions}
        assessment = {
            "format_version": 1,
            "id": f"{evidence_id}-assessment-001",
            "evidence": evidence_id,
            "type": evidence_type,
            "created_at": f"{day}T10:22:00+05:00",
            "result": result,
            "gaps": (
                []
                if all(value in {"good", "easy"} for value in result.values())
                else ["A tested quorum dimension needs improvement."]
            ),
            "summary": "Assessment of quorum application.",
        }
        if include_evaluated:
            assessment["evaluated"] = evaluated
        if evidence_type == "review":
            assessment["review_outcome"] = self.repository.calculate_review_outcome(result)
        self.repository.create_assessment(assessment)
        self.repository.rebuild_progress()
        self.repository.complete_session(session["id"], [evidence_id], f"{day}T10:25:00+05:00")
        return evidence_id

    @staticmethod
    def gap_by_key(gaps: list[dict], node: str, dimension: str) -> dict:
        return next(gap for gap in gaps if gap["node"] == node and gap["dimension"] == dimension)

    def test_gap_lifecycle_blocking_and_no_parent_promotion(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        gaps = self.repository.list_gaps()
        self.assertEqual(1, len(gaps))
        self.assertEqual("detected", gaps[0]["status"])
        self.assertEqual("quorum", gaps[0]["node"])
        self.assertFalse(any(gap["node"] == "replication" for gap in gaps))

        second = self.attempt("practice", "2026-09-15", "hard", first)
        gap = self.repository.list_gaps()[0]
        self.assertEqual("confirmed", gap["status"])
        self.assertEqual("blocking", gap["routing_impact"])
        self.assertEqual(2, len(gap["signals"]))
        candidates = self.repository.session_candidates(25)["candidates"]
        dependent = next(item for item in candidates if item["id"] == "study-consensus")
        self.assertEqual("blocked", dependent["availability"])
        self.assertEqual([gap["id"]], dependent["blocked_by_gaps"])

        third = self.attempt("practice", "2026-09-16", "good", second)
        gap = self.repository.list_gaps()[0]
        self.assertEqual("resolved", gap["status"])
        self.assertEqual("2026-09-16T10:22:00+05:00", gap["resolved_at"])

        self.attempt("review", "2026-09-23", "hard", third)
        gap = self.repository.list_gaps()[0]
        self.assertEqual("confirmed", gap["status"])
        self.assertIsNone(gap["resolved_at"])
        self.assertEqual("confirmed", gap["history"][-1]["status"])
        self.assertEqual(3, len(gap["signals"]))
        self.assertEqual([], self.repository.validate_repository())

    def test_carried_forward_dimension_does_not_confirm_gap(self) -> None:
        first = self.attempt(
            "initial",
            "2026-09-14",
            "hard",
            result={"recall": "hard", "understanding": "good", "application": "hard"},
            evaluated={
                "recall": {"nodes": ["quorum"]},
                "application": {"nodes": ["quorum"]},
            },
        )
        self.attempt(
            "practice",
            "2026-09-15",
            "good",
            first,
            result={"recall": "hard", "understanding": "good", "application": "good"},
            evaluated={"application": {"nodes": ["quorum"]}},
        )
        gaps = self.repository.list_gaps()
        recall_gap = self.gap_by_key(gaps, "quorum", "recall")
        application_gap = self.gap_by_key(gaps, "quorum", "application")
        self.assertEqual("detected", recall_gap["status"])
        self.assertEqual(1, len(recall_gap["signals"]))
        self.assertEqual("resolved", application_gap["status"])

    def test_second_real_evaluation_confirms_gap(self) -> None:
        first = self.attempt(
            "initial",
            "2026-09-14",
            "hard",
            result={"recall": "hard", "understanding": "good", "application": "hard"},
            evaluated={"recall": {"nodes": ["quorum"]}, "application": {"nodes": ["quorum"]}},
        )
        self.attempt(
            "practice",
            "2026-09-15",
            "hard",
            first,
            result={"recall": "hard", "understanding": "good", "application": "hard"},
            evaluated={"recall": {"nodes": ["quorum"]}, "application": {"nodes": ["quorum"]}},
        )
        recall_gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "recall")
        self.assertEqual("confirmed", recall_gap["status"])
        self.assertEqual(2, len(recall_gap["signals"]))

    def test_dimension_to_node_attribution_does_not_create_cross_product(self) -> None:
        self.attempt(
            "initial",
            "2026-09-14",
            "hard",
            result={"recall": "hard", "understanding": "good", "application": "hard"},
            evaluated={
                "recall": {"nodes": ["quorum"]},
                "application": {"nodes": ["consensus"]},
            },
        )
        keys = {(gap["node"], gap["dimension"]) for gap in self.repository.list_gaps()}
        self.assertEqual({("quorum", "recall"), ("consensus", "application")}, keys)
        signals = self.repository.detect_weak_signals()
        self.assertEqual(
            {("quorum", "recall"), ("consensus", "application")},
            {(signal["node"], signal["dimension"]) for signal in signals},
        )

    def test_detected_gap_resolves_then_reopens_with_same_id(self) -> None:
        first = self.attempt(
            "initial",
            "2026-09-14",
            "hard",
            evaluated={"application": {"nodes": ["quorum"]}},
        )
        original = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        second = self.attempt(
            "practice",
            "2026-09-15",
            "good",
            first,
            evaluated={"application": {"nodes": ["quorum"]}},
        )
        resolved = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual(original["id"], resolved["id"])
        self.assertEqual("resolved", resolved["status"])
        self.assertEqual(["detected", "resolved"], [item["status"] for item in resolved["history"]])
        self.assertEqual(1, len(resolved["signals"]))

        self.attempt(
            "review",
            "2026-09-22",
            "hard",
            second,
            evaluated={"application": {"nodes": ["quorum"]}},
        )
        reopened = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual(original["id"], reopened["id"])
        self.assertEqual("confirmed", reopened["status"])
        self.assertEqual(["detected", "resolved", "confirmed"], [item["status"] for item in reopened["history"]])
        self.assertEqual(2, len(reopened["signals"]))

    def test_legacy_assessment_without_evaluated_stays_valid_and_creates_no_gap(self) -> None:
        learning = self.repository.read("learning")
        learning["learning_core"]["version"] = "0.4.0"
        write_yaml(self.root / "learning.yaml", learning)
        evidence_id = self.attempt(
            "initial",
            "2026-09-14",
            "hard",
            include_evaluated=False,
        )
        self.assertEqual([], self.repository.list_gaps())
        self.assertEqual([], self.repository.detect_weak_signals(evidence_id))
        self.assertEqual([], self.repository.update_gaps_for_evidence(evidence_id))

        learning["learning_core"]["version"] = "0.5.0"
        write_yaml(self.root / "learning.yaml", learning)
        self.assertEqual([], self.repository.validate_repository())

    def test_new_stage5_assessment_requires_evaluated(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires evaluated"):
            self.attempt(
                "initial",
                "2026-09-14",
                "hard",
                include_evaluated=False,
            )

    def test_interest_graph_expansion_activation_and_routing_reason(self) -> None:
        self.add_existing_storage_branch()
        delta = {
            "nodes": [
                {"id": "document-databases", "title": "Document databases", "type": "concept", "importance": "supporting"},
                {"id": "wide-column-databases", "title": "Wide-column databases", "type": "concept", "importance": "supporting"},
                {"id": "graph-databases", "title": "Graph databases", "type": "concept", "importance": "supporting"},
            ],
            "edges": [
                {"from": "document-databases", "to": "storage-selection", "type": "part-of"},
                {"from": "wide-column-databases", "to": "storage-selection", "type": "part-of"},
                {"from": "graph-databases", "to": "storage-selection", "type": "part-of"},
            ],
        }
        result = self.repository.expand_graph(delta)
        self.assertEqual(3, len(result["added_nodes"]))
        graph = self.repository.read("graph")
        self.assertNotIn("data-models", {node["id"] for node in graph["nodes"]})
        self.assertTrue(all(edge in graph["edges"] for edge in delta["edges"]))
        interest = {
            "format_version": 1,
            "id": "interest-non-relational-databases",
            "created_at": "2026-09-18T12:00:00+05:00",
            "source": "user",
            "request": "Хочу глубже изучить document, wide-column и graph databases.",
            "related_nodes": ["document-databases", "wide-column-databases", "graph-databases"],
            "status": "pending",
            "history": [{"status": "pending", "at": "2026-09-18T12:00:00+05:00"}],
        }
        self.repository.create_interest(interest)
        self.assertEqual("pending", self.repository.list_interests()[0]["status"])

        frontier = self.repository.read("frontier")
        frontier["units"][2]["nodes"] = ["graph-databases"]
        frontier["units"][2]["routing_reasons"] = [
            {"type": "primary-route"},
            {"type": "interest", "interest": interest["id"]},
        ]
        write_yaml(self.root / "map/frontier.yaml", frontier)
        self.assertEqual([], self.repository.validate_frontier())
        routing = self.repository.update_routing_metadata("2026-09-18T12:05:00+05:00")
        self.assertEqual([interest["id"]], routing["activated_interests"])
        self.assertEqual("active", self.repository.list_interests()[0]["status"])
        candidates = self.repository.session_candidates(25)["candidates"]
        routed = next(item for item in candidates if item["id"] == "unit-3")
        self.assertEqual([interest["id"]], routed["related_interests"])
        self.assertEqual([], self.repository.validate_repository())

    def test_automatic_disconnected_subtree_is_rejected_without_writing(self) -> None:
        original = self.repository.read("graph")
        delta = {
            "nodes": [
                {"id": "new-area", "title": "New area", "type": "area", "importance": "supporting"},
                {"id": "new-concept", "title": "New concept", "type": "concept", "importance": "supporting"},
            ],
            "edges": [{"from": "new-concept", "to": "new-area", "type": "part-of"}],
        }

        with self.assertRaisesRegex(ValueError, "new component not anchored to the existing graph"):
            self.repository.expand_graph(delta)

        self.assertEqual(original, self.repository.read("graph"))

    def test_anchored_subtree_is_accepted(self) -> None:
        delta = {
            "nodes": [
                {"id": "child-topic", "title": "Child topic", "type": "topic", "importance": "supporting"},
                {"id": "new-concept", "title": "New concept", "type": "concept", "importance": "supporting"},
            ],
            "edges": [
                {"from": "child-topic", "to": "replication", "type": "part-of"},
                {"from": "new-concept", "to": "child-topic", "type": "part-of"},
            ],
        }

        result = self.repository.expand_graph(delta)

        self.assertEqual(["child-topic", "new-concept"], result["added_nodes"])
        self.assertEqual([], self.repository.validate_graph())

    def test_explicitly_approved_structural_delta_may_add_a_root(self) -> None:
        delta = {
            "nodes": [
                {"id": "new-area", "title": "New area", "type": "area", "importance": "supporting"},
                {"id": "new-concept", "title": "New concept", "type": "concept", "importance": "supporting"},
            ],
            "edges": [{"from": "new-concept", "to": "new-area", "type": "part-of"}],
        }

        result = self.repository.expand_graph(delta, allow_unanchored=True)

        self.assertEqual(["new-area", "new-concept"], result["added_nodes"])
        self.assertEqual([], self.repository.validate_graph())

    def test_existing_multiple_roots_remain_valid(self) -> None:
        self.add_existing_storage_branch()

        self.assertEqual([], self.repository.validate_graph())
        result = self.repository.expand_graph(
            {
                "nodes": [
                    {
                        "id": "document-databases",
                        "title": "Document databases",
                        "type": "concept",
                        "importance": "supporting",
                    }
                ],
                "edges": [{"from": "document-databases", "to": "storage-selection", "type": "part-of"}],
            }
        )
        self.assertEqual(["document-databases"], result["added_nodes"])

    def test_stage5_frontier_requires_explainable_routing(self) -> None:
        frontier = self.repository.read("frontier")
        del frontier["units"][0]["routing_reasons"]
        issues = self.repository.validate_frontier(frontier)
        self.assertTrue(any("requires at least one routing reason" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
