# QORE UMI-12 final owner recertification — R34 hardening

## Status

DeepSeek Expert R34 reviewed frozen PR #461 HEAD `a0fe70056a23aa016b1bf254fef4bdd476c0a36f` and published `HALLAZGOS: 1 / VALIDACIÓN NO OK` with `plan_incomplete=false`.

R34 is consumed and cannot certify any later HEAD. The run completed binding verification, exact checkout, semantic review, final HEAD revalidation, and publication on the exact reviewed commit.

## R34-H1 — accepted

Witness:

```python
flag = True
for *fns, tail in ((eval, len),):
    fns[:flag][0]("1+1")
```

Python retains `flag is True`, so the slice upper bound is numerically `1`. The starred list is `[eval]`, `fns[:flag]` is therefore `[eval]`, `[0]` recovers `eval`, and the call executes dynamic code.

R33 already handled literal boolean bounds because it normalized literal `True`/`False` directly. However, R14 represents an exact boolean stored in the bounded environment as a single `bool-index` atom. R33's environment-value fallback accepted only the `integer` atom kind, so an exact boolean alias degraded to unknown and the dangerous selected slot was lost.

## R34 correction

`_R34BoolAliasSliceScanner` extends `_R33ExactSliceScanner` and keeps the same bounded slice contract. Its only semantic change is to treat a single exact environment atom of kind `bool-index` exactly like Python treats a boolean index/slice component: integer `1` or `0`.

The normalization is limited to single exact atoms:

```text
integer   -> exact int
bool-index -> exact int 0/1
anything ambiguous -> UNKNOWN
```

This preserves R33's evaluation order and conservative handling of dynamic or ambiguous bounds. It does not broaden generic truthy/falsy objects, arbitrary `__index__` implementations, or whole-program value inference.

## Regression surface

R34 adds guards for:

- the exact DeepSeek witness using a `True` alias as the upper bound;
- `False` alias as an upper bound excluding the dangerous slot;
- `True` alias as a lower bound recovering a dangerous suffix;
- `True` alias as step `1`;
- `False` alias as step `0`, where Python raises before later element access/call;
- rebinding an exact boolean alias before the slice;
- complete current D04 owner universe plus the historical full-closure oracle remaining marker-free.

## Boundaries

This remains tests/docs-only bounded static-analysis hardening. It does not modify `src/qore`, the historical oracle, provider support, runtime execution, Production authorization, or real-capital posture. It does not add generic iterable interpretation, arbitrary object `__index__` modeling, mutable-container taint, or whole-program taint analysis.
