# QORE UMI-12 Final Owner Recertification — R62C Hardening

## Scope

R62C is a bounded falsification-harness correction derived from independently
adjudicated executable evidence obtained after R62B. It changes test-harness
semantics only. It does not modify `src/qore`, any D04 semantic owner,
provider/runtime behavior, Production authority, or real-capital behavior.

## Trigger and review status

DeepSeek Expert packages R71, R72, and R73 are consumed and do not certify the
R62C candidate.

- R71 failed mechanically because the model did not invoke the mandatory probe
  suite; no semantic review was published.
- R72 failed mechanically before any model call because the generic runtime
  sandbox correctly rejected a non-allowlisted `import importlib`; no semantic
  review was published.
- Reviewer v8 preserved that generic sandbox and executed only a closed set of
  infrastructure-owned importlib runtime witnesses before the model. R73 later
  failed mechanically in final-fallback budget admission and published no
  review, but its deterministic pre-model CPython/scanner matrix completed and
  is valid primary evidence independent of the absent model verdict.

Integration Authority adjudicated that raw matrix directly.

## Material findings from the R73 pre-executed matrix

Four dangerous paths executed under CPython while R62B returned an empty marker
tuple. Each was adjudicated `VALID / MATERIAL / HARNESS DEFECT`:

1. `(lambda: eval)()("1+1")` returned `2`, while R62B returned `()`.
2. `getattr(importlib, "import_module")("math")` imported `math`, while R62B
   returned `()`.
3. `importlib.__dict__["import_module"]("math")` imported `math`, while R62B
   returned `()`.
4. `vars(importlib)["import_module"]("math")` imported `math`, while R62B
   returned `()`.

The corresponding safe lambda/importlib inverses remained marker-free. The
prior R62B closures also remained effective in the same matrix: failed-star
keyword execution, explicit/computed function return egress, direct/static
`importlib.import_module` aliases, successful opaque-call keyword/positional
escapes, multiple starred segments, and builtins lookup forms were marked as
expected.

A model review is not required to establish these four defects because the
runtime and exact scanner outputs were produced deterministically by reviewer
infrastructure before the model call. The model package itself remains consumed
as a mechanical failure and cannot be reused as certification.

## R62C correction

`test_universal_cross_asset_conformance_final_owner_r62c_guards.py` extends the
R62B scanner without rewriting the inherited abstraction stack.

### Lambda sensitive-value egress

R62C preserves inherited lambda scope/default/body scanning. It captures only
the abstract value that the inherited scanner already computes for the lambda
body. If that body value is sensitive, the existing explicit binding marker is
emitted.

This closes visible capability egress such as direct `lambda: eval` and computed
`lambda: getattr(builtins, "eval")` while leaving `lambda: len` clean. It does
not introduce arbitrary function or lambda execution into the scanner.

### Computed `importlib` namespace access

R62C decorates the statically known `importlib` namespace as a mapping with a
single security-relevant selected slot:

- namespace atom: `importlib`;
- mapping container metadata;
- present key `s:import_module`;
- selected slot `s:import_module -> dangerous`.

The existing inherited mapping/accessor machinery can therefore remain
authoritative. R62C adds only bounded namespace behavior necessary to preserve
that metadata through:

- direct `importlib.import_module`;
- `getattr(importlib, "import_module")`;
- `getattr(importlib, "__dict__")`;
- `importlib.__dict__["import_module"]`;
- `vars(importlib)["import_module"]`;
- aliases/rebinding of the namespace or dangerous callable;
- mapping `.get`;
- `operator.getitem`, `operator.itemgetter`, and `operator.attrgetter`.

Unknown or explicitly safe importlib attributes remain `_UNKNOWN`/clean rather
than being globally classified dangerous.

## Regression surface

R62C includes regressions for:

- real direct lambda dangerous egress;
- computed lambda dangerous egress;
- safe lambda callable inverse;
- computed importlib `getattr` execution;
- computed importlib alias/rebinding;
- `__dict__` and `vars` lookup execution;
- namespace alias then subscript/rebinding;
- mapping `.get`;
- operator getitem/itemgetter/attrgetter paths;
- safe computed importlib inverses;
- R62B failed-star keyword chronology;
- R62B explicit return egress;
- R62B direct importlib path;
- complete current owner plus historical full-closure oracle surface remaining
  marker-free.

No `type: ignore`, skip, xfail, strictness reduction, or coverage weakening is
used.

## Quality Gate evidence

The code-only R62C HEAD `78aafcb65dfb5c0fdc2c4f9fc87ffb9101888b3a`
was certified by QORE CI #1624 / run `33125409310` on the PR synthetic
`a35cdca45be25e65d2da145a24395f52f9104b0a`:

- CPython 3.12.14;
- Ruff: all checks passed;
- Mypy: no issues in 729 source files;
- Pytest: 4731 passed;
- six pre-existing `PytestCollectionWarning` entries;
- `src/qore` coverage: 47568 statements / 6234 missed / 87%.

The historical full-closure oracle remains blob
`249caa1504e2b62277a9389dc7e73bcabf12e7db`.

This documentation commit changes the Core HEAD, so #1624 is historical evidence
only after this commit. A fresh exact-head Quality Gate is mandatory before any
new external Expert package can certify the candidate.

## Review validity and next gate

R70 through R73 are all consumed and invalid for the post-R62C documentation
HEAD. The next DeepSeek Expert must use a fresh package ID and be bound to the
new exact HEAD, synthetic merge, oracle blob, and fresh exact-head Quality Gate.
The reviewer matrix must target the exact R62C scanner and must include the
lambda and computed-importlib attacks above plus their safe inverses.

Only after a fresh Expert produces complete evidence and every finding is
independently adjudicated may a fresh Coder review be considered. Claude and
integration/merge gates remain downstream and blocked until then.

## Authority boundary

R62C does not certify Program-D, provider readiness, operational readiness,
Production readiness, Production execution, or real capital. It does not grant
merge authority. QORE Integration Authority remains final, and the canonical
sequence remains: exact-head QG, frozen binding, fresh Expert, independent
adjudication, fresh Coder, independent adjudication, Claude handoff,
integration gate, protected expected-head merge, post-merge exact-main QG, then
issue closure.
