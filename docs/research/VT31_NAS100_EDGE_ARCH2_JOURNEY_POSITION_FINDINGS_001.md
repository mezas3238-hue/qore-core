# VT31 NAS100 — Arquitecto 2 — Edge / Journey / Position Findings 001

**Status:** ACTIVE RESEARCH / CONSUMED EVIDENCE ONLY / NO HOLDOUT OPENED  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Scope:** VT31 NAS100 post-entry intelligence and edge-only certification  
**Authority:** GitHub is source of truth; VPS is test bank only.

## 1. Governance

This research does not authorize LIVE, real capital, production, merge, funded
execution, sizing, leverage, compounding, portfolio weighting, risk scaling, or
a new holdout.

VT31 edge is measured from equal-weight structural R outcomes. Provider volume
compatibility begins at `0.01` when the provider supports that minimum, but
volume is not an input to trader-edge metrics.

Silver Bullet methodology remains frozen.

## 2. Edge-only certification repair

The old R5 certification identity is not authoritative for the new VT31 exam
because its economics include differentiated capital requests, monthly capital
budgets, and a global risk scalar.

Architect 2 added a separate development authority:

- `src/qore/infrastructure/traders/vt31_nas100_edge_certification.py`
- `scripts/vt31_nas100_edge_certification_v1.py`

The new metric plane requires structural `r_multiple` and derives
`normalized_trade_r` on an equal-1R basis. Capital fields such as
`capital_weighted_net_r`, `requested_risk_r`, volume, leverage, portfolio
weight, and risk scalars are explicitly non-authoritative.

The current identity is development-only:

`VT31_NAS100_EDGE_CERT_V1_DEV`

It cannot claim candidate freeze, certification, LIVE, real-capital, or
production authority.

### Risk-adjusted metric binding

The repository's existing Sharpe/Sortino research contracts are explicitly
same-period and non-annualized. The Owner certification thresholds
Sharpe >= 1.50 and Sortino >= 2.00 therefore cannot be silently applied to a
different metric convention.

Current development reports retain descriptive trade-period ratios, but the
final Sharpe/Sortino gates remain intentionally unbound until the exact
certification return series, period, risk-free/MAR convention, and any legal
annualization method are frozen.

## 3. Immutable consumed-evidence provenance

CIBO Intelligence Bridge:

- workflow run: `35288950361`
- source SHA: `279335bf61b131d3b028e41bc6357ece418f696f`

Bridge artifacts:

| Partition | Artifact | SHA256 |
|---|---:|---|
| R8 | 10525486699 | a9b5693095b15f6bd9067d935c1472081b1a61e56ba2d5d58514d645a5487b99 |
| R6 | 10525421953 | 6bc95bc5f6a836c373b33d7ab6dba05f2b6c5caf89e89fdb08351529a33b0aa0 |
| R5 | 10525736274 | 26716fb1e2546e0176bd12170a13d4a5ea06bb1f44f1d30ef4028040af020fe5 |

Original market-evidence artifacts:

| Partition | Artifact | SHA256 |
|---|---:|---|
| R8 | 10402199719 | 9f5df4eba1882cb498b4e3657176f34a7c27083f3ac1af7856ebddf01447f34d |
| R6 | 10389112524 | 9b0f3a05dc76b5dd83e5e3610266484bee1b79595dbbaacdff1d799115ad58b9 |
| R5 | 10380044761 | 828335b99cd51c663e3f0f095df5137e881da3d7e8da741da8ca116a0400edf8 |

The VPS lab reproduced journey forensics directly from those consumed NAS100 M1
market-evidence files. No new holdout was opened.

## 4. Cross-partition NY journey evidence

Exact journey script:

`scripts/vt31_nas100_ny_delivery_journey_forensics_v1.py`

| Metric | R8 | R6 | R5 |
|---|---:|---:|---:|
| labeled journeys | 228 | 279 | 316 |
| FAILED_BEFORE_1R | 95 | 88 | 115 |
| GIVEBACK_AFTER_1R | 72 | 114 | 109 |
| RUNNER_3R_PLUS (3R to <5R) | 19 | 26 | 36 |
| EXTENDED_RUNNER_5R_PLUS | 40 | 48 | 55 |
| >=3R runner total | 59 | 74 | 91 |
| 1R reached | 58.33% | 68.46% | 63.61% |
| median time to 1R | 0m | 0m | 0m |
| 3R reached | 25.88% | 26.52% | 28.80% |
| 5R reached | 17.54% | 17.20% | 17.41% |
| DOL1 boundary reached | 12.72% | 12.90% | 12.97% |

