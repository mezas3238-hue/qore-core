# QORE UMI-12 Final Owner Recertification — R48 Hardening

## Context

DeepSeek Expert R48 reviewed frozen candidate `9d57c413422e9bc17ef926c4f3887c787362a8d6` and returned `HALLAZGOS: 1 / VALIDACIÓN NO OK`.

The finding was independently adjudicated as valid. The R47 builtins-namespace predicate used membership checks such as `_contains_kind(..., "helper", "vars")` and `_contains_kind(..., "builtins")`. After conservative branch merging, an abstract value such as `{helper:vars, unknown}` could therefore be promoted incorrectly to exact `vars` identity. That promotion could force an ambiguous `v(builtins)` expression into the exact builtins namespace, recover `Ellipsis`, manufacture a definite unary failure, and suppress a later `eval` that is reachable in real Python execution.

## R48 correction

R48 adds an authoritative successor scanner without modifying earlier guard layers or `src/qore`.

The direct `.get` / `.__getitem__` evaluation path now:

1. evaluates the receiver and arguments in Python order;
2. preserves definite-failure short-circuiting;
3. preserves exact mapping and sequence selected-slot behavior;
4. applies special builtins lookup semantics only when the evaluated receiver is exactly `_BUILTINS_NAMESPACE`;
5. returns unknown for mixed or merged builtins-like values instead of coercing them to exact builtins identity.

This removes the R48 false negative while preserving the exact imported-`vars` alias and direct builtins `Ellipsis` failure regressions established by R47.

## Added regressions

The R48 layer asserts that:

- a branch-merged `vars`/unknown binding does not suppress a reachable `eval`;
- a branch-merged builtins/unknown namespace does not become exact builtins identity;
- an exact `from builtins import vars as v` alias still propagates exact `Ellipsis` lookup identity;
- direct `builtins.__dict__.get` / `.__getitem__` exact `Ellipsis` lookup still fails before later unreachable execution;
- the complete owner/oracle surface remains marker-free.

## Scope and non-claims

This is a tests/docs-only falsification-harness hardening. It does not modify QORE runtime/product code, enable a provider, authorize Production, authorize real capital, close #458, or establish Program-D final PASS. All subsequent external-review gates must bind to the new exact candidate HEAD produced by this correction.