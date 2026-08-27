# QORE UMI-12 final-owner recertification — R58 hardening

## Scope

This additive tests/docs-only successor corrects the R57 module/class comprehension `vars()` model introduced concurrently after the R56 correction.

No `src/qore` code is changed. This work does not authorize provider support, operational activation, Production, real capital, or Program-D final PASS.

## R57 adjudication

R57 correctly noted that Python 3.12 implements PEP 709 and inlines list, set, and dictionary comprehensions, while generator expressions remain separate generator scopes. However, R57 drew an incorrect conclusion for `locals()` / zero-argument `vars()` at module and class scope.

PEP 709 states that comprehensions still introduce an isolated sub-scope for iteration variables even when inlined. More importantly for the owner scanner, the language/runtime behavior for `locals()` at module/class scope does not expose the module/class namespace to an inlined comprehension as if the call occurred directly in that outer scope. PEP 667's discussion of PEP 709 explicitly records that module/class inlined comprehensions behave as if the comprehension were still a distinct function for `locals()`.

Therefore this witness:

```python
values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]
```

raises at the `__builtins__` lookup instead of reaching `eval`. The same applies to set and dictionary comprehensions at module scope. Treating those calls as true module `vars()` creates a false positive and can fabricate dynamic-execution reachability.

The Python 3.13 PEP 667 changes do not justify projecting module globals into Python 3.12 comprehensions. PEP 667 standardizes namespace-view behavior while explicitly describing module/class inlined comprehensions as nested-function-like for `locals()`.

## Bounded R58 correction

`test_universal_cross_asset_conformance_final_owner_r58_guards.py` adds a successor scanner that:

1. preserves the R57 file as historical evidence rather than rewriting it;
2. restores R56's call-position scope classifier for the narrow zero-argument `vars()` module-vs-non-module distinction;
3. keeps list/set/dict comprehension bodies non-module at module/class scope;
4. keeps generator-expression bodies nested while preserving the outer evaluation of the leftmost iterable;
5. preserves true module `vars()` and function/lambda definition-default detection;
6. preserves the inherited R56 global/lambda/class scope fixes and all R55 fallback fixes;
7. validates real runtime key visibility for list/set/dict comprehensions and revalidates the complete owner/oracle surface as marker-free.

## External review posture

DeepSeek Expert R56 is consumed and applies only to predecessor HEAD `c7cc6efb1928e21754a3714d0d21f4ccb22c1876`. No DeepSeek R57 package was activated against the transient R57 Core candidate. The R58 successor requires a full exact-head QORE Quality Gate and a fresh frozen Expert review before any Coder review can proceed.

## Boundaries preserved

- tests/docs only;
- no `src/qore` delta;
- historical full-closure oracle unchanged;
- no provider or operational capability claim;
- no Production authorization;
- no real-capital authorization;
- no Program-D final PASS claim.
