# UMI14 / UMI12 — R41 hardening

## Scope

This correction is limited to the UMI-12 final-owner falsification harness. It does not change `src/qore`, provider support, runtime behavior, valuation/execution capability, Production readiness, production authorization, or real-capital readiness.

## Frozen reviewed candidate

DeepSeek Expert R41 reviewed exact HEAD `a364498e3000f318ae67db0c3e3786714a346ac6` and reported `HALLAZGOS: 2 / VALIDACIÓN NO OK`.

Both findings were independently adjudicated as valid against Python evaluation and mapping semantics.

## R41-F1 — exact non-iterable numeric/Ellipsis starred expansion

Valid.

The R39 layer intentionally represented exact non-string constants with a generic atom so `builtins.__dict__.get` could classify non-string misses. That representation also covered `bytes`, which is iterable. R40 therefore could not safely treat the generic atom as definitely non-iterable and only added exact `None`/`bool` kinds.

The residual consequence was that exact `float`, `complex`, and `Ellipsis` values used under `*` were treated as unknown iterable shapes. Python instead raises `TypeError` while expanding those values, before evaluating later arguments/elements.

R41 separates exact float, complex, and Ellipsis values from the inherited generic non-string representation and classifies only those scalar kinds as definitely non-iterable. `bytes` remains outside that classification and therefore does not suppress reachable later expressions.

## R41-F2 — numeric mapping-key equality and last-write-wins

Valid.

Python mapping keys apply ordinary numeric equality/hash semantics. In particular, `True`, `1`, `1.0`, and a zero-imaginary complex value numerically equal to `1` identify the same dictionary key. A later equal key must replace the earlier selected value.

R38 tokenized integer/bool keys but R39's generic non-string float representation had no selected-slot token. A later `1.0` therefore failed to replace stale `i:1` metadata, producing both false negatives and false positives.

R41 preserves exact float/complex values and normalizes mapping-only numeric key tokens:

- integral finite floats normalize to the existing integer token;
- zero-imaginary complex values normalize through the same real-number rule;
- non-integral floats and non-real complex values receive deterministic exact tokens;
- NaN is deliberately not assigned an equality token;
- float/complex mapping tokens are not treated as sequence indices.

The same selected-slot rules are used by direct subscripting, `.get` / `.__getitem__`, `operator.getitem`, and `operator.itemgetter` for exact mappings.

## Regression evidence added

The R41 layer includes fixed regression witnesses for:

- `*0.0`, `*0j`, `*...`, aliases, and tuple/list composites stopping later unreachable execution;
- a reachable dangerous call before the definite star failure remaining marked;
- `bytes` expansion remaining iterable and preserving later reachable execution;
- `1`/`1.0` and `True`/`1.0` last-write-wins in both dangerous and safe directions;
- precise non-integral float and complex mapping selection;
- `operator.getitem` / `operator.itemgetter` parity;
- rejection of treating float keys as sequence indices;
- existing builtins-map non-string default behavior;
- the complete current owner/oracle surface remaining marker-free.

## Non-claims

This is an additive test-harness correction only. A green quality gate is necessary regression evidence but is not by itself semantic acceptance. A fresh exact-head DeepSeek Expert review is required after the candidate is frozen again, and no Coder, Claude, merge, #458 closure, or Program-D PASS is authorized by this document.
