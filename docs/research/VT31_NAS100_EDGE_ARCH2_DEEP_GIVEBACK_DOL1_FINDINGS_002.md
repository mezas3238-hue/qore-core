# VT31 NAS100 — Architect B Deep Giveback + DOL1 Findings 002

**Status:** CONSUMED-EVIDENCE RESEARCH / EDGE-ONLY / NO POLICY PROMOTION  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Scope:** post-entry position intelligence, giveback control, DOL1 extension  
**Authority:** GitHub is source of truth. VPS/lab is test bank only.

## 1. Governance

This research:

- changes no trade admission;
- changes no entry gate;
- changes no Silver Bullet source identity;
- widens no initial stop;
- uses no sizing, leverage, compounding, portfolio weighting or capital scalar;
- uses no absolute lot/volume as an edge variable;
- opens no new holdout;
- authorizes no LIVE, real capital, funded execution or production;
- makes no merge.

All economics are expressed as equal normalized structural R with 0.05R
research friction.

## 2. Why generic trailing remains rejected

The consumed M1 journey study established two facts simultaneously:

1. post-1R giveback is material;
2. the large-runner tail is also material and stable.

A generic stop move after 1R is therefore unsafe. The next question was not
"how tightly can VT31 trail?" but:

> Can VT31 detect a journey that has already delivered meaningful favorable
> excursion and has subsequently collapsed back near entry, then use a newly
> confirmed structural swing to reduce further giveback without cutting the
> original winners?

## 3. Deep Giveback Rescue frontier

Research implementation:

`scripts/vt31_nas100_deep_giveback_rescue_frontier_v1.py`

The mechanism uses only state observable at a closed M1 bar:

- observed intrabar MFE >= 1.50R;
- peak-close giveback >= 1.00R;
- recent 5-bar path efficiency <= 0.10;
- current close tested on the predeclared frontier:
  - <= +0.25R;
  - <= +0.50R;
  - <= +0.75R;
  - <= +1.00R;
- a confirmed M1 protective swing must exist;
- the swing becomes actionable only on the next M1 bar;
- the stop may only improve, never widen;
- DOL1 remains the opposite frozen 09:00 reference boundary;
- no partial exit is required.

The most conservative member, `CURRENT_CLOSE_MAX_0_25`, is treated only as a
**research witness**. It is not a promoted runtime policy.

## 4. Exact cross-partition results for the 0.25R witness

### R8

Baseline:

- trades: 31
- PF: 1.2061504656
- mean: +0.1885279258R
- max DD: 15.7500R

DGR <= +0.25R:

- PF: 1.2177842065
- mean: +0.1972644849R
- max DD: 15.4791666667R
- armed trades: 1
- winner-count preservation: 100%
- winner-R preservation: 100%

No half-year block degraded.

### R6

Baseline:

- trades: 56
- PF: 0.4769230769
- mean: -0.5100000000R
- max DD: 28.5600R

DGR <= +0.25R:

- PF: 0.4942965487
- mean: -0.4757308249R
- max DD: 26.6409261916R
- armed trades: 5
- winner-count preservation: 100%
- winner-R preservation: 100%

Every half-year is non-degrading.

R6 remains economically weak. Architect B does **not** interpret this management
improvement as a repair of the admission problem. The negative admitted
population remains Architect 1 territory.

### R5

Baseline:

- trades: 71
- PF: 1.8130531756
- mean: +0.6973934985R
- max DD: 15.7630434783R

DGR <= +0.25R:

- PF: 1.9870322248
- mean: +0.7726863709R
- max DD: 15.7630434783R
- armed trades: 9
- winner-count preservation: 100%
- winner-R preservation: 100%

Every half-year is non-degrading.

## 5. Temporal deltas — 0.25R witness

Every observed half-year delta is >= 0.

R8:

- 2016H1: unchanged
- 2016H2: +0.03869R/trade
- 2017H1: unchanged
- 2017H2: unchanged
- 2018H1: unchanged

R6:

- 2018H1: +0.02000R/trade
- 2018H2: +0.03710R/trade
- 2019H1: +0.04784R/trade
- 2019H2: unchanged
- 2020H1: +0.05285R/trade

R5:

- 2020H2: +0.03688R/trade
- 2021H1: +0.04122R/trade
- 2021H2: +0.08286R/trade
- 2022H1: +0.07551R/trade
- 2022H2: +0.37391R/trade

This matters more than the aggregate uplift: the witness does not obtain its
benefit by sacrificing a chronological block.

## 6. Wider thresholds falsify "protect earlier is better"

Cross-partition adjudication:

`scripts/vt31_nas100_deep_giveback_cross_partition_v1.py`

### <= +0.50R

R8 and R6 improve, but R5 fails temporal non-degradation:

- R5 2021H2 worsens;
- R5 winner-R preservation falls to ~94.96%.

It still clears the minimum 90% winner-R gate, but it is not clean enough to
replace the conservative research witness.

### <= +0.75R

R5 materially degrades:

