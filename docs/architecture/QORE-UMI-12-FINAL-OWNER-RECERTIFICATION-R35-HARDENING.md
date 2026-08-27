# QORE UMI-12 final owner recertification — R35 hardening

## Status

DeepSeek Expert R35 reviewed frozen PR #461 HEAD
`009a95087f3c200464787dff15983861063dd68a` and published
`HALLAZGOS: 4 / VALIDACIÓN NO OK` with `plan_incomplete=false`.

R35 is consumed and cannot certify any later HEAD. Its workflow verified the
live PR binding, checked out the exact qore-core commit, verified synthetic
parents/tree, completed semantic review, revalidated the frozen HEAD, and
published review `5036307553` on that exact commit.

All four HIGH findings are accepted after independent Python-semantic
adjudication.

## R35-H1 — explicit and aliased `None` slice components

Witness:

```python
for *fns, tail in ((eval, len),):
    fns[:None][0]("1+1")
```

Python treats an explicit `None` slice component the same as an omitted bound.
R34 represented exact integer/bool aliases but did not preserve `None`, so
`fns[:None]` degraded to unknown and hid the reachable `eval`.

The R35 layer introduces one bounded exact value atom, `none`, used only to
retain literal/aliased `None` through the existing static environment and
normalize it to an omitted slice component. It does not infer generic
nullability.

## R35-H2 — unary sign over exact integer/bool aliases

Witness:

```python
for *fns, tail in ((len, eval, str),):
    step = 1
    fns[::-step][0]("1+1")
```

Python evaluates `-step` as `-1`; the exact reversed starred list starts with
`eval`. R34 normalized unary signs only when the operand was a literal.

R35 evaluates the unary operand once, preserves its execution side effects, and
applies unary `+`/`-` only when the operand resolves to one exact `integer` or
`bool-index` atom. Ambiguous operands remain unknown.

## R35-H3 — definite slice failure stops later slice components

Witness:

```python
for *fns, tail in ((eval, len),):
    fns[fns[::0] : eval("1+1")][0]("1+1")
```

For an exact Python sequence, `fns[::0]` raises `ValueError`. Because that
failure occurs while evaluating the outer lower bound, the outer upper bound
`eval(...)` is never evaluated.

R33 returned ordinary unknown for the recognized zero-step failure. That lost
the distinction between "unknown value" and "expression definitely failed",
allowing later bounds to be scanned and fabricating dynamic execution.

R35 introduces an internal bounded `definite-failure` value for recognized
exact-sequence slice failure. Subscript evaluation now preserves Python order:

```text
receiver -> lower -> upper -> step -> subscription
```

If receiver or a prior component has a recognized definite failure, subsequent
subscript components are not scanned. A zero step is considered definite only
after proving the receiver is an exact sequence; arbitrary custom objects are
not assumed to reject `slice(..., step=0)`.

## R35-H4 — exact ordinary tuple/list assignment distribution

Witness:

```python
for *fns, tail in ((len, eval, str),):
    start, inc = True, 1
    fns[start::inc][0]("1+1")
```

The existing ordinary `_assign_target` recursively copied the flattened RHS
value union into every tuple/list target. That made both aliases ambiguous even
though the RHS sequence had exact positional metadata.

R35 distributes exact static sequence slots positionally for ordinary
tuple/list assignment. Exact one-star assignment is also distributed with the
starred target retaining an exact sequence value. Nested exact destructuring is
recursive. Non-exact or ambiguous structures retain the inherited conservative
behavior.

## Regression surface

R35 adds guards for:

- the exact explicit-`None` DeepSeek witness;
- an aliased `None` bound;
- the exact unary integer-alias negative-step witness;
- unary negative sign over a boolean alias;
- the exact earlier-zero-step-failure witness;
- preservation of a prior reachable bound call while suppressing a later step;
- the exact ordinary tuple-unpack witness;
- a safe positional-unpack inverse;
- nested exact ordinary unpacking;
- `None` surviving exact ordinary unpacking;
- the complete current D04 owner universe plus the unchanged historical oracle
  remaining marker-free.

## Boundaries

This remains tests/docs-only bounded static-analysis hardening. It does not
modify `src/qore`, the historical full-closure oracle, provider support,
runtime execution, Production authorization, or real-capital posture.

It does not add arbitrary `__index__` modeling, generic iterable
interpretation, generic truthiness/nullability analysis, whole-program taint,
container mutation tracking, or exception-flow reconstruction outside the
recognized exact slice failure described above.
