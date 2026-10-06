# VT31 NAS100 — Sovereign Trader Certification Standard 001

**Owner / CEO:** Sergio Meza  
**Status:** CANONICAL CURRENT STANDARD  
**Scope:** VT31 and trader certification under EDGE PURO

## 1. Observed maximum drawdown — HARD GATE

`MAX_DRAWDOWN_R <= 6R`

- 6.00R may pass this requirement.
- 6.01R or more fails certification.
- Historical 10R and 15R observed-drawdown certification thresholds are
  superseded.
- Monte Carlo p95 drawdown is a separate robustness metric and must not be
  confused with observed maximum drawdown.

## 2. Pure edge / equal-R

Certification must come from entry, exit and management edge.

Volume/exposure is neutral and decision-invariant during certification.

## 3. Capital rescue is forbidden

Certification may not be obtained, improved or rescued by:

- sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio allocation;
- capital weighting;
- exposure reduction to hide drawdown;
- CIBO capital rescue;
- any equivalent capital engineering.

Sovereign rule:

> R is allowed as trader logic. Sizing to obtain certification is forbidden.

## 4. R-management freedom

When justified by market intelligence, the trader may:

- move stop;
- move to breakeven;
- trail;
- take partials;
- close early;
- modify or extend target;
- let winners run;
- adapt management after entry.

These are edge decisions, not sizing.

## 5. Maximum intelligence is mandatory

Certification must use all applicable causal intelligence, including where
available:

- regime;
- structure;
- liquidity;
- volatility;
- trend/range;
- HTF/LTF context;
- timing/freshness;
- DOL;
- journey;
- momentum;
- post-entry reassessment;
- memory/cognitive context.

Available intelligence may be neutral, but it may not be silently bypassed to
make certification easier.

## 6. Profit factor

- OOS / era PF >= 1.50.
- Combined PF >= 1.70.
- Preferred combined PF >= 2.00.

## 7. Expectancy

- Must be > 0R/trade.
- Operational target approximately >= +0.15R/trade.

## 8. Payoff

- >= 1.20.
- Preferred approximately >= 1.50.

A high artificial win rate is not required when payoff carries the edge.

## 9. Sharpe

- >= 1.50.
- Preferred approximately >= 2.00.

The exact final formula/annualization convention must be frozen before the
fresh holdout.

## 10. Sortino

- >= 2.00.

The exact final convention must be frozen before the fresh holdout.

## 11. Monte Carlo

- Positive-terminal probability approximately >= 90%.
- Preferred >= 95%.
- Monte Carlo must not expose severe clustering or fragility.

The current VT31 harness also tracks MC p95 drawdown as a separate robustness
metric. It is not the observed-DD 6R gate.

## 12. OOS / temporal robustness

The trader must survive materially different:

- years;
- eras;
- regimes;
- folds/WFO;
- relevant temporal blocks.

One favorable window cannot certify the trader.

## 13. Cost/slippage stress

Under degraded costs the trader must retain PF > 1.0.

## 14. Winner preservation

When improving a version, approximately:

- >=80% of winner count must remain;
- >=90% of winner-R must remain.

Drawdown may not be cosmetically improved by destroying the trades that create
the edge.

## 15. Fresh holdout governance

1. Freeze the exact candidate first.
2. Freeze formulas, thresholds, memory fingerprints and evidence exclusions.
3. Open the fresh holdout once.
4. No retuning after opening.
5. If the candidate fails, it does not certify and that holdout becomes
   consumed.

## 16. Causality / anti-leakage

Forbidden:

- outcome-aware tuning;
- oracle variables;
- threshold changes after seeing final results;
- reuse of a consumed holdout as fresh;
- mixing evidence from different candidate versions to certify one candidate.

## Certification interpretation

A certified trader must therefore be:

> excellent by pure market edge, using maximum applicable intelligence, with
> real observed drawdown <=6R and scientific robustness.

Only after trader certification may CIBO apply sizing, leverage, compounding,
portfolio logic or other capital engineering.

## VT31 current state

VT31 is not certified.

No merge, LIVE, real-capital, production or fresh-holdout authority follows
from this standard alone.
