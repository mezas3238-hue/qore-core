# CIBO GEN-C11 — ROBUST MULTI-PERIOD CAPITAL MPC V1

Status: PREREGISTERED / RESEARCH-ONLY / SHADOW / NO PRODUCTIVE AUTHORITY

Policy:

`CIBO_GENC11_ROBUST_MULTI_PERIOD_CAPITAL_MPC_V1`

Frozen at:

`2026-09-30T07:40:00Z`

Digest:

`sha256:a919f08abd0dbf4496a9bac553fc9e5c7ca32d4d9a564431f928ba9e4038d7f4`

## Purpose

GEN-C11 extends the existing Phase20I forecastless receding-horizon capacity
planner into a robust multi-period planning layer over GEN-C10 Digital Twin
worlds.

It does not replace Phase20I.

It does not forecast actual future opportunities.

It does not select a production allocation.

## Base planner

Each world/step uses:

`plan_phase20i_receding_horizon_capacity`

with headroom taken from the corresponding GEN-C10 projected state.

## Known-option law

Only options already present in the observed GEN-C10 twin may carry:

- opportunity identity;
- stop-risk geometry;
- margin geometry;
- executable decision step.

Every known option whose earliest action lies inside the horizon must be
scheduled. It may not be silently omitted or delayed.

## Oracle-arrival firewall

GEN-C10 worlds may contain an anonymous hypothetical new-option count.

Those anonymous future arrivals:

- have no identity;
- have no stop-risk geometry;
- have no margin geometry;
- cannot enter Phase20I;
- cannot drive a capital allocation.

## World paths

Every path must:

- contain contiguous steps;
- use one declared GEN-C10 world kind;
- share the same step clock as all compared paths;
- carry factor-interaction evidence;
- carry optionality evidence;
- carry reserve-need evidence;
- carry no market probability;
- carry no future outcome.

Cumulative GEN-C10 scenarios are reconstructed from declared step assumptions.

## Robust envelope

At each step GEN-C11 reports across all worlds:

- minimum common stop-risk headroom;
- minimum common margin headroom;
- maximum required reserve stop risk;
- maximum required reserve margin;
- minimum deployable stop-risk headroom;
- minimum deployable margin headroom;
- minimum projected realized capital;
- whether every world can preserve its known-option horizon.

These are descriptive planning constraints, not execution orders.

## Forbidden

- future opportunity identities;
- outcome-aware arrivals;
- market probability claims;
- weighted-score winner selection;
- hidden future state;
- validation tuning;
- productive mutation;
- allocation authority;
- Risk authority;
- Execution authority.

## V1 claims

V1 may claim only:

- multi-period state consistency;
- robust capacity-envelope mechanics;
- no-oracle option scheduling;
- reuse of the existing forecastless Phase20I planner;
- no productive authority.

V1 must keep false:

- value demonstrated;
- OOS pass;
- stress pass;
- temporal replication pass;
- certification ready.
