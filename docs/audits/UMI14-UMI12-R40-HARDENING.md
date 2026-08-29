# UMI-14 / UMI-12 — DeepSeek Expert R40 hardening

## Exact reviewed candidate

DeepSeek Expert R40 reviewed PR #461 at exact HEAD
`6d8196508690f3bfef49d47ef592e74dc3b42cc2`, synthetic merge
`236fb2ec907d967a46a2a5f4e08ae55f41df4dba`, against base
`ebd0adf000874797653df92ea1c08a892cce6c8c`.

The public R40 verdict was `HALLAZGOS: 2 / VALIDACIÓN NO OK`. R40 is consumed and is not approval for any later HEAD.

## Independent adjudication

### R40-F1 — VALID

Witnesses using `f(*None, eval(...))` and `f(*True, eval(...))` are real Python reachability failures. Argument evaluation reaches the starred value, expansion raises `TypeError`, and later arguments are not evaluated. The R39 path still delegated definite non-iterability to the R27 atom set, which did not include the exact `none` or `bool-index` atoms.

The correction is additive in the R40 scanner. It extends definite non-iterability locally with `none` and `bool-index`, preserves exact earlier side effects, and applies the same reachability rule to starred tuple/list composites. R27 through R39 remain unchanged.

### R40-F2 — VALID

`operator.getitem({None: eval}, None)` selects `eval`, and `operator.itemgetter(None)({None: exec})` selects `exec`. R38 introduced exact mapping token `n:none`, but the inherited operator accessor path still reconstructed only the older string/integer itemgetter tokens.

The R40 scanner routes exact known-container `operator.getitem` and applied `itemgetter` selection through the R38 selected-slot/token machinery. Itemgetter construction also admits the R38 `n:none` key token. Exact safe selections remain safe even when a different mapping entry contains `eval` or `exec`.

## Regression evidence added

The R40 guard layer tests:

- `None`, `True`, and aliased `None` starred call failure before later dynamic calls;
- preservation of a reachable dynamic call before a later definite starred failure;
- equivalent starred tuple/list composite reachability;
- exact `None` selection through `operator.getitem`;
- exact `None` selection through `operator.itemgetter`;
- safe `None` selections with co-present dangerous values;
- signed sequence selection parity for both operator accessors; and
- the complete current owner/oracle surface remains marker-free.

## Scope and non-claims

This is falsification-harness hardening only. It changes no `src/qore` implementation and does not establish provider support, operational readiness, Production readiness, production authorization, or real-capital readiness. A fresh exact-head FULL QG and fresh Expert review are required after this mutation.
