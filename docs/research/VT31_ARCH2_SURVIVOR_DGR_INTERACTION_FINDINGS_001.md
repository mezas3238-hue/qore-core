# VT31 NAS100 — Architect B Survivor + DGR Interaction Findings 001

**Status:** INTERACTION FALSIFIED / SURVIVOR RETAINED / NO POLICY PROMOTION  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Run:** `37382200281` — SUCCESS  
**Head tested:** `6a96ec13e31323b79c8c4ca2f6514546c4329692`

Aggregate artifact: `11375896203`

Fold artifacts:

- R5: `11376230654`
- R6: `11375246925`
- R8: `11375251912`
- consumed 2Y: `11375526395`

## 1. Governance

The experiment preserves:

- identical OCO admitted population;
- identical entry;
- identical initial stop;
- identical structural target;
- identical 3R breakeven;
- identical 16:00 lifecycle;
- equal normalized R;
- no sizing;
- no leverage;
- no compounding;
- no capital weighting;
- no absolute-volume rule;
- no provider-volume rule;
- no partial-exit requirement;
- no terminal-PnL runtime input;
- no future-journey runtime label;
- no fresh holdout.

The combined policy permits at most one Architect-B structural protection move
per trade.

## 2. Variants

- V0: `BASELINE`
- V1: `SURVIVOR_PS1_ONLY`
- V2: `DGR025_SINGLE_ONLY`
- V3: `SURVIVOR_PS1_PLUS_DGR025_FALLBACK`

V3 is mutually exclusive:

1. if `LBB_PATH_SHALLOW_PS1` is eligible, PS1 owns the trade;
2. otherwise DGR025 may act if its post-entry journey condition qualifies;
3. the two mechanisms never stack.

## 3. Equal-R results

### R5

| Variant | PF | Mean R | Total R | DD |
|---|---:|---:|---:|---:|
| Baseline | 1.0938 | +0.0700 | +22.96R | 61.30R |
| Survivor PS1 | **1.1201** | **+0.0882** | **+28.94R** | **57.70R** |
| DGR025 | 1.0190 | +0.0140 | +4.58R | 70.42R |
| Survivor + DGR | 1.0446 | +0.0322 | +10.56R | 66.82R |

DGR materially damages R5. V3 is worse than both V0 and V1.

### R6

| Variant | PF | Mean R | Total R | DD |
|---|---:|---:|---:|---:|
| Baseline | 1.5857 | +0.4195 | +125.43R | 29.06R |
| Survivor PS1 | **1.6200** | **+0.4370** | **+130.67R** | **28.40R** |
| DGR025 | 1.5629 | +0.3944 | +117.91R | 29.10R |
| Survivor + DGR | 1.5969 | +0.4116 | +123.06R | 28.44R |

V3 improves DD slightly versus baseline but degrades PF/mean/total versus the
survivor. DGR is not additive to cognition in R6.

### R8

| Variant | PF | Mean R | Total R | DD |
|---|---:|---:|---:|---:|
| Baseline | 0.9988 | -0.0010 | -0.25R | 43.43R |
| Survivor PS1 | 1.0113 | +0.0087 | +2.24R | 40.94R |
| DGR025 | 1.0061 | +0.0045 | +1.16R | 42.36R |
| Survivor + DGR | **1.0156** | **+0.0115** | **+2.96R** | **40.55R** |

V3 is additive in R8.

### Consumed 2Y

| Variant | PF | Mean R | Total R | DD |
|---|---:|---:|---:|---:|
| Baseline | 0.7413 | -0.2005 | -58.14R | 74.59R |
| Survivor PS1 | 0.7721 | -0.1752 | -50.81R | 68.03R |
| DGR025 | 0.7828 | -0.1594 | -46.23R | 64.85R |
| Survivor + DGR | **0.8142** | **-0.1355** | **-39.29R** | **58.68R** |

V3 helps substantially, but the population remains negative and the effect does
not transfer to R5/R6.

## 4. Frozen gate adjudication

Failed:

- V3 vs baseline PF/mean/DD non-degrading 4/4;
- V3 vs survivor improves PF or mean in >=3/4;
- V3 vs survivor PF/mean/DD non-degrading 4/4;
- R5/R6/R8 half-year mean-delta non-degradation.

Passed:

- winner-preservation floor 4/4.

Final aggregate adjudication:

`NOT_SUPPORTED`

## 5. Temporal failure

V3 obtains aggregate improvement by sacrificing chronological blocks.

Negative mean-R deltas vs baseline include:

- R5: 2021H1, 2021H2, 2022H1;
- R6: 2018H1, 2018H2, 2020H1;
- R8: 2017H2.

Therefore the interaction is not temporally invariant.

## 6. Winner preservation

V3 vs baseline:

- R5: winner count 90.91%, winner-R 91.61%;
- R6: 92.86% / 96.38%;
- R8: 95.24% / 96.03%;
- consumed: 100% / 100%.

The floor passes, but passing winner preservation is insufficient because PF,
mean and temporal gates fail.

## 7. Root-cause attribution

DGR025 on the dense OCO population is not the same economic mechanism as the
earlier smaller-population DGR witness.

On DGR-changed trades:

- R5 total DGR delta is materially negative;
- R6 total DGR delta is negative;
- R8 is slightly positive;
- consumed is positive.

The main broad families are unstable across folds. In particular FVG DGR is
negative in R5/R6 but positive in R8/consumed. It therefore cannot be promoted
as either a positive or negative global DGR rule.

A post-hoc `order-block` DGR subset has positive mean delta in all four burned
folds, including the `order-block + NEUTRAL` intersection, but sample sizes are
very small. This is **mechanism discovery only**, not validation and not
eligible for direct promotion.

No outcome-aware rule is created from that observation.

## 8. Architect B decision

Retain:

`LBB_PATH_SHALLOW_PS1`

Reject for the current dense OCO admitted population:

`DGR025_SINGLE_ONLY`

Reject:

`SURVIVOR_PS1_PLUS_DGR025_FALLBACK`

The earlier DGR witness remains valid only within the population on which it
was established; it is not universalized across VT31 admission populations.

## 9. Next work

Architect B will not respond by tightening generic exits.

Next post-entry work should prioritize causal target/destination intelligence
that can increase payoff without:

- entry filtering;
- sizing;
- partial-volume dependence;
- winner-tail destruction.

The current entry population is still not certifiable. Architect 1 retains
ownership of the admission defect already handed off in
`VT31_ARCH2_TO_ARCH1_EDGE_DEFECT_EVIDENCE_001.md`.

No fresh holdout, candidate freeze, merge, LIVE, real-capital or production
authority is granted by this result.
