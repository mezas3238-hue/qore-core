# VT08 CRT PURE — FX HIGH-DENSITY ADVANCEMENT GATE 001

**Frozen:** before R2-AR / R2-AT outcome inspection  
**Scope:** AUDUSD and USDJPY high-density recovery research  
**Purpose:** advancement gate only — NOT final certification

## Required advancement conditions

A high-density FX research candidate may advance only if all of the following hold on
its causal/OOS characterization:

1. **Density**
   - >= 170 executed/retained trades per evaluated year on average.

2. **Economic edge**
   - Profit Factor >= 1.05.
   - Total-R > 0.

3. **Temporal breadth**
   - at least 60% of evaluated annual OOS windows have Total-R > 0.

4. **Drawdown**
   - max drawdown must not exceed the corresponding unfiltered/baseline OOS max drawdown.

5. **Density integrity**
   - causal entry-slot duplication must remain <= 1%.
   - opposite-direction same-clock collisions must be measured before advancement.

6. **Causality**
   - every suitability/target decision must be frozen from information available before
     the OOS trade/year being evaluated.
   - no current/future OOS outcome may participate in selection.

## Why these are not certification thresholds

These gates only determine whether the density-recovery architecture deserves the next
research stage.

They do NOT authorize:
- DEMO
- LIVE
- production
- real capital
- portfolio admission
- final CRT certification

Final certification still requires frozen candidate identity, genuinely reserved holdout,
stress, slippage, robustness, Monte Carlo/resampling, Risk review, CIBO review and
independent validation.

## Current density reference

The unfiltered rolling-H4 structural core already demonstrates approximately:

- AUDUSD: 244-251 trades/year across 2016-2026 windows.
- USDJPY: 242-267 trades/year across 2014-2026 windows.

Therefore the recovery problem is now edge discrimination under high retained density,
not opportunity generation.
