from __future__ import annotations

import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import test_stage5  # noqa: E402


class Stage7Test(unittest.TestCase):
    def setUp(self) -> None:
        test_stage5.Stage5Test.setUp(self)

    def tearDown(self) -> None:
        test_stage5.Stage5Test.tearDown(self)

    def attempt(self, *args, **kwargs) -> str:
        return test_stage5.Stage5Test.attempt(self, *args, **kwargs)

    @staticmethod
    def gap_by_key(gaps: list[dict], node: str, dimension: str) -> dict:
        return test_stage5.Stage5Test.gap_by_key(gaps, node, dimension)

    def frontier_units_routed_by_gap(self, gap_id: str) -> list[str]:
        return sorted(
            unit["id"]
            for unit in self.repository.read("frontier")["units"]
            if any(
                reason.get("type") == "gap" and reason.get("gap") == gap_id
                for reason in unit.get("routing_reasons", [])
            )
        )

    def reevaluation(
        self,
        evidence_id: str,
        grade: str,
        sequence: int = 2,
        *,
        target: str | None = None,
        node: str = "quorum",
        reason: str = "user_request",
    ) -> dict:
        active = self.repository.active_assessment(evidence_id)
        return {
            "format_version": 1,
            "id": f"{evidence_id}-assessment-{sequence:03d}",
            "evidence": evidence_id,
            "type": "reevaluation",
            "supersedes": target or active["id"],
            "reason": reason,
            "created_at": f"2026-09-{14 + sequence:02d}T11:00:00+05:00",
            "result": {
                "recall": "good",
                "understanding": "good",
                "application": grade,
            },
            "gaps": [] if grade in {"good", "easy"} else ["Application needs improvement."],
            "summary": f"Reevaluated the original Evidence as {grade}.",
            "evaluated": {"application": {"nodes": [node]}},
        }

    def test_basic_reevaluation_preserves_old_assessment_and_attempt(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        original = self.repository.active_assessment(evidence_id)
        before_evidence = list((self.root / "evidence").rglob("*.yaml"))

        result = self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "good"))

        active = self.repository.active_assessment(evidence_id)
        progress = self.repository.read_progress()["practice-quorum"]
        gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual(f"{evidence_id}-assessment-002", active["id"])
        self.assertTrue((self.root / f"assessments/{evidence_id}/001.yaml").is_file())
        self.assertTrue((self.root / f"assessments/{evidence_id}/002.yaml").is_file())
        self.assertEqual(original["id"], active["supersedes"])
        self.assertEqual(1, progress["attempts"])
        self.assertEqual("verified", progress["status"])
        self.assertEqual(active["id"], progress["latest_assessment"])
        self.assertEqual("invalidated", gap["status"])
        self.assertEqual(1, len(gap["signals"]))
        self.assertEqual([], self.repository.detect_weak_signals(evidence_id))
        self.assertEqual(active["id"], gap["history"][-1]["assessment"])
        self.assertEqual("reevaluation", gap["history"][-1]["reason"])
        self.assertEqual(before_evidence, list((self.root / "evidence").rglob("*.yaml")))
        self.assertTrue(result["effects"]["frontier_rebuilt"])
        self.assertEqual([], self.repository.validate_repository())

    def test_three_event_chain_has_one_active_tip_and_can_worsen_progress(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "good"))
        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "hard", 3))

        active = self.repository.active_assessment(evidence_id)
        gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual(f"{evidence_id}-assessment-003", active["id"])
        self.assertEqual(f"{evidence_id}-assessment-002", active["supersedes"])
        self.assertEqual("practice", self.repository.read_progress()["practice-quorum"]["status"])
        self.assertEqual(1, self.repository.read_progress()["practice-quorum"]["attempts"])
        self.assertEqual("detected", gap["status"])
        self.assertEqual(2, len(gap["signals"]))
        self.assertEqual([], self.repository.validate_repository())

    def test_cross_evidence_and_inactive_target_are_rejected(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        second = self.attempt("practice", "2026-09-15", "hard", first)
        cross = self.reevaluation(second, "good", target=f"{first}-assessment-001")
        with self.assertRaisesRegex(ValueError, "another Evidence"):
            self.repository.reevaluate_assessment(cross)

        self.repository.reevaluate_assessment(self.reevaluation(second, "good"))
        branch = self.reevaluation(second, "hard", 3, target=f"{second}-assessment-001")
        with self.assertRaisesRegex(ValueError, "not active"):
            self.repository.reevaluate_assessment(branch)
        self.assertFalse((self.root / f"assessments/{second}/003.yaml").exists())

    def test_confirmed_gap_downgrades_then_invalidates(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        second = self.attempt("practice", "2026-09-15", "hard", first)
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])

        self.repository.reevaluate_assessment(self.reevaluation(second, "good"))
        gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual("detected", gap["status"])

        self.repository.reevaluate_assessment(self.reevaluation(first, "good"))
        gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual("invalidated", gap["status"])
        self.assertEqual(2, len(gap["signals"]))
        self.assertEqual([], self.repository._active_gap_signals(gap))
        self.assertEqual(
            ["detected", "confirmed", "detected", "invalidated"],
            [item["status"] for item in gap["history"]],
        )

    def test_resolved_gap_reopens_when_resolving_assessment_becomes_weak(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        second = self.attempt("practice", "2026-09-15", "good", first)
        self.assertEqual("resolved", self.repository.list_gaps()[0]["status"])

        self.repository.reevaluate_assessment(self.reevaluation(second, "hard"))

        gap = self.gap_by_key(self.repository.list_gaps(), "quorum", "application")
        self.assertEqual("confirmed", gap["status"])
        self.assertIsNone(gap["resolved_at"])
        self.assertEqual("confirmed", gap["history"][-1]["status"])

    def test_invalidated_gap_is_removed_from_frontier_routing(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        gap_id = self.repository.list_gaps()[0]["id"]
        frontier = self.repository.read("frontier")
        frontier["units"][0]["routing_reasons"].append({"type": "gap", "gap": gap_id})
        test_stage5.write_yaml(self.root / "map/frontier.yaml", frontier)

        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "good"))

        rebuilt = self.repository.read("frontier")
        reasons = rebuilt["units"][0]["routing_reasons"]
        self.assertFalse(any(reason.get("gap") == gap_id for reason in reasons))
        candidates = self.repository.session_candidates(25)["candidates"]
        self.assertFalse(any(gap_id in item["related_gaps"] for item in candidates))

    def test_invalidated_gap_routing_is_restored_when_gap_becomes_detected_again(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        gap_id = self.repository.list_gaps()[0]["id"]
        self.repository.rebuild_frontier()
        initially_routed = self.frontier_units_routed_by_gap(gap_id)
        self.assertEqual(["practice-quorum"], initially_routed)

        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "good"))
        self.assertEqual("invalidated", self.repository.list_gaps()[0]["status"])
        self.assertEqual([], self.frontier_units_routed_by_gap(gap_id))

        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "hard", 3))
        self.assertEqual("detected", self.repository.list_gaps()[0]["status"])
        self.assertEqual(initially_routed, self.frontier_units_routed_by_gap(gap_id))
        self.assertEqual([], self.repository.validate_repository())

        before_rebuild = deepcopy(self.repository.read("frontier"))
        self.repository.rebuild_frontier()
        self.assertEqual(before_rebuild, self.repository.read("frontier"))
        self.assertEqual([], self.repository.validate_repository())

    def test_confirmed_gap_routing_is_restored_after_all_signals_reactivate(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        second = self.attempt("practice", "2026-09-15", "hard", first)
        gap_id = self.repository.list_gaps()[0]["id"]
        self.repository.rebuild_frontier()
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])
        self.assertEqual(["practice-quorum"], self.frontier_units_routed_by_gap(gap_id))

        self.repository.reevaluate_assessment(self.reevaluation(first, "good"))
        self.repository.reevaluate_assessment(self.reevaluation(second, "good"))
        self.assertEqual("invalidated", self.repository.list_gaps()[0]["status"])
        self.assertEqual([], self.frontier_units_routed_by_gap(gap_id))

        self.repository.reevaluate_assessment(self.reevaluation(first, "hard", 3))
        self.repository.reevaluate_assessment(self.reevaluation(second, "hard", 3))
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])
        self.assertEqual(["practice-quorum"], self.frontier_units_routed_by_gap(gap_id))

    def test_resolved_gap_routing_is_restored_when_gap_reopens(self) -> None:
        first = self.attempt("initial", "2026-09-14", "hard")
        second = self.attempt("practice", "2026-09-15", "good", first)
        gap_id = self.repository.list_gaps()[0]["id"]
        self.repository.rebuild_frontier()
        self.assertEqual("resolved", self.repository.list_gaps()[0]["status"])
        self.assertEqual([], self.frontier_units_routed_by_gap(gap_id))

        self.repository.reevaluate_assessment(self.reevaluation(second, "hard"))
        self.assertEqual("confirmed", self.repository.list_gaps()[0]["status"])
        self.assertEqual(["practice-quorum"], self.frontier_units_routed_by_gap(gap_id))

    def test_invalid_mixed_boundary_is_atomic(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        before_progress = deepcopy(self.repository.read_progress())
        before_gaps = deepcopy(self.repository.list_gaps())
        before_frontier = deepcopy(self.repository.read("frontier"))
        before_assessments = sorted((self.root / "assessments").rglob("*.yaml"))
        invalid = self.reevaluation(evidence_id, "good", node="consensus")

        with self.assertRaisesRegex(ValueError, "out-of-scope Node consensus"):
            self.repository.reevaluate_assessment(invalid)

        self.assertEqual(before_progress, self.repository.read_progress())
        self.assertEqual(before_gaps, self.repository.list_gaps())
        self.assertEqual(before_frontier, self.repository.read("frontier"))
        self.assertEqual(before_assessments, sorted((self.root / "assessments").rglob("*.yaml")))

    def test_repository_validation_rejects_a_manual_branch(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        self.repository.reevaluate_assessment(self.reevaluation(evidence_id, "good"))
        branch = self.reevaluation(
            evidence_id,
            "hard",
            3,
            target=f"{evidence_id}-assessment-001",
        )
        path = self.root / f"assessments/{evidence_id}/003.yaml"
        test_stage5.write_yaml(path, branch)

        rendered = "\n".join(issue.render() for issue in self.repository.validate_repository())
        self.assertIn("branches", rendered)
        self.assertIn("exactly one active Assessment", rendered)

    def test_schema_and_repository_validation_reject_invalid_chain_metadata(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        missing_reason = self.reevaluation(evidence_id, "good")
        del missing_reason["reason"]
        issues = self.repository.validate_assessment(
            missing_reason,
            f"assessments/{evidence_id}/002.yaml",
        )
        self.assertTrue(any("reason" in issue.message for issue in issues))

        original_path = self.root / f"assessments/{evidence_id}/001.yaml"
        original = yaml.safe_load(original_path.read_text(encoding="utf-8"))
        original["supersedes"] = "forbidden-on-initial"
        issues = self.repository.validate_assessment(
            original,
            f"assessments/{evidence_id}/001.yaml",
        )
        self.assertTrue(issues)

    def test_cli_reevaluation_reports_old_new_and_effects(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        input_path = self.root / "reevaluation.yaml"
        test_stage5.write_yaml(input_path, self.reevaluation(evidence_id, "good"))

        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts/learning.py"),
                "--root",
                str(self.root),
                "reevaluate-assessment",
                str(input_path),
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        output = yaml.safe_load(result.stdout)
        self.assertEqual(f"{evidence_id}-assessment-001", output["old_assessment"])
        self.assertEqual(f"{evidence_id}-assessment-002", output["new_assessment"])
        self.assertEqual("invalidated", output["effects"]["gap_changes"][0]["to"])
        self.assertTrue(output["effects"]["frontier_rebuilt"])

    def test_repository_validation_reports_supersedes_cycle(self) -> None:
        evidence_id = self.attempt("initial", "2026-09-14", "hard")
        second = self.reevaluation(
            evidence_id,
            "good",
            2,
            target=f"{evidence_id}-assessment-003",
        )
        third = self.reevaluation(
            evidence_id,
            "hard",
            3,
            target=f"{evidence_id}-assessment-002",
        )
        for sequence, assessment in ((2, second), (3, third)):
            path = self.root / f"assessments/{evidence_id}/{sequence:03d}.yaml"
            test_stage5.write_yaml(path, assessment)

        rendered = "\n".join(issue.render() for issue in self.repository.validate_repository())
        self.assertIn("supersedes cycle", rendered)


if __name__ == "__main__":
    unittest.main()
