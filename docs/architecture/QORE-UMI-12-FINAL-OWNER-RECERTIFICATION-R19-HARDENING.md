# QORE UMI-12 Final Owner Recertification — R19 Hardening

## Status

DeepSeek Expert R19B reviewed frozen HEAD
`990ffd499c757420fd79fa2c3892a270496a8f56` after the original R19 package
failed mechanically before model invocation because complete changed-file
evidence exceeded the reviewer input cap. R19B completed on the same frozen
QORE Core HEAD and returned one material HIGH finding.

Independent adjudication accepted the finding but refined the proposed fix to
match Python execution order exactly. The adjudication also falsified nearby
bounded execution/scope forms that remained uncovered by the authoritative
R18 scanner.

This hardening remains tests/docs only. It adds no product, provider, network,
execution, Production, or real-capital authority.

## Accepted R19B finding — valueless `AnnAssign` does not bind its target

For module/class code such as:

```python
eval: eval("1+1")
```

Python evaluates the annotation but does not bind `eval` because the annotated
assignment has no value. R18 assigned `_UNKNOWN` to the target before scanning
the annotation, masking the builtin `eval` and producing a false negative.

The same root defect also hid later calls:

```python
eval: int
eval("1+1")
```

The annotation-only statement does not bind `eval`; the later call still
resolves to the builtin and must be rejected.

R19 preserves the real order for valued annotated assignments:

1. evaluate the value;
2. bind the target;
3. evaluate the annotation where annotations are runtime-evaluated.

For annotation-only assignments, R19 does not invent a binding and evaluates
the annotation only in module/class annotation-execution contexts. Postponed
annotations remain deferred, while the absence of a value still does not bind
the target.

## Independent bounded falsification closed in R19

### `global` declarations

The local-binding collector previously treated a later store as a function
local even when the name was declared `global`, allowing a real earlier builtin
call to be masked:

```python
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result
```

R19 distinguishes `global`/`nonlocal` declarations from genuine local
bindings. Exception targets and structural-pattern captures are also treated as
lexical bindings where Python does so.

### Comprehension scopes and executable clauses

Comprehension targets belong to the implicit comprehension scope, not the
enclosing function. R19 therefore no longer lets a later comprehension target
mask an earlier enclosing builtin call. It also scans generator iterables,
filters, and result expressions in their correct bounded execution scopes.

A statically exact singleton sequence can propagate its selected callable into
the comprehension target, closing the direct alias form:

```python
[fn("1+1") for fn in (eval,)]
```

Safe target shadowing remains unmarked.

### Lambda defaults and lambda lexical bindings

Lambda defaults are evaluated when the lambda expression is created. R18 only
scanned those defaults in the class-specialized path. R19 scans defaults in all
lambda contexts and precomputes lambda-local bindings so a later assignment
expression cannot falsely expose an enclosing builtin for an earlier use.

### `match` guards/bodies and exception matching

The inherited fallback did not traverse `match_case` statement bodies or
guards, and normal `try` handling did not scan exception-type expressions.
`TryStar` was not handled explicitly.

R19 scans:

- the match subject;
- pattern expressions;
- case guards;
- case bodies with capture names bound in the case environment;
- normal and `except*` exception-type expressions;
- normal and `except*` handler bodies.

These are bounded syntax/execution semantics, not arbitrary whole-program
taint analysis.

## Boundary preservation

- `src/qore` remains unchanged.
- Historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- D04 owner convention is unchanged.
- Changes remain tests/docs only.
- R19B is provenance only after this HEAD mutation.
- A fresh exact-head full Quality Gate and a new Expert R20 package are
  mandatory before any Coder review.
