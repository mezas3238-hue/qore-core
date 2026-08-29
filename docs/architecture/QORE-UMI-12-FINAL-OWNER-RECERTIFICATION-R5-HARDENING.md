# QORE UMI-12 final owner recertification — Expert R5 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R5 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R5` against candidate HEAD `b6120d62429b682fce8c0901231785278ccb0364`.

Both R5 findings were independently reproduced and accepted as material falsification-harness bypasses. No production source code was changed; the correction remains test/documentation-only and does not authorize provider support, valuation, execution, Production, or real capital.

## Accepted R5 findings

1. **Builtins module alias / `__dict__` access.** A chain such as `import builtins as b; f = b; f.eval(...)` was not propagated into the builtins alias set, and `builtins.__dict__["eval"](...)` was not recognized as dynamic execution.
2. **Starred value rebinding.** Composite values such as `x = [*[b.eval]]` hid a dangerous callable below `ast.Starred`, while the R4 helper only covered starred targets.

## R5 hardening

A supplemental independent R5 guard now:

- computes builtins-module aliases to fixed point across `Assign`, `AnnAssign`, and `NamedExpr` scalar alias chains;
- recognizes both a builtins alias and its `.__dict__` as builtins namespaces;
- rejects direct dangerous attributes, `getattr(...)`, dictionary lookup, and direct calls derived from those namespaces;
- recursively descends tuple/list/set/dict and `ast.Starred` value shapes;
- scans every current D04 owner discovered through the certified suffix/legacy convention plus the unchanged historical full-closure oracle;
- includes fixed regressions for module-alias chains, `builtins.__dict__[...]`, `getattr(alias.__dict__, ...)`, and starred-value rebinding.

The historical oracle remains unchanged. Any mutation after Expert R5 invalidates that SHA-bound review, so this hardening requires a fresh full QORE Quality Gate, new BASE/HEAD/SYNTHETIC/TREE freeze, and restart from DeepSeek Expert before Coder or Claude can run.
