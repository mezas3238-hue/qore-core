# QORE UMI-12 Final Owner Recertification — R20B Global-Scope Hardening

## Status

The R20 correction reached exact-head QORE CI green at
`9f5807ef1df86df1802eb2ad87542bf2e3cf4a62`, but independent falsification
found a further bounded Python-scope defect before a new Expert freeze.

R20 correctly distinguished a nested `global` from an ordinary enclosing local,
but its global stack retained only declared-name sets. When a function declaring
`global eval` was separated from a nested user by an intervening function with a
local `eval`, the nested global lookup could read the intervening local instead
of the active module/global path.

This hardening is tests/docs only. It grants no provider, operational,
Production, execution, or real-capital authority.

## Reproduced defect

The critical safe-looking witness is structurally:

```python
eval = lambda value: value

def outer():
    global eval
    del eval

    def middle():
        eval = lambda value: value

        def inner():
            global eval
            return eval("1+1")
```

Python resolves `inner`'s `global eval` through module globals. After the
declared-global `del eval`, the module name is absent and lookup falls through to
the builtin `eval`. The intervening `middle.eval` is irrelevant.

R20 could instead use the immediate definition environment and lose that global
path, yielding no call marker.

## Correction

R20B records each active function-global declaration together with the exact
abstract environment carrying that global path. Nested `global` lookup searches
those overlays directly and therefore skips intervening ordinary locals.

A deleted declared-global name is represented by absence from its overlay, so a
subsequent global lookup falls through to the implicit builtin binding when
appropriate.

## Delete-name semantics

Independent falsification also exposed the same unbinding issue outside nested
globals:

- module `del eval` must remove the module binding so later lookup can reach the
  builtin `eval`;
- a function-local `del eval` must remain locally unbound and must not fall back
  to builtins;
- a class-body delete restores the class lexical parent when one exists, rather
  than converting the name into an opaque local value.

Positive and negative regressions cover all three cases.

## Preserved guarantees

R20B inherits and preserves R20's accepted corrections:

- nested `global` does not close over an enclosing ordinary local;
- method lambdas/comprehensions close over method locals, not residual class
  lexical environments;
- class-body lambdas continue to use the non-class lexical parent;
- valued `AnnAssign` remains RHS -> target/binding -> annotation;
- executable expressions in assignment, annotated-assignment, `for`, `with`,
  comprehension, and `del` targets remain scanned;
- R6-R19 builtins/operator/selected-slot/annotation/scope regressions remain
  authoritative.

## Boundary preservation

- `src/qore` remains unchanged.
- Historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- The previous QORE CI #1533 certifies only `9f5807ef...` and is invalidated by
  this mutation.
- A fresh exact-head full Quality Gate is mandatory before the next SHA-bound
  Expert package.
