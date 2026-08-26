# QORE UMI-12 Final Owner Recertification — R13B Hardening

## Scope

This record adjudicates the exact-head DeepSeek Expert R13B review for PR #461.
The reviewed candidate was `32b81bbfd3397c1acdfa8cfaddec4aec6fb2cdb3`.
R13B reported three bounded defects in the R12 dynamic-execution scanner. Independent code inspection accepted all three as real defects.

## Accepted defects

1. Negative static sequence indices used through `operator.getitem` / `operator.itemgetter` could lose dangerous-position provenance.
2. Bound `get` / `__getitem__` methods obtained from the `builtins` namespace could be assigned to a local name and later extract `eval`, `exec`, or `__import__` without detection.
3. Direct subscripting propagated danger from any co-present container element instead of only the statically selected dangerous position/key, causing a safe-negative false positive.

## Correction

A new R13 guard layer supersedes the R12 scanner as the authoritative complete-suite dynamic-execution check while preserving the R12 file as historical review evidence.

The R13 layer:

- carries explicit static sequence-length metadata so negative indices are normalized deterministically;
- applies the same negative-index resolution to direct subscript, `operator.getitem`, and `operator.itemgetter` extraction;
- models bound `builtins` mapping methods `get` and `__getitem__` as explicit helper values that retain their namespace authority through assignment;
- propagates danger from direct subscripting only when the selected static position/key is dangerous;
- keeps prior R12 positive witnesses closed;
- adds explicit safe-selected-position regressions; and
- scans the full current D04 owner universe plus the unchanged historical full-closure oracle.

## Boundaries

This hardening changes tests/docs only. It does not add provider support, runtime/network authority, Production authorization, trading authority, real-capital capability, or source implementation behavior.

Any HEAD mutation invalidates prior SHA-bound external certification. The corrected candidate therefore requires a new full Quality Gate, freeze, and fresh DeepSeek Expert review before Coder may run.
