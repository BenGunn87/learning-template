Fix the Stage 6 integration edge case where a single Session can contain multiple `study` actions.

Current Stage 6 stores one `session.study` object with:

* `mode`
* `resources`
* `discussion_summary`

Evidence resource validation is also tied to this single `session.study`.

Therefore a Session with multiple `study` actions for different Units can create inconsistent state: later Study state may overwrite the earlier one while earlier Evidence still belongs to the previous Unit.

## Required change

Enforce the invariant:

```text
A Session may contain at most one study action.
```

This should apply to all Session creation paths, including explicit/manual CLI or API input, not only the automatic planner.

Do not redesign Stage 6 to support multiple study states per Session.

Do not introduce `study[]` or per-action Study state in this fix.

## Validation

Add deterministic validation so an existing Session containing more than one `study` action is rejected with a clear error.

The error should explain that the current Session model supports only one Study attempt per Session.

## Tests

Add tests covering:

```text
create session with one study action
→ valid
```

```text
create session with multiple non-study actions
→ remains valid if already allowed
```

```text
create session with two study actions
→ rejected
```

Also test validation of a manually constructed Session file containing two study actions.

Run the full existing test suite and ensure Stage 1–6 behavior remains unchanged otherwise.

Do not make unrelated refactors.
