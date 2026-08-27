# QORE UMI-12 Final Owner Recertification — R37 Hardening

## Scope

This additive hardening layer adjudicates the three exact-head DeepSeek Expert R37 findings for PR #461. It changes only the UMI-12 falsification harness and documentation; it does not change any production semantic owner.

`src/qore delta = 0`

## Independent adjudication

All three R37 findings are **VALID** against HEAD `4c3ec355d14f6c8d6af8ecc1bd4044e6bb8d3a24`.

### R37-H1 — definite call-argument failure

Python evaluates the callable and call arguments in execution order. In the exact witness, `fns[::0]` raises `ValueError: slice step cannot be zero` before the later `eval("1+1")` argument is evaluated.

The hardening layer therefore propagates the already-modeled definite-failure value across calls and stops scanning arguments that are unreachable after that failure. The rule is applied to ordinary calls and the special `.get` / `.__getitem__` paths. A complementary regression proves that a dangerous argument evaluated *before* a later failure remains marked.

### R37-H2 — unary signs on exact direct indices

Python numeric index semantics apply equally to direct subscripts and operator accessors. With `idx = 1`, `-idx` is exactly `-1`; for `fns == [eval]`, `fns[-idx]` selects `eval`.

The hardening layer reuses R35's exact integer/bool scalar semantics for unary `+` / `-` outside `ast.Slice`, while scanning the operand only once. This makes direct `Subscript`, `operator.getitem`, and `operator.itemgetter` consume the same exact signed index value.

### R37-H3 — no dangerous propagation by container co-presence

For `{None: len, "eval": eval}[None]`, Python selects `len`. The R35 fallback could not encode the `None` key as a selectable token and then reintroduced `dangerous` because `eval` was merely co-present in the mapping.

The hardening layer now treats a statically known container with an unselectable key as `UNKNOWN` rather than flattening co-present semantic atoms. Exact supported keys continue to select their precise slot, including dangerous slots.

## Regression guarantees

The R37 layer adds direct witnesses for all three findings plus bounded inverse cases:

- later arguments after a definite failure remain unreachable;
- earlier reachable dangerous arguments are not suppressed;
- direct and operator-based signed indexing recover exact dangerous slots;
- safe signed selection remains unmarked;
- unselectable static mapping keys do not inherit danger by co-presence;
- exact supported dangerous mapping keys remain detected;
- the complete current D04 owner/oracle surface remains free of dynamic-execution markers.

All historical R4–R35 layers remain unchanged and continue to act as independent regression evidence.

## Non-claims

This hardening does not authorize or claim:

- a Program-D final PASS;
- provider or operational readiness;
- Production readiness;
- Production accounts or credentials;
- real-money execution or real capital;
- any new D04 semantic ownership.

Promotion still requires the full QORE Quality Gate, exact diff audit, a new frozen HEAD/TREE/synthetic binding, and fresh serial external review. R37 is consumed and must not be reused.
