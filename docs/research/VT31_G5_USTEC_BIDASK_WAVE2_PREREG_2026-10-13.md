# VT31 G5 USTEC BID/ASK cTrader — WAVE 2 preregistration (before prices)

Date 2026-10-13. Owner authorizes historical cTrader source download toward VT31 economic edge. Wave 1 [PR #899](https://github.com/mezas3238-hue/qore-core/pull/899) downloaded 6 NY Silver Bullet hours, 99,322 BID+ASK tick records. Original source [Actions #38374757273](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273), source ZIP SHA256 `7c599294f3853c684f05ee17941b530f35b80bee832e115f51d3d5ff6c3c6f03`. Wave 1 showed paired BID/ASK identical timestamps and constant spread within each hour: **these source fields may be derived/reconstructed, not independently executable quotes**; do not assume tradability.

**WAVE 2 chosen BEFORE acquiring prices, without inspecting potential Silver Bullet entries or any future PnL.** Eight development dates, selected to sample two calendar years, seasons, winter/EDT and spring/autumn DST; all dates inside already consumed development **2024–2025** and away from fresh future holdout:

| NY day | NY offset | Source clocks NY |
|---|---|---|
| 2024-02-14 | EST UTC−5 | 03–04, 10–11, 14–15 |
| 2024-03-13 | EDT UTC−4 | 03–04, 10–11, 14–15 |
| 2024-05-15 | EDT UTC−4 | 03–04, 10–11, 14–15 |
| 2024-08-14 | EDT UTC−4 | 03–04, 10–11, 14–15 |
| 2024-10-16 | EDT UTC−4 | 03–04, 10–11, 14–15 |
| 2024-12-11 | EST UTC−5 | 03–04, 10–11, 14–15 |
| 2025-02-19 | EST UTC−5 | 03–04, 10–11, 14–15 |
| 2025-04-16 | EDT UTC−4 | 03–04, 10–11, 14–15 |

**24 actual ICT source hours / 48 bid-vs-ask side streams**, start/end UTC via `America/New_York` IANA zone; exclude terminal end ms. Date selection does not represent a statistically random sample, does not select winning setups or authorize calculation of economic VT31 V1 replay. Combine with pilot 6 hours only for *quote quality* diagnostics, never infer historical win rate or PF.

**Exact source contract**: read-only same IC Markets cTrader DEMO account as QORE Native original [PR #853](https://github.com/mezas3238-hue/qore-core/pull/853); original provider symbol `USTEC`, ID **10014**, verify before fetching. Source-only tools from QORE Native for `ProtoOAGetTickDataReq` BID and ASK separately, signed native deltas, `hasMore` exhaustion. Bounds **64 native requests per side/hour**, **300 in batch**, CI timeout **35 minutes**, no orders, no OAuth refresh, no live symbols. Record source run/commit/UTC dates/id and internal SHA256 files, source manifest/zip digest in GitHub Actions artifacts ONLY, **90-day expiry**, no raw prices in public Git, durable secure licensed QORE Data Vault still pending #837. If provider rate-limit, payload ambiguity, gaps, empty sides, invalid account or query budget: output safe partial/blocked, no interpolation.

**What this can show**: whether source real cTrader USTEC historical BID/ASK can cover intended VT31 session clocks at more dates, spread quality, timestamp pairing, duplicated/missing/zero/negative, stale gap frequency, and feasible request budget. **What it CANNOT show**: NAS100↔USTEC contract identity, independent executable bidask, fills or broker ACK, cost schedules, realistic SL/TP intrabar simulation, or whether Silver Bullet strategy has net edge. Do not overclaim six or 30 hours as full 3-year tick history.

**Hard governance boundary**: G3 act `a446afa17ed6e411b8f0b6fc182b103a78959a97`, G3 code `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` do not change. `G3_PENDING_DUAL_SIGNATURE`. No new population V1, no economic replay, no production, no fresh holdout, no historical B51 repair. Wave2 is a separate experimental source lane.
