# QORE UMI-12 final-owner recertification — R58 runtime adjudication

## Scope

This tests/docs-only layer records the direct CPython 3.12 adjudication of the version-sensitive comprehension `locals()` / zero-argument `vars()` behavior introduced in R57.

No `src/qore` code is changed. This work does not authorize provider support, operational activation, Production, real capital, or Program-D final PASS.

## Why a runtime adjudication was required

R57 correctly identified that Python 3.12 implements PEP 709: list, set, and dictionary comprehensions are inlined, while generator expressions remain separate generator scopes. The subtle point was whether an inlined comprehension at module scope exposes the module `__builtins__` binding through zero-argument `vars()`.

An initial R58 interpretation projected later Python namespace semantics backward and expected the module-scope comprehension lookup to fail. QORE CI #1603 deliberately executed the witness on its configured runtime, CPython 3.12.14, and falsified that interpretation:

```python
visible = ["__builtins__" in vars() for _ in (0,)]
```

On the QORE Python 3.12 gate the result is `[True]`. Therefore R57's module-scope classification is correct for this repository's current Quality Gate.

The corresponding dynamic witness is reachable under Python 3.12:

```python
values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]
```

R57 must mark the dynamic call. Set and dictionary comprehensions have the same Python 3.12 module-scope behavior.

This behavior is version-sensitive. Later Python releases changed/standardized `locals()` semantics through PEP 667, so a newer interpreter must not be used as a substitute for the repository's configured Python 3.12 gate when adjudicating this contract.

## Bounded R58 correction

The failed, unreviewed R58 scanner override was removed before any external package was dispatched. The R58 test layer now:

1. delegates marker semantics to the R57 Python 3.12 scanner;
2. executes list/set/dict comprehension visibility directly and records the version-sensitive result;
3. verifies R57 marks the Python 3.12 module dynamic witnesses;
4. preserves generator-expression nested-body semantics and outer evaluation of the leftmost iterable;
5. preserves non-module function-comprehension handling for zero-argument `vars()`;
6. preserves true module/default detection, R56 inherited scope fixes, and R55 fallback fixes;
7. revalidates the complete owner/oracle surface as marker-free.

## External review posture

DeepSeek Expert R56 is consumed and applies only to predecessor HEAD `c7cc6efb1928e21754a3714d0d21f4ccb22c1876`. No DeepSeek R57 or R58 package was activated against the transient candidates. After the corrected R58 layer passes the complete QORE Quality Gate, a fresh exact-head Expert package is required before Coder can proceed.

## Boundaries preserved

- tests/docs only;
- no `src/qore` delta;
- historical full-closure oracle unchanged;
- no provider or operational capability claim;
- no Production authorization;
- no real-capital authorization;
- no Program-D final PASS claim.
