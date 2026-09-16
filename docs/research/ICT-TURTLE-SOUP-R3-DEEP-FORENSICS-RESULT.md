# ICT Turtle Soup R3 — Exhaustive Winner/Loser Deep Forensics Result

Date: 2026-09-15
Parent identity: `ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD`
Parent authoritative run: `35038587031`
Parent artifact: `10424038795`
Parent executed HEAD: `9ddb92dfa9090b39fa43d7b7dff298f1d20d736c`
Tracks: #584
PR: #586

## Immutable parent reconciliation

The forensic analysis consumed the exact parent R3 outputs and the same seven retained read-only M5 evidence artifacts used by the parent replay.

Parent hashes verified before analysis:

- report SHA-256: `62bcd9b71623da31d8e63b707757723ad2f7fc6ea3229aa85eb4805bc7858a42`
- trades SHA-256: `0c1fa264a36375ebce5818fb9135a7aae9c0ca54135ae1d797023aa76f0bfb25`

Exact forensic trade reconciliation:

- parent trades: **1,843**
- primary-net winners: **911**
- primary-net losers: **932**
- primary-net flats: **0**
- gross winners / losers / flats: **972 / 868 / 3**

No fresh OOS was opened. No parent trade was changed or removed.

## Forensic tools executed

The analysis reconstructed every trade against original M5 evidence and produced:

- winner vs loser feature matrix;
- MFE / MAE path reconstruction;
- stop-path pre-stop excursion and post-stop recovery;
- target-path post-target continuation / Draw-on-Liquidity diagnostics;
- C3 time-exit diagnostics;
- C1 / C2 / CISD / protected-swing geometry;
- H4 range-regime context;
- winner-vs-loser quantiles and Cliff's delta effect sizes;
- fixed decile diagnostics for all numeric pre-entry features;
- symbol / side / session / NY-hour / quarter / half-year / year breadth;
- leave-one-symbol-out reconciliation;
- rolling 90-day and 180-day stability;
- simultaneous H4-entry cross-pair cluster analysis;
- deepest drawdown composition;
- longest losing-streak composition;
- positive-gain and negative-loss concentration;
- exact gross-to-primary friction attribution.

## 1. The dominant economic problem: near-zero gross edge plus friction

Parent gross economics were already almost exactly break-even:

- gross total: **-0.6138196072R**
- gross mean: **-0.0003330546R/trade**
- gross PF: **0.99907105**

The frozen primary friction subtracts exactly **92.15R** across 1,843 trades, producing:

- primary total: **-92.7638196072R**
- primary mean: **-0.0503330546R/trade**
- primary PF: **0.86855213**

Additionally, **61 gross-positive trades** become non-positive after 0.05R friction.

### Adjudication

`FRICTION_DOMINATES_NEAR_BREAK_EVEN_GROSS_EDGE` — **STRONGLY SUPPORTED**.

Friction is not the origin of the gross weakness, but it converts an essentially zero-expectancy gross model into a clearly negative net model.

## 2. Target / Draw-on-Liquidity mismatch is strongly supported

The R3 frozen target was the opposite C1 extreme. Among the **636 target exits**:

- mean target: **+0.7463R**
- median target: **+0.5045R**
- 316 / 636 targets were below **0.50R**
- 496 / 636 targets were below **1.00R**

After the target was already touched, using only subsequent M5 evidence:

- median additional favorable movement within the rest of the same C3: **+0.5093R**
- median additional favorable movement in the next H4: **+0.5388R**
- median additional favorable movement through the next 8 hours: **+0.8824R**
- mean additional favorable movement through the next 8 hours: **+1.4639R**

Continuation shares through the next 8h:

- target +0.25R: **82.39%**
- target +0.50R: **67.92%**
- target +1.00R: **47.01%**

This is trajectory evidence, not an executable counterfactual: it does not prove that simply moving the target would improve P&L, because post-target path ordering and later invalidation would need a separately frozen lifecycle.

### Adjudication

`TARGET_DOL_TOO_LOCAL_OR_TRUNCATED` — **STRONGLY SUPPORTED**.

The local opposite-C1 target frequently terminates trades while the same directional repricing continues materially farther. R4 should source-bind the higher-timeframe Draw on Liquidity before economics instead of extending the R3 target post hoc.

## 3. Protected-swing invalidation / retest mismatch exists, but widening the stop is not justified

There were **558 stop-family exits**.

Before the stop:

- median conservative pre-stop MFE: **+0.3085R**
- mean conservative pre-stop MFE: **+0.5024R**
- reached +0.25R before stop: **55.56%**
- reached +0.50R before stop: **35.30%**
- reached +1.00R before stop: **14.87%**

After the stop:

- recovered original entry during the remainder of the same C3: **46.77%**
- recovered original entry within the next 8h: **66.13%**
- subsequently reached the original R3 target within the next 8h: **26.88%**
- median favorable recovery through the next 8h: **+0.7070R** from the original entry

The majority of stopped trades do **not** subsequently reach the original target, so these data do not authorize a wider stop.

