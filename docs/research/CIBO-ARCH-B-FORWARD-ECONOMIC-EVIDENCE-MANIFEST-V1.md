# CIBO Architect B — Forward Economic Evidence Manifest V1

Status: **IMPLEMENTED CONTRACT / REAL FORWARD POPULATION REQUIRED**

This artifact is the machine boundary from Architect B to Architect A. It does
not create scientific results. It proves which forward observations have a
complete immutable economic lineage that Architect A may consume.

## Bound chain

For every complete row:

```text
Phase20D pre-outcome decision seal
  -> provider-native observation sealed in that decision
  -> frozen V3 policy seal + fixed baseline identity
  -> independent QORE Risk / executed structural-risk evidence
  -> terminal CMA settlement
  -> terminal Phase20 outcome
  -> observed T20 capacity release
```

The builder refuses to synthesize or impute any missing link.

## Frozen identity

The manifest accepts only the existing frozen Phase20 V3 lineage:

- candidate: `CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3`;
- code SHA: `edf96722fd0505711aa88bc1d15296b09e6dba6f`;
- exact frozen parameter SHA from the canonical candidate;
- Phase20D V4 qualification plan and its fixed minimal-seed baseline;
- chronological folds `WF1..WF4`.

No existing freeze is modified.

## Scientific consumption semantics

`ready_for_scientific_consumption=true` requires:

1. Phase20D has progressed beyond `NOT_READY` / `INVALID` to an empirical
   `PASS` or `FAIL`;
2. every outcome-bearing lineage required for the qualified population is
   reconciled through Risk, execution, CMA settlement and T20 release;
3. no selected baseline/policy observation is missing its terminal outcome;
4. provider evidence is pre-decision and the collector Git SHA is present.

An empirical `FAIL` may still be scientifically consumable: A must be able to
learn that a hypothesis was falsified. It is **not** certification.

The manifest permanently reports:

- `certification_ready=false`;
- `productive_authority=false`.

## Provider economics

Provider economics are copied only from the sealed pre-decision
`ProviderEconomicObservation`: bid/ask, minimum volume, volume step,
margin-per-volume, commission reserve and slippage reserve. The manifest also
hashes that exact provider payload. It does not project current DEMO terms onto
2017 or invent historical USD economics.

## Risk / CMA / release truth

The manifest verifies that:

- outcome executed-risk id equals the durable executed-risk evidence;
- executed stop risk is arithmetically identical;
- CMA settlement is terminal and deal ids match the outcome exactly;
- terminal settlement realized net PnL equals the Phase20 outcome;
- T20 authorization binds the same decision/signal/position/execution id;
- T20 release restores all realized stop-risk capacity;
- terminal release timestamp and capital-minutes agree with the Phase20 outcome.

A mismatch raises a hard error. Missing evidence becomes an explicit gap.

## Current limitation

The repository does not contain a completed real Phase20D population at the
frozen thresholds. Therefore this contract can be CI-certified mechanically
while the B workstreams `FORWARD_QUALIFICATION`, `FRESH_OOS`, `T20`,
provider execution calibration and the final USD60 capability program remain
empirically open.
