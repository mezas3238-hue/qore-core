# QORE UMI-12 Final Owner Recertification — R20 Hardening

## Status

DeepSeek Expert R20 reviewed frozen HEAD
`3bbf8964df92dc112bf4279ebced67d9e94b8a87`.

Independent adjudication rejected R20 finding 1: Python evaluates a valued
module/class `AnnAssign` as RHS, assignment target/binding, then annotation.
The existing R19 regression for
`eval: eval("safe") = lambda value: value` is therefore a valid safe negative.

R20 findings 2 and 3 were accepted as real. Independent falsification also
confirmed that executable expressions embedded in assignment targets were not
traversed by the authoritative scanner.

This hardening remains tests/docs only. It grants no provider, operational,
Production, execution, or real-capital authority.

## Accepted R20 finding — nested `global` resolution

A nested function declaring `global eval` must resolve `eval` from module/global
state, not from a same-named local in its enclosing function. R19 subtracted
`global` names from local bindings but still copied the enclosing lexical value,
allowing a safe outer local to hide the builtin `eval`.

R20 tracks module state separately and resolves an inner `global` from module
state unless an active enclosing function itself declared that name `global`,
in which case the current global-path value is preserved.

## Accepted R20 finding — class-context leakage

R19 could leave an outer class lexical environment on the scanner stack while a
method body was being traversed. A lambda or comprehension nested inside that
method could then incorrectly use the class lexical parent instead of the
method environment.

R20 distinguishes class-body execution from function-body execution. Methods
still exclude class locals, while nested functions, lambdas, comprehensions,
and classes inside a method inherit the method's lexical environment.

## Independent hardening — executable assignment targets

Python executes expressions used to locate non-name assignment targets.
Examples include subscript/attribute targets in:

- ordinary and annotated assignment;
- `for` / `async for`;
- comprehension targets;
- `with` / `async with` `as` targets;
- `del`.

The inherited scanner assigned abstract values to targets without traversing
those executable target expressions. R20 now scans target bases and subscript
keys in Python execution order before applying binding effects. Safe literal
targets remain unmarked.

## Preserved semantics

- Valued module/class `AnnAssign`: RHS -> target/binding -> annotation.
- Annotation-only simple names do not bind the target.
- Function-local variable annotations remain unevaluated.
- `from __future__ import annotations` keeps annotation expressions postponed.
- Method bodies do not close over class locals.
- Lambdas/comprehensions directly in class bodies retain class lexical-parent
  semantics.
- Existing R6-R19 selected-slot, builtins, operator accessor, import,
  directionality, owner-discovery, and safe-negative regressions remain
  authoritative.

## Boundary preservation

- `src/qore` remains unchanged.
- Historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- A fresh exact-head full Quality Gate and a new SHA-bound Expert review are
  required after this mutation.
