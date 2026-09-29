@AGENTS.md

## Claude Code

- Project Skills are discovered through `.claude/skills`, a symlink to `.agents/skills`. Edit Skills only in `.agents/skills/`.
- Skills trigger automatically from their descriptions; the user can also invoke one explicitly, for example `/topic-onboarding` or `/run-session`.
- `.claude/settings.json` pre-approves `scripts/learning.py` and the test runner, so run the deterministic commands directly instead of reimplementing them.
