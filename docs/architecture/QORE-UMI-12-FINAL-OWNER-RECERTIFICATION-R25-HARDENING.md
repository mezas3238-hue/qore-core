# QORE UMI-12 Final Owner Recertification — R25 Hardening

## Scope

This correction is a tests/docs-only hardening of the UMI-12 final D04 owner-universe
falsification harness after DeepSeek Expert R25. It does not change `src/qore`, provider
support, execution capability, Production posture, or real-capital authorization.

The historical oracle remains unchanged:

`tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`

## Accepted R25 findings

R25 identified three bounded iteration-model defects, all accepted after independent
adjudication against Python semantics and the exact scanner implementation.

1. Comprehensions propagated exact sequence values only when the sequence length was
   exactly one. A comprehension over `(len, eval)` therefore lost the second iteration
   and could miss a real call to `eval`.
2. Synchronous `for` propagation required one unique `sequence-length` atom. Merging
   exact sequence alternatives with different non-zero lengths could therefore degrade
   to unknown even when a dangerous member was present.
3. Tuple/list iteration targets received the flattened union of every semantic atom in
   the iterated item. Exact unpacking such as `for fn, safe in ((len, eval),)` could
   incorrectly classify `fn` as dangerous even though Python binds `fn = len`.

## Correction

The R25 layer preserves the existing bounded abstract-value model and does not introduce
whole-program taint analysis.

- Exact sequence iteration selects the recorded `selected-slot` values for every
  reachable non-empty static position and merges those selected values.
- Divergent exact sequence lengths are retained as alternatives instead of requiring
  one unique length.
- Tuple/list iteration targets are assigned from the exact selected slot when the
  iterated item has a unique structural length.
- Nested unpacking is recursive.
- One-starred-target unpacking preserves exact fixed prefix/suffix slots while the
  starred middle remains conservatively merged.
- Comprehensions use the same exact iteration propagation as synchronous `for`.
- `async for` behavior is not broadened: a synchronous tuple is not treated as a
  reachable asynchronous iteration source.

## Regression witnesses

The layer includes fixed positive and negative witnesses for:

- `[fn("1+1") for fn in (len, eval)]`;
- safe multi-element comprehensions;
- `IfExp` sequence alternatives with divergent non-zero lengths;
- safe divergent alternatives;
- safe exact unpacking `for fn, safe in ((len, eval),): fn(...)`;
- dangerous selected-slot unpacking;
- nested structural unpacking;
- complete current D04 owner plus historical-oracle zero-marker recertification.

## Boundaries

This hardening makes no claim of arbitrary Python data-flow completeness. It remains a
bounded static contract for the current D04 owner surface and the explicitly evidenced
syntactic families. Any future material expansion of that contract requires a new
review package and exact-head recertification.
