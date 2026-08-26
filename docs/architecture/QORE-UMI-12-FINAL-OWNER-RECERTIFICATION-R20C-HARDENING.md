# QORE UMI-12 Final Owner Recertification — R20C Class-Scope Mutation Guard

## Status

Exact-head QORE CI #1535 was green on
`38f86bbbaa94632ee6e0b0b1f17081b981c922ee`.

Before dispatching a new Expert package, independent falsification found a
separate bounded lexical escape: Python permits `global` and `nonlocal`
declarations directly inside class bodies. Those declarations mutate module or
enclosing-cell bindings while the existing class scanner intentionally models a
class namespace plus a non-class lexical parent.

This hardening is tests/docs only and invalidates the previous exact-head gate.

## Reproduced escapes

A class body can mutate a module binding without an ordinary assignment marker:

```python
eval = lambda value: value

class Carrier:
    global eval
    from builtins import eval

eval("1+1")
```

Likewise, a class nested in a function may mutate an enclosing cell:

```python
def outer():
    eval = lambda value: value

    class Carrier:
        nonlocal eval
        from builtins import eval

    def inner():
        return eval("1+1")
```

Treating those import bindings as ordinary class-namespace state can hide the
later dangerous call.

## Bounded fail-closed rule

D04 semantic owner classes have no legitimate need to mutate module globals or
enclosing closure cells during class-body execution.

R20C therefore rejects class-body `global` and `nonlocal` declarations
fail-closed. This is deliberately narrower than whole-program scope analysis:

- function-level `global` remains supported and modeled by R20B;
- ordinary class lexical-parent behavior remains supported;
- method, lambda, comprehension, annotation, target-execution, and selected-slot
  semantics are unchanged.

The complete current owner universe plus historical oracle is scanned through
the R20C layer, so this rule is evidence-checked against the live bounded
surface rather than assumed.

## Boundary preservation

- `src/qore` remains unchanged.
- Historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- No provider, runtime, network, Production, execution, or real-capital
  authority is added.
- A fresh exact-head full Quality Gate is required before Expert R21.
