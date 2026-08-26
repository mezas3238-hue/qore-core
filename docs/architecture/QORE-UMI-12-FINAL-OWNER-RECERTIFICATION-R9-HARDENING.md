# QORE UMI-12 final owner recertification — Expert R9 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R9 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R9` against candidate HEAD `a48ccb55196bf09c79ee5b89c55cf23b05a268cf`.

R9 first confirmed that the exact R8 nested-`getattr(..., "__dict__")` witness was closed. It then reported two HIGH bounded static derivations. Both were independently reproduced against both scanners named by the review and accepted as real falsification-harness false negatives:

1. `vars(builtins_alias)["eval"](...)` and equivalent `exec` / `__import__` lookups.
2. `builtins_namespace.__dict__.get("eval")(...)` and equivalent mapping lookup forms.

For each exact R9 witness, the reviewed R6 scanner and the older final-owner scanner returned an empty marker tuple. No production source code was changed by this adjudication or correction.

## R9 hardening

The latest complete-suite R6 guard is hardened in place:

- `_is_builtins_namespace` recognizes `vars(namespace)` only when the argument recursively resolves to the builtins namespace;
- `_contains_dangerous_callable_reference` recognizes `.get(...)` and `.__getitem__(...)` only when the receiver recursively resolves to the builtins namespace and the lookup key is a constant `eval`, `exec`, or `__import__`;
- fixed regressions cover direct `vars(...)` subscripting, `getattr(vars(...), ...)`, mapping `.get(...)`, and `.__getitem__(...)` for the prohibited callables;
- an explicit negative regression proves that ordinary objects or mappings with an `eval`-spelled member/key do not fail merely by spelling when they are not rooted in builtins;
- the existing R6 complete owner/oracle scan continues to apply this hardened resolver across every current D04 owner under the certified suffix/legacy convention plus the unchanged historical oracle.

The older final-owner helper remains a narrower independent layer; closure is established by the current complete suite, not by forcing every historical helper to be textually equivalent.

This HEAD mutation invalidates Expert R9 as certification of the new candidate. A full QORE Quality Gate, new BASE/HEAD/SYNTHETIC/TREE freeze, and a fresh DeepSeek Expert package are required before Coder or Claude can run.

No provider support, valuation execution, Production authorization, or real-capital authority is inferred.