# QORE UMI-12 Final Owner Recertification — R62B Hardening

## Scope

R62B is a bounded test-harness correction derived from the independently
adjudicated DeepSeek Expert R70 evidence. It does not modify `src/qore`, add
provider/runtime authority, change a D04 semantic owner, or authorize
Production/real-capital behavior.

## Trigger

DeepSeek Expert R70 executed the mandatory CPython/scanner matrix against the
frozen R62 HEAD and exposed material false negatives in the final-owner dynamic
execution harness. Integration Authority independently adjudicated the raw
witnesses rather than accepting the reviewer conclusion by authority.

Three defect classes survive adjudication:

1. A locally defined function can return a dangerous builtin callable, e.g.
   `def get_eval(): return eval`, after which `get_eval()("1+1")` executes under
   CPython while the inherited scanner returns no marker.
2. Statically known `importlib.import_module` calls and aliases can perform
   dynamic import while the inherited scanner returns no marker.
3. CPython 3.12 evaluates keyword value expressions after a definitely failing
   starred positional expansion even though later positional expressions are
   not evaluated. Therefore `consume(*None, candidate=eval("1+1"))` executes
   the nested `eval` before the outer call raises `TypeError`; the prior R39/R40
   argument scanner returned immediately on the starred failure and lost that
   reachable keyword execution.

R70 itself classified the first two as material harness defects. Integration
Authority separately classified the third as material because the raw runtime
and scanner outputs proved CPython-executed dynamic code with no scanner marker.
The outer call's later `TypeError` does not erase code execution that has already
occurred while evaluating a keyword expression.

## Correction

`test_universal_cross_asset_conformance_final_owner_r62b_guards.py` adds a
successor scanner over R62 and changes only falsification semantics.

### Sensitive return egress

A `Return` statement is scanned using the existing abstract-value machinery. If
the returned value is already known as sensitive (`dangerous` or `builtins`),
R62B emits the inherited explicit binding marker. This does not attempt arbitrary
function interpretation; it closes the bounded case where dynamic capability is
visibly exported by the function body itself.

### `importlib.import_module`

R62B models a statically known `importlib` namespace and treats
`importlib.import_module` plus `from importlib import import_module` aliases as
dangerous callables. Existing binding/call logic then rejects direct calls and
rebindings without inventing network/provider behavior or executing imports in
the harness.

### Failed-star keyword chronology

R62B preserves the inherited ordered positional assembly, exact star expansion,
unknown-star shape handling, and definite failure result. The only chronology
correction is the CPython 3.12 asymmetry proven by executable evidence: once a
starred positional expansion is definitely non-iterable, later positional
expressions remain unscanned, but remaining keyword value expressions are
scanned for their own side effects/dynamic execution before the outer call is
reported as failed.

A bare keyword value such as `candidate=eval` is not promoted merely because it
is syntactically present after the failed star; if no execution occurs, the
failed outer call remains marker-free. A nested call such as
`candidate=eval("1+1")` is marked because the nested dynamic execution actually
occurs before the outer failure.

## Adversarial regression set

R62B covers:

- real CPython ordering: later positional expression skipped after `*None`;
- real CPython ordering: keyword value expression evaluated after `*None`;
- nested `eval("1+1")` in that reachable keyword path is marked;
- bare `candidate=eval` after failed star remains clean because the outer call
  cannot expose the callable and no dynamic execution occurs;
- safe keyword expression after failed star remains clean;
- direct `return eval` egress is marked;
- computed `return getattr(builtins, "eval")` egress is marked;
- safe `return len` inverse remains clean;
- direct `importlib.import_module` is marked;
- module alias plus rebound callable remains marked;
- `from importlib import import_module as ...` remains marked;
- safe non-dynamic importlib attribute inverse remains clean;
- complete current owner plus historical full-closure oracle surface remains
  marker-free.

The runtime ordering witness is expressed without Mypy suppressions. No
`type: ignore`, skip, xfail, reduced strictness, or coverage weakening is used.

## Quality Gate

The first exact-head R62B code correction was certified by QORE CI #1620 on
CPython 3.12.14: Ruff clean, Mypy clean, 4718 tests passed with the same six
pre-existing PytestCollectionWarning entries, and 87% `src/qore` coverage.

This documentation commit itself changes the Core HEAD and therefore invalidates
that prior exact-head gate for integration purposes. A fresh exact-head QORE CI
is mandatory before any new external Expert package is authoritative.

## Review validity

DeepSeek Expert R70 is consumed evidence for the old R62 HEAD. Because R62B
mutates the candidate, R70 cannot certify the corrected HEAD. Expert, Coder and
Claude reviews must all be fresh and bound to the same post-R62B frozen
HEAD/synthetic/QG.

## Authority boundary

This hardening does not self-certify UMI-12, UMI-14, Program-D, provider
readiness, operational readiness, Production readiness, or real-capital
authorization. No Production enablement is introduced. The canonical sequence
remains exact-head Quality Gate, frozen binding, fresh Expert, independent
adjudication, fresh Coder, independent adjudication, Claude handoff, final
integration gate, protected merge and post-merge verification.
