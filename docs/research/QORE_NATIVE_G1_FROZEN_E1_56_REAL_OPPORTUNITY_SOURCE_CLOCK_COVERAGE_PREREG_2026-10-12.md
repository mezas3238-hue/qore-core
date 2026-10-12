# QORE Native — E1 original event timestamps vs real 5-market native BID/ASK source windows (2026-10-12)

## Scope / empirical origin, NON-VIRGIN, not NET

Following user request to continue, we found frozen **E1 7×33 original market method** witnesses in [Actions #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836), code SHA `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`, prereg commit `67022daf7e2c3335eda991fd217df83fc1a34bc4`, G0 source SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. They contain a **historical research opportunity/decision** timestamp `reference_entry_utc`, theoretical sign and *future gross* labels. We MUST NOT copy future gross labels or mistake E1 M5 returns for fills. The study is descriptive and post-hoc because the historical outcomes were already evaluated; it is NOT a new holdout or independent positive edge study.

The five E1 source artifacts correspond to the five real native Protobuf instruments validated in [PR #860](https://github.com/mezas3238-hue/qore-core/pull/860), [Actions #38288815999](https://github.com/mezas3238-hue/qore-core/actions/runs/38288815999): EURUSD, GBPUSD, USDJPY, XAGUSD, SP500. Exact original E1 symbol source artifacts from run #38257207836:
- EURUSD artifact #11750423859, ZIP SHA `7778ff7b91375dbb2795b892aa8e7a11d69c08a11cd9c19269c67c8c0a044b42`
- GBPUSD #11749804668, `b714aa0f47ba00ddb017e4e9e1865a9f4df46c3da477328b140cef8606fd06a8`
- USDJPY #11750653329, `53197e51d9b6c19f463e5a2487ab58d3bf454c0b63a6c372a6f381eb0446a0a9`
- XAGUSD #11750733271, `9ccad45b0ca2fca7e8483b420bf4f340fab3476af93e85986b6449d4ad262ed8`
- SP500 #11750917832, `c1a31a57a4385ad1609346e1d7e7ab8c460f5639004df1966bc53e2e2f419bef`.
Historical E1 entries already exposed in prior E2 work; prior to this method's creation we inspected these witnesses and counted **56 original method×symbol opportunities** on exactly two dates 2021-03-16 and 2023-03-21. This observed count is NOT preregistered fresh evidence and cannot be used to tune a strategy.

Source quotes: original `ProtoOATickData` artifact #11764163362, workflow #38288411671, original code `8dfae03e8212566d7d334c2598931e57c7b55d64`, SHA ZIP `b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684`. Frozen 2021-03-16 and 2023-03-21, **13:00–13:30 UTC only** (two windows per market). Read/test source using full independent `ProtoOATickData` second decoder SHA + disjoint hasMore leaf validation. Source broker contract equivalence with original CIBO is NOT assumed.

## Deterministic opportunity ledger and theoretical target close only

From all 7 per-symbol E1 method sections, validate exact E1 identity, 7 method roster, source SHA, code SHA, original file digest, `future_ohlc_not_read`, `net_certified=false`, events UTC before 2024-09-17 and duplicate-day exclusion. Extract only `method_id`, `canonical_symbol`, `reference_entry_utc`, frozen E1-derived **theoretical target close clock** (= entry clock + fixed M5 target duration), **without future returns, strategy sign, prices, p-values or money**.

Fixed durations from original E1 code `dfe78f1`, **not optimizable**:
- `REVERSAL_12H`, `PERSISTENCE_12H`, `TREND_MULTI_DAY`: 48×5min = **240min**.
- `SWEEP_RECLAIM`, `RANGE_BREAK_CONT`, `POST_OPEN_CONT`: 24×5min = **120min**.
- `OPEN_INITIAL_REACTION`: 3×5min = **15min**.

For session-dependent E1 clocks, independently reconstruct fixed reference from market family and timezone (FX 08:00 Europe/London; metals 08:00 America/New_York; equity index 09:30 America/New_York), add +15 or +30min as appropriate, and demand exact E1 stored clock. For other methods E1 clock exactly 13:00 or 16:00 UTC. These are **research proxy sessions**, not broker-executable true opens.

For each event on the two historical dates, determine:
1. whether the **actual E1 opportunity timestamp** lies inside same-market frozen quote window;
2. whether the **frozen theoretical exit close** also lies inside that exact 30-minute quote window;
3. if within coverage, quality of BID/ASK at timestamp from last tick <= timestamp, no future, max side age 5000ms, spread must be >0 and not crossed;
4. distinct BLOCKERS `ENTRY_OUTSIDE_SOURCE_WINDOW`, `EXIT_OUTSIDE_SOURCE_WINDOW`, `ENTRY_SOURCE_QUOTE_INVALID`, `EXIT_SOURCE_QUOTE_INVALID` versus `BOTH_SOURCE_QUOTES_OK_NOT_NET`. Do not infer cause from missing data as an absence of trading opportunities.

**No synthetic backtest, no NET, no PF/DD/Sharpe, no authorization for LIVE.** Main result might legitimately be zero eligible pairs if the source 30-minute windows do not span frozen E1 target horizons; that result identifies the **next exact source collection window** instead of a negative edge. Do NOT change the 56 selected opportunities, seven methods, broker aliases, research dates or embargo after seeing the result.

## Exit criteria and follow-up

PASS = all five signed E1 source witnesses SHA/code/prereg checked + exact original Protobuf SHA as-of second decoder + complete deterministic opportunity inventory + theoretical close clocks validated causally + gap counts and file digest in GitHub Actions. Rejected source does NOT equal failed financial strategy, and the tests do NOT certify a trader. Follow-up P0: use these missing E1 entry/exit clock intervals to freeze **bounded native BID/ASK captures** around both times, validate broker contract equivalence, zero spread semantics and historical true costs prior to any G1 NET. No Git public raw quotes, no VPS/MT5/LIVE/CIBO/Shared/QDLE.
