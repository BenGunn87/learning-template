from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from learning_core import Repository  # noqa: E402
from learning import main as learning_main  # noqa: E402


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


class Stage6Test(unittest.TestCase):
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
            "resources/generated",
            ".agents/skills",
        ):
            (self.root / directory).mkdir(parents=True)
        write_yaml(
            self.root / "learning.yaml",
            {
                "format_version": 1,
                "topic": {"id": "system-design", "title": "System Design"},
                "learning_core": {"version": "0.6.0"},
                "created_at": "2026-09-20",
            },
        )
        write_yaml(
            self.root / "config/context.yaml",
            {
                "format_version": 1,
                "goal": {"why": "professional-growth", "outcome": "Design reliable data systems."},
                "experience": {"level": "beginner"},
                "depth": "working",
                "constraints": {"default_session_minutes": 25},
                "preferences": {"languages": ["en"], "resources": ["documentation"]},
                "diagnostic": {
                    "status": "completed",
                    "completed_at": "2026-09-20",
                    "areas": [{"area": "Quorum", "level": "weak"}],
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
                ],
                "edges": [{"from": "quorum", "to": "replication", "type": "part-of"}],
            },
        )
        units = [
            {
                "id": "quorum-reads-writes" if index == 1 else f"unit-{index}",
                "title": "Quorum reads and writes" if index == 1 else f"Unit {index}",
                "nodes": ["replication", "quorum"] if index == 1 else ["replication"],
                "goal": "Reason about consistency, latency, and availability.",
                "estimated_minutes": 25,
                "priority": "high" if index == 1 else "medium",
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
                "id": "quorum-reads-writes",
                "title": "Quorum reads and writes",
                "nodes": ["replication", "quorum"],
                "goal": "Understand quorum trade-offs.",
                "estimated_minutes": 25,
                "concepts": ["read quorum", "write quorum"],
                "study_focus": ["When do quorums intersect?", "What affects availability?"],
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

    @staticmethod
    def external(status: str = "completed") -> dict:
        return {
            "type": "external",
            "title": "Quorum documentation",
            "url": "https://example.com/quorum",
            "format": "documentation",
            "language": "en",
            "status": status,
        }

    @staticmethod
    def generated(status: str = "completed") -> dict:
        return {
            "type": "generated",
            "id": "resource-quorum-20260920-001",
            "path": "resources/generated/resource-quorum-20260920-001.md",
            "title": "Quorum reads and writes",
            "format": "article",
            "language": "en",
            "status": status,
        }

    @staticmethod
    def evidence_resources(resources: list[dict]) -> list[dict]:
        return [{key: value for key, value in resource.items() if key != "status"} for resource in resources]

    def generated_document(self, session_id: str) -> str:
        return f"""---
format_version: 1
id: resource-quorum-20260920-001
type: generated
format: article
created_at: 2026-09-20T10:02:00+05:00
unit: quorum-reads-writes
session: {session_id}
title: Quorum reads and writes
learning_goal: Understand how quorum choices affect consistency, latency, and availability.
depth: working
coverage:
  - quorum
sources: []
---

# Quorum reads and writes

Quorums coordinate which replicas participate in reads and writes. Their overlap is useful, but it is not by itself a complete consistency guarantee.
"""

    def checkpoint(
        self,
        mode: str,
        resources: list[dict],
        *,
        stage: str = "study",
        discussion_summary: dict | None = None,
    ) -> dict:
        result = {
            "unit": "quorum-reads-writes",
            "action": "study",
            "stage": stage,
            "completed_steps": {
                "mode_selected": True,
                "resources_prepared": bool(resources),
                "study_focus_shown": True,
                "study_completed": all(item["status"] == "completed" for item in resources),
                "recall_completed": stage in {"practice", "takeaways"},
                "practice_completed": stage == "takeaways",
            },
            "study_mode": mode,
            "resources": resources,
        }
        if discussion_summary is not None:
            result["discussion_summary"] = discussion_summary
        return result

    def create_resource(self, session_id: str) -> Path:
        path, outcome = self.repository.create_generated_resource(self.generated_document(session_id))
        self.assertEqual("created", outcome)
        return path

    def finish_attempt(
        self,
        session_id: str,
        resources: list[dict],
        *,
        grade: str = "good",
        completed_at: str = "2026-09-20T10:25:00+05:00",
    ) -> str:
        evidence_id = f"{session_id}-initial-001"
        evidence = {
            "format_version": 1,
            "id": evidence_id,
            "unit": "quorum-reads-writes",
            "session": session_id,
            "type": "initial",
            "created_at": "2026-09-20T10:20:00+05:00",
            "resources": self.evidence_resources(resources),
            "recall": {"prompts": ["What makes quorums overlap?"], "answers": ["R + W greater than N."]},
            "practice": {"prompt": "Choose R and W for N=3.", "answer": "R=2 and W=2 for overlap."},
            "takeaways": ["Intersection is useful but is not a complete consistency guarantee."],
            "observations": [],
        }
        self.repository.create_evidence(evidence)
        result = {"recall": "good", "understanding": grade, "application": grade}
        self.repository.create_assessment(
            {
                "format_version": 1,
                "id": f"{evidence_id}-assessment-001",
                "evidence": evidence_id,
                "type": "initial",
                "created_at": "2026-09-20T10:22:00+05:00",
                "result": result,
                "evaluated": {
                    "recall": {"nodes": ["quorum"]},
                    "understanding": {"nodes": ["quorum"]},
                    "application": {"nodes": ["quorum"]},
                },
                "gaps": [] if grade == "good" else ["Quorum guarantees need clarification."],
                "summary": "Independent quorum check.",
            }
        )
        self.repository.rebuild_progress()
        self.repository.complete_session(session_id, [evidence_id], completed_at)
        return evidence_id

    def test_external_mode_keeps_existing_pipeline_with_canonical_format(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        resources = [self.external()]
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("external", resources, stage="takeaways"), "2026-09-20T10:18:00+05:00", "completed"
        )
        evidence_id = self.finish_attempt(session["id"], resources)
        stored_session = yaml.safe_load((self.root / f"sessions/{session['id']}.yaml").read_text())
        stored_evidence = yaml.safe_load((self.root / f"evidence/quorum-reads-writes/{evidence_id}.yaml").read_text())
        self.assertEqual("external", stored_session["study"]["mode"])
        self.assertEqual("documentation", stored_session["study"]["resources"][0]["format"])
        self.assertNotIn("resource", stored_evidence)
        self.assertEqual([], self.repository.validate_repository())

    def test_create_session_with_one_study_action_is_valid(self) -> None:
        _, session = self.repository.create_session(
            None,
            25,
            "2026-09-20T10:00:00+05:00",
            [{"type": "study", "unit": "quorum-reads-writes"}],
        )
        self.assertEqual([], self.repository.validate_session(session))

    def test_create_session_with_multiple_allowed_non_study_actions_remains_valid(self) -> None:
        progress = {
            "quorum-reads-writes": {"status": "practice"},
            "unit-2": {"status": "practice"},
        }
        with patch.object(self.repository, "read_progress", return_value=progress):
            _, session = self.repository.create_session(
                None,
                25,
                "2026-09-20T10:00:00+05:00",
                [
                    {"type": "practice", "unit": "quorum-reads-writes"},
                    {"type": "practice", "unit": "unit-2"},
                ],
            )
        self.assertEqual([], self.repository.validate_session(session))

    def test_create_session_with_two_study_actions_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "supports only one Study attempt per Session"):
            self.repository.create_session(
                None,
                25,
                "2026-09-20T10:00:00+05:00",
                [
                    {"type": "study", "unit": "quorum-reads-writes"},
                    {"type": "study", "unit": "unit-2"},
                ],
            )
        self.assertEqual([], list((self.root / "sessions").glob("*.yaml")))

        errors = StringIO()
        with redirect_stderr(errors):
            result = learning_main(
                [
                    "--root",
                    str(self.root),
                    "create-session",
                    "--minutes",
                    "25",
                    "--started-at",
                    "2026-09-20T10:00:00+05:00",
                    "--action",
                    "study:quorum-reads-writes",
                    "--action",
                    "study:unit-2",
                ]
            )
        self.assertEqual(1, result)
        self.assertIn("supports only one Study attempt per Session", errors.getvalue())
        self.assertEqual([], list((self.root / "sessions").glob("*.yaml")))

    def test_validation_rejects_manual_session_file_with_two_study_actions(self) -> None:
        path, session = self.repository.create_session(
            None,
            25,
            "2026-09-20T10:00:00+05:00",
            [{"type": "study", "unit": "quorum-reads-writes"}],
        )
        session["plan"]["actions"].append({"type": "study", "unit": "unit-2"})
        session["actual"]["actions"].append({"type": "study", "unit": "unit-2", "status": "planned"})
        write_yaml(path, session)
        issues = self.repository.validate_session(session["id"])
        self.assertTrue(
            any("supports only one Study attempt per Session" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_generated_mode_persists_primary_document_and_reuses_it_after_resume(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        resource_path = self.create_resource(session["id"])
        original = resource_path.read_bytes()
        selected = [self.generated("selected")]
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("generated", selected), "2026-09-20T10:08:00+05:00"
        )
        self.repository.pause_session(session["id"], paused_at="2026-09-20T10:10:00+05:00")
        _, resumed, _ = self.repository.resume_session(session["id"], 20, "2026-09-20T11:00:00+05:00")
        self.assertEqual("resource-quorum-20260920-001", resumed["checkpoint"]["resources"][0]["id"])
        self.assertEqual(original, resource_path.read_bytes())

        completed = [self.generated()]
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("generated", completed, stage="takeaways"), "2026-09-20T11:15:00+05:00", "completed"
        )
        evidence_id = self.finish_attempt(session["id"], completed, completed_at="2026-09-20T11:20:00+05:00")
        before_rebuild = resource_path.read_bytes()
        self.repository.rebuild_progress()
        self.assertEqual(before_rebuild, resource_path.read_bytes())
        evidence = yaml.safe_load((self.root / f"evidence/quorum-reads-writes/{evidence_id}.yaml").read_text())
        self.assertEqual("resource-quorum-20260920-001", evidence["resources"][0]["id"])

    def test_cli_creates_and_validates_generated_resource(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        draft = self.root / "generated-resource.md"
        draft.write_text(self.generated_document(session["id"]), encoding="utf-8")
        with redirect_stdout(StringIO()):
            created = learning_main(["--root", str(self.root), "create-generated-resource", str(draft)])
            validated = learning_main(
                ["--root", str(self.root), "validate", "resource", "resource-quorum-20260920-001"]
            )
        self.assertEqual(0, created)
        self.assertEqual(0, validated)

    def _run_hybrid_order(self, first_type: str) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        resource_path = self.create_resource(session["id"])
        first = self.external() if first_type == "external" else self.generated()
        second = self.generated("selected") if first_type == "external" else self.external("selected")
        partial = [first, second]
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("hybrid", partial), "2026-09-20T10:08:00+05:00"
        )
        self.repository.pause_session(session["id"], paused_at="2026-09-20T10:10:00+05:00")
        _, resumed, _ = self.repository.resume_session(session["id"], 20, "2026-09-20T11:00:00+05:00")
        self.assertEqual(["completed", "selected"], [item["status"] for item in resumed["checkpoint"]["resources"]])
        self.assertEqual([first_type], [item["type"] for item in resumed["study"]["resources"]])

        completed = [{**item, "status": "completed"} for item in partial]
        summary = {
            "clarifications": ["Quorum overlap and consistency guarantees are separate claims."],
            "assessment_focus": ["explain what overlap does and does not guarantee"],
        }
        self.repository.update_checkpoint(
            session["id"],
            self.checkpoint("hybrid", completed, stage="takeaways", discussion_summary=summary),
            "2026-09-20T11:15:00+05:00",
            "completed",
        )
        evidence_id = self.finish_attempt(session["id"], completed, completed_at="2026-09-20T11:20:00+05:00")
        evidence = yaml.safe_load((self.root / f"evidence/quorum-reads-writes/{evidence_id}.yaml").read_text())
        self.assertEqual([item["type"] for item in completed], [item["type"] for item in evidence["resources"]])
        stored_session = yaml.safe_load((self.root / f"sessions/{session['id']}.yaml").read_text())
        self.assertEqual(summary, stored_session["study"]["discussion_summary"])
        before = resource_path.read_bytes()
        self.repository.rebuild_progress()
        self.assertEqual(before, resource_path.read_bytes())
        self.assertEqual([], self.repository.validate_repository())

    def test_hybrid_supports_external_then_generated_with_partial_pause(self) -> None:
        self._run_hybrid_order("external")

    def test_hybrid_supports_generated_then_external_with_partial_pause(self) -> None:
        self._run_hybrid_order("generated")

    def test_discussion_summary_is_study_state_and_only_evidence_can_create_gap(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        summary = {
            "questions_raised": ["Is quorum intersection sufficient for linearizability?"],
            "possible_gaps": ["relationship between intersection and consistency guarantees"],
            "new_interests": ["sloppy quorum"],
            "assessment_focus": ["distinguish intersection from consistency guarantees"],
        }
        resources = [self.external()]
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("external", resources, discussion_summary=summary), "2026-09-20T10:12:00+05:00"
        )
        stored = yaml.safe_load((self.root / f"sessions/{session['id']}.yaml").read_text())
        self.assertEqual(summary, stored["study"]["discussion_summary"])
        self.assertEqual([], stored["evidence"])
        self.assertEqual({}, self.repository.read_progress())
        self.assertEqual([], self.repository.list_gaps())
        self.assertEqual([], self.repository.list_interests())

        self.repository.create_interest(
            {
                "format_version": 1,
                "id": "interest-sloppy-quorum",
                "created_at": "2026-09-20T10:13:00+05:00",
                "source": "user",
                "request": "I want to study sloppy quorum later.",
                "related_nodes": ["quorum"],
                "status": "pending",
                "history": [{"status": "pending", "at": "2026-09-20T10:13:00+05:00"}],
            }
        )
        self.assertEqual(["interest-sloppy-quorum"], [item["id"] for item in self.repository.list_interests()])

        self.repository.update_checkpoint(
            session["id"], self.checkpoint("external", resources, stage="takeaways", discussion_summary=summary), "2026-09-20T10:18:00+05:00", "completed"
        )
        self.finish_attempt(session["id"], resources, grade="hard")
        gaps = self.repository.list_gaps()
        self.assertTrue(gaps)
        self.assertTrue(all(signal["evidence"] for gap in gaps for signal in gap["signals"]))

    def test_no_meaningful_discussion_does_not_create_summary(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        self.repository.update_checkpoint(
            session["id"], self.checkpoint("external", [self.external()]), "2026-09-20T10:12:00+05:00"
        )
        stored = yaml.safe_load((self.root / f"sessions/{session['id']}.yaml").read_text())
        self.assertNotIn("discussion_summary", stored["study"])

    def test_legacy_resource_records_validate_but_new_stage6_evidence_must_use_resources(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        legacy = {
            "format_version": 1,
            "id": f"{session['id']}-initial-001",
            "unit": "quorum-reads-writes",
            "session": session["id"],
            "type": "initial",
            "created_at": "2026-09-20T10:20:00+05:00",
            "resource": {
                "title": "Legacy article",
                "url": "https://example.com/legacy",
                "type": "article",
                "language": "en",
            },
            "recall": {"prompts": ["What is a quorum?"], "answers": ["A replica subset."]},
            "practice": {"prompt": "Choose a quorum.", "answer": "R=2, W=2."},
            "takeaways": ["Legacy data remains readable."],
            "observations": [],
        }
        self.assertEqual([], self.repository.validate_evidence(legacy, "evidence/quorum-reads-writes/2026-09-20-001-initial-001.yaml"))
        with self.assertRaisesRegex(ValueError, "requires resources"):
            self.repository.create_evidence(legacy)

    def test_invalid_generated_reference_and_structure_are_reported(self) -> None:
        _, session = self.repository.create_session("quorum-reads-writes", 25, "2026-09-20T10:00:00+05:00")
        invalid = self.generated_document(session["id"]).replace("  - quorum", "  - unknown-node")
        with self.assertRaisesRegex(ValueError, "unknown node"):
            self.repository.create_generated_resource(invalid)
        checkpoint = self.checkpoint("generated", [self.generated("selected")])
        issues = self.repository.validate_session(
            {**session, "checkpoint": {"updated_at": "2026-09-20T10:05:00+05:00", **checkpoint}},
            f"sessions/{session['id']}.yaml",
        )
        self.assertTrue(any("does not exist" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
