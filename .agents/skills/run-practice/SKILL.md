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

Create `Evidence(type=practice)` with `target.dimension`, `based_on.evidence` pointing to the latest Evidence, and `practice.prompt/answer`. Do not assess mastery or calculate Review dates here; return control to `run-session` for Assessment and deterministic Progress update.
