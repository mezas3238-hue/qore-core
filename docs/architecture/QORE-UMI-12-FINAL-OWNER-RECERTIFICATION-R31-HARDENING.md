# QORE UMI-12 final owner recertification — R31 hardening

## Status

DeepSeek Expert R31 reviewed frozen PR #461 HEAD `85742a8f6f5e31238b446e1daa74438dfb9c7026` and published `HALLAZGOS: 2 / VALIDACIÓN NO OK`.

The R31 package is consumed. Its semantic verdict cannot certify any later HEAD. The run also reported `plan_incomplete=true` because one planner `git_show` request used an invalid ref; this does not invalidate the two independently reproducible findings, but it independently prevents treating R31 as a clean certification even hypothetically.

## R31-H1 — accepted

Witness:

```python
bucket = {}
for *bucket["items"], (fn, safe) in ((eval, (1,)),):
    pass
```

Python completes the outer extended unpack and then performs target stores from left to right. The starred `Subscript` therefore receives `[eval]` before the later nested `(fn, safe)` unpack fails on `(1,)`.

R30 called `_scan_reachable_target_execution` first and deferred all binding markers to `_assign_iterated_target`. A later nested failure returned `False` before assignment, so the already-reachable sensitive binding was lost.

R31 correction keeps the existing ordered reachability traversal but emits the fail-closed `binding` marker when an `Attribute`/`Subscript` target is actually reached with a sensitive value. Outer arity failure still stops before child targets; a later nested failure cannot erase earlier target execution/binding.

The same rule is exercised for comprehensions.

## R31-H2 — accepted

Witness:

```python
for *fns, tail in ((eval, len),):
    fns("1+1")
```

Python binds `fns` to the list `[eval]`. Calling that list raises `TypeError`; it does not invoke `eval`.

R30 encoded the starred list with correct sequence metadata but also flattened its element semantic atoms into the container value. That made the `Name` itself contain a top-level `dangerous` atom and fabricated `call:2`.

R31 correction represents a starred capture as a sequence value only:

- `container-kind=sequence`;
- exact `sequence-length`;
- per-index `selected-slot` metadata;
- `dangerous-index` / `builtins-index` metadata for direct sensitive elements.

It deliberately does not promote contained semantic atoms to top-level callability. Therefore direct list calls remain unmarked, while exact selection and exact iteration still recover the dangerous element and remain fail-closed.

For sensitive `Attribute`/`Subscript` starred targets, `_is_sensitive_value` additionally recognizes the direct sensitive-index metadata, preserving the accepted R27-R30 binding rule without introducing generic container taint.

## Regression surface

R31 adds guards for:

- sensitive starred `Subscript` binding before a later nested unpack failure;
- the same ordering in a comprehension;
- direct call of a starred `Name` sequence remaining non-dangerous;
- selected dangerous element from that sequence still producing a dynamic-call marker;
- iteration over that sequence still producing a dynamic-call marker;
- ordinary sensitive starred `Subscript` binding remaining fail-closed;
- complete current D04 owner universe plus the historical full-closure oracle remaining marker-free.

## Boundaries

This is a tests/docs-only bounded static-analysis hardening. It does not modify `src/qore`, the historical oracle, provider support, runtime execution, Production authorization, or real-capital posture. It does not add arbitrary whole-program taint or generic iterable interpretation.
