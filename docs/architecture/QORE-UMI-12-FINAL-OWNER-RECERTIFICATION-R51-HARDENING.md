# QORE UMI-12 Final Owner Recertification — R51 Hardening

## Context

DeepSeek Expert R51 reviewed PR #461 at exact HEAD `d412dbd3e2bc55606ecb39697507cfe859186b0c` and found one valid harness defect. The authoritative scanner could derive `builtins.__dict__.get` as `{helper:builtins-map:get, unknown}` instead of an exact helper identity. That uncertainty prevented exact `Ellipsis` propagation, so unary `-Ellipsis` was not recognized as a definite failure and an unreachable later `eval(...)` was falsely marked reachable.

This is a test-harness correction only. `src/qore` remains unchanged and no provider, Production, execution, or real-capital readiness is inferred.

## R51 correction

The successor scanner makes builtins mapping-method derivation exact only when the abstract receiver is exactly `_BUILTINS_NAMESPACE`.

Covered forms:

- `builtins.__dict__.get`
- `builtins.__dict__.__getitem__`
- `getattr(builtins.__dict__, "get")`
- `getattr(builtins.__dict__, "__getitem__")`
- `operator.attrgetter("get")(builtins.__dict__)`
- `operator.attrgetter("__getitem__")(builtins.__dict__)`

For an exact builtins namespace these expressions reduce to the exact helper atom `builtins-map:get` or `builtins-map:__getitem__` without inherited `_UNKNOWN`. A mixed abstract receiver containing both builtins and another possibility is not promoted to an exact builtins helper and remains unknown.

## Required invariants

- Exact builtins identities preserve exact `Ellipsis` lookup and real Python unary failure ordering.
- Mixed `{builtins, ...}` values never manufacture an exact namespace or helper identity.
- Reachable `eval`/`exec`/`__import__` calls remain detectable.
- Effects after a statically definite failure remain unreachable.
- Historical owner/oracle surface remains marker-free.
- `src/qore` delta remains zero.

## Gate posture

R51 Expert is consumed and invalid for any successor HEAD. The successor candidate requires the full QORE Quality Gate and a fresh exact-head DeepSeek Expert review before Coder or merge gates may proceed.
