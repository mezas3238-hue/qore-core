# VT31_NAS100 — CIBO Adaptation Model V1

Status: ACTIVE MODELING / CONSUMED EVIDENCE ONLY / FRESH 1Y HOLDOUT SEALED

This document reopens `VT31_NAS100_R1` modeling before candidate freeze. Silver Bullet remains the trading methodology. CIBO Atlas supplies consumed market-behavior evidence used to specialize how that methodology handles timing, entry, invalidation, target and lifecycle on NAS100.

CIBO is not an execution authority and does not replace Silver Bullet. POST_OUTCOME_RESEARCH labels are never legal runtime inputs. They are used only to formulate finite causal hypotheses that must survive leakage-free WFO on consumed evidence before any exact candidate is frozen.

## Immutable evidence binding

- CIBO Eight-Ledger run: `35175782935`
- CIBO Eight-Ledger artifact: `10478487667`
- CIBO Eight-Ledger digest: `sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192`
- CIBO source SHA: `6dc334723de5b7dca187e12b3a8ff531f4f1045e`
- NAS100 admitted market-days: `1591`
- NAS100 completed opposite-boundary reversal episodes: `547`
- NAS100 definitive trader roots: `208`

No fresh pre-2016 holdout evidence is opened by this model.

## 1. Timing — primary modeling axis

The consumed NAS100 Atlas shows a large mismatch between the old trader's signal timing and the market's final pre-departure reaction.

### Old trader timing

Across the 208 definitive NAS100 trader roots:

- signal time P25: `10:05 NY`
- signal time P50: `10:07 NY`
- signal time P75: `10:11 NY`

For the 68 roots that can be joined to a completed market reversal episode:

- 67/68 signals occurred before the final departure pivot;
- signal → departure P25: `53 min`
- signal → departure P50: `118 min`
- signal → departure P75: `220.75 min`

This does not prove that every entry should simply be delayed. It demonstrates that the existing implementation frequently commits long before the market finishes its reaction sequence.

### Independent market timing

Among 547 completed NAS100 reversal episodes:

- first breach in `10:00–10:14`: `399` episodes (`72.94%`);
- first breach in `10:15–10:29`: `88`;
- first breach in `10:30–10:44`: `42`;
- first breach in `10:45–10:59`: `18`.

The first breach is therefore usually early, but the final departure is not.

Final departure pivot:

- P25: `10:52 NY`
- P50: `11:44 NY`
- P75: `13:40 NY`

Only `153/547` completed reversals make their final departure inside the original 10:00–10:59 Silver Bullet hour. Of those, `104/153` (`67.97%`) occur in `10:30–10:59`.

The departure-to-opposite-boundary move is fast once departure occurs:

- P25: `4 min`
- P50: `5 min`
- P75: `8 min`

### Timing interpretation

The first modeling priority is therefore to separate:

1. **setup discovery** — the AM Silver Bullet breach/reversal thesis is formed inside the source window; from
2. **execution timing** — the trader may need to wait for a later causal reaction/reclaim before committing capital.

This is not permission to use the retrospective final-departure pivot live. The live rule must be based only on events observable at that moment.

## 2. Entry structure

The last observed structure before final departure in the 547 completed NAS100 reversal episodes was:

- local-liquidity sweep/reclaim: `431` (`78.79%`);
- reference-liquidity sweep/reclaim: `79` (`14.44%`);
- Fair Value Gap: `19`;
- Breaker: `13`;
- Order Block: `4`;
- none recognized: `1`.

This supports a causal research hypothesis: the source-valid early Silver Bullet thesis may need a **second-stage execution confirmation** instead of filling the earliest available R2.2 PD-array mechanically.

The second stage must be defined live as an observable sweep/reclaim plus source-valid displacement / PD-array retest. It may not ask whether that event later became the final departure pivot.

## 3. Initial stop / invalidation

NAS100 root-cause evidence does not support a universal wider stop.

- initial-stop roots: `87`; later source objective completed in `20` (`22.99%`);
- protected-stop roots: `68`; later source objective completed in `31` (`45.59%`).

The larger mismatch is therefore in premature protection/management, not simply the initial structural invalidation.

The stop research families are:

- source-methodological structural swing extreme, no arbitrary buffer;
- structural extreme belonging to the causal reclaim that authorizes a delayed entry.

The latter changes stop geometry because the entry structure changes, not because a fixed number of points is added retrospectively.

## 4. Target

The primary source destination remains the opposite frozen 09:00 reference boundary.

Across 1,591 admitted NAS100 market-days, that opposite boundary was reached by 16:00 on `547` days (`34.38%`). Conditional on reaching it, post-boundary extension was observed at least:

- `+0.25` reference width: `434/547` (`79.34%`);
- `+0.50` reference width: `320/547` (`58.50%`);
- `+1.00` reference width: `185/547` (`33.82%`);
- `+1.50` reference width: `106/547` (`19.38%`);
- `+2.00` reference width: `68/547` (`12.43%`).

For the first specialist model, the opposite 09:00 boundary remains the canonical structural target. A `+0.25 reference` runner is retained only as a finite research family to be evaluated by WFO; it is not yet a trader rule.

## 5. Predeclared finite research families

### Timing

- `T0_SOURCE_BASELINE`: existing 10:00–10:59 signal and earliest executable R2.2 entry.
- `T1_LATE_SOURCE_HOUR`: setup thesis can form from 10:00, but entry is permitted only 10:30–10:59 after a causal reclaim plus PD-array retest.
- `T2_DELAYED_EXECUTION`: setup thesis forms inside 10:00–10:59, while execution may extend through 11:29 only if the original thesis remains structurally valid and a new causal reclaim/confirmation appears.

### Entry

- `E0_R22`: current earliest actionable R2.2 confluence.
- `E1_RECLAIM_PDARRAY`: post-raid local/reference sweep-reclaim followed by a source-valid FVG / Breaker / Order Block retest.

### Initial stop

- `S0_SOURCE_SWING`: source-methodological structural swing extreme.
- `S1_RECLAIM_EXTREME`: structural extreme belonging to the reclaim that authorizes entry.

### Target

- `P0_OPPOSITE_09_BOUNDARY`: full exit at opposite frozen 09:00 boundary.
- `P1_BOUNDARY_PLUS_RUNNER`: realize at source boundary and research a predefined `+0.25 reference` runner.

### Management

- `M0_NO_M1_TRAIL`: remove R8 protected-swing M1 trailing.
- `M1_ONE_SHOT_BE`: at most one breakeven transition at a threshold chosen only through consumed WFO; no repeated protected-swing trailing.

## 6. Next mandatory gate

Do **not** freeze `VT31_NAS100_R1` yet.

The next execution step is a leakage-free WFO over consumed R5/R6/R8 evidence comparing only the finite families above. The selection criterion is temporal stability, economics, stress behavior and drawdown across blocks—not the best aggregate bucket.

After the model survives WFO:

1. materialize one exact NAS100 Silver Bullet contract;
2. run focused validation + Full QORE;
3. freeze exact SHA + fingerprint;
4. only then open the untouched one-year NAS100 holdout once.
