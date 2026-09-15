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


class Stage3Test(unittest.TestCase):
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
        frontier_units = [
            {
                "id": "define-requirements" if index == 1 else f"unit-{index}",
                "title": "Define requirements" if index == 1 else f"Unit {index}",
                "nodes": ["design-process", "requirements"] if index == 1 else ["design-process"],
                "goal": "Make one concrete design decision.",
                "estimated_minutes": 20 if index == 2 else 25,
                "priority": "high" if index == 1 else "medium",
            }
            for index in range(1, 6)
        ]
        write_yaml(
            self.root / "map/frontier.yaml",
            {"format_version": 1, "focus": {"primary": "design-process", "secondary": []}, "units": frontier_units},
        )
        self.repository = Repository(self.root)
        self.repository.create_unit(self.unit())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def unit(unit_id: str = "define-requirements", title: str = "Define requirements") -> dict:
        return {
            "format_version": 1,
            "id": unit_id,
            "title": title,
            "nodes": ["design-process", "requirements"] if unit_id == "define-requirements" else ["design-process"],
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

    def attempt(
        self,
        evidence_type: str,
        day: str,
        result: dict[str, str],
        previous_evidence: str | None = None,
        prompt: str | None = None,
    ) -> tuple[str, str, Path]:
        path, session = self.repository.create_session(
            "define-requirements",
            25,
            f"{day}T10:00:00+05:00",
        )
        self.assertTrue(path.is_file())
        session_id = session["id"]
        evidence_id = f"{session_id}-{evidence_type}-001"
        common = {
            "format_version": 1,
            "id": evidence_id,
            "unit": "define-requirements",
            "session": session_id,
            "type": evidence_type,
            "created_at": f"{day}T10:20:00+05:00",
            "takeaways": ["Constraints and trade-offs must be explicit."],
            "observations": [],
        }
        if evidence_type == "initial":
            evidence = {
                **common,
                "resource": {
                    "title": "System Design Primer",
                    "url": "https://example.com/system-design",
                    "type": "article",
                    "language": "en",
                },
                "recall": {"prompts": ["What are constraints?"], "answers": ["Hard limits on a design."]},
                "practice": {
                    "prompt": prompt or "Define requirements for a URL shortener.",
                    "answer": "Prioritize redirect latency and availability.",
                },
            }
        elif evidence_type == "practice":
            evidence = {
                **common,
                "target": {"dimension": "application"},
                "based_on": {"evidence": previous_evidence},
                "practice": {
                    "prompt": prompt or "Frame requirements for a photo sharing service.",
                    "answer": "Uploads need durability; reads need low latency and graceful degradation.",
                },
            }
        else:
            evidence = {
                **common,
                "based_on": {"previous_evidence": previous_evidence},
                "prompt": prompt or f"Re-evaluate requirements for a service on {day}.",
                "answer": "I would make scale, consistency, and failure assumptions explicit.",
            }
        evidence_path = self.repository.create_evidence(evidence)
        assessment = {
            "format_version": 1,
            "id": f"{evidence_id}-assessment-001",
            "evidence": evidence_id,
            "type": evidence_type,
            "created_at": f"{day}T10:22:00+05:00",
            "result": result,
            "gaps": [] if min(result.values()) in {"good", "easy"} else ["A tested dimension remains weak."],
            "summary": "Assessment of the demonstrated attempt.",
        }
        if evidence_type == "review":
            assessment["review_outcome"] = self.repository.calculate_review_outcome(result)
        self.repository.create_assessment(assessment)
        self.repository.rebuild_progress()
        self.repository.complete_session(session_id, [evidence_id], f"{day}T10:25:00+05:00")
        return session_id, evidence_id, evidence_path

    def test_practice_targets_gap_without_repeating_study_and_starts_review_cycle(self) -> None:
        _, initial_id, initial_path = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "hard"},
        )
        initial_bytes = initial_path.read_bytes()
        candidates = self.repository.plan_session_candidates(25, "2026-09-15")
        self.assertEqual({"type": "practice", "unit": "define-requirements"}, candidates["suggested_actions"][0])

        _, practice_id, practice_path = self.attempt(
            "practice",
            "2026-09-15",
            {"recall": "good", "understanding": "good", "application": "good"},
            initial_id,
        )
        item = self.repository.read_progress()["define-requirements"]
        self.assertEqual("verified", item["status"])
        self.assertNotEqual(initial_path, practice_path)
        self.assertEqual(initial_bytes, initial_path.read_bytes())
        self.assertEqual(practice_id, item["latest_evidence"])
        self.assertEqual({"due": "2026-09-22", "interval_days": 7, "repetitions": 0}, item["review"])

    def test_failed_recall_during_practice_returns_unit_to_learning(self) -> None:
        _, initial_id, _ = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "hard"},
        )
        self.attempt(
            "practice",
            "2026-09-15",
            {"recall": "failed", "understanding": "good", "application": "hard"},
            initial_id,
        )
        self.assertEqual("learning", self.repository.read_progress()["define-requirements"]["status"])

    def test_practice_prompt_cannot_repeat_previous_prompt_verbatim(self) -> None:
        _, initial_id, _ = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "hard"},
        )
        _, session = self.repository.create_session("define-requirements", 25, "2026-09-15T10:00:00+05:00")
        evidence = {
            "format_version": 1,
            "id": f"{session['id']}-practice-001",
            "unit": "define-requirements",
            "session": session["id"],
            "type": "practice",
            "created_at": "2026-09-15T10:20:00+05:00",
            "target": {"dimension": "application"},
            "based_on": {"evidence": initial_id},
            "practice": {"prompt": " Define requirements for a URL shortener. ", "answer": "A second answer."},
            "takeaways": ["One takeaway."],
            "observations": [],
        }
        with self.assertRaisesRegex(ValueError, "must not repeat"):
            self.repository.create_evidence(evidence)

    def test_due_detection_budget_and_mixed_session_plan(self) -> None:
        self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "good"},
        )
        self.assertEqual([], self.repository.get_due_reviews("2026-09-20"))
        due = self.repository.get_due_reviews("2026-09-21")
        self.assertEqual(["define-requirements"], [item["id"] for item in due])
        plan = self.repository.plan_session_candidates(25, "2026-09-21")
        self.assertEqual(6, plan["review_budget_minutes"])
        self.assertEqual(
            [
                {"type": "review", "unit": "define-requirements"},
                {"type": "study", "unit": "unit-2"},
            ],
            plan["suggested_actions"],
        )

    def test_review_intervals_are_adaptive_and_failed_review_resets(self) -> None:
        _, previous, _ = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "good"},
        )
        cases = [
            ("2026-09-21", {"recall": "hard", "understanding": "good", "application": "good"}, 11, "2026-10-02", "verified"),
            ("2026-10-02", {"recall": "good", "understanding": "good", "application": "good"}, 22, "2026-10-24", "verified"),
            ("2026-10-24", {"recall": "easy", "understanding": "easy", "application": "easy"}, 66, "2026-12-29", "verified"),
            ("2026-12-29", {"recall": "failed", "understanding": "hard", "application": "hard"}, 1, "2026-12-30", "learning"),
        ]
        for repetition, (day, result, interval, due, status) in enumerate(cases, start=1):
            _, previous, _ = self.attempt("review", day, result, previous)
            item = self.repository.read_progress()["define-requirements"]
            self.assertEqual(status, item["status"])
            self.assertEqual(interval, item["review"]["interval_days"])
            self.assertEqual(due, item["review"]["due"])
            self.assertEqual(repetition, item["review"]["repetitions"])

    def test_application_gap_in_review_moves_to_practice_and_keeps_review_history(self) -> None:
        _, initial_id, initial_path = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "good"},
        )
        initial_bytes = initial_path.read_bytes()
        self.attempt(
            "review",
            "2026-09-21",
            {"recall": "good", "understanding": "good", "application": "hard"},
            initial_id,
        )
        item = self.repository.read_progress()["define-requirements"]
        self.assertEqual("practice", item["status"])
        self.assertEqual("2026-09-21", item["review"]["last"])
        self.assertEqual(initial_bytes, initial_path.read_bytes())
        self.assertEqual([], self.repository.get_due_reviews(item["review"]["due"]))

    def test_reviewing_is_not_a_progress_status(self) -> None:
        invalid = {
            "define-requirements": {
                "status": "reviewing",
                "attempts": 1,
                "mastery": {"recall": "good", "understanding": "good", "application": "good"},
                "latest_evidence": "evidence-id",
                "latest_assessment": "assessment-id",
                "last_attempt": "2026-09-14T10:20:00+05:00",
            }
        }
        issues = self.repository.validate_schema("progress", invalid, "progress/units.yaml")
        self.assertTrue(any("is not one of" in issue.message for issue in issues))

    def test_session_can_complete_review_and_new_study_actions(self) -> None:
        _, previous, _ = self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "good"},
        )
        self.repository.create_unit(self.unit("unit-2", "Unit 2"))
        _, session = self.repository.create_session(
            None,
            25,
            "2026-09-21T10:00:00+05:00",
            [
                {"type": "review", "unit": "define-requirements"},
                {"type": "study", "unit": "unit-2"},
            ],
        )
        review_id = f"{session['id']}-review-001"
        study_id = f"{session['id']}-initial-001"
        review = {
            "format_version": 1,
            "id": review_id,
            "unit": "define-requirements",
            "session": session["id"],
            "type": "review",
            "created_at": "2026-09-21T10:05:00+05:00",
            "based_on": {"previous_evidence": previous},
            "prompt": "Frame the consistency requirements for a collaborative editor.",
            "answer": "Edits require convergence and explicit conflict semantics.",
            "takeaways": ["Consistency requirements are product decisions."],
            "observations": [],
        }
        study = {
            "format_version": 1,
            "id": study_id,
            "unit": "unit-2",
            "session": session["id"],
            "type": "initial",
            "created_at": "2026-09-21T10:20:00+05:00",
            "resource": {
                "title": "A second resource",
                "url": "https://example.com/second",
                "type": "article",
                "language": "en",
            },
            "recall": {"prompts": ["What is the main idea?"], "answers": ["A useful idea."]},
            "practice": {"prompt": "Apply the second idea.", "answer": "A valid application."},
            "takeaways": ["A second takeaway."],
            "observations": [],
        }
        self.repository.create_evidence(review)
        self.repository.create_evidence(study)
        for evidence_id, evidence_type in ((review_id, "review"), (study_id, "initial")):
            assessment = {
                "format_version": 1,
                "id": f"{evidence_id}-assessment-001",
                "evidence": evidence_id,
                "type": evidence_type,
                "created_at": "2026-09-21T10:22:00+05:00",
                "result": {"recall": "good", "understanding": "good", "application": "good"},
                "gaps": [],
                "summary": "The action was completed successfully.",
            }
            if evidence_type == "review":
                assessment["review_outcome"] = "good"
            self.repository.create_assessment(assessment)
        self.repository.rebuild_progress()
        _, completed, _ = self.repository.complete_session(
            session["id"],
            [review_id, study_id],
            "2026-09-21T10:25:00+05:00",
        )
        self.assertEqual(session["plan"]["actions"], completed["actual"]["actions"])
        self.assertEqual([review_id, study_id], completed["evidence"])

    def test_status_is_rebuilt_from_files_in_a_new_context(self) -> None:
        self.attempt(
            "initial",
            "2026-09-14",
            {"recall": "good", "understanding": "good", "application": "good"},
        )
        status = Repository(self.root).render_status("2026-09-21")
        self.assertIn("Verified:", status)
        self.assertIn("Reviews due:", status)
        self.assertIn("Define requirements — due 2026-09-21", status)
        self.assertNotIn("reviewing", status.casefold())


if __name__ == "__main__":
    unittest.main()
