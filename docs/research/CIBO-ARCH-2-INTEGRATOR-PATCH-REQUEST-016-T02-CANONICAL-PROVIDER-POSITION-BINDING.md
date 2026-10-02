# CIBO Architect 2 — Integrator Patch Request 016

Status: **T02 EXTERNAL BINDING REQUIRED / ARCHITECT-2 LOCAL INTAKE GREEN**

Architect-2 branch:

`agent/cibo-external-scientific-closure-001`

Local implementation HEAD before this documentation seal:

`2abd8c9a08e4b5de330f47a6df90f186d11b4325`

Scientific closure validating the T02 hardening:

`36953297742 = SUCCESS`

## Problem removed inside Architect-2

The previous T02 lifecycle intake accepted:

`provider_position_binding_verified=True`

as a caller-provided boolean.  That was not sufficient for strict scientific
closure because the QORE `ClientPositionLifecycle` owns a UUID while the
provider/Risk/settlement plane owns an integer provider `position_id`.

Architect-2 no longer accepts that boolean.

The current local contract is:

`T02ProviderPositionBindingReceipt`

in:

`src/qore/infrastructure/cibo_arch2_t02_provider_position_binding.py`

and is consumed by:

- `cibo_arch2_t02_lifecycle_intake.py`;
- `cibo_arch2_t02_structural_binding.py`.

## External producer requirement

B/Integrator must produce the authoritative cross-boundary binding from the
real forward lifecycle.  Architect-2 must not manufacture it.

The receipt binds exactly:

- frozen decision evidence SHA;
- signal fingerprint;
- QORE client-position UUID;
- QORE entry execution receipt UUID;
- QORE exit execution receipt UUID;
- provider position id;
- executed-risk evidence id;
- executed-risk SHA;
- CMA settlement SHA;
- settlement deal ids;
- immutable source-evidence SHA.

The structural binder then requires the executed-risk id/SHA and settlement
SHA/deal ids to match the canonical Architect-B manifest and Phase20 outcome.

## Current upstream gap

The current Architect-B forward economic manifest proves Risk, settlement and
release lineage but does not expose the QORE client-position UUID plus its
entry/exit execution-receipt UUIDs.  Therefore the exact lifecycle/provider
bridge cannot be reconstructed by Architect-2 from the current manifest row
alone.

This is an external evidence dependency, not permission to restore the old
boolean.

## Required action

Produce a canonical source artifact/receipt that can instantiate
`T02ProviderPositionBindingReceipt` from real forward evidence.

Do not:

- infer lifecycle identity from PnL;
- infer a stop from price proximity;
- map positions by symbol/time heuristics;
- invent provider position ids;
- invent settlement deals;
- mark a caller boolean as verified.

After the receipt population exists, Architect-2 can run the already-frozen:

1. lifecycle terminal-reason intake;
2. structural OOS audit;
3. provider-bound T02 economic ablation;
4. mechanical terminal disposition.

## Relationship to Patch Request 011

Patch 011 remains the population request for T02/T20.  This Patch 016 narrows
the T02 binding format required for that population and supersedes any
interpretation that a boolean `provider_position_binding_verified` is
admissible scientific evidence.

## Governance

- canonical ledger modified by Architect-2: **false**
- Phase22 V2 consumed: **false**
- provider outcome invented: **false**
- lifecycle/provider binding invented: **false**
- FundedNext/VPS touched: **false**
- productive authority: **false**
