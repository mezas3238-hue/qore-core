# VT31_NAS100 Intelligence Pilot V1

## Purpose

Build the first intelligent VT31 specialist as a NAS100-only research pilot. Silver Bullet remains the trading methodology. CIBO supplies historical market knowledge; the intelligence layer converts that knowledge into causal, auditable decisions about timing, entry, structural stop, structural target, management, and abstention.

## Governance

- Research only.
- NAS100 only.
- No merge authorization.
- No live, production, real-capital, demo-eligibility, or certification claim.
- No fresh holdout is opened or consumed.
- Only already-consumed CIBO Eight-Ledger evidence and already-consumed R8/R6/R5 M1 evidence are used.
- Aggregate CIBO knowledge may be used; date-level future outcome lookup is forbidden.

## CIBO knowledge binding

- Artifact: `10478487667`
- Digest: `sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192`
- Source SHA: `6dc334723de5b7dca187e12b3a8ff531f4f1045e`

## V1 intelligence policy

1. Timing: no execution before 10:30 New York.
2. Entry: causal local/reference-liquidity reclaim followed by a source-valid Silver Bullet PD-array.
3. Stop: adverse structural extreme observed from raid through decision time.
4. Target: opposite boundary of the frozen 09:00 reference.
5. Management: no premature protected-swing trail or early BE.
6. Abstention: incomplete causal sequence, ambiguous entry, or invalid geometry => no trade.

## Official consumed-fold execution

Workflow run: `35281370819` — SUCCESS across all three folds.

Pilot SHA: `29eb024d7134470c805fa59b1848195acae5e63d`.

> `r8_fresh` is only the inherited historical partition name. It is already-consumed development evidence and is not a fresh holdout in this pilot.

### Stressed economics (-0.05R/trade)

| Fold | Mode | Trades | Total R | Mean R | PF | Max DD R | Max losing streak |
|---|---|---:|---:|---:|---:|---:|---:|
| R8 | fixed baseline | 228 | +12.2671 | +0.05380 | 1.06936 | 50.9176 | 25 |
| R8 | intelligence V1 | 59 | +10.3019 | +0.17461 | 1.20023 | 16.5555 | 14 |
| R6 | fixed baseline | 278 | +91.4948 | +0.32912 | 1.42765 | 37.2176 | 27 |
| R6 | intelligence V1 | 60 | -7.2616 | -0.12103 | 0.86630 | 26.5943 | 22 |
| R5 | fixed baseline | 316 | +40.4513 | +0.12801 | 1.16733 | 46.5236 | 22 |
| R5 | intelligence V1 | 59 | -44.8799 | -0.76068 | 0.20847 | 47.1085 | 30 |

### Capability and geometry

| Fold | Executed decisions | Terminal trades | Median planned target R | Median MFE R | Median MAE R |
|---|---:|---:|---:|---:|---:|
| R8 | 81 | 59 | 7.75 | 0.7822 | 1.2456 |
| R6 | 94 | 60 | 8.6206 | 0.7688 | 1.2446 |
| R5 | 99 | 59 | 9.6259 | 1.1691 | 1.3000 |

Terminal exits:
- R8: 49 initial stops, 9 structural targets, 1 lifecycle exit.
- R6: 51 initial stops, 6 structural targets, 3 lifecycle exits.
- R5: 54 initial stops, 2 structural targets, 3 lifecycle exits.

Artifacts:
- R8: `10521868964`, digest `sha256:00fd62043b5985a86bebc57411f454db73980824742dacc0ae181fdb289114b3`
- R6: `10522393593`, digest `sha256:6db23d8d3a7777a25805710f4b216fbc86359c6a3e9e7d98b2da518d6843d0f5`
- R5: `10522738120`, digest `sha256:50e411ac73eacf8b73b0464efd0a0881578a5b53cf9ea2acc4904a23cd6f63a9`

## V1 forensic interpretation

The architecture proves that a VT31 specialist can make causal, auditable, per-setup decisions from CIBO-derived knowledge without date-level future lookup. It also proves that this first reasoning policy is not stable enough to freeze.

R8 improved materially: mean R increased by `+0.12081R`, PF by `+0.13087`, and max drawdown fell by `34.3621R`. That improvement did not persist: R6 became negative and R5 deteriorated severely.

The dominant V1 geometry mismatch is the combination of a relatively tight adaptive structural stop with a full opposite-09:00-boundary target. Median planned target distance is roughly 7.75R to 9.63R. In R5, every terminal setup whose planned target was at least 8R lost. This is a development diagnostic, not a promotion rule.

The next intelligence iteration must make target destination and timing context-adaptive instead of hard-coding `wait until 10:30` plus `opposite 09 boundary` for every valid setup. Stop geometry must remain causal and structural, with explicit feasibility checks so risk and destination are reasoned about jointly.

## Decision

`VT31_NAS100_INTELLIGENCE_PILOT_V1 = RESEARCH_CAPABILITY_PROVEN_BUT_UNSTABLE`

`FREEZE_READY = FALSE`

`OPEN_FRESH_HOLDOUT = FALSE`
