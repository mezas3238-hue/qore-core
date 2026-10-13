# VT31 G5 — REAL USTEC historical BID/ASK on real Silver Bullet NY source hours: RESULTS

**2026-10-13 · DONE source acquisition / QA, NO EDGE inference / NOT NET.** The owner's request to download source from cTrader has been actioned in a research branch independent of G3. Source selection and time windows were preregistered BEFORE the broker request in commit **`e4835cce13f19e1787b0ec24bad330a13832e471`**. Code/workflow executed on `7bc6f13fb009a9af010a95b144dc10ae5f28a185`, [PR #899](https://github.com/mezas3238-hue/qore-core/pull/899).

## Source execution and integrity (audited, not estimated)

- [GitHub Actions run #38374757273](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273): **SUCCESS** both `source_clock_contract` and `read_only_ustec_source`; frozen clock + no-orders unit tests successful. No source API error reported.
- [GitHub Actions artifact #11801205225](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273/artifacts/11801205225), ZIP digest **SHA256 `7c599294f3853c684f05ee17941b530f35b80bee832e115f51d3d5ff6c3c6f03`**, expires **2027-01-11**. **27 ZIP members**, manifest, 24 side data JSONL files (integer price + decimal converted for each of 12 sided streams), filewise `SHA256SUMS.txt`; inspected independently: **25 / 25 listed hashes match** original ZIP content. No raw market quote files committed to public Git.
- Source **real cTrader historical provider feed**, IC Markets DEMO, native USTEC `symbolId=10014` as of 2026-10-13 (historical NAS100/NDX100 contract equivalence **NOT VERIFIED**). Two sides fetched independently; total **49,661 BID ticks + 49,661 ASK ticks = 99,322**; **20 native broker queries**, cap 300, 6/6 hours have both sides.

| NY day | NY session | UTC source hour (DST-aware) | BID ticks | ASK ticks | Broker requests BID+ASK | Observed spread, index points |
|---|---|---|---:|---:|---:|---:|
| 2024-06-12 | London 03–04 EDT | 07:00–08:00Z | 4,915 | 4,915 | 1+1 | 0.60 |
| 2024-06-12 | NY AM 10–11 EDT | 14:00–15:00Z | 12,445 | 12,445 | 3+3 | 0.40 |
| 2024-06-12 | NY PM 14–15 EDT | 18:00–19:00Z | 13,716 | 13,716 | 3+3 | 0.40 |
| 2025-01-15 | London 03–04 EST | 08:00–09:00Z | 4,378 | 4,378 | 1+1 | 1.00 |
| 2025-01-15 | NY AM 10–11 EST | 15:00–16:00Z | 8,090 | 8,090 | 1+1 | 0.80 |
| 2025-01-15 | NY PM 14–15 EST | 19:00–20:00Z | 6,117 | 6,117 | 1+1 | 0.80 |
| **TOTAL** | **6 hours** | **2 prereg days** | **49,661** | **49,661** | **10+10** | variable across hours |

## Independently rechecked quality observations, limitations

ZIP content test: the corresponding BID and ASK **timestamps are identical in all 49,661 paired rows**; quote values differ, so the streams are NOT copied identical. ALL paired ASK > BID; **0 zero-spread, 0 crossed** at these paired timestamps. Within EACH HOUR the price differential `ASK - BID` is exactly **CONSTANT** (0.60, 0.40, 0.40, 1.00, 0.80, 0.80 index points). This strong synchronization/fixed spread pattern is **a broker history feed property to investigate, not proof of true executable market spreads, independent side arrivals, liquidity, or fills**. At 5-second freshness threshold, one-sided gaps >5 seconds occurred on some hours (observed 29, 0, 3, 21, 0, 0 gaps between paired updates respectively; 53 total), despite all six hours having both sides.

**Critically:** source data **SIX HOURS**, not the 3-year VT31 population. Existing 2,140 opportunities A/B are distinct historical methodology and cannot be used to choose subsequent source hours by PnL. Before integration: verify NAS100↔USTEC↔NDX100 contracts, tick/point money, execution sessions, observed vs historically executable spread, outages, commissions, slippage, broker OMS ACK and real exit. Real source record does not automatically mean real fills. This G5 capture provides *feasibility for acquiring prices at Silver Bullet clock*, not strategy performance, PF, DD, win rate, or certification.

## Next collection work (not falsely represented as already completed)

1. **New larger source-only manifest** of 3Y development sessions by NY date/DST, excluding new fresh OOS; separate ordered shards and batches by month/day, no dependence on PnL or first-trade outcome. Preserve chronology, 2 sides + SHA per bounded shard. Estimate total broker request/tick-byte quotas and durable vault storage with rights and restore BEFORE unbounded requests. QORE Data Vault [#837](https://github.com/mezas3238-hue/qore-core/issues/837).
2. Audit the fixed-spread/same-timestamp observation with known cTrader Protobuf source semantics, before using any value as an executable spread (QORE Native [#856](https://github.com/mezas3238-hue/qore-core/issues/856)); contract NAS100→USTEC [#857](https://github.com/mezas3238-hue/qore-core/issues/857) still open.
3. Remain READ-ONLY, no new cohort V1, no economic replay until G3 protocol gates, no holdout, no main/VPS/LIVE.

**G3 pairs not touched:** act `a446afa17ed6e411b8f0b6fc182b103a78959a97`, tested MSS code `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`; G3 `PENDING_DUAL_SIGNATURE`. QA source ≠ approvals and ≠ edge.
