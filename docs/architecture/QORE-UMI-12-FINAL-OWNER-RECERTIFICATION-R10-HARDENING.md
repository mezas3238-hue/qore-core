# QORE UMI-12 final owner recertification — Expert R10 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R10 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R10` against candidate HEAD `ed9e465b814a28cd68145faec1f8a25aa541daf6`.

R10 confirmed the exact R9 `vars(...)`, `.get(...)`, and `.__getitem__(...)` witnesses were closed, then reported three HIGH bounded static derivations. All three were independently reproduced against the exact reviewed R6 resolver and accepted as real falsification-harness false negatives:

1. `from builtins import __dict__ as ns; ns["eval"](...)`.
2. A single-assignment constant-string alias such as `key = "eval"; getattr(builtins, key)(...)` or `builtins.__dict__[key](...)`.
3. `operator.getitem(builtins.__dict__, "eval")(...)` and equivalent statically bound aliases.

For each exact R10 witness, the reviewed complete-suite R6 helper returned an empty marker tuple. No production source code was changed by this adjudication or correction.

## R10 hardening

The latest complete-suite R6 guard is hardened in place:

- `_builtins_aliases` now recognizes `from builtins import __dict__` aliases as builtins namespace bindings;
- a bounded constant-string resolver follows single-write `Assign`, `AnnAssign`, and `NamedExpr` names to fixed point, including simple static string concatenation, while refusing multiply-written names;
- the resolved strings are used for dangerous `getattr`, subscript, `.get`, `.__getitem__`, and builtins-`__dict__` namespace derivations;
- `operator.getitem` is recognized only through actual `operator` imports or imported `getitem` aliases, only when its first argument resolves to the builtins namespace and its key resolves to `eval`, `exec`, or `__import__`;
- fixed regressions cover all three R10 findings plus alias forms for `operator.getitem` and chained/static string aliases;
- a negative regression proves ordinary mappings using an `eval`-spelled constant key, including `operator.getitem`, remain unmarked when they are not rooted in builtins;
- all R6/R7/R8/R9 regressions remain in the same complete guard and the owner/oracle scan continues across the current certified D04 owner universe plus the unchanged historical oracle.

This HEAD mutation invalidates Expert R10 as certification of the new candidate. A full QORE Quality Gate, new BASE/HEAD/SYNTHETIC/TREE freeze, and a fresh DeepSeek Expert package are required before Coder or Claude can run.

No provider support, valuation execution, Production authorization, or real-capital authority is inferred.
