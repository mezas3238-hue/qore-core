# QORE UMI-12 final owner recertification — R49 hardening

## Status

R49 is a bounded, tests/docs-only correction to the UMI-12 final owner/oracle dynamic-execution falsification harness. It does not modify `src/qore`, provider support, runtime behavior, Production readiness, or real-capital authorization.

## Trigger

DeepSeek Expert R49 reviewed frozen HEAD `728fcb965066f30d26a63b4cc462ca3a88703e0a` and reported one valid false-negative class: R48 required exact builtins identity for direct `.get` / `.__getitem__` calls, but inherited R45 paths still used membership-style `_contains_kind(..., "builtins")` when deriving exact `Ellipsis` identity.

A mixed abstract value such as `{builtins, unknown}` could therefore be promoted to the exact builtins namespace in direct attribute/subscript or helper/accessor paths. That promotion could fabricate a definite unary failure and suppress a later `eval`/`exec` call that remains reachable in real Python.

## Correction

`test_universal_cross_asset_conformance_final_owner_r49_guards.py` adds an additive successor scanner over R48 and requires exact `_BUILTINS_NAMESPACE` identity before deriving exact `Ellipsis` through:

- direct `.Ellipsis` attribute access;
- direct non-slice `[...]` access;
- `getattr` and `operator.getitem` helper paths;
- `operator.itemgetter("Ellipsis")`;
- `operator.attrgetter("Ellipsis")`.

For a mixed or otherwise non-exact receiver, the scanner returns `_UNKNOWN` instead of manufacturing the exact singleton. Existing exact builtins aliases and accessor witnesses remain fail-closed.

## Regression witnesses

The R49 layer fixes the exact R49 witness using an inline `builtins if flag else SafeLookup()` receiver and adds equivalent tests for:

- direct `.Ellipsis`;
- `getattr`;
- `operator.getitem`;
- `operator.itemgetter`;
- `operator.attrgetter`;
- preservation of exact builtins `Ellipsis` failure semantics;
- complete current owner/oracle marker-free certification.

## Gate doctrine

R49 invalidates all prior external reviews because HEAD changed. Required sequence remains:

1. exact-head QORE CI;
2. diff/freeze audit and synthetic-parent verification;
3. fresh DeepSeek Expert on the new exact HEAD;
4. only after a clean Expert, DeepSeek Coder on that identical frozen candidate;
5. subsequent manual/final gates before protected merge.

No merge, Program-D final PASS, Production readiness, provider readiness, or capital authorization is implied by this correction.
