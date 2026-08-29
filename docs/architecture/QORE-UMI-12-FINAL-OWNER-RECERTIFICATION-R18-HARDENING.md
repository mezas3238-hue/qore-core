# QORE UMI-12 Final Owner Recertification — R18 Hardening

## Status

DeepSeek Expert R18 reviewed frozen HEAD
`c08ae8a97f93713edf4bf85442bb426c5e371166` and returned one material
HIGH finding: annotation-time dynamic execution was not traversed by the
newest authoritative scanner.

Independent adjudication accepted the finding as real and bounded. This
hardening remains tests/docs only and introduces no product, provider,
network, execution, Production, or real-capital authority.

## Accepted R18 finding — runtime annotation evaluation

Without `from __future__ import annotations`, Python evaluates function
parameter/return annotations when the `def` statement executes, and evaluates
module/class variable annotations in their execution scope. Therefore sources
such as:

```python
def f(value: eval("1+1")):
    return value
```

and:

```python
x: eval("1+1") = 1
```

contain actual dynamic execution and must be rejected by the owner/oracle
falsification scanner.

The previous R17 layer scanned decorators/defaults and executable bodies but
not function annotations or `AnnAssign.annotation`, causing a bounded false
negative.

## R18 correction

The R18 scanner now models annotation execution explicitly:

- function argument and return annotations are scanned when annotations are
  evaluated at definition time;
- module- and class-scope `AnnAssign.annotation` expressions are scanned;
- function-local variable annotations remain unscanned because Python does not
  evaluate them;
- `from __future__ import annotations` postpones annotation evaluation and
  therefore suppresses annotation-expression scanning for the module;
- function defaults remain executable even with postponed annotations and are
  still scanned;
- method annotations are evaluated in the class-body execution environment,
  while method bodies retain the R17 lexical-parent correction and do not
  close over class locals.

Regression witnesses cover direct `eval`, `exec`, and `__import__` annotation
execution, function-local safe negatives, class-local annotation shadowing,
postponed annotations, and executable defaults under postponed annotations.

## Boundary preservation

- `src/qore` remains unchanged.
- Historical oracle
  `tests/infrastructure/test_universal_cross_asset_conformance_full_closure.py`
  remains unchanged.
- Changes remain tests/docs only.
- Earlier SHA-bound reviews are provenance only after this HEAD mutation.
- A fresh exact-head Quality Gate and a new DeepSeek Expert package are
  required before Coder may run.
