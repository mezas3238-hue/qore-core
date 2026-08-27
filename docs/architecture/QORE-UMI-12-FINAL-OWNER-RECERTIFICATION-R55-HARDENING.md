# QORE UMI-12 Final Owner Recertification — R55 Hardening

## Status

Additive tests/docs hardening only. This correction does not modify `src/qore`, provider integrations, runtime activation, Production authorization, or real-capital behavior.

## Trigger

DeepSeek Coder R55, bound to Core HEAD `87f093ef034070510daa479e3963e3581a65329f`, reported three material false-negative paths in the final-owner dynamic-execution falsification scanner. Independent adjudication confirmed all three against Python call semantics and the exact frozen implementation.

The earlier Expert R55 keyword-argument witness for `getattr(object=..., name=...)` remains non-material because Python's builtin `getattr` is positional-only and the call fails before the returned value could be invoked.

## Corrections

### 1. Mapping branch-presence correlation

Merged mappings now retain static-key presence metadata across conditional/environment merges. A key that is present in only some mapping alternatives is marked as possibly missing. For `.get(key, default)`, a selected value from one branch no longer suppresses a reachable default from another branch.

Regression witness:

```python
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", eval)("1+1")
```

The scanner must retain the reachable `eval` call.

### 2. Module-scope zero-argument `vars()`

At module scope, exact zero-argument `vars()` is modeled as the module namespace for the specific `__builtins__` binding needed by the falsification contract. Nested function, lambda, and class scopes do not inherit this module-only promotion.

Regression witness:

```python
vars()["__builtins__"].__dict__["eval"]("1+1")
```

The scanner must retain the reachable `eval` call.

### 3. Positional `getattr` default reachability

For a valid three-positional-argument `getattr(target, name, default)`, the default is retained when attribute presence cannot be proven. Exact known-present builtin attributes and the already-modeled dangerous `__call__` path continue to suppress an unreachable default.

Regression witness:

```python
class Safe:
    pass

getattr(Safe, "missing", eval)("1+1")
```

The scanner must retain the reachable `eval` call.

## Preservation checks

The R55 regression surface also requires:

- exact mapping key presence still suppresses an unreachable dangerous default;
- exact mapping absence still uses the default;
- nested `vars()` does not manufacture the module `__builtins__` binding;
- exact present builtin attributes do not manufacture fallback reachability;
- exact missing builtin attributes retain fallback reachability;
- the Expert R55 keyword-only `getattr` witness remains marker-free because the call fails;
- the complete owner/oracle surface remains free of dynamic-execution markers.

## Scope boundary

This hardening changes only the adversarial certification harness and its documentation. It is not evidence of provider support, operational activation, Production readiness, Production authorization, autonomous execution, or real-capital readiness. It does not constitute a Program-D PASS decision.
