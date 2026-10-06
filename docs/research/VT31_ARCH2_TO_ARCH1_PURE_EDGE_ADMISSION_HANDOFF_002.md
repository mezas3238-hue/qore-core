# VT31 NAS100 — Architect 2 -> Architect 1 Pure-Edge Admission Handoff 002

**Owner:** Sergio Meza  
**Status:** CURRENT PURE-EDGE EVIDENCE / NO ENTRY-GATE CHANGE  
**Source branch:** `agent/vt31-edge-position-cert-b-001`  
**Entry authority:** Architect 1

## Sovereign boundary

This evidence is generated from the certifiable pure-market path:

- no 1.25R partial;
- no 3R breakeven;
- no fixed-R trailing;
- no R scratch;
- no sizing;
- no leverage;
- no compounding;
- no capital weighting;
- volume does not affect the market decision.

R below is post-trade evaluation only.

## Current pure-edge baseline after 0.05R research friction

| Fold | Trades | PF | Mean R | Total R | DD |
|---|---:|---:|---:|---:|---:|
| R5 | 54 | 1.9169 | +0.7488 | +40.44R | 12.60R |
| R6 | 37 | 2.3035 | +1.1097 | +41.06R | 12.74R |
| R8 | 33 | 2.6708 | +1.3291 | +43.86R | 11.66R |
| recent consumed 2Y | 48 | 1.0464 | +0.0406 | +1.95R | 13.83R |

The recent consumed 2Y block remains the hard certification blocker.

## Strongest current admission defect — expanded reference volatility

`reference_volatility_state == expanded`

Across the current admitted population:

- R5: 4 trades, 0 winners, -4.20R;
- R6: 4 trades, 0 winners, -4.20R;
- R8: 2 trades, 0 winners, -2.10R;
- recent consumed 2Y: 5 trades, 0 winners, -5.25R.

Total:

- **15 trades**
- **0 winners**
- **-15.75R**
- every trade ended at original structural invalidation.

All 15 are SHORT because the current historical non-compressed fallback admits
SHORT + H1 mixed states.

This is diagnostic evidence only. Architect 2 does not promote an entry ban.

## Reference-volatility comparison

### Compressed

- R5: 37 trades, PF 2.8018, +1.3294R/trade
- R6: 21 trades, PF 1.6175, +0.5557R/trade
- R8: 19 trades, PF 4.2144, +2.1316R/trade
- recent 2Y: 31 trades, PF 1.4735, +0.4009R/trade

Compressed is the only reference-volatility regime that remains positive in
all four current folds.

### Normal

- R5: PF 0.6386
- R6: PF 4.9987
- R8: PF 1.4726
- recent 2Y: PF 0.5020

Normal is not stable enough for a universal ban or universal admission.

### Expanded

PF = 0 in all four folds.

## Entry-family attribution on the current pure-market population

### Breaker

- R5: 29 trades, PF 3.0003
- R6: 25 trades, PF 2.3191
- R8: 26 trades, PF 3.7095
- recent 2Y: 34 trades, PF 1.6099

Breaker is positive in all four current folds.

### Fair Value Gap

- R5: 16 trades, PF 0.8578
- R6: 6 trades, PF 3.7206
- R8: 4 trades, PF 0
- recent 2Y: 9 trades, PF 0

FVG is unstable and is a major recent-period drag.

### Order Block

- R5: 9 trades, PF 0.5264
- R6: 6 trades, PF 1.1040
- R8: 3 trades, PF 0
- recent 2Y: 5 trades, PF 0

Order Block is also unstable and materially weak outside R6.

## Important interaction — Breaker + compressed

`entry_family == breaker AND reference_volatility_state == compressed`

- R5: 15 trades, PF 6.4825
- R6: 15 trades, PF 1.4749
- R8: 15 trades, PF 6.3215
- recent 2Y: 25 trades, PF 1.9388

This is not a promoted filter. It is a high-value causal region for Architect 1
to study because it preserves the methodology while avoiding the obvious
expanded-volatility defect.

## Non-Breaker + compressed remains weak

FVG + compressed:

- R5 PF 0.9358
- R6 PF 3.3138
- R8 PF 0
- recent PF 0

Order Block + compressed:

- R5 PF 0.7018
- R6 PF 0
- R8 PF 0
- recent PF 0

Therefore simply requiring compression is not sufficient for non-Breaker
entries. Entry translation / confirmation / family validity still needs work.

## Architect-1 priority

1. Investigate why the SHORT + H1-mixed fallback permits expanded reference
   volatility even though the state loses 15/15 on burned evidence.
2. Revalidate whether expanded reference volatility should remain executable.
3. Rebuild FVG and Order Block precision from market structure, confirmation,
   freshness and M1 entry location rather than risk scaling.
4. Preserve Breaker + compressed edge.
5. Do not use side bans: side behavior is fold-dependent.
6. Do not use volume/sizing/capital to repair any of these defects.
7. Freeze a causal entry candidate before any fresh holdout opens.

## Architect-2 boundary

Architect 2 continues post-entry market-native management research but will not
alter admission gates.

No merge, LIVE, real capital, production authorization or fresh holdout is
granted by this handoff.
