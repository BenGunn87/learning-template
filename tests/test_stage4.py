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


class Stage4Test(unittest.TestCase):
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
                "learning_core": {"version": "0.4.0"},
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
        self.repository.create_unit(self.unit())

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
    def checkpoint(stage: str = "study") -> dict:
        return {
            "unit": "define-requirements",
            "action": "study",
            "stage": stage,
            "completed_steps": {
                "resource_selected": True,
                "study_focus_shown": True,
                "study_completed": stage != "study",
                "recall_completed": False,
                "practice_completed": False,
            },
            "resource": {
                "title": "System Design Primer",
                "url": "https://example.com/system-design",
                "type": "article",
                "language": "en",
            },
        }

    def start(self, at: str = "2026-09-15T10:00:00+05:00") -> tuple[Path, dict]:
        return self.repository.create_session("define-requirements", 25, at)

    def record_initial_attempt(
        self,
        session_id: str,
        day: str,
        result: dict[str, str] | None = None,
    ) -> str:
        result = result or {"recall": "good", "understanding": "good", "application": "good"}
        evidence_id = f"{session_id}-initial-001"
        self.repository.create_evidence(
            {
                "format_version": 1,
                "id": evidence_id,
                "unit": "define-requirements",
                "session": session_id,
                "type": "initial",
                "created_at": f"{day}T10:20:00+05:00",
                "resource": {
                    "title": "System Design Primer",
                    "url": "https://example.com/system-design",
                    "type": "article",
                    "language": "en",
                },
                "recall": {"prompts": ["What are constraints?"], "answers": ["Hard limits."]},
                "practice": {"prompt": "Define requirements.", "answer": "State scale and SLOs."},
                "takeaways": ["Constraints shape architecture."],
                "observations": [],
            }
        )
        self.repository.create_assessment(
            {
                "format_version": 1,
                "id": f"{evidence_id}-assessment-001",
                "evidence": evidence_id,
                "type": "initial",
                "created_at": f"{day}T10:22:00+05:00",
                "result": result,
                "gaps": [],
                "summary": "Completed attempt.",
            }
        )
        self.repository.rebuild_progress()
        return evidence_id

    def create_verified_attempt(self) -> str:
        _, session = self.repository.create_session(
            "define-requirements", 25, "2026-09-14T10:00:00+05:00"
        )
        evidence_id = self.record_initial_attempt(session["id"], "2026-09-14")
        self.repository.complete_session(session["id"], [evidence_id], "2026-09-14T10:25:00+05:00")
        return evidence_id

    def test_pause_saves_checkpoint_without_evidence_or_progress_change(self) -> None:
        _, session = self.start()
        self.repository.update_checkpoint(
            session["id"], self.checkpoint(), "2026-09-15T10:08:00+05:00"
        )
        _, paused, outcome = self.repository.pause_session(
            session["id"], paused_at="2026-09-15T10:10:00+05:00"
        )
        self.assertEqual("paused", outcome)
        self.assertEqual("paused", paused["status"])
        self.assertEqual("2026-09-15T10:10:00+05:00", paused["checkpoint"]["updated_at"])
        self.assertEqual("paused", paused["segments"][0]["end_reason"])
        self.assertEqual([], paused["evidence"])
        self.assertEqual({}, self.repository.read_progress())
        self.assertEqual("already-paused", self.repository.pause_session(session["id"])[2])

    def test_resume_keeps_session_id_resource_and_does_not_duplicate_segment(self) -> None:
        _, session = self.start()
        self.repository.update_checkpoint(session["id"], self.checkpoint(), "2026-09-15T10:08:00+05:00")
        self.repository.pause_session(session["id"], paused_at="2026-09-15T10:10:00+05:00")
        _, resumed, outcome = self.repository.resume_session(
            session["id"], 15, "2026-09-16T09:00:00+05:00"
        )
        self.assertEqual("resumed", outcome)
        self.assertEqual(session["id"], resumed["id"])
        self.assertEqual(2, len(resumed["segments"]))
        self.assertEqual(15, resumed["segments"][-1]["budget_minutes"])
        self.assertEqual("System Design Primer", resumed["checkpoint"]["resource"]["title"])
        _, repeated, repeat_outcome = self.repository.resume_session(session["id"], 15)
        self.assertEqual("already-active", repeat_outcome)
        self.assertEqual(2, len(repeated["segments"]))

    def test_partial_practice_interaction_survives_pause_and_resume(self) -> None:
        _, session = self.start()
        checkpoint = self.checkpoint("practice")
        checkpoint["interaction"] = {
            "scenario": "Choose a consistency model for a collaborative editor.",
            "answers": [{"stage": "practice", "answer": "I would begin with eventual consistency."}],
        }
        self.repository.update_checkpoint(session["id"], checkpoint, "2026-09-15T10:12:00+05:00")
        self.repository.pause_session(session["id"], paused_at="2026-09-15T10:13:00+05:00")
        _, resumed, _ = self.repository.resume_session(session["id"], 20, "2026-09-16T10:00:00+05:00")
        self.assertEqual(checkpoint["interaction"], resumed["checkpoint"]["interaction"])
        self.assertEqual("practice", resumed["checkpoint"]["stage"])

    def test_recovery_closes_at_last_checkpoint_and_is_idempotent(self) -> None:
        _, session = self.start()
        self.repository.update_checkpoint(session["id"], self.checkpoint(), "2026-09-15T10:08:00+05:00")
        _, recovered, outcome = self.repository.recover_session(
            session["id"], 20, "2026-09-16T09:00:00+05:00"
        )
        self.assertEqual("recovered", outcome)
        self.assertEqual("2026-09-15T10:08:00+05:00", recovered["segments"][0]["ended_at"])
        self.assertEqual("recovered", recovered["segments"][0]["end_reason"])
        self.assertEqual(
            {
                "recovered_at": "2026-09-16T09:00:00+05:00",
                "segment_closed_at": "2026-09-15T10:08:00+05:00",
                "source": "checkpoint",
            },
            recovered["last_recovery"],
        )
        self.assertEqual(8, self.repository.calculate_active_minutes(session["id"]))
        _, repeated, repeat_outcome = self.repository.recover_session(
            session["id"], 20, "2026-09-16T09:00:00+05:00"
        )
        self.assertEqual("already-recovered", repeat_outcome)
        self.assertEqual(2, len(repeated["segments"]))

    def test_recovery_without_checkpoint_requires_user_input(self) -> None:
        _, session = self.start()
        with self.assertRaisesRegex(ValueError, "user input is required"):
            self.repository.recover_session(session["id"], 20, "2026-09-16T09:00:00+05:00")

    def test_recovery_without_checkpoint_closes_at_segment_start(self) -> None:
        _, session = self.start()
        reconstructed = self.checkpoint("study_focus")
        _, recovered, outcome = self.repository.recover_session(
            session["id"],
            20,
            "2026-09-16T09:00:00+05:00",
            reconstructed,
        )
        self.assertEqual("recovered", outcome)
        self.assertEqual("2026-09-15T10:00:00+05:00", recovered["segments"][0]["ended_at"])
        self.assertEqual("2026-09-16T09:00:00+05:00", recovered["segments"][1]["started_at"])
        self.assertEqual("2026-09-16T09:00:00+05:00", recovered["checkpoint"]["updated_at"])
        self.assertEqual("study_focus", recovered["checkpoint"]["stage"])
        self.assertEqual(
            {
                "recovered_at": "2026-09-16T09:00:00+05:00",
                "segment_closed_at": "2026-09-15T10:00:00+05:00",
                "source": "segment_start",
            },
            recovered["last_recovery"],
        )
        self.assertEqual(0, self.repository.calculate_active_minutes(session["id"]))

        _, repeated, repeat_outcome = self.repository.recover_session(
            session["id"],
            20,
            "2026-09-16T09:00:00+05:00",
            reconstructed,
        )
        self.assertEqual("already-recovered", repeat_outcome)
        self.assertEqual(2, len(repeated["segments"]))
        self.assertEqual(0, self.repository.calculate_active_minutes(session["id"]))

    def test_unit_completes_once_across_three_segments(self) -> None:
        _, session = self.start("2026-09-15T10:00:00+05:00")
        self.repository.update_checkpoint(session["id"], self.checkpoint(), "2026-09-15T10:04:00+05:00")
        self.repository.pause_session(session["id"], paused_at="2026-09-15T10:05:00+05:00")

        self.repository.resume_session(session["id"], 15, "2026-09-16T10:00:00+05:00")
        practice_checkpoint = self.checkpoint("practice")
        practice_checkpoint["interaction"] = {
            "scenario": "Define requirements for a URL shortener.",
            "answers": [{"stage": "practice", "answer": "Prioritize redirect availability."}],
        }
        self.repository.update_checkpoint(
            session["id"], practice_checkpoint, "2026-09-16T10:04:00+05:00"
        )
        self.repository.pause_session(session["id"], paused_at="2026-09-16T10:05:00+05:00")

        self.repository.resume_session(session["id"], 10, "2026-09-17T10:00:00+05:00")
        evidence_id = self.record_initial_attempt(session["id"], "2026-09-17")
        _, completed, outcome = self.repository.complete_session(
            session["id"], [evidence_id], "2026-09-17T10:25:00+05:00"
        )
        self.assertEqual("completed", outcome)
        self.assertEqual(3, len(completed["segments"]))
        self.assertEqual([evidence_id], completed["evidence"])
        self.assertEqual(1, self.repository.read_progress()["define-requirements"]["attempts"])
        self.assertEqual(35, self.repository.calculate_active_minutes(session["id"]))
        self.assertEqual(
            "already-completed",
            self.repository.complete_session(session["id"], [evidence_id])[2],
        )

    def test_paused_session_blocks_creation_of_another_session(self) -> None:
        _, session = self.start()
        self.repository.update_checkpoint(session["id"], self.checkpoint(), "2026-09-15T10:08:00+05:00")
        self.repository.pause_session(session["id"], paused_at="2026-09-15T10:10:00+05:00")
        with self.assertRaisesRegex(ValueError, "unfinished Session already exists"):
            self.repository.create_session("unit-2", 25, "2026-09-16T10:00:00+05:00")

    def test_repository_validation_rejects_two_unfinished_sessions(self) -> None:
        _, session = self.start()
        second = yaml.safe_load(yaml.safe_dump(session))
        second["id"] = "2026-09-15-002"
        second["started_at"] = "2026-09-15T11:00:00+05:00"
        second["segments"][0]["started_at"] = "2026-09-15T11:00:00+05:00"
        write_yaml(self.root / "sessions/2026-09-15-002.yaml", second)
        issues = self.repository.validate_repository()
        self.assertTrue(any("at most one active or paused Session" in issue.message for issue in issues))

    def test_review_plus_oversized_unit_is_planned_as_partial(self) -> None:
        self.create_verified_attempt()
        plan = self.repository.plan_session_candidates(25, "2026-09-21")
        self.assertEqual(
            {"type": "review", "unit": "define-requirements"},
            plan["suggested_actions"][0],
        )
        self.assertEqual(
            {"type": "study", "unit": "unit-2", "partial": True, "available_minutes": 20},
            plan["suggested_actions"][1],
        )

    def test_planner_does_not_start_a_unit_below_partial_threshold(self) -> None:
        plan = self.repository.plan_session_candidates(9, "2026-09-15")
        self.assertEqual([], plan["suggested_actions"])

    def test_completion_without_started_action_closes_segment_without_evidence(self) -> None:
        _, session = self.start()
        _, completed, outcome = self.repository.complete_session(
            session["id"], [], "2026-09-15T10:03:00+05:00"
        )
        self.assertEqual("completed", outcome)
        self.assertEqual("completed", completed["status"])
        self.assertEqual([], completed["evidence"])
        self.assertEqual("planned", completed["actual"]["actions"][0]["status"])
        self.assertEqual(3, self.repository.calculate_active_minutes(session["id"]))

    def test_status_describes_checkpoint_from_repository(self) -> None:
        _, session = self.start()
        self.repository.update_checkpoint(session["id"], self.checkpoint(), "2026-09-15T10:08:00+05:00")
        self.repository.pause_session(session["id"], paused_at="2026-09-15T10:10:00+05:00")
        status = Repository(self.root).render_status("2026-09-15")
        self.assertIn("Paused Session:", status)
        self.assertIn("Unit: Define requirements", status)
        self.assertIn("Stage: study", status)
        self.assertIn("Resource: System Design Primer", status)
        self.assertIn("Active time: 10 min", status)

    def test_cli_checkpoint_pause_resume_and_active_minutes(self) -> None:
        _, session = self.start()
        checkpoint_path = self.root / "checkpoint.yaml"
        write_yaml(checkpoint_path, self.checkpoint())
        commands = [
            [
                "--root", str(self.root), "update-checkpoint", session["id"], str(checkpoint_path),
                "--updated-at", "2026-09-15T10:08:00+05:00",
            ],
            [
                "--root", str(self.root), "pause-session", session["id"],
                "--paused-at", "2026-09-15T10:10:00+05:00",
            ],
            [
                "--root", str(self.root), "resume-session", session["id"], "--minutes", "15",
                "--resumed-at", "2026-09-16T09:00:00+05:00",
            ],
            ["--root", str(self.root), "calculate-active-minutes", session["id"]],
        ]
        output = StringIO()
        with redirect_stdout(output):
            for command in commands:
                self.assertEqual(0, learning_main(command), command)
        self.assertIn("active_minutes: 10", output.getvalue())

    def test_cli_recovers_without_saved_checkpoint_from_semantic_state(self) -> None:
        _, session = self.start()
        checkpoint_path = self.root / "reconstructed-checkpoint.yaml"
        write_yaml(checkpoint_path, self.checkpoint("study_focus"))
        command = [
            "--root", str(self.root), "recover-session", session["id"],
            "--minutes", "20",
            "--recovered-at", "2026-09-16T09:00:00+05:00",
            "--checkpoint", str(checkpoint_path),
        ]
        with redirect_stdout(StringIO()):
            self.assertEqual(0, learning_main(command))
        recovered = yaml.safe_load((self.root / f"sessions/{session['id']}.yaml").read_text(encoding="utf-8"))
        self.assertEqual("2026-09-15T10:00:00+05:00", recovered["segments"][0]["ended_at"])
        self.assertEqual("segment_start", recovered["last_recovery"]["source"])
        self.assertEqual("2026-09-16T09:00:00+05:00", recovered["checkpoint"]["updated_at"])


if __name__ == "__main__":
    unittest.main()
