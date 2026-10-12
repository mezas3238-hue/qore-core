# QORE Native G1 — seis oportunidades originales E1: SOURCE BID/ASK at entry+theoretical M5 close

Date 2026-10-12. **Study is post hoc and source-only**. From verified E1 originals [PR #864](https://github.com/mezas3238-hue/qore-core/pull/864) / [run #38293096998](https://github.com/mezas3238-hue/qore-core/actions/runs/38293096998), exactly six method×symbol dates had E1 frozen research target-start clock **13:00 UTC**, but the earlier 13:00–13:30 source fragments had no prior native quote, and target theoretical M5 closes at **15:00** lay outside. This study seeks only to **remedy bounded quote-source gaps**, not choose methods or estimate profitability.

## Six frozen E1 opportunity identities (selected by event existence and calendar, never by PnL)

| E1 research symbol | current IC Markets DEMO provider symbol | date UTC | original E1 gross-only method | theoretical entry (bar-open) UTC | theoretical M5 horizon end UTC |
|---|---|---|---|---|---|
| SP500 | US500 | 2021-03-16 | SWEEP_RECLAIM | 13:00 | 15:00 |
| SP500 | US500 | 2023-03-21 | SWEEP_RECLAIM | 13:00 | 15:00 |
| GBPUSD | GBPUSD | 2021-03-16 | RANGE_BREAK_CONT | 13:00 | 15:00 |
| USDJPY | USDJPY | 2021-03-16 | RANGE_BREAK_CONT | 13:00 | 15:00 |
| USDJPY | USDJPY | 2023-03-21 | SWEEP_RECLAIM | 13:00 | 15:00 |
| XAGUSD | XAGUSD | 2023-03-21 | SWEEP_RECLAIM | 13:00 | 15:00 |

**Exactly two pre-specified 10-minute quote windows PER row**, including five minutes before each theoretical decision:
- Entry source: date UTC **[12:55:00,13:05:00)**.
- Theoretical close source: same UTC date **[14:55:00,15:05:00)**.

Six frozen symbol×date event rows ×2 clocks ×2 original broker quote sides = **24 minimum historical cTrader native requests**; all in same authorized IC Markets DEMO account, no orders, no OAuth refresh, no CIBO/Shared, no VPS/MT5/LIVE. Alias current SP500→US500 provenance is verified for this account, **not original 12-market G0 broker contract equivalence**. Indices/metals account swaps/point-lot/funding/news missing. Original E1 outcomes and strategy sign must not be consulted in this SOURCE capture; the source selection was made using **only already reported existence of 6 E1 events**, with no new hypothesis/holdout inference.

## Wire and source attestation

Use exact `ProtoOAGetTickDataReq` separately BID and ASK; preserve original provider `ProtoOATickData` serialized field bytes **without account wrapper/credentials**, page splits and explicit `hasMore` ranges; record integer 1e5 signed-delta replay and normalized decimal time-ordered streams, manifest and SHA. Never commit raw tick data to PUBLIC git; Actions artifact retention 90 days, private approved archive/licensing P0 #837. Fail closed on absent side, unpageable same-ms, more than 64 splits, broker mismatch, same-ms ambiguous prices, non-monotonic timestamp.

**Success only = six E1 historical *research* event clocks have BID/ASK source available at their theoretical entry and M5 horizon close** under quote-side max-age 5s, positive spread, no future tick. If 0/6 eligible, report precise limitation, DO NOT substitute windows or outcome-based parameter search. E1 gross-only no stop/target/real exit execution, no PIT news, no broker executable commission/slippage/financing. Gates HISTORICAL_NET_BLOCKED and CERTIFIED_0_OF_3 regardless. Maintain 2024-09-17+ economic holdout embargo intact.
