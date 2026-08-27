# UMI14 / UMI12 — R39 hardening

DeepSeek Expert package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R39` reviewed exact HEAD `f2b1a972b943cdbda80174ac461534922ab3e8de` and returned `HALLAZGOS: 3 / VALIDACIÓN NO OK`.

All three findings were independently adjudicated against Python execution semantics and the frozen R38 scanner and were accepted as valid harness defects. This hardening changes tests/evidence only; it does not change `src/qore`, does not add provider/runtime capability, and does not authorize Program-D final PASS, Production, provider readiness, or real capital.

## Accepted finding 1 — definite failure during starred expansion

Python raises `TypeError` while expanding a definitely non-iterable starred value before evaluating later tuple/list elements or later call arguments. R38 treated an unexpandable exact integer like an unknown-length expansion and could scan unreachable `eval`/`exec` calls.

R39 distinguishes:

- exact modeled sequences: expand positions exactly;
- definitely non-iterable values: propagate `definite-failure` and stop later evaluation;
- genuinely unknown expansion shapes: preserve uncertainty without inventing a positional arity for `.get`/`.__getitem__` selection.

Regression witnesses cover both tuple construction and call-argument expansion.

## Accepted finding 2 — container identity must dominate embedded `builtins`

A sequence or mapping may contain the `builtins` module as a selected value without itself becoming the builtins namespace. R38 inspected the flattened `builtins` atom before exact container dispatch in the special `.get` / `.__getitem__` path.

R39 gives an explicit exact container kind priority over embedded semantic atoms. Consequently:

- `[builtins].__getitem__(0)` returns the selected `builtins` module and a subsequent `.eval(...)` is detected;
- `{"eval": builtins}.__getitem__("eval")` returns the module itself and does not fabricate a dangerous callable merely because the selected mapping value is `builtins`.

## Accepted finding 3 — exact non-string builtins keys

The builtins namespace has string keys. An exact non-string `ast.Constant` such as `0.0`, `b"eval"`, or `0j` is therefore a known miss for `builtins.__dict__.get`, so a supplied default is selected.

R39 records bounded exact non-string constant identity only for this builtins-membership fact. It deliberately does not invent general mapping key equality for unsupported key classes. For a normal mapping with an unselectable key shape, `.get` degrades to unknown instead of falsely selecting its default.

## Regression and scope guarantees

The R39 guard inherits the full R4–R38 chain and adds regressions for:

- non-iterable starred tuple/list failure ordering;
- non-iterable starred call failure ordering;
- exact sequence `.__getitem__` containing `builtins`;
- exact mapping `.__getitem__` containing `builtins`;
- builtins `.get` with exact float/bytes/complex keys;
- safe unknown normal-mapping selection;
- complete current owner/oracle surface remaining marker-free.

The historical full-closure oracle remains unchanged. `src/qore` remains unchanged. A fresh exact-head FULL QG and a fresh DeepSeek Expert package are required; R39 is consumed and must not be rerun.
