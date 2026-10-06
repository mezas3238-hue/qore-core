# VT31 NAS100 — Residual Recent DD Forensics Findings 001

**Status:** CONSUMED-EVIDENCE FORENSICS CLOSED  
**Comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`  
**Workflow:** `37510639324` — SUCCESS  
**Evaluated head:** `d633b90874b0c3e41eeda90639b3a769f2ca3a65`

## Exact max-drawdown reconstruction

Comparator-007 recent consumed contains 33 trades.

The exact stressed maximum drawdown is:

`6.593383112613881844651075420R`

Peak:

- trade index: 16;
- signal: `2023-12-01T15:04:00+00:00`;
- equity after peak trade: `12.67306722001162779031480383R`.

Trough:

- trade index: 25;
- signal: `2024-03-01T15:05:00+00:00`.

The path contains 9 trades, indices 17 through 25.

The next trade after the trough is:

- `2024-03-04T15:07:00+00:00`;
- raw R: `+1.7224334600760456R`;
- stressed R: `+1.6724334600760456R`.

## Exact path

| Signal | Side | Raw R | Stressed R | DD after | Exit |
|---|---:|---:|---:|---:|---|
| 2023-12-12 15:16Z | SHORT | -1.0000 | -1.0500 | 1.0500R | structural-invalidation |
| 2023-12-14 15:08Z | LONG | -1.0000 | -1.0500 | 2.1000R | structural-invalidation |
| 2023-12-18 15:16Z | SHORT | -1.0000 | -1.0500 | 3.1500R | structural-invalidation |
| 2023-12-26 15:28Z | SHORT | -1.0000 | -1.0500 | 4.2000R | composite-pretarget-cognitive-exit |
| 2024-01-03 15:05Z | SHORT | +1.501587 | +1.451587 | 2.748413R | accepted-dol1-cognition-bank |
| 2024-01-29 15:26Z | LONG | -1.0000 | -1.0500 | 3.798413R | structural-invalidation |
| 2024-01-30 15:05Z | LONG | -1.0000 | -1.0500 | 4.848413R | structural-invalidation |
| 2024-02-08 15:07Z | SHORT | -1.0000 | -1.0500 | 5.898413R | structural-invalidation |
| 2024-03-01 15:05Z | SHORT | -0.644970 | -0.694970 | 6.593383R | composite-pretarget-cognitive-exit |

## Important finding: not a simple losing-streak problem

The maximum drawdown is not identical to the previously reported longest
five-loss streak.

It spans nine trades and includes one material winner of +1.451587R stressed.

Therefore, policies aimed only at "breaking the longest losing streak" are not
causally sufficient.

## Entry-family finding

All nine trades in the exact max-DD path are Breakers.

However, all eight winners in the full recent Comparator-007 sample are also
Breakers.

Therefore a blanket Breaker veto is directly contradicted by the matched-winner
control and remains forbidden as a serious candidate.

## State contrasts

Exact DD-path counts versus recent winners:

- prior-day bullish: 8/9 DD-path trades vs 4/8 winners;
- cash-open bullish: 7/9 DD-path trades vs 1/8 winners;
- H1 bullish: 2/9 DD-path trades vs 1/8 winners;
- H1 mixed: 7/9 DD-path trades vs 7/8 winners;
- H4 bearish: 7/9 DD-path trades vs 4/8 winners;
- SHORT: 6/9 DD-path trades vs 3/8 winners;
- compressed reference volatility: 6/9 DD-path trades vs 6/8 winners;
- FRESH_LT8M reclaim: 6/9 DD-path trades vs 8/8 winners.

This rejects several tempting broad filters:

- FRESH reclaim is not itself weak;
- compressed volatility is not itself weak;
- H1 mixed is not itself weak;
- Breaker is not itself weak.

## Narrow causal conflict selected for the next frontier

Two full-loss trades inside the exact DD path share:

- Breaker;
- SHORT;
- prior-day bullish;
- cash-open bullish;
- H1 bullish.

Those are:

- `2023-12-18T15:16:00+00:00`;
- `2024-02-08T15:07:00+00:00`.

This distinction is interpretable before entry as a SHORT position attempting to
fight simultaneous bullish prior-day context, bullish H1 context and bullish
cash-open state.

It requires no new numeric threshold.

It has been predeclared separately in:

`docs/research/VT31_ARCH2_BULLISH_H1_BREAKER_CONFLICT_ADMISSION_GATE_001.md`

and must prove itself unchanged across R5, R6, R8 and recent consumed before it
can become a development survivor.

## Governance

This findings document is observation-only.

No fresh holdout was opened.

No sizing, leverage, compounding, portfolio weighting, capital allocation or
CIBO rescue was used.

Comparator 007 remains the fixed research baseline until a later frontier
passes its predeclared cross-fold gate.
