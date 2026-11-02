# QORE Trader Lab — CRT RADAR PRO 34 preflight bridge (2026-11-01)

Status: **SOURCE METADATA VERIFIED 33/34; REAL HOLDOUT NOT STARTED; NO DEMO/LIVE/ORDERS**.

## Purpose
The owner asked to test CRT RADAR PRO across 34 instruments in the existing GitHub Trader Lab **before** issuing additional Android/Pine candidates. The existing canonical governed lab is `src/qore/infrastructure/trader_lab/`, QORE-TRADER-LAB-001, and its REPLAY→OOS→STRESS→MONTE_CARLO proof chain. The native `VT-08 CRT 4H AMD` evaluator in `src/qore/infrastructure/traders/evaluators.py` uses different methodology from `qore-deepseek-reviewer/crt-radar-pro/CRT_RADAR_PRO_V34_10W_C1_RAZONES_34_QA_NO_INTEGRADO.pine`; **DO NOT equate the two**.

## Reused code and coverage
- Native QORE Trader Lab contract tests: `tests/infrastructure/trader_lab/test_candidate_and_stage_evidence.py`, `test_lifecycle_and_promotion.py`. They prevent fake promotion/evidence transfer, not market-quality validation.
- The read-only, pinned CRT adapter from `mezas3238-hue/qore-deepseek-reviewer` commit `64836b2c23d32302d91d29e514c1a73e2a464440`, under `qore-crt-alerts/src/trader-lab-crt-34-gate.mjs`. The preflight checks source coverage and closed-H4 causal smoke on **synthetic** 34 sources. This stage never reports actual holdout successes.
- 33 original M5 source artifacts (not the raw data themselves) exist on QORE Core Actions runs `35166210458` (12, expires **2026-12-16T00:21:18Z**) and `38193802541` (21, expires **2027-01-10T01:56:00Z**). These are original IC Markets cTrader DEMO sources from the Native/Atlas research streams, not TradingView-certified data.
- Mapping of all **33/33 non-BTC** symbols in the radar catalog is 1:1. `NAS100USD` is the TradingView alias of archival `NAS100`; `US500` is archival `SP500`. Exact calendar/provider parity still needs evidence.
- **BTCUSD is source #34 and has no archived cTrader M5 source in those runs.** BTC on screenshots came from Coinbase; no approved historical Coinbase 5M artifact is verified. Do not import unmatched BTC prices.

## Hard STOP
- Artifact metadata present does NOT prove licensed right to move/read 700+MB broker OHLC outside authorized custody. No raw data downloaded, no secrets exposed, no repository uploads of broker prices.
- Prior VT08 OOS and CIBO research already used some evidence. Do not retroactively reclassify these prices as unseen holdout. Seal fresh disjoint time windows and code digest before consumption; never modify rules after seeing outcomes.
- Default, no-flag CLI `node qore-crt-alerts/scripts/trader-lab-crt-34-preflight.mjs` returns `BLOCKED_HOLDOUT` exit 2. The workflow uses `--expect-blocked` ONLY to assert **safe refusal** is working; a green workflow is **NOT** a green holdout.
- No orders, auto-execution, FCM, DEMO or LIVE promotion. Do not merge this PR into QORE Core main to imply certification.

## Native workflow
`.github/workflows/trader-lab-crt-radar-34-preflight.yml` checks out both repositories, runs native Trader Lab evidence/lifecycle tests and the exact pinned CRT 34 metadata QA tests, reporting the expected blocked verdict. Trigger by push to this **isolated branch** or DRAFT PR. All tests read deterministic source metadata/fixtures only, no broker APIs.

## Next stage, after preflight
1. Approve a private licensed source vault with restored SHA digests and approved access; preserve 33 originals before expiry.
2. Validate a 34th BTCUSD M5 source and explicit provider mapping (Coinbase vs IC Markets vs OANDA).
3. Freeze exact engine SHA, per-symbol OHLC source provider IDs, cutoff and fresh holdout windows; preregister four structural model rules and valid/invalid scenarios.
4. Convert M5→NY-H4/M15/H1 causally, carry separate MSS pivot/sweep timestamps; compare results to Pine on identical price data. Avoid mixing 2C/3C historical counts as distinct setups.
5. Run 34 real train/OOS replays under governed Trader Lab, produce named `PASS/FAIL/BLOCKED` results per instrument and per CRT morphology, no-lookahead tests and prefix invariance.
6. Validate Pine in TradingView with only those symbols whose provider parity is established. Enable no Android notifications until after real end-to-end push testing.

Evidence: QORE Core issue [#837](https://github.com/mezas3238-hue/qore-core/issues/837), [#812](https://github.com/mezas3238-hue/qore-core/issues/812), [QORE Trader Lab contract](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md), CRT 34 candidate research [PR #69](https://github.com/mezas3238-hue/qore-deepseek-reviewer/pull/69).

## 2026-11-02: Provenance correction and first causal M5 bridge
Pinned CRT candidate now includes [PR #70](https://github.com/mezas3238-hue/qore-deepseek-reviewer/pull/70):
- Origin is **12 cTrader Atlas DEMO broker-UNVERIFIED** and **21 IC Markets DEMO source-catalog-confirmed**, rather than falsely treating all 33 as proven identical IC Markets sources.
- Every archived ZIP has an exact `sha256:` digest reported by GitHub Actions, original capture head SHA, source run ID and expiration. ZIP digests are **not** verified uncompressed OHLC checksums.
- Reconstructs closed New York H4 from 48 contiguous native M5 (no implicit price scaling), with independent index 02/06/22 NY vs Forex/crypto 01/05/21 NY and strict validation of DST local close.
- Synthetic 34-source tests confirm candidate path and negative rejection of 36/60 DST blocks, 48-bar fall-back prefixes, partial candles, gaps, provider/identity mismatches and future candles.
- This stage is **not** historical holdout, no broker account privileges, no original raw price access, no production/FCM rights.
