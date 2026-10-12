# QORE-Alpha 2 — W2 volume/tick-activity feasibility prereg SOURCE ONLY
**Fecha:** 2026-10-12. **Issue #843**. W1 G1A results ALREADY observed, therefore W2 is a distinct, NEW hypothesis discovery track; no retrospective tuning of PATR W1. Do not call 2016–2024 a new independent validation set.

## Question
Does the retained provider-native M5 record a usable native **activity proxy**, e.g. broker tick count? Does this field have sufficient provenance and stable nonzero coverage before testing any causal liquidity/price-impact mechanisms? In spot FX and CFD, `volume` **must not be called real traded size** without independent broker-specific evidence.

## Strict pilot protocol before any W2 OHLC
Four FIXED symbols (not selected by return): **NAS100** index; **XAUUSD** metal; **EURUSD** USD FX major; **EURCHF** FX cross. Each worker downloads its ORIGINAL annual M5 SHA ledger from verified runs #35166210458 (first three) or #38193802541 (EURCHF), plus source33 manifest run #38207337960 and original12 aggregate where applicable. Reverify 11-year RAW+quality partitions and identity BEFORE inspection. Examine only `opened_at`, provider identity, `volume`; **never access OHLC price, direction, returns, PnL**. Observe retained pre-2024-09-17 bars only (years 2016–2024). Report per-year total row counts, volumes NULL, zero, positive, negative, non-integer and basic positive quantiles, plus source type; no filter by profitable market. Missing broker definition of `volume` = `PROVIDER_VOLUME_SEMANTICS_UNVERIFIED`. Timestamp/source verification is not a warranty of tradable data.

## Gate and next steps
If coverage or semantics inadequate, W2 activity mechanism SOURCE_BLOCKED, not market falsification. If adequate, extend SOURCE ONLY to all 33, reconcile cohort differences, then PRE-register entirely new independent market-impact/elasticity hypothesis including control NOT directionally tautological, costs/news-PIT and prospective OOS; never reuse W1 results for tuning. Do not touch production/MT5/VPS/CIBO/Shared; no orders, no gross or net PnL in this pilot.
