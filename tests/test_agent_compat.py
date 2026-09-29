from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from learning_core.yaml_io import load_yaml_text  # noqa: E402

SKILLS = PROJECT_ROOT / ".agents" / "skills"
CLAUDE_SKILLS = PROJECT_ROOT / ".claude" / "skills"
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"{path} has no YAML frontmatter")
    data = load_yaml_text(match.group(1))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} frontmatter is not a mapping")
    return data


class AgentCompatibilityTest(unittest.TestCase):
    def test_skills_have_frontmatter_accepted_by_codex_and_claude(self) -> None:
        skill_files = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertTrue(skill_files)
        for path in skill_files:
            with self.subTest(skill=path.parent.name):
                data = frontmatter(path)
                name = data.get("name")
                description = data.get("description")
                self.assertEqual(name, path.parent.name)
                self.assertRegex(name, SKILL_NAME)
                self.assertLessEqual(len(name), 64)
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())
                self.assertLessEqual(len(description), 1024)

    def test_claude_skills_mirror_agent_skills(self) -> None:
        self.assertTrue(CLAUDE_SKILLS.is_dir(), ".claude/skills must link to or copy .agents/skills")
        if CLAUDE_SKILLS.resolve() == SKILLS.resolve():
            return
        expected = {path.relative_to(SKILLS): path.read_bytes() for path in SKILLS.rglob("*") if path.is_file()}
        actual = {path.relative_to(CLAUDE_SKILLS): path.read_bytes() for path in CLAUDE_SKILLS.rglob("*") if path.is_file()}
        self.assertEqual(sorted(actual), sorted(expected), ".claude/skills copy has different files")
        for relative, content in expected.items():
            self.assertEqual(actual[relative], content, f".claude/skills/{relative} is stale")

    def test_claude_md_imports_shared_agent_instructions(self) -> None:
        self.assertTrue((PROJECT_ROOT / "AGENTS.md").is_file())
        claude_md = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", claude_md.splitlines())


if __name__ == "__main__":
    unittest.main()
