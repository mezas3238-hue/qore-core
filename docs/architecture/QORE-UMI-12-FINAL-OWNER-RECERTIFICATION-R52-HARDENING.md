# QORE UMI-12 Final Owner Recertification — R52 Hardening

## Scope

This additive hardening closes the two valid DeepSeek Expert R52 findings against the frozen UMI-12 final-owner recertification harness. It changes tests/docs only and makes no provider, operational, Production, or real-capital claim.

## R52 finding 1 — mixed builtins/sequence receiver

A merged abstract value can contain one exact `builtins` namespace alternative and one sequence alternative. Earlier logic inferred `container-kind=sequence` from the structural sequence metadata and treated `.get(...)` as a definite Python failure before scanning call arguments. That was unsound because the `builtins.__dict__` alternative legitimately supports `.get(...)`, making a later dynamic argument reachable.

R52 now preserves branch provenance with an explicit non-sequence-alternative atom whenever conditional-expression or statement-environment merging combines sequence and non-sequence values. A `.get(...)` call is a definite sequence failure only when the receiver is definitely sequence and has no preserved non-sequence alternative. Ambiguous mixed receivers scan their arguments and remain unknown/fail-closed rather than suppressing reachable evidence.

## R52 finding 2 — exact sequence `.get` attribute access

Exact Python list/tuple values do not expose a `.get` attribute. Earlier attribute evaluation degraded that access to unknown, which could incorrectly scan a later argument even though Python raises `AttributeError` while evaluating the earlier argument.

R52 treats `.get` attribute access on a definitely-sequence receiver as a definite failure. The failure is propagated through the existing ordered-expression machinery, so later arguments remain unreachable.

## Regression guarantees

The R52 successor tests assert that:

- direct conditional `builtins.__dict__ | sequence` receivers do not suppress a reachable later `eval`;
- branch-merged aliases preserve the same non-sequence alternative, including when the sequence itself contains `builtins`;
- exact sequence `.get` attribute access fails before a later dynamic argument;
- exact sequences containing `builtins` remain definite sequences and still fail on `.get`;
- the complete current owner surface plus the frozen historical full-closure oracle remains free of dynamic-execution markers.

All prior R4–R51 hardening layers remain inherited. The historical oracle is not modified.
