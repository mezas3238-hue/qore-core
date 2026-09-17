# VT31_NAS100_R1 — Freeze Contract

Status: DRAFT / HOLDOUT SEALED

This specialist identity is derived from consumed CIBO Atlas and VT31 laboratory evidence. It is intentionally isolated from SP500 and US30 specialist identities.

## Governance

- Research branch only.
- No merge without owner instruction.
- No live or production authority.
- Exactly one new 1Y NAS100 holdout may be opened only after this contract, implementation, focused validation and Full QORE are green and the identity is frozen.
- Once opened, that holdout becomes permanently consumed and must never be relabeled fresh.
- Post-outcome research fields may not be used to choose entries, stops, targets or filters.

## Methodological core retained

- Market: NAS100 only.
- Timezone: America/New_York, DST-aware.
- Reference: 09:00 NY reference structure.
- Operating window: AM Silver Bullet, approximately 10:00–11:00 NY.
- Setup family: liquidity raid/sweep followed by displacement/confirmation into an eligible PD-array context.
- Eligible PD-array context remains the source-method family (FVG / Breaker / Order Block); no retrospective family selection from consumed PnL.
- SMT/cross-index state is contextual telemetry only for R1 and is not a mandatory filter.
- Side is determined causally from the raid/reversal structure, never from future outcome.

## R1 causal corrections from consumed CIBO evidence

### Entry

R1 must not enter solely because a raid occurred. Entry requires a completed pre-entry reversal sequence in the Silver Bullet window with displacement/confirmation and a deterministic executable price derived from the confirmed PD-array/retrace rule implemented in code.

### Initial invalidation

The R8 raid/final-extreme stop is retired for R1. Initial invalidation must be tied to the deterministic displacement-associated/protected structural swing that exists before entry. The stop may not be widened or selected by retrospective PnL.

### Protection lifecycle

Consumed NAS100 research showed materially more post-stop continuation after protected-stop exits than after initial-stop exits. R1 therefore must not arm a protected stop immediately on first favorable movement. Protection may arm only after an objective post-entry structural confirmation defined in code from information available at that instant. Before that event, the original structural invalidation remains in force.

### Target

Fixed 2R is not assumed to be the destination. R1 target selection is structural: the deterministic opposite-liquidity destination known at entry. R-multiples remain measurement telemetry. If structural target data are unavailable or invalid, fail closed rather than substitute a retrospectively favorable target.

### Lifecycle

The trade remains bounded by the AM Silver Bullet lifecycle policy implemented in code. A position that has not completed its structural destination is handled by the deterministic time/lifecycle exit; no post-hoc extension is allowed.

## Mandatory measurements

For consumed validation, the new 1Y holdout and subsequent WFO report at minimum: roots, executable trades, no-trades, censored cases, initial/protected/time/target exits, win rate, total and mean R, PF, max drawdown, max losing streak, long/short decomposition, MFE, MAE, time-to-MFE, time-to-stop, time-to-target, 0.25R/0.5R/1R/1.5R/2R/2.5R/3R excursions, structural-target reach, friction stress, and Monte Carlo path risk.

## Freeze condition

`VT31_NAS100_R1` is not frozen by this document alone. Freeze requires implementation + focused tests + static validation + Full QORE GREEN, all bound to one git SHA/config fingerprint. Until then: `VT31_NAS100_R1 = NOT_FROZEN` and `NAS100_1Y_FRESH_HOLDOUT = SEALED`.
