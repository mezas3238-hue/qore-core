# QORE UMI-12 final owner recertification — Expert R8 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R8 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R8` against candidate HEAD `e5a8a93bad45d5b11aeffc828fb3c419688de595`.

The single R8 HIGH finding was independently reproduced against both reported scanners and accepted as a material false-negative in the dynamic-execution falsification harness. The exact witness was:

```python
import builtins
getattr(getattr(builtins, "__dict__"), "eval")("1+1")
```

Both the R6 scanner and the final-owner scanner returned no marker on the reviewed HEAD. No production source code was changed by this adjudication or correction.

## R8 hardening

The authoritative complete-suite R6 guard is hardened in place rather than adding another parallel scanner:

- `_is_builtins_namespace` now recursively recognizes `.__dict__` on an already-derived builtins namespace;
- it also recognizes `getattr(namespace, "__dict__")` when `namespace` recursively resolves to builtins;
- the existing dangerous-callable resolver therefore detects an outer `getattr(..., "eval"|"exec"|"__import__")` through that derived namespace;
- fixed regressions cover nested `getattr` through `__dict__` for `eval`, `exec`, and `__import__`;
- the same R6 owner/oracle scan continues to cover every current D04 owner discovered through the certified suffix/legacy convention plus the unchanged historical oracle.

The older final-owner helper remains a narrower independent layer; this is not relied upon for closure of the R8 witness because the complete suite now fails it through the current R6 guard. No claim is made that every historical helper is individually equivalent to the latest hardened scanner.

The historical oracle remains unchanged. This HEAD mutation invalidates R8 as certification of the new candidate and requires the full QORE Quality Gate, a new BASE/HEAD/SYNTHETIC/TREE freeze, and a fresh DeepSeek Expert package before Coder or Claude can run.

No provider support, valuation execution, Production authorization, or real-capital authority is inferred.