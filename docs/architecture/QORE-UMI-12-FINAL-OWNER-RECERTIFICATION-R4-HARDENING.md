# QORE UMI-12 final owner recertification — Expert R4 hardening

Status: candidate hardening for issue #458 / PR #461.

This note records independent adjudication of DeepSeek Expert R4 package `QORE-UMI14-UMI12-FINAL-OWNER-RECERT-001-DS-EXPERT-R4` against candidate HEAD `9f6b904556dbded2d606c7298470f2f0b0cc84e1`.

All three R4 findings were independently accepted as material harness bypasses. No production source code was changed by this hardening; the correction is test/documentation-only and does not authorize provider support, valuation, execution, Production, or real capital.

## Accepted R4 findings

1. **Absolute package `from` import expansion.** The prior normalized import scanner recorded only `qore.infrastructure` for `from qore.infrastructure import execution_boundary`, allowing the imported forbidden submodule to evade the provider/runtime/network classifier.
2. **Composite callable rebinding.** Tuple/list rebinding such as `first, second = eval, exec` was not represented by the scalar dangerous-callable resolver and therefore could evade the dynamic execution guard.
3. **Direct HTTP client roots.** The network deny surface did not include `http` or `urllib3`, allowing direct HTTP client imports such as `http.client` or `urllib3`.

## R4 hardening

A supplemental final-owner adversarial guard now:

- resolves relative imports and expands absolute `from qore.infrastructure import X` forms to `qore.infrastructure.X` before forbidden-authority classification;
- scans the complete current D04 owner surface under the already-certified naming/legacy convention plus the unchanged historical oracle;
- rejects provider/runtime/execution fragments and a broadened bounded set of direct standard-library and third-party network-client roots;
- rejects composite tuple/list/set/dict rebinding expressions containing `eval`, `exec`, `__import__`, dangerous `builtins` attributes, `getattr(builtins, ...)`, or `__builtins__[...]` references;
- includes fixed synthetic regressions for absolute package import, tuple/list/nested/starred rebinding, and direct HTTP roots.

The historical oracle remains unchanged. The pre-existing final-owner guards remain as independent layers; the R4 supplemental layer ensures the concrete accepted-invalid R4 witnesses cannot pass the complete recertification suite.

Any candidate mutation after the R4 review invalidates all SHA-bound external reviews. Therefore this hardening requires a new full QORE Quality Gate, new BASE/HEAD/SYNTHETIC/TREE freeze, and restart at DeepSeek Expert before Coder or Claude can run.
