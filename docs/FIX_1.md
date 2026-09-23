Implement an engine-level invariant:

> Assessment may update Progress / Gap state for a Graph Node only if that Node is declared in the corresponding `unit.nodes`.

Do not modify any existing learning/test data, historical Sessions, Evidence, Assessments, generated resources, Units, or files in `test_stage_6`.

This change must affect only the engine, validation, tests, and documentation.

## Problem

A live Stage 6 test revealed that an Assessment could evaluate and update a Graph Node that was not listed in `unit.nodes`.

This creates an inconsistency:

```text
Unit.nodes
!=
nodes actually assessed / used to update Progress and Gaps
```

The engine should make `unit.nodes` the authoritative boundary for which Graph Nodes a Unit is allowed to formally assess.

## Required invariant

For a Unit:

```yaml
nodes:
  - storage-selection
  - indexing
```

an Assessment may formally update only:

```text
storage-selection
indexing
```

It must not formally update:

```text
transactions
```

unless `transactions` is also present in `unit.nodes`.

## Allowed behavior for out-of-scope nodes

If Recall / Practice / Discussion reveals a weakness related to another Graph Node not in `unit.nodes`, the engine may preserve it only as a non-confirmed signal, for example:

```text
possible_gap
assessment_focus
note
routing signal requiring future verification
```

But it must not:

```text
update Progress for that node
create/confirm a Gap for that node
mark mastery/practice state for that node
treat the node as formally assessed
```

until that Node is evaluated through a Unit that declares it in `unit.nodes`.

## Validation

Add deterministic validation ensuring that every node formally assessed by an Assessment belongs to the source Unit's `unit.nodes`.

Validation should produce a clear error describing:

* Assessment ID;
* Unit ID;
* offending Node ID;
* allowed `unit.nodes`.

Apply this validation to normal repository validation as well as creation/update paths where appropriate.

## Runtime protection

Do not rely only on offline validation.

The engine path that applies Assessment results to Progress / Gaps must also enforce this boundary.

Invalid Assessment state must not partially mutate Derived State.

Prefer rejecting the invalid formal Assessment/update rather than silently ignoring the offending Node.

## Existing data

Do not migrate or rewrite historical data.

In particular:

* do not change `test_stage_6`;
* do not modify the tested Unit;
* do not change existing Evidence;
* do not change existing Assessments;
* do not rewrite generated resources.

Historical inconsistency discovered during the manual test may remain as test history.

The fix applies prospectively to engine behavior.

If repository validation of legacy/test data would now fail because of historical files, preserve backward compatibility appropriately rather than rewriting those files.

Use the existing project conventions for legacy compatibility.

## Tests

Add tests covering at least:

### Valid assessment

```text
Unit.nodes = [A, B]
Assessment formally evaluates A
→ valid
→ Progress/Gap update allowed
```

### Multiple valid nodes

```text
Unit.nodes = [A, B]
Assessment formally evaluates A and B
→ valid
```

### Out-of-scope node

```text
Unit.nodes = [A, B]
Assessment formally evaluates C
→ rejected
```

Verify that:

```text
Progress(C) unchanged
Gap(C) not created/updated
no partial derived-state mutation occurs
```

### Mixed valid + invalid assessment

```text
Assessment evaluates A and C
```

where only A belongs to `unit.nodes`.

The complete invalid update must be rejected atomically.

Do not apply A and then fail on C.

### Possible-gap signal

Verify that a non-confirmed signal about C may still be stored where the architecture already supports such signals, without affecting Progress or confirmed Gap state.

### Backward compatibility

Existing Stage 1–6 tests must continue to pass.

Do not require migration of existing repositories.

## Documentation

Update `docs/SPEC.md` to explicitly state:

```text
unit.nodes defines the formal assessment boundary of a Unit.
```

Also clarify:

```text
An Assessment may update Progress or confirmed Gap state
only for Graph Nodes declared in unit.nodes.
```

Out-of-scope observations remain hypotheses/signals until verified by an appropriate Unit.

## Scope

Do not redesign Unit, Evidence, Assessment, Progress, Gap, or Frontier models.

Do not add new top-level entities.

Do not modify test-learning content.

Do not perform unrelated refactors.

Keep the fix small and engine-focused.

After implementation, report:

* files changed;
* where the invariant is enforced;
* backward-compatibility behavior;
* tests added;
* full test-suite result.
