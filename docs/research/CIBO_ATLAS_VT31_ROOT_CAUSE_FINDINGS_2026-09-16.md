# CIBO Atlas — VT-31 demonstrated root-cause findings

Checkpoint: 2026-09-16
Scope: consumed evidence only; NAS100 / SP500 / US30; no fresh holdout opened.
Status: `NO_R9_NOT_CERTIFIED`; research only; no live/production authority.

## Evidence chain

- Definitive terminal feature source: 618 tick-corrected terminal trades.
- Independent market baseline: CIBO Atlas gap05-compatible scanner, 4,554 market-days, 780/780 ledger roots overlaid.
- Root-cause attribution workflow: run `35151974924`, SUCCESS, artifact `10469098482`, digest `sha256:722c92398e0af62f7ab20b27adc2d0e9fd013ebe7fd7f800122e126e6d6d6ffd`.
- Error concentration workflow: run `35152248833`, SUCCESS, artifact `10469487529`, digest `sha256:9caa2b160885fa4a6960125c231789cf0af2044a16838600fd7bf95100ff78ff`.

## Demonstrated fact

All 618 terminal rows have the source-defined opposite 09:00 liquidity objective beyond the frozen 2R target.

Therefore, for a trade whose terminal event is a stop, if CIBO later observes the opposite 09:00 boundary reached by 16:00, that source objective could not have been reached first while the original position remained open: the frozen 2R target would have been crossed first. Such cases are classified only as:

`DEMONSTRATED_EXIT_BEFORE_EVENTUAL_SOURCE_OBJECTIVE`

This demonstrates a path mismatch between QORE's exit lifecycle and the later market path. It does **not** by itself prove that the correct repair is a wider stop. Post-exit structure validity must still be tested.

## Aggregate result

- terminal trades: 618
- stops: 463
- demonstrated exit-before-eventual-source-objective cases: 163
- demonstrated rate among stops: 35.2052%
- initial stops: 277
- initial stops followed by eventual source objective: 99 (35.7401%)
- protected stops: 186
- protected stops followed by eventual source objective: 64 (34.4086%)

## Market-specific result

### NAS100

- terminal trades: 208
- stops: 155
- demonstrated path mismatches: 51 / 155 = 32.9032%
- initial stops: 87; later source objective: 20 = 22.9885%
- protected stops: 68; later source objective: 31 = 45.5882%

Primary observed concentration: protected-management exits are the dominant demonstrated mismatch family. This is a research diagnosis, not yet a management rule.

Among NAS100 stops, demonstrated mismatch rates by entry family:
- Breaker: 25 / 75 = 33.33%
- Breaker + Order Block: 6 / 27 = 22.22%
- Fair Value Gap: 13 / 31 = 41.94%
- Order Block: 7 / 22 = 31.82%

Long FVG stops show 7 / 13 = 53.85% eventual source-objective completion, a high consumed-evidence concentration that requires causal validation before any rule change.

### SP500

- terminal trades: 200
- stops: 157
- demonstrated path mismatches: 58 / 157 = 36.9427%
- initial stops: 103; later source objective: 43 = 41.7476%
- protected stops: 54; later source objective: 15 = 27.7778%

Primary observed concentration: initial invalidation is the dominant demonstrated mismatch family.

Among SP500 stops, demonstrated mismatch rates by entry family:
- Breaker: 29 / 67 = 43.28%
- Breaker + Order Block: 10 / 25 = 40.00%
- Fair Value Gap: 12 / 43 = 27.91%
- Order Block: 7 / 22 = 31.82%

SP500 LONG Breaker is especially concentrated: 16 / 27 stops = 59.26% later reach the source objective. SP500 three-index directional-conflict days are also concentrated: 16 / 26 stops = 61.54% later reach the source objective. These are diagnostic cohorts only.

A protected-swing-like state present at signal materially changes this consumed sample: only 1 / 12 such SP500 stops later reaches the source objective, compared with 57 / 145 when it is absent. Sample size is small and this is not a promotion rule.

### US30