### Adjudication

`PROTECTED_SWING_INVALIDATION_MISMATCH` — **SUPPORTED, NOT SUFFICIENT AS A SOLE CAUSE**.

Normal deep retests are clearly present, but a large stopped cohort remains structurally weak even after recovery.

## 4. CISD often creates an initial reaction without persistent delivery

The stopped cohort frequently moves favorably before failing, and the time-exit cohort also displays substantial two-sided excursion:

Time exits: **649 trades**

- gross mean at C3 close: **+0.1276R**
- gross PF: **1.8065**
- median MFE before C3 close: **+0.4294R**
- median MAE before C3 close: **0.4760R**
- next-H4 close from original entry: median **-0.0072R**, mean **+0.0381R**

The next H4 is therefore approximately neutral in aggregate; merely extending every C3 lifecycle is not supported.

### Adjudication

`CISD_CONFIRMATION_LACKS_PERSISTENCE` — **SUPPORTED**.

CISD often identifies a real initial reversal response, but R3 does not adequately distinguish persistent repricing from temporary reaction/retest.

## 5. C2 reversal quality contains a meaningful winner/loser signal

Among strictly pre-entry features, the clearest structural separation is the depth/quality of the C2 reversal closure rather than wick size alone.

Primary winners vs losers:

- C2 reclaim depth median: **0.4510 vs 0.3025 C1 ranges**
- Cliff's delta: **+0.2641**
- C2 directional close-location Cliff's delta: **+0.1567**
- C2 range / C1 range Cliff's delta: **+0.1784**
- C2 body-fraction Cliff's delta: **+0.0947**
- C2 rejection-wick fraction Cliff's delta: only **+0.0476**

This means stronger penetration back into the prior range is more discriminative than an isolated large rejection wick.

No threshold is selected from these consumed outcomes.

### Adjudication

`C2_REJECTION_QUALITY_INSUFFICIENT` — **SUPPORTED**.

R3's binary `sweep + close back through C1 level` condition appears too coarse relative to source concepts of reversal closure / delivery quality. The exact R4 mechanic must come from ICT/TTrades source adjudication, not from these deciles.

## 6. Projected-R geometry exposes the C1-target/C3-lifecycle conflict

Primary winners had a **lower**, not higher, projected-R distribution:

- winner median projected R: **0.7855R**
- loser median projected R: **1.3937R**
- Cliff's delta: **-0.2871**

The highest projected-R decile was materially weak after friction. This does **not** authorize a maximum-R filter. It shows that the R3 combination of local C1 target, protected-swing risk and one-C3 lifecycle creates inconsistent payoff geometry: farther local targets are frequently not delivered within the frozen lifecycle.

### Adjudication

This finding reinforces `TARGET_DOL_TOO_LOCAL_OR_TRUNCATED` plus lifecycle/context mismatch; it does not justify an R:R threshold.

## 7. Relevant-swing shallowness is not resolved by R3 outcomes

The R3 three-H4 relevant-swing separation metric barely distinguishes winners from losers:

- winner median separation: **0.4274 C1 ranges**
- loser median separation: **0.4473 C1 ranges**
- Cliff's delta: **-0.0103**

C1 range versus previous 3/6/12 H4 median ranges also shows only small effects.

### Adjudication

`RELEVANT_SWING_CONTEXT_TOO_SHALLOW` — **SOURCE-PLAUSIBLE BUT EMPIRICALLY UNDERDETERMINED HERE**.

The current simple three-H4 proxy is not a useful winner/loser discriminator. This does not validate it as the correct ICT relevant-swing hierarchy; it means the correct hierarchy must be source-defined rather than selected from outcome separation.

## 8. C3-open entry timing is not the dominant observed separator

Timing differences are weak:

- CISD-to-entry median: winners **105m**, losers **120m**
- Cliff's delta: **-0.0571**
- sweep-to-entry Cliff's delta: **-0.0257**
- sweep-to-CISD medians: both **75m**

### Adjudication

`ENTRY_TIMING_C3_OPEN_MISMATCH` — **UNDERDETERMINED / WEAKLY SUPPORTED BY CURRENT FEATURE SEPARATION**.

A different source-supported execution family may still matter, but R3 outcomes do not justify changing entry timing by themselves.

## 9. Market / side / temporal nonstationarity is real, but not reducible to one retrospective filter

By side:

- LONG: 863 trades, **-13.4271R**, PF **0.9556**
- SHORT: 980 trades, **-79.3368R**, PF **0.8033**

By symbol, only GBPJPY is positive after primary friction; all other symbols are negative. Nevertheless every leave-one-symbol-out portfolio remains negative.

By session:

- Asia: **-37.7508R**, PF 0.7865
- London: **+3.8351R**, PF 1.0130
- New York: **-19.5305R**, PF 0.8484
- Other: **-39.3177R**, PF 0.6248

London is diagnostic only and cannot be selected after the fact.

Quarterly stability is mixed: 2021-Q2 is strongly positive (+24.53R), while most other quarters are negative; 2022-Q1 is particularly weak (-37.25R). Rolling 90d/180d windows repeatedly cross above and below zero.

