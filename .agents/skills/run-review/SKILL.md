---
name: run-review
description: Run a due spaced Review for a verified Unit, creating a fresh check without reopening its original learning Resource.
---

# Run a due Review

Read the active Session, Unit, Progress.review, latest Assessment, and recent Evidence. Confirm with `get-due-reviews` that the Unit is due and that the Session contains its `review` action.

Create a compact new check broad enough to reassess recall, understanding, and application. Emphasize the historically weak dimension; after consistently strong attempts, use a more integrative scenario. Do not repeat any prior prompt verbatim and normally do not show or reopen a Resource.

Checkpoint the Review prompt as soon as it is chosen and update the checkpoint after every substantive answer or stage change. If interrupted, resume the same Review prompt and retained answers. Do not recalculate the due date or create Review Evidence until the check is complete.

After the user's answer, ask for concise takeaways and create `Evidence(type=review)` with `based_on.previous_evidence`, `prompt`, and `answer`. Preserve which parts of the check tested each mastery dimension and lowest Graph Node so `assess-answer` can populate `Assessment.evaluated` without broad attribution. Do not choose an interval. Return control to `run-session`: `assess-answer` derives `review_outcome`, and `update-progress` calculates the next date from config.
