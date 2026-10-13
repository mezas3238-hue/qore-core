# QORE-Alpha 2 — W2 Full33 provider-volume SOURCE G0B EXECUTED + G1A W1 root cause

**Fecha:** 2026-10-12. **Estado:** W1 NO POSITIVE GROSS SUPPORT/UNDERPOWERED, W2 SOURCE FIELD 33/33 VERIFIED, zero Alpha2 certified, zero orders. **Issue:** #838 and #843; **PR:** #840.

## A. Evidence of actual 33-market source-only experiment

- 4-class fixed source pilot [Actions #38272577494](https://github.com/mezas3238-hue/qore-core/actions/runs/38272577494), 6/6 SUCCESS, exact-head `ddb6112681b5ebc52e22b9cdfef3bbc2c864c22e`: NAS100 560,059/560,059 POSITIVE, XAUUSD 565,955/565,955, EURUSD 596,349/596,349, EURCHF 595,990/595,990 (native M5 rows from pre-embargo coverage).
- Prereg all33 SOURCE before execution: `docs/research/QORE_ALPHA2_W2_FULL33_NATIVE_VOLUME_FIELD_CENSUS_PREREG_2026-10-12.md`, commit `d1c6c5f85b35cc63f1512212b42aa31e491ecccd`.
- 33-source audit [Actions #38273144621](https://github.com/mezas3238-hue/qore-core/actions/runs/38273144621) **35/35 SUCCESS**, exact-head `acf421591a2ded838b0bd73fc6a98a0d918d81e6`, G0 33 original source manifest SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`, each 11-year RAW+quality SHA individually rechecked before reading any provider metadata. Each worker inspected ONLY opened_at, source identity and volume, not OHLC. Full signed artifact `alpha2-w2-source33-volume-census-acf421591a2ded838b0bd73fc6a98a0d918d81e6`.
- Result: **33/33 markets; 19,496,136 / 19,496,136 M5 rows pre-2024-09-17 with `volume` positive integer; 0 null, 0 zeros, 0 negatives, 0 noninteger in the executed coverage.** The original four pilot symbol category counts reconciled exactly against new full33 witnesses.
- **Important semantic limitation:** value type positivity proves a field is populated, **NOT** its semantics (broker-specific tick count? quotation updates? executed contracts?), stable contract mapping, or broker/account equivalence of 12+21. Must obtain original cTrader IC Markets documentation or broker-native identity confirmation before any claim of real traded volume. Historical BID/ASK/commission/fill/news PIT still unknown, and 2016–2024 is already exposed development/diagnosis, not independent certification.

## B. W1 G1A first gross forensic completed

- First native M5 33/33 PATR gross [Actions #38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595) exact-head `b406be34e16e61b7b4c042f31f95cf38a45f4e07`, 35/35 SUCCESS. 224 signal-only originals, 176 paired gross evaluable; DEV 130/163 mean −0.1674348441bps; DIAG 46/61 mean −3.4236609365bps. Neither era meets its prior n min; status UNDERPOWERED, GROSS NOT SUPPORTED, no net.
- Posthoc source-anchored anomaly audit [Actions #38272270791](https://github.com/mezas3238-hue/qore-core/actions/runs/38272270791) **SUCCESS** exact-head `ee30eac5342dc0bdf21d72f316310fedfbb57563`, 48/48 censored by `PATH_GAP_CENSORED`: 33 DEV, 15 DIAG, not losses or gains imputed. Six of 33 symbols had zero PATR signals; 147 weeks contained signals in original signal census.
- DEV calendar 4wk bootstrap of paired delta: mean −0.7287646443bps, IC95 [−2.42921548, 0.0], p descriptive 0.54136; DIAG delta 0.0, bootstrap degeneracy CI null/p=1. It is also logically NONDISCRIMINATIVE because comparator sign same as signal except zero own return.
- No rescue tuning of W1 correlation cutoff, donors or stop/target. Zero UTC-001 certifications.

## C. Next original research track — explicit methodological boundary

W2 G0B now supports investigating a broker-specific participation *proxy* as a causal feature, rather than OHLC-only classical price patterns or W1 lagged-correlation underresponse. **But field semantics remain unresolved.** Before any W2 PnL, freeze a separate mechanistic hypothesis, execution, non-tautological same-slot baseline, falsification, power, and source-to-fill contracts. Gross (if later measured) remains research-only, never labeled broker-net. Every one of the 33 instruments stays in the panel even with zero signals or nonpositive outcome. If poor power or source semantics, stop W2 as SOURCE_BLOCKED/UNDERPOWERED; do not retune consumed 2016–24 to chase returns.

GitHub-only, PR draft, 0 orders; no VPS/MT5/Shared/CIBO/QDLE/LIVE/production. Source field G0 PASS is **not** a strategy Gate pass.
