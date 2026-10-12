# QORE Native G1 — Ultra Fast as-of BID/ASK parity gate (2026-10-12)

## Why this path exists
QORE's existing **CIBO Trader Lab Ultra Fast** architecture in `docs/research/CIBO_TRADER_LAB_ULTRAFAST_2026-10-08.md` is a specialized prepared-M5/CIBO six-instrument simulation cache, not a native quote replay engine. It cannot automatically be applied to QORE Native's 33-market E1/E2 231 gross results or create historical BID/ASK where none exists.

This strictly isolated research module is a **candidate accelerated replay for decoded provider BID+ASK side streams**. It uses NumPy `searchsorted(..., side='right')` to align to latest available side at each event, with a 5-second source quality quarantine. All original source SHAs and symbol contracts are revalidated and no future quote may be used. The canonical scalar `qore_native_g1_pre_native_side_join_v1.join_historical` remains the authority until accelerated output matches **byte-for-byte**, including JSONL field values and record chronology.

## Unaltered scientific boundaries
- Exact parent G1-PRE source validator: [PR #842](https://github.com/mezas3238-hue/qore-core/pull/842), no actual quote protobuf attested; **never** NET/real fills.
- New native quote provider attempt: [PR #844](https://github.com/mezas3238-hue/qore-core/pull/844), independent branch on IC Markets 24 M1. Historical BID/ASK access is not established by a successful 3-symbol M1 capture.
- Native speed CI input is synthetic. It evaluates **algorithmic parity**, not alpha, not Sharpe/PF, not leverage, not trader certification. Any benchmark speedup is local runner wall time and excludes download, storage, source verification externalities.
- No case-result memoization counts as independent market data or as an additional experiment. The original E2 231 gross tests, Holm/FDR/E3 zero-support status, 0/3 certified traders remain unchanged.
- In a real future broker feed, paired streams require independent upstream decode+hasMore provenance, actual account/contract proof, and all cost/news/fill gates **before** economics. Original demo prices for a later run cannot be treated as the historical broker backtest for prior G0 source. Never merge to production.

## Acceptance
1. Ruff, Pytest and exact reference/parity cases pass for original G1 source contract tests plus 5,000+ synthetic side observations.
2. Benchmark prints CPU duration for scalar vs optimized calculation and hashes both; output SHA and run HEAD in GitHub artifact. **Don't advertise 'X times faster' unless measured**.
3. Any variance between optimized and scalar bytes must abort. Cache is an optimization only and never changes timestamps, decisions, or truth status.
4. GitHub research only; no VPS, no MT5, no LIVE, no CIBO/Shared/QDLE.

**State:** `G1_SPEED_CANDIDATE_ONLY`, `G1_HISTORICAL_NET_BLOCKED`, `CERTIFIED_0_OF_3`.