### Adjudication

`MARKET_SIDE_OR_SESSION_NONSTATIONARITY` — **SUPPORTED**.

The missing context is broader than one pair or one session. A source-bound higher-timeframe bias / POI / DOL model is required rather than pruning losing subgroups.

## 10. Cross-pair clustering is mixed, not a single root cause

There were **1,170 distinct entry timestamps**, including **427 multi-pair clusters**.

Cluster-size behavior is non-monotonic:

- size 1: negative
- size 2: negative
- size 3: positive
- size 4: negative
- size 5: positive
- size 6: negative

### Adjudication

`CROSS_PAIR_CLUSTER_REGIME_FAILURE` — **MIXED / PARTIALLY SUPPORTED**.

Common macro regimes matter, but simultaneous-entry count alone is not a sufficient causal discriminator.

## 11. Right-tail / outlier dependence is not the problem

Primary positive-gain concentration:

- top 1 winner: **1.58%** of positive gains
- top 10 winners: **9.36%**

Primary negative-loss concentration:

- top 1 loss: **0.16%** of losses
- top 10 losses: **1.50%**

### Adjudication

`RIGHT_TAIL_OR_OUTLIER_DEPENDENCE` — **NOT SUPPORTED AS A PRIMARY FAILURE**.

R3's weakness is broad and structural rather than being caused by a handful of extreme observations.

## Drawdown and losing-streak anatomy

The maximum primary drawdown is **111.2417R** and spans almost the entire sample (1,788 of 1,843 chronological trades), confirming persistent negative drift rather than one isolated crash regime.

The longest primary losing streak is **10 trades / -10.50R**, spread across six symbols, both directions and multiple sessions. It is not attributable to one instrument.

## Final root-cause order

### Strongest supported causes

1. **`TARGET_DOL_TOO_LOCAL_OR_TRUNCATED` — STRONGLY SUPPORTED**
2. **`FRICTION_DOMINATES_NEAR_BREAK_EVEN_GROSS_EDGE` — STRONGLY SUPPORTED**
3. **`C2_REJECTION_QUALITY_INSUFFICIENT` — SUPPORTED**
4. **`CISD_CONFIRMATION_LACKS_PERSISTENCE` — SUPPORTED**
5. **`PROTECTED_SWING_INVALIDATION_MISMATCH` — SUPPORTED, NOT SOLE CAUSE**
6. **`MARKET_SIDE_OR_SESSION_NONSTATIONARITY` — SUPPORTED**

### Not established as primary causes

7. **`CROSS_PAIR_CLUSTER_REGIME_FAILURE` — MIXED**
8. **`RELEVANT_SWING_CONTEXT_TOO_SHALLOW` — UNDERDETERMINED FROM R3 OUTCOMES**
9. **`ENTRY_TIMING_C3_OPEN_MISMATCH` — UNDERDETERMINED / WEAK CURRENT SEPARATION**
10. **`RIGHT_TAIL_OR_OUTLIER_DEPENDENCE` — NOT SUPPORTED**

## R4 implication

The forensic evidence does **not** authorize:

- wider stops;
- a minimum/maximum projected-R filter;
- London-only operation;
- LONG-only operation;
- GBPJPY-only operation;
- a C2 reclaim-depth threshold selected from deciles;
- a later time exit;
- target extension selected from post-target MFE.

The correct next step is source-first R4 formalization of:

`daily/HTF narrative -> valid relevant swing / POI -> qualified C2 reversal closure -> persistent lower-timeframe confirmation / protected swing -> source-supported entry family -> higher-timeframe Draw on Liquidity`.

Only after that contract is frozen may economics be replayed again under a new identity.

## Forensic output hashes

- `forensics-report.json`: `3e6743d0d5e3eaa36f8f32c74d9830dafc7e9a4dc9902e5f577c0b2fa41b1a4c`
- `trade-feature-ledger.json`: `a9a96bfd03e818dee44e99e304773d8568c77d246bb9ed910877222372bf7d24`
- `winners.json`: `d2c0002f70d5b040b89f178f17d4d3c325237e1a3ff16f7ced6a92e975dab819`
- `losers.json`: `3a8ae874e1fad65a93630b421bf826c93bde12d67dc3f00f46f2e061dea0a41c`
- `stopped-trades.json`: `1e80c5716f969e2517bffe9a0d2c25ff235fad626ba7668a82eb4abf21413ed5`
- `target-trades.json`: `cbaedbcf9bcf4c652937bc63b1a145932aea85badf15c868a723dde3e19db990`
- `time-exit-trades.json`: `9c5417f310da6366cef6f2e3ecc95062ffc6d04ad056154279f38b927b50e050`
- `feature-deciles.json`: `c50a0c59f94cba5b5d37519a19203eaa1f87753e10445a728255764d8edee6fd`
- `entry-clusters.json`: `34e2618d208f0abb54e4b696823e5cb49bbb5e98f4281236a61633b6227e8f79`

Governance remains:

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
