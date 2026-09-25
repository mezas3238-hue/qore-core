# VT08 CRT PURE — R2-BU USDJPY Overlap Expected-R WFO

Identity: `VT08_CRT_PURE_R2BU_USDJPY_OVERLAP_EXPECTED_R_WF_001`

Status: completed research WFO. Signal present, economics insufficient. No promotion.

## Contract

- USDJPY only.
- 2014-09-21 through 2026-09-21 source population.
- Prior 4Y -> next 1Y OOS.
- 20% training-score abstention threshold.
- Empirical-Bayes shrinkage.
- New dimension: `confirmation_source_overlap`, coarsened to:
  - `CONF_OVERLAP_LT_050`
  - `CONF_OVERLAP_GE_050`
- No AUDUSD state/economic transfer.

## Combined OOS baseline

- 1,968 trades.
- PF 0.88942.
- -97.55R.
- mean -0.04957R/trade.
- DD 107.53R.

## Heads

### REF_DELAY_DIRECTION_CONTROL

- 1,429 trades.
- 178.63 trades/year.
- PF 0.89284.
- -67.02R.
- mean -0.04690R/trade.
- DD 79.02R.
- 25% positive OOS years.
- cost 0.02R: PF 0.85102 / -95.60R.

### REF_DELAY_DIRECTION_OVERLAP

- 1,479 trades.
- 184.88 trades/year.
- PF 0.88054.
- -76.49R.
- mean -0.05171R/trade.
- DD 83.25R.
- 25% positive OOS years.
- cost 0.02R: PF 0.83859 / -106.07R.

This interaction does not improve the control.

### REF_DELAY_OVERLAP

- 1,331 trades.
- 166.38 trades/year.
- PF 0.95745.
- -23.09R.
- mean -0.01735R/trade.
- DD 38.19R.
- 50% positive OOS years.
- cost 0.02R: PF 0.91082 / -49.71R.
- cost 0.05R: PF 0.84545 / -89.64R.

## Adjudication

Confirmation/source overlap contains useful causal information for USDJPY when paired with REF+DELAY. It materially improves PF, Total-R, mean-R, drawdown and temporal breadth versus both baseline and the REF_DELAY_DIRECTION control.

It is still negative expectancy, fails friction, and falls slightly below the ~170 trades/year research floor. It is therefore not a candidate.

A methodological issue is visible in the fixed 20% abstention implementation: tied cell scores can cause actual training rejection materially above 20%. The next experiment may test a tie-safe threshold that never rejects the entire threshold tie group when doing so would exceed the predeclared abstention fraction. This is an execution of the same hypothesis, not a new economic state search.

Governance remains research-only.
