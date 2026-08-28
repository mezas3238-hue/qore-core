# QORE UMI-12 Final Owner Recertification — R62G hardening

Status: candidate hardening for PR #461 / issue #458.

## Trigger

Independent Claude review of the frozen R62F candidate identified a real precision regression in direct zero-argument `locals()` / `vars()` handling inside non-module runtime scopes. The prior R55/R56 scope model deliberately avoided inventing a module `__builtins__` binding for nested `vars()`. R62F enriched every zero-argument namespace helper result with module selected slots, so a construct such as:

```python
def run():
    return vars()["__builtins__"].eval("1+1")
```

was conservatively marked even though CPython raises `KeyError("__builtins__")` before reaching `eval` in that function scope.

The finding is accepted as a material harness-precision defect for the recertification gate. It is not an owner defect and does not imply a Production/runtime vulnerability.

## Adjudication refinement

The review attributed the regression broadly to R62E and proposed returning an unknown value for nested `locals()` / `vars()`. That correction is too broad.

R62E intentionally preserves zero-argument namespace objects when captured as callable defaults. A nested function can legitimately retain a local mapping containing an explicitly imported `builtins` module and later expose `eval` through `__defaults__`. Therefore a nested namespace result must remain sensitive for default retention even when it must not be treated as the module namespace for direct selected-slot access.

The direct false positive becomes actionable in R62F, where the retained namespace is decorated with static `builtins` / `__builtins__` selected slots regardless of runtime scope.

## R62G correction

`_R62GScopePreservingRetainedNamespaceScanner` extends R62F without rewriting historical layers.

For zero-argument `locals()` and `vars()`:

- module runtime scope keeps R62F `_R62F_MODULE_NAMESPACE`, including the bounded selected slots needed for direct dynamic-execution detection;
- non-module runtime scope returns R62E `_R62E_RETAINED_NAMESPACE`, which remains sensitive when captured as a default but carries no invented module selected slots.

For zero-argument `globals()`:

- R62F behavior remains unchanged because `globals()` refers to the module global namespace from nested functions as well.

The scope decision reuses the inherited R56/R57 CPython-3.12 runtime-call classification. This preserves PEP 709 behavior: module list/set/dict comprehensions remain module-scoped, function comprehensions remain function-scoped, and generator-expression bodies remain nested.

## Regression evidence

R62G adds executable checks proving:

- R62F reproduces the nested `locals()` / `vars()` false positive while CPython raises `KeyError`;
- R62G keeps those direct nested witnesses clean;
- function comprehensions do not invent module builtins;
- module `locals()` / `vars()` remain fail-closed;
- nested `globals()` remains fail-closed;
- nested retained namespace defaults remain fail-closed and still expose real `builtins` authority when present;
- module comprehensions retain CPython 3.12 module-scope behavior;
- R62F/R62E regressions and the complete owner/oracle surface remain authoritative.

## Boundary

This hardening is test/documentation only. It adds no `src/qore` behavior, provider integration, credential handling, valuation/execution/settlement authority, Production enablement, or real-capital authorization.

Any previous external review bound to the R62F HEAD is non-certifying after this mutation. A fresh exact-head Quality Gate and fresh serial external reviews are required before integration.