- PF falls below baseline;
- mean R falls;
- DD rises;
- winner-count preservation falls to ~84.62%;
- winner-R preservation falls to ~81.76%;
- 2021H2 and 2022H1 degrade.

Rejected for promotion.

### <= +1.00R

The frontier becomes destructive:

- R6 PF and mean deteriorate and DD rises;
- R6 winner-R preservation falls to ~66.64%;
- R5 PF/mean/DD deteriorate;
- R5 winner-R preservation falls to ~75.11%.

Rejected.

### Mechanism conclusion

The stable mechanism is not "trail once a trade has made money."

It is:

> After meaningful MFE, wait until the **closed-price journey has collapsed
> deeply back toward entry**, directional path efficiency is weak, and a new M1
> protective swing is confirmed. Only then consider improving the stop.

The `+0.25R` witness is the conservative consumed-evidence boundary currently
supported by all three partitions.

## 7. DOL1 extension evidence — 547 consumed NAS100 episodes

CIBO Eight-Ledger binding:

- workflow: `35175782935`
- artifact: `10478487667`
- digest:
  `17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192`

Completed opposite-boundary episodes:

- R8: 186
- R6: 180
- R5: 181
- total: 547

Post-DOL1 extension rates:

| Partition | +0.25 ref | +0.50 ref | +1.00 ref | +1.50 ref | +2.00 ref |
|---|---:|---:|---:|---:|---:|
| R8 | 74.19% | 52.15% | 29.03% | 20.97% | 15.05% |
| R6 | 81.11% | 61.11% | 35.00% | 16.67% | 11.67% |
| R5 | 82.87% | 62.43% | 37.57% | 20.44% | 10.50% |

### Stable extension-enriched causal states

The strongest cross-partition mechanisms are:

- first breach -> DOL1 <= 60 minutes;
- DOL1 reached during 10:00-10:59 NY;
- DOL1 reached during 11:00-11:59 NY;
- source confirmation -> DOL1 in the 31-60 minute region, with smaller sample.

For breach -> DOL1 <=60m:

| Partition | n | +0.25 ref | +0.50 ref | +1.00 ref |
|---|---:|---:|---:|---:|
| R8 | 64 | 89.06% | 70.31% | 46.88% |
| R6 | 54 | 87.04% | 75.93% | 46.30% |
| R5 | 55 | 89.09% | 74.55% | 49.09% |

### Stable depleted states

Extension is materially weaker when:

- breach -> DOL1 takes >240 minutes;
- source confirmation -> DOL1 takes >120 minutes;
- DOL1 is reached in 14:00-14:59 NY;
- DOL1 is reached in 15:00-15:59 NY.

Therefore time-to-delivery and remaining lifecycle are legitimate target
intelligence dimensions.

## 8. DOL1 lock falsification

A critical negative result:

> Moving the runner stop directly to DOL1 immediately after DOL1 conquest is
> not runner-safe.

Across the consumed 547-episode study, DOL1 is frequently retested before the
post-boundary extension develops. An exact DOL1 lock therefore destroys the
extension path.

Consequences:

- generic `DOL_LOCK` at the boundary remains disabled as a runner policy;
- reaching DOL1 is not sufficient evidence to trail to DOL1;
- target extension must be coupled to continuation quality and a protection
  geometry that leaves room for normal NAS100 retest.

## 9. Runner research status

Fast DOL1 delivery is a supported extension-capacity signal, but the tested
runner stop/target geometries are not freeze-ready.

A conservative +0.25-reference runner with buffered protection can be positive
in aggregate and by side, but small negative chronological blocks remain in R8.

Therefore:

- extension mechanism: **SUPPORTED FOR RESEARCH**;
- exact runner target/stop: **NOT PROMOTED**;
- DOL1 exact lock: **REJECTED**;
- fresh holdout: **REMAINS SEALED**.

## 10. Relation to the new full-cognition work

The branch now also contains the full-cognition position state and the
cognition-driven structural-protection frontier.

DGR is intentionally separate because it tests a different mechanism:

- cognitive frontier: pre-entry/full-cognition signatures identify admitted
  trades that may deserve earlier structural protection;
- DGR frontier: causal post-entry journey deterioration identifies a trade that
  has already achieved meaningful MFE and then given it back.

The next mandatory experiment is their interaction on the same admitted
population:

1. baseline;
2. cognition-only protection;
3. DGR-only protection;
4. cognition + DGR;
5. equal normalized R;
6. winner preservation;
7. by side / half-year / fold;
8. no sizing;
9. no holdout.

The combined mechanism may be promoted only if attribution proves that each
component contributes without hiding an entry defect or destroying the large
runner tail.

## 11. Current adjudication

`DGR_CURRENT_CLOSE_MAX_0_25`:

**SUPPORTED_CROSS_PARTITION_RESEARCH_WITNESS**

This is **not** equivalent to:

- runtime policy approved;
- candidate frozen;
- edge certified;
- holdout authorized;
- LIVE authorized.

The next stage is interaction/attribution against the full-cognition structural
protection frontier on consumed evidence.
