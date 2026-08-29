# QORE UMI-12 final owner recertification — R29 hardening

## Trigger

DeepSeek Expert R29 reviewed PR #461 at exact HEAD
`4166d59a2d0b4691f254fb133a6cd6425069e5d4` and reported two HIGH
iteration-structure defects. The run was mechanically complete, `plan_incomplete=false`,
and published its review on the exact frozen HEAD.

## Adjudication

Both findings are **ACCEPTED**.

### R29-H1 — divergent per-item lengths lose sensitive starred target

Witness:

```python
bucket = {}
for *bucket["items"], tail in ((eval, len), (eval, len, str)):
    bucket["items"][0]("1+1")
```

R28 merges the two iterated item values before target assignment. Their structural
lengths become `{2, 3}`, so the exact single-length path is lost and the starred
`Subscript` no longer reaches the R27/R28 fail-closed sensitive-target rule.
Python, however, assigns a list containing `eval` to the starred subscript on each
reachable iteration.

R29 fixes this without inventing arbitrary container taint: before the legacy merged
model is used, it probes the statically common exact iteration prefix item by item,
preserving each item's own selected-slot and length metadata. Reachable exact items
are assigned through the existing R28 recursive target logic, so a sensitive starred
`Attribute`/`Subscript` emits `binding`.

This is deliberately more precise than simply unioning all slots across divergent
lengths. Such a union can destroy length/slot correlation and falsely move a dangerous
tail value into a starred middle. R29 includes a negative regression proving that
correlation remains preserved.

### R29-H2 — first-item unpack failure incorrectly reaches body

Witness:

```python
for fn, safe in ((eval, len, str), (eval, len)):
    fn("1+1")
```

Python fails on the first target assignment because the first item has length three
and the target requires length two. The body, second item, and `for ... else` suite
are therefore unreachable.

R25's merged iterated value erased that order and combined lengths `{2, 3}`. R28 then
saw mixed compatibility and conservatively scanned the dangerous body, producing a
false positive.

R29 probes statically available iteration positions in execution order before
collapsing them. A definite target failure at the first reachable item terminates the
loop/comprehension scan before body/element/later positions. For a later definite
failure, only the already reachable prefix is admitted and the `else` suite is not
scanned. Exact empty iterables skip the body and retain the `else` path.

## Regression evidence

The R29 guard covers:

- divergent exact starred `Subscript` with `eval` -> fail-closed `binding`;
- a correlation-preserving safe divergent-star case where dangerous values are only
  tails and must not taint the starred target;
- definite first-item unpack failure -> no dangerous body marker;
- the same failure -> no unreachable `else` marker;
- exact empty iterable -> body unreachable, `else` reachable;
- comprehension first-item unpack failure -> element unreachable;
- comprehension divergent-star sensitive binding;
- complete current owner + historical oracle zero-marker recertification.

## Review-consumption boundary

DeepSeek Expert R29 certifies only the superseded HEAD
`4166d59a2d0b4691f254fb133a6cd6425069e5d4`. Its two accepted findings caused the
R29 correction, so that review is consumed and cannot certify any corrected HEAD.
The corrected candidate must pass a fresh exact-head Quality Gate and a new unique
Expert package before any Coder gate is eligible.

## Scope

This remains a tests/docs-only UMI-12 recertification hardening. It does not modify
`src/qore`, the historical full-closure oracle, provider support, Production
authorization, execution readiness, or real-capital posture.
