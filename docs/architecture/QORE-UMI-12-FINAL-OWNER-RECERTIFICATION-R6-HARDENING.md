# QORE UMI-12 final owner recertification — Expert R6 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R6 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R6` against candidate HEAD `7030cd95b884668b8016692e4ab20d38e382ab02`.

All three R6 findings were independently reproduced against the exact reviewed helpers and accepted as material falsification-harness bypasses. No production source code was changed; the correction remains test/documentation-only and does not authorize provider support, valuation, execution, Production, or real capital.

## Accepted R6 findings

1. **Composite builtins namespace rebinding.** Tuple unpacking and container bindings such as `c, d = b, builtins` and `x = [b]` could derive a builtins namespace without producing a dynamic-execution marker.
2. **Subscript callable extraction.** A trivial extraction such as `x = [eval][0]` crossed an `ast.Subscript` boundary that the R4/R5 scanners did not recursively inspect, so no marker was produced.
3. **Absolute package-from directionality bypass.** Directionality resolvers recorded only `qore.infrastructure` for `from qore.infrastructure import rainbow_option_composition_semantics`, allowing generic authorities to reverse-import product qualifications through that syntax.

## R6 hardening

A supplemental independent R6 guard now:

- rejects assignments whose values contain a builtins namespace directly or inside tuple/list/set/dict/starred/subscript shapes, so derived namespace containers fail closed at the binding boundary;
- recursively resolves dangerous callable references through `ast.Subscript`, including `[eval][0]`;
- preserves direct `eval`/`exec`/`__import__`, builtins attribute, `getattr`, and `__dict__` detection;
- expands both relative package imports and absolute `from qore.infrastructure import X` forms to the concrete submodule;
- applies the expanded resolver to generic/product and cross-family directionality across the current D04 owner surface;
- scans every current D04 owner discovered through the certified suffix/legacy convention plus the unchanged historical oracle;
- includes fixed synthetic regressions for all three accepted R6 witnesses.

The historical oracle remains unchanged. Any mutation after Expert R6 invalidates that SHA-bound review, so this hardening requires a fresh full QORE Quality Gate, new BASE/HEAD/SYNTHETIC/TREE freeze, and restart from DeepSeek Expert with a new package before Coder or Claude can run.
