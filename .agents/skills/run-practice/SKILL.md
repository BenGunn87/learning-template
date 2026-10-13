---
name: run-practice
description: Run targeted Practice for a Unit whose Progress status is practice, testing its current gap without repeating the original Study flow.
---

# Run targeted Practice

Read the active Session, the initialized Unit, current Progress, latest Assessment, and recent Evidence. Confirm that the Session contains a `practice` action for the Unit and that Progress has `status: practice`.

Choose the weak mastery dimension shown by the latest Assessment:

- recall: ask for active recall without consulting material;
- understanding: ask for causes, mechanisms, comparisons, or edge cases;
- application: give a new scenario requiring a decision and trade-off.

Test the same ability with a materially new prompt. Do not repeat an earlier prompt verbatim, show a Resource, restart Study Focus, or give the answer before the user attempts it. Ask for one to four concise takeaways after the answer and preserve the factual interaction for Evidence.

Immediately checkpoint the selected prompt or scenario and update the checkpoint after each substantive answer or stage change. If this Practice is resumed, continue that exact prompt and retained partial answers; do not generate a new scenario. An unfinished answer remains checkpoint state and is not Evidence.

Create `Evidence(type=practice)` with `target.dimension`, `based_on.evidence` pointing to the latest Evidence, and `practice.prompt/answer`. Preserve which lowest Graph Nodes the prompt tested. This Practice normally contributes only its target dimension to the later `Assessment.evaluated`; older grades carried into `Assessment.result` were not retested. Do not assess mastery or calculate Review dates here; return control to `run-session` for Assessment and deterministic Progress update.

Leave the source action `in_progress` for Assessment and the caller's optional Remediation. If the saved phase is already `remediation`, route to `../run-remediation/SKILL.md` instead of repeating this independent check.

Before asking the independent question, explicitly announce Reference permission: recall and understanding are closed by default; application is open. An explicit task-specific override is allowed. Separate parts if policies differ. Persist `reference: [{dimension: ..., allowed: ...}]` for the tested dimensions in checkpoint and Evidence, keeping the saved policy on resume. Trust the learner; do not ask whether they consulted Reference or record files. Open Reference does not authorize hints or reopening the original Study Resource.

After the activity, you may notice concise reusable knowledge worth adding or improving. Offer an update only when useful and follow `../manage-reference/SKILL.md`; a system proposal waits for explicit confirmation without modifying files. A direct user request needs no extra confirmation. Reference edits do not verify mastery or resolve a Gap.
