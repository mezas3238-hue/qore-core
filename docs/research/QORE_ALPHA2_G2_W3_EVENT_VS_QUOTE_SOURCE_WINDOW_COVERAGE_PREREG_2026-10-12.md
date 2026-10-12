# QORE-Alpha 2 — G2 source window VS W3 33-market event-time coverage, pre-registered

**2026-10-12, before joining the two existing signed artifacts for this question.** Diagnostic of data availability ONLY; do not recalculate any strategy's PnL or touch post-2024-09-17 OHLC/2026 held quote prices. W1/W2/W3 are frozen as non-supported economic hypotheses.

## Frozen original inputs

1. W3 CMTRL original event ledger: 33 worker artifacts from [GitHub Actions #38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503), exact frozen source HEAD `e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c`; 24,487 original signals and 24,399 strategy-control pairs in the original signed result. Required original 33 source manifest SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`; original worker SHA + exact head checked before inspecting entry and exit times.
2. G2 real historical quote **metadata index** from [Alpha2 Actions #38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813), exact HEAD `bffb5e8ff5bb9ce12e515bb2558d12001472d9a3`. SOURCE29 original provider BID/ASK side source SHA already independently verified. This experiment reads **only source metadata and no tick value bytes**, and only two windows of 10min: `[2020-09-15T13:00Z,13:10Z)` and `[2023-09-19T13:00Z,13:10Z)`. Original third 2026 historical quote window explicitly excluded.
3. Match exact canonical symbol for 29 sources. Remaining four symbols NZDUSD, XAGUSD, SP500 and NAS100 labelled `OUTSIDE_29_SOURCE_SCOPE`, even though separate source captures exist for some; do NOT infer NAS100=USTEC contract equivalence.

## Predeclared statistics, no search/no winner selection

For every one of 33 symbols, preserve original count, original paired count, and the timestamps of `plan.entry_utc`, `strategy.exit_utc` and `control.exit_utc` **only when arm status was COMPLETE_GROSS_PROXY**. Categorize whether planned entry lies in one of two fixed source quote windows, and whether the strategy and control's exit also fall inside **that same exact** 10-minute window. No stitching windows, no nearest tick imputation, no conditional selection by profitability. Require original `entry <= exit <= plan.exit_deadline`; if original evidence contradicts, fail closed.

All 24,487 opportunities including 88 censored enter the denominator; report by 33 markets, 4 families, both eras. Gate `SOURCE_WINDOW_COVERAGE_ONLY`, never `NET`. Even if an entry/exit timestamp overlaps 2020 or 2023, archived quote event timestamp does **not** prove true `available_at`, broker fill, spread if zero, commissions, overnight swap, currency conversion, tick/CFD contract or microstructure. Therefore `executable_net_paths_certified=0` by design; source-coverage count is an upper bound for further source review, NOT trade eligibility.

**No code modifications to W3, no retuning thresholds, no new simulation variant, no extra quote windows after result.** Source only, GitHub research PR #840.
