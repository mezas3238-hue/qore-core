# VT31_NY — 3Y FROZEN CONTROL FAST LOSS-CLUSTER FORENSICS

**Date:** 2026-10-09  
**Lane:** OPS / Architect 2  
**Workflow:** `QORE VT31 NY 3Y Fast Runner Loss Cluster Audit V1`  
**Verified run:** [37990916740](https://github.com/mezas3238-hue/qore-core/actions/runs/37990916740)  
**Execution commit:** `9b6aff4c9c0782e1a3492741f510df481b0e6843`  
**Artifact source:** frozen 3Y control `11459439466` @ `8f91ee489d33c1fa0b90972270d4ac6c32fcca32`.  
**Base:** `VT31_NAS100_OWNER_3Y_BASE_001`, 2023-10-01 inclusive -> 2026-10-01 exclusive.  
**Method:** OBSERVATION ONLY on 55 admitted historical control trades. No new backtest candidate, no market reacquisition, no exposure/sizing, no policy promotion.

## Independently reproduced control numbers

| Measurement | Result |
|---|---:|
| Trades | 55 |
| Aggregate net R (0.05R friction) | +25.4956512133R |
| Maximum continuous trade-order drawdown | 21.3585957183R |
| Maximum consecutive losing trades | 23 |
| Observed DD <=6R gate | FAIL |
| Control certified | NO |

The source's existing adjudicator DD is compared numerically against this fresh independent chronological reconstruction with fail-closed drift checks. Self-test and frozen-source authenticity checks all passed in GitHub Actions.

## Maximum drawdown episode — exact causal *attribution after terminal resolution*

**Peak:** trade index 17, 2024-05-07 (breaker LONG, `dol2-extended-target`).  
**Trough:** trade index 40, 2025-11-20 (breaker SHORT, `structural-invalidation`).  
**Trades after peak through trough:** 23; **23 losses / 0 wins**.  
**Negative loss mass:** 21.3585957183R; **positive offsets:** 0R.

### By source family

| Family | Losing trades | Negative mass |
|---|---:|---:|
| Breaker | 13 | 12.9324685818R |
| Fair-value-gap | 10 | 8.4261271365R |

### By exit reason

| Reason | Losing trades | Negative mass |
|---|---:|---:|
| structural-invalidation | 15 | 15.75R |
| composite-pretarget-cognitive-exit | 8 | 5.6085957183R |

### By side

| Side | Losing trades | Negative mass |
|---|---:|---:|
| Short | 16 | 14.4109756213R |
| Long | 7 | 6.9476200970R |

**Interpretation:** The risk gate failure is not a harmless one-day statistical fluctuation or a composite-DD stitching artifact. This exact frozen NY control suffered 23 successive negative post-friction outcomes over the peak-to-trough segment, despite a positive three-year aggregate R and high payoff winners outside that segment. The exits did cap individual losses but did not reverse their accumulation.

## Next disciplined OPS research

1. Extract *as-of* structural and entry conditions for each of the 23 trades from unchanged consumed 3Y evidence. Compare against winners across the full three-year timeline; attach the terminal label strictly after inference/attribution, never to runtime authority.
2. Especially investigate the 15 structural invalidations: prospective fill-time revalidation and post-fill producer truth owned by Architect 1 (COG). Do not transplant hindsight losses into filters.
3. Profile Breaker (13) and FVG (10) separately by prior closed HTF state, path efficiency, sweep/reclaim/confirmation, setup quality, stop distance and regime; record missing producers and non-applicable states honestly.
4. Candidate interventions must be predeclared and economically replayed on unchanged 3Y evidence with exact chronology and stress. Report rejected winners, lost winner-R, density delta, PF/expectancy, <=6R DD, Sharpe, Sortino and MC.
5. Maintain the >=400/3Y density gate. Reject blind admission relaxation: previous 183-trade relaxation raised DD to ~45.46R and failed robust edge.
6. Parallel lane: audit 3Y `Europe/London` M1 coverage and UK DST *before freezing* new London source/reference/execution model. Neither use NY clocks as London aliases nor claim London certified from NY evidence alone.

## Governance

The fast runner is a diagnostic, not a full cognitive/economic re-run. Consequently it does not establish an improved candidate, a complete London implementation, certification, authority for Fresh Holdout or LIVE deployment. Those remain prohibited until the frozen full Core gates have been independently satisfied.
