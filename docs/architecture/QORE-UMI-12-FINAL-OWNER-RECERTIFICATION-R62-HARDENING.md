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

A later Integration Authority reinspection of the exact R62 HEAD exposed a
second false-negative within the same bounded defect class. R39's authoritative
ordered/starred argument scanner evaluates keyword expressions for chronology
and failure handling, but returns only positional abstract values. The initial
R62 implementation therefore recovered direct keyword syntax such as
`candidate=eval`, while a computed keyword value such as
`candidate=getattr(builtins, "eval")`, `candidate=builtins.__dict__["eval"]`,
or `**{"candidate": eval}` could be evaluated as dangerous and then discarded
before R62's opaque-call escape decision.

## Correction

`test_universal_cross_asset_conformance_final_owner_r62_guards.py` adds a
successor scanner over R61. Known helper and mapping paths continue to delegate
to the inherited authoritative semantics. For an opaque `Name` call, argument
evaluation reuses the inherited ordered/star-expansion machinery. If argument
evaluation succeeds and a dangerous callable is passed into that opaque call,
R62 emits an explicit `dangerous-escape` review marker.

The follow-up correction captures the abstract value already produced while
the inherited argument scanner evaluates each keyword expression. It does not
reevaluate the expression, so it does not duplicate markers, mutate scanner
environment twice, or invent a new evaluation order. After successful argument
evaluation, R62 applies the same dangerous-callable predicate to both retained
positional values and captured keyword values. This includes statically known
`**` mappings because the inherited container abstraction preserves dangerous
semantic atoms in addition to structural selection metadata.

Definite argument failure remains authoritative for the existing positional
failure contract, and known `getattr` default semantics remain unchanged. The
separate question of exact CPython 3.12 evaluation behavior for mixed failed
starred positional expansion and keyword expressions remains a mandatory
adversarial review probe; this correction does not broaden that historical
contract by assumption.

## Adversarial regression set

R62 covers:

- positional dangerous-callable escape through the concrete mapping witness;
- direct keyword dangerous-callable escape;
- computed keyword escape through `getattr(builtins, "eval")`;
- computed keyword escape through `builtins.__dict__["eval"]`;
- computed keyword escape through statically known `**` mapping unpacking;
- safe direct `len` inverse;
- safe computed `getattr(builtins, "len")` inverse;
- definite starred failure before a later positional dangerous argument;
- preservation of known-helper default semantics;
- multiple legal starred positional segments in one call;
- the complete current owner plus historical-oracle surface remaining clean.

## Authority boundary

This is harness hardening only. It does not self-certify UMI-12, UMI-14,
Program-D, provider readiness, operational readiness, Production readiness, or
real-capital authorization. A fresh exact-head Quality Gate and the full
external review sequence are required after this mutation.
