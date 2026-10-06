# VT31 NAS100 — Architect A Stable-Negative Admission Frontier Findings 001

**Owner:** Sergio Meza  
**Status:** CONSUMED-EVIDENCE DEVELOPMENT SURVIVORS / NOT PROMOTION EVIDENCE  
**Branch:** `agent/vt31-edge-entry-reasoning-a-001`  
**Workflow:** `37445911665` — SUCCESS  
**Head tested:** `9e20879a8a10da866df3d9f361d642ad840a8682`

## Purpose

Test only causal pre-entry classes that were negative across all four burned
folds in the preceding admitted-state attribution.

Predeclared hypotheses:

1. hard ABSTAIN when selected family is Order Block;
2. hard ABSTAIN when Order Block entry-evidence age is 0-2m;
3. hard ABSTAIN when 09:00 reference volatility is expanded;
4. combinations of the Order Block refinements with expanded volatility.

The position/target management policy is held out of this A-side test. Every
retained trade uses the same source structural-boundary exit.

No sizing, leverage, compounding, capital weighting, fold identity, future
outcome, fresh holdout, LIVE or real-capital authority is used.

Because the hypotheses were discovered on these same consumed folds, all
survivors remain development evidence only.

## Baseline — recent consumed

- trades: 48
- PF: `1.099959`
- mean: `+0.075073R`
- total: `+3.6035R`
- DD: `12.8341R`
- max losing streak: 10
- MC positive terminal: `54.79%`
- MC p95 DD: `28.30R`

## Expanded-reference ABSTAIN

Cross-fold:

- PF non-degrading: 4/4
- mean-R non-degrading: 4/4
- DD non-degrading: 4/4
- density >=75%: 4/4
- winner floors: PASS
- temporal half-years: not fully non-degrading

Recent consumed:

- trades: 43
- PF: **`1.208949`**
- mean: **`+0.159384R`**
- total: **`+6.8535R`**
- DD: `12.8341R`
- MC positive: **`61.77%`**
- MC p95 DD: **`25.68R`**
- removed: 5 trades, 5 losses, `-3.25R`
- winner preservation: **100% / 100%**

Historical candidate PF:

- R5: `2.6709`
- R6: `2.7418`
- R8: `2.6288`

## Full Order-Block ABSTAIN

Cross-fold:

- PF non-degrading: 4/4
- mean-R non-degrading: 4/4
- DD non-degrading: 4/4
- density >=75%: 4/4
- winner floors: PASS
- temporal half-years: not fully non-degrading

Recent consumed:

- trades: 43
- PF: **`1.287452`**
- mean: **`+0.205896R`**
- total: **`+8.8535R`**
- DD: **`10.7341R`**
- max losing streak: 7
- MC positive: **`67.37%`**
- MC p95 DD: **`22.46R`**
- removed: 5 trades, 5 losses, `-5.25R`
- winner preservation: **100% / 100%**

Historical candidate PF:

- R5: `3.1042`
- R6: `3.0006`
- R8: `2.9257`

The family-level rule is economically powerful, but its temporal non-degradation
is not perfect. Therefore family deletion is not yet the preferred refinement.

## Narrow Order-Block 0-2m ABSTAIN

This is the cleanest A-side robustness result.

Cross-fold:

- PF non-degrading: **4/4**
- mean-R non-degrading: **4/4**
- DD non-degrading: **4/4**
- density >=75%: **4/4**
- winner floors: **PASS**
- temporal half-years: **ALL NON-DEGRADING**

Recent consumed:

- trades: 45
- PF: **`1.205274`**
- mean: **`+0.150078R`**
- total: **`+6.7535R`**
- DD: **`10.7341R`**
- MC positive: `61.71%`
- MC p95 DD: `24.85R`
- removed: 3 trades, all full stressed losses, `-3.15R`
- winner preservation: **100% / 100%**

This is the only variant in this frontier that satisfies the predeclared
cross-fold economic, density, winner, and complete half-year non-degradation
criteria simultaneously.

## Full Order Block + expanded

This is the strongest pure-entry arithmetic but violates the density floor in
one fold.

Recent consumed:

- trades: 39
- PF: **`1.386487`**
- mean: **`+0.283423R`**
- total: **`+11.0535R`**
- DD: **`10.7341R`**
- MC positive: **`71.18%`**
- MC p95 DD: **`21.33R`**
- removed: 9 losses, `-7.45R`
- winner preservation: **100% / 100%**

Cross-fold PF / mean / DD are non-degrading 4/4, but density passes only 3/4.
Therefore it is not a development survivor under the predeclared density gate.

## Narrow Order Block 0-2m + expanded

This combination preserves density in all four folds.

Cross-fold:

- PF non-degrading: 4/4
- mean-R non-degrading: 4/4
- DD non-degrading: 4/4
- density >=75%: 4/4
- winner floors: PASS
- temporal half-years: not fully non-degrading

Recent consumed:

- trades: 41
- PF: **`1.291645`**
- mean: **`+0.218378R`**
- total: **`+8.9535R`**
- DD: **`10.7341R`**
- MC positive: **`66.49%`**
- MC p95 DD: **`23.28R`**
- removed: 7 losses, `-5.35R`
- winner preservation: **100% / 100%**

## Decision

The preferred **robustness-first** Order-Block hypothesis is:

`ORDER_BLOCK + ENTRY_EVIDENCE_AGE_0_2M -> ABSTAIN`

It transfers 4/4 without temporal degradation and preserves all winners.

The expanded-reference anomaly remains a separate strong development survivor,
but needs better temporal/contextual understanding before promotion.

The family-level Order-Block veto is retained only as a research upper bound:
it produces more edge but is coarser than necessary.

## Required next test

Compose all A-side hypotheses with the fixed B-side research comparator:

`VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001`

on the current maximum-cognition B branch, where M15 context is present.

Do not modify H3, W5, DOL2 or PS2 while measuring admission changes.

The resulting A+B replay must report:

- R5 / R6 / R8 / recent consumed;
- PF / mean-R / total-R;
- observed DD / losing streak;
- Monte Carlo;
- temporal blocks;
- retained density;
- winner preservation;
- M15 and other causal context for removed states.

Fresh holdout remains sealed.

No candidate freeze or certification is authorized by this A-side finding.
