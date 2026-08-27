# QORE UMI-12 Final Owner Recertification — R62 Hardening

## Scope

R62 is a bounded test-harness correction. It does not modify `src/qore`, add
provider/runtime authority, or change any D04 semantic owner.

## Trigger

Independent Integration Authority adjudication after DeepSeek Coder R63 found
a remaining false-negative class outside the R61 mapping fix.

R61 correctly fails closed when an unknown starred selector may expose known
sensitive material. However, a dangerous builtin callable can enter a locally
opaque function as an argument, become abstractly `UNKNOWN` at the function
parameter boundary, be stored in a known mapping, and then be recovered by an
unknown-starred `.__getitem__` path. The direct caller can pass `eval`, while
the prior scanner chain observes only an unknown function result and emits no
marker.

The executable witness returns `42` under CPython 3.12 when the caller passes
`eval` and the mapping helper selects it. The earlier final-owner dynamic
execution scanner also does not mark the direct dangerous callable when it is
used only as an argument rather than bound or directly invoked.

## Correction

`test_universal_cross_asset_conformance_final_owner_r62_guards.py` adds a
successor scanner over R61. Known helper and mapping paths continue to delegate
to the inherited authoritative semantics. For an opaque `Name` call, argument
evaluation reuses the inherited ordered/star-expansion machinery. If argument
evaluation succeeds and a dangerous callable is passed into that opaque call,
R62 emits an explicit `dangerous-escape` review marker.

Definite argument failure remains authoritative and prevents a later dangerous
argument from being promoted. Known `getattr` default semantics remain
unchanged, so an unreachable `eval` default for an exact existing `len`
attribute is not falsely marked.

## Adversarial regression set

R62 covers:

- positional dangerous-callable escape through the concrete mapping witness;
- keyword dangerous-callable escape;
- safe `len` inverse;
- definite starred failure before a later dangerous argument;
- preservation of known-helper default semantics;
- multiple legal starred positional segments in one call;
- the complete current owner plus historical-oracle surface remaining clean.

## Authority boundary

This is harness hardening only. It does not self-certify UMI-12, UMI-14,
Program-D, provider readiness, operational readiness, Production readiness, or
real-capital authorization. A fresh exact-head Quality Gate and the full
external review sequence are required after this mutation.
