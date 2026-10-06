# CIBO USD60 / 6-MONTH MAXIMUM REAL CAPABILITY CERTIFICATION V1

**Primary PR:** #651  
**Branch:** `agent/cibo-capital-efficiency-sizing-lab-001`  
**Source of truth:** GitHub  
**Status:** FROZEN CERTIFICATION PROTOCOL / NOT YET CERTIFIED

## 1. Question being answered

This program answers exactly one empirical question:

> What can CIBO really do with USD60 over six complete months when all valid
> CIBO engineering capabilities are available, without an economic target and
> without helping the system with hindsight?

The mission is one coupled objective:

```text
SURVIVE
+
MAXIMIZE ROBUST ECONOMIC OUTPUT
```

Survival alone is insufficient. Aggressive terminal ruin is insufficient.

## 2. Frozen experiment identity

```text
INITIAL CAPITAL: USD60
DURATION:        6 COMPLETE MONTHS
TRADERS:         7 CANONICAL LINEAGES
CIBO:            T01..T20
ECONOMIC TARGET: NONE
```

Milestones are observation-only:

```text
100
150
200
300
500
1000
2500
5000
10000
```

The policy must never receive milestone state as a decision feature.

## 3. Authority chain

```text
TRADER VALID OPPORTUNITY
        |
        v
CIBO CAPITAL DECISION
        |
        v
QORE RISK
ALLOW / REDUCE / REJECT
        |
        v
EXECUTION MODEL
```

Trader owns technical methodology and geometry.

CIBO owns sizing and capital management.

Risk remains the independent hard survivability governor.

Execution mutates only after CIBO + Risk.

## 4. Capital law

The experiment starts with exactly USD60 of operational capital.

Forbidden:

- recapitalization;
- hidden external capital;
- balance reset after losses;
- fabricated margin/headroom;
- fabricated protected capacity;
- floating PnL treated as spendable realized capital;
- double-spend;
- reuse before reconciliation;
- target-aware sizing;
- martingale;
- loss-recovery sizing.

The USD60 base is not a permanent untouchable reserve. CIBO must decide
causally how much is available, reserved, deployed, protected, recycled,
expanded, de-risked or released.

## 5. Complete CE2I surface

The exam requires the full canonical surface:

- T01 Minimal Seed
- T02 Structural Leverage
- T03 Margin Efficiency
- T04 Risk Efficiency
- T05 Capital Recycling
- T06 Profit-Funded Expansion
- T07 Protected-Capacity Expansion
- T08 Portfolio Netting
- T09 Opportunity Competition
- T10 Capital Velocity
- T11 Execution-Efficient Exposure
- T12 Regime-Adaptive Capitalization
- T13 Drawdown Reserve
- T14 Dynamic De-risking
- T15 Capital Optionality
- T16 Hedged Exposure / Risk Transfer
- T17 Convex / Limited-Downside Exposure
- T18 Cross-Trader Capital Allocation
- T19 Capacity Reservation
- T20 Capital Release

`CONTRACT_IMPLEMENTED` is not empirical validation.

Every tool must demonstrate:

```text
correct input evidence
causal decision
correct capital source
correct action
correct rollback
fail-closed behavior
incremental economic behavior
```

If causal calibration is unavailable:

```text
CALIBRATION_UNAVAILABLE
-> FAIL_CLOSED
```

That is safe behavior, but it is not certification.

## 6. Growing-capital law

CIBO must adapt naturally to actual realized capital.

No hard-coded steps may be introduced for USD70, USD100, USD200, USD500,
USD1000 or any later balance.

Capital growth changes only causal state:

- available capital;
- realized profit;
- protected economic floor;
- risk/margin headroom;
- source-ledger balances;
- portfolio exposure;
- opportunity set;
- regime;
- optionality.

## 7. Baselines

Three complete six-month paths must be evaluated over the same sealed
opportunity population and provider economics:

