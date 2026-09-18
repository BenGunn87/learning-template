---
name: run-study
description: Conduct Study Focus, material study, Active Recall, application Practice, and user-authored Takeaways for the active learning Session.
---

# Run the study interaction

Read the active Session and initialized Unit. Confirm the chosen Resource, then show the Unit's two or three Study Focus questions without answers and let the user study.

Persist a minimal checkpoint with `update-checkpoint` after Resource selection, after showing Study Focus, after Study completes, after every substantive Recall or Practice answer, and whenever the current stage changes. Include the selected Resource, completed-step flags, current prompt or scenario, and substantive answers needed to continue; never store a transcript. On resume, reuse these fields and do not repeat completed steps or select a new Resource without a reason.

After the user reports finishing the material:

1. Ask a small set of questions that test recall and understanding without consulting the Resource. Require answers in the user's own words.
2. Give one compact scenario or exercise aligned with the Unit practice goal. Prefer a decision and trade-off explanation over a factual quiz.
3. Ask the user for two to four concise Takeaways in their own words. Do not write Takeaways for them. Point out a material error and let the user correct it when needed.

Keep the exact prompts and the substance of every user answer available for Evidence. Retain enough specificity to tell which lowest Graph Nodes each recall, understanding, or application check actually tested; `assess-answer` records that mapping in `Assessment.evaluated`. Record factual observations separately. Do not assess mastery, update Progress, or complete the Session in this skill.

If interrupted before the whole check is complete, leave the interaction only in the checkpoint; it is not Evidence. Follow `../pause-session/SKILL.md` when the user asks to stop.
