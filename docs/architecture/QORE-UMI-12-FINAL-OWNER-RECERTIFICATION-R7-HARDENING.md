# QORE UMI-12 final owner recertification — Expert R7 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R7 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R7` against candidate HEAD `78aace94a7a052cc93d4bd75ec7a483ca959d1a5`.

The single R7 HIGH finding was independently reproduced and accepted as a material false-negative in the dynamic-execution falsification harness. No production source code was changed; the correction remains test/documentation-only and does not authorize provider support, valuation, execution, Production, or real capital.

## Accepted R7 finding

The latest dynamic-callable resolver did not recurse through arbitrary AST wrapper expressions after its explicit special cases. Consequently direct dangerous callables could be invoked through callable attributes, including `eval.__call__("1+1")`, `exec.__call__("pass")`, `__import__.__call__("math")`, and `getattr(eval, "__call__")(... )`, without producing a marker.

## R7 hardening

The latest R6 guard is hardened rather than adding another parallel scanner. Its dangerous-callable resolver now:

- preserves the explicit builtins namespace, `getattr`, and `__builtins__` subscript cases;
- recursively descends remaining AST child expressions, so trivial static wrappers around a dangerous callable cannot terminate analysis;
- therefore catches callable-attribute invocation, nested wrapper expressions, and direct dangerous-callable references without treating unrelated attributes named `eval`/`exec` as dangerous unless their roots resolve to the prohibited callable;
- adds fixed regressions for `eval.__call__`, `exec.__call__`, `__import__.__call__`, and `getattr(eval, "__call__")`;
- continues scanning every current D04 owner and the unchanged historical oracle.

The historical oracle remains unchanged. Any mutation after Expert R7 invalidates that SHA-bound review. This candidate therefore requires a fresh full QORE Quality Gate, new exact freeze, and restart from DeepSeek Expert with a new package before Coder or Claude can run.
