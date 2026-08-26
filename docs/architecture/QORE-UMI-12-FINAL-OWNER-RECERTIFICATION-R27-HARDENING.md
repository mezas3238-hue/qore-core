# QORE UMI-12 Final Owner Recertification — R27 Hardening

## Scope

This correction is a tests/docs-only hardening of the UMI-12 final D04 owner-universe
falsification harness after DeepSeek Expert R27. It does not change `src/qore`, provider
support, execution capability, Production posture, or real-capital authorization.

The historical oracle remains unchanged:

`tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`

## R26 transport outcome

Expert R26 did not produce a semantic verdict. Its final model response transport ended
with `http.client.IncompleteRead`, publication was skipped, and the package is consumed
without certification. R27 is the next unique Expert package on the same frozen candidate.

## Accepted R27 findings

R27 identified two bounded iteration-target defects. Both were independently adjudicated
against real Python execution order and the exact R25 implementation and are accepted.

1. A synchronous loop target that is an `Attribute` or `Subscript` can receive a dangerous
   callable such as `eval`, but the inherited `_assign_target` models only names and
   tuple/list/starred bindings. The dangerous iterated value was therefore silently lost.
2. Structural unpacking with a statically non-iterable selected value or a statically
   incompatible exact arity falls back to flattened assignment in R25. Python raises
   before the loop/comprehension body runs, while the scanner could fabricate a dangerous
   binding and report an unreachable call.

## Correction

The R27 layer stays within the bounded D04 scanner contract and does not introduce generic
container taint or whole-program data-flow analysis.

- `Attribute` and `Subscript` iteration targets fail closed with a binding marker when the
  exact iterated value is sensitive. Their executable base/index expressions continue to
  be scanned by the inherited assignment-target execution logic.
- Exact structural target reachability is checked before target execution and binding.
- A selected value represented entirely by known non-iterable abstract kinds is treated as
  a definite unpacking failure for a tuple/list target.
- Exact sequence-length alternatives that are all incompatible with target arity are a
  definite unpacking failure.
- Exact nested unpacking checks recurse through selected slots, so a nested arity failure
  also makes that body unreachable.
- When reachability is not statically certain, the scanner remains conservative and keeps
  the inherited R25 behavior rather than inventing new arbitrary semantics.
- For a definite unpacking failure, synchronous `for` does not scan target expressions,
  body, or `else`; a comprehension does not scan filters, later generators, or element/body
  expressions that Python cannot reach after the failed assignment.

## Regression witnesses

The R27 layer includes positive and negative witnesses for:

- dangerous `Subscript` iteration target;
- dangerous `Attribute` iteration target;
- scalar `eval` unpacking into two targets;
- exact one-element tuple unpacked into two targets;
- nested exact arity mismatch;
- unreachable direct `eval` inside a body whose loop-target unpacking necessarily fails;
- comprehension element unreachable after definite unpacking failure;
- compatible exact unpacking preserving a dangerous selected slot;
- safe selected-slot precision when another slot contains `eval`;
- complete current D04 owner plus historical-oracle zero-marker recertification.

## Boundaries

This hardening makes no claim of arbitrary Python iteration or taint completeness. Ambiguous
or unmodelled runtime structures remain conservative. Any future material expansion of the
bounded D04 contract requires another exact-head Quality Gate and independent review cycle.
