# QORE UMI-12 final-owner recertification — R59 hardening

## Scope

This tests/docs-only successor corrects a concurrent R58 regression introduced after DeepSeek Expert R56 adjudication. No `src/qore` code is changed.

This work does not authorize provider support, operational activation, Production, real capital, or Program-D final PASS.

## Why R58 is not authoritative

R58 claimed that, although PEP 709 inlines list/set/dict comprehensions, module/class-scope `locals()` / zero-argument `vars()` in Python 3.12 still behaves as if the comprehension were an independent nested function.

That claim is the Python **3.13** PEP 667 behavior projected backward.

For Python 3.12, PEP 709 explicitly changed comprehensions so that:

- list, set, and dict comprehensions are inlined;
- `locals()` inside a comprehension includes locals from the containing scope;
- comprehensions at module and class scope are also inlined;
- generator expressions are not inlined by the PEP 709 reference implementation.

Python 3.13's PEP 667 porting notes explicitly state that module/class comprehension `locals()` once more behaves as if the comprehension were an independent nested function, and explicitly contrast this with Python 3.12, where containing-scope locals were included.

QORE CI currently runs CPython 3.12. Therefore R58's module-comprehension expectation is invalid for the frozen runtime contract.

## R59 correction

`test_universal_cross_asset_conformance_final_owner_r59_guards.py` resumes from the R57 scanner rather than inheriting R58's invalid override.

The regressions mechanically assert that on CPython 3.12:

1. module-level list/set/dict comprehensions keep module zero-argument `vars()` visibility and therefore preserve reachable dynamic execution through `__builtins__`;
2. direct runtime execution sees `"__builtins__" in vars()` as true in those module-level comprehensions;
3. generator-expression bodies remain nested for this purpose;
4. a generator expression's leftmost iterable remains evaluated in the enclosing module scope;
5. function comprehensions are not promoted to module `vars()`;
6. class comprehensions are not promoted to module `vars()`;
7. R56 inherited function/lambda/class scope restoration remains in force;
8. R55 mapping/default fallback hardening remains in force;
9. the full current owner/oracle surface remains marker-free.

## Review posture

- DeepSeek Expert R56 is consumed and applies only to predecessor HEAD `c7cc6efb1928e21754a3714d0d21f4ccb22c1876`.
- The previously prepared R57 reviewer prompt became stale before activation because Core mutated concurrently; it must never be activated against the successor.
- R58 is retained as historical evidence but is not the authoritative final scanner layer.
- The R59 successor requires a fresh full QORE Quality Gate and a new exact HEAD/TREE/synthetic freeze before any new DeepSeek Expert package may be activated.

## Boundaries preserved

- tests/docs only;
- no `src/qore` delta;
- historical oracle must remain unchanged;
- no provider/runtime/network capability claim;
- no Production authorization;
- no real-capital authorization;
- no Program-D final PASS claim.
