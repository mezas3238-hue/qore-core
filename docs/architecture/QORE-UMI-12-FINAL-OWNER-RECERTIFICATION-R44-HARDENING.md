# QORE UMI-12 Final Owner Recertification — R44 Hardening

## Scope

This correction is limited to the tests/docs-only UMI-12 final-owner recertification harness. It does not change `src/qore`, provider support, operational authority, Production readiness, or real-capital authorization.

## DeepSeek Expert R44 adjudication

DeepSeek Expert R44 reviewed frozen HEAD `d186fc91b084067e944cb4b9940f08629cc9bb7d` and reported one bounded finding:

```python
def f(*args):
    pass

f(*-..., eval("1+1"))
```

The finding is **VALID**.

Python evaluates the unary operand before attempting starred expansion and before later call arguments. `-Ellipsis` raises `TypeError: bad operand type for unary -: 'ellipsis'`; therefore the later `eval("1+1")` expression is unreachable. The R41 scanner represented exact Ellipsis but normalized unary `+`/`-` only for exact float and complex values, allowing unary Ellipsis to degrade to unknown and incorrectly scan the later argument.

## Bounded correction

The additive R44 scanner extends R41 only for exact unary Ellipsis failure semantics:

- direct `-...` and `+...` resolve to the existing definite-failure value;
- names already bound to exact Ellipsis receive the same treatment under unary `+`/`-`;
- later call arguments and later tuple/list elements are suppressed after that definite failure;
- dangerous execution that occurs before the failure remains visible;
- existing float/complex unary behavior and iterable `bytes` starred behavior remain inherited unchanged.

No general arbitrary-expression evaluator or new production behavior is introduced.

## Regression evidence

The R44 layer adds synthetic regressions for:

- direct unary Ellipsis in starred call arguments;
- exact Ellipsis aliases;
- tuple/list starred composite evaluation order;
- preservation of an earlier reachable dynamic call;
- preservation of R41 numeric-star and bytes-star behavior;
- marker-free scanning of the complete current owner/oracle surface.

A fresh full Quality Gate and exact-head external review are required after this mutation. Previous R44 review evidence is consumed and no longer certifies the mutated candidate.
