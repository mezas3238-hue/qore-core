# VT08 CRT PURE — R2-BM AUDUSD Passive Entry Economics

Identity: `VT08_CRT_PURE_R2BM_AUDUSD_PASSIVE_ENTRY_ECONOMICS_001`

Status: research adjudication only. No certification, runtime, DEMO, LIVE, production, merge, or capital authority.

## Frozen contract

- Market: AUDUSD.
- Window: 2011-09-21 through 2026-09-21.
- Population: rolling H4 + Model #1 + NEWEST_SUPERSEDES_CONFIRMATION_FIRST.
- R2-BK arms reused unchanged: NEXT_OPEN_CONTROL, SOURCE_OPEN, CONF_RANGE_MID, CONF_BODY_MID.
- Passive fill: observed M5 range touch, maximum 30 minutes.
- A structural stop touched before a passive fill invalidates the pending order.
- Same-M5 fill/stop ambiguity: STOP_FIRST.
- Stop: original source-candle structural extreme.
- Target: fixed 1.5R from actual fill.
- Expiry: C3 close.
- Management: BE_CLOSE_075 after a completed M15 close.
- Cost diagnostics: 0.02R and 0.05R per trade.

## Result

| Arm | Trades | Trades/y | PF | Total R | Mean R | DD R | PF @0.02R | Total @0.02R | PF @0.05R | Total @0.05R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NEXT_OPEN_CONTROL | 3727 | 248.47 | 1.04725 | +69.71 | +0.01870 | 61.11 | 0.99681 | -4.83 | 0.92623 | -116.64 |
| SOURCE_OPEN | 2502 | 166.80 | 1.08385 | +94.63 | +0.03782 | 30.36 | 1.03853 | +44.59 | 0.97464 | -30.47 |
| CONF_BODY_MID | 2429 | 161.93 | 1.05239 | +57.39 | +0.02363 | 53.92 | 1.00784 | +8.81 | 0.94511 | -64.06 |
| CONF_RANGE_MID | 2462 | 164.13 | 1.11891 | +128.53 | +0.05221 | 30.54 | 1.07150 | +79.29 | 1.00472 | +5.43 |

CONF_RANGE_MID also produced 11/15 positive annual windows and 12/14 positive rolling-2Y windows.

## Adjudication

Passive entry is a real causal economic lever for AUDUSD. CONF_RANGE_MID materially improves PF, Total-R, mean-R and drawdown versus next-open control and retains positive economics under 0.02R friction. It remains barely positive at 0.05R, so the margin is still too thin for certification.

Density is 164.13 trades/year, slightly below the current ~170/year research floor. Per Owner directive this is not grounds to reject the arm. The next step is density restoration using a previously demonstrated causal multi-hypothesis/rearm lever, without combining with BJ yet.

CONF_RANGE_MID is frozen only as the entry arm for the next density-restoration experiment. It is not a certified candidate.
