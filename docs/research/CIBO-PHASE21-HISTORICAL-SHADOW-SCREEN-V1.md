# CIBO Phase21 — Historical Shadow Empirical Screen V1

Status: **IMPLEMENTED / OWNER-AUTHORIZED SHADOW SUCCESSOR LANE**

The nine-month historical shadow closes the physical Phase20D population wait.
Phase21 does not re-use the TRAIN portion to judge the frozen TRAIN prior.
Instead it consumes only the causal post-TRAIN segment:

`2022-03-09T17:00Z -> 2022-06-29T09:00Z`.

That segment contains 332 opportunities across all seven Trader lineages and
still exceeds the original 80-decision / 200-outcome / 20-trading-day population
floor.

The policy screen is fixed by the already-frozen TRAIN priors. An opportunity
is structurally selected only when its pre-existing TRAIN expected structural R
is positive. Shadow outcomes cannot change that rule.

Hard gates:

- policy aggregate NCU delta must be positive and not below the all-opportunity
  baseline;
- policy settlement-path drawdown must not exceed baseline;
- policy NCU per risk-minute must strictly exceed baseline;
- 1,000 paired overlap-aware block-bootstrap paths must have policy median
  ending delta not below baseline and policy p95 drawdown not above baseline;
- no capital-capacity breach is allowed;
- all four temporal folds must retain population coverage and lineage breadth.

Per-fold positive PnL is retained as a diagnostic, not a final verdict, because
this lane is explicitly burned historical shadow evidence. The final fresh
verdict remains the sealed 2017H1 examination.

No historical USD/provider economics are claimed. Provider stress remains a
separate Phase21 prerequisite. No broker mutation or operational authority is
granted.
