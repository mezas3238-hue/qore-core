# QORE UMI-12 final owner recertification — Expert R12 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R12 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R12` against candidate HEAD `b9c71faa0b279daf0796d3a22516176f5f1b3f29`.

R12 reported three HIGH bounded static false negatives in the complete dynamic-execution falsification surface. Each was independently confirmed against the exact reviewed scanner implementation before mutation:

1. `builtins.getattr(builtins, "eval")(... )` and the equivalent `builtins.vars(...)` helper-identity path were reduced to unknown values because helper identity was recognized only for plain/imported names.
2. `operator.attrgetter("__call__")(eval)(...)`, `operator.getitem([eval], 0)(...)`, and `operator.itemgetter(0)([eval])(...)` could extract an already-dangerous callable because the operator layer only modeled builtins-namespace extraction.
3. A fully static f-string such as `f"{'ev'}{'al'}"` was not reduced to the same bounded constant string as the already-certified concatenation form.

No production source code was implicated; all findings concern the UMI-12 falsification harness.

## R12 hardening

A new independent R12 dynamic-execution closure layer is added without rewriting the historical R6 evidence layer. The complete suite now:

- recognizes `getattr` and `vars` when referenced through a statically resolved builtins namespace, including imported aliases;
- preserves the existing direct `eval` / `exec` / `__import__`, builtins namespace, `__dict__`, callable-`__call__`, import-alias, and lexical-shadowing boundaries;
- models static integer indices and positional dangerous-callable provenance for tuple/list extraction;
- models static string/integer dictionary keys carrying dangerous callables;
- propagates dangerous extraction through `operator.getitem`, `operator.itemgetter`, and `operator.attrgetter("__call__")` while preserving safe-index/key negatives;
- resolves fully static f-strings, including statically string-valued formatted fields and simple deterministic conversions/formats, before builtins lookup classification;
- includes explicit negative regressions for safe `builtins.getattr`, `len.__call__`, safe sequence indices, safe mapping keys, and safe f-string attribute names;
- scans every current D04 owner under the certified `*_semantics.py` / `*_qualification.py` minus `dataset_integrity_qualification` convention plus the six frozen legacy owners and the unchanged historical oracle.

The R6 layer remains historical provenance and is not by itself the certification target after this mutation; material acceptance is determined by the complete current suite including R12.

This HEAD mutation invalidates Expert R12 as certification of the new candidate. A full QORE Quality Gate, new exact BASE/HEAD/SYNTHETIC/TREE freeze, and a fresh DeepSeek Expert package are required before Coder or Claude.

No provider support, valuation/execution authority, Production authorization, or real-capital authority is inferred.