```text
A. MINIMAL_SEED_ONLY
B. PREVIOUS_CIBO_CORE
C. FULL_CIBO_T01_T20
```

The full policy cannot receive information unavailable to the baselines at the
same decision timestamp.

## 8. Ablation

Where scientifically identifiable:

```text
FULL - T01
FULL - T02
...
FULL - T20
```

Ablation measures multi-dimensional incremental value:

- realized output;
- drawdown;
- survival;
- risk efficiency;
- margin efficiency;
- velocity;
- reusable capacity;
- optionality;
- concentration;
- execution economics.

A tool need not increase raw profit directly to have value, but a tool with no
measured contribution cannot be called empirically valuable.

## 9. Full trajectory

The sealed path must retain at every capital event:

```text
timestamp
realized capital
equity when observationally available
available capital
reserved capital
deployed capital
protected capital
base capital at risk
realized profit
risk headroom
margin headroom
realized/economic drawdown
CIBO regime/stage
active tools
tool decisions
capital-source movements
```

## 10. Mandatory final metrics

At minimum:

- initial / ending / peak / minimum capital;
- net realized profit;
- return on initial capital;
- maximum realized and economic drawdown;
- drawdown duration;
- opportunities / executions / reductions / Risk rejects / CIBO holds;
- expansions / de-risk events;
- capital / margin / risk utilization;
- profit per risk-dollar;
- profit per margin-dollar;
- profit per capital-day;
- capital velocity;
- recycled risk and margin capacity;
- realized-profit deployment;
- protected-capacity deployment;
- reserve utilization;
- optionality preservation;
- cross-Trader reallocations;
- netting / hedge / convex events;
- T01..T20 activation / blocked / fail-closed counts;
- milestone timestamps, if reached.

## 11. Fresh OOS law

The final exam may not use periods consumed to modify or calibrate the
architecture.

```text
development/calibration
        |
        v
freeze
        |
        v
fresh independent holdout
```

Any consumed interval is BURNED for the final fresh holdout.

No threshold, allocation, tool selection, regime boundary or risk behavior may
be modified from the final holdout outcome and then retested on that same
holdout.

## 12. Stress program

Mandatory stress includes:

- loss clusters;
- bad Traders;
- simultaneous losers;
- correlation spikes;
- volatility changes;
- spread degradation;
- commission degradation;
- slippage degradation;
- margin compression;
- capital starvation;
- provider degradation;
- stale evidence;
- position reconciliation faults;
- reservation collisions.

## 13. Monte Carlo / path robustness

Mandatory path dimensions:

- trade ordering;
- loss clustering;
- capital path dependence;
- opportunity timing;
- capital-release timing.

The result must not depend only on one fortunate historical ordering.

## 14. Failure engineering

Mandatory failure scenarios:

- restart;
- duplicate event;
- duplicate reservation;
- partial settlement;
- ledger crash;
- mutation outcome unknown;
- reconciliation mismatch;
- stale snapshot;
- provider unavailable;
- capital-source mismatch;
- release before reconciliation;
- concurrent allocation.

Hard invariants:

```text
ZERO DOUBLE-SPEND
ZERO DUPLICATE AUTHORITY
ZERO SILENT SOURCE CREATION
ZERO RELEASE BEFORE RECONCILIATION
```

## 15. Final classification

Only after the six-month exam, baselines, ablation, stress, Monte Carlo,
failure engineering and fresh-OOS gates are complete:

```text
CERTIFIED
INTERVENTION_CONTINUE_ENGINEERING
REJECTED
```

CI GREEN alone cannot certify CIBO.

T01..T20 implementation alone cannot certify CIBO.

USD60 survival alone cannot certify CIBO.

## 16. Final reporting language

The final report must not say CIBO "hit the target", because no target exists.

The required interpretation is:

> This is the observed economic capability of CIBO under USD60 initial capital
> and a complete six-month independent evaluation.
