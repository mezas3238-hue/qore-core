# QORE UMI-12 Final Owner Recertification — R47 Hardening

## Scope

This additive hardening closes the two material findings published by DeepSeek Expert R47 on PR #461 at frozen HEAD `470932ec73542836537a1332ec76c4eddd52f122`.

R47 verdict: `HALLAZGOS: 2 / VALIDACIÓN NO OK`.

The correction remains test-harness-only. It does not change `src/qore`, provider/runtime behavior, Production authority, trading readiness, or real-capital posture.

## R47-F1 — exact unary bool index semantics

Python treats `bool` as an integer for unary plus/minus and sequence indexing. The prior R45 unary override handled exact integer/float/complex/Ellipsis values but omitted the inherited `bool-index` atom, so `-False` degraded to unknown and `[eval][-False](...)` lost the exact selected slot.

The R47 successor reuses `_r35_exact_slice_scalar` after the existing float/complex/Ellipsis handling. This preserves exact `bool-index` and integer semantics and treats exact `None` under unary plus/minus as a definite Python failure.

Regression surface includes:

- `[eval][-False]("1+1")` — dangerous call must be detected;
- `[len, eval][+True]("1+1")` — dangerous call must be detected;
- `[eval, len][-True]("x")` — safe selected slot remains marker-free;
- aliases of exact boolean values retain the same selection semantics;
- exact `None` aliases fail before later unreachable arguments.

## R47-F2 — abstract builtins lookup after `vars` aliases

The prior R45 direct `.get` / `.__getitem__` specialization used syntactic prechecks. That recognized literal `vars(...)` but not an imported helper alias such as `from builtins import vars as v`, even though the inherited scanner already models that alias as the exact `vars` helper.

The R47 successor extends the bounded static builtins-namespace predicate to helper aliases and then evaluates the receiver and call arguments through the existing abstract scanner before selecting the builtins member. This also preserves exact starred-argument expansion such as `get(*["Ellipsis"])`.

Regression surface includes:

- `v(builtins).get("Ellipsis")`;
- `v(builtins).__getitem__("Ellipsis")`;
- `builtins.__dict__.get(*["Ellipsis"])`;
- unary failure on the recovered singleton suppresses only later unreachable effects;
- earlier reachable dynamic effects remain marked.

## Non-claims

This hardening does not establish Program-D final PASS by itself. It does not authorize merge, provider support, Production readiness, Production credentials, autonomous execution, or real capital.

A fresh exact-head full Quality Gate and a fresh DeepSeek Expert package are required because the candidate HEAD changed after R47.
