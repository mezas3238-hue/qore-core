# QORE Native — G1-PRE IC Markets BID/ASK cTrader source feasibility prereg — 2026-10-12

**Source custody**: G0 33 M5 source SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`; G0 3 pilot M1 native SOURCE ONLY verified on [GitHub Actions #38262534602](https://github.com/mezas3238-hue/qore-core/actions/runs/38262534602), SHA `07a5d897703641ccf8317688f6abcdfb55b5766f`, three jobs completed NZDUSD/XAGUSD/SP500. This pilot asks a distinct question: whether the same IC Markets DEMO account makes original native BID/ASK ticks available.

## Experiment frozen BEFORE tick collection
- One symbol **NZDUSD** chosen because native M1 from the *new 21 IC Markets G0 sources* has a successful pilot. This choice is based on source access, **never** a 231-cell PnL ranking.
- Three historical source windows, all UTC and **10 minutes** each: [2020-09-15 13:00,13:10), [2023-09-19 13:00,13:10), [2026-09-15 13:00,13:10). Last sample is provider feasibility only; don't use it to score signals or remove 2024-09-17+ OHLC embargo.
- Queries: cTrader Open API DEMO `ProtoOAGetTickDataReq` strictly BID=1, ASK=2, exact broker-declared account and enabled provider symbol NZDUSD, 6 side requests minimum. No provider substitute, no M1/M5 tick fabrication or downsampling.
- Differential newest-first timestamp decoder; provider integer tick prices in 1e5; `hasMore` exhaustively checked by recursive disjoint millisecond splits, never silently discarding older native ticks. Fail closed on >64 requests per side, unpageable millisecond, bad epochs/prices.
- Exact SHA256 on every side *integer* and normalized-decimal JSONL and aggregate manifest. Zero side ticks are **not** proof of absence or zero spreads. Source quote native parsing is not an executable trade ledger.
- Allowed read requests only, **NO OAuth refresh or orders**, secrets never in artifacts or logs, no VPS/MT5/LIVE/CIBO/Shared/QDLE modifications.

## Fast Runner reuse policy
`docs/research/CIBO_TRADER_LAB_ULTRAFAST_2026-10-08.md` documents acceleration of CIBO H4M5 deterministic **six-source replay**, not third-party tick acquisition. This native pilot adopts its *proof requirements* (SHA custody, frozen experiment/config, bounded workload, no duplicated reads or double-counting a warm cache) but avoids reusing CIBO's strategy memoization or naming such cache as new evidence. First investigate whether native BID/ASK data EXISTS. Once obtained, fast-replay performance parity may be benchmarked on quotes, not PnL proxies.

## Gate
The collector job must authenticate an actual IC Markets DEMO source and produce three **two-sided nonempty** source windows with SHA and no truncation; run status and artifacts must be independently inspected. If broker rejects date range, account token or requests, preserve a sanitized fail-closed blocker; **no fabricated fallback**.

The code CI is synthetic only and cannot prove native quote history. Even complete 3/3 samples **cannot** establish 33-market historical cost, commission, swaps, slippage, broker contract equivalence with original 12 CIBO markets or economic alpha.

After valid source: submit side-stream bytes to [QORE Native G1 as-of join PR #842](https://github.com/mezas3238-hue/qore-core/pull/842), verify G1 join parity and per-side causality, then study executable costs. Otherwise investigate forward quote capture without submitting any orders. Retention 90 days != permanent archive, public repo licence prohibits raw provider dataset commits by default.

**Status before execution**: `G1_SOURCE_PILOT_PREREG`; `HISTORICAL_NET_BLOCKED`; `CERTIFIED_0_OF_3`; `RESEARCH_ONLY`.
