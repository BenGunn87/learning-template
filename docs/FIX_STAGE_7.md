Fix the Stage 7 edge case where a Gap can become active again after reevaluation, but its Frontier routing influence is not restored.

## Problem

Current Stage 7 behavior can produce:

```text
Gap active
→ Gap invalidated by reevaluation
→ Frontier routing_reason for that Gap removed
→ later reevaluation makes Gap active again
```

The Gap correctly returns to `detected` or `confirmed`, but Frontier may no longer contain the routing relationship that existed before invalidation.

This creates inconsistent state:

```text
Gap = active
but
Frontier does not reflect that active Gap
```

## Required behavior

Frontier must always be rebuilt from current Primary/Derived state, not patched only by removing invalidated Gap references.

Required lifecycle:

```text
Gap detected/confirmed
→ affects routing

Gap invalidated/resolved
→ stops affecting routing

Gap becomes detected/confirmed again
→ routing influence is restored
```

Do not preserve stale Frontier state merely because the Gap was previously invalidated.

## Preferred approach

Avoid implementing a special "undo previous deletion" mechanism.

Instead, make Frontier rebuilding deterministic from the current authoritative state:

```text
Graph
+ Progress
+ active Gaps
+ Interests
+ Context
+ Diagnostic
+ prerequisites
→ Frontier
```

Stage 7 should reuse the existing Stage 5 routing logic wherever possible.

Do not duplicate routing semantics inside Stage 7.

The goal is that after any reevaluation:

```text
Assessment changes
→ Progress rebuilt
→ Gap state reconciled
→ Frontier rebuilt from current state
```

rather than:

```text
Frontier manually patched based only on the latest transition
```

## Gap states and routing

Only current active Gap states should influence routing:

```text
detected
confirmed
```

These must not influence routing:

```text
resolved
invalidated
```

If an invalidated/resolved Gap later returns to `detected` or `confirmed`, it must again be eligible to influence Frontier according to normal Stage 5 rules.

## Required test

Add an integration test covering:

```text
Evidence weak
→ Assessment A
→ Gap detected
→ Frontier contains Gap-driven routing

reevaluate A:
weak → good
→ Gap invalidated
→ Frontier no longer contains Gap-driven routing

reevaluate again:
good → weak
→ Gap detected again
→ Frontier once again contains Gap-driven routing
```

Verify not only Gap status but the actual Frontier routing reason / priority effect.

## Additional tests

Also verify:

```text
confirmed
→ invalidated
→ confirmed
```

if current architecture supports this chain with multiple active signals.

And verify that:

```text
resolved → reopened
```

restores Gap-driven routing when the reopened Gap becomes `detected` or `confirmed`.

## Rebuild consistency

After the scenario above, run:

```text
validate
→ rebuild
→ validate
```

The rebuilt Frontier must be identical in routing semantics to the pre-rebuild current state.

No stale removed routing reason should depend on mutation history.

## Scope

Do not modify:

* Assessment reevaluation semantics;
* supersedes chain;
* Gap lifecycle rules;
* Progress calculation;
* Unit assessment boundary.

Do not introduce new Gap states.

Do not perform unrelated refactors.

Keep the fix focused on Frontier reconstruction after reevaluation.

## Completion criteria

The fix is complete when Frontier routing depends only on the **current active Gap state**, not on whether that Gap was previously invalidated or resolved.

After implementation, report:

* files changed;
* how Frontier is now rebuilt;
* tests added;
* full test-suite result.
