# QORE UMI-12 Final Owner Recertification — R17 Hardening

## Status

R17 DeepSeek Expert review on frozen HEAD
`ad556f18f8c148087a6030993ed279f1b8500fea` returned
`HALLAZGOS: 2 / VALIDACIÓN NO OK`.

Independent adjudication accepted both findings as real defects in the
test-only falsification harness. This hardening does not change product
code, provider support, execution behavior, or Production authority.

## Accepted R17 finding 1 — class lexical scope

Python class namespaces are execution namespaces, not lexical closures for
method bodies. The inherited R12 scanner passed the mutated class-body
environment into a nested method, so a class attribute such as `eval`
incorrectly shadowed the builtin inside the method.

The R17 scanner now separates:

- class-body execution environment;
- lexical parent captured before the class body;
- function/method body environment;
- lambda body environment created in a class body;
- comprehension body environment created in a class body.

Function decorators and defaults remain evaluated in the current class-body
environment, while method bodies use the lexical parent. Nested functions
inside methods continue to inherit the method environment.

The same boundary is applied to nested classes. Class bases, decorators, and
keyword expressions are scanned explicitly so dynamic execution in a class
header cannot evade the guard.

Regression witnesses include:

```python
class Safe:
    eval = lambda value: value

    def run(self):
        eval("1+1")
```

and class-body lambda/comprehension variants. Genuine class-body and
function-local shadowing remain accepted-safe.

## Accepted R17 finding 2 — bound builtins mapping helpers

R16 corrected direct:

```python
builtins.__dict__.get("len", eval)
```

but the inherited `builtins-map:get` helper path still treated every
non-dangerous builtin member as unknown and therefore selected a dangerous
default even when the key was present.

R17 applies the R16 Python-builtins membership rule to bound helper atoms:

- `builtins-map:get`;
- `builtins-map:__getitem__`;
- assignment aliases;
- `getattr(..., "get")`;
- `operator.attrgetter("get")`.

A present member dominates the default. A statically absent key uses the
default. Dangerous existing members such as `eval`, `exec`, and
`__import__` remain dangerous.

Representative safe witness:

```python
import builtins
getter = builtins.__dict__.get
getter("len", eval)("abc")
```

Representative dangerous witnesses:

```python
getter("missing", eval)("1+1")
getter("eval", len)("1+1")
```

## Boundary preservation

- `src/qore` remains unchanged.
- The historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- Changes remain tests/docs only.
- No provider, network, runtime, execution, Production, or real-capital
  authority is introduced.
- Earlier SHA-bound Expert reviews remain provenance only after this HEAD
  mutation.
- A fresh exact-head Quality Gate and a new DeepSeek Expert package are
  required before Coder may run.