- terminal trades: 210
- stops: 151
- demonstrated path mismatches: 54 / 151 = 35.7616%
- initial stops: 87; later source objective: 36 = 41.3793%
- protected stops: 64; later source objective: 18 = 28.1250%

Primary observed concentration: initial invalidation is again larger than protected-management mismatch.

Among US30 stops, demonstrated mismatch rates by entry family:
- Breaker: 32 / 77 = 41.56%
- Breaker + Order Block: 10 / 21 = 47.62%
- Fair Value Gap: 4 / 26 = 15.38%
- Order Block: 8 / 27 = 29.63%

US30 FVG behaves differently from Breaker/Breaker+OB in this consumed evidence. Long FVG specifically has 0 / 14 stops followed by the source objective, while short FVG has 4 / 12. This asymmetry is a hypothesis source only, not an admissibility rule.

## Cross-index concentration

Demonstrated path mismatches among stop cohorts:
- three-directional-conflict: 35 / 76 = 46.05%
- unanimous-high: 58 / 167 = 34.73%
- unanimous-low: 54 / 154 = 35.06%
- mixed-or-incomplete: 10 / 36 = 27.78%
- not-three-market-complete: 6 / 30 = 20.00%

The strongest market-specific cross-index concentration is SP500 under three-directional conflict: 16 / 26 = 61.54%.

This does not justify trading conflict or avoiding unanimity. It demonstrates that simple cross-index agreement is not a sufficient quality criterion and that the three specialists require market-specific context research.

## Pre-entry geometry contrasts

The demonstrated mismatch cohort is not identical across markets.

### NAS100
Median risk/reference:
- demonstrated mismatch stops: ~0.0907
- other stops: ~0.0608

Median entry location/reference:
- demonstrated: ~-0.0241
- other stops: ~-0.0630

This argues against a single universal explanation such as “all premature stops are simply too tight.” NAS100's protected-management problem requires path and structure analysis.

### SP500
Median risk/reference is similar between demonstrated and other stops (~0.0659 vs ~0.0678), while demonstrated cases have weaker median confirmation body (~0.722 vs ~0.800) and slightly larger displacement beyond anchor (~0.0646 vs ~0.0510).

This suggests the SP500 failure cannot be repaired by a simple risk-width threshold alone.

### US30
Median risk/reference:
- demonstrated mismatch stops: ~0.0622
- other stops: ~0.0728

Median raid-to-confirmation latency:
- demonstrated: 2 M1
- other stops: 3 M1

This supports investigation of premature confirmation/entry timing in US30, especially outside FVG, but it is not yet a trading rule.

## What CIBO has demonstrated vs what remains unresolved

Demonstrated:
1. 163 stopped trades exited before the market eventually completed the source-defined objective.
2. The failure mode differs materially by index.
3. NAS100 is disproportionately a protected-management problem in the demonstrated cohort.
4. SP500 and US30 are disproportionately initial-invalidation problems in the demonstrated cohort.
5. Entry-family behavior is market-specific; FVG behaves very differently in US30 from Breaker/Breaker+OB.
6. Cross-index state changes the concentration of path mismatches and cannot be reduced to “more agreement is better.”

Not yet demonstrated:
1. that any stop should simply be widened;
2. that the original signal remained source-valid after QORE exit;
3. that a later source-objective hit was caused by the same Silver Bullet structure rather than a later independent move;
4. the correct replacement protected swing / invalidation geometry;
5. the correct target/lifecycle for each specialist;
6. any R9 candidate.

## Mandatory next causal tests

1. Reconstruct the post-exit M1 path for the 163 demonstrated cases.
2. Test whether source-defined displacement / CISD / protected-swing structure remained valid after QORE exit.
3. Measure executable-fill MFE/MAE using tick evidence where available and conservative M1 bounds elsewhere.
4. Separate `same-setup-later-completes` from `new-independent-move-later-completes`.
5. Compare each demonstrated cohort with same-market stop controls that never reached the source objective.
6. Only then formulate finite market-specific repair hypotheses for NAS100, SP500 and US30.
7. No fresh holdout before market-specific WFO, MC, provider robustness, freeze and Full QORE.
