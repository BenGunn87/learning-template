from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import test_routing
from learning import main as learning_main
from learning_core import Repository
from learning_core.yaml_io import load_yaml, replace_yaml


class RemediationTest(unittest.TestCase):
    def setUp(self) -> None:
        test_routing.AdaptiveRoutingTest.setUp(self)
        self.root = self.root.resolve()

    def tearDown(self) -> None:
        test_routing.AdaptiveRoutingTest.tearDown(self)

    def attempt(self, *args, **kwargs) -> str:
        return test_routing.AdaptiveRoutingTest.attempt(self, *args, **kwargs)

    def source(self, action: str = "review", *, result: dict | None = None) -> dict:
        previous = self.attempt("initial", "2026-09-14", "hard" if action == "practice" else "good")
        self.day = "2026-09-15" if action == "practice" else "2026-09-21"
        with patch.object(self.repository, "complete_session"):
            evidence_id = self.attempt(action, self.day, "hard", previous, result=result)
        self.session_id = self.repository._find_by_id("evidence", evidence_id)[0][1]["session"]
        self.evidence_id = evidence_id
        self.repository.update_checkpoint(self.session_id, {
            "action": action, "unit": "practice-quorum", "stage": "assessment",
            "completed_steps": {"evidence_created": True, "assessment_created": True},
        }, self.at("23"))
        gap = next(gap for gap in self.repository.list_gaps() if gap["status"] in {"detected", "confirmed"})
        return {
            "id": "remediation-quorum-001", "session": self.session_id, "unit": "practice-quorum",
            "gap": gap["id"], "source_evidence": evidence_id,
            "source_assessment": self.repository.active_assessment(evidence_id)["id"],
            "level": 2, "focus": "Separate quorum intersection from consistency guarantees.",
        }

    def at(self, minute: str, hour: str = "10") -> str:
        return f"{self.day}T{hour}:{minute}:00+05:00"

    def session(self) -> dict:
        return load_yaml(self.root / f"sessions/{self.session_id}.yaml")

    def snapshot(self) -> dict:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for directory in ("evidence", "assessments", "progress", "map")
            for path in (self.root / directory).rglob("*.yaml")
        }

    def start(self, data: dict) -> None:
        self.repository.start_remediation(data, self.at("24"))

    def finish_session(self, hour: str = "10") -> None:
        self.repository.complete_session(self.session_id, [self.evidence_id], self.at("30", hour))

    def lesson(self, data: dict) -> str:
        return f"""---
format_version: 1
id: resource-remediation-quorum-001
type: generated
format: article
purpose: remediation
gap: {data['gap']}
created_at: {self.at('25')}
unit: practice-quorum
session: {self.session_id}
title: Quorum intersection and consistency
learning_goal: Explain the limits of intersecting quorums.
depth: working
coverage: [quorum]
sources: []
---

# Quorum intersection and consistency

An intersection lets a read contact a replica that accepted a write. Version selection and coordination still determine the consistency guarantee.
"""

    def test_detected_review_gap_teaching_is_neutral_and_adds_provenance(self) -> None:
        data = self.source()
        before = self.snapshot()
        gap_before = self.repository.list_gaps()[0]
        data["level"] = 1
        self.start(data)
        self.assertEqual(before, self.snapshot())
        self.assertNotIn("remediations", self.repository.list_gaps()[0])
        self.assertEqual([], self.session()["evidence"])
        self.repository.complete_remediation(data["id"], self.at("26"))
        gap_after = self.repository.list_gaps()[0]
        self.assertEqual(gap_before, {key: value for key, value in gap_after.items() if key != "remediations"})
        self.assertEqual("detected", gap_after["status"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(data["source_assessment"], gap_after["remediations"][0]["source_assessment"])
        self.assertEqual([{"gap": data["gap"], "remediation": data["id"]}], self.session()["remediations"])
        self.finish_session()
        self.assertEqual([self.evidence_id], self.session()["evidence"])
        self.assertEqual([], self.repository.validate_repository())

    def test_confirmed_prerequisite_gap_keeps_progress_and_blocking_routing(self) -> None:
        data = self.source("practice")
        self.repository.rebuild_frontier()
        gap_before = self.repository.list_gaps()[0]
        self.assertEqual("confirmed", gap_before["status"])
        self.assertEqual("blocking", gap_before["routing_impact"])
        before = self.snapshot()
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.assertEqual(before, self.snapshot())
        self.finish_session()
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])
        self.assertEqual([], self.repository.validate_repository())

    def test_declining_remediation_completes_normally(self) -> None:
        self.source()
        before = self.snapshot()
        self.finish_session()
        self.assertEqual([], self.repository.list_remediations())
        self.assertNotIn("remediations", self.repository.list_gaps()[0])
        self.assertEqual(before, self.snapshot())

    def test_skip_started_remediation_and_finish_session(self) -> None:
        data = self.source()
        before = self.snapshot()
        self.start(data)
        self.repository.skip_remediation(self.session_id, self.at("26"))
        self.assertEqual("already-skipped", self.repository.skip_remediation(self.session_id)[2])
        self.finish_session()
        self.assertNotIn("remediations", self.repository.list_gaps()[0])
        self.assertEqual("skipped", self.repository.list_remediations()[0]["status"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual([], self.repository.validate_repository())

    def test_finish_session_skips_saved_lesson_without_completed_gap_provenance(self) -> None:
        data = self.source()
        data["level"] = 3
        self.start(data)
        path, _ = self.repository.create_generated_resource(self.lesson(data))
        content = path.read_bytes()
        self.finish_session()
        self.assertNotIn("remediations", self.repository.list_gaps()[0])
        skipped = self.session()["skipped_remediations"][0]
        self.assertEqual(path.name, Path(skipped["resource"]["path"]).name)
        self.assertEqual(content, path.read_bytes())
        self.assertEqual([], self.repository.validate_generated_resource("resource-remediation-quorum-001"))
        self.assertEqual([], self.repository.validate_repository())

    def test_multiple_remediations_on_same_gap_and_same_action(self) -> None:
        data = self.source()
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        second = {**data, "id": "remediation-quorum-002", "level": 1}
        self.repository.start_remediation(second, self.at("27"))
        self.repository.complete_remediation(second["id"], self.at("28"))
        self.assertEqual(2, len(self.repository.list_gaps()[0]["remediations"]))
        self.assertEqual(2, len(self.session()["remediations"]))
        self.finish_session()
        self.assertEqual([], self.repository.validate_repository())

    def test_only_selected_gap_receives_remediation(self) -> None:
        data = self.source(result={"recall": "good", "understanding": "hard", "application": "hard"})
        untouched = [deepcopy(gap) for gap in self.repository.list_gaps() if gap["id"] != data["gap"]]
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.assertEqual(untouched, [gap for gap in self.repository.list_gaps() if gap["id"] != data["gap"]])
        self.finish_session()

    def test_guided_exercise_is_teaching_without_an_attempt(self) -> None:
        data = self.source()
        before = self.snapshot()
        self.start(data)
        checkpoint = self.session()["checkpoint"]
        checkpoint["remediation"]["step"] = "guided_exercise"
        checkpoint["remediation"]["guided_exercise"] = True
        checkpoint["remediation"]["misconceptions_addressed"] = ["Intersection alone guarantees consistency."]
        self.repository.update_checkpoint(self.session_id, checkpoint, self.at("25"))
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.assertTrue(self.repository.list_gaps()[0]["remediations"][0]["guided_exercise"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual("detected", self.repository.list_gaps()[0]["status"])

    def test_level_three_pause_resume_reuses_resource_and_same_remediation(self) -> None:
        data = self.source()
        data["level"] = 3
        self.start(data)
        path, _ = self.repository.create_generated_resource(self.lesson(data))
        content = path.read_bytes()
        self.assertEqual([], self.repository.validate_repository())
        self.repository.pause_session(self.session_id, paused_at=self.at("26"))
        self.repository = Repository(self.root)
        detected = self.repository.detect_resumable_session()
        self.assertEqual(data["id"], detected["checkpoint"]["remediation"]["id"])
        self.repository.resume_session(self.session_id, 20, self.at("00", "11"))
        self.assertEqual("reused", self.repository.create_generated_resource(self.lesson(data))[1])
        self.repository.complete_remediation(data["id"], self.at("10", "11"))
        self.finish_session("11")
        self.assertEqual(content, path.read_bytes())
        self.assertEqual(1, len(list((self.root / "resources/generated").glob("*.md"))))
        self.assertEqual(1, len(self.repository.list_gaps()[0]["remediations"]))
        self.assertEqual([], self.repository.validate_repository())
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.repository.create_generated_resource(self.lesson(data) + "Changed.\n")

    def test_escalation_and_checkpoint_cannot_lose_source_or_resource(self) -> None:
        data = self.source()
        data["level"] = 1
        self.start(data)
        for level in (2, 3):
            checkpoint = self.session()["checkpoint"]
            checkpoint["remediation"]["level"] = level
            checkpoint["remediation"]["step"] = "example" if level == 2 else "mini_lesson"
            self.repository.update_checkpoint(self.session_id, checkpoint, self.at("25"))
        with self.assertRaisesRegex(ValueError, "requires a Generated Resource"):
            self.repository.complete_remediation(data["id"], self.at("26"))
        self.repository.create_generated_resource(self.lesson(data))
        checkpoint = self.session()["checkpoint"]
        checkpoint["remediation"]["resource"] = None
        with self.assertRaisesRegex(ValueError, "must be reused"):
            self.repository.update_checkpoint(self.session_id, checkpoint, self.at("26"))
        checkpoint = self.session()["checkpoint"]
        checkpoint.pop("phase")
        checkpoint.pop("remediation")
        with self.assertRaisesRegex(ValueError, "complete or skip"):
            self.repository.update_checkpoint(self.session_id, checkpoint, self.at("26"), "completed")

    def test_invalid_source_references_and_unrelated_gap_are_rejected(self) -> None:
        data = self.source()
        initial = self.repository._read_files("evidence")[0][0][1]
        for field, value, message in (
            ("gap", "gap-unknown-application", "unknown Gap"),
            ("source_evidence", "unknown-evidence", "unknown Evidence"),
            ("source_assessment", "unknown-assessment", "unknown Assessment"),
            ("source_assessment", f"{initial['id']}-assessment-001", "another Evidence"),
            ("unit", "study-consensus", "Unit does not match"),
            ("level", 4, "not one of"),
            ("id", "invalid", "does not match"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, message):
                    self.start({**data, field: value})
        self.assertEqual([], self.repository.list_remediations())
        with self.assertRaisesRegex(ValueError, "no signal"):
            self.start({**data, "source_evidence": initial["id"], "source_assessment": f"{initial['id']}-assessment-001"})

    def test_active_reevaluation_source_and_historical_provenance(self) -> None:
        data = self.source()
        assessment = deepcopy(self.repository.active_assessment(self.evidence_id))
        assessment.pop("review_outcome", None)
        assessment.update({
            "id": f"{self.evidence_id}-assessment-002", "type": "reevaluation",
            "supersedes": data["source_assessment"], "reason": "user_request", "created_at": self.at("23"),
        })
        self.repository.reevaluate_assessment(assessment)
        with self.assertRaisesRegex(ValueError, "active source"):
            self.start(data)
        data["source_assessment"] = assessment["id"]
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        assessment.update({
            "id": f"{self.evidence_id}-assessment-003", "supersedes": assessment["id"],
            "created_at": self.at("35"), "gaps": [],
            "result": {"recall": "good", "understanding": "good", "application": "good"},
        })
        self.repository.reevaluate_assessment(assessment)
        self.assertEqual(data["source_assessment"], self.repository.list_gaps()[0]["remediations"][0]["source_assessment"])
        self.assertEqual([], self.repository.validate_repository())

    def test_completion_is_idempotent_and_rejects_rewriting(self) -> None:
        data = self.source()
        self.start(data)
        self.assertEqual("already-started", self.repository.start_remediation(data, self.at("24"))[2])
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        before = {path: path.read_bytes() for path in self.root.rglob("*.yaml")}
        self.assertEqual("already-completed", self.repository.complete_remediation(data["id"], self.at("26"))[2])
        self.assertEqual("already-completed", self.repository.complete_remediation(data["id"])[2])
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*.yaml")})
        with self.assertRaisesRegex(ValueError, "different timestamp"):
            self.repository.complete_remediation(data["id"], self.at("27"))

    def test_future_normal_practice_resolves_gap(self) -> None:
        data = self.source()
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        self.assertIn("practice-quorum", [unit["id"] for unit in self.repository.get_practice_units()])
        self.attempt("practice", "2026-09-22", "good", self.evidence_id)
        self.assertEqual("resolved", self.repository.list_gaps()[0]["status"])
        self.assertEqual(1, len(self.repository.list_gaps()[0]["remediations"]))
        self.assertEqual([], self.repository.validate_repository())

    def test_future_normal_review_resolves_gap_and_weak_review_can_repeat_teaching(self) -> None:
        data = self.source(result={"recall": "hard", "understanding": "good", "application": "good"})
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        due = self.repository.read_progress()["practice-quorum"]["review"]["due"]
        with patch.object(self.repository, "complete_session"):
            second = self.attempt(
                "review", due, "good", self.evidence_id,
                result={"recall": "hard", "understanding": "good", "application": "good"},
            )
        self.day = due
        self.evidence_id = second
        self.session_id = self.repository._find_by_id("evidence", second)[0][1]["session"]
        data.update({
            "id": "remediation-quorum-002", "source_evidence": second,
            "source_assessment": self.repository.active_assessment(second)["id"], "session": self.session_id,
        })
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])
        due = self.repository.read_progress()["practice-quorum"]["review"]["due"]
        self.attempt("review", due, "good", second)
        self.assertEqual("resolved", self.repository.list_gaps()[0]["status"])
        self.assertEqual(2, len(self.repository.list_gaps()[0]["remediations"]))
        self.assertEqual([], self.repository.validate_repository())

    def test_validation_rebuild_preserves_provenance_and_derived_semantics(self) -> None:
        data = self.source("practice")
        self.repository.rebuild_frontier()
        self.start(data)
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.finish_session()
        gaps = self.repository.list_gaps()
        before = self.snapshot()
        self.assertEqual([], self.repository.validate_repository())
        self.repository.rebuild_progress()
        self.repository.rebuild_frontier()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(gaps, self.repository.list_gaps())
        self.assertEqual([], self.repository.validate_repository())

    def test_completion_failure_rolls_back_gap_and_retry_succeeds(self) -> None:
        data = self.source()
        self.start(data)
        gap_before = self.repository.list_gaps()
        session_before = self.session()
        def fail_session(path, document):
            if path.parent.name == "sessions":
                raise OSError("simulated write failure")
            replace_yaml(path, document)
        with patch("learning_core.remediation.replace_yaml", side_effect=fail_session):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.repository.complete_remediation(data["id"], self.at("26"))
        self.assertEqual(gap_before, self.repository.list_gaps())
        self.assertEqual(session_before, self.session())
        self.repository.complete_remediation(data["id"], self.at("26"))
        self.assertEqual([], self.repository.validate_repository())

    def test_validation_checks_both_directions_and_completed_checkpoint_conflicts(self) -> None:
        data = self.source()
        self.start(data)
        active_checkpoint = self.session()["checkpoint"]
        self.repository.complete_remediation(data["id"], self.at("26"))
        path = self.root / f"sessions/{self.session_id}.yaml"
        original = self.session()
        broken = deepcopy(original)
        broken.pop("remediations")
        test_routing.write_yaml(path, broken)
        self.assertTrue(any("matching Session reference" in issue.message for issue in self.repository.validate_gap(data["gap"])))
        broken = deepcopy(original)
        broken["checkpoint"] = active_checkpoint
        test_routing.write_yaml(path, broken)
        self.assertTrue(any("completed Remediation cannot be in_progress" in issue.message for issue in self.repository.validate_session(self.session_id)))
        broken = deepcopy(original)
        broken["remediations"][0]["remediation"] = "remediation-unknown-001"
        test_routing.write_yaml(path, broken)
        self.assertTrue(any("one completed Gap record" in issue.message for issue in self.repository.validate_session(self.session_id)))
        test_routing.write_yaml(path, original)
        gap_path = self.root / f"gaps/{data['gap']}.yaml"
        gap = self.repository.list_gaps()[0]
        gap["remediations"].append(deepcopy(gap["remediations"][0]))
        test_routing.write_yaml(gap_path, gap)
        self.assertTrue(any("duplicate" in issue.message for issue in self.repository.validate_repository()))

    def test_cli_start_list_validate_complete_and_skip(self) -> None:
        data = self.source()
        draft = self.root / "remediation.yaml"
        test_routing.write_yaml(draft, data)
        base = ["--root", str(self.root)]
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(0, learning_main(base + ["start-remediation", str(draft), "--started-at", self.at("24")]))
            self.assertEqual(0, learning_main(base + ["list-remediations", "--session", self.session_id, "--gap", data["gap"]]))
            self.assertEqual(0, learning_main(base + ["validate", "remediation", data["id"]]))
            self.assertEqual(0, learning_main(base + ["complete-remediation", data["id"], "--completed-at", self.at("26")]))
            data["id"] = "remediation-quorum-002"
            test_routing.write_yaml(draft, data)
            self.assertEqual(0, learning_main(base + ["start-remediation", str(draft), "--started-at", self.at("27")]))
            self.assertEqual(0, learning_main(base + ["skip-remediation", self.session_id, "--skipped-at", self.at("28")]))

    def test_resource_validation_preserves_study_rules_and_rejects_unrelated_lessons(self) -> None:
        data = self.source()
        data["level"] = 3
        self.start(data)
        lesson = self.lesson(data)
        for content, message in (
            (lesson.replace(f"gap: {data['gap']}", "gap: gap-unknown-application"), "unknown Gap"),
            (lesson.replace("coverage: [quorum]", "coverage: [quorum, consensus]"), "within unit.nodes"),
            (lesson.replace("unit: practice-quorum", "unit: study-consensus"), "unknown Unit"),
            (lesson.replace("purpose: remediation\n", "").replace(f"gap: {data['gap']}\n", ""), "for study"),
            (lesson.replace("purpose: remediation", "purpose: study").replace(f"gap: {data['gap']}\n", ""), "for study"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.repository.create_generated_resource(content)
                self.assertFalse((self.root / "resources/generated/resource-remediation-quorum-001.md").exists())
                self.assertIsNone(self.session()["checkpoint"]["remediation"]["resource"])
        initial = next(item for _, item in self.repository._read_files("evidence")[0] if item["type"] == "initial")
        normal = lesson.replace(f"session: {self.session_id}", f"session: {initial['session']}")
        normal = normal.replace("purpose: remediation\n", "").replace(f"gap: {data['gap']}\n", "")
        normal = normal.replace("resource-remediation-quorum-001", "resource-study-legacy-001")
        path, _ = self.repository.create_generated_resource(normal)
        self.assertEqual([], self.repository.validate_generated_resource(path.stem))
        normal = normal.replace("resource-study-legacy-001", "resource-study-explicit-001")
        normal = normal.replace("type: generated\n", "type: generated\npurpose: study\n")
        path, _ = self.repository.create_generated_resource(normal)
        self.assertEqual([], self.repository.validate_generated_resource(path.stem))
        lesson_path, _ = self.repository.create_generated_resource(lesson)
        reference = {
            "type": "generated", "id": lesson_path.stem,
            "path": str(lesson_path.relative_to(self.root)),
            "title": "Quorum intersection and consistency", "format": "article",
        }
        issues = self.repository._validate_resource_references(
            [reference], "evidence/<draft>.yaml", "$.resources",
            unit_id="practice-quorum", session_id=self.session_id,
        )
        self.assertTrue(any("must have purpose=study" in issue.message for issue in issues))
        self.assertEqual([], self.repository.validate_repository())

    def test_resource_write_failure_rolls_back_and_retry_links_once(self) -> None:
        data = self.source()
        data["level"] = 3
        self.start(data)
        original = self.session()
        with patch("learning_core.remediation.replace_yaml", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                self.repository.create_generated_resource(self.lesson(data))
        self.assertFalse((self.root / "resources/generated/resource-remediation-quorum-001.md").exists())
        self.assertEqual(original, self.session())
        self.repository.create_generated_resource(self.lesson(data))
        self.assertEqual([], self.repository.validate_repository())

    def test_invalid_finish_session_does_not_discard_teaching(self) -> None:
        data = self.source()
        self.start(data)
        original = self.session()
        with self.assertRaisesRegex(ValueError, "source Evidence"):
            self.repository.complete_session(self.session_id, [], self.at("26"))
        self.assertEqual(original, self.session())
        with self.assertRaisesRegex(ValueError, "duplicate Evidence"):
            self.repository.complete_session(self.session_id, [self.evidence_id, self.evidence_id], self.at("26"))
        self.assertEqual(original, self.session())

    def test_stale_recovery_keeps_the_same_teaching_and_source_events(self) -> None:
        data = self.source()
        self.start(data)
        before = self.snapshot()
        self.repository = Repository(self.root)
        self.repository.recover_session(self.session_id, 20, self.at("00", "11"))
        self.assertEqual(data["id"], self.session()["checkpoint"]["remediation"]["id"])
        self.assertEqual(before, self.snapshot())
        self.repository.complete_remediation(data["id"], self.at("10", "11"))
        self.finish_session("11")
        self.assertEqual([], self.repository.validate_repository())

    def test_corrupted_source_attribution_cannot_bypass_unit_boundary(self) -> None:
        data = self.source()
        assessment_path, assessment = self.repository._find_by_id("assessments", data["source_assessment"])[0]
        assessment["evaluated"]["application"]["nodes"].append("consensus")
        test_routing.write_yaml(assessment_path, assessment)
        with self.assertRaisesRegex(ValueError, "out-of-scope.*unit.nodes"):
            self.start(data)
        self.assertEqual([], self.repository.list_remediations())


if __name__ == "__main__":
    unittest.main()
