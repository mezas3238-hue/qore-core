# SMT dual-route indices — preregistered research prototype (2026-11-07)

Status: **RESEARCH ONLY / NO LIVE / NO MERGE / NO VPS / NO ORDERS**.

## Owner mandate
Investigate SMT divergence across **SPX500, NDX100 and US30** both as:
- **Route A** CRT H4 + SMT divergence + closed MSS (confirmation of an existing CRT).
- **Route B** independently qualified liquidity sweep + SMT divergence + closed MSS (no valid CRT).

This module deliberately DOES NOT change CRT RADAR V34.12X, CRT seven-family
detection, VT08 CRT PURE, indicator Pine, funded accounts, QORE Risk or
production connectors. Source candle parity remains independently unapproved
under [PR #1005](https://github.com/mezas3238-hue/qore-core/pull/1005).

## Exact R0 hypothesis (QORE engineering, NOT an author-certified ICT rule)
Input: three separate, same-feed, closed M15 OHLC streams with exact common UTC
timestamps. No missing bars in the last lookback+1 sample, no cross-feed mixing.
Default prior-window lookback: 8 completed bars (120 minutes); tune only in
new, explicitly versioned research after a new preregistration.

For each pair, at end t:
- **Bearish**: one index high(t) strictly exceeds max(highs t-8..t-1)
  and closes strictly below that previous maximum (sweep + reclaim);
  the other index's high(t) does NOT exceed its own corresponding maximum.
- **Bullish**: one index low(t) strictly falls below min(lows t-8..t-1)
  and closes strictly above that previous minimum; the other index's
  low(t) does NOT fall below its own corresponding minimum.
- Exact highs/lows ties do not constitute breaks.
- This rolling-window operationalization is NOT a synchronized swing-pivot
  detector. The next phase must contrast with causal confirmed-swing SMT and
  sensitivity to feed, candle phase and clock alignment.
- Pairs in priority order: SPX500/NDX100, SPX500/US30, NDX100/US30.
  Multiple paired divergences of the same direction deduplicate to at most
  one research opportunity per instrument/direction at evaluation time.

## Evidence-based dual-route qualification
Output: `ResearchOpportunity(status="RESEARCH_ONLY")`, **not** an alert or order.

At observation clock t:
1. A candidate SMT must already exist, closed at or before t, age <=60m.
2. Closed MSS evidence for the instrument must be direction-aligned; its
   confirming close must cross its specified protected swing by price.
   The MSS must close **at or after SMT observation**, not before, and
   both SMT and MSS must be no older than 60m at evaluation.
3. Default research evaluation window is 09:30 inclusive to 11:30 exclusive
   **America/New_York**, with zone-aware DST and weekdays only.
4. Existing **valid, direction-aligned CRT** selects Route A only when
   its source supplies an explicit expiry timestamp and the observation is
   strictly before that expiry. Missing expiry fails closed.
5. Route B requires **explicit recent CRT-absence evidence** from a detector
   that evaluated **all seven families** and reported no active CRT, timestamped
   at or after the SMT candidate. A missing CRT record is UNKNOWN, never proof
   of absence. An active CRT in the opposing direction **blocks** both routes.
   Contradictory active-CRT and no-CRT evidence also blocks.
6. Opposite simultaneous SMT directions for one index abstain.
7. If one data/feed/time/MSS requirement is absent, the engine abstains.

CRT, certified seven-family CRT-absence and MSS evidences are presently
**independent input contracts** supplied by a future verified adapter. They are not invented or rebuilt from this module.
The `MSS` verifier checks timestamp/direction/price-vs-protected-level only;
actual source M5 candles, true protected-swing ownership and feed/phase parity
MUST be cross-checked by the integration gate before any external notification.

## Research evaluation plan (not yet run)
- Freeze event definitions **before** inspecting historical outcomes.
- Three years, full chronological replay; strictly separated development vs
  untouched holdout, with market-day grouping for correlated indices.
- Compare A: CRT+MSS, B: CRT+SMT+MSS, C: SMT+sweep+MSS without CRT,
  D: baseline A plus independent C.
- Report candidates, abstentions, per-symbol and per-pair density, average R,
  PF, MAE/MFE, transaction costs, MAXDD, opportunity concentration, and
  walk-forward + post-freeze OOS tests. Include spread/commission/slippage and
  funded-account volume/margin constraints.
- No synthetic bars, future-swings, lookahead or after-the-fact reassignment.
- Trades on correlated indices must be grouped by the same underlying event
  to avoid hidden double/triple exposure. Metrics after costs decide promotion.
- Validate that historical cTrader/ICMarkets sources match the actual execution
  symbol semantics before making financial claims.

## Gates and known blockers
- G0: standalone deterministic candidate algorithm — implemented, local test
  definitions committed; CI must confirm.
- G1: actual synchronized historical cTrader M15 feed for all three indices,
  broker symbol metadata and schedule — **missing**.
- G2: CRT seven-family authoritative validated event adapter — **missing**.
- G3: audited M5/M15 MSS causal detector / protected-swing evidence — **missing**.
- G4: real broker cost model, futures/CFD parity and news calendar — **missing**.
- G5: preregistered historical replay, OOS and independent review — **NOT DONE**.
- G6: Owner explicit approval for any alerts, account, demo or LIVE — **NOT GIVEN**.

**No real SMT signal is asserted for the November 5 screenshots**; the price
axis visual estimates and unsynchronized chart layouts cannot certify SMT.

## R1 — OFFLINE cTrader DEMO M5-to-M15 historical candidate census

Added read-only code:
- `src/qore/infrastructure/trader_lab/index_smt_census.py`
- `tests/research/test_index_smt_census.py`
- isolated index SMT CI gate.

**No historical candles were downloaded or authenticated by this change.**
R1 is an ingestion/chronological-census implementation, not realized
backtesting or P&L. R1 does not create MSS or CRT signals.

### Mandatory input contract

Supply **three separate CSV exports**, one per canonical symbol SPX500, NDX100,
US30, sourced from the same explicitly named IC Markets cTrader DEMO server.
Header order must be exact:

```csv
origin,broker,environment,server,canonical_symbol,broker_symbol,open_time_utc,open,high,low,close,closed
```

For each row:
- `origin=CTRADER_IC_DEMO`, `broker=IC MARKETS`, `environment=DEMO`;
- `server` is nonempty and identical across all three datasets;
- `canonical_symbol` must exactly match the independently selected research
  instrument and `broker_symbol` must match the **explicit** caller-provided
  ticker; no silent instrument aliasing is allowed;
- `open_time_utc` must carry a UTC offset or Z and align to an exact M5 open;
- OHLC must be finite and internally consistent; `closed=true`;
- timestamps strictly ascend with no duplicates, synthetic bars or forward fill.

An accepted row is **structured input**, not proof that the file was actually
issued by the broker. Source authenticity remains a separate gate. BLAKE? No:
SHA-256 is recorded for every supplied file, together with row coverage.

### Causal aggregation, census and output
- Three adjacent M5 opens at 00,05,10 / 15,20,25 / 30,35,40 / 45,50,55
  aggregate into exactly one closed M15. An incomplete group is skipped.
- For each M15 close in the 09:30–11:30 NY weekday observation window,
  a full strictly contiguous nine-M15-bar history **in all three symbols**
  must exist before a prior-eight-bar SMT candidate can be considered.
- Historical candle closes are timestamped as `open_time_utc + 15 min`.
- All detected pair/sweep/direction events retain price references and
  UTC confirmation time, even when multiple pairs overlap; they are
  **observations**, not entry signals or independent trades.
- Report distinguishes missing current-market bars from insufficient
  historical lookback; missing data always abstains.
- Timestamp conversion uses `America/New_York` to handle DST.

Run only after the authorized real CSVs are provided and reviewed:

```bash
python -m qore.infrastructure.trader_lab.index_smt_census \
  --spx500-csv /path/SPX500.csv --spx500-broker-symbol US500 \
  --ndx100-csv /path/NDX100.csv --ndx100-broker-symbol USTEC \
  --us30-csv /path/US30.csv --us30-broker-symbol US30 \
  --out /path/smt_candidate_census.json
```

Tickers in the command are **examples based on previous IC Markets research**,
not a confirmed symbol mapping for the user's specific cTrader account.
Verify broker metadata before executing. The output contains
`authorized_to_trade=false`, `authorized_to_emit_alerts=false`,
`data_source_authenticity_verified=false` and `economic_edge_certified=false`.

### Still blocked
No actual synchronized real M5 exports for all three instruments are present in
this research PR. No verified historical CRT or MSS event ledger has been
integrated. No baseline A/B/C/D market-outcome replay has been executed.
All gates G1–G6 remain open. No operational alert, account or broker connector
was activated.

## R1 safety correction: no-CRT is not the same as unobserved CRT

The no-CRT route explicitly requires a `CRTAbsenceEvidence` object for the
instrument. It must contain unique identities for all seven evaluated families,
a nonempty detector ID, and a recent scan time not earlier than the SMT event.
This is **only a research evidence contract**, not a certification of the
currently incomplete seven-family indicator. If the adapter cannot prove all
families were evaluated, independent opportunities abstain.

MSS confirmation must also occur no earlier than the SMT candidate; old MSS
cannot be retrospectively attached to a new divergence.

Existing historical candidate census remains usable independently: it reports
SMT divergence observations and does not claim to be an executable strategy.

## R2: reuse existing cTrader DEMO trendbar decoding (2026-11-08)

New pure bridge:
`src/qore/infrastructure/trader_lab/index_smt_ctrader_bridge.py`

The upstream QORE runtime already offers `CTraderTrendbarReadResult` and
`CTraderTrendbar` in `ctrader_demo_market_data.py`. The bridge accepts one
of these **sanitized pre-fetched read results** without owning API credentials,
network connections, account operations or filesystem privileges.

It requires the caller to supply:
- canonical research index and the QORE runtime instrument;
- broker symbol, positive cTrader symbol ID and digits;
- explicit cTrader DEMO server identity;
- UTC `observed_at` as the only permitted closed-candle cutoff.

Checks:
- exact provider symbol ID and digits against caller-supplied mapping;
- native M5 period, nonempty batch and `has_more=false`;
- ascending unique provider `utcTimestampInMinutes`, five-minute alignment;
- no trendbar whose full five-minute interval ends later than `observed_at`;
- cTrader `low + deltaOpen/deltaHigh/deltaClose` relative prices, divisor
  100000, digit quantization matching existing QORE decoder;
- exact 12-column CSV, preserving all raw M5 timestamps without gap-fill;
- roundtrip via independent M5 CSV validator and M15 aggregation.

**Important provider limitation:** existing `CTraderOpenApiMarketDataClient`
currently creates `CTraderTrendbarReadResult` without propagating a provider
pagination/truncation marker; `has_more` defaults to false. Therefore the
bridge's `has_more=false` check **alone cannot establish that a historical
response is complete**. Before historical certification, implement and audit
request-interval reconciliation against a server schedule and explicit source
symbol identity. Do not label source authenticity verified solely because
a CSV came from this bridge.

The current demo `read_external_ohlc` adapter is optimized for an exact
single M5 interval and rejects multi-bar replies. It is **not** yet a
three-year bulk downloader. This work creates a compatible offline bridge,
not a connected historical extraction service.

All tests use intentionally synthetic trendbars and establish only
deterministic serialization/validation. No real feed was read or analyzed.

## R2 integration control — full synthetic pipeline

The focused QA also contains
`tests/research/test_index_smt_pipeline.py`, which drives *all three*
synthetic cTrader-native M5 read results through:
`encode_sanitized_ctrader_m5` -> actual CSV serialization ->
`load_ctrader_m5_export` -> 3× M5 aggregation -> M15 SMT census.

A deliberate SPX500 high sweep against unconfirmed NDX100 and US30 produces
two pairwise **research candidates**, not two independent trades.
A deliberately shifted index series must not produce any candidate.
The test outputs always keep `authorized_to_trade=false` and
`authorized_to_emit_alerts=false`. No historical market data was provided.

**Next real integration gate:** obtain actual closed historical M5 cTrader
read results for all 3 broker symbol IDs from the same authorized DEMO
server, reconcile request coverage/market schedules and source timestamps,
verify the tick-value/contract metadata independently, and only then run
a documented 3-index census. Do not supply secrets in GitHub.
