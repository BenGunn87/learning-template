from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from learning_core import Repository  # noqa: E402
from learning import main as learning_main  # noqa: E402


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


class Stage2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copytree(PROJECT_ROOT / "schemas", self.root / "schemas")
        for directory in ("units", "evidence", "assessments", "sessions", "progress", "indexes", "scripts", ".agents/skills"):
            (self.root / directory).mkdir(parents=True)
        write_yaml(
            self.root / "learning.yaml",
            {
                "format_version": 1,
                "topic": {"id": "system-design", "title": "System Design"},
                "learning_core": {"version": "0.3.0"},
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
                    "areas": [{"area": "Requirements", "level": "weak"}],
                },
            },
        )
        write_yaml(
            self.root / "config/settings.yaml",
            {
                "session": {"default_minutes": 25},
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
                    {"id": "design-process", "title": "Design process", "type": "area", "importance": "core"},
                    {"id": "requirements", "title": "Requirements", "type": "concept", "importance": "core"},
                ],
                "edges": [{"from": "requirements", "to": "design-process", "type": "part-of"}],
            },
        )
        units = [
            {
                "id": "define-requirements" if index == 1 else f"unit-{index}",
                "title": "Define requirements" if index == 1 else f"Unit {index}",
                "nodes": ["design-process", "requirements"] if index == 1 else ["design-process"],
                "goal": "Make one concrete design decision.",
                "estimated_minutes": 25,
                "priority": "high" if index == 1 else "medium",
            }
            for index in range(1, 6)
        ]
        write_yaml(
            self.root / "map/frontier.yaml",
            {"format_version": 1, "focus": {"primary": "design-process", "secondary": []}, "units": units},
        )
        self.repository = Repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def unit() -> dict:
        return {
            "format_version": 1,
            "id": "define-requirements",
            "title": "Define requirements",
            "nodes": ["design-process", "requirements"],
            "goal": "Separate requirements, constraints, assumptions, and scope.",
            "estimated_minutes": 25,
            "concepts": ["functional requirements", "constraints"],
            "study_focus": ["What changes architecture?", "Where should scope be limited?"],
            "practice": {"type": "scenario", "goal": "Define requirements for a backend service."},
            "verification": {
                "recall": {"enabled": True},
                "understanding": {"enabled": True},
                "application": {"enabled": True},
            },
        }

    @staticmethod
    def evidence(session_id: str = "2026-09-14-001") -> dict:
        return {
            "format_version": 1,
            "id": f"{session_id}-initial",
            "unit": "define-requirements",
            "session": session_id,
            "type": "initial",
            "created_at": "2026-09-14T10:20:00+05:00",
            "resource": {
                "title": "System Design Primer",
                "url": "https://example.com/system-design",
                "type": "article",
                "language": "en",
            },
            "recall": {
                "prompts": ["What are constraints?", "Why limit scope?"],
                "answers": ["Hard limits on a design.", "To make the problem tractable."],
            },
            "practice": {
                "prompt": "Define requirements for a URL shortener.",
                "answer": "Shorten and redirect URLs; prioritize read latency and availability.",
            },
            "takeaways": ["Constraints shape architecture.", "Scope must be explicit."],
            "observations": ["Application omitted capacity assumptions."],
        }

    @staticmethod
    def assessment(evidence_id: str = "2026-09-14-001-initial") -> dict:
        return {
            "format_version": 1,
            "id": f"{evidence_id}-assessment-001",
            "evidence": evidence_id,
            "type": "initial",
            "created_at": "2026-09-14T10:22:00+05:00",
            "result": {"recall": "good", "understanding": "good", "application": "hard"},
            "gaps": ["Capacity constraints were not explicit."],
            "summary": "Understands requirements but needs application practice.",
        }

    def start(self) -> str:
        path, data = self.repository.create_session(
            "define-requirements",
            25,
            "2026-09-14T10:00:00+05:00",
        )
        self.assertTrue(path.is_file())
        return data["id"]

    def initialize(self) -> None:
        self.repository.create_unit(self.unit())

    def record_attempt(self) -> tuple[str, str]:
        session_id = self.start()
        self.initialize()
        evidence = self.evidence(session_id)
        self.repository.create_evidence(evidence)
        assessment = self.assessment(evidence["id"])
        self.repository.create_assessment(assessment)
        return session_id, evidence["id"]

    def assert_issue_contains(self, issues, text: str) -> None:
        self.assertTrue(any(text in issue.render() for issue in issues), [issue.render() for issue in issues])

    def test_unit_rejects_unknown_graph_node(self) -> None:
        unit = self.unit()
        unit["nodes"] = ["missing"]
        self.assert_issue_contains(self.repository.validate_unit(unit), "unknown node")

    def test_unit_rejects_progress_fields(self) -> None:
        unit = self.unit()
        unit["mastery"] = {"recall": "good"}
        self.assert_issue_contains(self.repository.validate_unit(unit), "Additional properties")

    def test_evidence_references_known_unit_and_session(self) -> None:
        self.start()
        evidence = self.evidence()
        self.assert_issue_contains(self.repository.validate_evidence(evidence), "unknown Unit")
        self.initialize()
        evidence["session"] = "2026-09-14-999"
        self.assert_issue_contains(self.repository.validate_evidence(evidence), "unknown Session")

    def test_duplicate_evidence_id_is_refused(self) -> None:
        session_id = self.start()
        self.initialize()
        evidence = self.evidence(session_id)
        self.repository.create_evidence(evidence)
        with self.assertRaisesRegex(ValueError, "duplicate Evidence id"):
            self.repository.create_evidence(evidence)

    def test_assessment_requires_evidence_and_enum(self) -> None:
        assessment = self.assessment("missing-evidence")
        self.assert_issue_contains(self.repository.validate_assessment(assessment), "unknown Evidence")
        assessment["result"]["application"] = "excellent"
        self.assert_issue_contains(self.repository.validate_assessment(assessment), "is not one of")

    def test_progress_is_derived_from_assessment(self) -> None:
        _, evidence_id = self.record_attempt()
        progress = self.repository.rebuild_progress()
        item = progress["define-requirements"]
        self.assertEqual("practice", item["status"])
        self.assertEqual(1, item["attempts"])
        self.assertEqual(evidence_id, item["latest_evidence"])

    def test_verified_unit_is_not_a_next_candidate(self) -> None:
        self.record_attempt()
        assessment_path = self.root / "assessments/2026-09-14-001-initial/001.yaml"
        assessment = yaml.safe_load(assessment_path.read_text(encoding="utf-8"))
        assessment["result"]["application"] = "good"
        write_yaml(assessment_path, assessment)
        self.repository.rebuild_progress()
        candidates = self.repository.session_candidates(25)["candidates"]
        self.assertNotIn("define-requirements", {candidate["id"] for candidate in candidates})

    def test_session_completion_requires_existing_evidence(self) -> None:
        session_id = self.start()
        with self.assertRaisesRegex(ValueError, "unknown or duplicate Evidence"):
            self.repository.complete_session(session_id, ["missing-evidence"])

    def test_complete_session_links_evidence_after_progress(self) -> None:
        session_id, evidence_id = self.record_attempt()
        self.repository.rebuild_progress()
        _, session, outcome = self.repository.complete_session(
            session_id,
            [evidence_id],
            "2026-09-14T10:25:00+05:00",
        )
        self.assertEqual("completed", outcome)
        self.assertEqual("completed", session["status"])
        self.assertEqual("define-requirements", session["actual"]["unit"])
        self.assertEqual([evidence_id], session["evidence"])
        self.assertEqual([], self.repository.validate_repository())

    def test_new_repository_context_renders_persisted_status(self) -> None:
        session_id, evidence_id = self.record_attempt()
        self.repository.rebuild_progress()
        self.repository.complete_session(
            session_id,
            [evidence_id],
            "2026-09-14T10:25:00+05:00",
        )

        status = Repository(self.root).render_status()
        self.assertIn("Completed attempts: 1", status)
        self.assertIn("Needs practice:", status)
        self.assertIn("Capacity constraints were not explicit.", status)
        self.assertIn("Next:", status)

    def test_second_active_session_is_refused(self) -> None:
        session_id = self.start()
        with self.assertRaisesRegex(ValueError, session_id):
            self.repository.create_session("unit-2", 25, "2026-09-14T11:00:00+05:00")

    def test_cli_runs_complete_stage2_write_sequence(self) -> None:
        unit_input = self.root / "unit-input.yaml"
        evidence_input = self.root / "evidence-input.yaml"
        assessment_input = self.root / "assessment-input.yaml"
        write_yaml(unit_input, self.unit())
        write_yaml(evidence_input, self.evidence())
        write_yaml(assessment_input, self.assessment())

        commands = [
            ["--root", str(self.root), "create-session", "--unit", "define-requirements", "--minutes", "25", "--started-at", "2026-09-14T10:00:00+05:00"],
            ["--root", str(self.root), "create-unit", str(unit_input)],
            ["--root", str(self.root), "create-evidence", str(evidence_input)],
            ["--root", str(self.root), "create-assessment", str(assessment_input)],
            ["--root", str(self.root), "update-progress"],
            ["--root", str(self.root), "complete-session", "2026-09-14-001", "--evidence", "2026-09-14-001-initial", "--completed-at", "2026-09-14T10:25:00+05:00"],
        ]
        with redirect_stdout(StringIO()):
            for command in commands:
                self.assertEqual(0, learning_main(command), command)
        session = yaml.safe_load((self.root / "sessions/2026-09-14-001.yaml").read_text(encoding="utf-8"))
        self.assertEqual("completed", session["status"])

    def test_failed_recall_takes_priority_over_application_hard(self) -> None:
        result = {
            "recall": "failed",
            "understanding": "good",
            "application": "hard",
        }

        self.assertEqual("learning", self.repository._progress_status(result))

if __name__ == "__main__":
    unittest.main()
