# QORE UMI-12 final owner recertification — R33 hardening

## Status

DeepSeek Expert R33 reviewed frozen PR #461 HEAD `3c0267926f6064c2c236c9b692722e89d1f484c6` and published `HALLAZGOS: 1 / VALIDACIÓN NO OK`.

R33 is consumed and cannot certify any later HEAD. Its run was mechanically complete: exact BASE/HEAD/synthetic binding passed, `plan_incomplete=false`, final HEAD revalidation passed, and the review was published on the exact reviewed commit.

## R33-F1 — accepted

Witness:

```python
for *fns, tail in ((eval, len),):
    fns[:][0]("1+1")
```

Python binds `fns` to `[eval]`. A full slice produces a new list containing the same element, so `fns[:][0]` resolves to `eval` and the call executes dynamic code.

R31 deliberately stopped flattening a starred sequence's contained semantic atoms into the container itself. That fixed the direct-list-call false positive, but inherited subscript handling did not model `ast.Slice`. Consequently `fns[:]` collapsed to unknown and the reachable `eval` disappeared.

## R33 correction

`_R33ExactSliceScanner` extends the R31 scanner without changing earlier layers.

For `ast.Subscript` whose slice is `ast.Slice`, it:

- evaluates the receiver first and scans lower/upper/step expressions in Python order so dynamic execution in slice bounds remains observable;
- acts only when the receiver is an exact `container-kind=sequence` with an exact sequence length;
- accepts omitted bounds, literal integer/bool bounds, unary signed integer/bool literals, and a single exact integer value already present in the bounded environment;
- applies Python `range(length)[slice(start, stop, step)]` semantics, including negative bounds/steps;
- reconstructs the sliced result from the exact selected slots using the existing R31 sequence representation, thereby recalculating selected-slot, dangerous-index, and builtins-index metadata;
- returns unknown for non-exact bounds/shapes;
- returns unknown for `step == 0`, matching the fact that Python raises before any subsequent element call.

The correction does not promote contained values to top-level callability. Directly calling a starred list therefore remains unmarked, while exact slicing followed by indexing/iteration can recover a dangerous element.

## Regression surface

R33 adds guards for:

- the exact DeepSeek witness `fns[:][0]`;
- a safe bounded slice that excludes `eval`;
- a bounded slice that selects `eval`;
- negative-step reindexing;
- Python bool-as-index slice semantics;
- an exact integer local alias used as a bound;
- dynamic slice-bound execution being scanned without assuming an exact result;
- zero-step slicing not fabricating callability;
- complete current D04 owner universe plus the historical full-closure oracle remaining marker-free.

## Boundaries

This remains a tests/docs-only bounded static-analysis hardening. It does not modify `src/qore`, the historical oracle, provider support, runtime execution, Production authorization, or real-capital posture. It does not add generic iterable interpretation, arbitrary mutable-container taint, or whole-program taint analysis.
