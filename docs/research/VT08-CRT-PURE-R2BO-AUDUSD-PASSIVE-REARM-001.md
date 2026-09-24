# VT08 CRT PURE — R2-BO AUDUSD Passive Rearm Density

Identity: `VT08_CRT_PURE_R2BO_AUDUSD_PASSIVE_REARM_DENSITY_001`

Status: density-restoration hypothesis insufficient. Research only. No certification, runtime, DEMO, LIVE, production, merge, or capital authority.

## Frozen contract

- Market: AUDUSD.
- Window: 2011-09-21 through 2026-09-21.
- Primary entry arm: R2-BM `CONF_RANGE_MID`.
- Primary competition: `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`.
- Maximum two passive attempts per parent.
- Maximum one realised trade per parent.
- Second attempt only after the first passive attempt resolves without fill.
- Second attempt requires a genuinely later source event.
- No fallback after invalid geometry or missing M5 evidence.
- Same source structural stop, fixed 1.5R target, C3 expiry and BE_CLOSE_075 as R2-BM.
- R2-BJ selector not combined.

## Result

### CAP1 control

- 2,462 trades.
- 164.13 trades/year.
- PF 1.11890640.
- +128.5346R.
- mean +0.052207R/trade.
- DD 30.5395R.
- 11/15 annual windows positive.
- 12/14 rolling-2Y windows positive.
- Cost 0.02R: PF 1.071503 / +79.2946R.
- Cost 0.05R: PF 1.004720 / +5.4346R.

### CAP2 causal terminal rearm

- 2,514 trades.
- 167.60 trades/year.
- PF 1.11673333.
- +128.3847R.
- mean +0.051068R/trade.
- DD 31.3532R.
- 10/15 annual windows positive.
- 12/14 rolling-2Y windows positive.
- Cost 0.02R: PF 1.069218 / +78.1047R.
- Cost 0.05R: PF 1.002291 / +2.6847R.

Density gain: +52 realised trades over 15 years.

## Adjudication

Terminal causal rearm increases density only marginally and slightly degrades PF, mean-R, drawdown and annual breadth. It does not solve the AUDUSD density/edge margin problem.

The hypothesis is frozen as insufficient and must not be tuned by extending arbitrary wait windows or adding retrospective fallback rules.

The next independent lever is the already-demonstrated R2-AI cap-2 multi-hypothesis capacity, tested with causal concurrent passive orders and OCO so that maximum realised trades remain one per parent.
