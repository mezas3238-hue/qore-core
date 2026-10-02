# CIBO T12/T13 Phase22 Causal Population Lineage V1

Status: **A1 PHASE22-NATIVE CAUSAL POPULATION CONTRACT / NO UTILITY CLAIM**

Identity:

`CIBO_T12_T13_PHASE22_CAUSAL_POPULATION_LINEAGE_V1`

## T12

The contract requires the historical replay population to preserve the same
canonical regime surface already frozen for Phase20:

- liquidity;
- volatility;
- correlation;
- provider condition;
- risk/margin/drawdown utilization;
- opportunity count;
- adverse-path state;
- evidence-staleness state.

All seven CIBO Trader lineages must be represented with causal capital/Risk
snapshots and provider-condition state.

T12 lineage never reads outcomes and cannot prove regime-adaptive utility.

## T13

T13 reconstructs reserve-pressure state strictly from outcomes whose
`observed_at` precedes the current decision.

For every replay decision it derives:

- settled-history availability;
- trailing settled-loss cluster;
- current and maximum settlement cash drawdown;
- candidate presence;
- decision-time stop-risk scarcity;
- drawdown/loss pressure intersecting scarce capital.

Outcomes that become known after a decision are excluded from that decision's
history.

## Scientific boundary

Lineage completion means the population is causally consumable. It does not
identify a reserve policy or prove economic utility.

Remaining scientific gates include:

```text
T12_CAUSAL_REGIME_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED
T13_RESERVE_POLICY_NOT_IDENTIFIED
T13_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED
```

No LIVE, real-capital, merge, PRE_EXAM, global-ledger or certification
authority is created.