Giveback-after-1R rate:

- R8: 31.58%
- R6: 40.86%
- R5: 34.49%

The >=5R tail is unusually stable across the three consumed partitions:
approximately 17.2%-17.5%.

This simultaneously confirms:

1. a material post-1R giveback problem exists;
2. a large-runner tail also exists and must be preserved;
3. generic aggressive protection is unsafe until winner destruction is measured.

## 5. State evidence at the first 1R milestone

Median favorable-close-rate state at the 1R milestone:

| Journey class | R8 | R6 | R5 |
|---|---:|---:|---:|
| GIVEBACK_AFTER_1R | 0.000 | 0.000 | 0.333 |
| RUNNER_3R_PLUS | 0.500 | 0.733 | 0.450 |
| EXTENDED_RUNNER_5R_PLUS | 0.450 | 0.667 | 0.600 |

Using the weaker of the two runner classes, the runner-minus-giveback
separation remains positive in every partition:

- R8: +0.450
- R6: +0.667
- R5: +0.117

Therefore favorable close persistence is supported as a causal research
mechanism.

By contrast:

- overlap around the first 1R touch is not a stable discriminator;
- path efficiency at the first 1R touch is not monotonic across partitions;
- raw 1R touch alone is too early to justify immediate generic protection.

Cross-partition authority:

`scripts/vt31_nas100_journey_cross_partition_adjudication_v1.py`

Current adjudication:

- giveback problem: `CONFIRMED_CROSS_PARTITION`
- large runner tail: `CONFIRMED_CROSS_PARTITION`
- favorable close persistence: `SUPPORTED_CAUSAL_RESEARCH_HYPOTHESIS`
- overlap at 1R: `REQUIRES_MORE_EVIDENCE`
- path efficiency at 1R: `NOT_STABLE_AS_SOLE_DISCRIMINATOR`
- immediate generic protection at 1R: `NOT_JUSTIFIED_FOR_PROMOTION`

No threshold and no runtime management policy have been promoted.

## 6. Validation state

On isolated VPS checkout `C:\QORE_VT31_ARCH2_LAB`, exact branch HEAD
`db85fced2418b817f22bf52c4fc256d60557de41` produced:

- 21/21 targeted tests PASS;
- cross-partition adjudication PASS;
- no runtime policy promoted.

Static analysis then found six hygiene-only findings (unused/import-order
issues). These were repaired in subsequent GitHub commits before the next
research stage.

## 7. Next predeclared experiment

The next experiment is **post-1R closed-bar persistence**, not an optimized
stop level.

Predeclared horizons:

- 2 closed M1 bars after the first unambiguous 1R touch;
- 3 closed M1 bars;
- 5 closed M1 bars.

At each horizon, use only information observable by that bar close:

- current close R;
- fraction of post-1R closes that remain >=1R;
- fraction remaining positive;
- favorable candle-close persistence;
- overlap;
- path efficiency;
- favorable excursion achieved by that time;
- giveback from causal peak;
- available structural protection state.

Future 3R/5R delivery and later invalidation are research labels only.

The experiment must:

1. censor ambiguous same-bar 1R/stop paths;
2. require the original thesis to remain alive through the observation close;
3. use identical state semantics in R8/R6/R5;
4. report cross-partition behavior;
5. select no best horizon after reading results;
6. promote no runtime threshold;
7. open no holdout.

Only if a causal state is stable across partitions should Architect 2 run
structural stop counterfactuals and winner-preservation tests.

## 8. Current conclusion

VT31 does not currently need a blunt tighter stop.

It needs a NAS100-native distinction between:

- early 1R touch that is followed by genuine delivery persistence; and
- early 1R touch whose post-touch structure loses directional persistence and
  becomes a giveback journey.

That distinction must be proven before replacing
`RESEARCH_UNCALIBRATED_POLICY`.
