# QORE UMI-12 Final Owner Recertification — R60 hardening

## Scope

This hardening closes the external-review finding that generic dynamic-access helpers could receive an inline starred positional tuple whose runtime arguments were collapsed into one abstract scanner argument.

The concrete witnesses were:

- `getattr(*(builtins, "eval"))("1+1")`
- `operator.getitem(*(builtins.__dict__, "eval"))("1+1")`

Under CPython call semantics the starred iterable is expanded into positional arguments. The inherited generic helper path did not preserve that expansion even though later mapping-specific paths already had exact starred-argument machinery.

## Correction

`test_universal_cross_asset_conformance_final_owner_r60_guards.py` adds a monotonic successor scanner over R59. It:

- leaves every non-starred call path unchanged;
- preserves inherited mapping `get` / `__getitem__` handling;
- reuses the existing exact positional-star expansion and definite-failure machinery for generic helper calls;
- preserves the R56/R57 runtime-scope classification used by Python 3.12 `vars()` / comprehension guards;
- fails closed with an explicit review marker when a known helper/accessor receives an unresolved starred positional shape;
- adds discriminating dangerous and safe witnesses;
- rechecks the complete current owner plus historical-oracle surface.

## Ownership and boundaries

This is a harness-only correction. No `src/qore` owner is changed and no production semantic defect is asserted. The historical full-closure oracle remains untouched. This hardening does not authorize provider readiness, operational readiness, Production, deployment, or real capital.

The prior DeepSeek Expert/Coder R60 and Claude review remain historical evidence for their frozen predecessor HEAD only. Any external approval for this corrected candidate must bind to the new exact HEAD/tree/synthetic and exact-head QORE Quality Gate.
