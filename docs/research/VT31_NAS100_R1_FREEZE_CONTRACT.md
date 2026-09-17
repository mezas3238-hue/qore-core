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
- Reference: 09:00–10:00 NY frozen reference range built only from closed M1 bars.
- Operating window: 10:00–11:00 NY AM Silver Bullet.
- Setup family: strict first-side liquidity raid/sweep, both-sides-swept abstention, post-raid structural close, then eligible PD-array evidence.
- Eligible PD-array families remain the source-method families: FVG / Breaker / Order Block. No family is selected or removed using consumed PnL.
- Executable price uses the already-versioned R2.2 execution policy: FVG consequent encroachment, Breaker/OB body midpoint, earliest actionable confluence, fail closed on ambiguous contemporaneous prices.
- SMT/cross-index state is contextual telemetry only for R1 and is not a mandatory filter.
- Side is determined causally from the raid/reversal structure, never from future outcome.

## R1 causal corrections from consumed CIBO evidence

### Entry

R1 does not inherit the R8 empirical quality/tail filters. It uses the source-anchored R2.2 causal sequence and its separately fingerprinted execution policy. This prevents consumed outcome labels from becoming new entry filters.

### Initial invalidation

The initial stop is the source-methodological swing extreme already frozen in the R2.2 source setup, with no retrospective widening and no extra buffer. CIBO root-cause evidence explicitly does not prove that initial stops should simply be widened; therefore R1 does not optimize stop distance from consumed PnL.

### Protection lifecycle

R8/R5 M1 protected-swing trailing is removed from R1. Consumed NAS100 research showed substantially more eventual source-objective completion after protected-stop exits than after initial-stop exits, concentrating the repair on premature management rather than on arbitrary stop widening. R1 uses the source-anchored containment rule: the original structural stop remains in force until price reaches the setup's precomputed 3R management boundary; only then is the stop moved once to breakeven. No further trailing is allowed.

### Target

Fixed 2R is retired. The target is the opposite frozen 09:00 reference boundary carried by the source setup and known before entry. R-multiples are measurement telemetry, not the target selector. If the structural target is not valid relative to entry/stop, the setup fails closed.

### Lifecycle

Pending orders expire at 11:00 NY. Filled positions may survive 11:00 and are bounded by the deterministic 16:00 NY research lifecycle. If neither stop nor structural target has resolved by the lifecycle boundary, the last admissible pre-16:00 close is used as the time exit. Gaps or unresolved same-bar path ambiguity fail closed/censor rather than assume a favorable sequence.

## Mandatory measurements

The new 1Y holdout and subsequent WFO report at minimum: market days, source setups, executable setups, fills, no-fills, censored cases, initial-stop / breakeven-stop / lifecycle / structural-target exits, win rate, total and mean R, PF, max drawdown, max losing streak, long/short decomposition, entry family, planned structural target R, MFE, MAE, time-to-MFE, time-to-stop, time-to-target, 0.25R/0.5R/1R/1.5R/2R/2.5R/3R excursion reach, structural-target reach, friction stress, and Monte Carlo path risk.

## Holdout order

Per Owner instruction dated 17-Sep-2026, R1 is frozen before opening the holdout; the new intact 1Y NAS100 holdout is then evaluated once, permanently consumed, and only after that result is the unchanged R1 introduced to WFO. The holdout is not reused as fresh evidence and no post-open retuning is permitted.

## Freeze condition

`VT31_NAS100_R1` is not frozen by this document alone. Freeze requires implementation + focused tests + static validation + Full QORE GREEN, all bound to one git SHA/config fingerprint. Until then: `VT31_NAS100_R1 = NOT_FROZEN` and `NAS100_1Y_FRESH_HOLDOUT = SEALED`.