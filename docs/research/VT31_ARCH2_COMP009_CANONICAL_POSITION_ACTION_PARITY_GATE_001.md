# VT31 NAS100 — Comparator-009 Canonical PositionAction Parity Repair Gate 001

**Status:** PREDECLARED SEMANTIC PARITY REPAIR  
**Economic baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Defect

The read-only cognitive sensor audit recorded:

- 109 Comparator-009 trades;
- 3,279 post-entry cognitive calls;
- 3,279 canonical `PositionAction.HOLD` outputs;
- 28 `UNEXPECTED_ROUTE_WHILE_HOLDING` events.

The research replay was therefore routing validated EXIT actions through a
parallel authorizer while the canonical full-cognition decision still reported
HOLD.

That is semantic/replay-runtime incoherence.

## Repair scope

This repair may **not add a new economic rule**.

It may only express inside the canonical post-entry decision the exact adverse
exit logic already frozen in Comparator 009:

### Existing Comparator-003 adverse-exit component

Requires:

- maximum cognition verified;
- causal `current_open_r <= -0.50R`;
- and at least one already-validated condition:
  - management context CAUTIOUS; or
  - management context MIXED with reclaim age in the existing 8-14 minute
    stale bucket; or
  - FVG entry with non-SHALLOW destination; or
  - normal frozen reference-volatility state with entry family other than
    Order Block.

### Existing Comparator-009 Breaker weak-efficiency component

Requires:

- maximum cognition verified;
- causal `current_open_r <= -0.50R`;
- Breaker entry;
- management context MIXED;
- causal recent path efficiency available and <= the existing 0.30 weak-path
  threshold.

No threshold is new.

## Canonical action

When either frozen adverse-exit component is true before the primary target,
the canonical post-entry decision must expose:

`PositionAction.EXIT`

with a distinct parity reason.

The replay authorizer may still exist temporarily for backwards compatibility,
but its route must agree with the canonical output.

## Non-regression requirements

The repair must demonstrate:

1. same Comparator-009 admitted trade identity;
2. same terminal R for every Comparator-009 trade;
3. same per-fold metrics;
4. same stitched metrics;
5. no new exit dates or fold-specific authority;
6. cognitive sensor no longer reports an EXIT route while canonical output is
   HOLD for Comparator-009 baseline;
7. full-cognition and maximum-cognition accounting remain required;
8. no sizing, leverage, compounding or capital logic.

If economics change, this is **not** a parity repair and must be rejected.

## Governance

Consumed development evidence only.

No Fresh Holdout access.

No certification, LIVE, real-capital or production authorization.
