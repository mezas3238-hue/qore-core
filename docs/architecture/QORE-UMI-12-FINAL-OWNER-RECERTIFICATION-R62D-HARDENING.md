# QORE UMI-12 Final Owner Recertification — R62D Hardening

## Scope

R62D is a bounded test-harness correction for dangerous callable authority
stored in function or lambda defaults. It changes tests/documentation only. It
does not modify `src/qore`, any D04 semantic owner, provider/runtime behavior,
Production authority, or real-capital behavior.

## Trigger — R74 was published CLEAN but not adjudicated CLEAN

DeepSeek Expert R74 was a real, successfully published review on the exact R62C
candidate. Its binding, checkout, synthetic parents/tree, exact `scanner=r62c`
pre-executed matrix, model finalization, and publication all succeeded. For the
attacks it actually executed, R74 correctly observed that R62C closed the prior
lambda-return and computed-`importlib` false negatives and concluded:

`HALLAZGOS: NINGUNO`

`VALIDACIÓN OK`

Integration Authority did not accept that conclusion by authority. Independent
post-review falsification inspected definition-time/default handling outside the
R74 matrix and found a material callable-default escape. R74 is therefore
consumed evidence, but it is not an adjudicated CLEAN certification and cannot
advance the candidate to Coder.

## Exact predecessor defect

The inherited current scanner chain does scan function and lambda defaults. In
particular, the R19 layer scans positional and keyword-only default expressions
in the defining environment. The defect is not that those AST nodes are wholly
unvisited.

The defect is that their resulting abstract values are discarded before the
callable body is scanned with parameter names set to `_UNKNOWN`. Thus a default
that evaluates to a dangerous callable can be stored by CPython and later
exposed through an omitted argument while the R62C scanner emits no marker.

The R62D regression suite explicitly executes the predecessor R62C scanner on
both a lambda and a function witness and requires the historical false-negative
result `()` before checking the successor closure. This prevents the correction
from being justified only by code-reading inference.

## Executable witnesses

Under the exact CPython 3.12.14 Quality Gate, the following families execute the
stored dangerous callable and are required to fail closed under R62D:

- positional lambda default: `(lambda candidate=eval: candidate)()("1+1")`;
- keyword-only lambda default: `(lambda *, candidate=eval: candidate)()("1+1")`;
- computed lambda default: `getattr(builtins, "eval")`;
- positional function default: `def reveal(candidate=eval): ...`;
- keyword-only function default: `def reveal(*, candidate=eval): ...`;
- computed function default: `getattr(builtins, "eval")`;
- function and lambda defaults carrying `importlib.import_module`;
- a container default carrying `eval`.

The direct `eval` witnesses produce `2`; the importlib witnesses load `math`.
Safe `len` defaults remain clean.

## R62D correction

`test_universal_cross_asset_conformance_final_owner_r62d_guards.py` extends
`_R62CLambdaAndComputedImportlibScanner` without reimplementing default
semantics.

A stack of AST-node-identity capture dictionaries records only the `_Value`
objects already returned by inherited `_scan_expression` calls while a function
or lambda is being scanned. The successor then retrieves the values associated
with the exact `defaults` and non-`None` `kw_defaults` nodes. If any captured
default is already sensitive according to the inherited `_is_sensitive_value`
contract, R62D emits the existing definition-line `binding` marker.

No default expression is scanned a second time. This preserves:

- inherited decorator/default/body evaluation order;
- current class/function/lambda lexical scope handling;
- postponed-annotation behavior;
- existing call markers for dangerous actions executed inside a default;
- R62C lambda-body capture;
- R62C computed-importlib behavior;
- all prior scanner layers and their conservative failure semantics.

Nested lambdas/functions remain stack-safe because each active callable gets an
independent capture dictionary and the outer capture resumes only after the
inner scan returns.

## Regression surface

R62D covers:

- predecessor R62C false-negative reproduction for function and lambda defaults;
- positional and keyword-only lambda `eval` defaults;
- computed lambda `eval` default;
- safe lambda `len` inverse;
- positional and keyword-only function `eval` defaults;
- computed function `eval` default;
- function/lambda `importlib.import_module` defaults;
- safe function `len` inverse;
- sensitive container default;
- inherited R62C lambda-return, computed-importlib, and failed-star chronology
  regressions;
- the complete current owner plus historical full-closure oracle surface
  remaining marker-free.

No `type: ignore`, skip, xfail, strictness reduction, or coverage weakening is
used.

## Code-only Quality Gate

The corrected code-only R62D HEAD
`e376e870a3f9d1a90368939af9a1d0ea388767f9` was certified by QORE CI #1627 /
run `33126982169` on synthetic
`3a264e84732be13c5fcd0cc5037397ab09a87c73`:

- CPython 3.12.14;
- Ruff: all checks passed;
- Mypy: no issues in 730 source files;
- Pytest: 4744 passed;
- same six pre-existing `PytestCollectionWarning` entries;
- `src/qore` coverage: 47568 statements / 6234 missed / 87%.

The 13-test increase from the prior exact R62C gate is exactly the R62D
regression module.

## Review and gate validity

This documentation commit changes the Core HEAD and therefore makes #1627
historical evidence rather than the final integration gate. A fresh exact-head
Quality Gate is mandatory before another external package is activated.

R74 is permanently consumed and becomes SHA-invalid after the R62D mutation.
The next Expert must use a fresh package ID, bind the new HEAD/synthetic/QG, run
the exact `scanner=r62d`, and explicitly compare predecessor R62C versus
successor R62D on positional/keyword-only function and lambda defaults, computed
`eval`, importlib defaults, container defaults, and safe inverses.

Only a fresh Expert that survives independent adjudication may unblock a fresh
Coder review. Claude and integration/merge gates remain downstream.

## Authority boundary

R62D does not certify Program-D, provider readiness, operational readiness,
Production readiness, Production execution, or real capital. It grants no merge
authority. The canonical sequence remains exact-head QG, frozen binding, fresh
Expert, independent adjudication, fresh Coder, independent adjudication, Claude
handoff, integration gate, protected expected-head merge, post-merge exact-main
QG, and issue closure.
