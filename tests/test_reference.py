from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from learning import main as learning_main  # noqa: E402
from learning_core import Repository  # noqa: E402
from learning_core.yaml_io import load_yaml  # noqa: E402
import test_learning_cycle as cycle  # noqa: E402


class ReferenceFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repository = Repository(self.root)

    def cli(self, *args: str) -> tuple[int, str, str]:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = learning_main(["--root", str(self.root), *args])
        return code, output.getvalue(), errors.getvalue()

    def test_validation_does_not_initialize_reference(self) -> None:
        self.assertEqual([], self.repository.validate_reference())
        self.assertEqual(0, self.cli("validate", "reference")[0])
        self.assertFalse((self.root / "reference").exists())

    def test_first_operations_initialize_only_index(self) -> None:
        for operation in ("ensure", "list", "read"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                repository = Repository(directory)
                if operation == "ensure":
                    repository.ensure_reference()
                elif operation == "list":
                    self.assertEqual(["reference/index.md"], repository.list_reference_files())
                else:
                    self.assertEqual("# Reference\n", repository.read_reference())
                self.assertEqual(["index.md"], [path.name for path in repository.path("reference").iterdir()])

    def test_thematic_creation_and_authored_index(self) -> None:
        content = "# Аэродинамика\n\nL = ½ρv²SCₗ.\n"
        path = self.repository.create_reference("reference/aerodynamics.md", content)
        self.assertEqual(content, path.read_text())
        previous = self.repository.read_reference()
        index = previous + "\n- [Аэродинамика](aerodynamics.md)\n"
        self.repository.update_reference("reference/index.md", index, previous)
        self.assertEqual(index, self.repository.read_reference())
        self.assertEqual(["reference/aerodynamics.md", "reference/index.md"], self.repository.list_reference_files())
        self.assertEqual([], self.repository.validate_reference())

    def test_custom_index_can_be_created_first(self) -> None:
        content = "# Рабочий справочник\n"
        self.repository.create_reference("reference/index.md", content)
        self.repository.ensure_reference()
        self.assertEqual(content, self.repository.read_reference())

    def test_update_replaces_same_file_and_create_refuses_overwrite(self) -> None:
        self.repository.create_reference("reference/storage.md", "# Storage\n")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.repository.create_reference("reference/storage.md", "# Other\n")
        self.repository.update_reference("reference/storage.md", "# Storage\n\nA rule.\n", "# Storage\n")
        self.assertEqual("# Storage\n\nA rule.\n", self.repository.read_reference("reference/storage.md"))
        self.assertEqual(2, len(self.repository.list_reference_files()))

    def test_stale_expected_text_preserves_current_file(self) -> None:
        self.repository.create_reference("reference/storage.md", "# Current\n")
        with self.assertRaisesRegex(ValueError, "changed since"):
            self.repository.update_reference("reference/storage.md", "# Replacement\n", "# Old\n")
        self.assertEqual("# Current\n", self.repository.read_reference("reference/storage.md"))

    def test_write_failure_keeps_original_and_cleans_temporary_file(self) -> None:
        path = self.repository.create_reference("reference/storage.md", "# Original\n")
        with patch("learning_core.reference.os.replace", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(ValueError, "write failed"):
                self.repository.update_reference("reference/storage.md", "# Replacement\n", "# Original\n")
        self.assertEqual("# Original\n", path.read_text())
        self.assertEqual(["index.md", "storage.md"], sorted(p.name for p in path.parent.iterdir()))

    def test_conflict_during_write_keeps_concurrent_edit(self) -> None:
        path = self.repository.create_reference("reference/storage.md", "# Original\n")

        def concurrent_edit(_descriptor: int) -> None:
            path.write_text("# User edit\n")

        with patch("learning_core.reference.os.fsync", side_effect=concurrent_edit):
            with self.assertRaisesRegex(ValueError, "changed since"):
                self.repository.update_reference("reference/storage.md", "# Replacement\n", "# Original\n")
        self.assertEqual("# User edit\n", path.read_text())
        self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_empty_writes_are_rejected_before_initialization(self) -> None:
        for content in ("", " \n\t"):
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, "empty"):
                self.repository.create_reference("reference/storage.md", content)
        self.assertFalse((self.root / "reference").exists())
        self.repository.ensure_reference()
        with self.assertRaisesRegex(ValueError, "empty"):
            self.repository.update_reference("reference/index.md", "", "# Reference\n")
        self.assertEqual("# Reference\n", self.repository.read_reference())

    def test_invalid_paths_rejected_without_creating_reference(self) -> None:
        for relative in ("../escape.md", "reference/../escape.md", "/reference/a.md", "reference//a.md",
                         "reference/./a.md", "reference/sub/../../a.md", "reference/a.txt", "other/a.md",
                         "reference\\a.md", "reference/a\x00.md", "reference/a\n.md", "reference"):
            with self.subTest(relative=relative):
                for operation in (
                    lambda: self.repository.create_reference(relative, "# Text\n"),
                    lambda: self.repository.update_reference(relative, "# Text\n", "# Old\n"),
                    lambda: self.repository.read_reference(relative),
                ):
                    with self.assertRaises(ValueError):
                        operation()
        self.assertFalse((self.root / "reference").exists())

    def test_symlink_directory_cannot_escape_reference(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "index.md").write_text("# Outside\n")
        (self.root / "reference").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.repository.ensure_reference()
        self.assertTrue(self.repository.validate_reference())
        self.assertEqual("# Outside\n", (outside / "index.md").read_text())

    def test_symlink_files_and_nested_directories_are_rejected(self) -> None:
        self.repository.ensure_reference()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "a.md").write_text("# Outside\n")
        self.repository.path("reference/link.md").symlink_to(outside / "a.md")
        self.repository.path("reference/nested").symlink_to(outside, target_is_directory=True)
        for relative in ("reference/link.md", "reference/nested/a.md"):
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    self.repository.update_reference(relative, "# Changed\n", "# Outside\n")
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    self.repository.read_reference(relative)
        self.assertTrue(self.repository.validate_reference())
        self.assertEqual("# Outside\n", (outside / "a.md").read_text())

    def test_validation_checks_readability_without_semantic_schema(self) -> None:
        self.repository.create_reference("reference/formulas.md", "A formula with no IDs or headings.\n")
        self.assertEqual([], self.repository.validate_reference())
        self.repository.path("reference/bad.md").write_bytes(b"\xff")
        self.assertTrue(self.repository.validate_reference())
        self.assertEqual(1, self.cli("validate", "reference")[0])

    def test_explicit_cli_update_needs_no_second_confirmation(self) -> None:
        replacement, expected = self.root / "replacement.md", self.root / "expected.md"
        replacement.write_text("# Storage\n")
        self.assertEqual(0, self.cli("create-reference", "reference/storage.md", str(replacement))[0])
        self.assertEqual((0, "# Storage\n", ""), self.cli("read-reference", "reference/storage.md"))
        expected.write_text("# Storage\n")
        replacement.write_text("# Storage\n\nUpdated rule.\n")
        self.assertEqual(0, self.cli("update-reference", "reference/storage.md", str(replacement), "--expected", str(expected))[0])
        self.assertIn("Updated rule", self.repository.read_reference("reference/storage.md"))
        self.assertIn("reference/storage.md", self.cli("list-reference")[1])

    def test_proposal_inspection_preserves_reference_until_execution(self) -> None:
        self.repository.create_reference("reference/storage.md", "# Storage\n")
        before = {path: path.read_bytes() for path in self.repository.path("reference").iterdir()}
        self.repository.read_reference()
        original = self.repository.read_reference("reference/storage.md")
        proposed_content = original + "\nA reusable constraint.\n"
        self.assertEqual(before, {path: path.read_bytes() for path in self.repository.path("reference").iterdir()})
        # Confirmation is conversational; only subsequent execution persists it.
        self.repository.update_reference("reference/storage.md", proposed_content, original)
        self.assertEqual(proposed_content, self.repository.read_reference("reference/storage.md"))

    def test_invalid_filesystem_destinations_report_cli_errors(self) -> None:
        self.repository.ensure_reference()
        self.repository.path("reference/blocker").write_text("An ordinary file.")
        content = self.root / "input.md"
        content.write_text("# Rule\n")
        self.assertEqual(1, self.cli("create-reference", "reference/blocker/rule.md", str(content))[0])
        self.repository.path("reference/directory.md").mkdir()
        self.assertEqual(1, self.cli("read-reference", "reference/directory.md")[0])

    def test_cli_missing_input_reports_error_without_initializing(self) -> None:
        self.assertEqual(1, self.cli("create-reference", "reference/storage.md", str(self.root / "missing.md"))[0])
        self.assertFalse((self.root / "reference").exists())


class ReferenceLearningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = cycle.LearningCycleTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root.resolve()
        self.repository = self.fixture.repository
        self.fixture.initialize()
        self.session_id = self.fixture.start()

    def snapshot(self, directory: str = "") -> dict[str, bytes]:
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in (self.root / directory).rglob("*")
            if path.is_file() and "reference" not in path.relative_to(self.root).parts
        }

    def test_edits_do_not_mutate_any_learning_state(self) -> None:
        self.repository.create_evidence(self.fixture.evidence(self.session_id))
        assessment = self.fixture.assessment()
        assessment["evaluated"] = {"application": {"nodes": ["requirements"]}}
        self.repository.create_assessment(assessment)
        self.repository.rebuild_progress()
        self.repository.rebuild_frontier()
        self.assertTrue(self.repository.list_gaps())
        before = self.snapshot()
        self.repository.create_reference("reference/storage.md", "# Storage\n")
        self.repository.update_reference("reference/storage.md", "# Storage\n\nA rule.\n", "# Storage\n")
        self.repository.update_reference("reference/index.md", "# Reference\n\n[Storage](storage.md)\n", "# Reference\n")
        self.assertEqual(before, self.snapshot())

    def test_reference_usage_mixed_modes_and_overrides(self) -> None:
        for permissions in (
            [{"dimension": "recall", "allowed": False, "used": False}],
            [{"dimension": "understanding", "allowed": False, "used": False}],
            [{"dimension": "application", "allowed": True, "used": True}],
            [{"dimension": "application", "allowed": True, "used": False}],
            [{"dimension": "recall", "allowed": True, "used": True}],
            [{"dimension": "understanding", "allowed": True, "used": False}],
            [{"dimension": "application", "allowed": False, "used": False}],
            [{"dimension": "recall", "allowed": False, "used": False},
             {"dimension": "understanding", "allowed": False, "used": False},
             {"dimension": "application", "allowed": True, "used": True}],
        ):
            with self.subTest(permissions=permissions):
                evidence = self.fixture.evidence(self.session_id)
                evidence["reference"] = permissions
                self.assertEqual([], self.repository.validate_evidence(evidence, f"evidence/{evidence['unit']}/{evidence['id']}.yaml"))
        evidence = self.fixture.evidence(self.session_id)
        evidence["reference"] = permissions
        path = self.repository.create_evidence(evidence)
        self.assertEqual(permissions, load_yaml(path)["reference"])
        self.assertFalse((self.root / "reference").exists())

    def test_old_evidence_remains_valid_and_is_not_rewritten(self) -> None:
        evidence = self.fixture.evidence(self.session_id)
        self.assertEqual([], self.repository.validate_evidence(evidence, f"evidence/{evidence['unit']}/{evidence['id']}.yaml"))
        path = self.repository.create_evidence(evidence)
        before = path.read_bytes()
        self.repository.create_reference("reference/storage.md", "# Storage\n")
        self.assertEqual([], self.repository.validate_repository())
        self.repository.rebuild_progress()
        self.repository.rebuild_frontier()
        self.assertEqual(before, path.read_bytes())
        self.assertNotIn("reference", load_yaml(path))

    def test_historical_permission_only_evidence_is_valid_and_not_rewritten(self) -> None:
        evidence = self.fixture.evidence(self.session_id)
        evidence["reference"] = [{"dimension": "recall", "allowed": False}, {"dimension": "application", "allowed": True}]
        path = self.repository.path(f"evidence/{evidence['unit']}/{evidence['id']}.yaml")
        # Model a record saved by the previous version, bypassing new-write rules.
        cycle.write_yaml(path, evidence)
        before = path.read_bytes()
        self.assertEqual([], self.repository.validate_evidence(evidence["id"]))
        self.repository.create_assessment(self.fixture.assessment())
        self.repository.rebuild_progress()
        self.repository.rebuild_frontier()
        self.assertEqual([], self.repository.validate_repository())
        self.assertEqual(before, path.read_bytes())
        self.assertTrue(all("used" not in entry for entry in load_yaml(path)["reference"]))

    def test_new_evidence_requires_usage_for_each_reference_dimension(self) -> None:
        for policies in (
            [{"dimension": "recall", "allowed": False}],
            [{"dimension": "application", "allowed": True}],
            [{"dimension": "recall", "allowed": False, "used": False}, {"dimension": "application", "allowed": True}],
        ):
            with self.subTest(policies=policies):
                evidence = self.fixture.evidence(self.session_id)
                evidence["reference"] = policies
                with self.assertRaisesRegex(ValueError, "requires used for every dimension"):
                    self.repository.create_evidence(evidence)
        self.assertFalse(list(self.repository.path("evidence").rglob("*.yaml")))

    def test_schema_rejects_closed_reference_usage(self) -> None:
        for dimension in ("recall", "understanding", "application"):
            with self.subTest(dimension=dimension):
                evidence = self.fixture.evidence(self.session_id)
                evidence["reference"] = [{"dimension": dimension, "allowed": False, "used": True}]
                issues = self.repository.validate_evidence(evidence, f"evidence/{evidence['unit']}/{evidence['id']}.yaml")
                self.assertTrue(any(issue.path == "$.reference[0].used" for issue in issues), issues)
                with self.assertRaises(ValueError):
                    self.repository.create_evidence(evidence)

    def test_cli_records_open_used_and_unused_as_distinct_values(self) -> None:
        for used in (False, True):
            evidence = self.fixture.evidence(self.session_id)
            evidence["id"] += "-used" if used else "-unused"
            evidence["reference"] = [{"dimension": "application", "allowed": True, "used": used}]
            staging = self.root / "evidence-input.yaml"
            cycle.write_yaml(staging, evidence)
            with redirect_stdout(StringIO()):
                self.assertEqual(0, learning_main(["--root", str(self.root), "create-evidence", str(staging)]))
            path = self.repository.path(f"evidence/{evidence['unit']}/{evidence['id']}.yaml")
            self.assertIs(used, load_yaml(path)["reference"][0]["used"])

    def test_invalid_permissions_are_rejected(self) -> None:
        for permissions in (
            [], True, [{"dimension": "recall", "allowed": "false"}],
            [{"dimension": "other", "allowed": True}], [{"dimension": "recall"}],
            [{"dimension": "recall", "allowed": False, "used": True}],
            [{"dimension": "understanding", "allowed": False, "used": True}],
            [{"dimension": "application", "allowed": True, "used": "true"}],
            [{"dimension": "application", "allowed": True, "used": None}],
            [{"dimension": "application", "allowed": True, "used": 1}],
            [{"dimension": "application", "allowed": True, "used": True, "files": ["reference/storage.md"]}],
            [{"dimension": "recall", "allowed": False, "used": False}, {"dimension": "recall", "allowed": True, "used": True}],
        ):
            with self.subTest(permissions=permissions):
                evidence = self.fixture.evidence(self.session_id)
                evidence["reference"] = permissions
                with self.assertRaises(ValueError):
                    self.repository.create_evidence(evidence)
        self.assertFalse(list((self.root / "evidence").rglob("*.yaml")))

    def test_practice_and_review_accept_reference_permissions(self) -> None:
        source = self.fixture.evidence(self.session_id)
        self.repository.create_evidence(source)
        self.repository.create_assessment(self.fixture.assessment(source["id"]))
        self.repository.rebuild_progress()
        self.repository.complete_session(self.session_id, [source["id"]], "2026-09-14T10:25:00+05:00")
        _, session = self.repository.create_session("define-requirements", 25, "2026-09-15T10:00:00+05:00")
        common = {key: source[key] for key in ("format_version", "unit", "session", "created_at", "takeaways", "observations")}
        common.update(session=session["id"], created_at="2026-09-15T10:20:00+05:00")
        practice = {**common, "id": "practice-check", "type": "practice", "target": {"dimension": "application"},
                    "based_on": {"evidence": source["id"]}, "practice": {"prompt": "New case", "answer": "New answer"},
                    "reference": [{"dimension": "application", "allowed": True, "used": False}]}
        path = self.repository.create_evidence(practice)
        self.assertEqual(practice["reference"], load_yaml(path)["reference"])
        assessment = {**self.fixture.assessment(practice["id"]), "type": "practice",
                      "created_at": "2026-09-15T10:22:00+05:00",
                      "result": {"recall": "good", "understanding": "good", "application": "good"}}
        self.repository.create_assessment(assessment)
        self.repository.rebuild_progress()
        self.repository.complete_session(session["id"], [practice["id"]], "2026-09-15T10:25:00+05:00")
        _, session = self.repository.create_session("define-requirements", 25, "2026-09-30T10:00:00+05:00")
        common.update(session=session["id"], created_at="2026-09-30T10:20:00+05:00")
        review = {**common, "id": "review-check", "type": "review", "based_on": {"previous_evidence": practice["id"]},
                  "prompt": "Recall then apply", "answer": "Response",
                  "reference": [{"dimension": "recall", "allowed": False, "used": False},
                                {"dimension": "application", "allowed": True, "used": True}]}
        path = self.repository.create_evidence(review)
        self.assertEqual(review["reference"], load_yaml(path)["reference"])

    def test_permissions_survive_pause_resume_and_recovery(self) -> None:
        policy = [{"dimension": "recall", "allowed": False, "used": False},
                  {"dimension": "application", "allowed": True, "used": True}]
        checkpoint = {"unit": "define-requirements", "action": "study", "stage": "recall",
                      "completed_steps": {}, "reference": policy}
        self.repository.update_checkpoint(self.session_id, checkpoint, "2026-09-14T10:05:00+05:00")
        self.repository.pause_session(self.session_id, paused_at="2026-09-14T10:06:00+05:00")
        _, resumed, _ = self.repository.resume_session(self.session_id, 20, "2026-09-14T11:00:00+05:00")
        self.assertEqual(policy, resumed["checkpoint"]["reference"])
        _, recovered, _ = self.repository.recover_session(self.session_id, 20, "2026-09-14T12:00:00+05:00")
        self.assertEqual(policy, recovered["checkpoint"]["reference"])

    def test_legacy_checkpoint_keeps_usage_unknown_on_resume_and_recovery(self) -> None:
        policy = [{"dimension": "recall", "allowed": False}, {"dimension": "application", "allowed": True}]
        checkpoint = {"unit": "define-requirements", "action": "study", "stage": "recall",
                      "completed_steps": {}, "reference": policy}
        self.repository.update_checkpoint(self.session_id, checkpoint, "2026-09-14T10:05:00+05:00")
        self.repository.pause_session(self.session_id, paused_at="2026-09-14T10:06:00+05:00")
        _, resumed, _ = self.repository.resume_session(self.session_id, 20, "2026-09-14T11:00:00+05:00")
        self.assertEqual(policy, resumed["checkpoint"]["reference"])
        _, recovered, _ = self.repository.recover_session(self.session_id, 20, "2026-09-14T12:00:00+05:00")
        self.assertEqual(policy, recovered["checkpoint"]["reference"])
        self.assertTrue(all("used" not in entry for entry in recovered["checkpoint"]["reference"]))

    def test_invalid_checkpoint_usage_is_rejected_atomically(self) -> None:
        path = self.repository.path(f"sessions/{self.session_id}.yaml")
        before = path.read_bytes()
        for policy in (
            {"dimension": "recall", "allowed": False, "used": True},
            {"dimension": "application", "allowed": True, "used": "true"},
        ):
            with self.subTest(policy=policy):
                checkpoint = {"unit": "define-requirements", "action": "study", "stage": "recall",
                              "completed_steps": {}, "reference": [policy]}
                with self.assertRaises(ValueError):
                    self.repository.update_checkpoint(self.session_id, checkpoint, "2026-09-14T10:05:00+05:00")
                self.assertEqual(before, path.read_bytes())

    def test_conflicting_checkpoint_policy_is_rejected_atomically(self) -> None:
        path = self.repository.path(f"sessions/{self.session_id}.yaml")
        before = path.read_bytes()
        checkpoint = {"unit": "define-requirements", "action": "study", "stage": "recall", "completed_steps": {},
                      "reference": [{"dimension": "recall", "allowed": False}, {"dimension": "recall", "allowed": True}]}
        with self.assertRaisesRegex(ValueError, "duplicate Reference dimension"):
            self.repository.update_checkpoint(self.session_id, checkpoint, "2026-09-14T10:05:00+05:00")
        self.assertEqual(before, path.read_bytes())

    def test_validate_rebuild_validate_preserves_reference_exactly(self) -> None:
        self.repository.create_evidence(self.fixture.evidence(self.session_id))
        self.repository.create_assessment(self.fixture.assessment())
        self.repository.create_reference("reference/storage.md", "# Storage\n\nA rule.\n")
        before = {path.relative_to(self.root): path.read_bytes() for path in self.repository.path("reference").rglob("*") if path.is_file()}
        self.assertEqual([], self.repository.validate_repository())
        self.repository.rebuild_progress()
        self.repository.rebuild_frontier()
        self.assertEqual([], self.repository.validate_repository())
        after = {path.relative_to(self.root): path.read_bytes() for path in self.repository.path("reference").rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_reference_permission_does_not_change_progress_scores(self) -> None:
        evidence = self.fixture.evidence(self.session_id)
        evidence["reference"] = [{"dimension": "application", "allowed": True, "used": True}]
        self.repository.create_evidence(evidence)
        self.repository.create_assessment(self.fixture.assessment())
        self.repository.rebuild_progress()
        progress = load_yaml(self.repository.path("progress/units.yaml"))
        self.assertEqual(self.fixture.assessment()["result"], progress["define-requirements"]["mastery"])

    def test_usage_alone_does_not_change_learning_state_or_planning(self) -> None:
        for grade in ("hard", "good"):
            results = []
            for used in (False, True):
                with tempfile.TemporaryDirectory() as directory:
                    clone = Path(directory) / "repository"
                    shutil.copytree(self.root, clone)
                    repository = Repository(clone)
                    evidence = self.fixture.evidence(self.session_id)
                    evidence["reference"] = [{"dimension": "application", "allowed": True, "used": used}]
                    repository.create_evidence(evidence)
                    assessment = self.fixture.assessment()
                    assessment["result"]["application"] = grade
                    assessment["evaluated"] = {"application": {"nodes": ["requirements"]}}
                    repository.create_assessment(assessment)
                    repository.rebuild_progress()
                    repository.rebuild_frontier()
                    results.append({
                        "progress": repository.read_progress(),
                        "gaps": repository.list_gaps(),
                        "frontier": repository.read("frontier"),
                        "practice": repository.get_practice_units(),
                        "reviews": repository.get_due_reviews("2026-09-30"),
                        "planning": repository.plan_session_candidates(25, "2026-09-30"),
                    })
            with self.subTest(grade=grade):
                self.assertEqual(results[0], results[1])
                progress = results[0]["progress"]["define-requirements"]
                self.assertEqual(1, progress["attempts"])
                if grade == "hard":
                    self.assertTrue(results[0]["gaps"])
                    self.assertTrue(results[0]["practice"])
                else:
                    self.assertTrue(results[0]["reviews"])


if __name__ == "__main__":
    unittest.main()
