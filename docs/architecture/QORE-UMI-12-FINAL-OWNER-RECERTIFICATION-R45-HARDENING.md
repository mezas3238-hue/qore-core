# QORE UMI-12 Final Owner Recertification — R45 Hardening

## Scope

This is a tests/docs-only correction to the UMI-12 final-owner falsification harness. It does not modify `src/qore`, provider capability, operational authority, Production readiness, or real-capital authorization.

## DeepSeek Expert R45 adjudication

DeepSeek Expert R45 reviewed frozen HEAD `243d598439c011e1aa65a78832f8d26dfda82932` and reported one bounded finding: R44 correctly treated the literal singleton `...` as an exact unary failure, but did not preserve the same identity through Python's builtin name `Ellipsis` and equivalent exact builtin aliases.

The finding is **VALID**.

For example:

```python
def f(*args):
    pass

f(*-Ellipsis, eval("1+1"))
```

Python resolves `Ellipsis` to the builtin singleton, then unary `-` raises `TypeError` before starred expansion and before the later `eval` argument can be evaluated. The same ordering applies to unary `+`, `from builtins import Ellipsis as ...`, and `builtins.Ellipsis`.

## Bounded correction

The additive R45 scanner extends R44 without rewriting historical layers. It:

- recognizes the implicit builtin name `Ellipsis` only when no lexical binding shadows that name;
- preserves exact Ellipsis identity through `from builtins import Ellipsis` aliases;
- preserves exact identity through `builtins.Ellipsis` and aliases of the actual builtins namespace;
- carries that identity through already-bounded static builtins lookup/accessor forms used by the harness (`__dict__` selection, `.get`/`.__getitem__`, `getattr`, `operator.getitem`, `operator.itemgetter`, and `operator.attrgetter`);
- evaluates unary `+`/`-` operands once, propagates existing definite failure, and converts an exact Ellipsis result to the existing definite-failure value;
- preserves existing exact float/complex/integer unary behavior needed by inherited indexing/star semantics;
- does not force a lexical variable named `Ellipsis` to mean the builtin singleton.

The correction remains an abstract static model over explicitly supported Python forms; it does not attempt arbitrary whole-program evaluation or dynamic type inference.

## Regression evidence

The R45 layer adds fixed regressions for:

- bare builtin `Ellipsis` under unary `+`/`-` starred expansion;
- `from builtins import Ellipsis`;
- `builtins.Ellipsis` and module aliases;
- local propagation of exact Ellipsis identity;
- static builtins namespace lookup/accessor equivalents;
- preservation of an earlier reachable dynamic call before the unary failure;
- lexical shadowing of `Ellipsis` by non-builtin values;
- marker-free scanning of the complete current owner/oracle surface.

A fresh full Quality Gate and fresh exact-head DeepSeek Expert review are required after this mutation. R45 is consumed and no longer certifies the mutated candidate.
