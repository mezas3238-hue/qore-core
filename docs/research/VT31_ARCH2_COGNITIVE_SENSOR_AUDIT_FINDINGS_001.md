# VT31 NAS100 — Cognitive Sensor Audit Findings 001

**Status:** OBSERVATION CLOSED / ARCHITECTURE BLOCKERS IDENTIFIED  
**Baseline:** VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR  
**Sensor workflow:** 37543170256 — SUCCESS  
**Sensor head:** 9b97af8e22fcab45c1c3a9e5d4d8da870a608d4e  
**Fresh Holdout:** SEALED

## What was instrumented

The post-entry pipeline now emits read-only telemetry for:

INPUT -> COGNITION -> REASONING -> POSITION OUTPUT -> ACTUATION ROUTE

The sensors do not change admission, exits, targets, stops, size, leverage,
capital, or any economic decision.

A separate Comparator-010 replay after sensor insertion completed SUCCESS
(run 37543029592) and reproduced the same stitched metrics as before the
instrumentation, proving that the sensors themselves are economically inert.

## Cross-fold call accounting

Across the frozen Comparator-009 consumed population:

- trades: 109;
- cognitive post-entry calls: 3,279;
- average calls per trade: 30.0825688073;
- minimum calls per trade: 0;
- maximum calls per trade: 239;
- sensor-missing calls: 0.

Calls by retained partition:

- R5: 1,305;
- R6: 657;
- R8: 810;
- recent consumed: 507.

## Finding 1 — maximum cognition is falsely green with H4 unavailable

All 3,279 calls report:

- full cognitive accounting verified = true;
- maximum cognition verified = true;
- maximum-intelligence blockers = none.

However the input sensor observed:

- H4 state unresolved/unavailable on 1,142 calls;
- those calls span 23 trades.

The reasoning engine explicitly consults the H4 domain and records H4
unavailability as uncertainty, but the maximum-intelligence readiness audit
does not currently promote H4 unavailability to a blocker.

Therefore:

MAXIMUM_COGNITION_VERIFIED currently does not prove that all declared
multitimeframe intelligence is actually available.

This is a certification-integrity defect.

## Finding 2 — one liquidity input is completely unwired

For every one of the 3,279 calls:

recent_liquidity_event_count_10m = None

The field is part of the causal Situation Model and the position cognition can
actuate it when present, yet the current entry snapshot and live post-entry
adapter both hard-code it to None.

The repository already contains a causal closed-M1 structure-event stream
(reference sweeps, local liquidity sweeps and PD-array events), so this is a
plumbing gap rather than missing source data.

No new trading threshold is required: the field itself already defines the
10-minute semantic window.

## Finding 3 — canonical PositionAction is HOLD while a sidecar exits trades

Across all 3,279 observed post-entry calls, the canonical position output is:

- HOLD: 3,279;
- TRAIL: 0;
- EXTEND: 0;
- EXIT: 0.

The canonical output reason is always:

MARKET_STRUCTURE_REMAINS_VALID

At the same time, the frozen Comparator-003/009 pretarget policy authorizes
EXIT through a separate route on 28 calls.

The actuation sensor therefore reports:

- HOLD -> ALIGNED_NO_ACTION: 3,251;
- HOLD -> UNEXPECTED_ROUTE_WHILE_HOLDING: 28.

Those 28 sidecar exits are not random:

- 22 are Comparator-003 base exits only;
- 4 are Comparator-003 + Comparator-009 weak-efficiency exits;
- 2 are Comparator-009 weak-efficiency exits only.

By entry family:

- Breaker: 16;
- Fair Value Gap: 12.

By retained fold:

- R5: 8;
- R6: 3;
- R8: 6;
- recent consumed: 11.

This proves the economic exit path and the canonical full PositionAction path
are still semantically split.

## Finding 4 — 17 terminal losses have zero post-entry cognitive calls

Exactly 17 of the 109 admitted Comparator-009 trades have zero post-entry
cognitive evaluations.

Every one of those 17 trades ends:

- raw R = -1.0;
- exit_reason = structural-invalidation.

Population:

- Breaker: 16;
- FVG: 1.

By fold:

- R5: 4;
- R6: 6;
- R8: 2;
- recent consumed: 5.

One of them is the exact stitched-DD trough trade on 2023-05-01.

These trades cannot be repaired by a decision that requires a fully closed
post-entry M1 if no such decision point exists before structural invalidation.
They belong to the admission / execution-observability problem, not to a
late post-entry management problem.

## Finding 5 — current market-native facts remain unconstructed

The live research adapter still supplies:

- structure_invalidated = false;
- liquidity_failure_confirmed = false;
- regime_changed_against_thesis = false.

Therefore the canonical market-native PositionAction cannot express those
failure modes even though the runtime interface supports them.

This work is assigned to the parallel sensor architect under
VT31_COGNITIVE_SENSOR_PARALLEL_DIRECTIVE_001.md.

## Economic non-interference proof

After sensor insertion, Comparator 010 reproduced:

CONTROL:
- stitched DD: 10.1496554650811747544085540R;
- annualized Sharpe: 1.2766694517591155;
- PF: 4.5979210171;
- expectancy: +2.1310113470R/trade.

LONG + M15 bearish variant:
- stitched DD: 9.8702437003752924014673775R;
- annualized Sharpe: 1.2798980993159643;
- PF: 4.6380091325;
- expectancy: +2.1361307365R/trade.

These match the pre-sensor result. The telemetry did not alter economics.

## Required next repairs

1. Correct maximum-intelligence readiness so declared H4 context cannot be
   unavailable while maximum cognition is reported green.
2. Wire the existing 10-minute causal liquidity-event count into entry and
   post-entry Situation Models.
3. Unify the frozen Comparator-009 pretarget exit decision with the canonical
   PositionAction/actuation surface without changing its economic semantics.
4. In parallel, construct and sensor the three missing market-native facts.
5. Keep the 17 zero-call structural invalidations as a separate admission /
   observability research class.

No Fresh Holdout access is permitted during these repairs.

VT31 remains NOT CERTIFIED.
